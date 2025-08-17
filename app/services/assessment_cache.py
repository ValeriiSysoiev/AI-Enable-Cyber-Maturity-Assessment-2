"""
Assessment Schemas Caching Service

Provides caching for assessment-related data including:
- Assessment schemas and templates
- Question sets and validation rules
- Scoring algorithms and matrices
- Assessment metadata and configurations
"""

import logging
from typing import Any, Dict, List, Optional
from ..api.schemas.assessment import AssessmentPreset
from .cache import get_cached, invalidate_cache_key, cache_manager
from ..config import config

logger = logging.getLogger(__name__)


class AssessmentCacheService:
    """Service for caching assessment schemas and related data"""
    
    CACHE_NAME = "assessment_schemas"
    
    def __init__(self):
        self.cache_config = {
            "max_size_mb": config.cache.assessment_schemas_max_size_mb,
            "max_entries": config.cache.assessment_schemas_max_entries,
            "default_ttl_seconds": config.cache.assessment_schemas_ttl_seconds,
            "cleanup_interval_seconds": config.cache.cleanup_interval_seconds
        }
    
    async def get_assessment_schema(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """Get cached assessment schema for a specific preset"""
        if not config.cache.enabled:
            return await self._load_assessment_schema_uncached(preset_id)
        
        async def compute_schema():
            return await self._load_assessment_schema_uncached(preset_id)
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key=f"schema_{preset_id}",
            factory=compute_schema,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def get_question_set(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """Get cached question set for a specific preset"""
        if not config.cache.enabled:
            return await self._load_question_set_uncached(preset_id)
        
        async def compute_questions():
            return await self._load_question_set_uncached(preset_id)
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key=f"questions_{preset_id}",
            factory=compute_questions,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def get_scoring_algorithm(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """Get cached scoring algorithm for a specific preset"""
        if not config.cache.enabled:
            return await self._load_scoring_algorithm_uncached(preset_id)
        
        async def compute_scoring():
            return await self._load_scoring_algorithm_uncached(preset_id)
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key=f"scoring_{preset_id}",
            factory=compute_scoring,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def get_validation_rules(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """Get cached validation rules for a specific preset"""
        if not config.cache.enabled:
            return await self._load_validation_rules_uncached(preset_id)
        
        async def compute_validation():
            return await self._load_validation_rules_uncached(preset_id)
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key=f"validation_{preset_id}",
            factory=compute_validation,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def get_assessment_template(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """Get cached assessment template for a specific preset"""
        if not config.cache.enabled:
            return await self._load_assessment_template_uncached(preset_id)
        
        async def compute_template():
            return await self._load_assessment_template_uncached(preset_id)
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key=f"template_{preset_id}",
            factory=compute_template,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def get_assessment_metadata(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        """Get cached assessment metadata"""
        if not config.cache.enabled:
            return await self._load_assessment_metadata_uncached(assessment_id)
        
        async def compute_metadata():
            return await self._load_assessment_metadata_uncached(assessment_id)
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key=f"metadata_{assessment_id}",
            factory=compute_metadata,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def list_available_presets(self) -> List[Dict[str, Any]]:
        """Get cached list of available assessment presets"""
        if not config.cache.enabled:
            return await self._load_presets_list_uncached()
        
        async def compute_presets():
            return await self._load_presets_list_uncached()
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key="presets_list",
            factory=compute_presets,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def invalidate_preset_cache(self, preset_id: str) -> None:
        """Invalidate all cache entries for a specific preset"""
        if not config.cache.enabled:
            return
        
        cache_keys = [
            f"schema_{preset_id}",
            f"questions_{preset_id}",
            f"scoring_{preset_id}",
            f"validation_{preset_id}",
            f"template_{preset_id}",
            "presets_list"  # List needs refresh when individual preset changes
        ]
        
        for key in cache_keys:
            await invalidate_cache_key(self.CACHE_NAME, key)
        
        logger.info(
            f"Invalidated assessment cache for preset {preset_id}",
            extra={
                "preset_id": preset_id,
                "invalidated_keys": len(cache_keys)
            }
        )
    
    async def invalidate_assessment_cache(self, assessment_id: str) -> None:
        """Invalidate cache entries for a specific assessment"""
        if not config.cache.enabled:
            return
        
        await invalidate_cache_key(self.CACHE_NAME, f"metadata_{assessment_id}")
        
        logger.info(
            f"Invalidated assessment cache for {assessment_id}",
            extra={"assessment_id": assessment_id}
        )
    
    async def invalidate_all_assessment_cache(self) -> None:
        """Invalidate all assessment cache entries"""
        if not config.cache.enabled:
            return
        
        cache = cache_manager.get_cache(self.CACHE_NAME, **self.cache_config)
        await cache.clear()
        
        logger.info("Invalidated all assessment cache entries")
    
    async def _load_assessment_schema_uncached(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """Load assessment schema without caching"""
        # This would integrate with the presets service and domain models
        from ..services.presets import _get_preset_uncached
        
        try:
            preset = _get_preset_uncached(preset_id)
            if not preset:
                return None
            
            # Extract schema from preset
            schema = {
                "id": preset.id,
                "name": preset.name,
                "version": preset.version,
                "schema_version": "1.0",
                "pillars": [
                    {
                        "id": pillar.id,
                        "name": pillar.name,
                        "description": pillar.description,
                        "weight": pillar.weight,
                        "capability_count": len(pillar.capabilities)
                    }
                    for pillar in preset.pillars
                ],
                "scoring_config": {
                    "levels": ["Not Implemented", "Partially Implemented", "Fully Implemented"],
                    "score_mapping": {
                        "Not Implemented": 0,
                        "Partially Implemented": 2,
                        "Fully Implemented": 4
                    },
                    "gates": preset.gates if hasattr(preset, 'gates') else {}
                }
            }
            
            logger.debug(
                f"Loaded assessment schema for {preset_id}",
                extra={
                    "preset_id": preset_id,
                    "pillars_count": len(schema["pillars"])
                }
            )
            
            return schema
            
        except Exception as e:
            logger.error(
                f"Failed to load assessment schema for {preset_id}",
                extra={"preset_id": preset_id, "error": str(e)}
            )
            return None
    
    async def _load_question_set_uncached(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """Load question set without caching"""
        from ..services.presets import _get_preset_uncached
        
        try:
            preset = _get_preset_uncached(preset_id)
            if not preset:
                return None
            
            # Extract questions from preset
            questions = {
                "preset_id": preset.id,
                "total_questions": 0,
                "questions_by_pillar": {}
            }
            
            total_questions = 0
            for pillar in preset.pillars:
                pillar_questions = []
                for capability in pillar.capabilities:
                    for question in capability.questions:
                        pillar_questions.append({
                            "id": question.id,
                            "text": question.text,
                            "capability_id": capability.id,
                            "capability_name": capability.name,
                            "guidance": getattr(question, 'guidance', ''),
                            "references": getattr(question, 'references', [])
                        })
                        total_questions += 1
                
                questions["questions_by_pillar"][pillar.id] = {
                    "pillar_name": pillar.name,
                    "questions": pillar_questions
                }
            
            questions["total_questions"] = total_questions
            
            logger.debug(
                f"Loaded question set for {preset_id}",
                extra={
                    "preset_id": preset_id,
                    "total_questions": total_questions
                }
            )
            
            return questions
            
        except Exception as e:
            logger.error(
                f"Failed to load question set for {preset_id}",
                extra={"preset_id": preset_id, "error": str(e)}
            )
            return None
    
    async def _load_scoring_algorithm_uncached(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """Load scoring algorithm without caching"""
        from ..services.presets import _get_preset_uncached
        
        try:
            preset = _get_preset_uncached(preset_id)
            if not preset:
                return None
            
            # Extract scoring configuration
            scoring = {
                "preset_id": preset.id,
                "algorithm_type": "weighted_average",
                "pillar_weights": {
                    pillar.id: pillar.weight
                    for pillar in preset.pillars
                },
                "level_scores": {
                    "Not Implemented": 0,
                    "Partially Implemented": 2,
                    "Fully Implemented": 4
                },
                "gates": getattr(preset, 'gates', {}),
                "score_ranges": {
                    "low": {"min": 0, "max": 1.5},
                    "medium": {"min": 1.5, "max": 3.0},
                    "high": {"min": 3.0, "max": 4.0}
                }
            }
            
            logger.debug(
                f"Loaded scoring algorithm for {preset_id}",
                extra={
                    "preset_id": preset_id,
                    "algorithm_type": scoring["algorithm_type"],
                    "pillar_count": len(scoring["pillar_weights"])
                }
            )
            
            return scoring
            
        except Exception as e:
            logger.error(
                f"Failed to load scoring algorithm for {preset_id}",
                extra={"preset_id": preset_id, "error": str(e)}
            )
            return None
    
    async def _load_validation_rules_uncached(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """Load validation rules without caching"""
        # Placeholder implementation - would load from preset configuration
        validation_rules = {
            "preset_id": preset_id,
            "required_fields": ["preset_id", "engagement_id", "created_by"],
            "pillar_validation": {
                "min_pillars": 1,
                "max_pillars": 10,
                "required_fields": ["id", "name", "weight"]
            },
            "question_validation": {
                "min_questions_per_capability": 1,
                "max_questions_per_capability": 20,
                "required_fields": ["id", "text"]
            },
            "response_validation": {
                "valid_levels": ["Not Implemented", "Partially Implemented", "Fully Implemented"],
                "max_notes_length": 2000
            },
            "business_rules": {
                "require_all_questions_answered": False,
                "allow_partial_assessments": True,
                "minimum_completion_percentage": 0.0
            }
        }
        
        logger.debug(
            f"Loaded validation rules for {preset_id}",
            extra={"preset_id": preset_id}
        )
        
        return validation_rules
    
    async def _load_assessment_template_uncached(self, preset_id: str) -> Optional[Dict[str, Any]]:
        """Load assessment template without caching"""
        from ..services.presets import _get_preset_uncached
        
        try:
            preset = _get_preset_uncached(preset_id)
            if not preset:
                return None
            
            # Create assessment template
            template = {
                "preset_id": preset.id,
                "template_version": "1.0",
                "name": f"Assessment Template - {preset.name}",
                "description": f"Template for {preset.name} assessments",
                "structure": {
                    "metadata": {
                        "required_fields": ["name", "engagement_id", "created_by"],
                        "optional_fields": ["description", "notes"]
                    },
                    "pillars": [
                        {
                            "id": pillar.id,
                            "name": pillar.name,
                            "description": pillar.description,
                            "weight": pillar.weight,
                            "capabilities": [
                                {
                                    "id": capability.id,
                                    "name": capability.name,
                                    "description": capability.description,
                                    "question_count": len(capability.questions)
                                }
                                for capability in pillar.capabilities
                            ]
                        }
                        for pillar in preset.pillars
                    ]
                },
                "default_values": {
                    "status": "draft",
                    "completion_percentage": 0.0,
                    "score": None
                }
            }
            
            logger.debug(
                f"Loaded assessment template for {preset_id}",
                extra={
                    "preset_id": preset_id,
                    "template_version": template["template_version"]
                }
            )
            
            return template
            
        except Exception as e:
            logger.error(
                f"Failed to load assessment template for {preset_id}",
                extra={"preset_id": preset_id, "error": str(e)}
            )
            return None
    
    async def _load_assessment_metadata_uncached(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        """Load assessment metadata without caching"""
        # This would integrate with the repository layer
        # Placeholder implementation
        metadata = {
            "assessment_id": assessment_id,
            "status": "active",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "completion_percentage": 0.0,
            "total_questions": 0,
            "answered_questions": 0,
            "last_activity": "2024-01-01T00:00:00Z"
        }
        
        logger.debug(
            f"Loaded assessment metadata for {assessment_id}",
            extra={"assessment_id": assessment_id}
        )
        
        return metadata
    
    async def _load_presets_list_uncached(self) -> List[Dict[str, Any]]:
        """Load list of available presets without caching"""
        from ..services.presets import _list_presets_uncached
        
        try:
            presets = _list_presets_uncached()
            
            logger.debug(
                f"Loaded {len(presets)} assessment presets",
                extra={"presets_count": len(presets)}
            )
            
            return presets
            
        except Exception as e:
            logger.error(
                f"Failed to load presets list",
                extra={"error": str(e)}
            )
            return []


# Global instance
assessment_cache_service = AssessmentCacheService()


# Convenience functions
async def get_assessment_schema(preset_id: str) -> Optional[Dict[str, Any]]:
    """Get assessment schema with caching"""
    return await assessment_cache_service.get_assessment_schema(preset_id)


async def get_question_set(preset_id: str) -> Optional[Dict[str, Any]]:
    """Get question set with caching"""
    return await assessment_cache_service.get_question_set(preset_id)


async def get_scoring_algorithm(preset_id: str) -> Optional[Dict[str, Any]]:
    """Get scoring algorithm with caching"""
    return await assessment_cache_service.get_scoring_algorithm(preset_id)


async def get_validation_rules(preset_id: str) -> Optional[Dict[str, Any]]:
    """Get validation rules with caching"""
    return await assessment_cache_service.get_validation_rules(preset_id)


async def invalidate_preset_cache(preset_id: str) -> None:
    """Invalidate cache for specific preset"""
    await assessment_cache_service.invalidate_preset_cache(preset_id)


async def invalidate_assessment_cache(assessment_id: str) -> None:
    """Invalidate cache for specific assessment"""
    await assessment_cache_service.invalidate_assessment_cache(assessment_id)