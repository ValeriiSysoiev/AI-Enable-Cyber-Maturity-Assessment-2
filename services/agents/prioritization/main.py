from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(title="Prioritization Agent", version="0.1.0")

class Initiative(BaseModel):
    title: str
    description: str
    related_controls: List[str]
    impact: int = 3
    effort: int = 3

class PrioRequest(BaseModel):
    initiatives: List[Initiative]

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/prioritize")
def prioritize(req: PrioRequest):
    scored = []
    for it in req.initiatives:
        score = it.impact / max(1, it.effort)
        scored.append({
            "title": it.title,
            "related_controls": it.related_controls,
            "impact": it.impact,
            "effort": it.effort,
            "score": round(score, 2)
        })
    scored.sort(key=lambda x: (-x["score"], -x["impact"]))
    for i, s in enumerate(scored, start=1):
        s["rank"] = i
    return {"prioritized": scored}
