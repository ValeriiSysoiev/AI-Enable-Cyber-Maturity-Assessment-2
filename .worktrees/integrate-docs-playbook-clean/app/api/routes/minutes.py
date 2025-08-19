"""
Minutes API Routes

Provides endpoints for managing workshop minutes:
- Generate draft minutes from workshop data
- Update draft minutes
- Retrieve minutes by ID
"""

from fastapi import APIRouter, Depends, HTTPException, Request
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from domain.repository import Repository
from domain.models import Minutes, MinutesSection
from repos.cosmos_repository import CosmosRepository
from ..security import current_context, require_member
from services.minutes_agent import create_minutes_agent
from config import config

logger = logging.getLogger(__name__)

# Response models
class MinutesResponse(BaseModel):
    """Public minutes response model"""
    id: str
    workshop_id: str
    status: str
    sections: MinutesSection
    generated_by: str
    published_at: Optional[datetime] = None
    content_hash: Optional[str] = None
    parent_id: Optional[str] = None
    created_at: datetime
    updated_by: str

class GenerateMinutesRequest(BaseModel):
    """Request model for generating minutes"""
    workshop_type: str = Field(default="general")
    attendees: Optional[list[str]] = None
    additional_context: Optional[Dict[str, Any]] = None

class UpdateMinutesRequest(BaseModel):
    """Request model for updating draft minutes"""
    sections: MinutesSection

# Router setup
router = APIRouter(prefix="/api/v1", tags=["minutes"])

def get_repo(request: Request) -> Repository:
    return request.app.state.repo

def get_correlation_id(request: Request) -> str:
    """Extract correlation ID from request headers"""
    return request.headers.get(config.logging.correlation_id_header, str(uuid.uuid4()))

@router.post("/workshops/{workshop_id}/minutes:generate", response_model=MinutesResponse)
async def generate_minutes(
    workshop_id: str,
    request_data: GenerateMinutesRequest,
    request: Request,
    repo: Repository = Depends(get_repo),
    ctx = Depends(current_context)
):
    """
    Generate draft minutes for a workshop using the Minutes Agent.
    Creates a new Minutes document with status='draft' and generatedBy='agent'.
    
    Requires engagement membership for the workshop's engagement.
    """
    # Note: For S4, we assume workshop_id maps to engagement_id for simplicity
    # In a full implementation, we'd lookup the workshop's engagement_id
    engagement_id = ctx["engagement_id"]
    
    # Verify user has access to the engagement
    require_member(repo, ctx, "member")
    
    correlation_id = get_correlation_id(request)
    
    logger.info(
        "Generating minutes for workshop",
        extra={
            "correlation_id": correlation_id,
            "workshop_id": workshop_id,
            "engagement_id": engagement_id,
            "user_email": ctx["user_email"],
            "workshop_type": request_data.workshop_type
        }
    )
    
    try:
        # Create workshop data for the agent
        workshop_data = {
            "id": workshop_id,
            "type": request_data.workshop_type,
            "attendees": request_data.attendees or [],
            "additional_context": request_data.additional_context or {}
        }
        
        # Generate minutes using the agent
        minutes_agent = create_minutes_agent(correlation_id)
        minutes_section = await minutes_agent.generate_draft_minutes(workshop_data)
        
        # Create the Minutes model
        minutes = Minutes(
            workshop_id=workshop_id,
            status="draft",
            sections=minutes_section,
            generated_by="agent",
            updated_by=ctx["user_email"]
        )
        
        # Store in repository
        if isinstance(repo, CosmosRepository):
            stored_minutes = await repo._create_minutes_async(minutes)
        else:
            stored_minutes = repo.create_minutes(minutes)
        
        logger.info(
            "Successfully generated minutes",
            extra={
                "correlation_id": correlation_id,
                "minutes_id": stored_minutes.id,
                "workshop_id": workshop_id,
                "engagement_id": engagement_id,
                "sections_count": {
                    "attendees": len(stored_minutes.sections.attendees),
                    "decisions": len(stored_minutes.sections.decisions),
                    "actions": len(stored_minutes.sections.actions),
                    "questions": len(stored_minutes.sections.questions)
                }
            }
        )
        
        # Return response
        return MinutesResponse(
            id=stored_minutes.id,
            workshop_id=stored_minutes.workshop_id,
            status=stored_minutes.status,
            sections=stored_minutes.sections,
            generated_by=stored_minutes.generated_by,
            published_at=stored_minutes.published_at,
            content_hash=stored_minutes.content_hash,
            parent_id=stored_minutes.parent_id,
            created_at=stored_minutes.created_at,
            updated_by=stored_minutes.updated_by
        )
        
    except Exception as e:
        logger.error(
            "Failed to generate minutes",
            extra={
                "correlation_id": correlation_id,
                "workshop_id": workshop_id,
                "engagement_id": engagement_id,
                "error": str(e)
            }
        )
        raise HTTPException(status_code=500, detail=f"Failed to generate minutes: {str(e)}")

