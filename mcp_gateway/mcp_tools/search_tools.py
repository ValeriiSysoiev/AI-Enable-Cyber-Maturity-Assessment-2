"""
Search tools for MCP Gateway

Provides embedding and vector search capabilities with per-engagement vector stores.
"""

import logging
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime

from . import McpTool, McpCallResult, McpError, McpToolRegistry
from vector_store import VectorStoreManager

logger = logging.getLogger(__name__)

class SearchEmbedTool(McpTool):
    """Tool for embedding text and storing in engagement vector store"""
    
    def __init__(self, vector_store_manager: VectorStoreManager):
        super().__init__(
            name="search.embed",
            description="Embed text and store in engagement vector store",
            schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to embed and store"
                    },
                    "id": {
                        "type": "string",
                        "description": "Unique identifier for this text (optional, will be auto-generated if not provided)"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata to store with the embedding",
                        "default": {}
                    },
                    "chunk_strategy": {
                        "type": "string",
                        "description": "Strategy for chunking long text",
                        "enum": ["none", "sentence", "paragraph"],
                        "default": "none"
                    },
                    "max_chunk_size": {
                        "type": "integer",
                        "description": "Maximum size for text chunks in characters",
                        "default": 1000,
                        "minimum": 100,
                        "maximum": 5000
                    }
                },
                "required": ["text"]
            }
        )
        self.vector_store_manager = vector_store_manager
    
    async def execute(self, payload: Dict[str, Any], engagement_id: str) -> McpCallResult:
        """Execute text embedding operation"""
        try:
            self.validate_payload(payload, ["text"])
            
            text = payload["text"]
            text_id = payload.get("id")
            metadata = payload.get("metadata", {})
            chunk_strategy = payload.get("chunk_strategy", "none")
            max_chunk_size = payload.get("max_chunk_size", 1000)
            
            # Validate text length
            if len(text) > 50000:  # 50KB limit
                raise McpError("Text too long (max 50KB)", "TEXT_TOO_LONG")
            
            if not text.strip():
                raise McpError("Empty text cannot be embedded", "EMPTY_TEXT")
            
            # Get vector store for engagement
            store = self.vector_store_manager.get_store(engagement_id)
            
            # Generate ID if not provided
            if not text_id:
                text_hash = hashlib.md5(text.encode()).hexdigest()
                text_id = f"text_{text_hash[:12]}"
            
            # Add engagement metadata
            metadata.update({
                "engagement_id": engagement_id,
                "created_at": datetime.utcnow().isoformat(),
                "text_length": len(text)
            })
            
            # Handle chunking if requested
            if chunk_strategy != "none" and len(text) > max_chunk_size:
                chunks = self._chunk_text(text, chunk_strategy, max_chunk_size)
                embedded_ids = []
                
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{text_id}_chunk_{i}"
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "parent_id": text_id
                    })
                    
                    # Generate embedding
                    embedding = self.vector_store_manager.generate_embedding(chunk)
                    
                    # Store in vector store
                    store.add_vector(chunk_id, chunk, embedding, chunk_metadata)
                    embedded_ids.append(chunk_id)
                
                self.logger.info(
                    f"Text embedded as {len(chunks)} chunks: {text_id}",
                    extra={"engagement_id": engagement_id, "chunks": len(chunks)}
                )
                
                return McpCallResult(
                    success=True,
                    result={
                        "id": text_id,
                        "chunks": embedded_ids,
                        "total_chunks": len(chunks),
                        "strategy": chunk_strategy,
                        "text_length": len(text)
                    }
                )
            else:
                # Embed as single text
                embedding = self.vector_store_manager.generate_embedding(text)
                
                # Store in vector store
                store.add_vector(text_id, text, embedding, metadata)
                
                self.logger.info(
                    f"Text embedded: {text_id}",
                    extra={"engagement_id": engagement_id, "text_length": len(text)}
                )
                
                return McpCallResult(
                    success=True,
                    result={
                        "id": text_id,
                        "text_length": len(text),
                        "embedding_dimension": len(embedding)
                    }
                )
                
        except McpError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in search.embed: {e}", exc_info=True)
            raise McpError(f"Internal error: {e}", "INTERNAL_ERROR")
    
    def _chunk_text(self, text: str, strategy: str, max_size: int) -> List[str]:
        """Chunk text based on strategy"""
        if strategy == "sentence":
            return self._chunk_by_sentences(text, max_size)
        elif strategy == "paragraph":
            return self._chunk_by_paragraphs(text, max_size)
        else:
            # Fallback to simple character chunking
            return [text[i:i+max_size] for i in range(0, len(text), max_size)]
    
    def _chunk_by_sentences(self, text: str, max_size: int) -> List[str]:
        """Chunk text by sentences"""
        import re
        
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(current_chunk) + len(sentence) + 1 <= max_size:
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk + ".")
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk + ".")
        
        return chunks
    
    def _chunk_by_paragraphs(self, text: str, max_size: int) -> List[str]:
        """Chunk text by paragraphs"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            if len(current_chunk) + len(paragraph) + 2 <= max_size:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = paragraph
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

class SearchQueryTool(McpTool):
    """Tool for querying the engagement vector store"""
    
    def __init__(self, vector_store_manager: VectorStoreManager):
        super().__init__(
            name="search.query",
            description="Search engagement vector store using text query",
            schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top results to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "score_threshold": {
                        "type": "number",
                        "description": "Minimum similarity score for results",
                        "default": 0.0,
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "metadata_filter": {
                        "type": "object",
                        "description": "Filter results by metadata fields",
                        "default": {}
                    }
                },
                "required": ["query"]
            }
        )
        self.vector_store_manager = vector_store_manager
    
    async def execute(self, payload: Dict[str, Any], engagement_id: str) -> McpCallResult:
        """Execute vector search operation"""
        try:
            self.validate_payload(payload, ["query"])
            
            query = payload["query"]
            top_k = payload.get("top_k", 10)
            score_threshold = payload.get("score_threshold", 0.0)
            metadata_filter = payload.get("metadata_filter", {})
            
            # Validate query
            if not query.strip():
                raise McpError("Empty query", "EMPTY_QUERY")
            
            if len(query) > 1000:
                raise McpError("Query too long (max 1000 characters)", "QUERY_TOO_LONG")
            
            # Get vector store for engagement
            store = self.vector_store_manager.get_store(engagement_id)
            
            # Generate query embedding
            query_embedding = self.vector_store_manager.generate_embedding(query)
            
            # Perform search
            search_results = store.search(query_embedding, top_k * 2)  # Get more to allow filtering
            
            # Apply score threshold
            filtered_results = [r for r in search_results if r.score >= score_threshold]
            
            # Apply metadata filter
            if metadata_filter:
                filtered_results = [
                    r for r in filtered_results 
                    if self._matches_metadata_filter(r.metadata, metadata_filter)
                ]
            
            # Limit to top_k
            final_results = filtered_results[:top_k]
            
            # Format results
            results = []
            for result in final_results:
                results.append({
                    "id": result.id,
                    "text": result.text,
                    "score": result.score,
                    "metadata": result.metadata
                })
            
            self.logger.info(
                f"Search completed: {len(results)} results for query",
                extra={
                    "engagement_id": engagement_id,
                    "query_length": len(query),
                    "results_count": len(results)
                }
            )
            
            return McpCallResult(
                success=True,
                result={
                    "query": query,
                    "results": results,
                    "total_results": len(results),
                    "total_store_size": store.count_vectors()
                }
            )
            
        except McpError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in search.query: {e}", exc_info=True)
            raise McpError(f"Internal error: {e}", "INTERNAL_ERROR")
    
    def _matches_metadata_filter(self, metadata: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        """Check if metadata matches filter criteria"""
        for key, value in filter_dict.items():
            if key not in metadata:
                return False
            if metadata[key] != value:
                return False
        return True

class SearchListTool(McpTool):
    """Tool for listing vectors in the engagement store"""
    
    def __init__(self, vector_store_manager: VectorStoreManager):
        super().__init__(
            name="search.list",
            description="List vectors in engagement vector store",
            schema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of vectors to return",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of vectors to skip",
                        "default": 0,
                        "minimum": 0
                    },
                    "include_embeddings": {
                        "type": "boolean",
                        "description": "Include embedding vectors in response",
                        "default": False
                    }
                },
                "required": []
            }
        )
        self.vector_store_manager = vector_store_manager
    
    async def execute(self, payload: Dict[str, Any], engagement_id: str) -> McpCallResult:
        """Execute vector listing operation"""
        try:
            limit = payload.get("limit", 20)
            offset = payload.get("offset", 0)
            include_embeddings = payload.get("include_embeddings", False)
            
            # Get vector store for engagement
            store = self.vector_store_manager.get_store(engagement_id)
            
            # List vectors
            vectors = store.list_vectors(limit, offset)
            total_count = store.count_vectors()
            
            # Format results
            results = []
            for vector in vectors:
                result = {
                    "id": vector.id,
                    "text": vector.text[:200] + "..." if len(vector.text) > 200 else vector.text,
                    "text_length": len(vector.text),
                    "metadata": vector.metadata,
                    "created_at": vector.created_at
                }
                
                if include_embeddings:
                    result["embedding"] = vector.embedding
                
                results.append(result)
            
            self.logger.info(
                f"Listed {len(results)} vectors",
                extra={"engagement_id": engagement_id, "total_count": total_count}
            )
            
            return McpCallResult(
                success=True,
                result={
                    "vectors": results,
                    "total_count": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(results) < total_count
                }
            )
            
        except Exception as e:
            self.logger.error(f"Unexpected error in search.list: {e}", exc_info=True)
            raise McpError(f"Internal error: {e}", "INTERNAL_ERROR")

def register_search_tools(registry: McpToolRegistry, vector_store_manager: VectorStoreManager):
    """Register search tools with the registry"""
    registry.register(SearchEmbedTool(vector_store_manager))
    registry.register(SearchQueryTool(vector_store_manager))
    registry.register(SearchListTool(vector_store_manager))
    
    logger.info("Search tools registered")