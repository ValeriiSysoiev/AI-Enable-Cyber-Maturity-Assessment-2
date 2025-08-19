import os, json, shutil
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

from common.models import Project, Document, Report

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")
ORCH_URL = os.environ.get("ORCHESTRATOR_URL", "http://localhost:8010")

os.makedirs(DATA_DIR, exist_ok=True)

app = FastAPI(title="Cyber AI Maturity – API Gateway", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

class NewProject(BaseModel):
    name: str
    standard: str = "NIST CSF 2.0"

def _project_path(project_id: str) -> str:
    return os.path.join(DATA_DIR, "projects", project_id)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/projects", response_model=Project)
def create_project(payload: NewProject):
    project = Project(name=payload.name, standard=payload.standard)
    pdir = _project_path(project.project_id)
    os.makedirs(pdir, exist_ok=True)
    with open(os.path.join(pdir, "project.json"), "w", encoding="utf-8") as f:
        f.write(project.model_dump_json(indent=2))
    return project

@app.get("/projects", response_model=List[Project])
def list_projects():
    projects_dir = os.path.join(DATA_DIR, "projects")
    if not os.path.exists(projects_dir):
        return []
    out = []
    for pid in os.listdir(projects_dir):
        pjson = os.path.join(projects_dir, pid, "project.json")
        if os.path.exists(pjson):
            with open(pjson, "r", encoding="utf-8") as f:
                out.append(Project.model_validate_json(f.read()))
    return out

@app.post("/projects/{project_id}/documents", response_model=Document)
def upload_document(project_id: str, file: UploadFile = File(...)):
    pdir = _project_path(project_id)
    if not os.path.exists(pdir):
        raise HTTPException(404, "Project not found")
    docs_dir = os.path.join(pdir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    dest_path = os.path.join(docs_dir, file.filename)
    with open(dest_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    # Load content if text-ish
    content = None
    if file.filename.lower().endswith((".txt", ".md")):
        with open(dest_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

    # Update project record
    pjson = os.path.join(pdir, "project.json")
    with open(pjson, "r", encoding="utf-8") as f:
        project = Project.model_validate_json(f.read())
    doc = Document(filename=file.filename, content=content)
    project.documents.append(doc)
    with open(pjson, "w", encoding="utf-8") as f:
        f.write(project.model_dump_json(indent=2))

    return doc

@app.post("/projects/{project_id}/analyze")
def analyze_project(project_id: str):
    r = requests.post(f"{ORCH_URL}/orchestrate/analyze", json={"project_id": project_id})
    if r.status_code != 200:
        raise HTTPException(r.status_code, r.text)
    return r.json()

@app.get("/projects/{project_id}/report", response_model=Report)
def get_report(project_id: str):
    pdir = _project_path(project_id)
    rep_path = os.path.join(pdir, "report.json")
    if not os.path.exists(rep_path):
        raise HTTPException(404, "Report not found. Run analysis first.")
    with open(rep_path, "r", encoding="utf-8") as f:
        return Report.model_validate_json(f.read())
