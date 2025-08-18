from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging
import uuid
from domain.models import Finding, Recommendation
from domain.repository import Repository
from ai.orchestrator import Orchestrator
from ..security import current_context, require_member
from util.files import extract_text
from services.rag_service import create_rag_service
from services.rag_retriever import create_rag_retriever
from config import config

router = APIRouter(prefix="/orchestrations", tags=["orchestrations"])
logger = logging.getLogger(__name__)

def get_repo(request: Request) -> Repository:
    return request.app.state.repo

def get_orchestrator(request: Request) -> Orchestrator:
    return request.app.state.orchestrator

def get_correlation_id(request: Request) -> str:
    """Extract correlation ID from request headers"""
    return request.headers.get(config.logging.correlation_id_header, str(uuid.uuid4()))

class AnalyzeRequest(BaseModel):
    assessment_id: str
    content: str
    use_evidence: bool = False

class AnalyzeResponse(BaseModel):
    findings: List[Finding]
    evidence_used: bool = False
    citations: List[str] = []
    rag_operational: bool = False
    search_backend: Optional[str] = None
    evidence_summary: Optional[str] = None

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    req: AnalyzeRequest, 
    request: Request,
    repo: Repository = Depends(get_repo), 
    orch: Orchestrator = Depends(get_orchestrator),
    ctx: Dict[str, str] = Depends(current_context)
):
    # Ensure user is a member of the engagement
    require_member(repo, ctx, "member")
    
    # Get and verify assessment
    assessment = repo.get_assessment(req.assessment_id)
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    
    # Verify assessment belongs to the engagement
    if assessment.engagement_id != ctx["engagement_id"]:
        raise HTTPException(403, "Assessment not in this engagement")
    
    correlation_id = get_correlation_id(request)
    
    # Prepare content for analysis
    analysis_content = req.content
    evidence_context = ""
    
    # If evidence is requested, use the retriever for enhanced search
    search_backend_used = None
    evidence_summary = None
    
    if req.use_evidence:
        try:
            logger.info(
                "Searching for evidence documents using retriever",
                extra={
                    "correlation_id": correlation_id,
                    "assessment_id": req.assessment_id,
                    "engagement_id": ctx["engagement_id"],
                    "content_length": len(req.content)
                }
            )
            
            # Use the new retriever for better backend support
            retriever = create_rag_retriever(correlation_id)
            
            if retriever.is_operational():
                search_results = await retriever.retrieve(
                    query=req.content,
                    query_vector=None,  # Let retriever generate if needed
                    engagement_id=ctx["engagement_id"],
                    top_k=5,
                    use_semantic_ranking=True
                )
                
                if search_results:
                    evidence_context = retriever.format_results_for_context(search_results)
                    search_backend_used = retriever.backend.value
                    
                    # Create summary of evidence found
                    evidence_summary = f"Found {len(search_results)} relevant documents using {search_backend_used} backend"
                    
                    # Combine original content with evidence and citations
                    analysis_content = f"""Original Content:
{req.content}

Relevant Evidence from Documents:
{evidence_context}

Please analyze the original content while considering the relevant evidence provided above. When referencing evidence in your findings, include the citation numbers [1], [2], etc. to indicate which document the evidence comes from."""
                    
                    logger.info(
                        "Added evidence context to analysis using retriever",
                        extra={
                            "correlation_id": correlation_id,
                            "assessment_id": req.assessment_id,
                            "evidence_documents": len(search_results),
                            "evidence_length": len(evidence_context),
                            "search_backend": search_backend_used,
                            "citations": [r.citation for r in search_results]
                        }
                    )
                else:
                    logger.info(
                        "No relevant evidence documents found using retriever",
                        extra={
                            "correlation_id": correlation_id,
                            "assessment_id": req.assessment_id,
                            "engagement_id": ctx["engagement_id"],
                            "search_backend": retriever.backend.value
                        }
                    )
                    search_backend_used = retriever.backend.value
                    evidence_summary = f"No relevant documents found using {search_backend_used} backend"
            else:
                logger.warning(
                    "RAG retriever not operational for evidence search",
                    extra={
                        "correlation_id": correlation_id,
                        "assessment_id": req.assessment_id,
                        "backend": retriever.backend.value
                    }
                )
                evidence_summary = f"Retriever not operational (backend: {retriever.backend.value})"
        
        except Exception as e:
            logger.warning(
                "Failed to retrieve evidence using retriever, proceeding without",
                extra={
                    "correlation_id": correlation_id,
                    "assessment_id": req.assessment_id,
                    "error": str(e)
                }
            )
            evidence_summary = f"Evidence retrieval failed: {str(e)}"
            # Continue without evidence rather than failing the analysis
    
    elif req.use_evidence and not config.is_rag_enabled():
        logger.warning(
            "Evidence requested but RAG is not enabled",
            extra={
                "correlation_id": correlation_id,
                "assessment_id": req.assessment_id
            }
        )
    
    # Perform analysis
    findings, log = orch.analyze(req.assessment_id, analysis_content)
    
    # Track evidence usage and citations
    evidence_used = False
    citations = []
    rag_operational = False
    
    # Add evidence context information to the log if used
    if evidence_context:
        log.input_preview = f"Content with evidence ({len(search_results)} docs): {req.content[:100]}..."
        evidence_used = True
        citations = [r.citation for r in search_results]
        rag_operational = True
    elif req.use_evidence:
        # Check if retriever is operational
        try:
            retriever = create_rag_retriever(correlation_id)
            rag_operational = retriever.is_operational()
            if not search_backend_used:
                search_backend_used = retriever.backend.value
        except:
            rag_operational = False
    
    repo.add_findings(req.assessment_id, findings)
    repo.add_runlog(log)
    
    return AnalyzeResponse(
        findings=findings,
        evidence_used=evidence_used,
        citations=citations,
        rag_operational=rag_operational,
        search_backend=search_backend_used,
        evidence_summary=evidence_summary
    )

