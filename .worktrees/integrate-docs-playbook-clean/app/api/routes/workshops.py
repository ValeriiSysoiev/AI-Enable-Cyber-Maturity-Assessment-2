"""Workshop API Routes"""

import logging
from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from domain.models import Workshop, WorkshopAttendee, ConsentRecord
from repos.cosmos_repository import CosmosRepository
from services.audit import create_audit_service
from util.logging import get_correlation_id
from ..security import current_context, require_member
from ..schemas.workshop import (
    WorkshopCreateRequest,
    WorkshopResponse,
    ConsentRequest,
    WorkshopListResponse,
    StartWorkshopResponse
)

router = APIRouter(prefix="/api/v1/workshops", tags=["workshops"])
logger = logging.getLogger(__name__)


def get_repo(request: Request) -> CosmosRepository:
    """Get repository instance from app state"""
    return request.app.state.repo


@router.post("", response_model=WorkshopResponse)
async def create_workshop(
    payload: WorkshopCreateRequest,
    repo: CosmosRepository = Depends(get_repo),
    ctx: Dict[str, str] = Depends(current_context)
):
    """
    Create a new workshop
    Requires engagement membership
    """
    correlation_id = get_correlation_id()
    
    try:
        # Verify user has access to the engagement
        require_member(repo, ctx, "member")
        
        # Create attendees
        attendees = []
        for attendee_req in payload.attendees:
            attendee = WorkshopAttendee(
                user_id=attendee_req.user_id,
                email=attendee_req.email,
                role=attendee_req.role
            )
            attendees.append(attendee)
        
        # Create workshop
        workshop = Workshop(
            engagement_id=payload.engagement_id,
            title=payload.title,
            start_ts=payload.start_ts,
            attendees=attendees,
            created_by=ctx["user_email"]
        )
        
        # Store in repository
        created_workshop = await repo.create_workshop(workshop)
        
        # Audit log
        audit_service = create_audit_service(repo)
        await audit_service.log_audit_event(
            action_type="data_modification",
            user_email=ctx["user_email"],
            action_description=f"Created workshop: {created_workshop.title}",
            engagement_id=created_workshop.engagement_id,
            resource_type="workshop",
            resource_id=created_workshop.id,
            correlation_id=correlation_id
        )
        
        logger.info(
            f"Workshop created successfully",
            extra={
                "correlation_id": correlation_id,
                "workshop_id": created_workshop.id,
                "engagement_id": created_workshop.engagement_id,
                "created_by": ctx["user_email"],
                "attendee_count": len(created_workshop.attendees)
            }
        )
        
        # Convert to response model
        return _workshop_to_response(created_workshop)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to create workshop: {str(e)}",
            extra={
                "correlation_id": correlation_id,
                "engagement_id": payload.engagement_id,
                "user_email": ctx["user_email"],
                "error": str(e)
            }
        )
        raise HTTPException(500, f"Failed to create workshop: {str(e)}")


@router.post("/{workshop_id}/consent", response_model=WorkshopResponse)
async def give_consent(
    workshop_id: str,
    payload: ConsentRequest,
    repo: CosmosRepository = Depends(get_repo),
    ctx: Dict[str, str] = Depends(current_context)
):
    """
    Give consent for workshop attendance
    Requires engagement membership
    """
    correlation_id = get_correlation_id()
    
    try:
        # Verify user has access to the engagement
        require_member(repo, ctx, "member")
        
        # Create consent record
        consent = ConsentRecord(
            by=ctx["user_email"],
            user_id=ctx["user_email"],  # Using email as user_id for now
            timestamp=datetime.now(timezone.utc)
        )
        
        # Update workshop consent
        updated_workshop = await repo.update_workshop_consent(
            workshop_id=workshop_id,
            engagement_id=ctx["engagement_id"],
            attendee_id=payload.attendee_id,
            consent=consent
        )
        
        # Audit log
        audit_service = create_audit_service(repo)
        await audit_service.log_audit_event(
            action_type="data_modification",
            user_email=ctx["user_email"],
            action_description=f"Gave consent for workshop: {updated_workshop.title}",
            engagement_id=updated_workshop.engagement_id,
            resource_type="workshop",
            resource_id=updated_workshop.id,
            correlation_id=correlation_id
        )
        
        logger.info(
            f"Workshop consent given",
            extra={
                "correlation_id": correlation_id,
                "workshop_id": workshop_id,
                "attendee_id": payload.attendee_id,
                "user_email": ctx["user_email"]
            }
        )
        
        # Convert to response model
        return _workshop_to_response(updated_workshop)
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(
            f"Invalid consent request: {str(e)}",
            extra={
                "correlation_id": correlation_id,
                "workshop_id": workshop_id,
                "attendee_id": payload.attendee_id,
                "user_email": ctx["user_email"]
            }
        )
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(
            f"Failed to give consent: {str(e)}",
            extra={
                "correlation_id": correlation_id,
                "workshop_id": workshop_id,
                "attendee_id": payload.attendee_id,
                "user_email": ctx["user_email"],
                "error": str(e)
            }
        )
        raise HTTPException(500, f"Failed to give consent: {str(e)}")


