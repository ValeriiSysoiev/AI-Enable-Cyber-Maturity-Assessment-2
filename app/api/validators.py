"""
Input validation utilities for API security

This module provides centralized validation functions for all user inputs
to prevent injection attacks and ensure data integrity.
"""

import re
import email.utils
from typing import Optional, Dict, Any
from fastapi import HTTPException

# Maximum lengths for different input types
MAX_EMAIL_LENGTH = 254  # RFC 5321
MAX_ENGAGEMENT_ID_LENGTH = 100
MAX_TENANT_ID_LENGTH = 36  # UUID length
MAX_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 1000
MAX_URL_LENGTH = 2048
MAX_GENERIC_STRING_LENGTH = 500

# Validation patterns - more restrictive for security
PATTERNS = {
    # Alphanumeric with limited special chars, no spaces
    'engagement_id': re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,98}[a-zA-Z0-9]$'),
    
    # UUID format for tenant IDs
    'tenant_id': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE),
    
    # Alphanumeric with spaces and limited punctuation for names
    'name': re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\s\-_.]{0,98}[a-zA-Z0-9]$'),
    
    # More permissive for descriptions but still safe
    'description': re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\s\-_.,;:!?()\'"]{0,998}[a-zA-Z0-9.!?]$'),
    
    # Email validation pattern (simplified but effective)
    'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
    
    # URL validation - support ports and query strings
    'url': re.compile(r'^https?://[a-zA-Z0-9.-]+(:[0-9]+)?(?:\.[a-zA-Z]{2,})?(?:/[^\\<>]*)?$'),
    
    # Generic safe string (no special chars that could be used for injection)
    'safe_string': re.compile(r'^[a-zA-Z0-9\s\-_.]{1,500}$')
}


def validate_email(email_input: str, field_name: str = "email") -> str:
    """
    Validate and normalize an email address
    
    Args:
        email_input: The email string to validate
        field_name: Name of the field for error messages
        
    Returns:
        Normalized email address
        
    Raises:
        HTTPException: If validation fails
    """
    if not email_input or not isinstance(email_input, str):
        raise HTTPException(422, f"{field_name} is required and must be a string")
    
    # Check length - email_input is the raw input
    if len(email_input.strip()) > MAX_EMAIL_LENGTH:
        raise HTTPException(422, f"{field_name} exceeds maximum length of {MAX_EMAIL_LENGTH}")
    
    # Parse and validate format
    parsed = email.utils.parseaddr(email_input.strip())
    if not parsed[1] or '@' not in parsed[1]:
        raise HTTPException(422, f"Invalid {field_name} format")
    
    canonical_email = parsed[1].strip().lower()
    
    # Validate against pattern
    if not PATTERNS['email'].match(canonical_email):
        raise HTTPException(422, f"Invalid {field_name} format")
    
    return canonical_email


def validate_engagement_id(engagement_id: str) -> str:
    """
    Validate an engagement ID
    
    Args:
        engagement_id: The engagement ID to validate
        
    Returns:
        Validated engagement ID
        
    Raises:
        HTTPException: If validation fails
    """
    if not engagement_id or not isinstance(engagement_id, str):
        raise HTTPException(422, "Engagement ID is required")
    
    engagement_id = engagement_id.strip()
    
    # Check length
    if len(engagement_id) > MAX_ENGAGEMENT_ID_LENGTH:
        raise HTTPException(422, f"Engagement ID exceeds maximum length of {MAX_ENGAGEMENT_ID_LENGTH}")
    
    # Validate pattern - must start and end with alphanumeric
    if not PATTERNS['engagement_id'].match(engagement_id):
        raise HTTPException(
            422, 
            "Engagement ID must start and end with alphanumeric characters and contain only letters, numbers, hyphens, and underscores"
        )
    
    return engagement_id


def validate_tenant_id(tenant_id: Optional[str]) -> Optional[str]:
    """
    Validate a tenant ID (should be UUID format)
    
    Args:
        tenant_id: The tenant ID to validate (optional)
        
    Returns:
        Validated tenant ID or None
        
    Raises:
        HTTPException: If validation fails
    """
    if not tenant_id:
        return None
    
    if not isinstance(tenant_id, str):
        raise HTTPException(422, "Tenant ID must be a string")
    
    tenant_id = tenant_id.strip().lower()
    
    # Check length
    if len(tenant_id) != MAX_TENANT_ID_LENGTH:
        raise HTTPException(422, f"Tenant ID must be exactly {MAX_TENANT_ID_LENGTH} characters (UUID format)")
    
    # Validate UUID format
    if not PATTERNS['tenant_id'].match(tenant_id):
        raise HTTPException(422, "Tenant ID must be a valid UUID")
    
    return tenant_id


def validate_name(name: str, field_name: str = "name", max_length: int = MAX_NAME_LENGTH) -> str:
    """
    Validate a name field (e.g., user name, assessment name)
    
    Args:
        name: The name to validate
        field_name: Name of the field for error messages
        max_length: Maximum allowed length
        
    Returns:
        Validated name
        
    Raises:
        HTTPException: If validation fails
    """
    if not name or not isinstance(name, str):
        raise HTTPException(422, f"{field_name} is required and must be a string")
    
    name = name.strip()
    
    # Check length
    if len(name) < 2:
        raise HTTPException(422, f"{field_name} must be at least 2 characters")
    
    if len(name) > max_length:
        raise HTTPException(422, f"{field_name} exceeds maximum length of {max_length}")
    
    # Validate pattern
    if not PATTERNS['name'].match(name):
        raise HTTPException(
            422,
            f"{field_name} must start and end with alphanumeric characters and contain only letters, numbers, spaces, and basic punctuation"
        )
    
    return name


