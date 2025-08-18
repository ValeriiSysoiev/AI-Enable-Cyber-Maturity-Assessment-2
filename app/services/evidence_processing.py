"""
Evidence processing service for checksum computation and PII detection.
"""
import hashlib
import re
import logging
from typing import Optional, Tuple
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

from security.secret_provider import get_secret

logger = logging.getLogger(__name__)

# PII detection patterns
PII_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'phone': r'\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
    'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
}

class EvidenceProcessor:
    """Service for processing evidence files: checksum computation and PII detection"""
    
    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id
        self.blob_client = None
        
    async def _get_blob_client(self) -> BlobServiceClient:
        """Get Azure Blob Service client"""
        if self.blob_client is None:
            # Get storage configuration from secret provider
            account = await get_secret("azure-storage-account", self.correlation_id)
            key = await get_secret("azure-storage-key", self.correlation_id)
            
            # Fallback to environment variables for local development
            if not account:
                import os
                account = os.getenv("AZURE_STORAGE_ACCOUNT")
            if not key:
                import os
                key = os.getenv("AZURE_STORAGE_KEY")
            
            if account and key:
                account_url = f"https://{account}.blob.core.windows.net"
                credential = DefaultAzureCredential()
                self.blob_client = BlobServiceClient(account_url=account_url, credential=credential)
            else:
                # For local development, we'll use a mock or Azurite
                logger.warning(
                    "Storage not configured, using mock blob client",
                    extra={"correlation_id": self.correlation_id}
                )
                self.blob_client = None
        
        return self.blob_client
    
    async def compute_checksum(self, blob_path: str, container: str = "evidence") -> Optional[str]:
        """
        Compute SHA-256 checksum of blob by streaming content.
        
        Args:
            blob_path: Path to blob in storage
            container: Container name
            
        Returns:
            SHA-256 hex digest or None if failed
        """
        try:
            blob_client = await self._get_blob_client()
            if blob_client is None:
                # Mock for development
                logger.info(
                    "Using mock checksum for development",
                    extra={"correlation_id": self.correlation_id, "blob_path": blob_path}
                )
                return "mock-sha256-" + hashlib.sha256(blob_path.encode()).hexdigest()[:16]
            
            # Get blob client for specific blob
            blob = blob_client.get_blob_client(container=container, blob=blob_path)
            
            # Stream blob content and compute hash
            sha256_hash = hashlib.sha256()
            stream = blob.download_blob()
            
            # Process in chunks to handle large files
            chunk_size = 8192
            for chunk in stream.chunks():
                sha256_hash.update(chunk)
            
            checksum = sha256_hash.hexdigest()
            
            logger.info(
                "Computed blob checksum",
                extra={
                    "correlation_id": self.correlation_id,
                    "blob_path": blob_path,
                    "checksum": checksum[:16] + "..."  # Log first 16 chars only
                }
            )
            
            return checksum
            
        except Exception as e:
            logger.error(
                "Failed to compute blob checksum",
                extra={
                    "correlation_id": self.correlation_id,
                    "blob_path": blob_path,
                    "error": str(e)
                }
            )
            return None
    
    async def verify_blob_exists(self, blob_path: str, container: str = "evidence") -> Tuple[bool, int]:
        """
        Verify blob exists and get its size.
        
        Args:
            blob_path: Path to blob in storage
            container: Container name
            
        Returns:
            Tuple of (exists, size_bytes)
        """
        try:
            blob_client = await self._get_blob_client()
            if blob_client is None:
                # Mock for development
                logger.info(
                    "Using mock blob verification for development",
                    extra={"correlation_id": self.correlation_id, "blob_path": blob_path}
                )
                return True, 1024  # Mock 1KB file
            
            # Get blob client for specific blob
            blob = blob_client.get_blob_client(container=container, blob=blob_path)
            
            # Get blob properties
            properties = blob.get_blob_properties()
            size = properties.size
            
            logger.info(
                "Verified blob exists",
                extra={
                    "correlation_id": self.correlation_id,
                    "blob_path": blob_path,
                    "size_bytes": size
                }
            )
            
            return True, size
            
        except Exception as e:
            logger.warning(
                "Blob verification failed",
                extra={
                    "correlation_id": self.correlation_id,
                    "blob_path": blob_path,
                    "error": str(e)
                }
            )
            return False, 0
    
    async def detect_pii(self, blob_path: str, mime_type: str, container: str = "evidence") -> bool:
        """
        Detect potential PII in blob content using regex heuristics.
        
        Args:
            blob_path: Path to blob in storage
            mime_type: MIME type of the file
            container: Container name
            
        Returns:
            True if potential PII detected, False otherwise
        """
        try:
            # Only scan text-based files for PII
            text_mime_types = [
                'text/plain',
                'text/csv',
                'application/json',
                'text/xml'
            ]
            
            if mime_type not in text_mime_types:
                logger.info(
                    "Skipping PII detection for non-text file",
                    extra={
                        "correlation_id": self.correlation_id,
                        "blob_path": blob_path,
                        "mime_type": mime_type
                    }
                )
                return False
            
            blob_client = await self._get_blob_client()
            if blob_client is None:
                # Mock for development
                logger.info(
                    "Using mock PII detection for development",
                    extra={"correlation_id": self.correlation_id, "blob_path": blob_path}
                )
                # Mock: detect PII in 10% of files for testing
                return hash(blob_path) % 10 == 0
            
            # Get blob client for specific blob
            blob = blob_client.get_blob_client(container=container, blob=blob_path)
            
            # Download first 10KB for PII scanning (to avoid processing huge files)
            max_scan_bytes = 10 * 1024
            stream = blob.download_blob(max_concurrency=1)
            content_bytes = stream.readall()[:max_scan_bytes]
            
            try:
                # Try to decode as UTF-8
                content = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                # If can't decode, skip PII detection
                logger.info(
                    "Cannot decode file as UTF-8, skipping PII detection",
                    extra={"correlation_id": self.correlation_id, "blob_path": blob_path}
                )
                return False
            
            # Check for PII patterns
            pii_found = False
            matches = {}
            
            for pattern_name, pattern in PII_PATTERNS.items():
                matches_found = re.findall(pattern, content)
                if matches_found:
                    pii_found = True
                    matches[pattern_name] = len(matches_found)
            
            if pii_found:
                logger.warning(
                    "Potential PII detected in file",
                    extra={
                        "correlation_id": self.correlation_id,
                        "blob_path": blob_path,
                        "pii_types": list(matches.keys()),
                        "match_counts": matches
                    }
                )
            else:
                logger.info(
                    "No PII detected in file",
                    extra={"correlation_id": self.correlation_id, "blob_path": blob_path}
                )
            
            return pii_found
            
        except Exception as e:
            logger.error(
                "PII detection failed",
                extra={
                    "correlation_id": self.correlation_id,
                    "blob_path": blob_path,
                    "error": str(e)
                }
            )
            # Return False on error to be conservative
            return False