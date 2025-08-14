from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict
from ...domain.models import Engagement, Membership
from ...domain.repository import Repository
from ..security import current_context, is_admin, require_member
from ..schemas import EngagementCreate, AddMemberRequest

router = APIRouter(prefix="/engagements", tags=["engagements"])


def get_repo(request: Request) -> Repository:
    return request.app.state.repo


@router.post("", response_model=Engagement)
def create_engagement(
    payload: EngagementCreate, 
    repo: Repository = Depends(get_repo), 
    ctx: Dict[str, str] = Depends(current_context)
):
    """Create a new engagement (Admin only)"""
    if not is_admin(ctx["user_email"]):
        raise HTTPException(403, "Admin only")
    
    e = Engagement(
        name=payload.name, 
        client_code=payload.client_code, 
        created_by=ctx["user_email"]
    )
    created = repo.create_engagement(e)
    
    # Automatically add creator as lead
    m = Membership(
        engagement_id=created.id,
        user_email=ctx["user_email"],
        role="lead"
    )
    repo.add_membership(m)
    
    return created


@router.get("", response_model=List[Engagement])
def list_my_engagements(
    repo: Repository = Depends(get_repo), 
    ctx: Dict[str, str] = Depends(current_context)
):
    """List engagements accessible to the current user"""
    return repo.list_engagements_for_user(ctx["user_email"], is_admin(ctx["user_email"]))


@router.post("/{engagement_id}/members", response_model=Membership)
def add_member(
    engagement_id: str, 
    payload: AddMemberRequest, 
    repo: Repository = Depends(get_repo), 
    ctx: Dict[str, str] = Depends(current_context)
):
    """Add a member to an engagement (Lead or Admin only)"""
    # Verify user has lead access to this engagement
    # Create a new context with the specific engagement_id
    member_ctx = ctx.copy()
    member_ctx["engagement_id"] = engagement_id
    require_member(repo, member_ctx, "lead")
    
    m = Membership(
        engagement_id=engagement_id, 
        user_email=payload.user_email, 
        role=payload.role
    )
    return repo.add_membership(m)
