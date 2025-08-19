import os, json, time, glob
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

from common.models import Project, Report

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")

DOC_ANALYZER = os.environ.get("DOC_ANALYZER_URL", "http://localhost:8111")
GAP_ANALYSIS = os.environ.get("GAP_ANALYSIS_URL", "http://localhost:8121")
INITIATIVE   = os.environ.get("INITIATIVE_URL",   "http://localhost:8131")
PRIORITIZE   = os.environ.get("PRIORITIZATION_URL","http://localhost:8141")
ROADMAP      = os.environ.get("ROADMAP_URL",      "http://localhost:8151")
REPORT       = os.environ.get("REPORT_URL",       "http://localhost:8161")

app = FastAPI(title="AI Orchestrator", version="0.1.0")

def _project_path(project_id: str) -> str:
    return os.path.join(DATA_DIR, "projects", project_id)

class OrchestrateRequest(BaseModel):
    project_id: str

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/orchestrate/analyze")
def orchestrate(req: OrchestrateRequest):
    pdir = _project_path(req.project_id)
    pjson = os.path.join(pdir, "project.json")
    if not os.path.exists(pjson):
        raise HTTPException(404, "Project not found")

    with open(pjson, "r", encoding="utf-8") as f:
        project = Project.model_validate_json(f.read())

    # 1) Documentation Analyzer over all docs
    docs_dir = os.path.join(pdir, "docs")
    doc_texts = []
    if os.path.exists(docs_dir):
        for doc in project.documents:
            # prefer stored content; fallback to reading file
            if doc.content:
                doc_texts.append({"filename": doc.filename, "content": doc.content})
            else:
                fpath = os.path.join(docs_dir, doc.filename)
                if os.path.exists(fpath):
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as ftxt:
                            doc_texts.append({"filename": doc.filename, "content": ftxt.read()})
                    except Exception:
                        pass

    da = requests.post(f"{DOC_ANALYZER}/analyze", json={"documents": doc_texts}).json()

    # 2) Gap Analysis
    gaps = requests.post(f"{GAP_ANALYSIS}/analyze", json={
        "standard": project.standard,
        "evidence": da.get("evidence", [])
    }).json()

    # 3) Initiatives
    inits = requests.post(f"{INITIATIVE}/generate", json={"gaps": gaps["gaps"]}).json()

    # 4) Prioritization
    prio = requests.post(f"{PRIORITIZE}/prioritize", json={"initiatives": inits["initiatives"]}).json()

    # 5) Roadmap
    road = requests.post(f"{ROADMAP}/plan", json={"prioritized": prio["prioritized"]}).json()

    # 6) Report
    rep = requests.post(f"{REPORT}/generate", json={
        "project_id": project.project_id,
        "project_name": project.name,
        "standard": project.standard,
        "evidence": da.get("evidence", []),
        "gaps": gaps["gaps"],
        "initiatives": prio["prioritized"],
        "roadmap": road["roadmap"]
    }).json()

    # Persist report
    with open(os.path.join(pdir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)

    return {"status": "ok", "summary": {"evidence": len(da.get("evidence", [])), "gaps": len(gaps["gaps"]), "initiatives": len(prio["prioritized"]) }}
