"""Roadmap prioritization schemas for composite scoring and weight configuration"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime


class ScoringWeights(BaseModel):
    """Configurable weights for composite scoring algorithm"""
    impact: float = Field(default=0.3, ge=0.0, le=1.0, description="Weight for business impact score")
    risk: float = Field(default=0.25, ge=0.0, le=1.0, description="Weight for risk mitigation score")
    effort: float = Field(default=0.2, ge=0.0, le=1.0, description="Weight for implementation effort (inverted)")
    compliance: float = Field(default=0.15, ge=0.0, le=1.0, description="Weight for compliance alignment score")
    dependency_penalty: float = Field(default=0.1, ge=0.0, le=1.0, description="Weight for dependency penalty")
    
    @validator('*')
    def weights_sum_to_one(cls, v, values):
        """Ensure all weights sum to approximately 1.0"""
        total = sum(values.values()) + v
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        return v


class InitiativeScoring(BaseModel):
    """Individual scoring components for a roadmap initiative"""
    impact_score: float = Field(ge=0.0, le=10.0, description="Business impact score (0-10)")
    risk_score: float = Field(ge=0.0, le=10.0, description="Risk mitigation score (0-10)")
    effort_score: float = Field(ge=1.0, le=10.0, description="Implementation effort score (1-10, higher = more effort)")
    compliance_score: float = Field(ge=0.0, le=10.0, description="Compliance alignment score (0-10)")
    dependency_count: int = Field(ge=0, description="Number of dependencies")


class CompositeScore(BaseModel):
    """Calculated composite score with breakdown"""
    total_score: float = Field(description="Final composite score (0-10)")
    weighted_impact: float = Field(description="Weighted impact contribution")
    weighted_risk: float = Field(description="Weighted risk contribution")
    weighted_effort: float = Field(description="Weighted effort contribution (inverted)")
    weighted_compliance: float = Field(description="Weighted compliance contribution")
    dependency_penalty: float = Field(description="Dependency penalty applied")
    weights_used: ScoringWeights = Field(description="Weights configuration used for calculation")


class InitiativePrioritization(BaseModel):
    """Complete prioritization data for an initiative"""
    initiative_id: str = Field(description="Unique identifier for the initiative")
    name: str = Field(description="Initiative name")
    description: Optional[str] = Field(description="Initiative description")
    scoring: InitiativeScoring = Field(description="Individual scoring components")
    composite_score: CompositeScore = Field(description="Calculated composite score")
    priority_rank: Optional[int] = Field(description="Calculated priority ranking")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PrioritizationRequest(BaseModel):
    """Request to calculate prioritization for initiatives"""
    initiatives: List[InitiativeScoring] = Field(description="List of initiatives to score")
    initiative_ids: List[str] = Field(description="Corresponding initiative IDs")
    weights: Optional[ScoringWeights] = Field(description="Custom weights (optional, uses defaults if not provided)")


class PrioritizationResponse(BaseModel):
    """Response with calculated prioritizations"""
    prioritized_initiatives: List[InitiativePrioritization] = Field(description="Initiatives sorted by priority")
    weights_used: ScoringWeights = Field(description="Weights configuration used")
    calculation_timestamp: datetime = Field(default_factory=datetime.utcnow)


class WeightsConfigRequest(BaseModel):
    """Request to update scoring weights configuration"""
    weights: ScoringWeights = Field(description="New weights configuration")
    description: Optional[str] = Field(description="Description of weights configuration")


class WeightsConfigResponse(BaseModel):
    """Response with current weights configuration"""
    weights: ScoringWeights = Field(description="Current weights configuration")
    description: Optional[str] = Field(description="Description of weights configuration")
    last_updated: datetime = Field(description="When weights were last updated")
    updated_by: Optional[str] = Field(description="User who last updated weights")


class ScoringAlgorithmInfo(BaseModel):
    """Information about the scoring algorithm and JSON schema"""
    algorithm_version: str = Field(default="v2.0", description="Version of scoring algorithm")
    formula_description: str = Field(
        default="score = (impact * w_impact) + (risk * w_risk) + ((10 - effort) * w_effort) + (compliance * w_compliance) - (dependency_count * w_penalty)",
        description="Mathematical formula used for scoring"
    )
    schema: Dict = Field(description="JSON schema for scoring models")
    weights_defaults: ScoringWeights = Field(description="Default weights configuration")