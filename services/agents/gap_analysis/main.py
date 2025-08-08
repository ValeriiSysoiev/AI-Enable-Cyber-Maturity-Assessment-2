from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI(title="Gap Analysis Agent", version="0.1.0")

class EvidenceItem(BaseModel):
    control: str
    description: str
    confidence: float = 0.6

class GapItem(BaseModel):
    control: str
    current: str = "Not Evidenced"
    target: str = "Defined"
    risk: str = "Medium"
    rationale: str

class GapRequest(BaseModel):
    standard: str = "NIST CSF 2.0"
    evidence: List[EvidenceItem]

TARGET_CONTROLS = ["ID.AM-1", "ID.GV-1", "PR.AC-1", "DE.DP-1", "RS.RP-1"]

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/analyze")
def analyze(req: GapRequest):
    present_controls = {e.control for e in req.evidence}
    gaps: List[GapItem] = []
    for ctl in TARGET_CONTROLS:
        if ctl not in present_controls:
            gaps.append(GapItem(control=ctl, rationale=f"No evidence detected for {ctl}"))
    return {"gaps": [g.model_dump() for g in gaps]}
