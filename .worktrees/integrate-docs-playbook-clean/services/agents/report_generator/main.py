from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime

app = FastAPI(title="Report Generator Agent", version="0.1.0")

class Evidence(BaseModel):
    control: str
    description: str
    confidence: float

class Gap(BaseModel):
    control: str
    current: str
    target: str
    risk: str
    rationale: str

class Initiative(BaseModel):
    title: str
    related_controls: List[str]
    impact: int
    effort: int
    score: float
    rank: int

class RoadmapItem(BaseModel):
    title: str
    quarter: str
    depends_on: List[str] = []

class GenerateRequest(BaseModel):
    project_id: str
    project_name: str
    standard: str
    evidence: List[Evidence]
    gaps: List[Gap]
    initiatives: List[Initiative]
    roadmap: List[RoadmapItem]

@app.get("/health")
def health():
    return {"ok": True}

def md_section(title: str, body: str) -> str:
    return f"## {title}\n\n{body}\n\n"

@app.post("/generate")
def generate(req: GenerateRequest):
    # Very lightweight markdown summary for MVP
    md = f"# Cyber Maturity Assessment – {req.project_name}\n\n"
    md += f"**Standard:** {req.standard}  \n"
    md += f"**Generated:** {datetime.utcnow().isoformat()}Z\n\n"

    md += md_section("Evidence", "\n".join([f"- **{e.control}**: {e.description} (confidence {e.confidence})" for e in req.evidence]) or "_None_")
    md += md_section("Gaps", "\n".join([f"- **{g.control}**: {g.current} → {g.target}. Risk: {g.risk}. {g.rationale}" for g in req.gaps]) or "_None_")
    md += md_section("Prioritized Initiatives", "\n".join([f"{i.rank}. **{i.title}** (Ctrls: {', '.join(i.related_controls)}; Impact {i.impact}, Effort {i.effort}, Score {i.score})" for i in req.initiatives]) or "_None_")
    md += md_section("Roadmap", "\n".join([f"- **{r.title}** → {r.quarter}" for r in req.roadmap]) or "_None_")

    return {"project_id": req.project_id, "summary_markdown": md, "artifacts": {}}
