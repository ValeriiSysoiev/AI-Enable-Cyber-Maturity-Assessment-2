from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict

app = FastAPI(title="Initiative Generation Agent", version="0.1.0")

class GapItem(BaseModel):
    control: str
    current: str = "Not Evidenced"
    target: str = "Defined"
    risk: str = "Medium"
    rationale: str

class InitRequest(BaseModel):
    gaps: List[GapItem]

@app.get("/health")
def health():
    return {"ok": True}

def propose_initiatives_for_gap(gap: GapItem):
    ctl = gap.control
    if ctl == "ID.AM-1":
        return [{
            "title": "Establish Asset Inventory",
            "description": "Deploy a centralized CMDB and implement auto-discovery.",
            "related_controls": [ctl],
            "impact": 4, "effort": 3
        }]
    if ctl == "ID.GV-1":
        return [{
            "title": "Formalize Security Governance",
            "description": "Define ISMS governance charter, roles, and review cadence.",
            "related_controls": [ctl],
            "impact": 5, "effort": 2
        }]
    if ctl == "PR.AC-1":
        return [{
            "title": "Implement RBAC & MFA",
            "description": "Harden IAM with RBAC, SSO/MFA, and periodic access reviews.",
            "related_controls": [ctl],
            "impact": 5, "effort": 3
        }]
    if ctl == "DE.DP-1":
        return [{
            "title": "SIEM Detection Use-Cases",
            "description": "Onboard logs to Sentinel/Splunk and build detections.",
            "related_controls": [ctl],
            "impact": 4, "effort": 3
        }]
    if ctl == "RS.RP-1":
        return [{
            "title": "Incident Response Playbooks",
            "description": "Create and test IR playbooks with annual tabletop exercises.",
            "related_controls": [ctl],
            "impact": 4, "effort": 2
        }]
    return [{
        "title": f"Improve control {ctl}",
        "description": "Define, implement, and monitor control baseline.",
        "related_controls": [ctl], "impact": 3, "effort": 3
    }]

@app.post("/generate")
def generate(req: InitRequest):
    initiatives = []
    for gap in req.gaps:
        initiatives.extend(propose_initiatives_for_gap(gap))
    return {"initiatives": initiatives}