class RecommendRequest(BaseModel):
    assessment_id: str

class RecommendResponse(BaseModel):
    recommendations: List[Recommendation]
    evidence_used: bool = False
    citations: List[str] = []
    rag_operational: bool = False
    search_backend: Optional[str] = None
    evidence_summary: Optional[str] = None

class RAGSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = None

class RAGSearchResultResponse(BaseModel):
    document_id: str
    chunk_index: int
    content: str
    filename: str
    similarity_score: float
    citation: str
    metadata: Dict[str, Any]

class RAGSearchResponse(BaseModel):
    results: List[RAGSearchResultResponse]
    query: str
    engagement_id: str
    total_results: int
    search_duration_seconds: float
    rag_operational: bool

@router.post("/recommend", response_model=RecommendResponse)
async def recommend(
    req: RecommendRequest, 
    request: Request,
    repo: Repository = Depends(get_repo), 
    orch: Orchestrator = Depends(get_orchestrator),
    ctx: Dict[str, str] = Depends(current_context)
):
    """
    Generate recommendations based on findings, optionally enhanced with RAG evidence.
    
    This endpoint analyzes findings from an assessment and generates recommendations.
    If RAG is enabled, it searches for relevant evidence to enhance recommendations.
    """
    # Ensure user is a member of the engagement
    require_member(repo, ctx, "member")
    
    correlation_id = get_correlation_id(request)
    engagement_id = ctx["engagement_id"]
    
    # Get and verify assessment
    assessment = repo.get_assessment(req.assessment_id)
    if not assessment:
        raise HTTPException(404, "Assessment not found")
    
    # Verify assessment belongs to the engagement
    if assessment.engagement_id != engagement_id:
        raise HTTPException(403, "Assessment not in this engagement")
    
    # Get findings for this assessment
    findings = [f for f in repo.get_findings(engagement_id) if f.assessment_id == req.assessment_id]
    if not findings:
        raise HTTPException(400, "No findings available; run analyze first")
    
    logger.info(
        "Generating recommendations",
        extra={
            "correlation_id": correlation_id,
            "assessment_id": req.assessment_id,
            "engagement_id": engagement_id,
            "findings_count": len(findings)
        }
    )
    
    # Prepare findings text for recommendation generation
    findings_text = "\n".join(f"- [{f.severity}] {f.area or 'General'}: {f.title}" for f in findings)
    
    # Enhanced recommendation context with RAG evidence
    evidence_used = False
    citations = []
    rag_operational = False
    
    recommendation_content = findings_text
    
    # If RAG is enabled, search for relevant evidence to enhance recommendations
    if config.is_rag_enabled():
        try:
            logger.info(
                "Searching for evidence to enhance recommendations",
                extra={
                    "correlation_id": correlation_id,
                    "assessment_id": req.assessment_id,
                    "engagement_id": engagement_id,
                    "findings_count": len(findings)
                }
            )
            
            rag_service = create_rag_service(correlation_id)
            
            if rag_service.is_operational():
                rag_operational = True
                
                # Search for evidence using findings as query
                search_results = await rag_service.search(
                    query=findings_text,
                    engagement_id=engagement_id,
                    top_k=3  # Limit to top 3 for recommendations
                )
                
                if search_results:
                    evidence_context = rag_service.format_search_results_for_context(search_results)
                    
                    # Enhance recommendation content with evidence
                    recommendation_content = f"""Findings:
{findings_text}

Relevant Evidence from Documents:
{evidence_context}

Please generate recommendations considering both the findings and the relevant evidence. Include citation numbers [1], [2], etc. when referencing specific evidence in your recommendations."""
                    
                    evidence_used = True
                    citations = [r.citation for r in search_results]
                    
                    logger.info(
                        "Added evidence context to recommendations",
                        extra={
                            "correlation_id": correlation_id,
                            "assessment_id": req.assessment_id,
                            "evidence_documents": len(search_results),
                            "citations": citations
                        }
                    )
                else:
                    logger.info(
                        "No relevant evidence found for recommendations",
                        extra={
                            "correlation_id": correlation_id,
                            "assessment_id": req.assessment_id,
                            "engagement_id": engagement_id
                        }
                    )
            else:
                logger.warning(
                    "RAG service not operational for recommendation enhancement",
                    extra={
                        "correlation_id": correlation_id,
                        "assessment_id": req.assessment_id,
                        "rag_mode": rag_service.mode.value if rag_service.mode else "unknown"
                    }
                )
        
        except Exception as e:
            logger.warning(
                "Failed to retrieve evidence for recommendations, proceeding without",
                extra={
                    "correlation_id": correlation_id,
                    "assessment_id": req.assessment_id,
                    "error": str(e)
                }
            )
            # Continue without evidence rather than failing
    
    # Generate recommendations
    recs, log = orch.recommend(req.assessment_id, recommendation_content)
    
    # Update log with evidence information if used
    if evidence_used:
        log.input_preview = f"Findings with evidence ({len(citations)} docs): {findings_text[:100]}..."
    
    repo.add_recommendations(req.assessment_id, recs)
    repo.add_runlog(log)
    
    logger.info(
        "Recommendations generated",
        extra={
            "correlation_id": correlation_id,
            "assessment_id": req.assessment_id,
            "recommendations_count": len(recs),
            "evidence_used": evidence_used
        }
    )
    
    return RecommendResponse(
        recommendations=recs,
        evidence_used=evidence_used,
        citations=citations,
        rag_operational=rag_operational
    )


