"""
Performance Tracking Middleware

FastAPI middleware for comprehensive performance monitoring including:
- Request/response time tracking
- Slow endpoint detection
- Performance headers
- Request correlation IDs
- Cache and database metrics integration
"""

import time
import uuid
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from config import config
from services.performance import performance_monitor, RequestMetrics
import logging

logger = logging.getLogger(__name__)


class PerformanceTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for tracking request performance metrics
    
    Features:
    - Request/response time measurement
    - Correlation ID assignment and tracking
    - Performance headers in responses
    - Slow request detection and logging
    - Integration with performance monitoring service
    """
    
    def __init__(self, app, enable_timing_headers: bool = None, enable_cache_headers: bool = None):
        super().__init__(app)
        self.enable_timing_headers = (
            enable_timing_headers 
            if enable_timing_headers is not None 
            else config.performance.include_timing_headers
        )
        self.enable_cache_headers = (
            enable_cache_headers 
            if enable_cache_headers is not None 
            else config.performance.include_cache_headers
        )
        
        logger.info(
            "Performance tracking middleware initialized",
            extra={
                "timing_headers": self.enable_timing_headers,
                "cache_headers": self.enable_cache_headers,
                "slow_request_threshold_ms": config.performance.slow_request_threshold_ms
            }
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> StarletteResponse:
        """Process request and track performance metrics"""
        
        # Extract or generate correlation ID
        correlation_id = self._get_correlation_id(request)
        
        # Extract user information if available
        user_id = self._get_user_id(request)
        
        # Start timing
        start_time = time.time()
        
        # Get initial cache metrics for delta calculation
        cache_hits_start, cache_misses_start = self._get_cache_metrics()
        
        # Track query count before request
        initial_query_count = len(performance_monitor.query_metrics)
        
        # Set correlation ID in request state for other components
        request.state.correlation_id = correlation_id
        request.state.start_time = start_time
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Handle exceptions and still record metrics
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Create error response metrics
            error_metrics = RequestMetrics(
                method=request.method,
                path=self._normalize_path(str(request.url.path)),
                status_code=500,
                execution_time_ms=execution_time_ms,
                correlation_id=correlation_id,
                user_id=user_id
            )
            
            performance_monitor.record_request_metrics(error_metrics)
            
            # Log error with performance context
            logger.error(
                f"Request failed with exception",
                extra={
                    "method": request.method,
                    "path": str(request.url.path),
                    "execution_time_ms": execution_time_ms,
                    "correlation_id": correlation_id,
                    "user_id": user_id,
                    "error": str(e)
                }
            )
            
            raise
        
        # Calculate final timing and metrics
        execution_time_ms = (time.time() - start_time) * 1000
        cache_hits_end, cache_misses_end = self._get_cache_metrics()
        
        # Calculate deltas
        cache_hits_delta = cache_hits_end - cache_hits_start
        cache_misses_delta = cache_misses_end - cache_misses_start
        db_queries_delta = len(performance_monitor.query_metrics) - initial_query_count
        
        # Create request metrics
        request_metrics = RequestMetrics(
            method=request.method,
            path=self._normalize_path(str(request.url.path)),
            status_code=response.status_code,
            execution_time_ms=execution_time_ms,
            cache_hits=cache_hits_delta,
            cache_misses=cache_misses_delta,
            db_queries=db_queries_delta,
            correlation_id=correlation_id,
            user_id=user_id
        )
        
        # Record metrics
        performance_monitor.record_request_metrics(request_metrics)
        
        # Add performance headers if enabled
        if self.enable_timing_headers:
            response.headers["X-Response-Time-MS"] = str(round(execution_time_ms, 2))
            response.headers["X-Correlation-ID"] = correlation_id
        
        if self.enable_cache_headers and (cache_hits_delta > 0 or cache_misses_delta > 0):
            response.headers["X-Cache-Hits"] = str(cache_hits_delta)
            response.headers["X-Cache-Misses"] = str(cache_misses_delta)
            if cache_hits_delta + cache_misses_delta > 0:
                hit_rate = cache_hits_delta / (cache_hits_delta + cache_misses_delta) * 100
                response.headers["X-Cache-Hit-Rate"] = f"{round(hit_rate, 1)}%"
        
        # Log slow requests
        if execution_time_ms > config.performance.slow_request_threshold_ms:
            logger.warning(
                f"Slow request detected",
                extra={
                    "method": request.method,
                    "path": str(request.url.path),
                    "execution_time_ms": execution_time_ms,
                    "status_code": response.status_code,
                    "cache_hits": cache_hits_delta,
                    "cache_misses": cache_misses_delta,
                    "db_queries": db_queries_delta,
                    "correlation_id": correlation_id,
                    "user_id": user_id
                }
            )
        
        # Log request summary for debugging
        if config.performance.enable_request_timing:
            logger.debug(
                f"Request completed",
                extra={
                    "method": request.method,
                    "path": str(request.url.path),
                    "execution_time_ms": execution_time_ms,
                    "status_code": response.status_code,
                    "cache_hits": cache_hits_delta,
                    "cache_misses": cache_misses_delta,
                    "db_queries": db_queries_delta,
                    "correlation_id": correlation_id,
                    "user_id": user_id
                }
            )
        
        return response
    
    def _get_correlation_id(self, request: Request) -> str:
        """Extract or generate correlation ID for request tracking"""
        # Check for existing correlation ID in headers
        correlation_id = request.headers.get(config.logging.correlation_id_header)
        
        if not correlation_id:
            # Check common alternative headers
            correlation_id = (
                request.headers.get("X-Request-ID") or
                request.headers.get("X-Trace-ID") or
                request.headers.get("Request-ID")
            )
        
        # Generate new correlation ID if not found
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        return correlation_id
    
    def _get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request if available"""
        # Try to get user from various sources
        user_id = None
        
        # Check for user email header (common pattern in this app)
        user_id = request.headers.get("X-User-Email")
        
        # Check for user in request state (set by auth middleware)
        if hasattr(request.state, "user"):
            user_info = getattr(request.state, "user")
            if isinstance(user_info, dict):
                user_id = user_info.get("email") or user_info.get("id")
            elif hasattr(user_info, "email"):
                user_id = user_info.email
            elif hasattr(user_info, "id"):
                user_id = user_info.id
        
        # Check for authenticated user in security context
        if not user_id and hasattr(request.state, "current_user"):
            current_user = getattr(request.state, "current_user")
            if isinstance(current_user, str):
                user_id = current_user
            elif hasattr(current_user, "email"):
                user_id = current_user.email
        
        return user_id
    
    def _normalize_path(self, path: str) -> str:
        """Normalize request path for metrics grouping"""
        # Remove query parameters
        if "?" in path:
            path = path.split("?")[0]
        
        # Replace UUIDs and IDs with placeholders for better grouping
        import re
        
        # Replace UUIDs
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{uuid}',
            path,
            flags=re.IGNORECASE
        )
        
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        
        # Replace email addresses
        path = re.sub(r'/[^/]+@[^/]+', '/{email}', path)
        
        return path
    
    def _get_cache_metrics(self) -> tuple[int, int]:
        """Get current cache hit/miss counts"""
        try:
            from ...services.cache import get_cache_metrics
            cache_metrics = get_cache_metrics()
            
            total_hits = sum(metrics.get("hits", 0) for metrics in cache_metrics.values())
            total_misses = sum(metrics.get("misses", 0) for metrics in cache_metrics.values())
            
            return total_hits, total_misses
        except Exception:
            return 0, 0


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Lightweight middleware to ensure correlation ID is set for all requests
    
    This middleware runs before the performance middleware and ensures
    correlation IDs are available for logging throughout the request lifecycle.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> StarletteResponse:
        """Ensure correlation ID is set in request state"""
        
        # Get or generate correlation ID
        correlation_id = (
            request.headers.get(config.logging.correlation_id_header) or
            request.headers.get("X-Request-ID") or
            request.headers.get("X-Trace-ID") or
            str(uuid.uuid4())
        )
        
        # Set in request state for access by other components
        request.state.correlation_id = correlation_id
        
        # Process request
        response = await call_next(request)
        
        # Always include correlation ID in response
        response.headers[config.logging.correlation_id_header] = correlation_id
        
        return response


def create_performance_middleware(
    enable_timing_headers: Optional[bool] = None,
    enable_cache_headers: Optional[bool] = None
) -> PerformanceTrackingMiddleware:
    """
    Factory function to create performance tracking middleware
    
    Args:
        enable_timing_headers: Override config for timing headers
        enable_cache_headers: Override config for cache headers
        
    Returns:
        PerformanceTrackingMiddleware instance
    """
    return PerformanceTrackingMiddleware(
        app=None,  # Will be set by FastAPI
        enable_timing_headers=enable_timing_headers,
        enable_cache_headers=enable_cache_headers
    )


def create_correlation_id_middleware() -> CorrelationIDMiddleware:
    """
    Factory function to create correlation ID middleware
    
    Returns:
        CorrelationIDMiddleware instance
    """
    return CorrelationIDMiddleware(app=None)  # Will be set by FastAPI