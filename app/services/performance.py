"""
Performance Monitoring Service

Provides comprehensive performance monitoring including:
- Query execution time tracking
- Cache hit/miss metrics collection
- Database operation performance monitoring
- Slow query detection and logging
- Performance alerts and thresholds
- Memory and resource usage tracking
"""

import asyncio
import logging
import time
import psutil
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Awaitable
from contextlib import asynccontextmanager
import statistics

import sys
sys.path.append("/app")
from config import config
from services.cache import get_cache_metrics

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for database query performance"""
    query_type: str
    execution_time_ms: float
    ru_consumed: Optional[float] = None
    rows_returned: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    engagement_id: Optional[str] = None


@dataclass
class RequestMetrics:
    """Metrics for HTTP request performance"""
    method: str
    path: str
    status_code: int
    execution_time_ms: float
    cache_hits: int = 0
    cache_misses: int = 0
    db_queries: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class PerformanceAlert:
    """Performance alert when thresholds are exceeded"""
    alert_type: str
    message: str
    severity: str
    timestamp: datetime
    metrics: Dict[str, Any]
    correlation_id: Optional[str] = None


@dataclass
class PerformanceStatistics:
    """Aggregated performance statistics"""
    total_requests: int = 0
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    slow_requests_count: int = 0
    total_db_queries: int = 0
    avg_query_time_ms: float = 0.0
    slow_queries_count: int = 0
    cache_hit_rate: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0


class PerformanceMonitor:
    """
    Comprehensive performance monitoring service
    
    Tracks and analyzes application performance metrics including:
    - HTTP request/response times
    - Database query performance
    - Cache efficiency
    - System resource usage
    - Performance alerts
    """
    
    def __init__(self):
        self.config = config.performance
        
        # Memory-efficient storage with reasonable limits for production
        # Reduced limits to prevent memory leaks while maintaining functionality
        self.request_metrics: deque = deque(maxlen=self._get_request_metrics_limit())
        self.query_metrics: deque = deque(maxlen=self._get_query_metrics_limit())  
        self.performance_alerts: deque = deque(maxlen=500)  # Reduced from 1000
        
        # Real-time statistics tracking with smaller windows
        self.current_requests = 0
        self.response_times: deque = deque(maxlen=500)  # Reduced from 1000
        self.query_times: deque = deque(maxlen=1000)     # Reduced from 5000
        
        # Alert tracking
        self.slow_request_window = deque(maxlen=self.config.alert_slow_request_count_threshold)
        self.last_alert_time = defaultdict(lambda: datetime.min)
        
        # Background monitoring and cleanup
        self._monitoring_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event: Optional[asyncio.Event] = None  # Lazy initialization
        self._last_cleanup_time = datetime.utcnow()
        
        # Memory management settings
        self._cleanup_interval_seconds = 300  # 5 minutes
        self._metrics_retention_hours = 1     # Keep metrics for 1 hour max
        
        logger.info(
            "Performance monitor initialized",
            extra={
                "slow_request_threshold_ms": self.config.slow_request_threshold_ms,
                "slow_query_threshold_ms": self.config.slow_query_threshold_ms,
                "enable_alerts": self.config.enable_performance_alerts,
                "request_metrics_limit": self.request_metrics.maxlen,
                "query_metrics_limit": self.query_metrics.maxlen,
                "cleanup_interval_seconds": self._cleanup_interval_seconds,
                "metrics_retention_hours": self._metrics_retention_hours
            }
        )
    
    def _get_request_metrics_limit(self) -> int:
        """Get memory-efficient limit for request metrics based on environment"""
        import os
        
        # Use smaller limits in production to prevent memory leaks
        is_production = (
            os.getenv('NODE_ENV') == 'production' or 
            os.getenv('ENVIRONMENT', '').lower() == 'production'
        )
        
        if is_production:
            return 2000  # Reduced from 10000 for production
        else:
            return 5000  # Moderate limit for development
    
    def _get_query_metrics_limit(self) -> int:
        """Get memory-efficient limit for query metrics based on environment"""
        import os
        
        # Use smaller limits in production to prevent memory leaks
        is_production = (
            os.getenv('NODE_ENV') == 'production' or 
            os.getenv('ENVIRONMENT', '').lower() == 'production'
        )
        
        if is_production:
            return 5000  # Reduced from 50000 for production
        else:
            return 15000  # Moderate limit for development
    
    def _get_shutdown_event(self) -> asyncio.Event:
        """Get or create shutdown event (lazy initialization)"""
        if self._shutdown_event is None:
            self._shutdown_event = asyncio.Event()
        return self._shutdown_event
    
    async def start_monitoring(self) -> None:
        """Start background monitoring and cleanup tasks"""
        if self._monitoring_task is None:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Started performance monitoring background task")
        
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Started performance cleanup background task")
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring and cleanup tasks"""
        tasks_to_stop = []
        
        if self._monitoring_task:
            tasks_to_stop.append(self._monitoring_task)
        
        if self._cleanup_task:
            tasks_to_stop.append(self._cleanup_task)
        
        if tasks_to_stop:
            shutdown_event = self._get_shutdown_event()
            shutdown_event.set()
            
            try:
                await asyncio.wait_for(asyncio.gather(*tasks_to_stop, return_exceptions=True), timeout=5.0)
            except asyncio.TimeoutError:
                for task in tasks_to_stop:
                    if not task.done():
                        task.cancel()
            
            self._monitoring_task = None
            self._cleanup_task = None
            self._shutdown_event = None  # Clean up event
            logger.info("Stopped performance monitoring and cleanup background tasks")
    
    async def _monitoring_loop(self) -> None:
        """Background monitoring loop"""
        shutdown_event = self._get_shutdown_event()
        while not shutdown_event.is_set():
            try:
                # Collect system metrics if enabled
                if self.config.enable_memory_monitoring:
                    await self._collect_system_metrics()
                
                # Check for performance alerts
                if self.config.enable_performance_alerts:
                    await self._check_performance_alerts()
                
                # Log cache metrics if enabled
                if self.config.enable_cache_metrics:
                    await self._log_cache_metrics()
                
                # Wait for next monitoring interval
                await asyncio.wait_for(
                    shutdown_event.wait(),
                    timeout=self.config.cache_metrics_interval_seconds
                )
                
            except asyncio.TimeoutError:
                # Normal timeout, continue monitoring
                continue
            except Exception as e:
                logger.error(
                    f"Error in performance monitoring loop: {e}",
                    extra={"error": str(e)}
                )
                await asyncio.sleep(30)  # Wait before retrying
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop to prevent memory leaks"""
        shutdown_event = self._get_shutdown_event()
        while not shutdown_event.is_set():
            try:
                # Perform cleanup at regular intervals
                await asyncio.wait_for(
                    shutdown_event.wait(),
                    timeout=self._cleanup_interval_seconds
                )
                
            except asyncio.TimeoutError:
                # Normal timeout, perform cleanup
                await self._cleanup_old_metrics()
                continue
            except Exception as e:
                logger.error(
                    f"Error in performance cleanup loop: {e}",
                    extra={"error": str(e)}
                )
                await asyncio.sleep(60)  # Wait longer before retrying cleanup
    
    async def _cleanup_old_metrics(self) -> None:
        """Clean up old metrics to prevent memory leaks"""
        try:
            current_time = datetime.utcnow()
            cutoff_time = current_time - timedelta(hours=self._metrics_retention_hours)
            
            # Count metrics before cleanup
            initial_request_count = len(self.request_metrics)
            initial_query_count = len(self.query_metrics)
            initial_alert_count = len(self.performance_alerts)
            
            # Clean up old request metrics
            # Convert deque to list for filtering, then create new deque
            filtered_requests = [
                metric for metric in self.request_metrics
                if metric.timestamp >= cutoff_time
            ]
            self.request_metrics.clear()
            self.request_metrics.extend(filtered_requests)
            
            # Clean up old query metrics
            filtered_queries = [
                metric for metric in self.query_metrics
                if metric.timestamp >= cutoff_time
            ]
            self.query_metrics.clear()
            self.query_metrics.extend(filtered_queries)
            
            # Clean up old alerts
            filtered_alerts = [
                alert for alert in self.performance_alerts
                if alert.timestamp >= cutoff_time
            ]
            self.performance_alerts.clear()
            self.performance_alerts.extend(filtered_alerts)
            
            # Clean up slow request window (keep only recent timestamps)
            slow_window_cutoff = current_time - timedelta(minutes=self.config.alert_time_window_minutes * 2)
            recent_slow_requests = [
                timestamp for timestamp in self.slow_request_window
                if timestamp >= slow_window_cutoff
            ]
            self.slow_request_window.clear()
            self.slow_request_window.extend(recent_slow_requests)
            
            # Update cleanup timestamp
            self._last_cleanup_time = current_time
            
            # Log cleanup results
            requests_cleaned = initial_request_count - len(self.request_metrics)
            queries_cleaned = initial_query_count - len(self.query_metrics)
            alerts_cleaned = initial_alert_count - len(self.performance_alerts)
            
            if requests_cleaned > 0 or queries_cleaned > 0 or alerts_cleaned > 0:
                logger.info(
                    "Performance metrics cleanup completed",
                    extra={
                        "requests_cleaned": requests_cleaned,
                        "queries_cleaned": queries_cleaned,
                        "alerts_cleaned": alerts_cleaned,
                        "remaining_requests": len(self.request_metrics),
                        "remaining_queries": len(self.query_metrics),
                        "remaining_alerts": len(self.performance_alerts),
                        "retention_hours": self._metrics_retention_hours
                    }
                )
            
        except Exception as e:
            logger.error(
                f"Failed to cleanup old metrics: {e}",
                extra={"error": str(e)}
            )
    
    async def _collect_system_metrics(self) -> None:
        """Collect system resource metrics"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()
            
            # Log system metrics
            logger.debug(
                "System metrics collected",
                extra={
                    "memory_rss_mb": round(memory_info.rss / (1024 * 1024), 2),
                    "memory_vms_mb": round(memory_info.vms / (1024 * 1024), 2),
                    "cpu_percent": cpu_percent,
                    "active_requests": self.current_requests
                }
            )
            
        except Exception as e:
            logger.warning(f"Failed to collect system metrics: {e}")
    
    async def _check_performance_alerts(self) -> None:
        """Check for performance threshold violations and generate alerts"""
        try:
            # Check for slow request patterns
            recent_slow_requests = sum(
                1 for timestamp in self.slow_request_window
                if datetime.utcnow() - timestamp < timedelta(minutes=self.config.alert_time_window_minutes)
            )
            
            if recent_slow_requests >= self.config.alert_slow_request_count_threshold:
                await self._generate_alert(
                    "slow_requests",
                    f"High number of slow requests: {recent_slow_requests} in last {self.config.alert_time_window_minutes} minutes",
                    "warning",
                    {"slow_request_count": recent_slow_requests, "threshold": self.config.alert_slow_request_count_threshold}
                )
            
            # Check cache hit rate if enabled
            if self.config.enable_cache_metrics:
                cache_metrics = get_cache_metrics()
                for cache_name, metrics in cache_metrics.items():
                    hit_rate = metrics.get("hit_rate_percent", 0)
                    if hit_rate < 50:  # Low hit rate threshold
                        await self._generate_alert(
                            "low_cache_hit_rate",
                            f"Low cache hit rate for {cache_name}: {hit_rate}%",
                            "warning",
                            {"cache_name": cache_name, "hit_rate": hit_rate}
                        )
            
        except Exception as e:
            logger.warning(f"Failed to check performance alerts: {e}")
    
    async def _log_cache_metrics(self) -> None:
        """Log cache performance metrics"""
        try:
            cache_metrics = get_cache_metrics()
            if cache_metrics:
                logger.info(
                    "Cache performance metrics",
                    extra={"cache_metrics": cache_metrics}
                )
        except Exception as e:
            logger.warning(f"Failed to log cache metrics: {e}")
    
    async def _generate_alert(
        self,
        alert_type: str,
        message: str,
        severity: str,
        metrics: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> None:
        """Generate and store performance alert"""
        # Throttle alerts to prevent spam
        last_alert = self.last_alert_time[alert_type]
        if datetime.utcnow() - last_alert < timedelta(minutes=5):
            return
        
        alert = PerformanceAlert(
            alert_type=alert_type,
            message=message,
            severity=severity,
            timestamp=datetime.utcnow(),
            metrics=metrics,
            correlation_id=correlation_id
        )
        
        self.performance_alerts.append(alert)
        self.last_alert_time[alert_type] = datetime.utcnow()
        
        # Log alert
        logger.warning(
            f"Performance alert: {message}",
            extra={
                "alert_type": alert_type,
                "severity": severity,
                "metrics": metrics,
                "correlation_id": correlation_id
            }
        )
    
    def record_request_metrics(self, metrics: RequestMetrics) -> None:
        """Record HTTP request performance metrics"""
        self.request_metrics.append(metrics)
        self.response_times.append(metrics.execution_time_ms)
        
        # Track slow requests for alerting
        if metrics.execution_time_ms > self.config.slow_request_threshold_ms:
            self.slow_request_window.append(datetime.utcnow())
        
        # Log slow requests
        if (self.config.enable_request_timing and 
            metrics.execution_time_ms > self.config.slow_request_threshold_ms):
            logger.warning(
                f"Slow request detected",
                extra={
                    "method": metrics.method,
                    "path": metrics.path,
                    "execution_time_ms": metrics.execution_time_ms,
                    "status_code": metrics.status_code,
                    "correlation_id": metrics.correlation_id,
                    "user_id": metrics.user_id
                }
            )
    
    def record_query_metrics(self, metrics: QueryMetrics) -> None:
        """Record database query performance metrics"""
        self.query_metrics.append(metrics)
        self.query_times.append(metrics.execution_time_ms)
        
        # Log slow queries
        if (self.config.enable_query_timing and 
            metrics.execution_time_ms > self.config.slow_query_threshold_ms):
            logger.warning(
                f"Slow query detected",
                extra={
                    "query_type": metrics.query_type,
                    "execution_time_ms": metrics.execution_time_ms,
                    "ru_consumed": metrics.ru_consumed,
                    "rows_returned": metrics.rows_returned,
                    "correlation_id": metrics.correlation_id,
                    "user_id": metrics.user_id,
                    "engagement_id": metrics.engagement_id
                }
            )
    
    @asynccontextmanager
    async def track_request(
        self,
        method: str,
        path: str,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """Context manager to track request performance"""
        start_time = time.time()
        self.current_requests += 1
        
        cache_hits_start = 0
        cache_misses_start = 0
        db_queries_start = len(self.query_metrics)
        
        # Get initial cache metrics if enabled
        if self.config.enable_cache_metrics:
            cache_metrics = get_cache_metrics()
            for metrics in cache_metrics.values():
                cache_hits_start += metrics.get("hits", 0)
                cache_misses_start += metrics.get("misses", 0)
        
        try:
            yield
        finally:
            self.current_requests -= 1
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Calculate cache metrics delta
            cache_hits_delta = 0
            cache_misses_delta = 0
            if self.config.enable_cache_metrics:
                cache_metrics = get_cache_metrics()
                cache_hits_end = sum(m.get("hits", 0) for m in cache_metrics.values())
                cache_misses_end = sum(m.get("misses", 0) for m in cache_metrics.values())
                cache_hits_delta = cache_hits_end - cache_hits_start
                cache_misses_delta = cache_misses_end - cache_misses_start
            
            # Calculate database queries delta
            db_queries_delta = len(self.query_metrics) - db_queries_start
            
            # Create request metrics (status_code will be set by middleware)
            request_metrics = RequestMetrics(
                method=method,
                path=path,
                status_code=200,  # Default, will be updated by middleware
                execution_time_ms=execution_time_ms,
                cache_hits=cache_hits_delta,
                cache_misses=cache_misses_delta,
                db_queries=db_queries_delta,
                correlation_id=correlation_id,
                user_id=user_id
            )
            
            self.record_request_metrics(request_metrics)
    
    @asynccontextmanager
    async def track_query(
        self,
        query_type: str,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        engagement_id: Optional[str] = None
    ):
        """Context manager to track database query performance"""
        start_time = time.time()
        
        try:
            yield
        finally:
            execution_time_ms = (time.time() - start_time) * 1000
            
            query_metrics = QueryMetrics(
                query_type=query_type,
                execution_time_ms=execution_time_ms,
                correlation_id=correlation_id,
                user_id=user_id,
                engagement_id=engagement_id
            )
            
            self.record_query_metrics(query_metrics)
    
    def get_performance_statistics(self, time_window_minutes: int = 60) -> PerformanceStatistics:
        """Get aggregated performance statistics for the specified time window"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        # Filter metrics by time window
        recent_requests = [
            m for m in self.request_metrics
            if m.timestamp >= cutoff_time
        ]
        recent_queries = [
            m for m in self.query_metrics
            if m.timestamp >= cutoff_time
        ]
        
        # Calculate request statistics
        request_times = [m.execution_time_ms for m in recent_requests]
        slow_requests = [m for m in recent_requests if m.execution_time_ms > self.config.slow_request_threshold_ms]
        
        # Calculate query statistics
        query_times = [m.execution_time_ms for m in recent_queries]
        slow_queries = [m for m in recent_queries if m.execution_time_ms > self.config.slow_query_threshold_ms]
        
        # Calculate cache statistics
        total_cache_hits = sum(m.cache_hits for m in recent_requests)
        total_cache_misses = sum(m.cache_misses for m in recent_requests)
        cache_hit_rate = (
            total_cache_hits / (total_cache_hits + total_cache_misses) * 100
            if (total_cache_hits + total_cache_misses) > 0 else 0
        )
        
        # System resource usage
        memory_usage_mb = 0.0
        cpu_usage_percent = 0.0
        try:
            process = psutil.Process()
            memory_usage_mb = process.memory_info().rss / (1024 * 1024)
            cpu_usage_percent = process.cpu_percent()
        except Exception:
            pass
        
        return PerformanceStatistics(
            total_requests=len(recent_requests),
            avg_response_time_ms=statistics.mean(request_times) if request_times else 0.0,
            p95_response_time_ms=statistics.quantiles(request_times, n=20)[18] if len(request_times) >= 20 else 0.0,
            p99_response_time_ms=statistics.quantiles(request_times, n=100)[98] if len(request_times) >= 100 else 0.0,
            slow_requests_count=len(slow_requests),
            total_db_queries=len(recent_queries),
            avg_query_time_ms=statistics.mean(query_times) if query_times else 0.0,
            slow_queries_count=len(slow_queries),
            cache_hit_rate=cache_hit_rate,
            memory_usage_mb=memory_usage_mb,
            cpu_usage_percent=cpu_usage_percent
        )
    
    def get_recent_alerts(self, limit: int = 50) -> List[PerformanceAlert]:
        """Get recent performance alerts"""
        return list(self.performance_alerts)[-limit:]
    
    def get_slow_requests(self, limit: int = 100) -> List[RequestMetrics]:
        """Get recent slow requests"""
        slow_requests = [
            m for m in self.request_metrics
            if m.execution_time_ms > self.config.slow_request_threshold_ms
        ]
        return sorted(slow_requests, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def get_slow_queries(self, limit: int = 100) -> List[QueryMetrics]:
        """Get recent slow queries"""
        slow_queries = [
            m for m in self.query_metrics
            if m.execution_time_ms > self.config.slow_query_threshold_ms
        ]
        return sorted(slow_queries, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def clear_metrics(self) -> None:
        """Clear all stored metrics and force garbage collection"""
        # Count metrics before clearing
        request_count = len(self.request_metrics)
        query_count = len(self.query_metrics)
        alert_count = len(self.performance_alerts)
        
        # Clear all collections
        self.request_metrics.clear()
        self.query_metrics.clear()
        self.performance_alerts.clear()
        self.response_times.clear()
        self.query_times.clear()
        self.slow_request_window.clear()
        
        # Clear alert tracking
        self.last_alert_time.clear()
        
        # Force garbage collection to free memory immediately
        import gc
        gc.collect()
        
        logger.info(
            "Cleared all performance metrics",
            extra={
                "cleared_requests": request_count,
                "cleared_queries": query_count,
                "cleared_alerts": alert_count
            }
        )
    
    async def cleanup_old_metrics_now(self) -> None:
        """Manually trigger cleanup of old metrics (useful for testing and maintenance)"""
        await self._cleanup_old_metrics()
    
    def get_memory_usage_info(self) -> Dict[str, Any]:
        """Get current memory usage information for monitoring"""
        try:
            import sys
            
            # Calculate approximate memory usage of metrics collections
            request_metrics_size = sys.getsizeof(self.request_metrics)
            for metric in self.request_metrics:
                request_metrics_size += sys.getsizeof(metric)
            
            query_metrics_size = sys.getsizeof(self.query_metrics)
            for metric in self.query_metrics:
                query_metrics_size += sys.getsizeof(metric)
            
            return {
                "request_metrics_count": len(self.request_metrics),
                "query_metrics_count": len(self.query_metrics),
                "alert_count": len(self.performance_alerts),
                "request_metrics_size_bytes": request_metrics_size,
                "query_metrics_size_bytes": query_metrics_size,
                "request_metrics_limit": self.request_metrics.maxlen,
                "query_metrics_limit": self.query_metrics.maxlen,
                "last_cleanup_time": self._last_cleanup_time.isoformat(),
                "cleanup_interval_seconds": self._cleanup_interval_seconds,
                "retention_hours": self._metrics_retention_hours
            }
            
        except Exception as e:
            logger.warning(f"Failed to get memory usage info: {e}")
            return {
                "request_metrics_count": len(self.request_metrics),
                "query_metrics_count": len(self.query_metrics),
                "alert_count": len(self.performance_alerts),
                "error": str(e)
            }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# Convenience functions
async def start_performance_monitoring() -> None:
    """Start performance monitoring"""
    await performance_monitor.start_monitoring()


async def stop_performance_monitoring() -> None:
    """Stop performance monitoring"""
    await performance_monitor.stop_monitoring()


def track_request(method: str, path: str, correlation_id: Optional[str] = None, user_id: Optional[str] = None):
    """Track HTTP request performance"""
    return performance_monitor.track_request(method, path, correlation_id, user_id)


def track_query(query_type: str, correlation_id: Optional[str] = None, user_id: Optional[str] = None, engagement_id: Optional[str] = None):
    """Track database query performance"""
    return performance_monitor.track_query(query_type, correlation_id, user_id, engagement_id)


def get_performance_statistics(time_window_minutes: int = 60) -> PerformanceStatistics:
    """Get performance statistics"""
    return performance_monitor.get_performance_statistics(time_window_minutes)


def get_recent_alerts(limit: int = 50) -> List[PerformanceAlert]:
    """Get recent performance alerts"""
    return performance_monitor.get_recent_alerts(limit)


def record_query_metrics(metrics: QueryMetrics) -> None:
    """Record database query metrics"""
    performance_monitor.record_query_metrics(metrics)