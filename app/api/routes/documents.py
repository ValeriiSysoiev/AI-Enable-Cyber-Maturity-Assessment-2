from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, BackgroundTasks
from fastapi.responses import FileResponse
import os, uuid, shutil, logging
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, List

from domain.repository import Repository
from domain.models import Document
from ..security import current_context, require_member, is_admin
from ...util.files import safe_join, extract_text
from ...services.rag import create_rag_service, IngestionStatus, SearchResult
from ...config import config

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


# RAG-related models and endpoints

class IngestionStatusResponse(BaseModel):
    """Response model for document ingestion status"""
    document_id: str
    status: str
    chunks_processed: int
    total_chunks: int
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class BulkIngestionStatusResponse(BaseModel):
    """Response model for bulk ingestion status"""
    engagement_id: str
    documents: List[IngestionStatusResponse]
    summary: Dict[str, int]


class SearchDocumentsRequest(BaseModel):
    """Request model for document search"""
    query: str
    top_k: Optional[int] = None


class SearchDocumentsResponse(BaseModel):
    """Response model for document search"""
    query: str
    results: List[Dict[str, Any]]
    total_results: int
    engagement_id: str


logger = logging.getLogger(__name__)


def get_correlation_id(request: Request) -> str:
    """Extract correlation ID from request headers"""
    return request.headers.get(config.logging.correlation_id_header, str(uuid.uuid4()))


async def _ingest_document_background(
    document: Document, 
    correlation_id: str
):
    """Background task for document ingestion"""
    try:
        # Extract text content
        extract_result = extract_text(document.path, document.content_type)
        if not extract_result.text:
            logger.warning(
                "No text extracted from document",
                extra={
                    "correlation_id": correlation_id,
                    "document_id": document.id,
                    "filename": document.filename,
                    "note": extract_result.note
                }
            )
            return
        
        # Create RAG service and ingest
        rag_service = create_rag_service(correlation_id)
        await rag_service.ingest_document(document, extract_result.text)
        
    except Exception as e:
        logger.error(
            "Background document ingestion failed",
            extra={
                "correlation_id": correlation_id,
                "document_id": document.id,
                "error": str(e)
            }
        )


