"""
Security utilities for authentication and authorization.
Mock implementation for audit logging endpoints.
"""
from typing import List
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Get current authenticated user.
    Mock implementation for testing purposes.
    """
    # In a real implementation, this would validate the JWT token
    # and return user information from the token or database
    return {
        "user_id": "test_user_123",
        "username": "test_user",
        "permissions": [
            "audit:read",
            "audit:export", 
            "audit:export:pii",
            "audit:replay"
        ]
    }


def require_permissions(user: dict, required_permissions: List[str]):
    """
    Check if user has required permissions.
    
    Args:
        user: User object with permissions
        required_permissions: List of required permission strings
        
    Raises:
        HTTPException: If user lacks required permissions
    """
    user_permissions = user.get("permissions", [])
    
    missing_permissions = []
    for perm in required_permissions:
        if perm not in user_permissions:
            missing_permissions.append(perm)
    
    if missing_permissions:
        raise HTTPException(
            status_code=403,
            detail=f"Missing required permissions: {', '.join(missing_permissions)}"
        )