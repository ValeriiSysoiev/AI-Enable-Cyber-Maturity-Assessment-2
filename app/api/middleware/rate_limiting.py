"""
Rate Limiting Middleware

Implements basic rate limiting using in-memory storage with sliding window approach.
Protects against abuse and ensures fair resource usage.
"""

import time
import logging
from typing import Dict, Optional
from collections import defaultdict, deque
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimitStore:
    """In-memory rate limit storage with automatic cleanup"""
    
    def __init__(self):
        # Store request timestamps per client
        self._requests: Dict[str, deque] = defaultdict(deque)
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
    
    def _cleanup_old_requests(self):
        """Remove old request records to prevent memory leaks"""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff_time = now - 3600  # Remove requests older than 1 hour
        clients_to_remove = []
        
        for client, requests in self._requests.items():
            # Remove old requests
            while requests and requests[0] < cutoff_time:
                requests.popleft()
            
            # Remove empty client records
            if not requests:
                clients_to_remove.append(client)
        
        for client in clients_to_remove:
            del self._requests[client]
        
        self._last_cleanup = now
        logger.debug(f"Rate limit cleanup completed. Active clients: {len(self._requests)}")
    
    def add_request(self, client_id: str, timestamp: float):
        """Add a request timestamp for a client"""
        self._cleanup_old_requests()
        self._requests[client_id].append(timestamp)
    
    def get_request_count(self, client_id: str, window_seconds: int) -> int:
        """Get number of requests in the last window_seconds"""
        now = time.time()
        cutoff_time = now - window_seconds
        
        requests = self._requests.get(client_id, deque())
        
        # Remove old requests from the window
        while requests and requests[0] < cutoff_time:
            requests.popleft()
        
        return len(requests)


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with configurable limits
    
    Uses sliding window approach with in-memory storage.
    Different limits can be applied based on endpoint patterns.
    """
    
    def __init__(
        self,
        app,
        default_requests_per_minute: int = 60,
        burst_requests_per_second: int = 10,
        admin_requests_per_minute: int = 120,
        health_requests_per_minute: int = 300,
        enabled: bool = True
    ):
        super().__init__(app)
        self.enabled = enabled
        self.default_requests_per_minute = default_requests_per_minute
        self.burst_requests_per_second = burst_requests_per_second
        self.admin_requests_per_minute = admin_requests_per_minute
        self.health_requests_per_minute = health_requests_per_minute
        self.store = RateLimitStore()
    
    def get_client_id(self, request: Request) -> str:
        """
        Get client identifier for rate limiting
        Uses IP address and user agent for identification
        """
        # Try to get real IP from reverse proxy headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Include User-Agent to differentiate between clients from same IP
        user_agent = request.headers.get("User-Agent", "")[:50]  # Truncate
        
        return f"{client_ip}|{user_agent}"
    
    def get_rate_limits(self, request: Request) -> tuple[int, int]:
        """
        Get rate limits for the request based on endpoint
        Returns (requests_per_minute, requests_per_second)
        """
        path = request.url.path.lower()
        
        # Health endpoints get higher limits
        if path in ["/health", "/version", "/"]:
            return self.health_requests_per_minute, self.burst_requests_per_second * 2
        
        # Admin endpoints get higher limits
        if path.startswith("/api/admin/"):
            return self.admin_requests_per_minute, self.burst_requests_per_second
        
        # OpenAPI documentation
        if path in ["/docs", "/redoc", "/openapi.json"]:
            return self.default_requests_per_minute // 2, self.burst_requests_per_second // 2
        
        # Default limits for API endpoints
        return self.default_requests_per_minute, self.burst_requests_per_second
    
    def create_rate_limit_response(
        self, 
        requests_per_minute: int, 
        current_count_minute: int,
        requests_per_second: int,
        current_count_second: int,
        retry_after: int
    ) -> JSONResponse:
        """Create a rate limit exceeded response"""
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please slow down.",
                "limits": {
                    "requests_per_minute": requests_per_minute,
                    "requests_per_second": requests_per_second
                },
                "current": {
                    "requests_this_minute": current_count_minute,
                    "requests_this_second": current_count_second
                },
                "retry_after_seconds": retry_after
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit-Minute": str(requests_per_minute),
                "X-RateLimit-Limit-Second": str(requests_per_second),
                "X-RateLimit-Remaining-Minute": str(max(0, requests_per_minute - current_count_minute)),
                "X-RateLimit-Remaining-Second": str(max(0, requests_per_second - current_count_second))
            }
        )
    
    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)
        
        client_id = self.get_client_id(request)
        requests_per_minute, requests_per_second = self.get_rate_limits(request)
        
        now = time.time()
        
        # Check current request counts
        current_count_minute = self.store.get_request_count(client_id, 60)
        current_count_second = self.store.get_request_count(client_id, 1)
        
        # Check rate limits
        minute_exceeded = current_count_minute >= requests_per_minute
        second_exceeded = current_count_second >= requests_per_second
        
        if minute_exceeded or second_exceeded:
            # Determine retry after time
            if second_exceeded:
                retry_after = 1  # Wait 1 second for burst limit
            else:
                retry_after = 60  # Wait 1 minute for rate limit
            
            logger.warning(
                f"Rate limit exceeded for client {client_id}",
                extra={
                    "client_id": client_id,
                    "path": request.url.path,
                    "current_minute": current_count_minute,
                    "current_second": current_count_second,
                    "limit_minute": requests_per_minute,
                    "limit_second": requests_per_second,
                    "retry_after": retry_after
                }
            )
            
            return self.create_rate_limit_response(
                requests_per_minute, current_count_minute,
                requests_per_second, current_count_second,
                retry_after
            )
        
        # Record the request
        self.store.add_request(client_id, now)
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit-Minute"] = str(requests_per_minute)
        response.headers["X-RateLimit-Limit-Second"] = str(requests_per_second)
        response.headers["X-RateLimit-Remaining-Minute"] = str(max(0, requests_per_minute - current_count_minute - 1))
        response.headers["X-RateLimit-Remaining-Second"] = str(max(0, requests_per_second - current_count_second - 1))
        
        return response


def create_rate_limiting_middleware(
    requests_per_minute: int = 60,
    burst_requests_per_second: int = 10,
    enabled: bool = True
) -> RateLimitingMiddleware:
    """
    Create rate limiting middleware with configuration
    
    Args:
        requests_per_minute: Default requests per minute limit
        burst_requests_per_second: Burst protection limit
        enabled: Whether rate limiting is enabled
    
    Returns:
        Configured RateLimitingMiddleware instance
    """
    return RateLimitingMiddleware(
        app=None,  # Will be set by FastAPI
        default_requests_per_minute=requests_per_minute,
        burst_requests_per_second=burst_requests_per_second,
        enabled=enabled
    )