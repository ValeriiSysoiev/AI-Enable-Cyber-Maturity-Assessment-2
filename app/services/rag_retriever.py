"""
Production-ready RAG retriever with multiple backend support.
Supports Azure Cognitive Search and Cosmos DB with graceful fallback.
"""
import asyncio
import logging
import time
import uuid
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum

from .azure_search_index import create_azure_search_index_manager, SearchResult as AzureSearchResult
from .rag_service import RAGSearchResult, ProductionRAGService
from ..repos.cosmos_embeddings_repository import create_cosmos_embeddings_repository, VectorSearchResult
from ..domain.models import EmbeddingDocument
from ..config import config
from ..util.logging import get_correlated_logger


logger = logging.getLogger(__name__)


class SearchBackend(Enum):
    """Available search backends"""
    AZURE_SEARCH = "azure_search"
    COSMOS_DB = "cosmos_db" 
    NONE = "none"


@dataclass
class RetrievalResult:
    """Unified result from RAG retrieval"""
    document_id: str
    chunk_index: int
    content: str
    filename: str
    similarity_score: float
    engagement_id: str
    uploaded_by: str
    uploaded_at: str
    metadata: Dict[str, Any]
    citation: str
    backend_used: str
    reranker_score: Optional[float] = None
    highlights: Optional[Dict[str, List[str]]] = None


@dataclass
class RetrievalMetrics:
    """Metrics for retrieval operations"""
    backend: str
    query_length: int
    results_found: int
    search_duration_seconds: float
    use_semantic_ranking: bool
    top_k: int
    engagement_id: str
    success: bool
    error_message: Optional[str] = None


