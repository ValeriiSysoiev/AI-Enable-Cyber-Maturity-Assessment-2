"""
Structured logging utilities for RAG operations and general application use.
Provides correlation ID tracking and structured log formatting.
"""
import logging
import json
import uuid
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from functools import wraps
from contextlib import contextmanager

from ..config import config


# Configure JSON formatter for structured logging
class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'correlation_id'):
            log_entry["correlation_id"] = record.correlation_id
        
        if hasattr(record, 'engagement_id'):
            log_entry["engagement_id"] = record.engagement_id
            
        if hasattr(record, 'user_email'):
            log_entry["user_email"] = record.user_email
        
        # Add any other extra fields
        extra_fields = getattr(record, '__dict__', {})
        for key, value in extra_fields.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                          'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
                          'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'message']:
                log_entry[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


def setup_structured_logging():
    """Setup structured logging for the application"""
    root_logger = logging.getLogger()
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler with JSON formatter
    handler = logging.StreamHandler()
    
    if config.logging.format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, config.logging.level.upper()))


class CorrelatedLogger:
    """Logger with automatic correlation ID injection"""
    
    def __init__(self, logger_name: str, correlation_id: Optional[str] = None):
        self.logger = logging.getLogger(logger_name)
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs):
        """Set context fields to be included in all log messages"""
        self.context.update(kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method with context injection"""
        extra = {
            "correlation_id": self.correlation_id,
            **self.context,
            **kwargs
        }
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)


def get_correlated_logger(name: str, correlation_id: Optional[str] = None) -> CorrelatedLogger:
    """Get a correlated logger instance"""
    return CorrelatedLogger(name, correlation_id)


@contextmanager
def log_operation(
    logger: CorrelatedLogger,
    operation: str,
    level: int = logging.INFO,
    **context
):
    """Context manager for logging operations with timing"""
    start_time = time.time()
    
    logger.info(
        f"Starting {operation}",
        operation=operation,
        operation_phase="start",
        **context
    )
    
    try:
        yield
        duration = time.time() - start_time
        logger.log(
            level,
            f"Completed {operation}",
            operation=operation,
            operation_phase="complete",
            duration_seconds=round(duration, 3),
            success=True,
            **context
        )
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Failed {operation}",
            operation=operation,
            operation_phase="error",
            duration_seconds=round(duration, 3),
            success=False,
            error=str(e),
            error_type=type(e).__name__,
            **context
        )
        raise


def log_rag_metrics(
    logger: CorrelatedLogger,
    operation: str,
    duration_seconds: float,
    success: bool,
    engagement_id: str,
    **metrics
):
    """Log RAG-specific metrics"""
    logger.info(
        f"RAG {operation} metrics",
        metric_type="rag_operation",
        operation=operation,
        duration_seconds=round(duration_seconds, 3),
        success=success,
        engagement_id=engagement_id,
        **metrics
    )


def log_error_with_context(
    logger: CorrelatedLogger,
    error: Exception,
    operation: str,
    **context
):
    """Log an error with full context"""
    logger.error(
        f"Error in {operation}: {str(error)}",
        operation=operation,
        error=str(error),
        error_type=type(error).__name__,
        **context
    )


def log_security_event(
    logger: CorrelatedLogger,
    event_type: str,
    user_email: str,
    engagement_id: str,
    success: bool,
    **details
):
    """Log security-related events"""
    logger.info(
        f"Security event: {event_type}",
        event_type="security",
        security_event_type=event_type,
        user_email=user_email,
        engagement_id=engagement_id,
        success=success,
        **details
    )


def measure_performance(operation_name: str):
    """Decorator to measure and log function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_correlated_logger(func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    f"Performance: {operation_name}",
                    metric_type="performance",
                    operation=operation_name,
                    function=func.__name__,
                    duration_seconds=round(duration, 3),
                    success=True
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error(
                    f"Performance: {operation_name} failed",
                    metric_type="performance",
                    operation=operation_name,
                    function=func.__name__,
                    duration_seconds=round(duration, 3),
                    success=False,
                    error=str(e),
                    error_type=type(e).__name__
                )
                
                raise
        
        return wrapper
    return decorator


class RAGMetricsLogger:
    """Specialized logger for RAG operations"""
    
    def __init__(self, correlation_id: str):
        self.logger = get_correlated_logger("rag.metrics", correlation_id)
    
    def log_embedding_operation(
        self,
        document_id: str,
        engagement_id: str,
        chunks_processed: int,
        total_chunks: int,
        duration_seconds: float,
        success: bool,
        model: str,
        error: Optional[str] = None
    ):
        """Log embedding operation metrics"""
        self.logger.info(
            "Embedding operation completed",
            metric_type="embedding",
            document_id=document_id,
            engagement_id=engagement_id,
            chunks_processed=chunks_processed,
            total_chunks=total_chunks,
            duration_seconds=round(duration_seconds, 3),
            success=success,
            model=model,
            error=error,
            success_rate=chunks_processed / total_chunks if total_chunks > 0 else 0
        )
    
    def log_search_operation(
        self,
        engagement_id: str,
        query_length: int,
        results_found: int,
        top_k: int,
        duration_seconds: float,
        success: bool,
        similarity_threshold: float,
        error: Optional[str] = None
    ):
        """Log search operation metrics"""
        self.logger.info(
            "Search operation completed",
            metric_type="search",
            engagement_id=engagement_id,
            query_length=query_length,
            results_found=results_found,
            top_k=top_k,
            duration_seconds=round(duration_seconds, 3),
            success=success,
            similarity_threshold=similarity_threshold,
            hit_rate=results_found / top_k if top_k > 0 else 0,
            error=error
        )
    
    def log_ingestion_operation(
        self,
        document_id: str,
        engagement_id: str,
        chunks_stored: int,
        total_chunks: int,
        duration_seconds: float,
        success: bool,
        storage_backend: str,
        error: Optional[str] = None
    ):
        """Log ingestion operation metrics"""
        self.logger.info(
            "Ingestion operation completed",
            metric_type="ingestion",
            document_id=document_id,
            engagement_id=engagement_id,
            chunks_stored=chunks_stored,
            total_chunks=total_chunks,
            duration_seconds=round(duration_seconds, 3),
            success=success,
            storage_backend=storage_backend,
            storage_success_rate=chunks_stored / total_chunks if total_chunks > 0 else 0,
            error=error
        )


# Global metrics logger instance
_metrics_logger = None

def get_rag_metrics_logger(correlation_id: str) -> RAGMetricsLogger:
    """Get a RAG metrics logger instance"""
    return RAGMetricsLogger(correlation_id)


# Error handling utilities
class RAGError(Exception):
    """Base exception for RAG operations"""
    def __init__(self, message: str, operation: str, correlation_id: str, **context):
        super().__init__(message)
        self.operation = operation
        self.correlation_id = correlation_id
        self.context = context


class EmbeddingError(RAGError):
    """Exception for embedding generation errors"""
    pass


class SearchError(RAGError):
    """Exception for search operation errors"""
    pass


class IngestionError(RAGError):
    """Exception for document ingestion errors"""
    pass


def handle_rag_error(
    logger: CorrelatedLogger,
    error: Exception,
    operation: str,
    fallback_value=None,
    **context
):
    """Handle RAG errors with logging and optional fallback"""
    if isinstance(error, RAGError):
        logger.error(
            f"RAG {operation} failed",
            operation=operation,
            error=str(error),
            error_type=type(error).__name__,
            **error.context,
            **context
        )
    else:
        logger.error(
            f"Unexpected error in RAG {operation}",
            operation=operation,
            error=str(error),
            error_type=type(error).__name__,
            **context
        )
    
    return fallback_value