# app/api/main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from pathlib import Path
import json
import os
from typing import List, Dict
from .assist import router as assist_router
from .storage import router as storage_router
from .db import create_db_and_tables, get_session
from .models import Assessment, Answer
from .schemas import AssessmentCreate, AssessmentResponse, AnswerUpsert, ScoreResponse, PillarScore
from .scoring import compute_scores
from .routes import assessments as assessments_router, orchestrations as orchestrations_router, engagements as engagements_router, documents, summary, presets as presets_router
from ..domain.repository import InMemoryRepository
from ..domain.file_repo import FileRepository
from ..ai.llm import LLMClient
from ..ai.orchestrator import Orchestrator

app = FastAPI(title="AI Maturity Tool API", version="0.1.0")

# --- CORS configuration (env-driven) ---
_origins_env = os.getenv("API_ALLOWED_ORIGINS", "")
_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]
if not _origins:
    # Dev-safe fallback; prod will set explicit origin(s) via release script
    _origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  # allow custom headers like X-User-Email, X-Engagement-ID
    expose_headers=["Content-Disposition"],
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    # Wire up new domain dependencies
    app.state.repo = FileRepository()
    app.state.orchestrator = Orchestrator(LLMClient())
    
    # Initialize preset service
    from ..services import presets as preset_service
    preset_service.ensure_dirs()
    # register bundled presets if present
    try:
        bundled = {
            "cyber-for-ai": Path("app/config/presets/cyber-for-ai.json"),
            # add others here if you have them
        }
        preset_service.BUNDLED.update({k: v for k, v in bundled.items() if v.exists()})
    except Exception:
        pass



app.include_router(assist_router)
app.include_router(storage_router)
app.include_router(assessments_router.router)
app.include_router(orchestrations_router.router)
app.include_router(engagements_router.router)
app.include_router(documents.router)
app.include_router(summary.router)
app.include_router(presets_router.router)

def load_preset(preset_id: str) -> dict:
    # Use new preset service for consistency
    from ..services import presets as preset_service
    try:
        preset = preset_service.get_preset(preset_id)
        return preset.model_dump()
    except HTTPException as e:
        # Fallback to old bundled method for backwards compatibility
        preset_path = Path(__file__).resolve().parents[1] / "config" / "presets" / f"{preset_id}.json"
        if not preset_path.exists():
            raise FileNotFoundError(preset_path) from e
        return json.loads(preset_path.read_text(encoding="utf-8"))

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/assessments", response_model=AssessmentResponse)
def create_assessment(assessment: AssessmentCreate, session: Session = Depends(get_session)):
    """Create a new assessment"""
    # Verify preset exists
    try:
        load_preset(assessment.preset_id)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Invalid preset_id")
    
    db_assessment = Assessment(**assessment.dict())
    session.add(db_assessment)
    session.commit()
    session.refresh(db_assessment)
    
    return AssessmentResponse(
        id=db_assessment.id,
        name=db_assessment.name,
        preset_id=db_assessment.preset_id,
        created_at=db_assessment.created_at,
        answers=[]
    )


@app.get("/assessments/{assessment_id}", response_model=AssessmentResponse)
def get_assessment(assessment_id: str, session: Session = Depends(get_session)):
    """Get assessment with answers"""
    assessment = session.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    answers = [
        AnswerUpsert(
            pillar_id=ans.pillar_id,
            question_id=ans.question_id,
            level=ans.level,
            notes=ans.notes
        )
        for ans in assessment.answers
    ]
    
    return AssessmentResponse(
        id=assessment.id,
        name=assessment.name,
        preset_id=assessment.preset_id,
        created_at=assessment.created_at,
        answers=answers
    )


@app.post("/assessments/{assessment_id}/answers")
def upsert_answer(assessment_id: str, answer: AnswerUpsert, session: Session = Depends(get_session)):
    """Upsert an answer (insert or update by pillar_id and question_id)"""
    # Verify assessment exists
    assessment = session.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    # Find existing answer
    statement = select(Answer).where(
        Answer.assessment_id == assessment_id,
        Answer.pillar_id == answer.pillar_id,
        Answer.question_id == answer.question_id
    )
    existing = session.exec(statement).first()
    
    if existing:
        # Update existing
        existing.level = answer.level
        existing.notes = answer.notes
    else:
        # Create new
        db_answer = Answer(
            assessment_id=assessment_id,
            **answer.dict()
        )
        session.add(db_answer)
    
    session.commit()
    return {"status": "success"}


@app.get("/assessments/{assessment_id}/scores", response_model=ScoreResponse)
def get_scores(assessment_id: str, session: Session = Depends(get_session)):
    """Get scores for an assessment"""
    # Get assessment
    assessment = session.get(Assessment, assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    # Load preset
    try:
        preset = load_preset(assessment.preset_id)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Preset not found")
    
    # Group answers by pillar
    answers_by_pillar: Dict[str, List[Answer]] = {}
    for answer in assessment.answers:
        if answer.pillar_id not in answers_by_pillar:
            answers_by_pillar[answer.pillar_id] = []
        answers_by_pillar[answer.pillar_id].append(answer)
    
    # Compute scores
    pillar_scores_dict, overall_score, gates_applied = compute_scores(answers_by_pillar, preset)
    
    # Build response
    pillar_scores = []
    for pillar in preset["pillars"]:
        pillar_id = pillar["id"]
        total_questions = len(preset["questions"].get(pillar_id, []))
        questions_answered = len(answers_by_pillar.get(pillar_id, []))
        
        pillar_scores.append(PillarScore(
            pillar_id=pillar_id,
            score=pillar_scores_dict.get(pillar_id),
            weight=pillar["weight"],
            questions_answered=questions_answered,
            total_questions=total_questions
        ))
    
    return ScoreResponse(
        assessment_id=assessment_id,
        pillar_scores=pillar_scores,
        overall_score=overall_score,
        gates_applied=gates_applied
    )
