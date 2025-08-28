"""Roadmap prioritization service with composite scoring algorithm"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json
from api.schemas.roadmap import (
    ScoringWeights, InitiativeScoring, CompositeScore, 
    InitiativePrioritization, PrioritizationRequest, PrioritizationResponse
)

logger = logging.getLogger(__name__)


class RoadmapPrioritizationService:
    """Service for roadmap initiative prioritization using composite scoring"""
    
    def __init__(self):
        self._default_weights = ScoringWeights()
        self._current_weights = ScoringWeights()
        self._weights_description = "Default weights configuration"
        self._weights_last_updated = datetime.utcnow()
        self._weights_updated_by = "system"
    
    def calculate_composite_score(
        self, 
        scoring: InitiativeScoring, 
        weights: Optional[ScoringWeights] = None
    ) -> CompositeScore:
        """
        Calculate composite score using the formula:
        score = (impact * w_impact) + (risk * w_risk) + ((10 - effort) * w_effort) + 
                (compliance * w_compliance) - (dependency_count * w_penalty)
        
        Args:
            scoring: Individual scoring components
            weights: Optional custom weights (uses current config if not provided)
            
        Returns:
            CompositeScore with breakdown of calculation
        """
        if weights is None:
            weights = self._current_weights
            
        # Calculate weighted components
        weighted_impact = scoring.impact_score * weights.impact
        weighted_risk = scoring.risk_score * weights.risk
        # Invert effort score (higher effort = lower priority)
        weighted_effort = (10.0 - scoring.effort_score) * weights.effort
        weighted_compliance = scoring.compliance_score * weights.compliance
        
        # Calculate dependency penalty (linear penalty per dependency)
        dependency_penalty = scoring.dependency_count * weights.dependency_penalty
        
        # Calculate total score
        total_score = (
            weighted_impact + 
            weighted_risk + 
            weighted_effort + 
            weighted_compliance - 
            dependency_penalty
        )
        
        # Ensure score is within bounds [0, 10]
        total_score = max(0.0, min(10.0, total_score))
        
        logger.info(
            f"Calculated composite score: {total_score:.2f}",
            extra={
                "impact": weighted_impact,
                "risk": weighted_risk,
                "effort": weighted_effort,
                "compliance": weighted_compliance,
                "dependency_penalty": dependency_penalty,
                "total_score": total_score
            }
        )
        
        return CompositeScore(
            total_score=total_score,
            weighted_impact=weighted_impact,
            weighted_risk=weighted_risk,
            weighted_effort=weighted_effort,
            weighted_compliance=weighted_compliance,
            dependency_penalty=dependency_penalty,
            weights_used=weights
        )
    
    def prioritize_initiatives(
        self, 
        request: PrioritizationRequest
    ) -> PrioritizationResponse:
        """
        Prioritize a list of initiatives using composite scoring
        
        Args:
            request: Prioritization request with initiatives and optional weights
            
        Returns:
            PrioritizationResponse with sorted initiatives
        """
        if len(request.initiatives) != len(request.initiative_ids):
            raise ValueError("Number of initiatives must match number of initiative IDs")
        
        weights = request.weights if request.weights else self._current_weights
        
        # Calculate scores for all initiatives
        scored_initiatives = []
        for i, (initiative_id, scoring) in enumerate(zip(request.initiative_ids, request.initiatives)):
            composite_score = self.calculate_composite_score(scoring, weights)
            
            prioritization = InitiativePrioritization(
                initiative_id=initiative_id,
                name=f"Initiative {initiative_id}",  # Would come from database in real implementation
                description=f"Initiative {initiative_id} description",
                scoring=scoring,
                composite_score=composite_score,
                priority_rank=None  # Will be set after sorting
            )
            scored_initiatives.append(prioritization)
        
        # Sort by composite score (descending)
        scored_initiatives.sort(key=lambda x: x.composite_score.total_score, reverse=True)
        
        # Assign priority ranks
        for rank, initiative in enumerate(scored_initiatives, 1):
            initiative.priority_rank = rank
        
        logger.info(
            f"Prioritized {len(scored_initiatives)} initiatives",
            extra={
                "top_score": scored_initiatives[0].composite_score.total_score if scored_initiatives else 0,
                "weights_used": weights.dict()
            }
        )
        
        return PrioritizationResponse(
            prioritized_initiatives=scored_initiatives,
            weights_used=weights
        )
    
    def update_weights(
        self, 
        weights: ScoringWeights, 
        description: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> None:
        """Update the current weights configuration"""
        self._current_weights = weights
        self._weights_description = description or "Updated weights configuration"
        self._weights_last_updated = datetime.utcnow()
        self._weights_updated_by = updated_by or "unknown"
        
        logger.info(
            "Updated scoring weights configuration",
            extra={
                "weights": weights.dict(),
                "description": self._weights_description,
                "updated_by": self._weights_updated_by
            }
        )
    
    def get_current_weights(self) -> Tuple[ScoringWeights, str, datetime, str]:
        """Get current weights configuration with metadata"""
        return (
            self._current_weights,
            self._weights_description,
            self._weights_last_updated,
            self._weights_updated_by
        )
    
    def get_default_weights(self) -> ScoringWeights:
        """Get default weights configuration"""
        return self._default_weights
    
    def reset_weights_to_default(self, updated_by: Optional[str] = None) -> None:
        """Reset weights to default configuration"""
        self.update_weights(
            self._default_weights, 
            "Reset to default weights configuration",
            updated_by
        )
    
    def get_algorithm_schema(self) -> Dict:
        """Get JSON schema for the scoring algorithm"""
        return {
            "algorithm": {
                "name": "Composite Initiative Scoring",
                "version": "v2.0",
                "formula": "score = (impact * w_impact) + (risk * w_risk) + ((10 - effort) * w_effort) + (compliance * w_compliance) - (dependency_count * w_penalty)"
            },
            "components": {
                "impact_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 10.0,
                    "description": "Business impact score (0-10)"
                },
                "risk_score": {
                    "type": "number", 
                    "minimum": 0.0,
                    "maximum": 10.0,
                    "description": "Risk mitigation score (0-10)"
                },
                "effort_score": {
                    "type": "number",
                    "minimum": 1.0, 
                    "maximum": 10.0,
                    "description": "Implementation effort score (1-10, higher = more effort)"
                },
                "compliance_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 10.0,
                    "description": "Compliance alignment score (0-10)"
                },
                "dependency_count": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Number of dependencies"
                }
            },
            "weights": {
                "impact": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.3,
                    "description": "Weight for business impact score"
                },
                "risk": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.25,
                    "description": "Weight for risk mitigation score"
                },
                "effort": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.2,
                    "description": "Weight for implementation effort (inverted)"
                },
                "compliance": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.15,
                    "description": "Weight for compliance alignment score"
                },
                "dependency_penalty": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.1,
                    "description": "Weight for dependency penalty"
                }
            },
            "constraints": {
                "weights_sum": 1.0,
                "score_range": [0.0, 10.0]
            }
        }


# Global service instance
roadmap_prioritization_service = RoadmapPrioritizationService()