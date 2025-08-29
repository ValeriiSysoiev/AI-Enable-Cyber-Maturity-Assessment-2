"""
Document Metadata Caching Service

Provides caching for document-related data including:
- Document metadata and file information
- Document access permissions and policies
- Document processing status and results
- Document search indexes and tags
"""

import logging
from typing import List, Optional
from datetime import datetime
from services.cache import get_cached, invalidate_cache_key, cache_manager
import sys
sys.path.append("/app")
from config import config
from domain.models import (
    DocumentMetadata,
    DocumentPermissions, 
    DocumentProcessingStatus,
    DocumentSearchIndex
)

logger = logging.getLogger(__name__)


class DocumentCacheService:
    """Service for caching document metadata and related data"""
    
    CACHE_NAME = "document_metadata"
    
    def __init__(self):
        self.cache_config = {
            "max_size_mb": config.cache.document_metadata_max_size_mb,
            "max_entries": config.cache.document_metadata_max_entries,
            "default_ttl_seconds": config.cache.document_metadata_ttl_seconds,
            "cleanup_interval_seconds": config.cache.cleanup_interval_seconds
        }
    
    async def get_document_metadata(self, engagement_id: str, doc_id: str) -> Optional[DocumentMetadata]:
        """Get cached document metadata"""
        if not config.cache.enabled:
            return await self._load_document_metadata_uncached(engagement_id, doc_id)
        
        async def compute_metadata():
            return await self._load_document_metadata_uncached(engagement_id, doc_id)
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key=f"doc_{engagement_id}_{doc_id}",
            factory=compute_metadata,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def list_engagement_documents(self, engagement_id: str) -> List[DocumentMetadata]:
        """Get cached list of documents for an engagement"""
        if not config.cache.enabled:
            return await self._load_engagement_documents_uncached(engagement_id)
        
        async def compute_documents():
            return await self._load_engagement_documents_uncached(engagement_id)
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key=f"engagement_docs_{engagement_id}",
            factory=compute_documents,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def get_document_permissions(self, engagement_id: str, doc_id: str) -> Optional[DocumentPermissions]:
        """Get cached document permissions"""
        if not config.cache.enabled:
            return await self._load_document_permissions_uncached(engagement_id, doc_id)
        
        async def compute_permissions():
            return await self._load_document_permissions_uncached(engagement_id, doc_id)
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key=f"permissions_{engagement_id}_{doc_id}",
            factory=compute_permissions,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def get_document_processing_status(self, engagement_id: str, doc_id: str) -> Optional[DocumentProcessingStatus]:
        """Get cached document processing status"""
        if not config.cache.enabled:
            return await self._load_processing_status_uncached(engagement_id, doc_id)
        
        async def compute_status():
            return await self._load_processing_status_uncached(engagement_id, doc_id)
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key=f"processing_{engagement_id}_{doc_id}",
            factory=compute_status,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def get_document_search_index(self, engagement_id: str) -> Optional[DocumentSearchIndex]:
        """Get cached document search index for an engagement"""
        if not config.cache.enabled:
            return await self._load_search_index_uncached(engagement_id)
        
        async def compute_index():
            return await self._load_search_index_uncached(engagement_id)
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key=f"search_index_{engagement_id}",
            factory=compute_index,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def get_document_tags(self, engagement_id: str, doc_id: str) -> List[str]:
        """Get cached document tags"""
        if not config.cache.enabled:
            return await self._load_document_tags_uncached(engagement_id, doc_id)
        
        async def compute_tags():
            return await self._load_document_tags_uncached(engagement_id, doc_id)
        
        return await get_cached(
            cache_name=self.CACHE_NAME,
            key=f"tags_{engagement_id}_{doc_id}",
            factory=compute_tags,
            ttl_seconds=self.cache_config["default_ttl_seconds"],
            **self.cache_config
        )
    
    async def invalidate_document_cache(self, engagement_id: str, doc_id: str) -> None:
        """Invalidate all cache entries for a specific document"""
        if not config.cache.enabled:
            return
        
        cache_keys = [
            f"doc_{engagement_id}_{doc_id}",
            f"permissions_{engagement_id}_{doc_id}",
            f"processing_{engagement_id}_{doc_id}",
            f"tags_{engagement_id}_{doc_id}",
            f"engagement_docs_{engagement_id}",  # List needs refresh
            f"search_index_{engagement_id}"  # Search index needs refresh
        ]
        
        for key in cache_keys:
            await invalidate_cache_key(self.CACHE_NAME, key)
        
        logger.info(
            f"Invalidated document cache for {doc_id} in engagement {engagement_id}",
            extra={
                "engagement_id": engagement_id,
                "doc_id": doc_id,
                "invalidated_keys": len(cache_keys)
            }
        )
    
    async def invalidate_engagement_cache(self, engagement_id: str) -> None:
        """Invalidate all cache entries for an engagement"""
        if not config.cache.enabled:
            return
        
        # Use pattern invalidation to clear all cache entries for this engagement
        from services.cache import invalidate_cache_pattern
        
        patterns = [
            f"_{engagement_id}_",  # Matches doc_ENGAGEMENT_ID_DOCID
            f"engagement_docs_{engagement_id}",
            f"search_index_{engagement_id}"
        ]
        
        total_invalidated = 0
        for pattern in patterns:
            count = await invalidate_cache_pattern(self.CACHE_NAME, pattern)
            total_invalidated += count
        
        logger.info(
            f"Invalidated engagement document cache for {engagement_id}",
            extra={
                "engagement_id": engagement_id,
                "total_invalidated": total_invalidated
            }
        )
    
    async def invalidate_all_document_cache(self) -> None:
        """Invalidate all document cache entries"""
        if not config.cache.enabled:
            return
        
        cache = cache_manager.get_cache(self.CACHE_NAME, **self.cache_config)
        await cache.clear()
        
        logger.info("Invalidated all document cache entries")
    
    async def _load_document_metadata_uncached(self, engagement_id: str, doc_id: str) -> Optional[DocumentMetadata]:
        """Load document metadata without caching"""
        # This would integrate with the repository layer and storage services
        # Placeholder implementation
        try:
            # In a real system, this would query the repository
            from domain.repository import InMemoryRepository
            
            # Placeholder metadata structure
            metadata = DocumentMetadata(
                id=doc_id,
                engagement_id=engagement_id,
                filename=f"document_{doc_id}.pdf",
                original_filename=f"uploaded_document.pdf",
                content_type="application/pdf",
                size_bytes=1024000,  # 1MB placeholder
                upload_date=datetime.utcnow().isoformat(),
                uploaded_by="system@example.com",
                status="processed",
                checksum=f"sha256_{doc_id}",
                storage_path=f"data/engagements/{engagement_id}/documents/{doc_id}",
                processing_complete=True,
                text_extracted=True,
                embeddings_generated=False,
                security_scan_complete=True,
                security_scan_status="clean"
            )
            
            logger.debug(
                f"Loaded document metadata for {doc_id}",
                extra={
                    "engagement_id": engagement_id,
                    "doc_id": doc_id,
                    "size_mb": round(metadata.size_bytes / (1024 * 1024), 2)
                }
            )
            
            return metadata
            
        except Exception as e:
            logger.error(
                f"Failed to load document metadata for {doc_id}",
                extra={
                    "engagement_id": engagement_id,
                    "doc_id": doc_id,
                    "error": str(e)
                }
            )
            return None
    
    async def _load_engagement_documents_uncached(self, engagement_id: str) -> List[DocumentMetadata]:
        """Load engagement documents without caching"""
        try:
            # In a real system, this would query the repository
            # Placeholder implementation
            documents = [
                DocumentMetadata(
                    id="doc_001",
                    engagement_id=engagement_id,
                    filename="security_policy.pdf",
                    original_filename="security_policy.pdf",
                    content_type="application/pdf",
                    size_bytes=512000,
                    upload_date="2024-01-01T10:00:00Z",
                    uploaded_by="admin@example.com",
                    status="processed",
                    checksum="sha256_001",
                    storage_path=f"data/engagements/{engagement_id}/documents/doc_001",
                    processing_complete=True,
                    text_extracted=True,
                    security_scan_complete=True,
                    security_scan_status="clean"
                ),
                DocumentMetadata(
                    id="doc_002",
                    engagement_id=engagement_id,
                    filename="network_diagram.png",
                    original_filename="network_diagram.png",
                    content_type="image/png",
                    size_bytes=256000,
                    upload_date="2024-01-02T14:30:00Z",
                    uploaded_by="engineer@example.com",
                    status="processed",
                    checksum="sha256_002",
                    storage_path=f"data/engagements/{engagement_id}/documents/doc_002",
                    processing_complete=True,
                    text_extracted=False,  # Images don't extract text
                    security_scan_complete=True,
                    security_scan_status="clean"
                ),
                DocumentMetadata(
                    id="doc_003",
                    engagement_id=engagement_id,
                    filename="incident_response_plan.docx",
                    original_filename="incident_response_plan.docx",
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    size_bytes=128000,
                    upload_date="2024-01-03T09:15:00Z",
                    uploaded_by="security@example.com",
                    status="processing",
                    checksum="sha256_003",
                    storage_path=f"data/engagements/{engagement_id}/documents/doc_003",
                    processing_complete=False,  # Still processing
                    text_extracted=False,
                    security_scan_complete=False,
                    security_scan_status="pending"
                )
            ]
            
            logger.debug(
                f"Loaded {len(documents)} documents for engagement {engagement_id}",
                extra={
                    "engagement_id": engagement_id,
                    "document_count": len(documents)
                }
            )
            
            return documents
            
        except Exception as e:
            logger.error(
                f"Failed to load engagement documents for {engagement_id}",
                extra={"engagement_id": engagement_id, "error": str(e)}
            )
            return []
    
    async def _load_document_permissions_uncached(self, engagement_id: str, doc_id: str) -> Optional[DocumentPermissions]:
        """Load document permissions without caching"""
        # Placeholder implementation
        permissions = DocumentPermissions(
            doc_id=doc_id,
            engagement_id=engagement_id,
            access_level="confidential",
            allowed_roles=["admin", "lead"],
            allowed_users=["admin@example.com", "user@example.com"],
            read_only=False,
            expires_at=None,
            created_by="admin@example.com"
        )
        
        logger.debug(
            f"Loaded document permissions for {doc_id}",
            extra={
                "engagement_id": engagement_id,
                "doc_id": doc_id,
                "access_level": permissions.access_level
            }
        )
        
        return permissions
    
    async def _load_processing_status_uncached(self, engagement_id: str, doc_id: str) -> Optional[DocumentProcessingStatus]:
        """Load document processing status without caching"""
        # Placeholder implementation
        status = DocumentProcessingStatus(
            doc_id=doc_id,
            engagement_id=engagement_id,
            stage="complete",
            progress_percent=100.0,
            completed_at=datetime.utcnow(),
            error_message=None,
            retry_count=0
        )
        
        logger.debug(
            f"Loaded processing status for {doc_id}",
            extra={
                "engagement_id": engagement_id,
                "doc_id": doc_id,
                "stage": status.stage,
                "progress_percent": status.progress_percent
            }
        )
        
        return status
    
    async def _load_search_index_uncached(self, engagement_id: str) -> Optional[DocumentSearchIndex]:
        """Load document search index without caching"""
        # Placeholder implementation
        search_index = DocumentSearchIndex(
            engagement_id=engagement_id,
            index_name=f"search_index_{engagement_id}",
            document_count=2,
            total_size_bytes=4096,
            search_enabled=True,
            embedding_model="text-embedding-3-large",
            chunk_count=150
        )
        
        logger.debug(
            f"Loaded search index for engagement {engagement_id}",
            extra={
                "engagement_id": engagement_id,
                "indexed_documents": search_index.document_count
            }
        )
        
        return search_index
    
    async def _load_document_tags_uncached(self, engagement_id: str, doc_id: str) -> List[str]:
        """Load document tags without caching"""
        # Placeholder implementation
        tags = [
            "security",
            "policy",
            "compliance",
            "official",
            "current"
        ]
        
        logger.debug(
            f"Loaded {len(tags)} tags for document {doc_id}",
            extra={
                "engagement_id": engagement_id,
                "doc_id": doc_id,
                "tag_count": len(tags)
            }
        )
        
        return tags


