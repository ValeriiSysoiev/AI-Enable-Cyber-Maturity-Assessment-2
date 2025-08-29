"""
Centralized input validation module for security and data integrity.
Provides comprehensive validation for all user inputs across the API.
"""
import re
import email.utils
from typing import Optional, Any, Dict
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

# Constants for validation
MAX_EMAIL_LENGTH = 254  # RFC 5321
MAX_ENGAGEMENT_ID_LENGTH = 100
MAX_TENANT_ID_LENGTH = 36  # UUID length
MAX_HEADER_VALUE_LENGTH = 1000
MAX_TEXT_INPUT_LENGTH = 10000
MAX_FILENAME_LENGTH = 255
ALLOWED_FILE_EXTENSIONS = {'.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.csv', '.json'}

# Regex patterns for validation
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
ENGAGEMENT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,98}[a-zA-Z0-9]$')
TENANT_ID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
SAFE_TEXT_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_.,;:!?()\[\]{}@#$%&*+=/<>"|\'`~\n\r\t]+$')
SQL_INJECTION_PATTERN = re.compile(r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC|EXECUTE|SCRIPT|JAVASCRIPT|EVAL)\b)', re.IGNORECASE)
PATH_TRAVERSAL_PATTERN = re.compile(r'(\.\./|\.\.\\|%2e%2e%2f|%2e%2e\\)')


def validate_email(email_str: Optional[str], field_name: str = "email") -> str:
    """
    Validate and canonicalize email address.
    
    Args:
        email_str: Email address to validate
        field_name: Field name for error messages
        
    Returns:
        Canonicalized email address (lowercase, trimmed)
        
    Raises:
        HTTPException: If email is invalid
    """
    if not email_str or not email_str.strip():
        raise HTTPException(422, f"{field_name} is required")
    
    email_str = email_str.strip()
    
    # Check length
    if len(email_str) > MAX_EMAIL_LENGTH:
        raise HTTPException(422, f"{field_name} exceeds maximum length of {MAX_EMAIL_LENGTH}")
    
    # Parse and validate structure
    parsed = email.utils.parseaddr(email_str)
    if not parsed[1] or '@' not in parsed[1]:
        raise HTTPException(422, f"{field_name} must be a valid email address")
    
    canonical_email = parsed[1].lower()
    
    # Additional validation with regex
    if not EMAIL_PATTERN.match(canonical_email):
        raise HTTPException(422, f"{field_name} format is invalid")
    
    # Check for SQL injection attempts
    if SQL_INJECTION_PATTERN.search(canonical_email):
        logger.warning(f"Potential SQL injection in {field_name}: {canonical_email[:50]}")
        raise HTTPException(422, f"{field_name} contains invalid characters")
    
    return canonical_email


def validate_engagement_id(engagement_id: Optional[str]) -> str:
    """
    Validate and sanitize engagement ID.
    
    Args:
        engagement_id: Engagement ID to validate
        
    Returns:
        Sanitized engagement ID
        
    Raises:
        HTTPException: If engagement ID is invalid
    """
    if not engagement_id or not engagement_id.strip():
        raise HTTPException(422, "Engagement ID is required")
    
    engagement_id = engagement_id.strip()
    
    # Check length
    if len(engagement_id) > MAX_ENGAGEMENT_ID_LENGTH:
        raise HTTPException(422, f"Engagement ID exceeds maximum length of {MAX_ENGAGEMENT_ID_LENGTH}")
    
    # Validate format (alphanumeric with hyphens and underscores)
    if not ENGAGEMENT_ID_PATTERN.match(engagement_id):
        raise HTTPException(422, "Engagement ID must contain only alphanumeric characters, hyphens, and underscores")
    
    # Check for path traversal attempts
    if PATH_TRAVERSAL_PATTERN.search(engagement_id):
        logger.warning(f"Path traversal attempt in engagement ID: {engagement_id}")
        raise HTTPException(422, "Engagement ID contains invalid characters")
    
    return engagement_id


def validate_tenant_id(tenant_id: Optional[str]) -> Optional[str]:
    """
    Validate tenant ID (UUID format).
    
    Args:
        tenant_id: Tenant ID to validate
        
    Returns:
        Validated tenant ID or None if not provided
        
    Raises:
        HTTPException: If tenant ID is invalid
    """
    if not tenant_id:
        return None
    
    tenant_id = tenant_id.strip()
    
    # Check length
    if len(tenant_id) > MAX_TENANT_ID_LENGTH:
        raise HTTPException(422, f"Tenant ID exceeds maximum length of {MAX_TENANT_ID_LENGTH}")
    
    # Validate UUID format
    if not TENANT_ID_PATTERN.match(tenant_id):
        raise HTTPException(422, "Tenant ID must be a valid UUID")
    
    return tenant_id.lower()


