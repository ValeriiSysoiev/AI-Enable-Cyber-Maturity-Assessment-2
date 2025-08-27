"""
Cosmos DB repository for vector embeddings storage and retrieval.
Provides efficient vector search with engagement-based filtering.
"""
import asyncio
import logging
import json
import os
import time
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError
from azure.identity import DefaultAzureCredential

from domain.models import EmbeddingDocument
import sys
sys.path.append("/app")
from config import config
from security.secret_provider import get_secret


logger = logging.getLogger(__name__)


@dataclass
class VectorSearchResult:
    """Result from vector similarity search"""
    embedding_doc: EmbeddingDocument
    similarity_score: float
    

class CosmosEmbeddingsRepository:
    """Repository for managing vector embeddings in Cosmos DB"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or "unknown"
        self.client = None
        self.database = None
        self.container = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Cosmos DB client with managed identity authentication"""
        try:
            # Use managed identity for authentication (no API keys)
            credential = DefaultAzureCredential()
            
            # Get Cosmos DB configuration from environment (fallback for sync init)
            cosmos_endpoint = os.getenv("COSMOS_ENDPOINT")
            cosmos_database = os.getenv("COSMOS_DATABASE", "cybermaturity")
            
            if not cosmos_endpoint:
                raise ValueError("COSMOS_ENDPOINT environment variable is required")
            
            self.client = CosmosClient(
                url=cosmos_endpoint,
                credential=credential
            )
            
            # Get or create database
            self.database = self.client.get_database_client(cosmos_database)
            
            # Get or create embeddings container
            container_name = config.rag.cosmos_container_name
            try:
                self.container = self.database.get_container_client(container_name)
            except CosmosResourceNotFoundError:
                # Create container with appropriate partition key for engagement-based queries
                self.container = self.database.create_container(
                    id=container_name,
                    partition_key=PartitionKey(path="/engagement_id"),
                    offer_throughput=400  # Start with minimal throughput
                )
            
            logger.info(
                "Initialized Cosmos DB embeddings repository (will upgrade to secret provider)",
                extra={
                    "correlation_id": self.correlation_id,
                    "endpoint": cosmos_endpoint,
                    "database": cosmos_database,
                    "container": container_name
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to initialize Cosmos DB embeddings repository",
                extra={
                    "correlation_id": self.correlation_id,
                    "error": str(e)
                }
            )
            raise
    
    async def _initialize_client_async(self):
        """Initialize Cosmos DB client with secret provider (async version)"""
        try:
            # Use managed identity for authentication (no API keys)
            credential = DefaultAzureCredential()
            
            # Get Cosmos DB configuration from secret provider
            cosmos_endpoint = await get_secret("cosmos-endpoint", self.correlation_id)
            cosmos_database = await get_secret("cosmos-database", self.correlation_id)
            
            # Fallback to environment variables for local development
            if not cosmos_endpoint:
                cosmos_endpoint = os.getenv("COSMOS_ENDPOINT")
            if not cosmos_database:
                cosmos_database = os.getenv("COSMOS_DATABASE", "cybermaturity")
            
            if not cosmos_endpoint:
                raise ValueError("COSMOS_ENDPOINT secret or environment variable is required")
            
            self.client = CosmosClient(
                url=cosmos_endpoint,
                credential=credential
            )
            
            # Get or create database
            self.database = self.client.get_database_client(cosmos_database)
            
            # Get or create embeddings container
            container_name = config.rag.cosmos_container_name
            try:
                self.container = self.database.get_container_client(container_name)
            except CosmosResourceNotFoundError:
                # Create container with appropriate partition key for engagement-based queries
                self.container = self.database.create_container(
                    id=container_name,
                    partition_key=PartitionKey(path="/engagement_id"),
                    offer_throughput=400  # Start with minimal throughput
                )
            
            logger.info(
                "Initialized Cosmos DB embeddings repository with secret provider",
                extra={
                    "correlation_id": self.correlation_id,
                    "endpoint": cosmos_endpoint,
                    "database": cosmos_database,
                    "container": container_name
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to initialize Cosmos DB embeddings repository with secret provider",
                extra={
                    "correlation_id": self.correlation_id,
                    "error": str(e)
                }
            )
            raise
    
    async def store_embeddings(
        self, 
        embeddings: List[EmbeddingDocument]
    ) -> Tuple[int, List[str]]:
        """
        Store embedding documents in Cosmos DB.
        
        Args:
            embeddings: List of EmbeddingDocument objects to store
            
        Returns:
            Tuple of (successful_count, error_messages)
        """
        if not embeddings:
            return 0, []
        
        try:
            logger.info(
                "Starting embeddings storage",
                extra={
                    "correlation_id": self.correlation_id,
                    "embedding_count": len(embeddings),
                    "engagement_id": embeddings[0].engagement_id if embeddings else None
                }
            )
            
            successful = 0
            errors = []
            
            # Process embeddings in batches to avoid rate limits
            batch_size = 25  # Cosmos DB batch operation limit
            for i in range(0, len(embeddings), batch_size):
                batch = embeddings[i:i + batch_size]
                
                logger.debug(
                    "Processing embeddings batch",
                    extra={
                        "correlation_id": self.correlation_id,
                        "batch_start": i,
                        "batch_size": len(batch)
                    }
                )
                
                # Store each embedding individually (Cosmos DB doesn't support vector batch operations)
                for embedding in batch:
                    try:
                        # Convert to dict for Cosmos DB storage
                        doc_dict = embedding.model_dump()
                        doc_dict["id"] = embedding.id  # Ensure id is set for Cosmos DB
                        
                        # Store with upsert to handle duplicates
                        await asyncio.to_thread(
                            self.container.upsert_item,
                            body=doc_dict
                        )
                        successful += 1
                        
                    except CosmosHttpResponseError as e:
                        error_msg = f"Failed to store embedding {embedding.id}: {e.message}"
                        errors.append(error_msg)
                        logger.warning(
                            "Failed to store individual embedding",
                            extra={
                                "correlation_id": self.correlation_id,
                                "embedding_id": embedding.id,
                                "error": str(e)
                            }
                        )
                    except Exception as e:
                        error_msg = f"Unexpected error storing embedding {embedding.id}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(
                            "Unexpected error storing embedding",
                            extra={
                                "correlation_id": self.correlation_id,
                                "embedding_id": embedding.id,
                                "error": str(e)
                            }
                        )
                
                # Add delay between batches to avoid rate limiting
                if i + batch_size < len(embeddings):
                    await asyncio.sleep(0.1)
            
            logger.info(
                "Completed embeddings storage",
                extra={
                    "correlation_id": self.correlation_id,
                    "total_embeddings": len(embeddings),
                    "successful": successful,
                    "failed": len(errors)
                }
            )
            
            return successful, errors
            
        except Exception as e:
            logger.error(
                "Failed to store embeddings",
                extra={
                    "correlation_id": self.correlation_id,
                    "error": str(e),
                    "embedding_count": len(embeddings)
                }
            )
            raise
    
    async def vector_search(
        self, 
        query_vector: List[float],
        engagement_id: str,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None
    ) -> List[VectorSearchResult]:
        """
        Perform vector similarity search with engagement filtering.
        
        Args:
            query_vector: Query embedding vector
            engagement_id: Filter results to this engagement
            top_k: Maximum number of results to return
            similarity_threshold: Minimum similarity score threshold
            
        Returns:
            List of VectorSearchResult objects
        """
        try:
            top_k = top_k or config.rag.search_top_k
            similarity_threshold = similarity_threshold or config.rag.similarity_threshold
            
            logger.info(
                "Starting vector search",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "top_k": top_k,
                    "similarity_threshold": similarity_threshold,
                    "vector_dimensions": len(query_vector)
                }
            )
            
            start_time = time.time()
            
            # Note: Cosmos DB doesn't have native vector search yet
            # We'll implement a brute-force approach for now
            # In production, consider Azure Cognitive Search for vector search
            
            # Query all embeddings for the engagement
            query = {
                "query": "SELECT * FROM c WHERE c.engagement_id = @engagement_id",
                "parameters": [
                    {"name": "@engagement_id", "value": engagement_id}
                ]
            }
            
            items = await asyncio.to_thread(
                lambda: list(self.container.query_items(
                    query=query["query"],
                    parameters=query["parameters"],
                    partition_key=engagement_id
                ))
            )
            
            # Calculate similarity scores
            results = []
            for item in items:
                try:
                    # Convert back to EmbeddingDocument
                    embedding_doc = EmbeddingDocument(**item)
                    
                    # Calculate cosine similarity
                    similarity = self._calculate_cosine_similarity(query_vector, embedding_doc.vector)
                    
                    if similarity >= similarity_threshold:
                        results.append(VectorSearchResult(
                            embedding_doc=embedding_doc,
                            similarity_score=similarity
                        ))
                        
                except Exception as e:
                    logger.warning(
                        "Failed to process embedding document in search",
                        extra={
                            "correlation_id": self.correlation_id,
                            "item_id": item.get("id", "unknown"),
                            "error": str(e)
                        }
                    )
                    continue
            
            # Sort by similarity score and limit results
            results.sort(key=lambda r: r.similarity_score, reverse=True)
            results = results[:top_k]
            
            search_duration = time.time() - start_time
            
            logger.info(
                "Vector search completed",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "results_found": len(results),
                    "total_candidates": len(items),
                    "search_duration_seconds": round(search_duration, 3),
                    "top_k": top_k
                }
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Vector search failed",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "error": str(e)
                }
            )
            raise
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            if len(vec1) != len(vec2):
                return 0.0
            
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = sum(a * a for a in vec1) ** 0.5
            magnitude2 = sum(b * b for b in vec2) ** 0.5
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
            
        except Exception:
            return 0.0
    
    async def delete_embeddings_by_document(self, engagement_id: str, doc_id: str) -> int:
        """
        Delete all embeddings for a specific document.
        
        Args:
            engagement_id: Engagement ID for partition filtering
            doc_id: Document ID to delete embeddings for
            
        Returns:
            Number of embeddings deleted
        """
        try:
            logger.info(
                "Starting embeddings deletion",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "doc_id": doc_id
                }
            )
            
            # Find all embeddings for the document
            query = {
                "query": "SELECT c.id FROM c WHERE c.engagement_id = @engagement_id AND c.doc_id = @doc_id",
                "parameters": [
                    {"name": "@engagement_id", "value": engagement_id},
                    {"name": "@doc_id", "value": doc_id}
                ]
            }
            
            items = await asyncio.to_thread(
                lambda: list(self.container.query_items(
                    query=query["query"],
                    parameters=query["parameters"],
                    partition_key=engagement_id
                ))
            )
            
            # Delete each embedding
            deleted_count = 0
            for item in items:
                try:
                    await asyncio.to_thread(
                        self.container.delete_item,
                        item=item["id"],
                        partition_key=engagement_id
                    )
                    deleted_count += 1
                except CosmosResourceNotFoundError:
                    # Already deleted, continue
                    pass
                except Exception as e:
                    logger.warning(
                        "Failed to delete embedding",
                        extra={
                            "correlation_id": self.correlation_id,
                            "embedding_id": item["id"],
                            "error": str(e)
                        }
                    )
            
            logger.info(
                "Embeddings deletion completed",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "doc_id": doc_id,
                    "deleted_count": deleted_count
                }
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error(
                "Failed to delete embeddings",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "doc_id": doc_id,
                    "error": str(e)
                }
            )
            raise
    
    async def delete_embeddings_by_engagement(self, engagement_id: str) -> int:
        """
        Delete all embeddings for an engagement.
        
        Args:
            engagement_id: Engagement ID to delete embeddings for
            
        Returns:
            Number of embeddings deleted
        """
        try:
            logger.info(
                "Starting engagement embeddings deletion",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id
                }
            )
            
            # Find all embeddings for the engagement
            query = {
                "query": "SELECT c.id FROM c WHERE c.engagement_id = @engagement_id",
                "parameters": [
                    {"name": "@engagement_id", "value": engagement_id}
                ]
            }
            
            items = await asyncio.to_thread(
                lambda: list(self.container.query_items(
                    query=query["query"],
                    parameters=query["parameters"],
                    partition_key=engagement_id
                ))
            )
            
            # Delete in batches
            deleted_count = 0
            batch_size = 25
            
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                
                for item in batch:
                    try:
                        await asyncio.to_thread(
                            self.container.delete_item,
                            item=item["id"],
                            partition_key=engagement_id
                        )
                        deleted_count += 1
                    except CosmosResourceNotFoundError:
                        # Already deleted, continue
                        pass
                    except Exception as e:
                        logger.warning(
                            "Failed to delete embedding",
                            extra={
                                "correlation_id": self.correlation_id,
                                "embedding_id": item["id"],
                                "error": str(e)
                            }
                        )
                
                # Add delay between batches
                if i + batch_size < len(items):
                    await asyncio.sleep(0.1)
            
            logger.info(
                "Engagement embeddings deletion completed",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "deleted_count": deleted_count
                }
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error(
                "Failed to delete engagement embeddings",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "error": str(e)
                }
            )
            raise
    
    async def get_embeddings_stats(self, engagement_id: str) -> Dict[str, Any]:
        """
        Get statistics about embeddings for an engagement.
        
        Args:
            engagement_id: Engagement ID to get stats for
            
        Returns:
            Dictionary with embedding statistics
        """
        try:
            query = {
                "query": """
                    SELECT 
                        COUNT(1) as total_embeddings,
                        COUNT(DISTINCT c.doc_id) as unique_documents,
                        AVG(c.token_count) as avg_tokens_per_chunk
                    FROM c 
                    WHERE c.engagement_id = @engagement_id
                """,
                "parameters": [
                    {"name": "@engagement_id", "value": engagement_id}
                ]
            }
            
            result = await asyncio.to_thread(
                lambda: list(self.container.query_items(
                    query=query["query"],
                    parameters=query["parameters"],
                    partition_key=engagement_id
                ))
            )
            
            stats = result[0] if result else {
                "total_embeddings": 0,
                "unique_documents": 0,
                "avg_tokens_per_chunk": 0
            }
            
            return stats
            
        except Exception as e:
            logger.error(
                "Failed to get embeddings stats",
                extra={
                    "correlation_id": self.correlation_id,
                    "engagement_id": engagement_id,
                    "error": str(e)
                }
            )
            return {
                "total_embeddings": 0,
                "unique_documents": 0,
                "avg_tokens_per_chunk": 0,
                "error": str(e)
            }


def create_cosmos_embeddings_repository(correlation_id: Optional[str] = None) -> CosmosEmbeddingsRepository:
    """Factory function to create a Cosmos embeddings repository instance"""
    return CosmosEmbeddingsRepository(correlation_id=correlation_id)