# Global instance
document_cache_service = DocumentCacheService()


# Convenience functions
async def get_document_metadata(engagement_id: str, doc_id: str) -> Optional[DocumentMetadata]:
    """Get document metadata with caching"""
    return await document_cache_service.get_document_metadata(engagement_id, doc_id)


async def list_engagement_documents(engagement_id: str) -> List[DocumentMetadata]:
    """List engagement documents with caching"""
    return await document_cache_service.list_engagement_documents(engagement_id)


async def get_document_permissions(engagement_id: str, doc_id: str) -> Optional[DocumentPermissions]:
    """Get document permissions with caching"""
    return await document_cache_service.get_document_permissions(engagement_id, doc_id)


async def get_document_processing_status(engagement_id: str, doc_id: str) -> Optional[DocumentProcessingStatus]:
    """Get document processing status with caching"""
    return await document_cache_service.get_document_processing_status(engagement_id, doc_id)


async def invalidate_document_cache(engagement_id: str, doc_id: str) -> None:
    """Invalidate cache for specific document"""
    await document_cache_service.invalidate_document_cache(engagement_id, doc_id)


async def invalidate_engagement_cache(engagement_id: str) -> None:
    """Invalidate cache for entire engagement"""
    await document_cache_service.invalidate_engagement_cache(engagement_id)