@router.post("/{workshop_id}/start", response_model=StartWorkshopResponse)
async def start_workshop(
    workshop_id: str,
    repo: CosmosRepository = Depends(get_repo),
    ctx: Dict[str, str] = Depends(current_context)
):
    """
    Start a workshop (requires all attendee consent)
    Requires lead role in engagement
    """
    correlation_id = get_correlation_id()
    
    try:
        # Verify user has lead access to the engagement
        require_member(repo, ctx, "lead")
        
        # Start the workshop
        started_workshop = await repo.start_workshop(
            workshop_id=workshop_id,
            engagement_id=ctx["engagement_id"]
        )
        
        # Audit log
        audit_service = create_audit_service(repo)
        await audit_service.log_audit_event(
            action_type="data_modification",
            user_email=ctx["user_email"],
            action_description=f"Started workshop: {started_workshop.title}",
            engagement_id=started_workshop.engagement_id,
            resource_type="workshop",
            resource_id=started_workshop.id,
            correlation_id=correlation_id
        )
        
        logger.info(
            f"Workshop started successfully",
            extra={
                "correlation_id": correlation_id,
                "workshop_id": workshop_id,
                "started_by": ctx["user_email"],
                "started_at": started_workshop.started_at
            }
        )
        
        return StartWorkshopResponse(
            workshop=_workshop_to_response(started_workshop),
            message=f"Workshop '{started_workshop.title}' started successfully"
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(
            f"Invalid start request: {str(e)}",
            extra={
                "correlation_id": correlation_id,
                "workshop_id": workshop_id,
                "user_email": ctx["user_email"]
            }
        )
        raise HTTPException(403 if "consent" in str(e).lower() else 400, str(e))
    except Exception as e:
        logger.error(
            f"Failed to start workshop: {str(e)}",
            extra={
                "correlation_id": correlation_id,
                "workshop_id": workshop_id,
                "user_email": ctx["user_email"],
                "error": str(e)
            }
        )
        raise HTTPException(500, f"Failed to start workshop: {str(e)}")


@router.get("", response_model=WorkshopListResponse)
async def list_workshops(
    engagement_id: str = Query(..., description="Engagement ID to filter workshops"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    repo: CosmosRepository = Depends(get_repo),
    ctx: Dict[str, str] = Depends(current_context)
):
    """
    List workshops for an engagement (paginated)
    Requires engagement membership
    """
    correlation_id = get_correlation_id()
    
    try:
        # Create context with specific engagement_id for membership check
        engagement_ctx = ctx.copy()
        engagement_ctx["engagement_id"] = engagement_id
        require_member(repo, engagement_ctx, "member")
        
        # Get workshops from repository
        workshops, total_count = await repo.list_workshops(
            engagement_id=engagement_id,
            page=page,
            page_size=page_size
        )
        
        # Audit log for data access
        audit_service = create_audit_service(repo)
        await audit_service.log_audit_event(
            action_type="data_access",
            user_email=ctx["user_email"],
            action_description=f"Listed workshops for engagement",
            engagement_id=engagement_id,
            resource_type="workshop",
            correlation_id=correlation_id
        )
        
        logger.info(
            f"Listed workshops",
            extra={
                "correlation_id": correlation_id,
                "engagement_id": engagement_id,
                "user_email": ctx["user_email"],
                "page": page,
                "workshop_count": len(workshops),
                "total_count": total_count
            }
        )
        
        # Convert to response models
        workshop_responses = [_workshop_to_response(w) for w in workshops]
        
        return WorkshopListResponse(
            workshops=workshop_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=total_count > (page * page_size)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to list workshops: {str(e)}",
            extra={
                "correlation_id": correlation_id,
                "engagement_id": engagement_id,
                "user_email": ctx["user_email"],
                "error": str(e)
            }
        )
        raise HTTPException(500, f"Failed to list workshops: {str(e)}")


def _workshop_to_response(workshop: Workshop) -> WorkshopResponse:
    """Convert domain model to response model"""
    from ..schemas.workshop import AttendeeResponse, ConsentResponse
    
    attendee_responses = []
    for attendee in workshop.attendees:
        consent_response = None
        if attendee.consent:
            consent_response = ConsentResponse(
                by=attendee.consent.by,
                user_id=attendee.consent.user_id,
                timestamp=attendee.consent.timestamp
            )
        
        attendee_response = AttendeeResponse(
            id=attendee.id,
            user_id=attendee.user_id,
            email=attendee.email,
            role=attendee.role,
            consent=consent_response
        )
        attendee_responses.append(attendee_response)
    
    return WorkshopResponse(
        id=workshop.id,
        engagement_id=workshop.engagement_id,
        title=workshop.title,
        start_ts=workshop.start_ts,
        attendees=attendee_responses,
        created_by=workshop.created_by,
        created_at=workshop.created_at,
        started=workshop.started,
        started_at=workshop.started_at
    )