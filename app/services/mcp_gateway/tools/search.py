"""
MCP Search tools implementation.
Provides text embedding and vector search using sentence-transformers.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field
from util.logging import get_correlated_logger, log_operation

# Conditional imports for heavy ML dependencies
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    HAS_ML_DEPENDENCIES = True
except ImportError:
    # Mock classes for CI environment without heavy ML dependencies
    np = None
    SentenceTransformer = None
    HAS_ML_DEPENDENCIES = False

# Check if ML features are disabled via environment variables
ML_DISABLED = os.getenv('DISABLE_ML', '0') == '1' or os.getenv('CI_MODE', '0') == '1'

from ..config import MCPConfig, MCPOperationContext
from ..security import MCPSecurityValidator, redact_sensitive_content


class SearchEmbedRequest(BaseModel):
    """Request model for search.embed operation"""
    texts: List[str] = Field(..., description="List of texts to embed", max_items=100)
    model: str = Field(default="all-MiniLM-L6-v2", description="Embedding model to use")
    normalize: bool = Field(default=True, description="Normalize embeddings to unit vectors")


class SearchQueryRequest(BaseModel):
    """Request model for search.query operation"""
    query: str = Field(..., description="Search query text")
    embedding_file: str = Field(..., description="Path to embedding file to search")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of top results to return")
    similarity_threshold: float = Field(default=0.0, ge=-1.0, le=1.0, description="Minimum similarity score")
    model: str = Field(default="all-MiniLM-L6-v2", description="Embedding model to use for query")


class EmbeddingResult(BaseModel):
    """Single embedding result"""
    text: str
    embedding: List[float]
    index: int


class SearchResult(BaseModel):
    """Single search result"""
    text: str
    similarity: float
    index: int
    rank: int


class SearchEmbedResponse(BaseModel):
    """Response model for embedding operations"""
    success: bool
    message: str
    model: str
    embeddings_count: int
    embedding_file: Optional[str] = None
    results: Optional[List[EmbeddingResult]] = None


class SearchQueryResponse(BaseModel):
    """Response model for query operations"""
    success: bool
    message: str
    query: str
    model: str
    results_count: int
    results: Optional[List[SearchResult]] = None


class MCPSearchTool:
    """Vector search tool for MCP Gateway using sentence-transformers"""
    
    def __init__(self, config: MCPConfig):
        self.config = config
        self.tool_config = config.search
        self._models = {}  # Cache for loaded models
        
        # Check if ML features are available and enabled
        if ML_DISABLED or not HAS_ML_DEPENDENCIES:
            self._ml_available = False
        else:
            self._ml_available = True
    
    def _check_ml_available(self):
        """Check if ML features are available and raise appropriate error if not"""
        if not self._ml_available:
            if ML_DISABLED:
                raise ValueError("ML features are disabled via environment variables (DISABLE_ML=1 or CI_MODE=1)")
            else:
                raise ValueError("ML dependencies not available. Install sentence-transformers and numpy for vector search features.")
    
    def _get_model(self, model_name: str) -> SentenceTransformer:
        """Get or load sentence transformer model"""
        self._check_ml_available()
        
        if model_name not in self._models:
            try:
                self._models[model_name] = SentenceTransformer(model_name)
            except Exception as e:
                raise ValueError(f"Failed to load model '{model_name}': {e}")
        return self._models[model_name]
    
    async def embed_texts(self, request: SearchEmbedRequest, context: MCPOperationContext) -> SearchEmbedResponse:
        """
        Generate embeddings for a list of texts.
        
        Args:
            request: Embedding parameters
            context: Operation context with security info
            
        Returns:
            Text embeddings and metadata
        """
        logger = get_correlated_logger(f"mcp.search.embed", context.correlation_id)
        logger.set_context(
            engagement_id=context.engagement_id,
            user_email=context.user_email
        )
        
        # Create security validator
        validator = MCPSecurityValidator(self.config, context)
        
        with log_operation(
            logger, 
            "search_embed_operation", 
            texts_count=len(request.texts),
            model=request.model
        ):
            validator.log_operation_start(
                operation="embed", 
                texts_count=len(request.texts),
                model=request.model
            )
            
            try:
                # Check if ML features are available
                self._check_ml_available()
                
                # Validate input texts
                if not request.texts:
                    raise ValueError("No texts provided for embedding")
                
                if len(request.texts) > 100:
                    raise ValueError(f"Too many texts: {len(request.texts)} (max 100)")
                
                # Load model
                model = self._get_model(request.model)
                
                # Generate embeddings
                embeddings = model.encode(
                    request.texts,
                    normalize_embeddings=request.normalize,
                    show_progress_bar=False
                )
                
                # Convert to list format
                embedding_results = []
                for i, (text, embedding) in enumerate(zip(request.texts, embeddings)):
                    embedding_results.append(EmbeddingResult(
                        text=redact_sensitive_content(text, max_length=500),  # Redact for storage
                        embedding=embedding.tolist(),
                        index=i
                    ))
                
                # Generate unique filename for embeddings
                embedding_filename = f"embeddings_{context.correlation_id[:8]}_{len(request.texts)}.json"
                sandbox = self.config.get_engagement_sandbox(context.engagement_id)
                embedding_file = sandbox / "search" / embedding_filename
                embedding_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Save embeddings to file
                embedding_data = {
                    "model": request.model,
                    "normalized": request.normalize,
                    "texts": [result.text for result in embedding_results],
                    "embeddings": [result.embedding for result in embedding_results],
                    "metadata": {
                        "created_by": context.user_email,
                        "engagement_id": context.engagement_id,
                        "correlation_id": context.correlation_id,
                        "texts_count": len(request.texts)
                    }
                }
                
                embedding_file.write_text(json.dumps(embedding_data, indent=2))
                
                logger.info(
                    "Text embedding successful",
                    texts_count=len(request.texts),
                    model=request.model,
                    normalized=request.normalize,
                    embedding_file=str(embedding_file.relative_to(sandbox)),
                    avg_text_length=sum(len(t) for t in request.texts) / len(request.texts)
                )
                
                validator.log_operation_complete(
                    success=True,
                    operation="embed",
                    texts_count=len(request.texts),
                    embedding_file=str(embedding_file.relative_to(sandbox))
                )
                
                return SearchEmbedResponse(
                    success=True,
                    message=f"Generated embeddings for {len(request.texts)} texts",
                    model=request.model,
                    embeddings_count=len(embedding_results),
                    embedding_file=str(embedding_file.relative_to(sandbox)),
                    results=embedding_results
                )
                
            except Exception as e:
                error_msg = f"Failed to generate embeddings: {str(e)}"
                logger.error(error_msg, error_type=type(e).__name__)
                validator.log_operation_complete(success=False, error=error_msg)
                
                return SearchEmbedResponse(
                    success=False,
                    message=error_msg,
                    model=request.model,
                    embeddings_count=0
                )
    
    async def query_embeddings(self, request: SearchQueryRequest, context: MCPOperationContext) -> SearchQueryResponse:
        """
        Query embedded texts using vector similarity search.
        
        Args:
            request: Query parameters
            context: Operation context with security info
            
        Returns:
            Ranked search results
        """
        logger = get_correlated_logger(f"mcp.search.query", context.correlation_id)
        logger.set_context(
            engagement_id=context.engagement_id,
            user_email=context.user_email
        )
        
        # Create security validator
        validator = MCPSecurityValidator(self.config, context)
        
        with log_operation(
            logger, 
            "search_query_operation", 
            query_preview=redact_sensitive_content(request.query, max_length=200),
            embedding_file=request.embedding_file
        ):
            validator.log_operation_start(
                operation="query", 
                embedding_file=request.embedding_file,
                top_k=request.top_k,
                model=request.model
            )
            
            try:
                # Check if ML features are available
                self._check_ml_available()
                
                # Validate query
                if not request.query.strip():
                    raise ValueError("Query cannot be empty")
                
                # Validate and load embedding file
                sandbox = self.config.get_engagement_sandbox(context.engagement_id)
                embedding_path = sandbox / request.embedding_file
                
                if not embedding_path.exists():
                    raise FileNotFoundError(f"Embedding file not found: {request.embedding_file}")
                
                # Load embeddings
                try:
                    embedding_data = json.loads(embedding_path.read_text())
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid embedding file format: {e}")
                
                # Validate embedding data structure
                required_fields = ["model", "texts", "embeddings"]
                for field in required_fields:
                    if field not in embedding_data:
                        raise ValueError(f"Missing field in embedding file: {field}")
                
                stored_texts = embedding_data["texts"]
                stored_embeddings = np.array(embedding_data["embeddings"])
                stored_model = embedding_data["model"]
                
                # Load model (ensure consistency)
                model = self._get_model(request.model)
                
                # Generate query embedding
                query_embedding = model.encode(
                    [request.query],
                    normalize_embeddings=embedding_data.get("normalized", True),
                    show_progress_bar=False
                )[0]
                
                # Compute similarities
                similarities = np.dot(stored_embeddings, query_embedding)
                
                # Get top results
                top_indices = np.argsort(similarities)[::-1]
                
                results = []
                for rank, idx in enumerate(top_indices[:request.top_k]):
                    similarity = float(similarities[idx])
                    
                    # Apply similarity threshold
                    if similarity < request.similarity_threshold:
                        break
                    
                    results.append(SearchResult(
                        text=stored_texts[idx],
                        similarity=similarity,
                        index=int(idx),
                        rank=rank + 1
                    ))
                
                logger.info(
                    "Search query successful",
                    query_length=len(request.query),
                    embedding_file=str(embedding_path.relative_to(sandbox)),
                    model_used=request.model,
                    stored_model=stored_model,
                    stored_texts_count=len(stored_texts),
                    results_found=len(results),
                    top_k=request.top_k,
                    similarity_threshold=request.similarity_threshold,
                    top_similarity=results[0].similarity if results else 0.0
                )
                
                validator.log_operation_complete(
                    success=True,
                    operation="query",
                    results_found=len(results),
                    top_similarity=results[0].similarity if results else 0.0
                )
                
                return SearchQueryResponse(
                    success=True,
                    message=f"Found {len(results)} results for query",
                    query=redact_sensitive_content(request.query, max_length=200),
                    model=request.model,
                    results_count=len(results),
                    results=results
                )
                
            except Exception as e:
                error_msg = f"Failed to execute search query: {str(e)}"
                logger.error(error_msg, error_type=type(e).__name__)
                validator.log_operation_complete(success=False, error=error_msg)
                
                return SearchQueryResponse(
                    success=False,
                    message=error_msg,
                    query=redact_sensitive_content(request.query, max_length=200),
                    model=request.model,
                    results_count=0
                )