def validate_header_value(value: Optional[str], header_name: str, required: bool = True) -> Optional[str]:
    """
    Validate generic header value.
    
    Args:
        value: Header value to validate
        header_name: Header name for error messages
        required: Whether the header is required
        
    Returns:
        Sanitized header value or None
        
    Raises:
        HTTPException: If header is invalid
    """
    if not value or not value.strip():
        if required:
            raise HTTPException(422, f"{header_name} header is required")
        return None
    
    value = value.strip()
    
    # Check length
    if len(value) > MAX_HEADER_VALUE_LENGTH:
        raise HTTPException(422, f"{header_name} header exceeds maximum length")
    
    # Check for control characters
    if any(ord(char) < 32 for char in value):
        raise HTTPException(422, f"{header_name} header contains invalid control characters")
    
    return value


def validate_text_input(text: Optional[str], field_name: str, max_length: int = MAX_TEXT_INPUT_LENGTH, 
                        allow_html: bool = False, required: bool = True) -> Optional[str]:
    """
    Validate text input for forms and API requests.
    
    Args:
        text: Text to validate
        field_name: Field name for error messages
        max_length: Maximum allowed length
        allow_html: Whether to allow HTML tags
        required: Whether the field is required
        
    Returns:
        Sanitized text or None
        
    Raises:
        HTTPException: If text is invalid
    """
    if not text or not text.strip():
        if required:
            raise HTTPException(422, f"{field_name} is required")
        return None
    
    text = text.strip()
    
    # Check length
    if len(text) > max_length:
        raise HTTPException(422, f"{field_name} exceeds maximum length of {max_length}")
    
    # Check for SQL injection
    if SQL_INJECTION_PATTERN.search(text):
        logger.warning(f"Potential SQL injection in {field_name}")
        raise HTTPException(422, f"{field_name} contains potentially dangerous content")
    
    # Check for script injection if HTML not allowed
    if not allow_html:
        if re.search(r'<script|javascript:|on\w+\s*=', text, re.IGNORECASE):
            logger.warning(f"Potential XSS in {field_name}")
            raise HTTPException(422, f"{field_name} contains invalid HTML or scripts")
    
    return text


def validate_filename(filename: Optional[str]) -> str:
    """
    Validate and sanitize filename.
    
    Args:
        filename: Filename to validate
        
    Returns:
        Sanitized filename
        
    Raises:
        HTTPException: If filename is invalid
    """
    if not filename or not filename.strip():
        raise HTTPException(422, "Filename is required")
    
    filename = filename.strip()
    
    # Check length
    if len(filename) > MAX_FILENAME_LENGTH:
        raise HTTPException(422, f"Filename exceeds maximum length of {MAX_FILENAME_LENGTH}")
    
    # Check for path traversal
    if PATH_TRAVERSAL_PATTERN.search(filename) or '/' in filename or '\\' in filename:
        logger.warning(f"Path traversal attempt in filename: {filename}")
        raise HTTPException(422, "Filename contains invalid characters")
    
    # Check extension
    import os
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(422, f"File type {ext} is not allowed. Allowed types: {', '.join(ALLOWED_FILE_EXTENSIONS)}")
    
    # Sanitize filename - remove special characters except dots, hyphens, underscores
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    return sanitized


def validate_pagination(offset: Optional[int], limit: Optional[int]) -> tuple[int, int]:
    """
    Validate pagination parameters.
    
    Args:
        offset: Offset for pagination
        limit: Limit for pagination
        
    Returns:
        Tuple of (offset, limit) with defaults and bounds applied
        
    Raises:
        HTTPException: If parameters are invalid
    """
    # Default values
    offset = offset or 0
    limit = limit or 20
    
    # Validate offset
    if offset < 0:
        raise HTTPException(422, "Offset must be non-negative")
    if offset > 10000:
        raise HTTPException(422, "Offset exceeds maximum value")
    
    # Validate limit
    if limit < 1:
        raise HTTPException(422, "Limit must be positive")
    if limit > 100:
        raise HTTPException(422, "Limit exceeds maximum value of 100")
    
    return offset, limit


def sanitize_dict(data: Dict[str, Any], max_depth: int = 10) -> Dict[str, Any]:
    """
    Recursively sanitize dictionary values.
    
    Args:
        data: Dictionary to sanitize
        max_depth: Maximum recursion depth
        
    Returns:
        Sanitized dictionary
        
    Raises:
        HTTPException: If data contains invalid content
    """
    if max_depth <= 0:
        raise HTTPException(422, "Data structure too deeply nested")
    
    sanitized = {}
    for key, value in data.items():
        # Sanitize key
        if not isinstance(key, str) or len(key) > 100:
            raise HTTPException(422, f"Invalid key: {key[:50]}")
        
        # Sanitize value based on type
        if isinstance(value, str):
            sanitized[key] = validate_text_input(value, key, required=False) or ""
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, max_depth - 1)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item, max_depth - 1) if isinstance(item, dict) 
                else validate_text_input(item, key, required=False) if isinstance(item, str)
                else item
                for item in value[:1000]  # Limit list size
            ]
        elif isinstance(value, (int, float, bool, type(None))):
            sanitized[key] = value
        else:
            # Skip unknown types
            logger.warning(f"Skipping unknown type for key {key}: {type(value)}")
    
    return sanitized


# Export validation functions
__all__ = [
    'validate_email',
    'validate_engagement_id',
    'validate_tenant_id',
    'validate_header_value',
    'validate_text_input',
    'validate_filename',
    'validate_pagination',
    'sanitize_dict'
]