"""Roadmap cost calculation API routes with T-shirt sizing and regional rates"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends

from app.api.schemas.roadmap_costs import (
    CostCalculationRequest, CostCalculationResponse,
    TSizeUpdateRequest, TSizeConfigResponse,
    CostConfigurationInfo, Region, Scenario
)
from app.services.roadmap_cost_calculation import roadmap_cost_service
from app.core.logging import get_correlation_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/roadmap/costs", tags=["roadmap-costs"])


def get_user_email(x_user_email: Optional[str] = Header(None)) -> Optional[str]:
    """Extract user email from headers for audit logging"""
    return x_user_email


@router.post("/calculate", response_model=CostCalculationResponse)
async def calculate_portfolio_costs(
    request: CostCalculationRequest,
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Calculate costs for a portfolio of initiatives using:
    - Regional labor rates by role
    - T-shirt size to cost mapping validation
    - Scenario-based multipliers (baseline/constrained/accelerated)
    - Cost breakdown: labor + tooling + Microsoft services
    
    Formula: cost = (labor + tooling + microsoft_services) * regional_multiplier * scenario_multiplier
    """
    try:
        logger.info(
            "Calculating portfolio costs",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email,
                "initiative_count": len(request.initiatives),
                "region": request.region.value,
                "scenario": request.scenario.value,
                "custom_rates": request.custom_rates is not None
            }
        )
        
        response = roadmap_cost_service.calculate_portfolio_costs(request)
        
        logger.info(
            "Successfully calculated portfolio costs",
            extra={
                "correlation_id": correlation_id,
                "total_portfolio_cost": response.total_portfolio_cost,
                "initiative_count": len(response.calculated_costs)
            }
        )
        
        return response
        
    except ValueError as e:
        logger.error(
            f"Invalid cost calculation request: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error calculating portfolio costs: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to calculate portfolio costs")


@router.get("/configuration", response_model=CostConfigurationInfo)
async def get_cost_configuration(
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """Get current cost calculation configuration including regional rates and T-shirt mappings"""
    try:
        logger.info(
            "Retrieved cost configuration",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email
            }
        )
        
        return roadmap_cost_service.get_configuration_info()
        
    except Exception as e:
        logger.error(
            f"Error retrieving cost configuration: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve cost configuration")


@router.get("/t-shirt-sizes", response_model=TSizeConfigResponse)
async def get_t_shirt_size_mappings(
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """Get current T-shirt size to cost range mappings"""
    try:
        config_info = roadmap_cost_service.get_configuration_info()
        
        logger.info(
            "Retrieved T-shirt size mappings",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email,
                "mapping_count": len(config_info.default_t_shirt_mappings)
            }
        )
        
        return TSizeConfigResponse(
            size_mappings=config_info.default_t_shirt_mappings,
            last_updated=roadmap_cost_service._last_updated,
            updated_by=roadmap_cost_service._updated_by
        )
        
    except Exception as e:
        logger.error(
            f"Error retrieving T-shirt size mappings: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve T-shirt size mappings")


@router.put("/t-shirt-sizes", response_model=TSizeConfigResponse)
async def update_t_shirt_size_mappings(
    request: TSizeUpdateRequest,
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """Update T-shirt size to cost range mappings"""
    try:
        logger.info(
            "Updating T-shirt size mappings",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email,
                "mapping_count": len(request.size_mappings)
            }
        )
        
        roadmap_cost_service.update_t_shirt_mappings(request.size_mappings, user_email or "unknown")
        
        logger.info(
            "Successfully updated T-shirt size mappings",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email
            }
        )
        
        return TSizeConfigResponse(
            size_mappings=request.size_mappings,
            last_updated=roadmap_cost_service._last_updated,
            updated_by=roadmap_cost_service._updated_by
        )
        
    except ValueError as e:
        logger.error(
            f"Invalid T-shirt size mappings: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error updating T-shirt size mappings: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to update T-shirt size mappings")


@router.get("/regions", response_model=dict)
async def get_regional_rates(
    region: Optional[Region] = None,
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """Get regional labor rates for cost calculation"""
    try:
        config_info = roadmap_cost_service.get_configuration_info()
        
        if region:
            rates = {region.value: config_info.regional_rates[region]}
            logger.info(
                f"Retrieved regional rates for {region.value}",
                extra={"correlation_id": correlation_id, "user_email": user_email}
            )
        else:
            rates = {r.value: rates_obj for r, rates_obj in config_info.regional_rates.items()}
            logger.info(
                "Retrieved all regional rates",
                extra={
                    "correlation_id": correlation_id,
                    "user_email": user_email,
                    "region_count": len(rates)
                }
            )
        
        return {
            "regional_rates": rates,
            "supported_regions": [r.value for r in Region],
            "rate_currency": "USD",
            "rate_period": "hourly"
        }
        
    except Exception as e:
        logger.error(
            f"Error retrieving regional rates: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve regional rates")


@router.get("/scenarios", response_model=dict)
async def get_scenario_multipliers(
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """Get scenario-based cost multipliers"""
    try:
        config_info = roadmap_cost_service.get_configuration_info()
        
        logger.info(
            "Retrieved scenario multipliers",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email
            }
        )
        
        return {
            "scenario_multipliers": {
                "baseline": config_info.scenario_multipliers.baseline,
                "constrained": config_info.scenario_multipliers.constrained,
                "accelerated": config_info.scenario_multipliers.accelerated
            },
            "scenario_descriptions": {
                "baseline": "Standard timeline and resource allocation",
                "constrained": "Reduced budget scenario with 20% cost reduction",
                "accelerated": "Fast-track scenario with 30% cost premium for expedited delivery"
            },
            "supported_scenarios": [s.value for s in Scenario]
        }
        
    except Exception as e:
        logger.error(
            f"Error retrieving scenario multipliers: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve scenario multipliers")