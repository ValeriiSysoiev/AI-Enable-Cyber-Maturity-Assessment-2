from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(title="Roadmap Planner Agent", version="0.1.0")

class Prioritized(BaseModel):
    title: str
    related_controls: List[str]
    impact: int
    effort: int
    score: float
    rank: int

class PlanRequest(BaseModel):
    prioritized: List[Prioritized]

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/plan")
def plan(req: PlanRequest):
    roadmap = []
    for p in req.prioritized:
        quarter = "Q1" if p.rank <= 2 else "Q2" if p.rank <= 4 else "Q3"
        roadmap.append({"title": p.title, "quarter": quarter, "depends_on": []})
    return {"roadmap": roadmap}
