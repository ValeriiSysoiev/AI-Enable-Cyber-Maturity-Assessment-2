from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
import re

app = FastAPI(title="Documentation Analyzer", version="0.1.0")

class Doc(BaseModel):
    filename: str
    content: str

class AnalyzeRequest(BaseModel):
    documents: List[Doc]

@app.get("/health")
def health():
    return {"ok": True}

# Very naive keyword-based "evidence" extraction for MVP
KEYWORDS = {
    "ID.AM-1": ["asset", "inventory", "device", "system list"],
    "ID.GV-1": ["policy", "governance", "committee", "charter"],
    "PR.AC-1": ["access control", "iam", "rbac", "mfa", "sso"],
    "DE.DP-1": ["monitoring", "detection", "siem", "splunk", "sentinel"],
    "RS.RP-1": ["incident", "playbook", "response plan", "pagerduty", "dispatch"]
}

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    evidence = []
    for doc in req.documents:
        text = doc.content.lower()
        for control, words in KEYWORDS.items():
            if any(w in text for w in words):
                snippet = next((line.strip() for line in text.splitlines() if any(w in line for w in words)), "evidence found")
                evidence.append({
                    "control": control,
                    "description": f"{doc.filename}: contains keywords suggesting {control}",
                    "confidence": 0.7,
                    "snippet": snippet[:180]
                })
    return {"evidence": evidence}