@router.patch("/minutes/{minutes_id}", response_model=MinutesResponse)
async def update_minutes(
    minutes_id: str,
    request_data: UpdateMinutesRequest,
    request: Request,
    repo: Repository = Depends(get_repo),
    ctx = Depends(current_context)
):
    """
    Update draft minutes. Only allows edits when status='draft'.
    Requires engagement membership.
    """
    correlation_id = get_correlation_id(request)
    engagement_id = ctx["engagement_id"]
    
    logger.info(
        "Updating minutes",
        extra={
            "correlation_id": correlation_id,
            "minutes_id": minutes_id,
            "engagement_id": engagement_id,
            "user_email": ctx["user_email"]
        }
    )
    
    try:
        # Get existing minutes
        existing_minutes = None
        if isinstance(repo, CosmosRepository):
            # For Cosmos, we need to find the minutes by querying all workshops in engagement
            # This is a simplification - in practice we'd have better indexing
            raise HTTPException(status_code=501, detail="Cosmos update not implemented in S4")
        else:
            existing_minutes = repo.get_minutes(minutes_id)
        
        if not existing_minutes:
            raise HTTPException(status_code=404, detail="Minutes not found")
        
        # Verify user has access to the engagement (simplified check)
        require_member(repo, ctx, "member")
        
        # Only allow edits on draft status
        if existing_minutes.status != "draft":
            logger.warning(
                "Attempted to edit non-draft minutes",
                extra={
                    "correlation_id": correlation_id,
                    "minutes_id": minutes_id,
                    "current_status": existing_minutes.status,
                    "user_email": ctx["user_email"]
                }
            )
            raise HTTPException(
                status_code=409, 
                detail=f"Cannot edit published minutes. Use POST /api/v1/minutes/{minutes_id}/versions/new to create a new version."
            )
        
        # Update the minutes
        updated_minutes = Minutes(
            id=existing_minutes.id,
            workshop_id=existing_minutes.workshop_id,
            status=existing_minutes.status,  # Keep current status
            sections=request_data.sections,
            generated_by="human",  # Changed to human since user edited
            published_at=existing_minutes.published_at,
            content_hash=existing_minutes.content_hash,
            parent_id=existing_minutes.parent_id,
            created_at=existing_minutes.created_at,
            updated_by=ctx["user_email"]
        )
        
        # Store updated minutes
        if isinstance(repo, CosmosRepository):
            stored_minutes = await repo._update_minutes_async(updated_minutes)
        else:
            stored_minutes = repo.update_minutes(updated_minutes)
        
        logger.info(
            "Successfully updated minutes",
            extra={
                "correlation_id": correlation_id,
                "minutes_id": stored_minutes.id,
                "updated_by": stored_minutes.updated_by,
                "generated_by": stored_minutes.generated_by
            }
        )
        
        # Return response
        return MinutesResponse(
            id=stored_minutes.id,
            workshop_id=stored_minutes.workshop_id,
            status=stored_minutes.status,
            sections=stored_minutes.sections,
            generated_by=stored_minutes.generated_by,
            published_at=stored_minutes.published_at,
            content_hash=stored_minutes.content_hash,
            parent_id=stored_minutes.parent_id,
            created_at=stored_minutes.created_at,
            updated_by=stored_minutes.updated_by
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update minutes",
            extra={
                "correlation_id": correlation_id,
                "minutes_id": minutes_id,
                "error": str(e)
            }
        )
        raise HTTPException(status_code=500, detail=f"Failed to update minutes: {str(e)}")

@router.get("/minutes/{minutes_id}", response_model=MinutesResponse)
async def get_minutes(
    minutes_id: str,
    request: Request,
    repo: Repository = Depends(get_repo),
    ctx = Depends(current_context)
):
    """
    Get minutes by ID. Requires engagement membership.
    """
    correlation_id = get_correlation_id(request)
    engagement_id = ctx["engagement_id"]
    
    # Verify user has access to the engagement
    require_member(repo, ctx, "member")
    
    logger.info(
        "Retrieving minutes",
        extra={
            "correlation_id": correlation_id,
            "minutes_id": minutes_id,
            "engagement_id": engagement_id,
            "user_email": ctx["user_email"]
        }
    )
    
    try:
        # Get minutes
        minutes = None
        if isinstance(repo, CosmosRepository):
            raise HTTPException(status_code=501, detail="Cosmos get not implemented in S4")
        else:
            minutes = repo.get_minutes(minutes_id)
        
        if not minutes:
            raise HTTPException(status_code=404, detail="Minutes not found")
        
        # Log access for audit
        logger.info(
            "Minutes retrieved successfully",
            extra={
                "correlation_id": correlation_id,
                "minutes_id": minutes_id,
                "workshop_id": minutes.workshop_id,
                "status": minutes.status,
                "accessed_by": ctx["user_email"]
            }
        )
        
        # Return response
        return MinutesResponse(
            id=minutes.id,
            workshop_id=minutes.workshop_id,
            status=minutes.status,
            sections=minutes.sections,
            generated_by=minutes.generated_by,
            published_at=minutes.published_at,
            content_hash=minutes.content_hash,
            parent_id=minutes.parent_id,
            created_at=minutes.created_at,
            updated_by=minutes.updated_by
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to retrieve minutes",
            extra={
                "correlation_id": correlation_id,
                "minutes_id": minutes_id,
                "error": str(e)
            }
        )
        raise HTTPException(status_code=500, detail=f"Failed to retrieve minutes: {str(e)}")