@router.post("/{doc_id}/ingest", response_model=IngestionStatusResponse)
async def ingest_document(
    engagement_id: str,
    doc_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    repo: Repository = Depends(get_repo),
    ctx=Depends(current_context)
):
    """
    Manually trigger ingestion of a document into the RAG search index.
    This endpoint processes the document in the background.
    """
    # Check if RAG is enabled
    if not config.is_rag_enabled():
        raise HTTPException(
            status_code=503, 
            detail="RAG service is not enabled or properly configured"
        )
    
    # Verify permissions
    require_member(repo, {"user_email": ctx["user_email"], "engagement_id": engagement_id}, "member")
    
    # Get document
    document = repo.get_document(engagement_id, doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Verify file exists
    if not os.path.exists(document.path):
        raise HTTPException(status_code=404, detail="Document file not found")
    
    correlation_id = get_correlation_id(request)
    
    logger.info(
        "Starting manual document ingestion",
        extra={
            "correlation_id": correlation_id,
            "document_id": doc_id,
            "engagement_id": engagement_id,
            "filename": document.filename,
            "user_email": ctx["user_email"]
        }
    )
    
    # Create initial status
    rag_service = create_rag_service(correlation_id)
    
    # Schedule background ingestion
    background_tasks.add_task(_ingest_document_background, document, correlation_id)
    
    # Return initial status
    return IngestionStatusResponse(
        document_id=doc_id,
        status="pending",
        chunks_processed=0,
        total_chunks=0,
        started_at=datetime.now()
    )


@router.post("/reindex", response_model=BulkIngestionStatusResponse)
async def reindex_documents(
    engagement_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    repo: Repository = Depends(get_repo),
    ctx=Depends(current_context)
):
    """
    Reindex all documents for an engagement in the RAG search index.
    This operation deletes existing indexed content and re-processes all documents.
    """
    # Check if RAG is enabled
    if not config.is_rag_enabled():
        raise HTTPException(
            status_code=503, 
            detail="RAG service is not enabled or properly configured"
        )
    
    # Verify permissions (lead or admin only for bulk operations)
    if not is_admin(ctx["user_email"]):
        require_member(repo, {"user_email": ctx["user_email"], "engagement_id": engagement_id}, "lead")
    
    correlation_id = get_correlation_id(request)
    
    # Get all documents for the engagement
    documents = repo.list_documents(engagement_id)
    
    if not documents:
        return BulkIngestionStatusResponse(
            engagement_id=engagement_id,
            documents=[],
            summary={"total": 0, "pending": 0, "processing": 0, "completed": 0, "failed": 0}
        )
    
    logger.info(
        "Starting bulk document reindexing",
        extra={
            "correlation_id": correlation_id,
            "engagement_id": engagement_id,
            "document_count": len(documents),
            "user_email": ctx["user_email"]
        }
    )
    
    # Schedule background reindexing
    async def _reindex_background():
        try:
            rag_service = create_rag_service(correlation_id)
            
            # Prepare documents with text content
            doc_tuples = []
            for doc in documents:
                if os.path.exists(doc.path):
                    extract_result = extract_text(doc.path, doc.content_type)
                    if extract_result.text:
                        doc_tuples.append((doc, extract_result.text))
                    else:
                        logger.warning(
                            "Skipping document with no extractable text",
                            extra={
                                "correlation_id": correlation_id,
                                "document_id": doc.id,
                                "filename": doc.filename
                            }
                        )
                else:
                    logger.warning(
                        "Skipping missing document file",
                        extra={
                            "correlation_id": correlation_id,
                            "document_id": doc.id,
                            "path": doc.path
                        }
                    )
            
            if doc_tuples:
                await rag_service.reindex_engagement_documents(engagement_id, doc_tuples)
            
        except Exception as e:
            logger.error(
                "Background reindexing failed",
                extra={
                    "correlation_id": correlation_id,
                    "engagement_id": engagement_id,
                    "error": str(e)
                }
            )
    
    background_tasks.add_task(_reindex_background)
    
    # Return initial status
    doc_statuses = [
        IngestionStatusResponse(
            document_id=doc.id,
            status="pending",
            chunks_processed=0,
            total_chunks=0
        )
        for doc in documents
    ]
    
    return BulkIngestionStatusResponse(
        engagement_id=engagement_id,
        documents=doc_statuses,
        summary={
            "total": len(documents),
            "pending": len(documents),
            "processing": 0,
            "completed": 0,
            "failed": 0
        }
    )


@router.get("/status", response_model=BulkIngestionStatusResponse)
def get_ingestion_status(
    engagement_id: str,
    request: Request,
    repo: Repository = Depends(get_repo),
    ctx=Depends(current_context)
):
    """Get ingestion status for all documents in an engagement"""
    # Check if RAG is enabled
    if not config.is_rag_enabled():
        raise HTTPException(
            status_code=503, 
            detail="RAG service is not enabled or properly configured"
        )
    
    # Verify permissions
    require_member(repo, {"user_email": ctx["user_email"], "engagement_id": engagement_id}, "member")
    
    correlation_id = get_correlation_id(request)
    
    # Get all documents
    documents = repo.list_documents(engagement_id)
    
    # Get RAG service status
    rag_service = create_rag_service(correlation_id)
    
    doc_statuses = []
    status_counts = {"total": len(documents), "pending": 0, "processing": 0, "completed": 0, "failed": 0}
    
    for doc in documents:
        status = rag_service.get_ingestion_status(doc.id)
        if status:
            doc_status = IngestionStatusResponse(
                document_id=doc.id,
                status=status.status,
                chunks_processed=status.chunks_processed,
                total_chunks=status.total_chunks,
                error=status.error,
                started_at=status.started_at,
                completed_at=status.completed_at
            )
            status_counts[status.status] = status_counts.get(status.status, 0) + 1
        else:
            # No status found - document not yet processed
            doc_status = IngestionStatusResponse(
                document_id=doc.id,
                status="not_processed",
                chunks_processed=0,
                total_chunks=0
            )
            status_counts["pending"] += 1
        
        doc_statuses.append(doc_status)
    
    return BulkIngestionStatusResponse(
        engagement_id=engagement_id,
        documents=doc_statuses,
        summary=status_counts
    )


@router.post("/search", response_model=SearchDocumentsResponse)
async def search_documents(
    engagement_id: str,
    search_request: SearchDocumentsRequest,
    request: Request,
    repo: Repository = Depends(get_repo),
    ctx=Depends(current_context)
):
    """Search documents using vector similarity and optional hybrid search"""
    # Check if RAG is enabled
    if not config.is_rag_enabled():
        raise HTTPException(
            status_code=503, 
            detail="RAG service is not enabled or properly configured"
        )
    
    # Verify permissions
    require_member(repo, {"user_email": ctx["user_email"], "engagement_id": engagement_id}, "member")
    
    if not search_request.query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    correlation_id = get_correlation_id(request)
    
    logger.info(
        "Document search requested",
        extra={
            "correlation_id": correlation_id,
            "engagement_id": engagement_id,
            "query_length": len(search_request.query),
            "top_k": search_request.top_k,
            "user_email": ctx["user_email"]
        }
    )
    
    try:
        # Perform search
        rag_service = create_rag_service(correlation_id)
        results = await rag_service.search(
            query=search_request.query,
            engagement_id=engagement_id,
            top_k=search_request.top_k
        )
        
        # Convert results to API format
        result_dicts = []
        for result in results:
            result_dicts.append({
                "document_id": result.document_id,
                "chunk_index": result.chunk_index,
                "content": result.content,
                "filename": result.filename,
                "score": result.score,
                "uploaded_by": result.uploaded_by,
                "uploaded_at": result.uploaded_at,
                "metadata": result.metadata
            })
        
        return SearchDocumentsResponse(
            query=search_request.query,
            results=result_dicts,
            total_results=len(results),
            engagement_id=engagement_id
        )
        
    except Exception as e:
        logger.error(
            "Document search failed",
            extra={
                "correlation_id": correlation_id,
                "engagement_id": engagement_id,
                "error": str(e),
                "query": search_request.query
            }
        )
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
