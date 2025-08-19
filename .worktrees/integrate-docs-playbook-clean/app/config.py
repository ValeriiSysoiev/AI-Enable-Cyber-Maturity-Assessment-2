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
    embedding_dimensions: int = Field(default_factory=lambda: int(os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", "3072")))
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
    search_backend: str = Field(default_factory=lambda: os.getenv("RAG_SEARCH_BACKEND", "azure_search"))  # azure_search|cosmos_db
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


class AADGroupsConfig(BaseModel):
    """Azure Active Directory groups configuration"""
    mode: str = Field(default_factory=lambda: os.getenv("AUTH_GROUPS_MODE", "disabled"))  # enabled|disabled
    enabled: bool = Field(default_factory=lambda: os.getenv("AUTH_GROUPS_MODE", "disabled") == "enabled")
    
    # Microsoft Graph API configuration
    tenant_id: Optional[str] = Field(default_factory=lambda: os.getenv("AAD_TENANT_ID"))
    client_id: Optional[str] = Field(default_factory=lambda: os.getenv("AAD_CLIENT_ID"))
    client_secret: Optional[str] = Field(default_factory=lambda: os.getenv("AAD_CLIENT_SECRET"))
    
    # Group to role mapping (JSON string)
    group_map_json: str = Field(default_factory=lambda: os.getenv("AAD_GROUP_MAP_JSON", "{}"))
    
    # Caching configuration
    cache_ttl_minutes: int = Field(default_factory=lambda: int(os.getenv("AAD_CACHE_TTL_MINUTES", "15")))
    
    # Security settings
    require_tenant_isolation: bool = Field(default_factory=lambda: os.getenv("AAD_REQUIRE_TENANT_ISOLATION", "true").lower() == "true")
    allowed_tenant_ids: list[str] = Field(default_factory=lambda: [
        t.strip() for t in os.getenv("AAD_ALLOWED_TENANT_IDS", "").split(",") if t.strip()
    ])


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    format: str = Field(default_factory=lambda: os.getenv("LOG_FORMAT", "json"))
    correlation_id_header: str = Field(default_factory=lambda: os.getenv("CORRELATION_ID_HEADER", "X-Correlation-ID"))


class CacheConfig(BaseModel):
    """Cache configuration for in-process caching"""
    # Presets cache (hot read optimization)
    presets_max_size_mb: int = Field(default_factory=lambda: int(os.getenv("CACHE_PRESETS_MAX_SIZE_MB", "100")))
    presets_ttl_seconds: int = Field(default_factory=lambda: int(os.getenv("CACHE_PRESETS_TTL_SECONDS", "3600")))  # 1 hour
    presets_max_entries: int = Field(default_factory=lambda: int(os.getenv("CACHE_PRESETS_MAX_ENTRIES", "100")))
    
    # Framework metadata cache
    framework_max_size_mb: int = Field(default_factory=lambda: int(os.getenv("CACHE_FRAMEWORK_MAX_SIZE_MB", "50")))
    framework_ttl_seconds: int = Field(default_factory=lambda: int(os.getenv("CACHE_FRAMEWORK_TTL_SECONDS", "1800")))  # 30 minutes
    framework_max_entries: int = Field(default_factory=lambda: int(os.getenv("CACHE_FRAMEWORK_MAX_ENTRIES", "50")))
    
    # User roles/groups cache (AAD integration)
    user_roles_max_size_mb: int = Field(default_factory=lambda: int(os.getenv("CACHE_USER_ROLES_MAX_SIZE_MB", "20")))
    user_roles_ttl_seconds: int = Field(default_factory=lambda: int(os.getenv("CACHE_USER_ROLES_TTL_SECONDS", "900")))  # 15 minutes
    user_roles_max_entries: int = Field(default_factory=lambda: int(os.getenv("CACHE_USER_ROLES_MAX_ENTRIES", "1000")))
    
    # Assessment schemas cache
    assessment_schemas_max_size_mb: int = Field(default_factory=lambda: int(os.getenv("CACHE_ASSESSMENT_SCHEMAS_MAX_SIZE_MB", "75")))
    assessment_schemas_ttl_seconds: int = Field(default_factory=lambda: int(os.getenv("CACHE_ASSESSMENT_SCHEMAS_TTL_SECONDS", "3600")))  # 1 hour
    assessment_schemas_max_entries: int = Field(default_factory=lambda: int(os.getenv("CACHE_ASSESSMENT_SCHEMAS_MAX_ENTRIES", "200")))
    
    # Document metadata cache
    document_metadata_max_size_mb: int = Field(default_factory=lambda: int(os.getenv("CACHE_DOCUMENT_METADATA_MAX_SIZE_MB", "30")))
    document_metadata_ttl_seconds: int = Field(default_factory=lambda: int(os.getenv("CACHE_DOCUMENT_METADATA_TTL_SECONDS", "600")))  # 10 minutes
    document_metadata_max_entries: int = Field(default_factory=lambda: int(os.getenv("CACHE_DOCUMENT_METADATA_MAX_ENTRIES", "500")))
    
    # General cache settings
    cleanup_interval_seconds: int = Field(default_factory=lambda: int(os.getenv("CACHE_CLEANUP_INTERVAL_SECONDS", "300")))  # 5 minutes
    enabled: bool = Field(default_factory=lambda: os.getenv("CACHE_ENABLED", "true").lower() == "true")


class PerformanceConfig(BaseModel):
    """Performance monitoring and optimization configuration"""
    # Request timing configuration
    slow_request_threshold_ms: int = Field(default_factory=lambda: int(os.getenv("PERF_SLOW_REQUEST_THRESHOLD_MS", "1000")))
    enable_request_timing: bool = Field(default_factory=lambda: os.getenv("PERF_ENABLE_REQUEST_TIMING", "true").lower() == "true")
    
    # Database query performance
    slow_query_threshold_ms: int = Field(default_factory=lambda: int(os.getenv("PERF_SLOW_QUERY_THRESHOLD_MS", "500")))
    enable_query_timing: bool = Field(default_factory=lambda: os.getenv("PERF_ENABLE_QUERY_TIMING", "true").lower() == "true")
    
    # Cache performance tracking
    enable_cache_metrics: bool = Field(default_factory=lambda: os.getenv("PERF_ENABLE_CACHE_METRICS", "true").lower() == "true")
    cache_metrics_interval_seconds: int = Field(default_factory=lambda: int(os.getenv("PERF_CACHE_METRICS_INTERVAL_SECONDS", "60")))
    
    # Response headers for debugging
    include_timing_headers: bool = Field(default_factory=lambda: os.getenv("PERF_INCLUDE_TIMING_HEADERS", "true").lower() == "true")
    include_cache_headers: bool = Field(default_factory=lambda: os.getenv("PERF_INCLUDE_CACHE_HEADERS", "false").lower() == "true")
    
    # Memory monitoring
    enable_memory_monitoring: bool = Field(default_factory=lambda: os.getenv("PERF_ENABLE_MEMORY_MONITORING", "false").lower() == "true")
    memory_check_interval_seconds: int = Field(default_factory=lambda: int(os.getenv("PERF_MEMORY_CHECK_INTERVAL_SECONDS", "300")))
    
    # Performance alerts
    enable_performance_alerts: bool = Field(default_factory=lambda: os.getenv("PERF_ENABLE_ALERTS", "false").lower() == "true")
    alert_slow_request_count_threshold: int = Field(default_factory=lambda: int(os.getenv("PERF_ALERT_SLOW_REQUEST_COUNT", "10")))
    alert_time_window_minutes: int = Field(default_factory=lambda: int(os.getenv("PERF_ALERT_TIME_WINDOW_MINUTES", "5")))


class ServiceBusConfig(BaseModel):
    """Azure Service Bus configuration for message queuing"""
    namespace: Optional[str] = Field(default_factory=lambda: os.getenv("SERVICE_BUS_NAMESPACE"))
    connection_string: Optional[str] = Field(default_factory=lambda: os.getenv("SERVICE_BUS_CONN_STRING"))
    
    # Queue configuration
    default_topic_name: str = Field(default_factory=lambda: os.getenv("SERVICE_BUS_DEFAULT_TOPIC", "orchestration"))
    max_retries: int = Field(default_factory=lambda: int(os.getenv("SERVICE_BUS_MAX_RETRIES", "3")))
    retry_delay_seconds: int = Field(default_factory=lambda: int(os.getenv("SERVICE_BUS_RETRY_DELAY", "5")))
    message_ttl_seconds: int = Field(default_factory=lambda: int(os.getenv("SERVICE_BUS_MESSAGE_TTL", "3600")))
    
    def is_configured(self) -> bool:
        """Check if Service Bus is properly configured"""
        return bool(self.namespace and self.connection_string)


class AppConfig(BaseModel):
    """Main application configuration"""
    azure_openai: AzureOpenAIConfig = Field(default_factory=AzureOpenAIConfig)
    azure_search: AzureSearchConfig = Field(default_factory=AzureSearchConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    aad_groups: AADGroupsConfig = Field(default_factory=AADGroupsConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    service_bus: ServiceBusConfig = Field(default_factory=ServiceBusConfig)
    
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

    def is_aad_groups_enabled(self) -> bool:
        """Check if AAD groups integration is properly configured and enabled"""
        return (
            self.aad_groups.enabled
            and self.aad_groups.mode == "enabled"
            and bool(self.aad_groups.tenant_id)
            and bool(self.aad_groups.client_id)
            and bool(self.aad_groups.client_secret)
        )

    def validate_aad_config(self) -> tuple[bool, list[str]]:
        """Validate AAD groups configuration"""
        errors = []
        
        if self.aad_groups.enabled:
            if not self.aad_groups.tenant_id:
                errors.append("AAD_TENANT_ID is required when AUTH_GROUPS_MODE is enabled")
            if not self.aad_groups.client_id:
                errors.append("AAD_CLIENT_ID is required when AUTH_GROUPS_MODE is enabled")
            if not self.aad_groups.client_secret:
                errors.append("AAD_CLIENT_SECRET is required when AUTH_GROUPS_MODE is enabled")
            
            # Validate group mapping JSON
            try:
                import json
                group_map = json.loads(self.aad_groups.group_map_json)
                if not isinstance(group_map, dict):
                    errors.append("AAD_GROUP_MAP_JSON must be a valid JSON object")
            except json.JSONDecodeError:
                errors.append("AAD_GROUP_MAP_JSON must be valid JSON")
                
        return len(errors) == 0, errors

    def get_aad_status(self) -> dict:
        """Get AAD groups configuration status for monitoring and debugging"""
        return {
            "mode": self.aad_groups.mode,
            "enabled": self.aad_groups.enabled,
            "tenant_id": self.aad_groups.tenant_id,
            "client_configured": bool(self.aad_groups.client_id),
            "cache_ttl_minutes": self.aad_groups.cache_ttl_minutes,
            "require_tenant_isolation": self.aad_groups.require_tenant_isolation,
            "allowed_tenant_count": len(self.aad_groups.allowed_tenant_ids),
            "is_operational": self.is_aad_groups_enabled()
        }
    
    async def load_secrets_async(self, correlation_id: Optional[str] = None) -> 'AppConfig':
        """Load configuration with secrets from SecretProvider"""
        try:
            from security.secret_provider import get_secret
            
            # Load Azure OpenAI secrets
            azure_openai_endpoint = await get_secret("azure-openai-endpoint", correlation_id)
            azure_openai_api_key = await get_secret("azure-openai-api-key", correlation_id)
            
            # Load Azure Search secrets
            azure_search_endpoint = await get_secret("azure-search-endpoint", correlation_id)
            azure_search_api_key = await get_secret("azure-search-api-key", correlation_id)
            
            # Load AAD secrets
            aad_client_secret = await get_secret("aad-client-secret", correlation_id)
            
            # Create new config with secrets if available
            updated_config = self.model_copy(deep=True)
            
            if azure_openai_endpoint:
                updated_config.azure_openai.endpoint = azure_openai_endpoint
            if azure_openai_api_key:
                updated_config.azure_openai.api_key = azure_openai_api_key
            if azure_search_endpoint:
                updated_config.azure_search.endpoint = azure_search_endpoint
            if azure_search_api_key:
                updated_config.azure_search.api_key = azure_search_api_key
            if aad_client_secret:
                updated_config.aad_groups.client_secret = aad_client_secret
            
            return updated_config
            
        except ImportError:
            # Secret provider not available, return current config
            return self
        except Exception as e:
            # Log error but don't fail, return current config
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Failed to load secrets: {str(e)}",
                extra={"correlation_id": correlation_id}
            )
            return self


class FeatureFlags(BaseSettings):
    """S4 Feature Flags - control feature availability by environment"""
    
    # CSF Grid Feature
    csf_enabled: bool = Field(
        default_factory=lambda: os.getenv("FEATURE_CSF_ENABLED", "true").lower() == "true"
    )
    
    # Workshops & Consent Feature
    workshops_enabled: bool = Field(
        default_factory=lambda: os.getenv("FEATURE_WORKSHOPS_ENABLED", "true").lower() == "true"
    )
    
    # Minutes Publishing Feature
    minutes_enabled: bool = Field(
        default_factory=lambda: os.getenv("FEATURE_MINUTES_ENABLED", "true").lower() == "true"
    )
    
    # Chat Shell Commands Feature
    chat_enabled: bool = Field(
        default_factory=lambda: os.getenv("FEATURE_CHAT_ENABLED", "true").lower() == "true"
    )
    
    # Service Bus Orchestration (requires Azure Service Bus)
    service_bus_orchestration_enabled: bool = Field(
        default_factory=lambda: os.getenv("FEATURE_SERVICE_BUS_ENABLED", "false").lower() == "true"
    )
    
    def is_s4_enabled(self) -> bool:
        """Check if any S4 feature is enabled"""
        return any([
            self.csf_enabled,
            self.workshops_enabled,
            self.minutes_enabled,
            self.chat_enabled,
            self.service_bus_orchestration_enabled
        ])
    
    def get_enabled_features(self) -> List[str]:
        """Get list of enabled S4 features"""
        features = []
        if self.csf_enabled:
            features.append("CSF Grid")
        if self.workshops_enabled:
            features.append("Workshops & Consent")
        if self.minutes_enabled:
            features.append("Minutes Publishing")
        if self.chat_enabled:
            features.append("Chat Shell Commands")
        if self.service_bus_orchestration_enabled:
            features.append("Service Bus Orchestration")
        return features


# Global configuration instance
config = AppConfig()

# S4 Feature flags instance
feature_flags = FeatureFlags()