"""
Azure Cognitive Search index schema and management for RAG.
Provides efficient vector search with semantic ranking capabilities.
"""
import asyncio
import logging
import json
import os
import time
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchProfile,
    VectorSearchAlgorithmConfiguration,
    HnswAlgorithmConfiguration,
    VectorSearchVectorizer,
    AzureOpenAIVectorizer,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch
)
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

from domain.models import EmbeddingDocument
import sys
sys.path.append("/app")
from config import config


logger = logging.getLogger(__name__)


@dataclass 
class SearchDocument:
    """Document format for Azure Cognitive Search"""
    id: str
    engagement_id: str
    doc_id: str
    chunk_id: str
    content: str
    filename: str
    uploaded_by: str
    uploaded_at: str
    chunk_index: int
    chunk_start: int
    chunk_end: int
    token_count: int
    model: str
    content_type: str
    size: int
    vector: List[float]
    metadata: str  # JSON string of metadata
    
    @classmethod
    def from_embedding_document(cls, embed_doc: EmbeddingDocument) -> "SearchDocument":
        """Convert EmbeddingDocument to SearchDocument"""
        return cls(
            id=embed_doc.id,
            engagement_id=embed_doc.engagement_id,
            doc_id=embed_doc.doc_id,
            chunk_id=embed_doc.chunk_id,
            content=embed_doc.text,
            filename=embed_doc.filename,
            uploaded_by=embed_doc.uploaded_by,
            uploaded_at=embed_doc.uploaded_at.isoformat() if embed_doc.uploaded_at else "",
            chunk_index=embed_doc.chunk_index,
            chunk_start=embed_doc.chunk_start,
            chunk_end=embed_doc.chunk_end,
            token_count=embed_doc.token_count,
            model=embed_doc.model,
            content_type=embed_doc.metadata.get("content_type", ""),
            size=embed_doc.metadata.get("size", 0),
            vector=embed_doc.vector,
            metadata=json.dumps(embed_doc.metadata)
        )


@dataclass
class SearchResult:
    """Result from Azure Cognitive Search"""
    document: SearchDocument
    score: float
    reranker_score: Optional[float] = None
    highlights: Optional[Dict[str, List[str]]] = None


