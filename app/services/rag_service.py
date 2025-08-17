"""
Production-ready RAG service with graceful fallback and mode switching.
Supports Azure OpenAI embeddings with Cosmos DB vector storage.
"""
import asyncio
import logging
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from .embeddings import create_embeddings_service, EmbeddingResult
from ..domain.models import Document, EmbeddingDocument
from ..repos.cosmos_embeddings_repository import create_cosmos_embeddings_repository, VectorSearchResult
from ..config import config
from ..util.files import extract_text
from ..util.logging import get_correlated_logger, log_operation, get_rag_metrics_logger, handle_rag_error, EmbeddingError, SearchError, IngestionError


logger = logging.getLogger(__name__)


class RAGMode(Enum):
    """Available RAG modes"""
    AZURE_OPENAI = "azure_openai"
    NONE = "none"


@dataclass
class RAGSearchResult:
    """Result from RAG search with citation information"""
    document_id: str
    chunk_index: int
    content: str
    filename: str
    similarity_score: float
    engagement_id: str
    uploaded_by: str
    uploaded_at: str
    metadata: Dict[str, Any]
    citation: str  # Formatted citation for LLM use


@dataclass
class RAGIngestionResult:
    """Result from document ingestion"""
    document_id: str
    status: str  # "success", "partial", "failed"
    chunks_processed: int
    total_chunks: int
    errors: List[str]
    processing_time_seconds: float


@dataclass
class RAGMetrics:
    """Metrics for RAG operations"""
    operation: str
    duration_seconds: float
    success: bool
    engagement_id: str
    document_count: int = 0
    chunk_count: int = 0
    error_message: Optional[str] = None


