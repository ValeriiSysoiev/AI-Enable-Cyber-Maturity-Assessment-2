from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse
import os, uuid, shutil
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from ...domain.repository import Repository
from ...domain.models import Document
from ..security import current_context, require_member, is_admin
from ...util.files import safe_join

class DocumentPublic(BaseModel):
    """Public document model that excludes the filesystem path"""
    id: str
    engagement_id: str
    filename: str
    content_type: Optional[str] = None
    size: int = 0
    uploaded_by: str
    uploaded_at: datetime

router = APIRouter(prefix="/engagements/{engagement_id}/docs", tags=["documents"])

def get_repo(request: Request) -> Repository:
    return request.app.state.repo

def _root_dir():
    return os.getenv("UPLOAD_ROOT", "data/engagements")

def _max_bytes():
    mb = int(os.getenv("MAX_UPLOAD_MB", "10"))
    return mb * 1024 * 1024

@router.post("", response_model=list[DocumentPublic])
async def upload_docs(engagement_id: str,
                      files: list[UploadFile] = File(...),
                      repo: Repository = Depends(get_repo),
                      ctx=Depends(current_context)):
    require_member(repo, {"user_email": ctx["user_email"], "engagement_id": engagement_id}, "member")
    saved = []
    base = _root_dir()
    updir = safe_join(base, engagement_id, "uploads")
    os.makedirs(updir, exist_ok=True)
    maxb = _max_bytes()
    for f in files:
        fname = os.path.basename(f.filename or f"upload-{uuid.uuid4().hex}")
        dest = safe_join(updir, f"{uuid.uuid4().hex}__{fname}")
        total = 0
        with open(dest, "wb") as out:
            while True:
                chunk = await f.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > maxb:
                    out.close()
                    try: os.remove(dest)
                    except: pass
                    raise HTTPException(status_code=413, detail="File too large")
                out.write(chunk)
        d = Document(
            engagement_id=engagement_id,
            filename=fname,
            content_type=f.content_type,
            size=total,
            path=os.path.abspath(dest),
            uploaded_by=ctx["user_email"],
        )
        repo.add_document(d)
        # Convert to public model excluding path
        public_doc = DocumentPublic(
            id=d.id,
            engagement_id=d.engagement_id,
            filename=d.filename,
            content_type=d.content_type,
            size=d.size,
            uploaded_by=d.uploaded_by,
            uploaded_at=d.uploaded_at
        )
        saved.append(public_doc)
    return saved

@router.get("", response_model=list[DocumentPublic])
def list_docs(engagement_id: str, repo: Repository = Depends(get_repo), ctx=Depends(current_context)):
    require_member(repo, {"user_email": ctx["user_email"], "engagement_id": engagement_id}, "member")
    documents = repo.list_documents(engagement_id)
    # Convert to public models excluding path
    return [
        DocumentPublic(
            id=d.id,
            engagement_id=d.engagement_id,
            filename=d.filename,
            content_type=d.content_type,
            size=d.size,
            uploaded_by=d.uploaded_by,
            uploaded_at=d.uploaded_at
        )
        for d in documents
    ]

@router.get("/{doc_id}")
def download_doc(engagement_id: str, doc_id: str, repo: Repository = Depends(get_repo), ctx=Depends(current_context)):
    require_member(repo, {"user_email": ctx["user_email"], "engagement_id": engagement_id}, "member")
    d = repo.get_document(engagement_id, doc_id)
    if not d: raise HTTPException(404, "Not found")
    if not os.path.exists(d.path): raise HTTPException(404, "File missing")
    return FileResponse(d.path, media_type=d.content_type or "application/octet-stream", filename=d.filename)

@router.delete("/{doc_id}")
def delete_doc(engagement_id: str, doc_id: str, repo: Repository = Depends(get_repo), ctx=Depends(current_context)):
    # lead or admin only
    mctx = {"user_email": ctx["user_email"], "engagement_id": engagement_id}
    if not is_admin(ctx["user_email"]):
        require_member(repo, mctx, "lead")
    ok = repo.delete_document(engagement_id, doc_id)
    if not ok: raise HTTPException(404, "Not found")
    return {"deleted": True}
