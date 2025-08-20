import os, json, time, glob, logging
import requests
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from common.models import Project, Report
from mcp_client import create_mcp_client, IMcpClient, generate_correlation_id

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")

DOC_ANALYZER = os.environ.get("DOC_ANALYZER_URL", "http://localhost:8111")
GAP_ANALYSIS = os.environ.get("GAP_ANALYSIS_URL", "http://localhost:8121")
INITIATIVE   = os.environ.get("INITIATIVE_URL",   "http://localhost:8131")
PRIORITIZE   = os.environ.get("PRIORITIZATION_URL","http://localhost:8141")
ROADMAP      = os.environ.get("ROADMAP_URL",      "http://localhost:8151")
REPORT       = os.environ.get("REPORT_URL",       "http://localhost:8161")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Orchestrator", version="0.1.0")

# Initialize MCP client
mcp_client: IMcpClient = create_mcp_client()
mcp_enabled = os.environ.get("MCP_ENABLED", "false").lower() == "true"

def _project_path(project_id: str) -> str:
    return os.path.join(DATA_DIR, "projects", project_id)

async def _call_service_or_mcp(service_url: str, endpoint: str, payload: Dict[str, Any], 
                              mcp_tool: str, engagement_id: str, corr_id: str) -> Dict[str, Any]:
    """
    Call either MCP tool or fallback to direct service call.
    
    Args:
        service_url: Direct service URL for fallback
        endpoint: Service endpoint path
        payload: Request payload
        mcp_tool: MCP tool name
        engagement_id: Engagement ID for tracking
        corr_id: Correlation ID for logging
        
    Returns:
        Service response with optional mcp_call_id
    """
    if mcp_enabled:
        try:
            logger.info(
                f"Attempting MCP call for {mcp_tool}",
                extra={"corr_id": corr_id, "engagement_id": engagement_id}
            )
            result = await mcp_client.call(mcp_tool, payload, engagement_id)
            logger.info(
                f"MCP call successful for {mcp_tool}",
                extra={
                    "corr_id": corr_id, 
                    "engagement_id": engagement_id,
                    "mcp_call_id": result.get("mcp_call_id")
                }
            )
            return result
        except Exception as e:
            logger.warning(
                f"MCP call failed for {mcp_tool}, falling back to direct service",
                extra={
                    "corr_id": corr_id,
                    "engagement_id": engagement_id,
                    "error": str(e)
                }
            )
    
    # Fallback to direct service call
    logger.info(
        f"Using direct service call for {endpoint}",
        extra={"corr_id": corr_id, "engagement_id": engagement_id}
    )
    
    response = requests.post(f"{service_url}/{endpoint}", json=payload)
    response.raise_for_status()
    result = response.json()
    
    # Add tracking field to indicate direct service call
    result["mcp_call_id"] = None
    
    return result


class OrchestrateRequest(BaseModel):
    project_id: str
    engagement_id: Optional[str] = None  # Optional engagement tracking

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/orchestrate/analyze")
async def orchestrate(req: OrchestrateRequest):
    # Generate correlation ID for request tracking
    corr_id = generate_correlation_id()
    engagement_id = req.engagement_id or f"eng_{req.project_id[:8]}"
    
    logger.info(
        "Orchestration started",
        extra={
            "corr_id": corr_id,
            "engagement_id": engagement_id,
            "project_id": req.project_id,
            "mcp_enabled": mcp_enabled
        }
    )
    
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

    # Call Documentation Analyzer via MCP or direct service
    da = await _call_service_or_mcp(
        DOC_ANALYZER, "analyze", 
        {"documents": doc_texts},
        "analyze_documents", engagement_id, corr_id
    )

    # 2) Gap Analysis via MCP or direct service
    gaps = await _call_service_or_mcp(
        GAP_ANALYSIS, "analyze",
        {"standard": project.standard, "evidence": da.get("evidence", [])},
        "gap_analysis", engagement_id, corr_id
    )

    # 3) Initiatives via MCP or direct service
    inits = await _call_service_or_mcp(
        INITIATIVE, "generate",
        {"gaps": gaps["gaps"]},
        "initiative_generation", engagement_id, corr_id
    )

    # 4) Prioritization via MCP or direct service
    prio = await _call_service_or_mcp(
        PRIORITIZE, "prioritize",
        {"initiatives": inits["initiatives"]},
        "prioritization", engagement_id, corr_id
    )

    # 5) Roadmap via MCP or direct service
    road = await _call_service_or_mcp(
        ROADMAP, "plan",
        {"prioritized": prio["prioritized"]},
        "roadmap_planning", engagement_id, corr_id
    )

    # 6) Report via MCP or direct service
    rep = await _call_service_or_mcp(
        REPORT, "generate",
        {
            "project_id": project.project_id,
            "project_name": project.name,
            "standard": project.standard,
            "evidence": da.get("evidence", []),
            "gaps": gaps["gaps"],
            "initiatives": prio["prioritized"],
            "roadmap": road["roadmap"]
        },
        "report_generation", engagement_id, corr_id
    )

    # Persist report
    with open(os.path.join(pdir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)

    logger.info(
        "Orchestration completed",
        extra={
            "corr_id": corr_id,
            "engagement_id": engagement_id,
            "project_id": req.project_id,
            "evidence_count": len(da.get("evidence", [])),
            "gaps_count": len(gaps["gaps"]),
            "initiatives_count": len(prio["prioritized"])
        }
    )

    return {
        "status": "ok", 
        "summary": {
            "evidence": len(da.get("evidence", [])), 
            "gaps": len(gaps["gaps"]), 
            "initiatives": len(prio["prioritized"])
        },
        "mcp_enabled": mcp_enabled,
        "engagement_id": engagement_id,
        "correlation_id": corr_id
    }
