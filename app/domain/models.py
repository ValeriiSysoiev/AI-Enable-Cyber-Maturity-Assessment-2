from __future__ import annotations
from typing import List, Optional, Literal, Dict, Any
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

class Evidence(BaseModel):
    """Evidence file record with checksum and PII detection"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    engagement_id: str
    blob_path: str  # Path in blob storage: engagements/{engagementId}/evidence/{uuid}/{filename}
    filename: str
    checksum_sha256: str  # Server-computed SHA-256 checksum
    size: int  # File size in bytes
    mime_type: str  # Content type
    uploaded_by: str  # User email who uploaded
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pii_flag: bool = False  # True if PII heuristics detected potential PII
    
    # Optional links to assessment items (many-to-many)
    linked_items: List[Dict[str, str]] = Field(default_factory=list)  # [{"itemType": "assessment", "itemId": "uuid"}]

class EmbeddingDocument(BaseModel):
    """Vector embedding document for RAG storage"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    engagement_id: str
    doc_id: str  # Reference to original Document
    chunk_id: str  # Unique identifier for this chunk
    vector: List[float]  # Embedding vector
    text: str  # Text content of the chunk
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Additional metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Chunk-specific metadata
    chunk_index: int = 0
    chunk_start: int = 0
    chunk_end: int = 0
    token_count: Optional[int] = None
    
    # Source document metadata
    filename: str = ""
    uploaded_by: str = ""
    uploaded_at: Optional[datetime] = None
    
    # Embedding metadata
    model: str = ""
    embedding_created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ServiceBusMessage(BaseModel):
    """Service Bus message for orchestration queuing"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # Message type for routing (e.g., "ingest", "minutes", "score")
    payload: Dict[str, Any]  # Message payload
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Retry handling
    retry_count: int = 0
    max_retries: int = 3
    
    # Dead letter queue support
    is_dead_lettered: bool = False
    dead_letter_reason: Optional[str] = None
    
    # Processing metadata
    processed_at: Optional[datetime] = None
    processed_by: Optional[str] = None
    
    # Engagement context
    engagement_id: Optional[str] = None
    user_email: Optional[str] = None


class QueueConfig(BaseModel):
    """Queue configuration with DLQ support"""
    name: str
    max_delivery_count: int = 3
    ttl_seconds: int = 3600  # 1 hour
    enable_dead_letter_queue: bool = True
    dead_letter_queue_name: str = Field(default_factory=lambda: "")
    
    def __post_init__(self):
        if not self.dead_letter_queue_name and self.enable_dead_letter_queue:
            self.dead_letter_queue_name = f"{self.name}-dlq"

class CSFSubcategory(BaseModel):
    """CSF 2.0 Subcategory model"""
    id: str
    function_id: str
    category_id: str
    title: str
    description: str

class CSFCategory(BaseModel):
    """CSF 2.0 Category model"""
    id: str
    function_id: str
    title: str
    description: str
    subcategories: List[CSFSubcategory] = Field(default_factory=list)

class CSFFunction(BaseModel):
    """CSF 2.0 Function model"""
    id: str
    title: str
    description: str
    categories: List[CSFCategory] = Field(default_factory=list)

class ConsentRecord(BaseModel):
    """Attendee consent record for workshops"""
    by: str  # User who gave consent (typically same as attendee email)
    user_id: str  # User ID who gave consent
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class WorkshopAttendee(BaseModel):
    """Workshop attendee information"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # User identifier
    email: str
    role: str  # attendee role in workshop
    consent: Optional[ConsentRecord] = None

class Workshop(BaseModel):
    """Workshop for engagement activities requiring consent"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    engagement_id: str
    title: str
    start_ts: Optional[datetime] = None
    attendees: List[WorkshopAttendee] = Field(default_factory=list)
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started: bool = False
    started_at: Optional[datetime] = None
