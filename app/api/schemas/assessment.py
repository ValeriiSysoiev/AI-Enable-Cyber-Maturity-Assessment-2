from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import datetime


class AssessmentCreate(BaseModel):
    """Schema for creating an assessment"""
    name: str
    preset_id: str


class AnswerUpsert(BaseModel):
    """Schema for upserting an answer"""
    pillar_id: str
    question_id: str
    level: int = Field(ge=1, le=5)
    notes: Optional[str] = None


class AssessmentResponse(BaseModel):
    """Schema for assessment response"""
    id: str
    name: str
    preset_id: str
    created_at: datetime
    answers: List[AnswerUpsert] = []


class PillarScore(BaseModel):
    """Schema for pillar score"""
    pillar_id: str
    score: Optional[float]
    weight: float
    questions_answered: int
    total_questions: int


class ScoreResponse(BaseModel):
    """Schema for scores response"""
    assessment_id: str
    pillar_scores: List[PillarScore]
    overall_score: Optional[float]
    gates_applied: List[str] = []


class EngagementCreate(BaseModel):
    """Schema for creating an engagement"""
    name: str = Field(..., min_length=1, description="Name of the engagement")
    client_code: Optional[str] = Field(None, description="Optional client code")


class AddMemberRequest(BaseModel):
    """Schema for adding a member to an engagement"""
    user_email: EmailStr = Field(..., description="Email of the user to add")
    role: Optional[Literal["member", "lead"]] = Field("member", description="Role of the member (member/lead)")
