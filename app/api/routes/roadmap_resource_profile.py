"""Roadmap resource profile API routes for wave planning and skill mapping"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends, Response
from fastapi.responses import StreamingResponse
import io

from app.api.schemas.resource_profile import (
    ResourcePlanningRequest, ResourcePlanningResponse,
    CSVExportRequest, CSVExportResponse,
    GanttChartRequest, GanttChartResponse,
    WaveOverlayRequest, WaveOverlayResponse,
    ResourceConfigurationInfo
)
from app.services.roadmap_resource_profile import roadmap_resource_service
from app.core.logging import get_correlation_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/roadmap/resources", tags=["roadmap-resources"])


def get_user_email(x_user_email: Optional[str] = Header(None)) -> Optional[str]:
    """Extract user email from headers for audit logging"""
    return x_user_email


@router.post("/planning", response_model=ResourcePlanningResponse)
async def calculate_resource_planning(
    request: ResourcePlanningRequest,
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Calculate comprehensive resource planning for roadmap initiatives.
    
    Generates:
    - Wave-based resource allocations with skill mapping
    - FTE demand forecasting by role and time period
    - Resource conflict identification and recommendations
    - Cost estimates by wave and initiative
    
    Supports planning horizons from 1 month to 3 years with configurable wave durations.
    """
    try:
        logger.info(
            "Calculating resource planning",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email,
                "initiative_count": len(request.initiatives),
                "planning_horizon_weeks": request.planning_horizon_weeks,
                "wave_duration_weeks": request.wave_duration_weeks
            }
        )
        
        response = roadmap_resource_service.calculate_resource_profile(request)
        
        logger.info(
            "Successfully calculated resource planning",
            extra={
                "correlation_id": correlation_id,
                "initiative_profile_count": len(response.initiative_profiles),
                "total_fte_demand": sum(p.total_fte_demand for p in response.initiative_profiles),
                "resource_conflicts": len(response.resource_conflicts)
            }
        )
        
        return response
        
    except ValueError as e:
        logger.error(
            f"Invalid resource planning request: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error calculating resource planning: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to calculate resource planning")


@router.post("/export/csv")
async def export_resource_planning_csv(
    export_request: CSVExportRequest,
    planning_request: ResourcePlanningRequest,
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Export resource planning data to CSV format.
    
    Supports multiple export formats:
    - summary: High-level initiative overview
    - detailed: Complete wave and role breakdown
    - skills_matrix: Skill requirements matrix by role
    
    Includes optional cost and skill detail inclusion.
    """
    try:
        logger.info(
            "Exporting resource planning to CSV",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email,
                "export_format": export_request.export_format,
                "include_skills": export_request.include_skills,
                "include_costs": export_request.include_costs
            }
        )
        
        # First calculate the resource planning
        resource_response = roadmap_resource_service.calculate_resource_profile(planning_request)
        
        # Then export to CSV
        csv_response = roadmap_resource_service.export_to_csv(
            resource_response.initiative_profiles, 
            export_request
        )
        
        logger.info(
            "Successfully exported resource planning to CSV",
            extra={
                "correlation_id": correlation_id,
                "record_count": csv_response.record_count,
                "filename": csv_response.filename
            }
        )
        
        # Return CSV as downloadable file
        csv_bytes = csv_response.csv_content.encode('utf-8')
        return StreamingResponse(
            io.BytesIO(csv_bytes),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={csv_response.filename}"}
        )
        
    except ValueError as e:
        logger.error(
            f"Invalid CSV export request: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error exporting resource planning to CSV: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to export resource planning to CSV")


@router.post("/gantt", response_model=GanttChartResponse)
async def generate_gantt_chart_data(
    gantt_request: GanttChartRequest,
    planning_request: ResourcePlanningRequest,
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Generate Gantt chart data for resource planning visualization.
    
    Returns:
    - Task hierarchy (initiatives -> waves -> roles)
    - Timeline data with start/end dates and durations
    - Resource allocation overlay with FTE demands
    - Critical path identification
    - Optional skill demand heatmap
    - Milestone tracking for wave completions
    
    Supports weekly, monthly, and quarterly timeline granularities.
    """
    try:
        logger.info(
            "Generating Gantt chart data",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email,
                "include_resource_overlay": gantt_request.include_resource_overlay,
                "include_skill_heatmap": gantt_request.include_skill_heatmap,
                "timeline_granularity": gantt_request.timeline_granularity
            }
        )
        
        # First calculate the resource planning
        resource_response = roadmap_resource_service.calculate_resource_profile(planning_request)
        
        # Then generate Gantt chart data
        gantt_response = roadmap_resource_service.generate_gantt_chart_data(
            resource_response.initiative_profiles,
            gantt_request
        )
        
        logger.info(
            "Successfully generated Gantt chart data",
            extra={
                "correlation_id": correlation_id,
                "task_count": len(gantt_response.tasks),
                "timeline_days": (gantt_response.timeline_end - gantt_response.timeline_start).days,
                "milestone_count": len(gantt_response.milestone_dates)
            }
        )
        
        return gantt_response
        
    except ValueError as e:
        logger.error(
            f"Invalid Gantt chart request: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error generating Gantt chart data: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to generate Gantt chart data")


