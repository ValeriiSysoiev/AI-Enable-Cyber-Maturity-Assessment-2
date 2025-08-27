import sys
sys.path.append("/app")
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict
from domain.models import Assessment
from domain.repository import Repository
from api.security import current_context, require_member

router = APIRouter(prefix="/api/domain-assessments", tags=["domain-assessments"])

def get_repo(request: Request) -> Repository:
    # wired in main.py app.state.repo
    return request.app.state.repo

@router.post("", response_model=Assessment)
def create_assessment(
    a: Assessment, 
    repo: Repository = Depends(get_repo),
    ctx: Dict[str, str] = Depends(current_context)
):
    # Ensure user is a member of the engagement
    require_member(repo, ctx, "member")
    
    # Validate required fields
    if not a.name or not a.name.strip():
        raise HTTPException(status_code=400, detail="Assessment name is required and cannot be empty")
    
    # Set engagement_id from context
    a.engagement_id = ctx["engagement_id"]
    
    # Check for duplicate assessment ID
    existing = repo.get_assessment(a.id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Assessment with ID '{a.id}' already exists")
    
    return repo.create_assessment(a)

@router.get("", response_model=List[Assessment])
def list_assessments(
    repo: Repository = Depends(get_repo),
    ctx: Dict[str, str] = Depends(current_context)
):
    # Ensure user is a member of the engagement
    require_member(repo, ctx, "member")
    
    # List assessments for the engagement
    return repo.list_assessments(ctx["engagement_id"])

@router.get("/{assessment_id}", response_model=Assessment)
def get_assessment(
    assessment_id: str, 
    repo: Repository = Depends(get_repo),
    ctx: Dict[str, str] = Depends(current_context)
):
    # Ensure user is a member of the engagement
    require_member(repo, ctx, "member")
    
    a = repo.get_assessment(assessment_id)
    if not a:
        raise HTTPException(404, "Assessment not found")
    
    # Verify assessment belongs to the engagement
    if a.engagement_id != ctx["engagement_id"]:
        raise HTTPException(403, "Assessment not in this engagement")
    
    return a
