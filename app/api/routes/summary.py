import sys
sys.path.append("/app")
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from datetime import datetime
from typing import List

from domain.repository import Repository
from api.security import current_context, require_member
from api.schemas import EngagementSummary, CountSummary, ActivityItem

router = APIRouter(prefix="/api/engagements/{engagement_id}", tags=["summary"])

def get_repo(request: Request) -> Repository:
    return request.app.state.repo

@router.get("/summary", response_model=EngagementSummary)
def get_summary(engagement_id: str, request: Request, repo: Repository = Depends(get_repo), ctx = Depends(current_context)):
    require_member(repo, {"user_email": ctx["user_email"], "engagement_id": engagement_id}, "member")

    # Gather
    assessments = repo.list_assessments(engagement_id) if hasattr(repo, "list_assessments") else []
    docs = repo.list_documents(engagement_id) if hasattr(repo, "list_documents") else []
    findings = repo.get_findings(engagement_id) if hasattr(repo, "get_findings") else []
    recs = repo.get_recommendations(engagement_id) if hasattr(repo, "get_recommendations") else []
    runlogs = repo.get_runlogs(engagement_id) if hasattr(repo, "get_runlogs") else []

    counts = CountSummary(
        assessments=len(assessments),
        documents=len(docs),
        findings=len(findings),
        recommendations=len(recs),
        runlogs=len(runlogs),
    )

    # Activity stream
    events: List[ActivityItem] = []
    def _ts(o: Any) -> Optional[str]:
        return getattr(o, "created_at", None) or getattr(o, "uploaded_at", None) or getattr(o, "ts", None) or getattr(o, "timestamp", None)

    for a in assessments[:50]:
        events.append(ActivityItem(type="assessment", id=getattr(a,"id",""), ts=_ts(a), title=getattr(a,"name",None)))
    for d in docs[:50]:
        events.append(ActivityItem(type="document", id=getattr(d,"id",""), ts=_ts(d), title=getattr(d,"filename",None)))
    for f in findings[:50]:
        events.append(ActivityItem(type="finding", id=getattr(f,"id",""), ts=_ts(f), title=getattr(f,"title",None)))
    for r in recs[:50]:
        events.append(ActivityItem(type="recommendation", id=getattr(r,"id",""), ts=_ts(r), title=getattr(r,"title",None)))
    for lg in runlogs[:50]:
        preview = (getattr(lg, "message", "") or "")[:140]
        events.append(ActivityItem(type="runlog", id=getattr(lg,"id",""), ts=_ts(lg), title=preview))

    # Sort desc by ts
    events = sorted(events, key=lambda e: e.ts or datetime.min, reverse=True)
    last_ts = events[0].ts if events else None

    # Build runlog excerpt
    recent_runlog_excerpt = None
    if runlogs:
        try:
            recent = sorted(runlogs, key=lambda lg: _ts(lg) or datetime.min, reverse=True)[0]
            msg = getattr(recent, "message", None)
            if msg:
                recent_runlog_excerpt = msg[:400]
        except Exception:
            pass

    return EngagementSummary(
        engagement_id=engagement_id,
        counts=counts,
        last_activity=last_ts,
        recent_activity=events[:20],
        recent_runlog_excerpt=recent_runlog_excerpt
    )

@router.get("/exports/report.md")
def export_report_md(engagement_id: str, request: Request, repo: Repository = Depends(get_repo), ctx = Depends(current_context)):
    require_member(repo, {"user_email": ctx["user_email"], "engagement_id": engagement_id}, "member")

    assessments = repo.list_assessments(engagement_id) if hasattr(repo, "list_assessments") else []
    docs = repo.list_documents(engagement_id) if hasattr(repo, "list_documents") else []
    findings = repo.get_findings(engagement_id) if hasattr(repo, "get_findings") else []
    recs = repo.get_recommendations(engagement_id) if hasattr(repo, "get_recommendations") else []
    runlogs = repo.get_runlogs(engagement_id) if hasattr(repo, "get_runlogs") else []

    def _fmt_dt(dt):
        try:
            return dt.isoformat(timespec="seconds")+"Z"
        except Exception:
            return ""

    lines = []
    lines.append(f"# Engagement Report")
    lines.append("")
    lines.append(f"**Engagement ID:** `{engagement_id}`")
    lines.append(f"**Generated:** `{datetime.utcnow().isoformat(timespec='seconds')}Z`")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Assessments: **{len(assessments)}**")
    lines.append(f"- Documents: **{len(docs)}**")
    lines.append(f"- Findings: **{len(findings)}**")
    lines.append(f"- Recommendations: **{len(recs)}**")
    lines.append("")
    if assessments:
        lines.append("## Assessments")
        for a in assessments[:50]:
            nm = getattr(a, 'name', '')
            aid = getattr(a, 'id', '')
            ts = getattr(a, 'created_at', None)
            lines.append(f"- **{nm}** (`{aid}`) {('— ' + _fmt_dt(ts)) if ts else ''}")
        lines.append("")
    if findings:
        lines.append("## Top Findings (max 20)")
        for f in findings[:20]:
            tt = getattr(f, 'title', '') or getattr(f, 'id', '')
            sev = getattr(f, 'severity', None)
            lines.append(f"- {tt}{(' — severity: ' + str(sev)) if sev is not None else ''}")
        lines.append("")
    if recs:
        lines.append("## Top Recommendations (max 20)")
        for r in recs[:20]:
            tt = getattr(r, 'title', '') or getattr(r, 'id', '')
            pri = getattr(r, 'priority', None)
            lines.append(f"- {tt}{(' — priority: ' + str(pri)) if pri is not None else ''}")
        lines.append("")
    if runlogs:
        lines.append("## Recent Run Logs (max 10)")
        for lg in sorted(runlogs, key=lambda x: getattr(x, 'timestamp', None) or getattr(x, 'ts', None) or datetime.min, reverse=True)[:10]:
            ts = getattr(lg, 'timestamp', None) or getattr(lg, 'ts', None)
            msg = getattr(lg, 'message', '')[:200].replace('\n',' ')
            lines.append(f"- { _fmt_dt(ts) if ts else '' } — {msg}")
        lines.append("")
    if docs:
        lines.append("## Documents (max 20)")
        for d in docs[:20]:
            nm = getattr(d, 'filename', '')
            sz = getattr(d, 'size', 0)
            ts = getattr(d, 'uploaded_at', None)
            lines.append(f"- {nm} — {sz} bytes {('— ' + _fmt_dt(ts)) if ts else ''}")
        lines.append("")

    md = "\n".join(lines)
    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")