@router.post("/wave-overlay", response_model=WaveOverlayResponse)
async def generate_wave_overlay(
    request: WaveOverlayRequest,
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Generate wave overlay visualization data for capacity planning.
    
    Provides:
    - Standard wave period definitions (12-week cycles)
    - Resource utilization trends across waves
    - Skill demand forecasting by wave
    - Cost distribution and budget planning
    - Capacity vs demand analysis
    - Resource planning recommendations
    
    Supports aggregation by role, skill category, or cost.
    """
    try:
        logger.info(
            "Generating wave overlay visualization",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email,
                "planning_horizon_weeks": request.planning_horizon_weeks,
                "include_resource_utilization": request.include_resource_utilization,
                "aggregate_by": request.aggregate_by
            }
        )
        
        response = roadmap_resource_service.generate_wave_overlay(request)
        
        logger.info(
            "Successfully generated wave overlay",
            extra={
                "correlation_id": correlation_id,
                "wave_count": len(response.wave_periods),
                "recommendation_count": len(response.recommendations)
            }
        )
        
        return response
        
    except ValueError as e:
        logger.error(
            f"Invalid wave overlay request: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error generating wave overlay: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to generate wave overlay")


@router.get("/configuration", response_model=ResourceConfigurationInfo)
async def get_resource_configuration(
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Get resource planning configuration and metadata.
    
    Returns:
    - Available role types with descriptions and typical requirements
    - Comprehensive skill catalog with categories and proficiency definitions
    - Role-to-skill mapping matrix
    - Configuration limits (planning horizon, wave duration, etc.)
    - Supported export formats and visualization options
    
    Used for UI configuration and validation.
    """
    try:
        logger.info(
            "Retrieved resource configuration",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email
            }
        )
        
        return roadmap_resource_service.get_configuration_info()
        
    except Exception as e:
        logger.error(
            f"Error retrieving resource configuration: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve resource configuration")


@router.get("/skills/catalog", response_model=dict)
async def get_skills_catalog(
    category: Optional[str] = None,
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Get comprehensive skills catalog for resource planning.
    
    Returns skills organized by category:
    - technical_skills: Cloud security, network security, automation, etc.
    - compliance_skills: SOC 2, ISO 27001, NIST framework, etc.
    - management_skills: Project management, stakeholder management, etc.
    - analytical_skills: Threat intelligence, metrics, data analysis, etc.
    
    Optionally filter by specific category.
    """
    try:
        config = roadmap_resource_service.get_configuration_info()
        skills_catalog = {
            "technical_skills": [s for s in config.skill_mapping.available_skills if s["category"] == "technical"],
            "compliance_skills": [s for s in config.skill_mapping.available_skills if s["category"] == "compliance"],
            "management_skills": [s for s in config.skill_mapping.available_skills if s["category"] == "management"],
            "analytical_skills": [s for s in config.skill_mapping.available_skills if s["category"] == "analytical"]
        }
        
        if category:
            if category in skills_catalog:
                result = {category: skills_catalog[category]}
            else:
                raise ValueError(f"Invalid skill category: {category}")
        else:
            result = skills_catalog
        
        logger.info(
            "Retrieved skills catalog",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email,
                "category_filter": category,
                "total_skills": sum(len(skills) for skills in result.values())
            }
        )
        
        return {
            "skills_catalog": result,
            "proficiency_levels": [level.value for level in list(config.skill_mapping.proficiency_definitions.keys())],
            "skill_categories": config.skill_mapping.skill_categories
        }
        
    except ValueError as e:
        logger.error(
            f"Invalid skills catalog request: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error retrieving skills catalog: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve skills catalog")


@router.get("/roles/templates", response_model=dict)
async def get_role_templates(
    role_type: Optional[str] = None,
    user_email: Optional[str] = Depends(get_user_email),
    correlation_id: str = Depends(get_correlation_id)
):
    """
    Get role templates with default skill requirements and capacity.
    
    Provides standard templates for:
    - Security Architect: Cloud security design, Azure expertise, risk assessment
    - Security Engineer: Network security, automation, incident response
    - Compliance Analyst: SOC 2, ISO 27001, audit and assurance
    - Project Manager: Cybersecurity project management, stakeholder management
    - And other cybersecurity roles...
    
    Optionally filter by specific role type.
    """
    try:
        config = roadmap_resource_service.get_configuration_info()
        
        if role_type:
            # Find specific role
            role_info = next(
                (role for role in config.available_roles if role["role_type"] == role_type),
                None
            )
            if not role_info:
                raise ValueError(f"Invalid role type: {role_type}")
            
            # Get skills for this role
            role_skills = config.skill_mapping.role_skill_matrix.get(role_type, [])
            
            result = {
                role_type: {
                    **role_info,
                    "default_skills": role_skills,
                    "skill_count": len(role_skills)
                }
            }
        else:
            # Return all role templates
            result = {}
            for role in config.available_roles:
                role_type_key = role["role_type"]
                role_skills = config.skill_mapping.role_skill_matrix.get(role_type_key, [])
                
                result[role_type_key] = {
                    **role,
                    "default_skills": role_skills,
                    "skill_count": len(role_skills)
                }
        
        logger.info(
            "Retrieved role templates",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email,
                "role_type_filter": role_type,
                "template_count": len(result)
            }
        )
        
        return {
            "role_templates": result,
            "available_role_types": [role["role_type"] for role in config.available_roles],
            "total_templates": len(result)
        }
        
    except ValueError as e:
        logger.error(
            f"Invalid role templates request: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error retrieving role templates: {e}",
            extra={"correlation_id": correlation_id, "user_email": user_email}
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve role templates")