@router.get("/runlogs")
def get_runlogs(
    repo: Repository = Depends(get_repo),
    ctx: Dict[str, str] = Depends(current_context)
):
    """Get runlogs for the current engagement"""
    # Ensure user is a member of the engagement
    require_member(repo, ctx, "member")
    
    return repo.get_runlogs(ctx["engagement_id"])


@router.post("/rag-search", response_model=RAGSearchResponse)
async def rag_search(
    req: RAGSearchRequest,
    request: Request,
    repo: Repository = Depends(get_repo),
    ctx: Dict[str, str] = Depends(current_context)
):
    """
    Perform vector search across engagement documents using RAG.
    
    This endpoint searches through document embeddings for the most relevant
    content based on the provided query. Results are filtered to the current
    engagement and ranked by semantic similarity.
    """
    # Ensure user is a member of the engagement
    require_member(repo, ctx, "member")
    
    engagement_id = ctx["engagement_id"]
    correlation_id = get_correlation_id(request)
    
    import time
    start_time = time.time()
    
    try:
        logger.info(
            "RAG search request received",
            extra={
                "correlation_id": correlation_id,
                "engagement_id": engagement_id,
                "query_length": len(req.query),
                "top_k": req.top_k
            }
        )
        
        # Validate query
        if not req.query.strip():
            raise HTTPException(400, "Query cannot be empty")
        
        if len(req.query) > 1000:
            raise HTTPException(400, "Query too long (max 1000 characters)")
        
        # Create RAG service and perform search
        rag_service = create_rag_service(correlation_id)
        
        # Check if RAG is operational
        if not rag_service.is_operational():
            logger.warning(
                "RAG search requested but service not operational",
                extra={
                    "correlation_id": correlation_id,
                    "engagement_id": engagement_id,
                    "rag_mode": rag_service.mode.value if rag_service.mode else "unknown"
                }
            )
            
            search_duration = time.time() - start_time
            return RAGSearchResponse(
                results=[],
                query=req.query,
                engagement_id=engagement_id,
                total_results=0,
                search_duration_seconds=search_duration,
                rag_operational=False
            )
        
        # Perform search
        search_results = await rag_service.search(
            query=req.query,
            engagement_id=engagement_id,
            top_k=req.top_k
        )
        
        # Convert to response format
        result_responses = []
        for result in search_results:
            result_response = RAGSearchResultResponse(
                document_id=result.document_id,
                chunk_index=result.chunk_index,
                content=result.content,
                filename=result.filename,
                similarity_score=result.similarity_score,
                citation=result.citation,
                metadata=result.metadata
            )
            result_responses.append(result_response)
        
        search_duration = time.time() - start_time
        
        logger.info(
            "RAG search completed successfully",
            extra={
                "correlation_id": correlation_id,
                "engagement_id": engagement_id,
                "results_found": len(result_responses),
                "search_duration": search_duration,
                "query_length": len(req.query)
            }
        )
        
        return RAGSearchResponse(
            results=result_responses,
            query=req.query,
            engagement_id=engagement_id,
            total_results=len(result_responses),
            search_duration_seconds=search_duration,
            rag_operational=True
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        search_duration = time.time() - start_time
        
        logger.error(
            "RAG search failed with unexpected error",
            extra={
                "correlation_id": correlation_id,
                "engagement_id": engagement_id,
                "error": str(e),
                "search_duration": search_duration
            }
        )
        
        # Return graceful error response instead of raising exception
        return RAGSearchResponse(
            results=[],
            query=req.query,
            engagement_id=engagement_id,
            total_results=0,
            search_duration_seconds=search_duration,
            rag_operational=False
        )


class AnalyzeDocRequest(BaseModel):
    doc_id: str

class AnalyzeDocResponse(BaseModel):
    analyzed: bool
    note: Optional[str] = None
    assessment_id: Optional[str] = None
    findings_count: int = 0
    rag_ingestion: Optional[Dict[str, Any]] = None


@router.post("/analyze-doc", response_model=AnalyzeDocResponse)
async def analyze_doc(
    payload: AnalyzeDocRequest,
    request: Request,
    repo: Repository = Depends(get_repo),
    ctx: Dict[str, str] = Depends(current_context)
):
    """
    Analyze a document and optionally ingest it into RAG system.
    
    This endpoint extracts text from a document, analyzes it for findings,
    and if RAG is enabled, automatically embeds and stores the document
    for future vector search.
    """
    require_member(repo, ctx, "member")
    engagement_id = ctx["engagement_id"]
    doc_id = payload.doc_id
    correlation_id = get_correlation_id(request)
    
    if not doc_id:
        raise HTTPException(400, "doc_id required")
    
    logger.info(
        "Document analysis request received",
        extra={
            "correlation_id": correlation_id,
            "engagement_id": engagement_id,
            "doc_id": doc_id
        }
    )
    
    doc = repo.get_document(engagement_id, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    
    # Extract text
    ex = extract_text(doc.path, doc.content_type)
    if not ex.text:
        logger.warning(
            "No text extracted from document",
            extra={
                "correlation_id": correlation_id,
                "doc_id": doc_id,
                "note": ex.note
            }
        )
        return AnalyzeDocResponse(
            analyzed=False,
            note=ex.note or "No text extracted"
        )
    
    logger.info(
        "Text extracted from document",
        extra={
            "correlation_id": correlation_id,
            "doc_id": doc_id,
            "text_length": len(ex.text)
        }
    )
    
    # Create a new assessment for this document analysis
    from ...domain.models import Assessment
    assessment = Assessment(
        name=f"Doc Analysis: {doc.filename}",
        engagement_id=engagement_id,
        framework="Custom"
    )
    repo.create_assessment(assessment)
    
    # Perform analysis with orchestrator
    orch = request.app.state.orchestrator if hasattr(request.app.state, "orchestrator") else None
    if not orch:
        raise HTTPException(500, "Orchestrator not configured")
    
    findings, log = orch.analyze(assessment.id, ex.text)
    repo.add_findings(assessment.id, findings)
    repo.add_runlog(log)
    
    logger.info(
        "Document analysis completed",
        extra={
            "correlation_id": correlation_id,
            "doc_id": doc_id,
            "assessment_id": assessment.id,
            "findings_count": len(findings)
        }
    )
    
    # RAG ingestion (if enabled)
    rag_ingestion_result = None
    if config.is_rag_enabled():
        try:
            logger.info(
                "Starting RAG ingestion for analyzed document",
                extra={
                    "correlation_id": correlation_id,
                    "doc_id": doc_id,
                    "engagement_id": engagement_id
                }
            )
            
            rag_service = create_rag_service(correlation_id)
            if rag_service.is_operational():
                ingestion_result = await rag_service.ingest_document(doc, ex.text)
                
                rag_ingestion_result = {
                    "status": ingestion_result.status,
                    "chunks_processed": ingestion_result.chunks_processed,
                    "total_chunks": ingestion_result.total_chunks,
                    "processing_time_seconds": ingestion_result.processing_time_seconds,
                    "errors": ingestion_result.errors[:3] if ingestion_result.errors else []  # Limit error list
                }
                
                logger.info(
                    "RAG ingestion completed",
                    extra={
                        "correlation_id": correlation_id,
                        "doc_id": doc_id,
                        "ingestion_status": ingestion_result.status,
                        "chunks_processed": ingestion_result.chunks_processed
                    }
                )
            else:
                logger.warning(
                    "RAG service not operational, skipping ingestion",
                    extra={
                        "correlation_id": correlation_id,
                        "doc_id": doc_id
                    }
                )
                rag_ingestion_result = {
                    "status": "skipped",
                    "reason": "RAG service not operational"
                }
                
        except Exception as e:
            logger.error(
                "RAG ingestion failed",
                extra={
                    "correlation_id": correlation_id,
                    "doc_id": doc_id,
                    "error": str(e)
                }
            )
            rag_ingestion_result = {
                "status": "failed",
                "error": str(e)
            }
            # Don't fail the entire analysis if RAG ingestion fails
    
    return AnalyzeDocResponse(
        analyzed=True,
        note=ex.note,
        assessment_id=assessment.id,
        findings_count=len(findings),
        rag_ingestion=rag_ingestion_result
    )
