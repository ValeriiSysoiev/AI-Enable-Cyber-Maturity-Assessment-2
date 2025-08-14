from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict
from ...domain.models import Finding, Recommendation
from ...domain.repository import Repository
from ...ai.orchestrator import Orchestrator
from ..security import current_context, require_member
from ...util.files import extract_text

router = APIRouter(prefix="/orchestrations", tags=["orchestrations"])

def get_repo(request: Request) -> Repository:
    return request.app.state.repo

def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator

class AnalyzeRequest(BaseModel):
    assessment_id: str
    content: str

class AnalyzeResponse(BaseModel):
    findings: List[Finding]

@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(
    req: AnalyzeRequest, 
    repo: Repository = Depends(get_repo), 
    orch: Orchestrator = Depends(get_orchestrator),
    ctx: Dict[str, str] = Depends(current_context)
):
    # Ensure user is a member of the engagement
    require_member(repo, ctx, "member")
    
    # Get and verify assessment
    assessment = repo.get_assessment(req.assessment_id)
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    
    # Verify assessment belongs to the engagement
    if assessment.engagement_id != ctx["engagement_id"]:
        raise HTTPException(403, "Assessment not in this engagement")
    
    findings, log = orch.analyze(req.assessment_id, req.content)
    repo.add_findings(req.assessment_id, findings)
    repo.add_runlog(log)
    return AnalyzeResponse(findings=findings)

class RecommendRequest(BaseModel):
    assessment_id: str

class RecommendResponse(BaseModel):
    recommendations: List[Recommendation]

@router.post("/recommend", response_model=RecommendResponse)
def recommend(
    req: RecommendRequest, 
    repo: Repository = Depends(get_repo), 
    orch: Orchestrator = Depends(get_orchestrator),
    ctx: Dict[str, str] = Depends(current_context)
):
    # Ensure user is a member of the engagement
    require_member(repo, ctx, "member")
    
    # Get and verify assessment
    assessment = repo.get_assessment(req.assessment_id)
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    
    # Verify assessment belongs to the engagement
    if assessment.engagement_id != ctx["engagement_id"]:
        raise HTTPException(403, "Assessment not in this engagement")
    
    # Get findings for this engagement
    findings = [f for f in repo.get_findings(ctx["engagement_id"]) if f.assessment_id == req.assessment_id]
    if not findings:
        raise HTTPException(400, "No findings available; run analyze first")
    
    findings_text = "\n".join(f"- [{f.severity}] {f.area or 'General'}: {f.title}" for f in findings)
    recs, log = orch.recommend(req.assessment_id, findings_text)
    repo.add_recommendations(req.assessment_id, recs)
    repo.add_runlog(log)
    return RecommendResponse(recommendations=recs)


@router.get("/runlogs")
def get_runlogs(
    repo: Repository = Depends(get_repo),
    ctx: Dict[str, str] = Depends(current_context)
):
    """Get runlogs for the current engagement"""
    # Ensure user is a member of the engagement
    require_member(repo, ctx, "member")
    
    return repo.get_runlogs(ctx["engagement_id"])


class AnalyzeDocRequest(BaseModel):
    doc_id: str


@router.post("/analyze-doc")
def analyze_doc(
    payload: AnalyzeDocRequest,
    request: Request,
    repo: Repository = Depends(get_repo),
    ctx: Dict[str, str] = Depends(current_context)
):
    require_member(repo, ctx, "member")
    engagement_id = ctx["engagement_id"]
    doc_id = payload.doc_id
    
    if not doc_id:
        raise HTTPException(400, "doc_id required")
    
    doc = repo.get_document(engagement_id, doc_id)
    if not doc:
        raise HTTPException(404, "Doc not found")
    
    ex = extract_text(doc.path, doc.content_type)
    if not ex.text:
        return {"analyzed": False, "note": ex.note or "No text extracted"}
    
    # Create a new assessment for this document analysis
    from ...domain.models import Assessment
    assessment = Assessment(
        name=f"Doc Analysis: {doc.filename}",
        engagement_id=engagement_id,
        framework="Custom"
    )
    repo.create_assessment(assessment)
    
    # Reuse existing analyze logic with the orchestrator
    orch = request.app.state.orchestrator if hasattr(request.app.state, "orchestrator") else None
    if not orch:
        raise HTTPException(500, "Orchestrator not configured")
    
    findings, log = orch.analyze(assessment.id, ex.text)
    repo.add_findings(assessment.id, findings)
    repo.add_runlog(log)
    
    return {
        "analyzed": True, 
        "note": ex.note, 
        "assessment_id": assessment.id,
        "findings_count": len(findings)
    }
