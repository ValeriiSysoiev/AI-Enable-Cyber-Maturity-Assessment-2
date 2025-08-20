"""
Logging utilities and correlation ID management.
"""
import uuid
from typing import Optional
from contextvars import ContextVar
from fastapi import Request

# Context variable for storing correlation ID throughout request lifecycle
correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: str):
    """Set correlation ID in context."""
    correlation_id_context.set(correlation_id)


def get_correlation_id() -> str:
    """
    Get correlation ID from context, or generate new one if not set.
    
    Returns:
        Correlation ID string
    """
    corr_id = correlation_id_context.get()
    if not corr_id:
        corr_id = generate_correlation_id()
        set_correlation_id(corr_id)
    return corr_id


def extract_correlation_id_from_request(request: Request) -> str:
    """
    Extract correlation ID from request headers or generate new one.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Correlation ID string
    """
    # Try to get from header first
    corr_id = request.headers.get('x-correlation-id')
    
    if not corr_id:
        # Generate new one
        corr_id = generate_correlation_id()
    
    # Set in context for this request
    set_correlation_id(corr_id)
    
    return corr_id