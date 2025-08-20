from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import uuid

def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

class Document(BaseModel):
    document_id: str = Field(default_factory=lambda: gen_id("doc"))
    filename: str
    content: Optional[str] = None   # raw text (for MVP)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

class Project(BaseModel):
    project_id: str = Field(default_factory=lambda: gen_id("proj"))
    name: str
    standard: str = "NIST CSF 2.0"  # or ISO27001
    created_at: datetime = Field(default_factory=datetime.utcnow)
    documents: List[Document] = Field(default_factory=list)

class EvidenceItem(BaseModel):
    control: str
    description: str
    confidence: float = 0.6
    mcp_call_id: Optional[str] = None  # Track MCP operation that generated this evidence

class GapItem(BaseModel):
    control: str
    current: str = "Not Evidenced"
    target: str = "Defined"
    risk: str = "Medium"
    rationale: str
    mcp_call_id: Optional[str] = None  # Track MCP operation that generated this gap

class Initiative(BaseModel):
    title: str
    description: str
    related_controls: List[str]
    impact: int = 3  # 1-5
    effort: int = 3  # 1-5
    dependencies: List[str] = Field(default_factory=list)
    mcp_call_id: Optional[str] = None  # Track MCP operation that generated this initiative

class PrioritizedInitiative(BaseModel):
    title: str
    related_controls: List[str]
    impact: int
    effort: int
    score: float  # e.g., impact/effort
    rank: int

class RoadmapItem(BaseModel):
    title: str
    quarter: str  # e.g. "Q1", "Q2", "Q3", "Q4"
    depends_on: List[str] = Field(default_factory=list)

class Report(BaseModel):
    project_id: str
    summary_markdown: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    artifacts: Dict[str, str] = Field(default_factory=dict)  # filename -> path
    mcp_call_id: Optional[str] = None  # Track MCP operation that generated this report
