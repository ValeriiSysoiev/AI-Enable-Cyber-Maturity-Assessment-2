"""
Embeddings service for generating vector embeddings using Azure OpenAI.
Handles text chunking, batch processing, and error handling with retries.
"""
import asyncio
import logging
import re
import time
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from openai import AsyncAzureOpenAI
from azure.identity import DefaultAzureCredential
from config import config


logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata"""
    text: str
    start_index: int
    end_index: int
    chunk_index: int
    token_count: Optional[int] = None


@dataclass
class EmbeddingResult:
    """Result of embedding generation"""
    chunk: TextChunk
    embedding: List[float]
    model: str
    usage_tokens: int


class EmbeddingsService:
    """Service for generating embeddings using Azure OpenAI"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or "unknown"
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Azure OpenAI client with proper authentication"""
        try:
            # Use API key if provided, otherwise use managed identity
            if config.azure_openai.api_key:
                self.client = AsyncAzureOpenAI(
                    api_key=config.azure_openai.api_key,
                    api_version=config.azure_openai.api_version,
                    azure_endpoint=config.azure_openai.endpoint
                )
            else:
                # Use managed identity for authentication
                credential = DefaultAzureCredential()
                self.client = AsyncAzureOpenAI(
                    azure_ad_token_provider=credential,
                    api_version=config.azure_openai.api_version,
                    azure_endpoint=config.azure_openai.endpoint
                )
            
            logger.info(
                "Initialized Azure OpenAI client",
                extra={
                    "correlation_id": self.correlation_id,
                    "endpoint": config.azure_openai.endpoint,
                    "model": config.azure_openai.embedding_model,
                    "deployment": config.azure_openai.embedding_deployment
                }
            )
        except Exception as e:
            logger.error(
                "Failed to initialize Azure OpenAI client",
                extra={
                    "correlation_id": self.correlation_id,
                    "error": str(e),
                    "endpoint": config.azure_openai.endpoint
                }
            )
            raise
    
    def chunk_text(self, text: str, document_id: str) -> List[TextChunk]:
        """
        Split text into chunks suitable for embedding generation.
        
        Args:
            text: The text to chunk
            document_id: Identifier for the document (for logging)
            
        Returns:
            List of TextChunk objects
        """
        try:
            # Clean and normalize text
            text = self._clean_text(text)
            
            if not text.strip():
                logger.warning(
                    "Empty text provided for chunking",
                    extra={
                        "correlation_id": self.correlation_id,
                        "document_id": document_id
                    }
                )
                return []
            
            # Split text into sentences for better chunk boundaries
            sentences = self._split_into_sentences(text)
            chunks = []
            current_chunk = ""
            current_start = 0
            chunk_index = 0
            
            for sentence in sentences:
                # Estimate token count (rough approximation: 1 token ≈ 4 characters)
                estimated_tokens = len(current_chunk + sentence) // 4
                
                if estimated_tokens > config.embeddings.chunk_size and current_chunk:
                    # Save current chunk
                    chunk_end = current_start + len(current_chunk)
                    chunks.append(TextChunk(
                        text=current_chunk.strip(),
                        start_index=current_start,
                        end_index=chunk_end,
                        chunk_index=chunk_index,
                        token_count=len(current_chunk) // 4
                    ))
                    
                    # Start new chunk with overlap
                    overlap_text = self._get_overlap_text(current_chunk, config.embeddings.chunk_overlap)
                    current_start = chunk_end - len(overlap_text)
                    current_chunk = overlap_text + sentence
                    chunk_index += 1
                else:
                    current_chunk += sentence
            
            # Add final chunk if not empty
            if current_chunk.strip():
                chunks.append(TextChunk(
                    text=current_chunk.strip(),
                    start_index=current_start,
                    end_index=current_start + len(current_chunk),
                    chunk_index=chunk_index,
                    token_count=len(current_chunk) // 4
                ))
            
            logger.info(
                "Text chunked successfully",
                extra={
                    "correlation_id": self.correlation_id,
                    "document_id": document_id,
                    "total_chunks": len(chunks),
                    "original_length": len(text),
                    "chunk_size": config.embeddings.chunk_size,
                    "overlap": config.embeddings.chunk_overlap
                }
            )
            
            return chunks
            
        except Exception as e:
            logger.error(
                "Failed to chunk text",
                extra={
                    "correlation_id": self.correlation_id,
                    "document_id": document_id,
                    "error": str(e),
                    "text_length": len(text) if text else 0
                }
            )
            raise
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for embedding"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove non-printable characters except common ones
        text = re.sub(r'[^\x20-\x7E\n\r\t]', '', text)
        return text.strip()
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using simple heuristics"""
        # Simple sentence splitting on periods, exclamation marks, question marks
        sentences = re.split(r'[.!?]+', text)
        # Add back punctuation and handle edge cases
        result = []
        for i, sentence in enumerate(sentences):
            if sentence.strip():
                # Add period back except for last sentence
                if i < len(sentences) - 1:
                    result.append(sentence.strip() + '. ')
                else:
                    result.append(sentence.strip())
        return result
    
    def _get_overlap_text(self, text: str, overlap_chars: int) -> str:
        """Get the last N characters for chunk overlap"""
        if len(text) <= overlap_chars:
            return text
        
        # Try to break at word boundary
        overlap_text = text[-overlap_chars:]
        space_index = overlap_text.find(' ')
        if space_index > 0:
            return overlap_text[space_index + 1:]
        return overlap_text
    
    async def generate_embeddings(
        self, 
        chunks: List[TextChunk], 
        document_id: str
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for a list of text chunks.
        
        Args:
            chunks: List of TextChunk objects
            document_id: Identifier for the document (for logging)
            
        Returns:
            List of EmbeddingResult objects
        """
        if not chunks:
            logger.warning(
                "No chunks provided for embedding generation",
                extra={
                    "correlation_id": self.correlation_id,
                    "document_id": document_id
                }
            )
            return []
        
        try:
            # Process chunks in batches
            results = []
            total_batches = (len(chunks) + config.embeddings.batch_size - 1) // config.embeddings.batch_size
            
            for batch_idx in range(0, len(chunks), config.embeddings.batch_size):
                batch_chunks = chunks[batch_idx:batch_idx + config.embeddings.batch_size]
                batch_num = (batch_idx // config.embeddings.batch_size) + 1
                
                logger.info(
                    "Processing embedding batch",
                    extra={
                        "correlation_id": self.correlation_id,
                        "document_id": document_id,
                        "batch": f"{batch_num}/{total_batches}",
                        "chunks_in_batch": len(batch_chunks)
                    }
                )
                
                batch_results = await self._generate_batch_embeddings(batch_chunks, document_id)
                results.extend(batch_results)
                
                # Add small delay between batches to avoid rate limiting
                if batch_idx + config.embeddings.batch_size < len(chunks):
                    await asyncio.sleep(0.1)
            
            logger.info(
                "Embeddings generated successfully",
                extra={
                    "correlation_id": self.correlation_id,
                    "document_id": document_id,
                    "total_chunks": len(chunks),
                    "total_embeddings": len(results),
                    "total_batches": total_batches
                }
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Failed to generate embeddings",
                extra={
                    "correlation_id": self.correlation_id,
                    "document_id": document_id,
                    "error": str(e),
                    "total_chunks": len(chunks)
                }
            )
            raise
    
    async def _generate_batch_embeddings(
        self, 
        chunks: List[TextChunk], 
        document_id: str
    ) -> List[EmbeddingResult]:
        """Generate embeddings for a batch of chunks with retry logic"""
        texts = [chunk.text for chunk in chunks]
        
        for attempt in range(config.embeddings.max_retries + 1):
            try:
                start_time = time.time()
                
                response = await self.client.embeddings.create(
                    model=config.azure_openai.embedding_deployment,
                    input=texts,
                    dimensions=None  # Use default dimensions for text-embedding-3-large
                )
                
                duration = time.time() - start_time
                
                # Process results
                results = []
                for i, embedding_data in enumerate(response.data):
                    results.append(EmbeddingResult(
                        chunk=chunks[i],
                        embedding=embedding_data.embedding,
                        model=response.model,
                        usage_tokens=response.usage.total_tokens // len(texts) if response.usage else 0
                    ))
                
                logger.info(
                    "Batch embeddings generated successfully",
                    extra={
                        "correlation_id": self.correlation_id,
                        "document_id": document_id,
                        "batch_size": len(chunks),
                        "attempt": attempt + 1,
                        "duration_seconds": round(duration, 2),
                        "total_tokens": response.usage.total_tokens if response.usage else 0,
                        "model": response.model
                    }
                )
                
                return results
                
            except Exception as e:
                if attempt < config.embeddings.max_retries:
                    delay = config.embeddings.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        "Embedding generation failed, retrying",
                        extra={
                            "correlation_id": self.correlation_id,
                            "document_id": document_id,
                            "attempt": attempt + 1,
                            "max_retries": config.embeddings.max_retries,
                            "error": str(e),
                            "retry_delay": delay
                        }
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "Embedding generation failed after all retries",
                        extra={
                            "correlation_id": self.correlation_id,
                            "document_id": document_id,
                            "attempts": attempt + 1,
                            "error": str(e)
                        }
                    )
                    raise
        
        # This should never be reached, but added for completeness
        raise RuntimeError("Unexpected error in embedding generation")
    
    async def embed_document(self, text: str, document_id: str) -> List[EmbeddingResult]:
        """
        Complete pipeline to chunk text and generate embeddings for a document.
        
        Args:
            text: The document text to embed
            document_id: Identifier for the document
            
        Returns:
            List of EmbeddingResult objects
        """
        try:
            # Validate input
            if not text or not text.strip():
                raise ValueError("Text cannot be empty")
            
            if len(text) > config.rag.max_document_length:
                logger.warning(
                    "Document exceeds maximum length, truncating",
                    extra={
                        "correlation_id": self.correlation_id,
                        "document_id": document_id,
                        "original_length": len(text),
                        "max_length": config.rag.max_document_length
                    }
                )
                text = text[:config.rag.max_document_length]
            
            # Chunk the text
            chunks = self.chunk_text(text, document_id)
            
            if not chunks:
                raise ValueError("No valid chunks generated from document text")
            
            # Generate embeddings
            embeddings = await self.generate_embeddings(chunks, document_id)
            
            return embeddings
            
        except Exception as e:
            logger.error(
                "Failed to embed document",
                extra={
                    "correlation_id": self.correlation_id,
                    "document_id": document_id,
                    "error": str(e),
                    "text_length": len(text) if text else 0
                }
            )
            raise


def create_embeddings_service(correlation_id: Optional[str] = None) -> EmbeddingsService:
    """Factory function to create an embeddings service instance"""
    return EmbeddingsService(correlation_id=correlation_id)