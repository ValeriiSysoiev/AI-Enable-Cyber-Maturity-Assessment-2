"""
Authorization module for secure resource access control

This module implements proper authorization checks to prevent
insecure direct object references (IDOR) vulnerabilities.
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, Depends
from domain.repository import Repository
from domain.models import Engagement, Membership
from api.security import current_context, is_admin_with_demo_fallback

logger = logging.getLogger(__name__)


class AuthorizationService:
    """Service for handling authorization checks"""
    
    def __init__(self, repository: Repository):
        self.repository = repository
    
    async def check_engagement_access(
        self, 
        user_email: str, 
        engagement_id: str,
        required_role: Optional[str] = None,
        is_admin: bool = False
    ) -> bool:
        """
        Check if a user has access to an engagement
        
        Args:
            user_email: The user's email address
            engagement_id: The engagement ID to check
            required_role: Optional specific role required (e.g., "owner", "admin")
            is_admin: Whether the user is a system admin
            
        Returns:
            True if user has access, False otherwise
        """
        # System admins have access to all engagements
        if is_admin:
            logger.info(f"Admin access granted for {user_email} to engagement {engagement_id}")
            return True
        
        try:
            # Get all memberships for this engagement
            memberships = self.repository.list_memberships_for_engagement(engagement_id)
            
            # Check if user is a member
            user_membership = None
            for membership in memberships:
                if membership.user_email.lower() == user_email.lower():
                    user_membership = membership
                    break
            
            if not user_membership:
                logger.warning(
                    f"Access denied: {user_email} is not a member of engagement {engagement_id}"
                )
                return False
            
            # If a specific role is required, check it
            if required_role:
                if user_membership.role != required_role:
                    logger.warning(
                        f"Access denied: {user_email} has role {user_membership.role}, "
                        f"but {required_role} is required for engagement {engagement_id}"
                    )
                    return False
            
            logger.info(
                f"Access granted for {user_email} to engagement {engagement_id} "
                f"with role {user_membership.role}"
            )
            return True
            
        except Exception as e:
            logger.error(
                f"Error checking engagement access for {user_email} to {engagement_id}: {e}"
            )
            # Fail closed - deny access on error
            return False
    
    async def check_assessment_access(
        self,
        user_email: str,
        assessment_id: str,
        is_admin: bool = False
    ) -> bool:
        """
        Check if a user has access to an assessment
        
        Args:
            user_email: The user's email address
            assessment_id: The assessment ID to check
            is_admin: Whether the user is a system admin
            
        Returns:
            True if user has access, False otherwise
        """
        # System admins have access to all assessments
        if is_admin:
            return True
        
        try:
            # Get the assessment to find its engagement
            assessment = self.repository.get_assessment(assessment_id)
            if not assessment:
                logger.warning(f"Assessment {assessment_id} not found")
                return False
            
            # Check engagement access
            return await self.check_engagement_access(
                user_email, 
                assessment.engagement_id,
                is_admin=is_admin
            )
            
        except Exception as e:
            logger.error(
                f"Error checking assessment access for {user_email} to {assessment_id}: {e}"
            )
            return False
    
    async def list_authorized_engagements(
        self,
        user_email: str,
        is_admin: bool = False
    ) -> List[Engagement]:
        """
        List all engagements a user has access to
        
        Args:
            user_email: The user's email address
            is_admin: Whether the user is a system admin
            
        Returns:
            List of engagements the user can access
        """
        try:
            # Use repository method which handles admin vs member access
            return self.repository.list_engagements_for_user(user_email, is_admin)
        except Exception as e:
            logger.error(f"Error listing engagements for {user_email}: {e}")
            return []
    
    def validate_engagement_id_format(self, engagement_id: str) -> bool:
        """
        Validate the format of an engagement ID to prevent injection
        
        Args:
            engagement_id: The engagement ID to validate
            
        Returns:
            True if valid format, False otherwise
        """
        import re
        
        # Engagement IDs should be UUIDs or alphanumeric with hyphens
        # This prevents path traversal and injection attacks
        pattern = r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,98}[a-zA-Z0-9]$'
        
        if not engagement_id or len(engagement_id) < 3 or len(engagement_id) > 100:
            return False
        
        return bool(re.match(pattern, engagement_id))


# Dependency injection helper
async def get_authorization_service(
    repository: Repository = Depends(lambda: Repository())
) -> AuthorizationService:
    """Get an instance of the authorization service"""
    return AuthorizationService(repository)


# Decorator for protecting engagement-scoped endpoints
def require_engagement_access(required_role: Optional[str] = None):
    """
    Decorator to require engagement access for an endpoint
    
    Args:
        required_role: Optional specific role required
    """
    async def check_access(
        context: Dict[str, Any] = Depends(current_context),
        auth_service: AuthorizationService = Depends(get_authorization_service)
    ):
        user_email = context.get("user_email")
        engagement_id = context.get("engagement_id")
        
        if not user_email or not engagement_id:
            raise HTTPException(
                status_code=400,
                detail="User email and engagement ID are required"
            )
        
        # Validate engagement ID format
        if not auth_service.validate_engagement_id_format(engagement_id):
            raise HTTPException(
                status_code=400,
                detail="Invalid engagement ID format"
            )
        
        # Check if user is admin
        is_admin = await is_admin_with_demo_fallback(user_email)
        
        # Check engagement access
        has_access = await auth_service.check_engagement_access(
            user_email,
            engagement_id,
            required_role=required_role,
            is_admin=is_admin
        )
        
        if not has_access:
            logger.warning(
                f"Unauthorized access attempt by {user_email} to engagement {engagement_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="You do not have access to this engagement"
            )
        
        return context
    
    return check_access


# Convenience decorators for common access patterns
require_engagement_member = require_engagement_access()
require_engagement_owner = require_engagement_access(required_role="owner")
require_engagement_admin = require_engagement_access(required_role="admin")