from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

Role = Literal["lead", "member"]

class Engagement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    client_code: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Membership(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    engagement_id: str
    user_email: str
    role: Role = "member"
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Assessment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    engagement_id: str
    framework: Literal["NIST-CSF", "ISO-27001", "CIS", "Custom"] = "NIST-CSF"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    assessment_id: str
    text: str
    pillar: Optional[str] = None

class Response(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    assessment_id: str
    question_id: str
    answer: str

class Finding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    assessment_id: str
    title: str
    evidence: Optional[str] = None
    severity: Literal["low", "medium", "high"] = "medium"
    area: Optional[str] = None  # e.g., Identity, Data, SecOps

class Recommendation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    assessment_id: str
    title: str
    rationale: Optional[str] = None
    priority: Literal["P1", "P2", "P3"] = "P2"
    effort: Literal["S", "M", "L"] = "M"
    timeline_weeks: Optional[int] = None

class RunLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    assessment_id: str
    agent: str  # "DocAnalyzer" | "GapRecommender" | etc.
    input_preview: Optional[str] = None
    output_preview: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    engagement_id: str
    filename: str
    content_type: Optional[str] = None
    size: int = 0
    path: str  # absolute or repo-root relative path on disk
    uploaded_by: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
