"""Roadmap prioritization API routes with composite scoring"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from datetime import datetime

from api.schemas.roadmap import (
    PrioritizationRequest, PrioritizationResponse,
    WeightsConfigRequest, WeightsConfigResponse,
    ScoringWeights, ScoringAlgorithmInfo
)
from services.roadmap_prioritization import roadmap_prioritization_service
from core.logging import get_correlation_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/roadmap/prioritization", tags=["roadmap-prioritization"])


def get_user_email(x_user_email: Optional[str] = Header(None)) -> Optional[str]:
    """Extract user email from headers for audit logging"""
    return x_user_email


@router.post("/calculate", response_model=PrioritizationResponse)
async def calculate_prioritization(
    request: PrioritizationRequest,
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Calculate prioritization for a list of initiatives using composite scoring.
    
    Applies the formula:
    score = (impact * w_impact) + (risk * w_risk) + ((10 - effort) * w_effort) + 
            (compliance * w_compliance) - (dependency_count * w_penalty)
    
    Returns initiatives sorted by priority score (highest first).
    """
    try:
        logger.info(
            "Calculating initiative prioritization",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email,
                "initiative_count": len(request.initiatives),
                "custom_weights": request.weights is not None
            }
        )
        
        response = roadmap_prioritization_service.prioritize_initiatives(request)
        
        logger.info(
            "Successfully calculated prioritization",
            extra={
                "correlation_id": correlation_id,
                "initiative_count": len(response.prioritized_initiatives),
                "top_score": response.prioritized_initiatives[0].composite_score.total_score if response.prioritized_initiatives else 0
            }
        )
        
        return response
        
    except ValueError as e:
        logger.error(
            f"Invalid prioritization request: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error calculating prioritization: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to calculate prioritization")


@router.get("/weights", response_model=WeightsConfigResponse)
async def get_scoring_weights(
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """Get current scoring weights configuration"""
    try:
        weights, description, last_updated, updated_by = roadmap_prioritization_service.get_current_weights()
        
        logger.info(
            "Retrieved scoring weights configuration",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email
            }
        )
        
        return WeightsConfigResponse(
            weights=weights,
            description=description,
            last_updated=last_updated,
            updated_by=updated_by
        )
        
    except Exception as e:
        logger.error(
            f"Error retrieving weights configuration: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve weights configuration")


@router.put("/weights", response_model=WeightsConfigResponse)
async def update_scoring_weights(
    request: WeightsConfigRequest,
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """Update scoring weights configuration"""
    try:
        logger.info(
            "Updating scoring weights configuration",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email,
                "new_weights": request.weights.dict()
            }
        )
        
        roadmap_prioritization_service.update_weights(
            request.weights,
            request.description,
            user_email
        )
        
        weights, description, last_updated, updated_by = roadmap_prioritization_service.get_current_weights()
        
        logger.info(
            "Successfully updated scoring weights",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email
            }
        )
        
        return WeightsConfigResponse(
            weights=weights,
            description=description,
            last_updated=last_updated,
            updated_by=updated_by
        )
        
    except ValueError as e:
        logger.error(
            f"Invalid weights configuration: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error updating weights configuration: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to update weights configuration")


@router.post("/weights/reset", response_model=WeightsConfigResponse)
async def reset_scoring_weights(
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """Reset scoring weights to default configuration"""
    try:
        logger.info(
            "Resetting scoring weights to defaults",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email
            }
        )
        
        roadmap_prioritization_service.reset_weights_to_default(user_email)
        
        weights, description, last_updated, updated_by = roadmap_prioritization_service.get_current_weights()
        
        logger.info(
            "Successfully reset scoring weights",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email
            }
        )
        
        return WeightsConfigResponse(
            weights=weights,
            description=description,
            last_updated=last_updated,
            updated_by=updated_by
        )
        
    except Exception as e:
        logger.error(
            f"Error resetting weights configuration: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to reset weights configuration")


@router.get("/algorithm/schema", response_model=ScoringAlgorithmInfo)
async def get_algorithm_schema(
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """Get JSON schema documentation for the scoring algorithm"""
    try:
        logger.info(
            "Retrieved algorithm schema",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email
            }
        )
        
        schema = roadmap_prioritization_service.get_algorithm_schema()
        default_weights = roadmap_prioritization_service.get_default_weights()
        
        return ScoringAlgorithmInfo(
            schema=schema,
            weights_defaults=default_weights
        )
        
    except Exception as e:
        logger.error(
            f"Error retrieving algorithm schema: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve algorithm schema")