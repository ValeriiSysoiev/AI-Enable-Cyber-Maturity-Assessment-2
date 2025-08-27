"""
Framework Metadata Caching Service

Provides caching for framework metadata including:
- Security frameworks (NIST, ISO 27001, etc.)
- Compliance standards metadata
- Assessment framework schemas
- Framework scoring matrices
"""

import logging
from typing import Any, Dict, List, Optional
from services.cache import get_cached, invalidate_cache_key, cache_manager
import sys
sys.path.append("/app")
from config import config

logger = logging.getLogger(__name__)


class FrameworkCacheService:
    """Service for caching framework metadata and schemas"""
    
    CACHE_NAME = "framework_metadata"
    
    def __init__(self):
        self.cache_config = {
            "max_size_mb": config.cache.framework_max_size_mb,
            "max_entries": config.cache.framework_max_entries,
            "default_ttl_seconds": config.cache.framework_ttl_seconds,
            "cleanup_interval_seconds": config.cache.cleanup_interval_seconds
        }
    
    async def get_framework_metadata(self, framework_id: str) -> Optional[Dict[str, Any]]:
        """Get cached framework metadata"""
        if not config.cache.enabled:
            return await self._load_framework_metadata_uncached(framework_id)
        
        async def compute_metadata():
            return await self._load_framework_metadata_uncached(framework_id)
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key=f"framework_{framework_id}",
            factory=compute_metadata,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def get_framework_schemas(self, framework_id: str) -> Optional[Dict[str, Any]]:
        """Get cached framework schemas"""
        if not config.cache.enabled:
            return await self._load_framework_schemas_uncached(framework_id)
        
        async def compute_schemas():
            return await self._load_framework_schemas_uncached(framework_id)
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key=f"schemas_{framework_id}",
            factory=compute_schemas,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def get_scoring_matrix(self, framework_id: str) -> Optional[Dict[str, Any]]:
        """Get cached scoring matrix for framework"""
        if not config.cache.enabled:
            return await self._load_scoring_matrix_uncached(framework_id)
        
        async def compute_matrix():
            return await self._load_scoring_matrix_uncached(framework_id)
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key=f"scoring_{framework_id}",
            factory=compute_matrix,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def list_available_frameworks(self) -> List[Dict[str, Any]]:
        """Get cached list of available frameworks"""
        if not config.cache.enabled:
            return await self._load_frameworks_list_uncached()
        
        async def compute_frameworks():
            return await self._load_frameworks_list_uncached()
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key="frameworks_list",
            factory=compute_frameworks,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def get_framework_capabilities(self, framework_id: str) -> Optional[Dict[str, Any]]:
        """Get cached framework capabilities mapping"""
        if not config.cache.enabled:
            return await self._load_framework_capabilities_uncached(framework_id)
        
        async def compute_capabilities():
            return await self._load_framework_capabilities_uncached(framework_id)
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key=f"capabilities_{framework_id}",
            factory=compute_capabilities,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def invalidate_framework_cache(self, framework_id: str) -> None:
        """Invalidate all cache entries for a specific framework"""
        if not config.cache.enabled:
            return
        
        cache_keys = [
            f"framework_{framework_id}",
            f"schemas_{framework_id}",
            f"scoring_{framework_id}",
            f"capabilities_{framework_id}",
            "frameworks_list"  # List needs refresh when individual framework changes
        ]
        
        for key in cache_keys:
            await invalidate_cache_key(self.CACHE_NAME, key)
        
        logger.info(
            f"Invalidated framework cache for {framework_id}",
            extra={
                "framework_id": framework_id,
                "invalidated_keys": len(cache_keys)
            }
        )
    
    async def invalidate_all_framework_cache(self) -> None:
        """Invalidate all framework cache entries"""
        if not config.cache.enabled:
            return
        
        cache = cache_manager.get_cache(self.CACHE_NAME, **self.cache_config)
        await cache.clear()
        
        logger.info("Invalidated all framework cache entries")
    
    async def _load_framework_metadata_uncached(self, framework_id: str) -> Optional[Dict[str, Any]]:
        """Load framework metadata without caching - implement actual loading logic"""
        # This is a placeholder implementation
        # In a real system, this would load from database, file system, or external API
        
        framework_metadata = {
            "nist-csf": {
                "id": "nist-csf",
                "name": "NIST Cybersecurity Framework",
                "version": "1.1",
                "description": "Framework for improving critical infrastructure cybersecurity",
                "categories": ["Identify", "Protect", "Detect", "Respond", "Recover"],
                "total_controls": 108,
                "last_updated": "2018-04-16"
            },
            "iso-27001": {
                "id": "iso-27001",
                "name": "ISO/IEC 27001",
                "version": "2013",
                "description": "Information security management systems requirements",
                "categories": ["A.5", "A.6", "A.7", "A.8", "A.9", "A.10", "A.11", "A.12", "A.13", "A.14", "A.15", "A.16", "A.17", "A.18"],
                "total_controls": 114,
                "last_updated": "2013-10-01"
            },
            "cscm-v3": {
                "id": "cscm-v3",
                "name": "Cyber Security Capability Maturity Model v3",
                "version": "3.0",
                "description": "Comprehensive cybersecurity maturity assessment framework",
                "categories": ["Governance", "Risk Management", "Asset Management", "Incident Response", "Business Continuity"],
                "total_controls": 156,
                "last_updated": "2024-01-01"
            }
        }
        
        result = framework_metadata.get(framework_id)
        if result:
            logger.debug(
                f"Loaded framework metadata for {framework_id}",
                extra={"framework_id": framework_id, "controls_count": result.get("total_controls")}
            )
        
        return result
    
    async def _load_framework_schemas_uncached(self, framework_id: str) -> Optional[Dict[str, Any]]:
        """Load framework schemas without caching"""
        # Placeholder implementation
        schemas = {
            "nist-csf": {
                "assessment_schema": {
                    "type": "object",
                    "properties": {
                        "identify": {"type": "object"},
                        "protect": {"type": "object"},
                        "detect": {"type": "object"},
                        "respond": {"type": "object"},
                        "recover": {"type": "object"}
                    }
                },
                "scoring_schema": {
                    "levels": ["Not Implemented", "Partially Implemented", "Fully Implemented"],
                    "weights": {"identify": 0.2, "protect": 0.3, "detect": 0.2, "respond": 0.15, "recover": 0.15}
                }
            },
            "cscm-v3": {
                "assessment_schema": {
                    "type": "object",
                    "properties": {
                        "governance": {"type": "object"},
                        "risk_management": {"type": "object"},
                        "asset_management": {"type": "object"},
                        "incident_response": {"type": "object"},
                        "business_continuity": {"type": "object"}
                    }
                },
                "scoring_schema": {
                    "levels": ["Initial", "Developing", "Defined", "Managed", "Optimizing"],
                    "weights": {"governance": 0.25, "risk_management": 0.2, "asset_management": 0.2, "incident_response": 0.2, "business_continuity": 0.15}
                }
            }
        }
        
        result = schemas.get(framework_id)
        if result:
            logger.debug(
                f"Loaded framework schemas for {framework_id}",
                extra={"framework_id": framework_id, "schema_keys": list(result.keys())}
            )
        
        return result
    
    async def _load_scoring_matrix_uncached(self, framework_id: str) -> Optional[Dict[str, Any]]:
        """Load scoring matrix without caching"""
        # Placeholder implementation
        scoring_matrices = {
            "nist-csf": {
                "scoring_method": "weighted_average",
                "level_scores": {
                    "Not Implemented": 0,
                    "Partially Implemented": 2,
                    "Fully Implemented": 4
                },
                "category_weights": {
                    "identify": 0.2,
                    "protect": 0.3,
                    "detect": 0.2,
                    "respond": 0.15,
                    "recover": 0.15
                },
                "gates": {
                    "minimum_protect_score": 2.0,
                    "minimum_detect_score": 1.5
                }
            },
            "cscm-v3": {
                "scoring_method": "maturity_levels",
                "level_scores": {
                    "Initial": 1,
                    "Developing": 2,
                    "Defined": 3,
                    "Managed": 4,
                    "Optimizing": 5
                },
                "category_weights": {
                    "governance": 0.25,
                    "risk_management": 0.2,
                    "asset_management": 0.2,
                    "incident_response": 0.2,
                    "business_continuity": 0.15
                },
                "gates": {
                    "minimum_governance_level": 2,
                    "minimum_overall_score": 2.5
                }
            }
        }
        
        result = scoring_matrices.get(framework_id)
        if result:
            logger.debug(
                f"Loaded scoring matrix for {framework_id}",
                extra={"framework_id": framework_id, "scoring_method": result.get("scoring_method")}
            )
        
        return result
    
    async def _load_frameworks_list_uncached(self) -> List[Dict[str, Any]]:
        """Load list of available frameworks without caching"""
        # In a real system, this would query the database or configuration
        frameworks = [
            {
                "id": "nist-csf",
                "name": "NIST Cybersecurity Framework",
                "version": "1.1",
                "description": "Framework for improving critical infrastructure cybersecurity",
                "status": "active",
                "supported_versions": ["1.0", "1.1"]
            },
            {
                "id": "iso-27001",
                "name": "ISO/IEC 27001",
                "version": "2013",
                "description": "Information security management systems requirements",
                "status": "active",
                "supported_versions": ["2005", "2013"]
            },
            {
                "id": "cscm-v3",
                "name": "Cyber Security Capability Maturity Model v3",
                "version": "3.0",
                "description": "Comprehensive cybersecurity maturity assessment framework",
                "status": "active",
                "supported_versions": ["2.0", "3.0"]
            }
        ]
        
        logger.debug(
            f"Loaded {len(frameworks)} available frameworks",
            extra={"frameworks_count": len(frameworks)}
        )
        
        return frameworks
    
    async def _load_framework_capabilities_uncached(self, framework_id: str) -> Optional[Dict[str, Any]]:
        """Load framework capabilities mapping without caching"""
        # Placeholder implementation
        capabilities = {
            "nist-csf": {
                "identify": {
                    "asset_management": ["ID.AM-1", "ID.AM-2", "ID.AM-3"],
                    "business_environment": ["ID.BE-1", "ID.BE-2", "ID.BE-3"],
                    "governance": ["ID.GV-1", "ID.GV-2", "ID.GV-3"],
                    "risk_assessment": ["ID.RA-1", "ID.RA-2", "ID.RA-3"],
                    "risk_management": ["ID.RM-1", "ID.RM-2", "ID.RM-3"],
                    "supply_chain": ["ID.SC-1", "ID.SC-2", "ID.SC-3"]
                },
                "protect": {
                    "identity_management": ["PR.AC-1", "PR.AC-2", "PR.AC-3"],
                    "awareness_training": ["PR.AT-1", "PR.AT-2", "PR.AT-3"],
                    "data_security": ["PR.DS-1", "PR.DS-2", "PR.DS-3"],
                    "info_protection": ["PR.IP-1", "PR.IP-2", "PR.IP-3"],
                    "maintenance": ["PR.MA-1", "PR.MA-2", "PR.MA-3"],
                    "protective_technology": ["PR.PT-1", "PR.PT-2", "PR.PT-3"]
                }
            },
            "cscm-v3": {
                "governance": {
                    "cybersecurity_strategy": ["GOV-001", "GOV-002", "GOV-003"],
                    "risk_governance": ["GOV-004", "GOV-005", "GOV-006"],
                    "compliance_management": ["GOV-007", "GOV-008", "GOV-009"]
                },
                "risk_management": {
                    "risk_identification": ["RISK-001", "RISK-002", "RISK-003"],
                    "risk_assessment": ["RISK-004", "RISK-005", "RISK-006"],
                    "risk_treatment": ["RISK-007", "RISK-008", "RISK-009"]
                }
            }
        }
        
        result = capabilities.get(framework_id)
        if result:
            total_capabilities = sum(len(controls) for category in result.values() for controls in category.values())
            logger.debug(
                f"Loaded framework capabilities for {framework_id}",
                extra={"framework_id": framework_id, "total_capabilities": total_capabilities}
            )
        
        return result


# Global instance
framework_cache_service = FrameworkCacheService()


# Convenience functions
async def get_framework_metadata(framework_id: str) -> Optional[Dict[str, Any]]:
    """Get framework metadata with caching"""
    return await framework_cache_service.get_framework_metadata(framework_id)


async def get_framework_schemas(framework_id: str) -> Optional[Dict[str, Any]]:
    """Get framework schemas with caching"""
    return await framework_cache_service.get_framework_schemas(framework_id)


async def get_scoring_matrix(framework_id: str) -> Optional[Dict[str, Any]]:
    """Get scoring matrix with caching"""
    return await framework_cache_service.get_scoring_matrix(framework_id)


async def list_available_frameworks() -> List[Dict[str, Any]]:
    """List available frameworks with caching"""
    return await framework_cache_service.list_available_frameworks()


async def invalidate_framework_cache(framework_id: str) -> None:
    """Invalidate cache for specific framework"""
    await framework_cache_service.invalidate_framework_cache(framework_id)