class RAGRetriever:
    """Production RAG retriever with multiple backend support"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.logger = get_correlated_logger(__name__, self.correlation_id)
        
        # Determine search backend based on configuration
        self.backend = self._determine_backend()
        
        # Initialize search services
        self.azure_search_manager = None
        self.cosmos_repo = None
        self.rag_service = None
        
        self._initialize_services()
    
    def _determine_backend(self) -> SearchBackend:
        """Determine which search backend to use based on configuration"""
        # Check if Azure Search is configured and preferred
        if (config.azure_search.endpoint and 
            config.azure_search.index_name and
            config.rag.search_backend == "azure_search"):
            return SearchBackend.AZURE_SEARCH
        
        # Fallback to Cosmos DB if RAG is enabled
        elif config.is_rag_enabled():
            return SearchBackend.COSMOS_DB
        
        # No backend available
        else:
            return SearchBackend.NONE
    
    def _initialize_services(self):
        """Initialize search services based on backend"""
        try:
            if self.backend == SearchBackend.AZURE_SEARCH:
                try:
                    self.azure_search_manager = create_azure_search_index_manager(self.correlation_id)
                    self.logger.info(
                        "Initialized Azure Search backend",
                        extra={
                            "backend": self.backend.value,
                            "index_name": config.azure_search.index_name
                        }
                    )
                except Exception as e:
                    self.logger.warning(
                        "Failed to initialize Azure Search, falling back to Cosmos DB",
                        extra={"error": str(e)}
                    )
                    self.backend = SearchBackend.COSMOS_DB
            
            if self.backend == SearchBackend.COSMOS_DB:
                try:
                    self.rag_service = ProductionRAGService(self.correlation_id)
                    if self.rag_service.is_operational():
                        self.logger.info(
                            "Initialized Cosmos DB backend",
                            extra={"backend": self.backend.value}
                        )
                    else:
                        self.logger.warning("RAG service not operational, falling back to none")
                        self.backend = SearchBackend.NONE
                except Exception as e:
                    self.logger.warning(
                        "Failed to initialize Cosmos DB backend, falling back to none",
                        extra={"error": str(e)}
                    )
                    self.backend = SearchBackend.NONE
            
            if self.backend == SearchBackend.NONE:
                self.logger.info(
                    "No search backend available",
                    extra={"backend": self.backend.value}
                )
                
        except Exception as e:
            self.logger.error(
                "Failed to initialize RAG retriever",
                extra={"error": str(e)}
            )
            self.backend = SearchBackend.NONE
    
    def is_operational(self) -> bool:
        """Check if retriever is operational"""
        if self.backend == SearchBackend.AZURE_SEARCH:
            return self.azure_search_manager is not None
        elif self.backend == SearchBackend.COSMOS_DB:
            return self.rag_service is not None and self.rag_service.is_operational()
        else:
            return False
    
    async def retrieve(
        self,
        query: str,
        query_vector: Optional[List[float]],
        engagement_id: str,
        top_k: Optional[int] = None,
        use_semantic_ranking: bool = True,
        similarity_threshold: Optional[float] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant documents using the configured backend.
        
        Args:
            query: Text query for semantic search
            query_vector: Pre-computed query vector (required for Cosmos DB)
            engagement_id: Filter results to this engagement
            top_k: Maximum number of results
            use_semantic_ranking: Enable semantic ranking (Azure Search only)
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of RetrievalResult objects
        """
        start_time = time.time()
        top_k = top_k or config.rag.search_top_k
        
        if not self.is_operational():
            self.logger.info(
                "RAG retriever not operational, returning empty results",
                extra={
                    "backend": self.backend.value,
                    "engagement_id": engagement_id
                }
            )
            return []
        
        try:
            if self.backend == SearchBackend.AZURE_SEARCH:
                results = await self._retrieve_azure_search(
                    query=query,
                    query_vector=query_vector,
                    engagement_id=engagement_id,
                    top_k=top_k,
                    use_semantic_ranking=use_semantic_ranking,
                    similarity_threshold=similarity_threshold
                )
            elif self.backend == SearchBackend.COSMOS_DB:
                if not query_vector:
                    self.logger.warning(
                        "Query vector required for Cosmos DB backend",
                        extra={"backend": self.backend.value}
                    )
                    return []
                
                results = await self._retrieve_cosmos_db(
                    query_vector=query_vector,
                    engagement_id=engagement_id,
                    top_k=top_k,
                    similarity_threshold=similarity_threshold
                )
            else:
                results = []
            
            duration = time.time() - start_time
            
            # Record metrics
            self._record_metrics(RetrievalMetrics(
                backend=self.backend.value,
                query_length=len(query),
                results_found=len(results),
                search_duration_seconds=duration,
                use_semantic_ranking=use_semantic_ranking,
                top_k=top_k,
                engagement_id=engagement_id,
                success=True
            ))
            
            self.logger.info(
                "RAG retrieval completed",
                extra={
                    "backend": self.backend.value,
                    "engagement_id": engagement_id,
                    "results_found": len(results),
                    "duration_seconds": round(duration, 3)
                }
            )
            
            return results
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Record failed metrics
            self._record_metrics(RetrievalMetrics(
                backend=self.backend.value,
                query_length=len(query),
                results_found=0,
                search_duration_seconds=duration,
                use_semantic_ranking=use_semantic_ranking,
                top_k=top_k,
                engagement_id=engagement_id,
                success=False,
                error_message=str(e)
            ))
            
            self.logger.error(
                "RAG retrieval failed",
                extra={
                    "backend": self.backend.value,
                    "engagement_id": engagement_id,
                    "error": str(e)
                }
            )
            return []
    
    async def _retrieve_azure_search(
        self,
        query: str,
        query_vector: Optional[List[float]],
        engagement_id: str,
        top_k: int,
        use_semantic_ranking: bool,
        similarity_threshold: Optional[float]
    ) -> List[RetrievalResult]:
        """Retrieve using Azure Cognitive Search"""
        try:
            # Generate query vector if not provided
            if not query_vector:
                # For Azure Search, we can use the built-in vectorizer
                # or generate using the embeddings service
                from .embeddings import create_embeddings_service
                embeddings_service = create_embeddings_service(self.correlation_id)
                
                query_chunks = embeddings_service.chunk_text(query, "search_query")
                if query_chunks:
                    query_embeddings = await embeddings_service.generate_embeddings(
                        query_chunks[:1], "search_query"
                    )
                    if query_embeddings:
                        query_vector = query_embeddings[0].embedding
                
                if not query_vector:
                    self.logger.warning("Failed to generate query vector for Azure Search")
                    return []
            
            # Perform search
            search_results = await self.azure_search_manager.search(
                query_vector=query_vector,
                engagement_id=engagement_id,
                top_k=top_k,
                use_semantic_ranking=use_semantic_ranking,
                similarity_threshold=similarity_threshold
            )
            
            # Convert to RetrievalResult
            results = []
            for i, search_result in enumerate(search_results, 1):
                result = RetrievalResult(
                    document_id=search_result.document.doc_id,
                    chunk_index=search_result.document.chunk_index,
                    content=search_result.document.content,
                    filename=search_result.document.filename,
                    similarity_score=search_result.score,
                    engagement_id=search_result.document.engagement_id,
                    uploaded_by=search_result.document.uploaded_by,
                    uploaded_at=search_result.document.uploaded_at,
                    metadata={"content_type": search_result.document.content_type, "size": search_result.document.size},
                    citation=f"[{i}] {search_result.document.filename}",
                    backend_used=self.backend.value,
                    reranker_score=search_result.reranker_score,
                    highlights=search_result.highlights
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Azure Search retrieval failed",
                extra={"error": str(e)}
            )
            raise
    
    async def _retrieve_cosmos_db(
        self,
        query_vector: List[float],
        engagement_id: str,
        top_k: int,
        similarity_threshold: Optional[float]
    ) -> List[RetrievalResult]:
        """Retrieve using Cosmos DB with RAG service"""
        try:
            # Use the existing RAG service search method
            rag_results = await self.rag_service.search(
                query="",  # Not used in vector search
                engagement_id=engagement_id,
                top_k=top_k
            )
            
            # Filter by similarity threshold if specified
            if similarity_threshold:
                rag_results = [r for r in rag_results if r.similarity_score >= similarity_threshold]
            
            # Convert to RetrievalResult
            results = []
            for rag_result in rag_results:
                result = RetrievalResult(
                    document_id=rag_result.document_id,
                    chunk_index=rag_result.chunk_index,
                    content=rag_result.content,
                    filename=rag_result.filename,
                    similarity_score=rag_result.similarity_score,
                    engagement_id=rag_result.engagement_id,
                    uploaded_by=rag_result.uploaded_by,
                    uploaded_at=rag_result.uploaded_at,
                    metadata=rag_result.metadata,
                    citation=rag_result.citation,
                    backend_used=self.backend.value
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Cosmos DB retrieval failed",
                extra={"error": str(e)}
            )
            raise
    
    async def ingest_documents(self, embeddings: List[EmbeddingDocument]) -> Dict[str, Any]:
        """Ingest documents into the search backend"""
        if not self.is_operational():
            return {"status": "skipped", "reason": "retriever not operational"}
        
        try:
            if self.backend == SearchBackend.AZURE_SEARCH:
                # Upload to Azure Search
                successful, errors = await self.azure_search_manager.upload_documents(embeddings)
                return {
                    "status": "success" if successful == len(embeddings) else "partial",
                    "backend": self.backend.value,
                    "documents_processed": successful,
                    "total_documents": len(embeddings),
                    "errors": errors
                }
                
            elif self.backend == SearchBackend.COSMOS_DB:
                # Use RAG service for ingestion
                # Note: This requires converting to Document objects and calling ingest_document
                # For now, we'll return a not implemented status
                return {
                    "status": "not_implemented",
                    "backend": self.backend.value,
                    "reason": "Cosmos DB ingestion should use RAG service directly"
                }
            
        except Exception as e:
            self.logger.error(
                "Failed to ingest documents",
                extra={
                    "backend": self.backend.value,
                    "error": str(e)
                }
            )
            return {"status": "error", "error": str(e)}
    
    async def delete_documents(self, engagement_id: str, doc_id: Optional[str] = None) -> bool:
        """Delete documents from the search backend"""
        if not self.is_operational():
            return True  # Consider successful if not operational
        
        try:
            if self.backend == SearchBackend.AZURE_SEARCH:
                # Build filter expression
                if doc_id:
                    filter_expr = f"engagement_id eq '{engagement_id}' and doc_id eq '{doc_id}'"
                else:
                    filter_expr = f"engagement_id eq '{engagement_id}'"
                
                deleted_count = await self.azure_search_manager.delete_documents_by_filter(filter_expr)
                
                self.logger.info(
                    "Deleted documents from Azure Search",
                    extra={
                        "engagement_id": engagement_id,
                        "doc_id": doc_id,
                        "deleted_count": deleted_count
                    }
                )
                return True
                
            elif self.backend == SearchBackend.COSMOS_DB:
                # Use RAG service for deletion
                if doc_id:
                    return await self.rag_service.delete_document_embeddings(engagement_id, doc_id)
                else:
                    # Delete all embeddings for engagement
                    # Note: This requires adding a method to RAG service
                    self.logger.warning(
                        "Engagement-wide deletion not implemented for Cosmos DB backend",
                        extra={"engagement_id": engagement_id}
                    )
                    return False
            
        except Exception as e:
            self.logger.error(
                "Failed to delete documents",
                extra={
                    "backend": self.backend.value,
                    "engagement_id": engagement_id,
                    "doc_id": doc_id,
                    "error": str(e)
                }
            )
            return False
        
        return True
    
    def format_results_for_context(self, results: List[RetrievalResult]) -> str:
        """Format retrieval results for LLM context"""
        if not results:
            return "No relevant documents found."
        
        context_parts = []
        for result in results:
            content = result.content.strip()
            
            # Truncate very long content
            if len(content) > 500:
                content = content[:500] + "..."
            
            # Add highlights if available (Azure Search)
            if result.highlights and "content" in result.highlights:
                highlighted_content = " ... ".join(result.highlights["content"])
                content = f"{highlighted_content}\n\nFull excerpt: {content}"
            
            context_parts.append(f"{result.citation}:\n{content}\n")
        
        return "\n".join(context_parts)
    
    def get_status(self) -> Dict[str, Any]:
        """Get retriever status for monitoring"""
        status = {
            "backend": self.backend.value,
            "operational": self.is_operational(),
            "config": {
                "search_backend": config.rag.search_backend,
                "azure_search_endpoint": config.azure_search.endpoint,
                "azure_search_index": config.azure_search.index_name,
                "cosmos_enabled": config.is_rag_enabled()
            }
        }
        
        if self.backend == SearchBackend.AZURE_SEARCH and self.azure_search_manager:
            try:
                # Get Azure Search specific status
                if self.azure_search_manager.index_exists():
                    status["azure_search"] = {
                        "index_exists": True,
                        "index_name": config.azure_search.index_name
                    }
                else:
                    status["azure_search"] = {"index_exists": False}
            except:
                status["azure_search"] = {"status": "error"}
        
        elif self.backend == SearchBackend.COSMOS_DB and self.rag_service:
            status["cosmos_db"] = self.rag_service.get_status()
        
        return status
    
    def _record_metrics(self, metrics: RetrievalMetrics):
        """Record retrieval metrics"""
        # For now, just log the metrics
        # In production, you might want to send to a monitoring system
        self.logger.info(
            "RAG retrieval metrics",
            extra={
                "backend": metrics.backend,
                "query_length": metrics.query_length,
                "results_found": metrics.results_found,
                "duration_seconds": metrics.search_duration_seconds,
                "success": metrics.success,
                "error": metrics.error_message
            }
        )


def create_rag_retriever(correlation_id: Optional[str] = None) -> RAGRetriever:
    """Factory function to create a RAG retriever"""
    return RAGRetriever(correlation_id=correlation_id)