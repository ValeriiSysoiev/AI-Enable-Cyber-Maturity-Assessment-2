"""
Configuration settings for the AI-Enabled Cyber Maturity Assessment application.
Includes Azure AI Search, OpenAI, and RAG service configurations.
"""
import os
from typing import Optional
from pydantic import BaseModel, Field


class AzureOpenAIConfig(BaseModel):
    """Azure OpenAI service configuration"""
    endpoint: str = Field(default_factory=lambda: os.getenv("AZURE_OPENAI_ENDPOINT", ""))
    api_key: Optional[str] = Field(default_factory=lambda: os.getenv("AZURE_OPENAI_API_KEY"))
    api_version: str = Field(default_factory=lambda: os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"))
    embedding_deployment: str = Field(default_factory=lambda: os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large"))
    embedding_model: str = Field(default_factory=lambda: os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"))
    max_tokens_per_request: int = Field(default_factory=lambda: int(os.getenv("AZURE_OPENAI_MAX_TOKENS", "8000")))


class AzureSearchConfig(BaseModel):
    """Azure AI Search service configuration"""
    endpoint: str = Field(default_factory=lambda: os.getenv("AZURE_SEARCH_ENDPOINT", ""))
    api_key: Optional[str] = Field(default_factory=lambda: os.getenv("AZURE_SEARCH_API_KEY"))
    index_name: str = Field(default_factory=lambda: os.getenv("AZURE_SEARCH_INDEX_NAME", "eng-docs"))
    api_version: str = Field(default_factory=lambda: os.getenv("AZURE_SEARCH_API_VERSION", "2024-07-01"))


class EmbeddingsConfig(BaseModel):
    """Text chunking and embedding configuration"""
    chunk_size: int = Field(default_factory=lambda: int(os.getenv("EMBEDDING_CHUNK_SIZE", "800")))
    chunk_overlap: int = Field(default_factory=lambda: int(os.getenv("EMBEDDING_CHUNK_OVERLAP", "200")))
    batch_size: int = Field(default_factory=lambda: int(os.getenv("EMBEDDING_BATCH_SIZE", "16")))
    max_retries: int = Field(default_factory=lambda: int(os.getenv("EMBEDDING_MAX_RETRIES", "3")))
    retry_delay: float = Field(default_factory=lambda: float(os.getenv("EMBEDDING_RETRY_DELAY", "1.0")))


class RAGConfig(BaseModel):
    """RAG service configuration"""
    mode: str = Field(default_factory=lambda: os.getenv("RAG_MODE", "none"))  # azure_openai|none
    enabled: bool = Field(default_factory=lambda: os.getenv("RAG_MODE", "none") == "azure_openai")
    search_top_k: int = Field(default_factory=lambda: int(os.getenv("RAG_SEARCH_TOP_K", "10")))
    similarity_threshold: float = Field(default_factory=lambda: float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.7")))
    use_hybrid_search: bool = Field(default_factory=lambda: os.getenv("RAG_USE_HYBRID_SEARCH", "true").lower() == "true")
    rerank_enabled: bool = Field(default_factory=lambda: os.getenv("RAG_RERANK_ENABLED", "false").lower() == "true")
    max_document_length: int = Field(default_factory=lambda: int(os.getenv("RAG_MAX_DOCUMENT_LENGTH", "100000")))
    
    # Feature flag support for gradual rollout
    feature_flag_enabled: bool = Field(default_factory=lambda: os.getenv("RAG_FEATURE_FLAG", "true").lower() == "true")
    
    # Cosmos DB configuration for vector storage
    cosmos_container_name: str = Field(default_factory=lambda: os.getenv("RAG_COSMOS_CONTAINER", "embeddings"))
    
    # Embedding configuration
    chunk_size_tokens: int = Field(default_factory=lambda: int(os.getenv("RAG_CHUNK_SIZE", "1500")))  # ~1-2k tokens
    chunk_overlap_percent: float = Field(default_factory=lambda: float(os.getenv("RAG_CHUNK_OVERLAP", "0.1")))  # 10% overlap
    batch_processing_size: int = Field(default_factory=lambda: int(os.getenv("RAG_BATCH_SIZE", "10")))
    rate_limit_requests_per_minute: int = Field(default_factory=lambda: int(os.getenv("RAG_RATE_LIMIT", "100")))


class StorageConfig(BaseModel):
    """Storage configuration for documents"""
    upload_root: str = Field(default_factory=lambda: os.getenv("UPLOAD_ROOT", "data/engagements"))
    max_upload_mb: int = Field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_MB", "10")))
    
    # Azure Blob Storage (optional)
    use_blob_storage: bool = Field(default_factory=lambda: os.getenv("USE_BLOB_STORAGE", "false").lower() == "true")
    azure_storage_account: Optional[str] = Field(default_factory=lambda: os.getenv("AZURE_STORAGE_ACCOUNT"))
    azure_storage_container: str = Field(default_factory=lambda: os.getenv("AZURE_STORAGE_CONTAINER", "documents"))


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    format: str = Field(default_factory=lambda: os.getenv("LOG_FORMAT", "json"))
    correlation_id_header: str = Field(default_factory=lambda: os.getenv("CORRELATION_ID_HEADER", "X-Correlation-ID"))


class AppConfig(BaseModel):
    """Main application configuration"""
    azure_openai: AzureOpenAIConfig = Field(default_factory=AzureOpenAIConfig)
    azure_search: AzureSearchConfig = Field(default_factory=AzureSearchConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Admin settings
    admin_emails: list[str] = Field(default_factory=lambda: [
        e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()
    ])
    
    # CORS settings
    allowed_origins: list[str] = Field(default_factory=lambda: [
        o.strip() for o in os.getenv("API_ALLOWED_ORIGINS", "").split(",") if o.strip()
    ] or ["*"])

    def is_rag_enabled(self) -> bool:
        """Check if RAG is properly configured and enabled"""
        return (
            self.rag.enabled 
            and self.rag.feature_flag_enabled
            and self.rag.mode == "azure_openai"
            and bool(self.azure_openai.endpoint)
        )

    def validate_azure_config(self) -> tuple[bool, list[str]]:
        """Validate Azure service configurations"""
        errors = []
        
        if self.rag.enabled and self.rag.mode == "azure_openai":
            if not self.azure_openai.endpoint:
                errors.append("AZURE_OPENAI_ENDPOINT is required when RAG mode is azure_openai")
            if not self.azure_openai.embedding_deployment:
                errors.append("AZURE_OPENAI_EMBEDDING_DEPLOYMENT is required when RAG mode is azure_openai")
                
        return len(errors) == 0, errors
    
    def get_rag_status(self) -> dict:
        """Get RAG configuration status for monitoring and debugging"""
        return {
            "mode": self.rag.mode,
            "enabled": self.rag.enabled,
            "feature_flag_enabled": self.rag.feature_flag_enabled,
            "azure_openai_configured": bool(self.azure_openai.endpoint),
            "embedding_model": self.azure_openai.embedding_model,
            "chunk_size": self.rag.chunk_size_tokens,
            "similarity_threshold": self.rag.similarity_threshold,
            "is_operational": self.is_rag_enabled()
        }


# Global configuration instance
config = AppConfig()