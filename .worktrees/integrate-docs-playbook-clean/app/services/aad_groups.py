"""
Azure Active Directory Groups Service

Provides integration with Microsoft Graph API for AAD group membership queries
and role mapping. Includes caching and tenant isolation for security.
"""
import json
import logging
import time
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

import msal
from cachetools import TTLCache

from config import config
from .cache import get_cached, invalidate_cache_key, cache_manager


logger = logging.getLogger(__name__)


@dataclass
class GroupMembership:
    """Represents a user's group membership"""
    group_id: str
    group_name: str
    tenant_id: str
    fetched_at: datetime


@dataclass
class UserRoles:
    """Represents a user's effective roles from group mappings"""
    user_email: str
    tenant_id: str
    groups: List[GroupMembership]
    roles: Set[str]
    is_admin: bool
    fetched_at: datetime


class AADGroupsService:
    """
    Service for querying Azure Active Directory group memberships
    and mapping them to application roles.
    """
    
    def __init__(self, correlation_id: str = "aad-groups"):
        """
        Initialize AAD Groups Service
        
        Args:
            correlation_id: Correlation ID for request tracking
        """
        self.correlation_id = correlation_id
        
        # Legacy cache for backward compatibility (will be phased out)
        cache_ttl_seconds = config.aad_groups.cache_ttl_minutes * 60
        self._legacy_cache: TTLCache = TTLCache(maxsize=1000, ttl=cache_ttl_seconds)
        
        # New unified cache configuration
        self.cache_name = "user_roles"
        self.cache_config = {
            "max_size_mb": config.cache.user_roles_max_size_mb,
            "max_entries": config.cache.user_roles_max_entries,
            "default_ttl_seconds": config.cache.user_roles_ttl_seconds,
            "cleanup_interval_seconds": config.cache.cleanup_interval_seconds
        }
        
        # Parse group mapping configuration
        self._group_roles_map = self._parse_group_mapping()
        
        # Initialize MSAL client
        self._msal_client = None
        if config.is_aad_groups_enabled():
            self._msal_client = self._create_msal_client()

    def _parse_group_mapping(self) -> Dict[str, str]:
        """Parse group ID to role mapping from configuration"""
        try:
            group_map = json.loads(config.aad_groups.group_map_json)
            if not isinstance(group_map, dict):
                logger.warning("AAD group mapping is not a dictionary, using empty mapping", extra={"correlation_id": self.correlation_id})
                return {}
            
            logger.info(
                "Loaded AAD group mapping",
                extra={"group_count": len(group_map), "correlation_id": self.correlation_id}
            )
            return group_map
            
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse AAD group mapping JSON",
                extra={"error": str(e), "raw_json": config.aad_groups.group_map_json, "correlation_id": self.correlation_id}
            )
            return {}

    def _create_msal_client(self) -> Optional[msal.ConfidentialClientApplication]:
        """Create MSAL client for Microsoft Graph API access"""
        try:
            authority = f"https://login.microsoftonline.com/{config.aad_groups.tenant_id}"
            
            client = msal.ConfidentialClientApplication(
                client_id=config.aad_groups.client_id,
                client_credential=config.aad_groups.client_secret,
                authority=authority
            )
            
            logger.info(
                "MSAL client initialized",
                extra={"tenant_id": config.aad_groups.tenant_id, "correlation_id": self.correlation_id}
            )
            return client
            
        except Exception as e:
            logger.error(
                "Failed to create MSAL client",
                extra={"error": str(e), "correlation_id": self.correlation_id}
            )
            return None

    def _get_access_token(self) -> Optional[str]:
        """Get access token for Microsoft Graph API"""
        if not self._msal_client:
            return None
        
        try:
            # Use client credentials flow for app-only access
            result = self._msal_client.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )
            
            if "access_token" in result:
                return result["access_token"]
            else:
                logger.error(
                    "Failed to acquire access token",
                    extra={"error": result.get("error_description", "Unknown error"), "correlation_id": self.correlation_id}
                )
                return None
                
        except Exception as e:
            logger.error(
                "Exception acquiring access token",
                extra={"error": str(e), "correlation_id": self.correlation_id}
            )
            return None

    def validate_tenant_isolation(self, user_tenant_id: str) -> bool:
        """
        Validate that user's tenant is allowed based on configuration
        
        Args:
            user_tenant_id: Tenant ID from user's token
            
        Returns:
            True if tenant is allowed, False otherwise
        """
        if not config.aad_groups.require_tenant_isolation:
            return True
        
        # Check if we have allowed tenants configured
        allowed_tenants = config.aad_groups.allowed_tenant_ids
        if not allowed_tenants:
            # If no allowed tenants configured but isolation required, 
            # allow only the configured tenant
            return user_tenant_id == config.aad_groups.tenant_id
        
        # Check if user's tenant is in allowed list
        is_allowed = user_tenant_id in allowed_tenants
        
        logger.info(
            "Tenant isolation check",
            extra={
                "user_tenant_id": user_tenant_id,
                "allowed_tenants": allowed_tenants,
                "is_allowed": is_allowed,
                "correlation_id": self.correlation_id
            }
        )
        
        return is_allowed

    async def get_user_groups(self, user_email: str, user_tenant_id: Optional[str] = None) -> List[GroupMembership]:
        """
        Get user's group memberships from Microsoft Graph API
        
        Args:
            user_email: User's email address
            user_tenant_id: User's tenant ID for isolation validation
            
        Returns:
            List of group memberships
        """
        if not config.is_aad_groups_enabled():
            logger.debug("AAD groups not enabled, returning empty groups", extra={"correlation_id": self.correlation_id})
            return []
        
        # Validate tenant isolation if required
        if user_tenant_id and not self.validate_tenant_isolation(user_tenant_id):
            logger.warning(
                "User tenant not allowed",
                extra={"user_email": user_email, "user_tenant_id": user_tenant_id, "correlation_id": self.correlation_id}
            )
            return []
        
        # Use unified cache if enabled, otherwise fall back to legacy cache
        if config.cache.enabled:
            return await self._get_user_groups_cached(user_email)
        else:
            return await self._get_user_groups_legacy_cache(user_email)

    async def _get_user_groups_cached(self, user_email: str) -> List[GroupMembership]:
        """Get user groups using unified cache system"""
        async def fetch_groups():
            groups = await self._fetch_user_groups_from_graph(user_email)
            # Convert to serializable format for caching
            return [
                {
                    "group_id": g.group_id,
                    "group_name": g.group_name,
                    "tenant_id": g.tenant_id,
                    "fetched_at": g.fetched_at.isoformat()
                }
                for g in groups
            ]
        
        try:
            cached_data = await get_cached(
                cache_name=self.cache_name,
                key=f"groups_{user_email}",
                factory=fetch_groups,
                ttl_seconds=self.cache_config["default_ttl_seconds"],
                **self.cache_config
            )
            
            # Convert back to GroupMembership objects
            groups = [
                GroupMembership(
                    group_id=item["group_id"],
                    group_name=item["group_name"],
                    tenant_id=item["tenant_id"],
                    fetched_at=datetime.fromisoformat(item["fetched_at"])
                )
                for item in cached_data
            ]
            
            logger.info(
                "Retrieved user groups (unified cache)",
                extra={
                    "user_email": user_email,
                    "group_count": len(groups),
                    "correlation_id": self.correlation_id
                }
            )
            
            return groups
            
        except Exception as e:
            logger.error(
                "Failed to fetch user groups (unified cache)",
                extra={"user_email": user_email, "error": str(e), "correlation_id": self.correlation_id}
            )
            return []
    
    async def _get_user_groups_legacy_cache(self, user_email: str) -> List[GroupMembership]:
        """Get user groups using legacy TTL cache"""
        # Check cache first
        cache_key = f"groups:{user_email}"
        cached_groups = self._legacy_cache.get(cache_key)
        if cached_groups:
            logger.debug(
                "Returning cached group memberships (legacy)",
                extra={"user_email": user_email, "group_count": len(cached_groups), "correlation_id": self.correlation_id}
            )
            return cached_groups
        
        # Fetch from Microsoft Graph API
        try:
            groups = await self._fetch_user_groups_from_graph(user_email)
            
            # Cache the results
            self._legacy_cache[cache_key] = groups
            
            logger.info(
                "Fetched user groups from Microsoft Graph (legacy cache)",
                extra={
                    "user_email": user_email,
                    "group_count": len(groups),
                    "cache_ttl_minutes": config.aad_groups.cache_ttl_minutes,
                    "correlation_id": self.correlation_id
                }
            )
            
            return groups
            
        except Exception as e:
            logger.error(
                "Failed to fetch user groups (legacy cache)",
                extra={"user_email": user_email, "error": str(e), "correlation_id": self.correlation_id}
            )
            return []

    async def _fetch_user_groups_from_graph(self, user_email: str) -> List[GroupMembership]:
        """
        Fetch user groups from Microsoft Graph API
        
        Args:
            user_email: User's email address
            
        Returns:
            List of group memberships
        """
        access_token = self._get_access_token()
        if not access_token:
            raise Exception("Failed to get access token for Microsoft Graph")
        
        import aiohttp
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Query user's group memberships
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/memberOf"
        
        groups = []
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for item in data.get("value", []):
                        # Filter for security groups only
                        if item.get("@odata.type") == "#microsoft.graph.group":
                            group = GroupMembership(
                                group_id=item.get("id", ""),
                                group_name=item.get("displayName", ""),
                                tenant_id=config.aad_groups.tenant_id,
                                fetched_at=datetime.utcnow()
                            )
                            groups.append(group)
                
                elif response.status == 404:
                    logger.warning(
                        "User not found in Microsoft Graph",
                        extra={"user_email": user_email, "correlation_id": self.correlation_id}
                    )
                else:
                    error_text = await response.text()
                    raise Exception(f"Microsoft Graph API error {response.status}: {error_text}")
        
        return groups

    def map_groups_to_roles(self, groups: List[GroupMembership]) -> Set[str]:
        """
        Map group memberships to application roles
        
        Args:
            groups: List of group memberships
            
        Returns:
            Set of role names
        """
        roles = set()
        
        for group in groups:
            role = self._group_roles_map.get(group.group_id)
            if role:
                roles.add(role)
                logger.debug(
                    "Mapped group to role",
                    extra={
                        "group_id": group.group_id,
                        "group_name": group.group_name,
                        "role": role,
                        "correlation_id": self.correlation_id
                    }
                )
        
        logger.info(
            "Completed group to role mapping",
            extra={
                "total_groups": len(groups),
                "mapped_roles": list(roles),
                "role_count": len(roles),
                "correlation_id": self.correlation_id
            }
        )
        
        return roles

    async def get_user_roles(self, user_email: str, user_tenant_id: Optional[str] = None) -> UserRoles:
        """
        Get user's effective roles based on group memberships
        
        Args:
            user_email: User's email address
            user_tenant_id: User's tenant ID for isolation validation
            
        Returns:
            UserRoles object with groups, roles, and admin status
        """
        # Get group memberships
        groups = await self.get_user_groups(user_email, user_tenant_id)
        
        # Map groups to roles
        roles = self.map_groups_to_roles(groups)
        
        # Check admin status (from groups or email-based admin list)
        from api.security import is_admin as is_email_admin
        is_admin = is_email_admin(user_email) or "admin" in roles
        
        user_roles = UserRoles(
            user_email=user_email,
            tenant_id=user_tenant_id or config.aad_groups.tenant_id,
            groups=groups,
            roles=roles,
            is_admin=is_admin,
            fetched_at=datetime.utcnow()
        )
        
        logger.info(
            "Determined user roles",
            extra={
                "user_email": user_email,
                "group_count": len(groups),
                "roles": list(roles),
                "is_admin": is_admin,
                "correlation_id": self.correlation_id
            }
        )
        
        return user_roles

    async def clear_cache(self, user_email: Optional[str] = None) -> None:
        """
        Clear group membership cache
        
        Args:
            user_email: If provided, clear cache for specific user only
        """
        if user_email:
            # Clear from both unified cache and legacy cache
            if config.cache.enabled:
                await invalidate_cache_key(self.cache_name, f"groups_{user_email}")
            
            cache_key = f"groups:{user_email}"
            self._legacy_cache.pop(cache_key, None)
            
            logger.info(
                "Cleared cache for user",
                extra={"user_email": user_email, "correlation_id": self.correlation_id}
            )
        else:
            # Clear all caches
            if config.cache.enabled:
                cache = cache_manager.get_cache(self.cache_name, **self.cache_config)
                await cache.clear()
            
            self._legacy_cache.clear()
            logger.info("Cleared all AAD groups cache", extra={"correlation_id": self.correlation_id})

    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics"""
        stats = {
            "legacy_cache": {
                "current_size": len(self._legacy_cache),
                "max_size": self._legacy_cache.maxsize,
                "ttl_seconds": self._legacy_cache.ttl,
                "hits": getattr(self._legacy_cache, 'hits', 0),
                "misses": getattr(self._legacy_cache, 'misses', 0)
            }
        }
        
        # Add unified cache stats if enabled
        if config.cache.enabled:
            try:
                cache = cache_manager.get_cache(self.cache_name, **self.cache_config)
                stats["unified_cache"] = cache.get_metrics()
            except Exception as e:
                stats["unified_cache"] = {"error": str(e)}
        
        return stats

    def is_operational(self) -> bool:
        """Check if AAD groups service is operational"""
        if not config.is_aad_groups_enabled():
            return False
        
        return (
            self._msal_client is not None
            and bool(self._group_roles_map)
        )

    def get_status(self) -> Dict[str, any]:
        """Get comprehensive service status for monitoring"""
        return {
            "enabled": config.aad_groups.enabled,
            "operational": self.is_operational(),
            "configuration": {
                "tenant_id": config.aad_groups.tenant_id,
                "client_configured": bool(config.aad_groups.client_id),
                "cache_ttl_minutes": config.aad_groups.cache_ttl_minutes,
                "require_tenant_isolation": config.aad_groups.require_tenant_isolation,
                "group_mapping_count": len(self._group_roles_map)
            },
            "cache_stats": self.get_cache_stats(),
            "group_role_mappings": self._group_roles_map,
            "timestamp": datetime.utcnow().isoformat()
        }


def create_aad_groups_service(correlation_id: str = "aad-groups") -> AADGroupsService:
    """
    Factory function to create AAD Groups Service instance
    
    Args:
        correlation_id: Correlation ID for request tracking
        
    Returns:
        AADGroupsService instance
    """
    return AADGroupsService(correlation_id=correlation_id)