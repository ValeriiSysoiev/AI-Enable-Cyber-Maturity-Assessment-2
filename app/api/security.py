import os
import logging
from fastapi import Header, HTTPException, Depends, Request
from typing import Any, Dict, Optional, Set
from domain.repository import Repository
from config import config
from services.aad_groups import create_aad_groups_service, UserRoles
from api.input_validation import validate_email, validate_engagement_id, validate_tenant_id

logger = logging.getLogger(__name__)


def is_admin(user_email: str) -> bool:
    """Check if user is an admin based on ADMIN_EMAILS env var"""
    # Validate email format first
    if not user_email or not isinstance(user_email, str):
        return False
    
    # Parse and normalize email
    parsed = email.utils.parseaddr(user_email.strip())
    if not parsed[1] or '@' not in parsed[1]:
        return False
    
    canonical_email = parsed[1].strip().lower()
    
    admins = [e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()]
    return canonical_email in admins


async def is_admin_with_demo_fallback(user_email: str, repository: Optional[Repository] = None) -> bool:
    """
    Check if user is an admin, including demo admin fallback
    
    Checks:
    1. ADMIN_EMAILS environment variable (always)
    2. Demo admin list (only in AUTH_MODE=demo)
    """
    # First check standard admin emails
    if is_admin(user_email):
        return True
    
    # In demo mode, also check demo admin list
    auth_mode = os.getenv("AUTH_MODE", "demo").lower()
    if auth_mode == "demo":
        try:
            from domain.admin_repository import create_admin_repository
            
            # Use provided repository or create a minimal one
            if repository is None:
                # Create a minimal repository for demo mode
                from domain.file_repo import FileRepository
                repository = FileRepository()
            
            admin_repo = create_admin_repository(
                data_backend=os.getenv("DATA_BACKEND", "local"),
                repository=repository
            )
            
            return await admin_repo.is_demo_admin(user_email)
        except Exception as e:
            logger.warning(f"Failed to check demo admin status: {e}")
            return False
    
    return False


async def current_context(
    request: Request,
    x_user_email: str = Header(..., alias="X-User-Email"),
    x_engagement_id: str = Header(..., alias="X-Engagement-ID"),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID")
) -> Dict[str, Any]:
    """
    Extract current user and engagement context from headers.
    Includes AAD group information when AAD groups mode is enabled.
    """
    # Use comprehensive input validation
    canonical_email = validate_email(x_user_email, "X-User-Email header")
    engagement_id_normalized = validate_engagement_id(x_engagement_id)
    tenant_id_validated = validate_tenant_id(x_tenant_id)
    
    # Base context (always present)
    context = {
        "user_email": canonical_email,
        "engagement_id": engagement_id_normalized,
        "tenant_id": tenant_id_validated,
        "aad_groups_enabled": config.is_aad_groups_enabled()
    }
    
    # Add AAD group information if enabled
    if config.is_aad_groups_enabled():
        try:
            correlation_id = request.headers.get("X-Correlation-ID", "security-context")
            aad_service = create_aad_groups_service(correlation_id)
            
            # Validate tenant isolation
            if tenant_id_validated and not aad_service.validate_tenant_isolation(tenant_id_validated):
                logger.warning(
                    "Tenant isolation violation",
                    extra={
                        "user_email": canonical_email,
                        "user_tenant_id": tenant_id_validated,
                        "correlation_id": correlation_id
                    }
                )
                raise HTTPException(403, "Access denied: tenant not allowed")
            
            # Get user roles from AAD groups
            user_roles = await aad_service.get_user_roles(canonical_email, tenant_id_validated)
            
            # Add AAD context information
            context.update({
                "aad_groups": [
                    {
                        "group_id": group.group_id,
                        "group_name": group.group_name
                    }
                    for group in user_roles.groups
                ],
                "aad_roles": list(user_roles.roles),
                "is_aad_admin": user_roles.is_admin,
                "tenant_validated": True
            })
            
            logger.info(
                "Enhanced security context with AAD groups",
                extra={
                    "user_email": canonical_email,
                    "group_count": len(user_roles.groups),
                    "roles": list(user_roles.roles),
                    "is_admin": user_roles.is_admin,
                    "correlation_id": correlation_id
                }
            )
            
        except HTTPException:
            # Re-raise HTTP exceptions (like tenant isolation failures)
            raise
        except Exception as e:
            # Log AAD failures but don't block access in demo mode fallback
            logger.error(
                "Failed to fetch AAD group information",
                extra={
                    "user_email": canonical_email,
                    "error": str(e),
                    "correlation_id": request.headers.get("X-Correlation-ID", "security-context")
                }
            )
            
            # Add failed AAD context but allow fallback to email-based auth
            context.update({
                "aad_groups": [],
                "aad_roles": [],
                "is_aad_admin": False,
                "aad_error": str(e),
                "tenant_validated": False
            })
    else:
        # AAD groups disabled - add empty context
        context.update({
            "aad_groups": [],
            "aad_roles": [],
            "is_aad_admin": False,
            "tenant_validated": True  # Not applicable when AAD disabled
        })
    
    return context


