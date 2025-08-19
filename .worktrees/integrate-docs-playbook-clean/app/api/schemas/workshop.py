"""Workshop API Schemas for Request/Response Validation"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr


class AttendeeRequest(BaseModel):
    """Request model for workshop attendee"""
    user_id: str = Field(..., min_length=1, description="User identifier")
    email: EmailStr = Field(..., description="Attendee email address")
    role: str = Field(..., min_length=1, description="Attendee role in workshop")


class WorkshopCreateRequest(BaseModel):
    """Request model for creating a workshop"""
    engagement_id: str = Field(..., min_length=1, description="Engagement ID")
    title: str = Field(..., min_length=1, max_length=255, description="Workshop title")
    start_ts: Optional[datetime] = Field(None, description="Workshop start timestamp")
    attendees: List[AttendeeRequest] = Field(..., min_items=1, description="Workshop attendees")


class ConsentResponse(BaseModel):
    """Response model for consent record"""
    by: str = Field(..., description="User who gave consent")
    user_id: str = Field(..., description="User ID who gave consent")
    timestamp: datetime = Field(..., description="Consent timestamp")


class AttendeeResponse(BaseModel):
    """Response model for workshop attendee"""
    id: str = Field(..., description="Attendee ID")
    user_id: str = Field(..., description="User identifier")
    email: str = Field(..., description="Attendee email address")
    role: str = Field(..., description="Attendee role in workshop")
    consent: Optional[ConsentResponse] = Field(None, description="Consent record if given")


class WorkshopResponse(BaseModel):
    """Response model for workshop"""
    id: str = Field(..., description="Workshop ID")
    engagement_id: str = Field(..., description="Engagement ID")
    title: str = Field(..., description="Workshop title")
    start_ts: Optional[datetime] = Field(None, description="Workshop start timestamp")
    attendees: List[AttendeeResponse] = Field(..., description="Workshop attendees")
    created_by: str = Field(..., description="User who created the workshop")
    created_at: datetime = Field(..., description="Workshop creation timestamp")
    started: bool = Field(..., description="Whether workshop has started")
    started_at: Optional[datetime] = Field(None, description="Workshop start timestamp")


class ConsentRequest(BaseModel):
    """Request model for giving consent"""
    attendee_id: str = Field(..., min_length=1, description="Attendee ID to update")
    consent: bool = Field(True, description="Consent status (must be true)")
    
    @classmethod
    def model_validate(cls, v):
        """Validate that consent is true"""
        if isinstance(v, dict) and not v.get('consent'):
            raise ValueError("Consent must be true")
        return super().model_validate(v)


class WorkshopListResponse(BaseModel):
    """Response model for paginated workshop list"""
    workshops: List[WorkshopResponse] = Field(..., description="Workshop list")
    total_count: int = Field(..., description="Total number of workshops")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    has_more: bool = Field(..., description="Whether there are more pages")


class StartWorkshopResponse(BaseModel):
    """Response model for starting a workshop"""
    workshop: WorkshopResponse = Field(..., description="Updated workshop")
    message: str = Field(..., description="Success message")