class AzureSearchIndexManager:
    """Manages Azure Cognitive Search index for RAG"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or "unknown"
        self.index_name = config.azure_search.index_name
        self.endpoint = config.azure_search.endpoint
        self.vector_dimensions = config.azure_openai.embedding_dimensions
        
        # Initialize clients
        self._initialize_clients()
        
    def _initialize_clients(self):
        """Initialize Azure Search clients"""
        try:
            # Use API key or managed identity
            if config.azure_search.api_key:
                credential = AzureKeyCredential(config.azure_search.api_key)
            else:
                credential = DefaultAzureCredential()
            
            self.index_client = SearchIndexClient(
                endpoint=self.endpoint,
                credential=credential
            )
            
            self.search_client = SearchClient(
                endpoint=self.endpoint,
                index_name=self.index_name,
                credential=credential
            )
            
            logger.info(
                "Initialized Azure Search clients",
                extra={
                    "correlation_id": self.correlation_id,
                    "endpoint": self.endpoint,
                    "index_name": self.index_name
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to initialize Azure Search clients",
                extra={
                    "correlation_id": self.correlation_id,
                    "error": str(e)
                }
            )
            raise
    
    def create_index(self) -> bool:
        """Create the search index with vector search configuration"""
        try:
            logger.info(
                "Creating Azure Search index",
                extra={
                    "correlation_id": self.correlation_id,
                    "index_name": self.index_name
                }
            )
            
            # Define the search fields
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SimpleField(name="engagement_id", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="doc_id", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="chunk_id", type=SearchFieldDataType.String),
                SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
                SearchableField(name="filename", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="uploaded_by", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="uploaded_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
                SimpleField(name="chunk_start", type=SearchFieldDataType.Int32),
                SimpleField(name="chunk_end", type=SearchFieldDataType.Int32),
                SimpleField(name="token_count", type=SearchFieldDataType.Int32, filterable=True),
                SimpleField(name="model", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="content_type", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="size", type=SearchFieldDataType.Int32, filterable=True),
                SearchField(
                    name="vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=self.vector_dimensions,
                    vector_search_profile_name="myHnswProfile"
                ),
                SimpleField(name="metadata", type=SearchFieldDataType.String)
            ]
            
            # Configure vector search
            vector_search = VectorSearch(
                profiles=[
                    VectorSearchProfile(
                        name="myHnswProfile",
                        algorithm_configuration_name="myHnsw",
                        vectorizer="myOpenAI"
                    )
                ],
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="myHnsw",
                        parameters={
                            "m": 4,
                            "efConstruction": 400,
                            "efSearch": 500,
                            "metric": "cosine"
                        }
                    )
                ],
                vectorizers=[
                    AzureOpenAIVectorizer(
                        name="myOpenAI",
                        resource_uri=config.azure_openai.endpoint,
                        deployment_id=config.azure_openai.embedding_model,
                        api_key=config.azure_openai.api_key if config.azure_openai.api_key else None
                    )
                ]
            )
            
            # Configure semantic search for better ranking
            semantic_config = SemanticConfiguration(
                name="my-semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="filename"),
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[SemanticField(field_name="doc_id")]
                )
            )
            
            semantic_search = SemanticSearch(configurations=[semantic_config])
            
            # Create the index
            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                vector_search=vector_search,
                semantic_search=semantic_search
            )
            
            result = self.index_client.create_or_update_index(index)
            
            logger.info(
                "Successfully created Azure Search index",
                extra={
                    "correlation_id": self.correlation_id,
                    "index_name": self.index_name,
                    "vector_dimensions": self.vector_dimensions
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to create Azure Search index",
                extra={
                    "correlation_id": self.correlation_id,
                    "error": str(e)
                }
            )
            return False
    
    def delete_index(self) -> bool:
        """Delete the search index"""
        try:
            self.index_client.delete_index(self.index_name)
            logger.info(
                "Deleted Azure Search index",
                extra={
                    "correlation_id": self.correlation_id,
                    "index_name": self.index_name
                }
            )
            return True
            
        except Exception as e:
            logger.error(
                "Failed to delete Azure Search index", 
                extra={
                    "correlation_id": self.correlation_id,
                    "error": str(e)
                }
            )
            return False
    
    def index_exists(self) -> bool:
        """Check if the index exists"""
        try:
            self.index_client.get_index(self.index_name)
            return True
        except:
            return False
    
    async def upload_documents(self, embeddings: List[EmbeddingDocument]) -> Tuple[int, List[str]]:
        """Upload embedding documents to the search index"""
        if not embeddings:
            return 0, []
        
        try:
            logger.info(
                "Uploading documents to search index",
                extra={
                    "correlation_id": self.correlation_id,
                    "document_count": len(embeddings),
                    "index_name": self.index_name
                }
            )
            
            # Convert to search documents
            search_docs = [SearchDocument.from_embedding_document(embed) for embed in embeddings]
            doc_dicts = [asdict(doc) for doc in search_docs]
            
            # Upload in batches (Azure Search has a 1000 document limit per batch)
            batch_size = 100  # Conservative batch size for reliability
            successful = 0
            errors = []
            
            for i in range(0, len(doc_dicts), batch_size):
                batch = doc_dicts[i:i + batch_size]
                
                try:
                    result = await asyncio.to_thread(
                        self.search_client.upload_documents,
                        documents=batch
                    )
                    
                    # Check results
                    for upload_result in result:
                        if upload_result.succeeded:
                            successful += 1
                        else:
                            error_msg = f"Failed to upload document {upload_result.key}: {upload_result.error_message}"
                            errors.append(error_msg)
                            
                except Exception as e:
                    error_msg = f"Batch upload failed: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(
                        "Failed to upload document batch",
                        extra={
                            "correlation_id": self.correlation_id,
                            "batch_start": i,
                            "batch_size": len(batch),
                            "error": str(e)
                        }
                    )
                
                # Add delay between batches to avoid rate limiting
                if i + batch_size < len(doc_dicts):
                    await asyncio.sleep(0.1)
            
            logger.info(
                "Completed document upload to search index",
                extra={
                    "correlation_id": self.correlation_id,
                    "total_documents": len(embeddings),
                    "successful": successful,
                    "failed": len(errors)
                }
            )
            
            return successful, errors
            
        except Exception as e:
            logger.error(
                "Failed to upload documents to search index",
                extra={
                    "correlation_id": self.correlation_id,
                    "error": str(e)
                }
            )
            raise
    
    async def search(
        self,
        query_vector: List[float],
        engagement_id: str,
        top_k: Optional[int] = None,
        use_semantic_ranking: bool = True,
        similarity_threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """Perform vector search with optional semantic ranking"""
        try:
            top_k = top_k or config.rag.search_top_k
            
            logger.info(
                "Starting Azure Search vector search",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "top_k": top_k,
                    "use_semantic_ranking": use_semantic_ranking,
                    "vector_dimensions": len(query_vector)
                }
            )
            
            start_time = time.time()
            
            # Create vector query
            vector_query = VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=top_k,
                fields="vector"
            )
            
            # Search parameters
            search_params = {
                "search_text": "*",  # Use * for pure vector search
                "vector_queries": [vector_query],
                "filter": f"engagement_id eq '{engagement_id}'",
                "top": top_k,
                "include_total_count": True,
                "highlight_fields": "content" if use_semantic_ranking else None
            }
            
            # Add semantic ranking if enabled
            if use_semantic_ranking:
                search_params.update({
                    "query_type": "semantic",
                    "semantic_configuration_name": "my-semantic-config",
                    "query_caption": "extractive",
                    "query_answer": "extractive"
                })
            
            # Perform search
            search_results = await asyncio.to_thread(
                lambda: self.search_client.search(**search_params)
            )
            
            # Process results
            results = []
            for result in search_results:
                # Apply similarity threshold if specified
                score = result.get("@search.score", 0.0)
                if similarity_threshold and score < similarity_threshold:
                    continue
                
                # Create SearchDocument from result
                search_doc = SearchDocument(
                    id=result["id"],
                    engagement_id=result["engagement_id"], 
                    doc_id=result["doc_id"],
                    chunk_id=result["chunk_id"],
                    content=result["content"],
                    filename=result["filename"],
                    uploaded_by=result["uploaded_by"],
                    uploaded_at=result["uploaded_at"],
                    chunk_index=result["chunk_index"],
                    chunk_start=result["chunk_start"],
                    chunk_end=result["chunk_end"],
                    token_count=result["token_count"],
                    model=result["model"],
                    content_type=result["content_type"],
                    size=result["size"],
                    vector=result.get("vector", []),
                    metadata=result["metadata"]
                )
                
                search_result = SearchResult(
                    document=search_doc,
                    score=score,
                    reranker_score=result.get("@search.reranker_score"),
                    highlights=result.get("@search.highlights")
                )
                
                results.append(search_result)
            
            search_duration = time.time() - start_time
            
            logger.info(
                "Azure Search vector search completed",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "results_found": len(results),
                    "search_duration_seconds": round(search_duration, 3),
                    "use_semantic_ranking": use_semantic_ranking
                }
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Azure Search vector search failed",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "error": str(e)
                }
            )
            raise
    
    async def delete_documents_by_filter(self, filter_expression: str) -> int:
        """Delete documents matching a filter"""
        try:
            logger.info(
                "Deleting documents by filter",
                extra={
                    "correlation_id": self.correlation_id,
                    "filter": filter_expression
                }
            )
            
            # First, find documents to delete
            search_results = await asyncio.to_thread(
                lambda: self.search_client.search(
                    search_text="*",
                    filter=filter_expression,
                    select="id",
                    top=1000  # Azure Search limit
                )
            )
            
            # Collect document IDs
            doc_ids = [result["id"] for result in search_results]
            
            if not doc_ids:
                return 0
            
            # Delete documents in batches
            batch_size = 100
            deleted_count = 0
            
            for i in range(0, len(doc_ids), batch_size):
                batch_ids = doc_ids[i:i + batch_size]
                delete_docs = [{"id": doc_id} for doc_id in batch_ids]
                
                try:
                    result = await asyncio.to_thread(
                        self.search_client.delete_documents,
                        documents=delete_docs
                    )
                    
                    for delete_result in result:
                        if delete_result.succeeded:
                            deleted_count += 1
                            
                except Exception as e:
                    logger.warning(
                        "Failed to delete document batch",
                        extra={
                            "correlation_id": self.correlation_id,
                            "batch_start": i,
                            "error": str(e)
                        }
                    )
                
                # Add delay between batches
                if i + batch_size < len(doc_ids):
                    await asyncio.sleep(0.1)
            
            logger.info(
                "Completed document deletion",
                extra={
                    "correlation_id": self.correlation_id,
                    "filter": filter_expression,
                    "deleted_count": deleted_count
                }
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error(
                "Failed to delete documents by filter",
                extra={
                    "correlation_id": self.correlation_id,
                    "filter": filter_expression,
                    "error": str(e)
                }
            )
            raise
    
    async def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        try:
            # Get document count
            count_result = await asyncio.to_thread(
                lambda: self.search_client.search(
                    search_text="*",
                    include_total_count=True,
                    top=0
                )
            )
            
            total_docs = count_result.get_count()
            
            # Get index info
            index = self.index_client.get_index(self.index_name)
            
            return {
                "index_name": self.index_name,
                "total_documents": total_docs,
                "field_count": len(index.fields),
                "vector_search_enabled": index.vector_search is not None,
                "semantic_search_enabled": index.semantic_search is not None
            }
            
        except Exception as e:
            logger.error(
                "Failed to get index stats",
                extra={
                    "correlation_id": self.correlation_id,
                    "error": str(e)
                }
            )
            return {"error": str(e)}


def create_azure_search_index_manager(correlation_id: Optional[str] = None) -> AzureSearchIndexManager:
    """Factory function to create Azure Search Index Manager"""
    return AzureSearchIndexManager(correlation_id=correlation_id)