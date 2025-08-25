"""
Admin Authentication Diagnostics Endpoint

Provides detailed authentication and authorization status information
for administrators to debug AAD groups integration and user permissions.
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from api.security import current_context, require_admin, get_user_groups, get_user_roles, is_admin_enhanced
from domain.repository import Repository
from config import config
from services.aad_groups import create_aad_groups_service


router = APIRouter(prefix="/api/admin", tags=["admin", "auth"])
logger = logging.getLogger(__name__)


def get_repository(request: Request) -> Repository:
    """Get repository from app state"""
    return request.app.state.repo


class AuthModeInfo(BaseModel):
    """Authentication mode information"""
    mode: str
    enabled: bool
    description: str


class TenantInfo(BaseModel):
    """Tenant isolation information"""
    current_tenant_id: Optional[str]
    isolation_required: bool
    isolation_enabled: bool
    allowed_tenants: List[str]
    tenant_validated: bool


class GroupInfo(BaseModel):
    """AAD group information"""
    group_id: str
    group_name: str
    mapped_role: Optional[str]


class RoleInfo(BaseModel):
    """Role information"""
    role_name: str
    source: str  # "aad_group", "email_admin", "membership"
    description: Optional[str]


class UserAuthStatus(BaseModel):
    """User authentication and authorization status"""
    user_email: str
    is_admin_email: bool
    is_admin_aad: bool
    is_admin_effective: bool
    groups: List[GroupInfo]
    roles: List[RoleInfo]
    engagement_membership: Optional[Dict[str, Any]]


class AADServiceStatus(BaseModel):
    """AAD Groups service status"""
    operational: bool
    configuration_valid: bool
    tenant_configured: bool
    client_configured: bool
    group_mappings_count: int
    cache_stats: Dict[str, Any]
    last_error: Optional[str]


class AuthDiagnosticsResponse(BaseModel):
    """Complete auth diagnostics response"""
    timestamp: str
    auth_modes: List[AuthModeInfo]
    tenant_info: TenantInfo
    user_status: UserAuthStatus
    aad_service_status: AADServiceStatus
    configuration: Dict[str, Any]
    recommendations: List[str]


class AdminStatusResponse(BaseModel):
    """Admin system status response"""
    timestamp: str
    service: str
    version: str
    status: str
    uptime_seconds: float
    auth_modes: List[AuthModeInfo]
    admin_users_count: int
    aad_enabled: bool
    aad_operational: bool
    environment: str
    health_checks: Dict[str, bool]


@router.get("/status", response_model=AdminStatusResponse)
async def get_admin_status(
    request: Request,
    ctx: Dict[str, Any] = Depends(current_context),
    repo: Repository = Depends(get_repository)
):
    """
    Get admin system status and health information.
    
    Admin-only endpoint that provides:
    - Service health status
    - Authentication system status  
    - AAD integration status
    - Basic system metrics
    - Environment information
    
    This endpoint is designed for monitoring and health checks.
    """
    # Require admin access
    require_admin(repo, ctx)
    
    correlation_id = request.headers.get("X-Correlation-ID", "admin-status")
    user_email = ctx["user_email"]
    
    logger.info(
        "Admin status requested",
        extra={
            "user_email": user_email,
            "correlation_id": correlation_id
        }
    )
    
    try:
        # Calculate uptime
        import os
        from datetime import datetime
        startup_time_str = os.getenv("STARTUP_TIME")
        if startup_time_str:
            from dateutil.parser import parse
            startup_time = parse(startup_time_str)
            uptime_seconds = (datetime.now(startup_time.tzinfo) - startup_time).total_seconds()
        else:
            uptime_seconds = 0.0
        
        # Get authentication modes
        auth_modes = [
            AuthModeInfo(
                mode="email_admin",
                enabled=True,
                description="Email-based admin authentication"
            ),
            AuthModeInfo(
                mode="aad_groups",
                enabled=config.is_aad_groups_enabled(),
                description="Azure Active Directory groups authentication"
            )
        ]
        
        # Get AAD status
        aad_operational = False
        if config.is_aad_groups_enabled():
            try:
                aad_service = create_aad_groups_service(correlation_id)
                status = aad_service.get_status()
                aad_operational = status.get("operational", False)
            except Exception:
                aad_operational = False
        
        # Basic health checks
        health_checks = {
            "database": True,  # Basic check - if we got here, DB is working
            "config_valid": True,  # Basic check - if we got here, config loaded
            "aad_service": aad_operational if config.is_aad_groups_enabled() else True
        }
        
        # Get version info
        version = os.getenv("APP_VERSION", "dev")
        environment = os.getenv("ENVIRONMENT", "development")
        
        response = AdminStatusResponse(
            timestamp=datetime.now().isoformat(),
            service="ai-maturity-assessment-api",
            version=version,
            status="healthy",
            uptime_seconds=uptime_seconds,
            auth_modes=auth_modes,
            admin_users_count=len(config.admin_emails),
            aad_enabled=config.is_aad_groups_enabled(),
            aad_operational=aad_operational,
            environment=environment,
            health_checks=health_checks
        )
        
        logger.info(
            "Admin status completed",
            extra={
                "user_email": user_email,
                "status": response.status,
                "aad_operational": aad_operational,
                "correlation_id": correlation_id
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Failed to get admin status",
            extra={
                "user_email": user_email,
                "error": str(e),
                "correlation_id": correlation_id
            }
        )
        raise


@router.get("/auth-diagnostics", response_model=AuthDiagnosticsResponse)
async def get_auth_diagnostics(
    request: Request,
    ctx: Dict[str, Any] = Depends(current_context),
    repo: Repository = Depends(get_repository)
):
    """
    Get comprehensive authentication and authorization diagnostics.
    
    Admin-only endpoint that provides detailed information about:
    - Current authentication modes and their status
    - User's effective permissions and group memberships
    - AAD groups service operational status
    - Configuration validation results
    - Tenant isolation status
    - Troubleshooting recommendations
    
    This endpoint is designed to help administrators debug authentication
    issues and validate AAD groups integration.
    """
    # Require admin access
    require_admin(repo, ctx)
    
    correlation_id = request.headers.get("X-Correlation-ID", "auth-diagnostics")
    user_email = ctx["user_email"]
    
    logger.info(
        "Auth diagnostics requested",
        extra={
            "user_email": user_email,
            "correlation_id": correlation_id
        }
    )
    
    try:
        # Gather authentication mode information
        auth_modes = [
            AuthModeInfo(
                mode="email_admin",
                enabled=True,
                description="Email-based admin authentication using ADMIN_EMAILS environment variable"
            ),
            AuthModeInfo(
                mode="aad_groups",
                enabled=config.is_aad_groups_enabled(),
                description="Azure Active Directory groups-based authentication and role mapping"
            ),
            AuthModeInfo(
                mode="engagement_membership",
                enabled=True,
                description="Engagement-based membership and role authentication"
            )
        ]
        
        # Gather tenant information
        tenant_info = TenantInfo(
            current_tenant_id=ctx.get("tenant_id"),
            isolation_required=config.aad_groups.require_tenant_isolation,
            isolation_enabled=config.aad_groups.enabled,
            allowed_tenants=config.aad_groups.allowed_tenant_ids,
            tenant_validated=ctx.get("tenant_validated", True)
        )
        
        # Get AAD service status
        aad_service_status = await _get_aad_service_status(correlation_id)
        
        # Gather user authentication status
        user_status = await _get_user_auth_status(ctx, repo, correlation_id)
        
        # Gather configuration information
        configuration = {
            "aad_groups": config.get_aad_status(),
            "admin_emails_configured": len(config.admin_emails),
            "cors_origins": config.allowed_origins,
            "environment": {
                "auth_groups_mode": config.aad_groups.mode,
                "tenant_id": config.aad_groups.tenant_id,
                "require_tenant_isolation": config.aad_groups.require_tenant_isolation,
                "cache_ttl_minutes": config.aad_groups.cache_ttl_minutes
            }
        }
        
        # Generate recommendations
        recommendations = _generate_recommendations(ctx, aad_service_status, user_status)
        
        response = AuthDiagnosticsResponse(
            timestamp=datetime.utcnow().isoformat(),
            auth_modes=auth_modes,
            tenant_info=tenant_info,
            user_status=user_status,
            aad_service_status=aad_service_status,
            configuration=configuration,
            recommendations=recommendations
        )
        
        logger.info(
            "Auth diagnostics completed",
            extra={
                "user_email": user_email,
                "aad_operational": aad_service_status.operational,
                "group_count": len(user_status.groups),
                "role_count": len(user_status.roles),
                "correlation_id": correlation_id
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Failed to generate auth diagnostics",
            extra={
                "user_email": user_email,
                "error": str(e),
                "correlation_id": correlation_id
            }
        )
        raise


async def _get_aad_service_status(correlation_id: str) -> AADServiceStatus:
    """Get AAD groups service operational status"""
    if not config.aad_groups.enabled:
        return AADServiceStatus(
            operational=False,
            configuration_valid=False,
            tenant_configured=False,
            client_configured=False,
            group_mappings_count=0,
            cache_stats={},
            last_error="AAD groups authentication is disabled"
        )
    
    try:
        aad_service = create_aad_groups_service(correlation_id)
        status = aad_service.get_status()
        
        is_valid, validation_errors = config.validate_aad_config()
        
        return AADServiceStatus(
            operational=status["operational"],
            configuration_valid=is_valid,
            tenant_configured=bool(config.aad_groups.tenant_id),
            client_configured=status["configuration"]["client_configured"],
            group_mappings_count=status["configuration"]["group_mapping_count"],
            cache_stats=status["cache_stats"],
            last_error="; ".join(validation_errors) if validation_errors else None
        )
        
    except Exception as e:
        return AADServiceStatus(
            operational=False,
            configuration_valid=False,
            tenant_configured=bool(config.aad_groups.tenant_id),
            client_configured=bool(config.aad_groups.client_id),
            group_mappings_count=0,
            cache_stats={},
            last_error=str(e)
        )


async def _get_user_auth_status(ctx: Dict[str, Any], repo: Repository, correlation_id: str) -> UserAuthStatus:
    """Get comprehensive user authentication status"""
    user_email = ctx["user_email"]
    engagement_id = ctx["engagement_id"]
    
    # Get email-based admin status
    from api.security import is_admin
    is_admin_email = is_admin(user_email)
    
    # Get AAD admin status
    is_admin_aad = ctx.get("is_aad_admin", False)
    
    # Get effective admin status
    is_admin_effective = is_admin_enhanced(ctx)
    
    # Get group information with role mappings
    groups = []
    if config.is_aad_groups_enabled():
        try:
            aad_service = create_aad_groups_service(correlation_id)
            group_mappings = aad_service._group_roles_map
            
            for group_data in ctx.get("aad_groups", []):
                mapped_role = group_mappings.get(group_data["group_id"])
                groups.append(GroupInfo(
                    group_id=group_data["group_id"],
                    group_name=group_data["group_name"],
                    mapped_role=mapped_role
                ))
        except Exception as e:
            logger.warning(
                "Failed to get group role mappings",
                extra={"error": str(e), "correlation_id": correlation_id}
            )
    
    # Get role information
    roles = []
    
    # Add email admin role
    if is_admin_email:
        roles.append(RoleInfo(
            role_name="admin",
            source="email_admin",
            description="Admin access granted via ADMIN_EMAILS configuration"
        ))
    
    # Add AAD roles
    for role_name in ctx.get("aad_roles", []):
        roles.append(RoleInfo(
            role_name=role_name,
            source="aad_group",
            description="Role granted via AAD group membership"
        ))
    
    # Get engagement membership
    engagement_membership = None
    try:
        membership = repo.get_membership(engagement_id, user_email)
        if membership:
            engagement_membership = {
                "engagement_id": engagement_id,
                "role": membership.role,
                "joined_at": membership.joined_at.isoformat() if membership.joined_at else None
            }
    except Exception as e:
        logger.warning(
            "Failed to get engagement membership",
            extra={
                "user_email": user_email,
                "engagement_id": engagement_id,
                "error": str(e),
                "correlation_id": correlation_id
            }
        )
    
    return UserAuthStatus(
        user_email=user_email,
        is_admin_email=is_admin_email,
        is_admin_aad=is_admin_aad,
        is_admin_effective=is_admin_effective,
        groups=groups,
        roles=roles,
        engagement_membership=engagement_membership
    )


def _generate_recommendations(
    ctx: Dict[str, Any], 
    aad_status: AADServiceStatus, 
    user_status: UserAuthStatus
) -> List[str]:
    """Generate troubleshooting recommendations based on current status"""
    recommendations = []
    
    # AAD configuration recommendations
    if config.aad_groups.enabled and not aad_status.operational:
        recommendations.append("AAD groups is enabled but not operational. Check tenant_id, client_id, and client_secret configuration.")
    
    if config.aad_groups.enabled and not aad_status.configuration_valid:
        recommendations.append("AAD groups configuration is invalid. Review environment variables and JSON group mapping.")
    
    if config.aad_groups.enabled and aad_status.group_mappings_count == 0:
        recommendations.append("No group-to-role mappings configured. Set AAD_GROUP_MAP_JSON to map AAD groups to application roles.")
    
    # Tenant isolation recommendations
    if config.aad_groups.require_tenant_isolation and not ctx.get("tenant_validated", True):
        recommendations.append("Tenant isolation is enabled but validation failed. Check AAD_ALLOWED_TENANT_IDS configuration.")
    
    # User access recommendations
    if not user_status.is_admin_effective and not user_status.engagement_membership:
        recommendations.append("User has no admin access and no engagement membership. Add to ADMIN_EMAILS or assign to an engagement.")
    
    if config.aad_groups.enabled and len(user_status.groups) == 0:
        recommendations.append("User has no AAD group memberships. Ensure user is assigned to appropriate AAD groups.")
    
    if config.aad_groups.enabled and len(user_status.roles) == 0 and not user_status.is_admin_email:
        recommendations.append("User has AAD groups but no mapped roles. Review group-to-role mappings in AAD_GROUP_MAP_JSON.")
    
    # Cache recommendations
    if aad_status.cache_stats.get("misses", 0) > aad_status.cache_stats.get("hits", 0):
        recommendations.append("AAD groups cache has more misses than hits. Consider increasing AAD_CACHE_TTL_MINUTES.")
    
    if not recommendations:
        recommendations.append("Authentication system appears to be functioning correctly.")
    
    return recommendations