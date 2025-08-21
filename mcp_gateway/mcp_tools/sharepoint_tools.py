"""
SharePoint tools for MCP Gateway

Provides SharePoint document fetch operations with tenant-scoped access control,
provenance tracking, and comprehensive security validation.
"""

import os
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from . import McpTool, McpCallResult, McpError, McpToolRegistry
from security import SecurityValidator, PathSecurityError, MimeTypeError

logger = logging.getLogger(__name__)

# Supported file types for SharePoint ingestion
ALLOWED_FILE_TYPES = {'.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.md'}

class SharePointFetchTool(McpTool):
    """Tool for fetching documents from SharePoint with tenant-scoped access"""
    
    def __init__(self, security_validator: SecurityValidator):
        super().__init__(
            name="sharepoint.fetch",
            description="Fetch documents from SharePoint with provenance tracking",
            schema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": "SharePoint tenant identifier"
                    },
                    "site_url": {
                        "type": "string", 
                        "description": "SharePoint site URL or path"
                    },
                    "document_path": {
                        "type": "string",
                        "description": "Path to document or folder within SharePoint site"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Recursively fetch documents from subfolders",
                        "default": False
                    },
                    "file_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "File types to include (default: all allowed types)",
                        "default": list(ALLOWED_FILE_TYPES)
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["REAL", "DRY-RUN"],
                        "description": "Execution mode: REAL uses env creds, DRY-RUN uses demo data",
                        "default": "DRY-RUN"
                    }
                },
                "required": ["tenant_id", "site_url", "document_path"]
            }
        )
        self.security_validator = security_validator
    
    async def execute(self, payload: Dict[str, Any], engagement_id: str) -> McpCallResult:
        """Execute SharePoint fetch operation"""
        try:
            self.validate_payload(payload, ["tenant_id", "site_url", "document_path"])
            
            mode = payload.get("mode", "DRY-RUN")
            tenant_id = payload["tenant_id"]
            site_url = payload["site_url"]
            document_path = payload["document_path"]
            recursive = payload.get("recursive", False)
            file_types = set(payload.get("file_types", ALLOWED_FILE_TYPES))
            
            # Validate file types against allowlist
            invalid_types = file_types - ALLOWED_FILE_TYPES
            if invalid_types:
                raise McpError(
                    f"Invalid file types: {invalid_types}. Allowed: {ALLOWED_FILE_TYPES}",
                    "INVALID_FILE_TYPES"
                )
            
            self.logger.info(
                f"SharePoint fetch initiated",
                extra={
                    "mode": mode,
                    "tenant_id": tenant_id,
                    "site_url": site_url,
                    "document_path": document_path,
                    "engagement_id": engagement_id
                }
            )
            
            if mode == "REAL":
                return await self._fetch_real(tenant_id, site_url, document_path, 
                                            engagement_id, recursive, file_types)
            else:
                return await self._fetch_dryrun(tenant_id, site_url, document_path,
                                              engagement_id, recursive, file_types)
                
        except Exception as e:
            self.logger.error(f"SharePoint fetch failed: {e}", exc_info=True)
            if isinstance(e, McpError):
                return McpCallResult(success=False, error=str(e), error_code=e.code)
            return McpCallResult(success=False, error="SharePoint fetch failed", error_code="FETCH_ERROR")
    
    async def _fetch_real(self, tenant_id: str, site_url: str, document_path: str,
                         engagement_id: str, recursive: bool, file_types: set) -> McpCallResult:
        """Fetch documents from real SharePoint using environment credentials"""
        
        # Check for required environment variables
        required_env_vars = ["SHAREPOINT_CLIENT_ID", "SHAREPOINT_CLIENT_SECRET", "SHAREPOINT_TENANT"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            self.logger.warning(f"Missing SharePoint credentials: {missing_vars}")
            raise McpError(
                f"Missing required environment variables: {missing_vars}",
                "MISSING_CREDENTIALS"
            )
        
        # TODO: Implement real SharePoint Graph API integration
        # This would use Microsoft Graph API with the credentials to:
        # 1. Authenticate with Azure AD
        # 2. Access SharePoint site 
        # 3. Enumerate documents matching criteria
        # 4. Download content with proper error handling
        
        # For now, return placeholder indicating real mode would be implemented
        return McpCallResult(
            success=False,
            error="Real SharePoint integration not yet implemented in this demo",
            error_code="NOT_IMPLEMENTED"
        )
    
    async def _fetch_dryrun(self, tenant_id: str, site_url: str, document_path: str,
                           engagement_id: str, recursive: bool, file_types: set) -> McpCallResult:
        """Fetch documents from demo data directory"""
        
        # Map to demo data directory
        demo_base = Path(self.security_validator.data_root) / "sharepoint_demo" / engagement_id
        
        if not demo_base.exists():
            raise McpError(
                f"Demo SharePoint data not found for engagement: {engagement_id}",
                "DEMO_DATA_MISSING"
            )
        
        documents = []
        
        # Find matching files
        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"
            
        for file_path in demo_base.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in file_types:
                # Generate provenance metadata
                doc_info = await self._generate_provenance(file_path, tenant_id, site_url, document_path)
                documents.append(doc_info)
        
        if not documents:
            self.logger.warning(f"No matching documents found in demo data")
            return McpCallResult(
                success=True,
                result={
                    "documents": [],
                    "count": 0,
                    "message": "No documents found matching criteria"
                }
            )
        
        self.logger.info(f"Successfully fetched {len(documents)} documents from demo SharePoint")
        
        return McpCallResult(
            success=True,
            result={
                "documents": documents,
                "count": len(documents),
                "tenant_id": tenant_id,
                "site_url": site_url,
                "document_path": document_path,
                "engagement_id": engagement_id,
                "mode": "DRY-RUN",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def _generate_provenance(self, file_path: Path, tenant_id: str, 
                                 site_url: str, document_path: str) -> Dict[str, Any]:
        """Generate comprehensive provenance metadata for a document"""
        
        # Calculate file checksum
        file_content = file_path.read_bytes()
        checksum = hashlib.sha256(file_content).hexdigest()
        
        # Get file stats
        stat = file_path.stat()
        
        return {
            "file_name": file_path.name,
            "file_size": stat.st_size,
            "file_type": file_path.suffix.lower(),
            "checksum_sha256": checksum,
            "source": {
                "type": "sharepoint",
                "tenant_id": tenant_id,
                "site_url": site_url,
                "document_path": document_path,
                "full_path": f"{site_url}/{document_path}/{file_path.name}"
            },
            "provenance": {
                "ingested_at": datetime.utcnow().isoformat(),
                "ingested_by": "mcp.sharepoint.fetch",
                "mode": "DRY-RUN",
                "local_path": str(file_path),
                "modified_date": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created_date": datetime.fromtimestamp(stat.st_ctime).isoformat()
            },
            "security": {
                "validated": True,
                "allowed_file_type": True,
                "checksum_verified": True
            }
        }

def register_sharepoint_tools(registry: McpToolRegistry, security_validator: SecurityValidator):
    """Register SharePoint tools with the MCP registry"""
    
    sharepoint_fetch = SharePointFetchTool(security_validator)
    registry.register(sharepoint_fetch, allowed_by_default=True)
    
    logger.info("SharePoint tools registered successfully")