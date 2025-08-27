"""
RAG (Retrieval-Augmented Generation) service for document ingestion and vector search.
Integrates with Azure AI Search for vector storage and hybrid search capabilities.
"""
import asyncio
import json
import logging
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery, VectorFilterMode
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

from services.embeddings import EmbeddingResult, create_embeddings_service
from domain.models import Document, EmbeddingDocument
from repos.cosmos_embeddings_repository import create_cosmos_embeddings_repository, VectorSearchResult
import sys
sys.path.append("/app")
from config import config


logger = logging.getLogger(__name__)


@dataclass
class SearchDocument:
    """Document structure for Azure AI Search index"""
    id: str
    engagement_id: str
    document_id: str
    chunk_index: int
    content: str
    content_vector: List[float]
    filename: str
    uploaded_by: str
    uploaded_at: str
    chunk_start: int
    chunk_end: int
    token_count: int
    metadata: Dict[str, Any]


@dataclass
class SearchResult:
    """Result from vector search"""
    document_id: str
    chunk_index: int
    content: str
    filename: str
    score: float
    engagement_id: str
    uploaded_by: str
    uploaded_at: str
    metadata: Dict[str, Any]


@dataclass
class IngestionStatus:
    """Status of document ingestion process"""
    document_id: str
    status: str  # "pending", "processing", "completed", "failed"
    chunks_processed: int
    total_chunks: int
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class RAGService:
    """Service for RAG document ingestion and search"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or "unknown"
        self.search_client = None
        self.index_client = None
        self.embeddings_service = create_embeddings_service(correlation_id)
        self._ingestion_status: Dict[str, IngestionStatus] = {}
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Azure AI Search clients"""
        try:
            # Use API key if provided, otherwise use managed identity
            if config.azure_search.api_key:
                credential = AzureKeyCredential(config.azure_search.api_key)
            else:
                credential = DefaultAzureCredential()
            
            self.search_client = SearchClient(
                endpoint=config.azure_search.endpoint,
                index_name=config.azure_search.index_name,
                credential=credential,
                api_version=config.azure_search.api_version
            )
            
            self.index_client = SearchIndexClient(
                endpoint=config.azure_search.endpoint,
                credential=credential,
                api_version=config.azure_search.api_version
            )
            
            logger.info(
                "Initialized Azure AI Search clients",
                extra={
                    "correlation_id": self.correlation_id,
                    "endpoint": config.azure_search.endpoint,
                    "index": config.azure_search.index_name,
                    "api_version": config.azure_search.api_version
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to initialize Azure AI Search clients",
                extra={
                    "correlation_id": self.correlation_id,
                    "error": str(e),
                    "endpoint": config.azure_search.endpoint
                }
            )
            raise
    
    async def ingest_document(
        self, 
        document: Document, 
        text_content: str
    ) -> IngestionStatus:
        """
        Ingest a document into the search index.
        
        Args:
            document: Document metadata
            text_content: Extracted text content
            
        Returns:
            IngestionStatus object
        """
        doc_id = document.id
        
        try:
            # Initialize status tracking
            status = IngestionStatus(
                document_id=doc_id,
                status="processing",
                chunks_processed=0,
                total_chunks=0,
                started_at=datetime.now(timezone.utc)
            )
            self._ingestion_status[doc_id] = status
            
            logger.info(
                "Starting document ingestion",
                extra={
                    "correlation_id": self.correlation_id,
                    "document_id": doc_id,
                    "engagement_id": document.engagement_id,
                    "filename": document.filename,
                    "text_length": len(text_content)
                }
            )
            
            # Generate embeddings
            embeddings = await self.embeddings_service.embed_document(text_content, doc_id)
            status.total_chunks = len(embeddings)
            
            if not embeddings:
                raise ValueError("No embeddings generated for document")
            
            # Prepare search documents
            search_docs = []
            for embedding_result in embeddings:
                search_doc = SearchDocument(
                    id=f"{doc_id}_{embedding_result.chunk.chunk_index}",
                    engagement_id=document.engagement_id,
                    document_id=doc_id,
                    chunk_index=embedding_result.chunk.chunk_index,
                    content=embedding_result.chunk.text,
                    content_vector=embedding_result.embedding,
                    filename=document.filename,
                    uploaded_by=document.uploaded_by,
                    uploaded_at=document.uploaded_at.isoformat(),
                    chunk_start=embedding_result.chunk.start_index,
                    chunk_end=embedding_result.chunk.end_index,
                    token_count=embedding_result.usage_tokens,
                    metadata={
                        "content_type": document.content_type,
                        "size": document.size,
                        "model": embedding_result.model,
                        "chunk_token_count": embedding_result.chunk.token_count or 0
                    }
                )
                search_docs.append(asdict(search_doc))
            
            # Upload to search index in batches
            batch_size = 50  # Azure AI Search recommendation
            total_batches = (len(search_docs) + batch_size - 1) // batch_size
            
            for batch_idx in range(0, len(search_docs), batch_size):
                batch_docs = search_docs[batch_idx:batch_idx + batch_size]
                batch_num = (batch_idx // batch_size) + 1
                
                logger.info(
                    "Uploading batch to search index",
                    extra={
                        "correlation_id": self.correlation_id,
                        "document_id": doc_id,
                        "batch": f"{batch_num}/{total_batches}",
                        "docs_in_batch": len(batch_docs)
                    }
                )
                
                # Upload batch with retry logic
                await self._upload_batch_with_retry(batch_docs, doc_id)
                status.chunks_processed = min(batch_idx + batch_size, len(search_docs))
            
            # Mark as completed
            status.status = "completed"
            status.completed_at = datetime.now(timezone.utc)
            
            logger.info(
                "Document ingestion completed",
                extra={
                    "correlation_id": self.correlation_id,
                    "document_id": doc_id,
                    "engagement_id": document.engagement_id,
                    "chunks_indexed": len(embeddings),
                    "total_batches": total_batches
                }
            )
            
            return status
            
        except Exception as e:
            # Mark as failed
            status = self._ingestion_status.get(doc_id, IngestionStatus(
                document_id=doc_id,
                status="failed",
                chunks_processed=0,
                total_chunks=0
            ))
            status.status = "failed"
            status.error = str(e)
            status.completed_at = datetime.now(timezone.utc)
            self._ingestion_status[doc_id] = status
            
            logger.error(
                "Document ingestion failed",
                extra={
                    "correlation_id": self.correlation_id,
                    "document_id": doc_id,
                    "engagement_id": document.engagement_id,
                    "error": str(e)
                }
            )
            raise
    
    async def _upload_batch_with_retry(self, batch_docs: List[Dict], doc_id: str):
        """Upload a batch of documents with retry logic"""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries + 1):
            try:
                result = await asyncio.to_thread(
                    self.search_client.upload_documents,
                    batch_docs
                )
                
                # Check for partial failures
                failed_docs = [r for r in result if not r.succeeded]
                if failed_docs:
                    error_details = [f"Doc {r.key}: {r.error_message}" for r in failed_docs]
                    raise Exception(f"Failed to upload {len(failed_docs)} documents: {'; '.join(error_details)}")
                
                logger.debug(
                    "Batch uploaded successfully",
                    extra={
                        "correlation_id": self.correlation_id,
                        "document_id": doc_id,
                        "batch_size": len(batch_docs),
                        "attempt": attempt + 1
                    }
                )
                return
                
            except Exception as e:
                if attempt < max_retries:
                    delay = retry_delay * (2 ** attempt)
                    logger.warning(
                        "Batch upload failed, retrying",
                        extra={
                            "correlation_id": self.correlation_id,
                            "document_id": doc_id,
                            "attempt": attempt + 1,
                            "error": str(e),
                            "retry_delay": delay
                        }
                    )
                    await asyncio.sleep(delay)
                else:
                    raise
    
    async def search(
        self, 
        query: str, 
        engagement_id: str,
        top_k: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Search for relevant documents using vector and hybrid search.
        
        Args:
            query: Search query text
            engagement_id: Filter results to this engagement
            top_k: Maximum number of results to return
            
        Returns:
            List of SearchResult objects
        """
        try:
            top_k = top_k or config.rag.search_top_k
            
            logger.info(
                "Starting document search",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "query_length": len(query),
                    "top_k": top_k,
                    "hybrid_search": config.rag.use_hybrid_search
                }
            )
            
            # Generate query embedding
            query_chunks = self.embeddings_service.chunk_text(query, "search_query")
            if not query_chunks:
                raise ValueError("Failed to process search query")
            
            # Use the first chunk for query embedding
            query_embeddings = await self.embeddings_service.generate_embeddings(
                [query_chunks[0]], "search_query"
            )
            if not query_embeddings:
                raise ValueError("Failed to generate query embedding")
            
            query_vector = query_embeddings[0].embedding
            
            # Prepare search parameters
            vector_query = VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=top_k,
                fields="content_vector"
            )
            
            # Engagement filter
            filter_expression = f"engagement_id eq '{engagement_id}'"
            
            # Execute search
            if config.rag.use_hybrid_search:
                # Hybrid search (vector + text)
                search_results = await asyncio.to_thread(
                    self.search_client.search,
                    search_text=query,
                    vector_queries=[vector_query],
                    filter=filter_expression,
                    top=top_k,
                    select=[
                        "document_id", "chunk_index", "content", "filename",
                        "engagement_id", "uploaded_by", "uploaded_at", "metadata"
                    ]
                )
            else:
                # Vector-only search
                search_results = await asyncio.to_thread(
                    self.search_client.search,
                    search_text=None,
                    vector_queries=[vector_query],
                    filter=filter_expression,
                    top=top_k,
                    select=[
                        "document_id", "chunk_index", "content", "filename",
                        "engagement_id", "uploaded_by", "uploaded_at", "metadata"
                    ]
                )
            
            # Process results
            results = []
            for result in search_results:
                if result.get("@search.score", 0) >= config.rag.similarity_threshold:
                    search_result = SearchResult(
                        document_id=result["document_id"],
                        chunk_index=result["chunk_index"],
                        content=result["content"],
                        filename=result["filename"],
                        score=result.get("@search.score", 0.0),
                        engagement_id=result["engagement_id"],
                        uploaded_by=result["uploaded_by"],
                        uploaded_at=result["uploaded_at"],
                        metadata=result.get("metadata", {})
                    )
                    results.append(search_result)
            
            logger.info(
                "Search completed",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "results_found": len(results),
                    "top_k": top_k,
                    "query_length": len(query)
                }
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Search failed",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "error": str(e),
                    "query_length": len(query) if query else 0
                }
            )
            raise
    
    async def reindex_engagement_documents(
        self, 
        engagement_id: str, 
        documents: List[Tuple[Document, str]]
    ) -> Dict[str, IngestionStatus]:
        """
        Reindex all documents for an engagement.
        
        Args:
            engagement_id: The engagement ID
            documents: List of (Document, text_content) tuples
            
        Returns:
            Dict mapping document_id to IngestionStatus
        """
        try:
            logger.info(
                "Starting engagement reindexing",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "document_count": len(documents)
                }
            )
            
            # Delete existing documents for this engagement
            await self._delete_engagement_documents(engagement_id)
            
            # Process documents concurrently (with limit)
            max_concurrent = 3  # Limit concurrent ingestion to avoid rate limits
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_document(doc_tuple):
                document, text_content = doc_tuple
                async with semaphore:
                    return await self.ingest_document(document, text_content)
            
            # Start all tasks
            tasks = [process_document(doc_tuple) for doc_tuple in documents]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect results
            status_map = {}
            for i, result in enumerate(results):
                document = documents[i][0]
                if isinstance(result, Exception):
                    status = IngestionStatus(
                        document_id=document.id,
                        status="failed",
                        chunks_processed=0,
                        total_chunks=0,
                        error=str(result),
                        completed_at=datetime.now(timezone.utc)
                    )
                else:
                    status = result
                status_map[document.id] = status
            
            successful = sum(1 for s in status_map.values() if s.status == "completed")
            failed = len(status_map) - successful
            
            logger.info(
                "Engagement reindexing completed",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "total_documents": len(documents),
                    "successful": successful,
                    "failed": failed
                }
            )
            
            return status_map
            
        except Exception as e:
            logger.error(
                "Engagement reindexing failed",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "error": str(e),
                    "document_count": len(documents)
                }
            )
            raise
    
    async def _delete_engagement_documents(self, engagement_id: str):
        """Delete all documents for an engagement from the search index"""
        try:
            # Search for all documents in the engagement
            filter_expr = f"engagement_id eq '{engagement_id}'"
            results = await asyncio.to_thread(
                self.search_client.search,
                search_text="*",
                filter=filter_expr,
                select=["id"],
                top=1000  # Adjust if needed
            )
            
            doc_ids = [result["id"] for result in results]
            
            if doc_ids:
                # Delete in batches
                batch_size = 50
                for i in range(0, len(doc_ids), batch_size):
                    batch_ids = doc_ids[i:i + batch_size]
                    delete_docs = [{"@search.action": "delete", "id": doc_id} for doc_id in batch_ids]
                    
                    await asyncio.to_thread(
                        self.search_client.index_documents,
                        documents=delete_docs
                    )
                
                logger.info(
                    "Deleted existing documents from index",
                    extra={
                        "correlation_id": self.correlation_id,
                        "engagement_id": engagement_id,
                        "deleted_count": len(doc_ids)
                    }
                )
            
        except Exception as e:
            logger.warning(
                "Failed to delete existing documents",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "error": str(e)
                }
            )
            # Don't raise - this is not critical for reindexing
    
    def get_ingestion_status(self, document_id: str) -> Optional[IngestionStatus]:
        """Get ingestion status for a document"""
        return self._ingestion_status.get(document_id)
    
    def get_engagement_ingestion_status(self, engagement_id: str) -> Dict[str, IngestionStatus]:
        """Get ingestion status for all documents in an engagement"""
        return {
            doc_id: status for doc_id, status in self._ingestion_status.items()
            if any(doc_id in status.document_id for status in [status])  # Simple filter
        }
    
    def format_search_results_for_context(self, results: List[SearchResult]) -> str:
        """Format search results into context text for LLM consumption"""
        if not results:
            return "No relevant documents found."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            citation = f"[{i}] {result.filename}"
            content = result.content.strip()
            # Truncate very long content
            if len(content) > 500:
                content = content[:500] + "..."
            
            context_parts.append(f"{citation}:\n{content}\n")
        
        return "\n".join(context_parts)


def create_rag_service(correlation_id: Optional[str] = None) -> RAGService:
    """Factory function to create a RAG service instance"""
    return RAGService(correlation_id=correlation_id)