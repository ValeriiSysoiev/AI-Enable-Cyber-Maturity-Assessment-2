from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, List
from datetime import datetime
import uuid

class Assessment(SQLModel, table=True):
    """Assessment database model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    preset_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship
    answers: List["Answer"] = Relationship(back_populates="assessment")


class Answer(SQLModel, table=True):
    """Answer database model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    assessment_id: str = Field(foreign_key="assessment.id")
    pillar_id: str
    question_id: str
    level: int = Field(ge=1, le=5)
    notes: Optional[str] = None
    
    # Relationship
    assessment: Optional[Assessment] = Relationship(back_populates="answers")














