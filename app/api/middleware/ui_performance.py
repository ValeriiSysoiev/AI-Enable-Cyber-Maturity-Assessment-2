"""
UI Performance Monitoring Middleware
Tracks and optimizes performance for grid operations to maintain p95 < 2s
"""
import time
import logging
from typing import Dict, List, Optional, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio
import psutil
import os

logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """Performance metrics collection and analysis"""
    
    def __init__(self, window_minutes: int = 10):
        self.window_minutes = window_minutes
        self.response_times = deque()
        self.grid_operations = deque()
        self.memory_usage = deque()
        self.cpu_usage = deque()
        self.endpoint_metrics = defaultdict(lambda: deque())
        self.alerts_sent = set()
        
        # Performance thresholds
        self.p95_threshold_ms = float(os.getenv('PERF_GRID_OPERATIONS_P95_THRESHOLD_MS', 2000))
        self.memory_threshold_mb = float(os.getenv('PERF_MEMORY_THRESHOLD_MB', 512))
        self.cpu_threshold_percent = float(os.getenv('PERF_CPU_THRESHOLD_PERCENT', 80))
        
    def add_response_time(self, endpoint: str, duration_ms: float, request_size: int = 0):
        """Add response time measurement"""
        now = datetime.utcnow()
        self.response_times.append({
            'timestamp': now,
            'endpoint': endpoint,
            'duration_ms': duration_ms,
            'request_size': request_size
        })
        
        # Add to endpoint-specific metrics
        self.endpoint_metrics[endpoint].append({
            'timestamp': now,
            'duration_ms': duration_ms,
            'request_size': request_size
        })
        
        # Clean old data
        self._cleanup_old_data()
        
        # Check for performance issues
        self._check_performance_alerts(endpoint, duration_ms)
    
    def add_grid_operation(self, operation_type: str, duration_ms: float, row_count: int = 0):
        """Add grid operation measurement"""
        now = datetime.utcnow()
        self.grid_operations.append({
            'timestamp': now,
            'operation_type': operation_type,
            'duration_ms': duration_ms,
            'row_count': row_count
        })
        
        # Clean old data
        self._cleanup_old_data()
        
        # Check grid-specific alerts
        if duration_ms > self.p95_threshold_ms:
            logger.warning(
                f"Grid operation {operation_type} exceeded p95 threshold",
                extra={
                    'operation_type': operation_type,
                    'duration_ms': duration_ms,
                    'threshold_ms': self.p95_threshold_ms,
                    'row_count': row_count
                }
            )
    
    def add_system_metrics(self):
        """Add current system metrics"""
        now = datetime.utcnow()
        
        try:
            # Memory usage
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.memory_usage.append({
                'timestamp': now,
                'memory_mb': memory_mb
            })
            
            # CPU usage
            cpu_percent = process.cpu_percent()
            self.cpu_usage.append({
                'timestamp': now,
                'cpu_percent': cpu_percent
            })
            
            # Clean old data
            self._cleanup_old_data()
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    def _cleanup_old_data(self):
        """Remove data older than window"""
        cutoff = datetime.utcnow() - timedelta(minutes=self.window_minutes)
        
        # Clean response times
        while self.response_times and self.response_times[0]['timestamp'] < cutoff:
            self.response_times.popleft()
        
        # Clean grid operations
        while self.grid_operations and self.grid_operations[0]['timestamp'] < cutoff:
            self.grid_operations.popleft()
        
        # Clean memory usage
        while self.memory_usage and self.memory_usage[0]['timestamp'] < cutoff:
            self.memory_usage.popleft()
        
        # Clean CPU usage
        while self.cpu_usage and self.cpu_usage[0]['timestamp'] < cutoff:
            self.cpu_usage.popleft()
        
        # Clean endpoint metrics
        for endpoint in self.endpoint_metrics:
            while (self.endpoint_metrics[endpoint] and 
                   self.endpoint_metrics[endpoint][0]['timestamp'] < cutoff):
                self.endpoint_metrics[endpoint].popleft()
    
    def _check_performance_alerts(self, endpoint: str, duration_ms: float):
        """Check for performance alert conditions"""
        alert_key = f"{endpoint}_{int(time.time() // 300)}"  # 5-minute buckets
        
        if alert_key in self.alerts_sent:
            return
        
        # Check if this endpoint is consistently slow
        if endpoint in self.endpoint_metrics:
            recent_metrics = list(self.endpoint_metrics[endpoint])
            if len(recent_metrics) >= 5:  # Need at least 5 samples
                recent_times = [m['duration_ms'] for m in recent_metrics[-5:]]
                avg_time = sum(recent_times) / len(recent_times)
                
                if avg_time > self.p95_threshold_ms * 0.8:  # 80% of threshold
                    logger.warning(
                        f"Endpoint {endpoint} showing degraded performance",
                        extra={
                            'endpoint': endpoint,
                            'avg_duration_ms': avg_time,
                            'threshold_ms': self.p95_threshold_ms,
                            'sample_count': len(recent_times)
                        }
                    )
                    self.alerts_sent.add(alert_key)
    
    def get_p95_response_time(self, endpoint: Optional[str] = None) -> float:
        """Calculate P95 response time"""
        if endpoint:
            times = [m['duration_ms'] for m in self.endpoint_metrics.get(endpoint, [])]
        else:
            times = [m['duration_ms'] for m in self.response_times]
        
        if not times:
            return 0.0
        
        times.sort()
        p95_index = int(len(times) * 0.95)
        return times[p95_index] if p95_index < len(times) else times[-1]
    
    def get_grid_operation_stats(self) -> Dict:
        """Get grid operation performance statistics"""
        if not self.grid_operations:
            return {
                'count': 0,
                'avg_duration_ms': 0,
                'p95_duration_ms': 0,
                'operations_over_threshold': 0
            }
        
        durations = [op['duration_ms'] for op in self.grid_operations]
        durations.sort()
        
        p95_index = int(len(durations) * 0.95)
        p95_duration = durations[p95_index] if p95_index < len(durations) else durations[-1]
        
        operations_over_threshold = sum(1 for d in durations if d > self.p95_threshold_ms)
        
        return {
            'count': len(self.grid_operations),
            'avg_duration_ms': sum(durations) / len(durations),
            'p95_duration_ms': p95_duration,
            'operations_over_threshold': operations_over_threshold,
            'threshold_ms': self.p95_threshold_ms
        }
    
    def get_system_health(self) -> Dict:
        """Get current system health metrics"""
        health = {
            'status': 'healthy',
            'memory_mb': 0,
            'cpu_percent': 0,
            'issues': []
        }
        
        if self.memory_usage:
            latest_memory = self.memory_usage[-1]['memory_mb']
            health['memory_mb'] = latest_memory
            
            if latest_memory > self.memory_threshold_mb:
                health['status'] = 'degraded'
                health['issues'].append(f"High memory usage: {latest_memory:.1f}MB")
        
        if self.cpu_usage:
            latest_cpu = self.cpu_usage[-1]['cpu_percent']
            health['cpu_percent'] = latest_cpu
            
            if latest_cpu > self.cpu_threshold_percent:
                health['status'] = 'degraded'
                health['issues'].append(f"High CPU usage: {latest_cpu:.1f}%")
        
        return health