def validate_description(description: Optional[str], max_length: int = MAX_DESCRIPTION_LENGTH) -> Optional[str]:
    """
    Validate a description field
    
    Args:
        description: The description to validate (optional)
        max_length: Maximum allowed length
        
    Returns:
        Validated description or None
        
    Raises:
        HTTPException: If validation fails
    """
    if not description:
        return None
    
    if not isinstance(description, str):
        raise HTTPException(422, "Description must be a string")
    
    description = description.strip()
    
    if not description:
        return None
    
    # Check length
    if len(description) > max_length:
        raise HTTPException(422, f"Description exceeds maximum length of {max_length}")
    
    # Validate pattern - more permissive but still safe
    if not PATTERNS['description'].match(description):
        raise HTTPException(
            422,
            "Description contains invalid characters. Only alphanumeric, spaces, and basic punctuation are allowed"
        )
    
    return description


def validate_url(url: str, field_name: str = "URL") -> str:
    """
    Validate a URL
    
    Args:
        url: The URL to validate
        field_name: Name of the field for error messages
        
    Returns:
        Validated URL
        
    Raises:
        HTTPException: If validation fails
    """
    if not url or not isinstance(url, str):
        raise HTTPException(422, f"{field_name} is required and must be a string")
    
    url = url.strip()
    
    # Check length
    if len(url) > MAX_URL_LENGTH:
        raise HTTPException(422, f"{field_name} exceeds maximum length of {MAX_URL_LENGTH}")
    
    # Validate pattern - only allow http/https URLs
    if not PATTERNS['url'].match(url):
        raise HTTPException(422, f"Invalid {field_name} format. Only HTTP/HTTPS URLs are allowed")
    
    return url


def validate_safe_string(
    value: str, 
    field_name: str = "value",
    max_length: int = MAX_GENERIC_STRING_LENGTH,
    allow_empty: bool = False
) -> str:
    """
    Validate a generic string for safety
    
    Args:
        value: The string to validate
        field_name: Name of the field for error messages
        max_length: Maximum allowed length
        allow_empty: Whether to allow empty strings
        
    Returns:
        Validated string
        
    Raises:
        HTTPException: If validation fails
    """
    if not value and not allow_empty:
        raise HTTPException(422, f"{field_name} is required")
    
    if not isinstance(value, str):
        raise HTTPException(422, f"{field_name} must be a string")
    
    value = value.strip()
    
    if not value and not allow_empty:
        raise HTTPException(422, f"{field_name} cannot be empty")
    
    if not value and allow_empty:
        return ""
    
    # Check length
    if len(value) > max_length:
        raise HTTPException(422, f"{field_name} exceeds maximum length of {max_length}")
    
    # Validate pattern - no special chars that could be used for injection
    if not PATTERNS['safe_string'].match(value):
        raise HTTPException(
            422,
            f"{field_name} contains invalid characters. Only alphanumeric, spaces, hyphens, underscores, and periods are allowed"
        )
    
    return value


def sanitize_dict(data: Dict[str, Any], max_depth: int = 5) -> Dict[str, Any]:
    """
    Recursively sanitize a dictionary by validating all string values
    
    Args:
        data: Dictionary to sanitize
        max_depth: Maximum recursion depth
        
    Returns:
        Sanitized dictionary
        
    Raises:
        HTTPException: If validation fails
    """
    if max_depth <= 0:
        raise HTTPException(422, "Data structure too deeply nested")
    
    sanitized = {}
    
    for key, value in data.items():
        # Validate key
        if not isinstance(key, str):
            raise HTTPException(422, "Dictionary keys must be strings")
        
        safe_key = validate_safe_string(key, f"key '{key}'", max_length=100)
        
        # Process value based on type
        if isinstance(value, str):
            # Don't validate emails within general dict sanitization - they have their own validators
            # Allow @ for email addresses in dict values
            if '@' in value:
                # Basic check to prevent injection but allow emails
                if '<' in value or '>' in value or ';' in value or '\'' in value or '"' in value:
                    raise HTTPException(422, f"value for '{safe_key}' contains invalid characters")
                sanitized[safe_key] = value.strip()
            else:
                sanitized[safe_key] = validate_safe_string(value, f"value for '{safe_key}'", allow_empty=True)
        elif isinstance(value, dict):
            sanitized[safe_key] = sanitize_dict(value, max_depth - 1)
        elif isinstance(value, list):
            sanitized[safe_key] = [
                sanitize_dict(item, max_depth - 1) if isinstance(item, dict)
                else validate_safe_string(item, f"list item", allow_empty=True) if isinstance(item, str) and '@' not in item
                else item.strip() if isinstance(item, str) else item
                for item in value
            ]
        else:
            # Numbers, booleans, None are passed through
            sanitized[safe_key] = value
    
    return sanitized