def get_user_groups(ctx: Dict[str, Any]) -> Set[str]:
    """
    Get user's AAD group IDs from context
    
    Args:
        ctx: Security context from current_context()
        
    Returns:
        Set of group IDs user belongs to
    """
    if not ctx.get("aad_groups_enabled", False):
        return set()
    
    return {group["group_id"] for group in ctx.get("aad_groups", [])}


def get_user_roles(ctx: Dict[str, Any]) -> Set[str]:
    """
    Get user's effective roles from AAD groups
    
    Args:
        ctx: Security context from current_context()
        
    Returns:
        Set of role names
    """
    if not ctx.get("aad_groups_enabled", False):
        return set()
    
    return set(ctx.get("aad_roles", []))


def is_admin_enhanced(ctx: Dict[str, Any]) -> bool:
    """
    Check if user is admin using both email-based and AAD group-based methods
    
    Args:
        ctx: Security context from current_context()
        
    Returns:
        True if user is admin, False otherwise
    """
    user_email = ctx["user_email"]
    
    # Check email-based admin status (legacy)
    if is_admin(user_email):
        return True
    
    # Check AAD-based admin status if available
    if ctx.get("aad_groups_enabled", False):
        return ctx.get("is_aad_admin", False)
    
    return False


def tenant_isolation_check(ctx: Dict[str, Any]) -> bool:
    """
    Verify tenant isolation requirements are met
    
    Args:
        ctx: Security context from current_context()
        
    Returns:
        True if tenant validation passes or is not required
    """
    if not config.aad_groups.require_tenant_isolation:
        return True
    
    return ctx.get("tenant_validated", True)


def require_member(repo=None, ctx: Dict[str, Any] = None, min_role: str = "member"):
    """
    Ensure user has required role in the engagement.
    Uses enhanced context with AAD group information.
    """
    m = repo.get_membership(ctx["engagement_id"], ctx["user_email"])
    
    # Admin users have access to everything (check both email and AAD admin status)
    if is_admin_enhanced(ctx):
        return
    
    # Verify tenant isolation if enabled
    if not tenant_isolation_check(ctx):
        raise HTTPException(403, "Access denied: tenant validation failed")
    
    # Check membership exists
    if m is None:
        raise HTTPException(403, "Not a member of this engagement")
    
    # Check role hierarchy
    if min_role == "lead" and m.role != "lead":
        raise HTTPException(403, "Lead role required")


def require_admin(repo: Repository, ctx: Dict[str, Any]):
    """
    Ensure user is an admin using enhanced authentication methods.
    Checks both email-based and AAD group-based admin status.
    """
    # Verify tenant isolation if enabled
    if not tenant_isolation_check(ctx):
        raise HTTPException(403, "Access denied: tenant validation failed")
    
    if not is_admin_enhanced(ctx):
        raise HTTPException(403, "Admin access required")


def require_role(ctx: Dict[str, Any], required_roles: Set[str]):
    """
    Ensure user has one of the required AAD roles
    
    Args:
        ctx: Security context from current_context()
        required_roles: Set of role names, user must have at least one
        
    Raises:
        HTTPException: If user doesn't have required role or AAD is not enabled
    """
    if not config.is_aad_groups_enabled():
        raise HTTPException(403, "AAD groups authentication is not enabled")
    
    # Verify tenant isolation if enabled
    if not tenant_isolation_check(ctx):
        raise HTTPException(403, "Access denied: tenant validation failed")
    
    # Admin users bypass role checks
    if is_admin_enhanced(ctx):
        return
    
    user_roles = get_user_roles(ctx)
    
    if not user_roles.intersection(required_roles):
        raise HTTPException(
            403, 
            f"Access denied: requires one of {list(required_roles)}, user has {list(user_roles)}"
        )