# Global metrics instance
performance_metrics = PerformanceMetrics()


class UIPerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track UI performance and grid operations"""
    
    def __init__(self, app, enable_monitoring: bool = True):
        super().__init__(app)
        self.enable_monitoring = enable_monitoring
        self.grid_endpoints = {
            '/api/roadmap/resource-profile/calculate',
            '/api/roadmap/resource-profile/gantt',
            '/api/roadmap/resource-profile/wave-overlay',
            '/api/roadmap/resource-profile/export',
            '/api/assessments',
            '/api/csf/grid-data'
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enable_monitoring:
            return await call_next(request)
        
        start_time = time.time()
        
        # Check if this is a grid operation
        is_grid_operation = any(endpoint in str(request.url) for endpoint in self.grid_endpoints)
        
        # Get request size for performance correlation
        request_size = int(request.headers.get('content-length', 0))
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Record metrics
            endpoint = f"{request.method} {request.url.path}"
            performance_metrics.add_response_time(endpoint, duration_ms, request_size)
            
            # Record grid-specific metrics
            if is_grid_operation:
                operation_type = self._get_operation_type(request)
                row_count = self._estimate_row_count(request, response)
                performance_metrics.add_grid_operation(operation_type, duration_ms, row_count)
            
            # Add performance headers
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            if is_grid_operation:
                response.headers["X-Grid-Performance"] = f"duration={duration_ms:.2f}ms"
                
                # Add warning header if over threshold
                if duration_ms > performance_metrics.p95_threshold_ms:
                    response.headers["X-Performance-Warning"] = "exceeded-threshold"
            
            return response
            
        except Exception as e:
            # Record error metrics
            duration_ms = (time.time() - start_time) * 1000
            endpoint = f"{request.method} {request.url.path}"
            performance_metrics.add_response_time(endpoint, duration_ms, request_size)
            
            logger.error(
                f"Request failed after {duration_ms:.2f}ms",
                extra={
                    'endpoint': endpoint,
                    'duration_ms': duration_ms,
                    'error': str(e)
                }
            )
            raise
    
    def _get_operation_type(self, request: Request) -> str:
        """Determine the type of grid operation"""
        path = request.url.path
        method = request.method
        
        if 'calculate' in path:
            return 'wave_calculation'
        elif 'gantt' in path:
            return 'gantt_generation'
        elif 'wave-overlay' in path:
            return 'wave_overlay'
        elif 'export' in path:
            return 'csv_export'
        elif 'assessments' in path:
            if method == 'GET':
                return 'assessment_load'
            else:
                return 'assessment_update'
        elif 'grid-data' in path:
            return 'grid_data_load'
        else:
            return 'unknown_grid_operation'
    
    def _estimate_row_count(self, request: Request, response: Response) -> int:
        """Estimate the number of rows processed"""
        try:
            # Try to get from response headers if available
            if 'X-Row-Count' in response.headers:
                return int(response.headers['X-Row-Count'])
            
            # Estimate based on response size
            content_length = response.headers.get('content-length')
            if content_length:
                # Rough estimate: ~100 bytes per row for JSON
                return max(1, int(content_length) // 100)
            
            return 0
        except (ValueError, TypeError):
            return 0


async def collect_system_metrics():
    """Background task to collect system metrics"""
    while True:
        try:
            performance_metrics.add_system_metrics()
            await asyncio.sleep(30)  # Collect every 30 seconds
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            await asyncio.sleep(60)  # Wait longer on error


def get_performance_summary() -> Dict:
    """Get comprehensive performance summary"""
    return {
        'response_times': {
            'overall_p95_ms': performance_metrics.get_p95_response_time(),
            'grid_operations': performance_metrics.get_grid_operation_stats()
        },
        'system_health': performance_metrics.get_system_health(),
        'thresholds': {
            'p95_threshold_ms': performance_metrics.p95_threshold_ms,
            'memory_threshold_mb': performance_metrics.memory_threshold_mb,
            'cpu_threshold_percent': performance_metrics.cpu_threshold_percent
        },
        'monitoring': {
            'window_minutes': performance_metrics.window_minutes,
            'total_requests': len(performance_metrics.response_times),
            'grid_operations_count': len(performance_metrics.grid_operations)
        }
    }


def check_docs_only_changes(files_changed: List[str]) -> bool:
    """Check if changes are documentation-only to skip performance checks"""
    if not files_changed:
        return False
    
    docs_patterns = {'.md', '.txt', '.rst', '/docs/', '/README', 'CHANGELOG', 'LICENSE'}
    
    for file_path in files_changed:
        # Check if file has documentation extension or is in docs directory
        is_docs = any(pattern in file_path.lower() for pattern in docs_patterns)
        if not is_docs:
            return False
    
    return True


def should_skip_performance_checks() -> bool:
    """Determine if performance checks should be skipped"""
    # Check environment variable
    if os.getenv('SKIP_PERFORMANCE_CHECKS', '').lower() == 'true':
        return True
    
    # Check if this is a docs-only change (would need to be passed from CI)
    docs_only = os.getenv('DOCS_ONLY_CHANGE', '').lower() == 'true'
    if docs_only:
        logger.info("Skipping performance checks for docs-only changes")
        return True
    
    return False