@router.post("/minutes/{minutes_id}:publish", response_model=MinutesResponse)
async def publish_minutes(
    minutes_id: str,
    request: Request,
    repo: Repository = Depends(get_repo),
    ctx = Depends(current_context)
):
    """
    Publish minutes by computing content hash, setting status='published', 
    and publishedAt timestamp. Only draft minutes can be published.
    Published minutes become immutable.
    """
    correlation_id = get_correlation_id(request)
    engagement_id = ctx["engagement_id"]
    
    # Verify user has access to the engagement
    require_member(repo, ctx, "member")
    
    logger.info(
        "Publishing minutes",
        extra={
            "correlation_id": correlation_id,
            "minutes_id": minutes_id,
            "engagement_id": engagement_id,
            "user_email": ctx["user_email"]
        }
    )
    
    try:
        # Publish the minutes using repository method
        published_minutes = None
        if isinstance(repo, CosmosRepository):
            published_minutes = await repo._publish_minutes_async(minutes_id)
        else:
            published_minutes = repo.publish_minutes(minutes_id)
        
        logger.info(
            "Successfully published minutes",
            extra={
                "correlation_id": correlation_id,
                "minutes_id": published_minutes.id,
                "workshop_id": published_minutes.workshop_id,
                "content_hash": published_minutes.content_hash,
                "published_at": published_minutes.published_at,
                "published_by": ctx["user_email"]
            }
        )
        
        # Return response
        return MinutesResponse(
            id=published_minutes.id,
            workshop_id=published_minutes.workshop_id,
            status=published_minutes.status,
            sections=published_minutes.sections,
            generated_by=published_minutes.generated_by,
            published_at=published_minutes.published_at,
            content_hash=published_minutes.content_hash,
            parent_id=published_minutes.parent_id,
            created_at=published_minutes.created_at,
            updated_by=published_minutes.updated_by
        )
        
    except ValueError as e:
        # Handle business logic errors (not found, wrong status, etc.)
        logger.warning(
            "Failed to publish minutes - business logic error",
            extra={
                "correlation_id": correlation_id,
                "minutes_id": minutes_id,
                "error": str(e),
                "user_email": ctx["user_email"]
            }
        )
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to publish minutes",
            extra={
                "correlation_id": correlation_id,
                "minutes_id": minutes_id,
                "error": str(e)
            }
        )
        raise HTTPException(status_code=500, detail=f"Failed to publish minutes: {str(e)}")

@router.post("/minutes/{minutes_id}/versions/new", response_model=MinutesResponse)
async def create_new_version(
    minutes_id: str,
    request: Request,
    repo: Repository = Depends(get_repo),
    ctx = Depends(current_context)
):
    """
    Create a new draft version of published minutes for editing.
    The new version will have a parent_id reference to the original.
    This allows editing published minutes without breaking immutability.
    """
    correlation_id = get_correlation_id(request)
    engagement_id = ctx["engagement_id"]
    
    # Verify user has access to the engagement
    require_member(repo, ctx, "member")
    
    logger.info(
        "Creating new version of minutes",
        extra={
            "correlation_id": correlation_id,
            "parent_minutes_id": minutes_id,
            "engagement_id": engagement_id,
            "user_email": ctx["user_email"]
        }
    )
    
    try:
        # Create new version using repository method
        new_version = None
        if isinstance(repo, CosmosRepository):
            new_version = await repo._create_new_version_async(minutes_id, ctx["user_email"])
        else:
            new_version = repo.create_new_version(minutes_id, ctx["user_email"])
        
        logger.info(
            "Successfully created new version",
            extra={
                "correlation_id": correlation_id,
                "new_minutes_id": new_version.id,
                "parent_minutes_id": minutes_id,
                "workshop_id": new_version.workshop_id,
                "created_by": ctx["user_email"]
            }
        )
        
        # Return response
        return MinutesResponse(
            id=new_version.id,
            workshop_id=new_version.workshop_id,
            status=new_version.status,
            sections=new_version.sections,
            generated_by=new_version.generated_by,
            published_at=new_version.published_at,
            content_hash=new_version.content_hash,
            parent_id=new_version.parent_id,
            created_at=new_version.created_at,
            updated_by=new_version.updated_by
        )
        
    except ValueError as e:
        # Handle business logic errors (parent not found, etc.)
        logger.warning(
            "Failed to create new version - business logic error",
            extra={
                "correlation_id": correlation_id,
                "parent_minutes_id": minutes_id,
                "error": str(e),
                "user_email": ctx["user_email"]
            }
        )
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to create new version",
            extra={
                "correlation_id": correlation_id,
                "parent_minutes_id": minutes_id,
                "error": str(e)
            }
        )
        raise HTTPException(status_code=500, detail=f"Failed to create new version: {str(e)}")