class ProductionRAGService:
    """Production-ready RAG service with graceful fallback"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.mode = RAGMode(config.rag.mode)
        self.embeddings_service = None
        self.cosmos_repo = None
        self._metrics: List[RAGMetrics] = []
        self.logger = get_correlated_logger(__name__, self.correlation_id)
        self.metrics_logger = get_rag_metrics_logger(self.correlation_id)
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize RAG services based on configuration with graceful fallback"""
        try:
            if self.mode == RAGMode.AZURE_OPENAI and config.is_rag_enabled():
                logger.info(
                    "Initializing RAG services in Azure OpenAI mode",
                    extra={
                        "correlation_id": self.correlation_id,
                        "mode": self.mode.value,
                        "feature_flag_enabled": config.rag.feature_flag_enabled
                    }
                )
                
                # Initialize embeddings service
                try:
                    self.embeddings_service = create_embeddings_service(self.correlation_id)
                    logger.info(
                        "Embeddings service initialized",
                        extra={"correlation_id": self.correlation_id}
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to initialize embeddings service, falling back to none mode",
                        extra={
                            "correlation_id": self.correlation_id,
                            "error": str(e)
                        }
                    )
                    self.mode = RAGMode.NONE
                    return
                
                # Initialize Cosmos DB repository
                try:
                    self.cosmos_repo = create_cosmos_embeddings_repository(self.correlation_id)
                    logger.info(
                        "Cosmos embeddings repository initialized",
                        extra={"correlation_id": self.correlation_id}
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to initialize Cosmos repository, falling back to none mode",
                        extra={
                            "correlation_id": self.correlation_id,
                            "error": str(e)
                        }
                    )
                    self.mode = RAGMode.NONE
                    return
                
            else:
                logger.info(
                    "RAG service initialized in none mode",
                    extra={
                        "correlation_id": self.correlation_id,
                        "configured_mode": config.rag.mode,
                        "rag_enabled": config.is_rag_enabled(),
                        "feature_flag": config.rag.feature_flag_enabled
                    }
                )
                self.mode = RAGMode.NONE
                
        except Exception as e:
            logger.error(
                "Failed to initialize RAG service, falling back to none mode",
                extra={
                    "correlation_id": self.correlation_id,
                    "error": str(e)
                }
            )
            self.mode = RAGMode.NONE
    
    def is_operational(self) -> bool:
        """Check if RAG service is operational"""
        return (
            self.mode == RAGMode.AZURE_OPENAI 
            and self.embeddings_service is not None 
            and self.cosmos_repo is not None
        )
    
    async def ingest_document(
        self, 
        document: Document, 
        text_content: Optional[str] = None
    ) -> RAGIngestionResult:
        """
        Ingest a document for RAG with graceful fallback.
        
        Args:
            document: Document metadata
            text_content: Optional pre-extracted text content
            
        Returns:
            RAGIngestionResult with processing details
        """
        start_time = time.time()
        
        try:
            if not self.is_operational():
                logger.info(
                    "RAG not operational, skipping document ingestion",
                    extra={
                        "correlation_id": self.correlation_id,
                        "document_id": document.id,
                        "mode": self.mode.value
                    }
                )
                return RAGIngestionResult(
                    document_id=document.id,
                    status="skipped",
                    chunks_processed=0,
                    total_chunks=0,
                    errors=["RAG service not operational"],
                    processing_time_seconds=time.time() - start_time
                )
            
            logger.info(
                "Starting document ingestion",
                extra={
                    "correlation_id": self.correlation_id,
                    "document_id": document.id,
                    "engagement_id": document.engagement_id,
                    "filename": document.filename
                }
            )
            
            # Extract text if not provided
            if text_content is None:
                try:
                    extraction = extract_text(document.path, document.content_type)
                    text_content = extraction.text
                    if not text_content:
                        raise ValueError(f"No text extracted: {extraction.note}")
                except Exception as e:
                    error_msg = f"Failed to extract text: {str(e)}"
                    logger.error(
                        "Text extraction failed",
                        extra={
                            "correlation_id": self.correlation_id,
                            "document_id": document.id,
                            "error": str(e)
                        }
                    )
                    return RAGIngestionResult(
                        document_id=document.id,
                        status="failed",
                        chunks_processed=0,
                        total_chunks=0,
                        errors=[error_msg],
                        processing_time_seconds=time.time() - start_time
                    )
            
            # Generate embeddings
            try:
                embeddings = await self.embeddings_service.embed_document(text_content, document.id)
                if not embeddings:
                    raise ValueError("No embeddings generated")
            except Exception as e:
                error_msg = f"Failed to generate embeddings: {str(e)}"
                logger.error(
                    "Embedding generation failed",
                    extra={
                        "correlation_id": self.correlation_id,
                        "document_id": document.id,
                        "error": str(e)
                    }
                )
                return RAGIngestionResult(
                    document_id=document.id,
                    status="failed",
                    chunks_processed=0,
                    total_chunks=len(embeddings) if embeddings else 0,
                    errors=[error_msg],
                    processing_time_seconds=time.time() - start_time
                )
            
            # Convert to EmbeddingDocument objects
            embedding_docs = []
            for embedding_result in embeddings:
                embedding_doc = EmbeddingDocument(
                    engagement_id=document.engagement_id,
                    doc_id=document.id,
                    chunk_id=f"{document.id}_{embedding_result.chunk.chunk_index}",
                    vector=embedding_result.embedding,
                    text=embedding_result.chunk.text,
                    metadata={
                        "content_type": document.content_type,
                        "size": document.size,
                        "embedding_model": embedding_result.model
                    },
                    chunk_index=embedding_result.chunk.chunk_index,
                    chunk_start=embedding_result.chunk.start_index,
                    chunk_end=embedding_result.chunk.end_index,
                    token_count=embedding_result.usage_tokens,
                    filename=document.filename,
                    uploaded_by=document.uploaded_by,
                    uploaded_at=document.uploaded_at,
                    model=embedding_result.model
                )
                embedding_docs.append(embedding_doc)
            
            # Store in Cosmos DB
            try:
                successful, errors = await self.cosmos_repo.store_embeddings(embedding_docs)
                
                status = "success" if successful == len(embedding_docs) else "partial" if successful > 0 else "failed"
                
                result = RAGIngestionResult(
                    document_id=document.id,
                    status=status,
                    chunks_processed=successful,
                    total_chunks=len(embedding_docs),
                    errors=errors,
                    processing_time_seconds=time.time() - start_time
                )
                
                # Record metrics with structured logging
                self._record_metric(RAGMetrics(
                    operation="ingestion",
                    duration_seconds=result.processing_time_seconds,
                    success=result.status == "success",
                    engagement_id=document.engagement_id,
                    document_count=1,
                    chunk_count=result.chunks_processed,
                    error_message="; ".join(errors) if errors else None
                ))
                
                # Log structured metrics
                self.metrics_logger.log_ingestion_operation(
                    document_id=document.id,
                    engagement_id=document.engagement_id,
                    chunks_stored=successful,
                    total_chunks=len(embedding_docs),
                    duration_seconds=result.processing_time_seconds,
                    success=result.status == "success",
                    storage_backend="cosmos_db",
                    error="; ".join(errors) if errors else None
                )
                
                logger.info(
                    "Document ingestion completed",
                    extra={
                        "correlation_id": self.correlation_id,
                        "document_id": document.id,
                        "status": result.status,
                        "chunks_processed": result.chunks_processed,
                        "total_chunks": result.total_chunks,
                        "processing_time": result.processing_time_seconds
                    }
                )
                
                return result
                
            except Exception as e:
                error_msg = f"Failed to store embeddings: {str(e)}"
                logger.error(
                    "Embedding storage failed",
                    extra={
                        "correlation_id": self.correlation_id,
                        "document_id": document.id,
                        "error": str(e)
                    }
                )
                return RAGIngestionResult(
                    document_id=document.id,
                    status="failed",
                    chunks_processed=0,
                    total_chunks=len(embedding_docs),
                    errors=[error_msg],
                    processing_time_seconds=time.time() - start_time
                )
            
        except Exception as e:
            error_msg = f"Unexpected error during ingestion: {str(e)}"
            logger.error(
                "Document ingestion failed with unexpected error",
                extra={
                    "correlation_id": self.correlation_id,
                    "document_id": document.id,
                    "error": str(e)
                }
            )
            return RAGIngestionResult(
                document_id=document.id,
                status="failed",
                chunks_processed=0,
                total_chunks=0,
                errors=[error_msg],
                processing_time_seconds=time.time() - start_time
            )
    
    async def search(
        self, 
        query: str, 
        engagement_id: str,
        top_k: Optional[int] = None
    ) -> List[RAGSearchResult]:
        """
        Search for relevant documents with graceful fallback.
        
        Args:
            query: Search query text
            engagement_id: Filter results to this engagement
            top_k: Maximum number of results to return
            
        Returns:
            List of RAGSearchResult objects (empty if RAG not operational)
        """
        start_time = time.time()
        
        try:
            if not self.is_operational():
                logger.info(
                    "RAG not operational, returning empty search results",
                    extra={
                        "correlation_id": self.correlation_id,
                        "engagement_id": engagement_id,
                        "mode": self.mode.value
                    }
                )
                return []
            
            top_k = top_k or config.rag.search_top_k
            
            logger.info(
                "Starting RAG search",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "query_length": len(query),
                    "top_k": top_k
                }
            )
            
            # Generate query embedding
            try:
                query_chunks = self.embeddings_service.chunk_text(query, "search_query")
                if not query_chunks:
                    logger.warning(
                        "No query chunks generated",
                        extra={
                            "correlation_id": self.correlation_id,
                            "query_length": len(query)
                        }
                    )
                    return []
                
                query_embeddings = await self.embeddings_service.generate_embeddings(
                    query_chunks[:1], "search_query"  # Use only first chunk
                )
                if not query_embeddings:
                    logger.warning(
                        "No query embeddings generated",
                        extra={"correlation_id": self.correlation_id}
                    )
                    return []
                
                query_vector = query_embeddings[0].embedding
                
            except Exception as e:
                logger.error(
                    "Failed to generate query embedding",
                    extra={
                        "correlation_id": self.correlation_id,
                        "error": str(e)
                    }
                )
                return []
            
            # Perform vector search
            try:
                search_results = await self.cosmos_repo.vector_search(
                    query_vector=query_vector,
                    engagement_id=engagement_id,
                    top_k=top_k
                )
                
                # Convert to RAGSearchResult format
                rag_results = []
                for i, result in enumerate(search_results, 1):
                    rag_result = RAGSearchResult(
                        document_id=result.embedding_doc.doc_id,
                        chunk_index=result.embedding_doc.chunk_index,
                        content=result.embedding_doc.text,
                        filename=result.embedding_doc.filename,
                        similarity_score=result.similarity_score,
                        engagement_id=result.embedding_doc.engagement_id,
                        uploaded_by=result.embedding_doc.uploaded_by,
                        uploaded_at=result.embedding_doc.uploaded_at.isoformat() if result.embedding_doc.uploaded_at else "",
                        metadata=result.embedding_doc.metadata,
                        citation=f"[{i}] {result.embedding_doc.filename}"
                    )
                    rag_results.append(rag_result)
                
                search_duration = time.time() - start_time
                
                # Record metrics with structured logging
                self._record_metric(RAGMetrics(
                    operation="search",
                    duration_seconds=search_duration,
                    success=True,
                    engagement_id=engagement_id,
                    chunk_count=len(rag_results)
                ))
                
                # Log structured search metrics
                self.metrics_logger.log_search_operation(
                    engagement_id=engagement_id,
                    query_length=len(query),
                    results_found=len(rag_results),
                    top_k=top_k,
                    duration_seconds=search_duration,
                    success=True,
                    similarity_threshold=config.rag.similarity_threshold
                )
                
                logger.info(
                    "RAG search completed",
                    extra={
                        "correlation_id": self.correlation_id,
                        "engagement_id": engagement_id,
                        "results_found": len(rag_results),
                        "search_duration": search_duration,
                        "top_k": top_k
                    }
                )
                
                return rag_results
                
            except Exception as e:
                logger.error(
                    "Vector search failed",
                    extra={
                        "correlation_id": self.correlation_id,
                        "engagement_id": engagement_id,
                        "error": str(e)
                    }
                )
                # Record failed search metric
                self._record_metric(RAGMetrics(
                    operation="search",
                    duration_seconds=time.time() - start_time,
                    success=False,
                    engagement_id=engagement_id,
                    error_message=str(e)
                ))
                return []
                
        except Exception as e:
            logger.error(
                "RAG search failed with unexpected error",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "error": str(e)
                }
            )
            return []
    
    def format_search_results_for_context(self, results: List[RAGSearchResult]) -> str:
        """Format search results into context text for LLM consumption"""
        if not results:
            return "No relevant documents found."
        
        context_parts = []
        for result in results:
            content = result.content.strip()
            # Truncate very long content
            if len(content) > 500:
                content = content[:500] + "..."
            
            context_parts.append(f"{result.citation}:\n{content}\n")
        
        return "\n".join(context_parts)
    
    async def delete_document_embeddings(self, engagement_id: str, doc_id: str) -> bool:
        """Delete all embeddings for a document"""
        try:
            if not self.is_operational():
                logger.info(
                    "RAG not operational, skipping embedding deletion",
                    extra={
                        "correlation_id": self.correlation_id,
                        "engagement_id": engagement_id,
                        "doc_id": doc_id
                    }
                )
                return True  # Consider it successful if RAG is not operational
            
            deleted_count = await self.cosmos_repo.delete_embeddings_by_document(
                engagement_id, doc_id
            )
            
            logger.info(
                "Document embeddings deleted",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "doc_id": doc_id,
                    "deleted_count": deleted_count
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to delete document embeddings",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "doc_id": doc_id,
                    "error": str(e)
                }
            )
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get RAG service status for monitoring"""
        return {
            "mode": self.mode.value,
            "operational": self.is_operational(),
            "embeddings_service_available": self.embeddings_service is not None,
            "cosmos_repo_available": self.cosmos_repo is not None,
            "config": config.get_rag_status()
        }
    
    def get_metrics(self) -> List[RAGMetrics]:
        """Get recorded metrics"""
        return self._metrics.copy()
    
    def _record_metric(self, metric: RAGMetrics):
        """Record a metric for monitoring"""
        self._metrics.append(metric)
        # Keep only last 100 metrics to prevent memory issues
        if len(self._metrics) > 100:
            self._metrics = self._metrics[-100:]


def create_rag_service(correlation_id: Optional[str] = None) -> ProductionRAGService:
    """Factory function to create a RAG service instance"""
    return ProductionRAGService(correlation_id=correlation_id)