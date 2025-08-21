"""
Attribute-Based Access Control for engagement-scoped resources
"""
from functools import wraps
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ABACPolicy:
    """ABAC policy enforcement for sensitive resources"""
    
    SENSITIVE_RESOURCES = [
        'audit_bundle',
        'mcp_tools',
        'engagement_download',
        'pii_export'
    ]
    
    @staticmethod
    def check_engagement_scope(
        user_claims: Dict[str, Any],
        resource_engagement_id: str,
        resource_type: str
    ) -> bool:
        """Check if user has access to engagement-scoped resource"""
        # Extract user's engagement scope
        user_engagements = user_claims.get('engagements', [])
        user_roles = user_claims.get('roles', [])
        
        # System admins bypass engagement checks
        if 'system_admin' in user_roles:
            logger.info(f"Admin access granted for {resource_type}")
            return True
        
        # Check engagement match
        if resource_engagement_id not in user_engagements:
            logger.warning(
                f"Access denied: user not in engagement {resource_engagement_id} "
                f"for resource {resource_type}"
            )
            return False
        
        # Check resource-specific permissions
        if resource_type in ABACPolicy.SENSITIVE_RESOURCES:
            required_role = f"{resource_type}_access"
            if required_role not in user_claims.get('permissions', []):
                logger.warning(
                    f"Access denied: missing permission {required_role}"
                )
                return False
        
        logger.info(f"Access granted for {resource_type} in {resource_engagement_id}")
        return True

def require_engagement_scope(resource_type: str):
    """Decorator for engagement-scoped access control"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user claims and engagement_id from request context
            request = kwargs.get('request') or args[0] if args else None
            if not request:
                raise ValueError("Request context required for ABAC")
            
            user_claims = getattr(request.state, 'user_claims', {})
            engagement_id = kwargs.get('engagement_id') or \
                           request.path_params.get('engagement_id')
            
            if not ABACPolicy.check_engagement_scope(
                user_claims, engagement_id, resource_type
            ):
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied to {resource_type} for engagement {engagement_id}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator