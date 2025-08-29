"""
Centralized database error handling module with retry logic and proper error categorization.
Provides comprehensive handling for Cosmos DB and other database errors.
"""
import asyncio
import logging
from typing import Any, Callable, Optional, TypeVar, Dict
from functools import wraps
from fastapi import HTTPException
from azure.cosmos.exceptions import (
    CosmosResourceNotFoundError,
    CosmosHttpResponseError,
    CosmosResourceExistsError,
    CosmosAccessConditionFailedError,
    CosmosBatchOperationError
)

logger = logging.getLogger(__name__)

# Type variable for generic return types
T = TypeVar('T')

# Error categories for proper handling
class DatabaseErrorCategory:
    """Categories of database errors for appropriate handling"""
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    VALIDATION = "validation"
    QUOTA_EXCEEDED = "quota_exceeded"
    TRANSIENT = "transient"
    PERMISSION = "permission"
    UNKNOWN = "unknown"


# Retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 0.5  # seconds
DEFAULT_MAX_DELAY = 10.0  # seconds
JITTER_FACTOR = 0.1  # 10% jitter


def categorize_database_error(error: Exception) -> str:
    """
    Categorize database errors for appropriate handling.
    
    Args:
        error: The exception to categorize
        
    Returns:
        Error category from DatabaseErrorCategory
    """
    if isinstance(error, CosmosResourceNotFoundError):
        return DatabaseErrorCategory.NOT_FOUND
    
    if isinstance(error, CosmosResourceExistsError):
        return DatabaseErrorCategory.CONFLICT
    
    if isinstance(error, CosmosAccessConditionFailedError):
        return DatabaseErrorCategory.CONFLICT
    
    if isinstance(error, CosmosBatchOperationError):
        return DatabaseErrorCategory.VALIDATION
    
    if isinstance(error, CosmosHttpResponseError):
        status_code = getattr(error, 'status_code', None)
        
        if status_code == 404:
            return DatabaseErrorCategory.NOT_FOUND
        elif status_code == 409:
            return DatabaseErrorCategory.CONFLICT
        elif status_code == 429:
            return DatabaseErrorCategory.RATE_LIMITED
        elif status_code == 408:
            return DatabaseErrorCategory.TIMEOUT
        elif status_code in [401, 403]:
            return DatabaseErrorCategory.PERMISSION
        elif status_code == 400:
            return DatabaseErrorCategory.VALIDATION
        elif status_code == 507:
            return DatabaseErrorCategory.QUOTA_EXCEEDED
        elif status_code in [500, 502, 503, 504]:
            return DatabaseErrorCategory.TRANSIENT
    
    # Check for connection errors
    error_message = str(error).lower()
    if any(keyword in error_message for keyword in ['connection', 'network', 'socket']):
        return DatabaseErrorCategory.CONNECTION
    
    if 'timeout' in error_message:
        return DatabaseErrorCategory.TIMEOUT
    
    return DatabaseErrorCategory.UNKNOWN


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable.
    
    Args:
        error: The exception to check
        
    Returns:
        True if the error is retryable, False otherwise
    """
    category = categorize_database_error(error)
    retryable_categories = {
        DatabaseErrorCategory.RATE_LIMITED,
        DatabaseErrorCategory.TIMEOUT,
        DatabaseErrorCategory.CONNECTION,
        DatabaseErrorCategory.TRANSIENT
    }
    return category in retryable_categories


def calculate_retry_delay(attempt: int, base_delay: float = DEFAULT_BASE_DELAY, 
                         max_delay: float = DEFAULT_MAX_DELAY) -> float:
    """
    Calculate exponential backoff delay with jitter.
    
    Args:
        attempt: Current retry attempt (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        
    Returns:
        Delay in seconds
    """
    import random
    
    # Exponential backoff
    delay = min(base_delay * (2 ** attempt), max_delay)
    
    # Add jitter to prevent thundering herd
    jitter = delay * JITTER_FACTOR * (2 * random.random() - 1)
    
    return max(0, delay + jitter)


def translate_database_error(error: Exception, context: str = "") -> HTTPException:
    """
    Translate database errors to appropriate HTTP exceptions.
    
    Args:
        error: The database error
        context: Additional context about the operation
        
    Returns:
        HTTPException with appropriate status code and message
    """
    category = categorize_database_error(error)
    
    # Log the error with context
    logger.error(
        f"Database error in {context}",
        extra={
            "error_type": type(error).__name__,
            "error_category": category,
            "error_message": str(error),
            "context": context
        },
        exc_info=True
    )
    
    # Map categories to HTTP responses
    if category == DatabaseErrorCategory.NOT_FOUND:
        return HTTPException(404, "Resource not found")
    
    elif category == DatabaseErrorCategory.CONFLICT:
        return HTTPException(409, "Resource conflict - another operation is in progress")
    
    elif category == DatabaseErrorCategory.RATE_LIMITED:
        return HTTPException(429, "Too many requests - please try again later")
    
    elif category == DatabaseErrorCategory.TIMEOUT:
        return HTTPException(504, "Database operation timed out - please try again")
    
    elif category == DatabaseErrorCategory.CONNECTION:
        return HTTPException(503, "Database connection error - service temporarily unavailable")
    
    elif category == DatabaseErrorCategory.VALIDATION:
        return HTTPException(400, "Invalid data provided")
    
    elif category == DatabaseErrorCategory.QUOTA_EXCEEDED:
        return HTTPException(507, "Storage quota exceeded")
    
    elif category == DatabaseErrorCategory.PERMISSION:
        return HTTPException(403, "Access denied - insufficient permissions")
    
    elif category == DatabaseErrorCategory.TRANSIENT:
        return HTTPException(503, "Service temporarily unavailable - please retry")
    
    else:
        # Unknown errors - don't expose internal details
        return HTTPException(500, "An unexpected error occurred")


async def retry_database_operation(
    operation: Callable[..., T],
    *args,
    max_retries: int = DEFAULT_MAX_RETRIES,
    context: str = "",
    **kwargs
) -> T:
    """
    Execute a database operation with retry logic.
    
    Args:
        operation: The async function to execute
        *args: Positional arguments for the operation
        max_retries: Maximum number of retry attempts
        context: Context for error messages
        **kwargs: Keyword arguments for the operation
        
    Returns:
        Result of the operation
        
    Raises:
        HTTPException: When operation fails after all retries
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            # Execute the operation
            return await operation(*args, **kwargs)
            
        except Exception as e:
            last_error = e
            
            # Check if error is retryable
            if not is_retryable_error(e) or attempt == max_retries:
                # Not retryable or last attempt - translate and raise
                raise translate_database_error(e, context)
            
            # Calculate retry delay
            delay = calculate_retry_delay(attempt)
            
            logger.warning(
                f"Retrying database operation after error",
                extra={
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "delay": delay,
                    "error": str(e),
                    "context": context
                }
            )
            
            # Wait before retry
            await asyncio.sleep(delay)
    
    # Should never reach here, but handle it
    if last_error:
        raise translate_database_error(last_error, context)
    raise HTTPException(500, "Unexpected error in retry logic")


def handle_database_errors(context: str = ""):
    """
    Decorator to handle database errors with proper translation.
    
    Args:
        context: Context description for error messages
        
    Usage:
        @handle_database_errors("user creation")
        async def create_user(...):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Already an HTTP exception - pass through
                raise
            except Exception as e:
                # Translate database error to HTTP exception
                raise translate_database_error(e, context or func.__name__)
        
        return wrapper
    
    return decorator


class DatabaseHealthCheck:
    """Health check utilities for database connections"""
    
    @staticmethod
    async def check_cosmos_health(client: Any, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Check Cosmos DB connection health.
        
        Args:
            client: Cosmos DB client
            timeout: Timeout in seconds
            
        Returns:
            Health status dictionary
        """
        import time
        
        start_time = time.time()
        
        try:
            # Try to list databases (lightweight operation)
            await asyncio.wait_for(
                asyncio.to_thread(lambda: list(client.list_databases())),
                timeout=timeout
            )
            
            response_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time * 1000, 2),
                "message": "Database connection is healthy"
            }
            
        except asyncio.TimeoutError:
            return {
                "status": "unhealthy",
                "response_time_ms": round(timeout * 1000, 2),
                "message": "Database health check timed out"
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            category = categorize_database_error(e)
            
            return {
                "status": "unhealthy",
                "response_time_ms": round(response_time * 1000, 2),
                "message": f"Database health check failed: {category}",
                "error": str(e)
            }


# Export public interface
__all__ = [
    'DatabaseErrorCategory',
    'categorize_database_error',
    'is_retryable_error',
    'calculate_retry_delay',
    'translate_database_error',
    'retry_database_operation',
    'handle_database_errors',
    'DatabaseHealthCheck'
]