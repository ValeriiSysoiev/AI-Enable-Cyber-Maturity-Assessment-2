"""
Evidence management endpoints for secure file upload and record management.
"""
import os
import re
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Response
from pydantic import BaseModel, Field

from security.deps import get_current_user, require_role
from domain.models import Evidence
from security.secret_provider import get_secret
from services.evidence_processing import EvidenceProcessor
from repos.cosmos_repository import create_cosmos_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/evidence", tags=["evidence"])

# Configuration
MAX_FILE_SIZE_MB = int(os.getenv("EVIDENCE_MAX_SIZE_MB", "25"))
SAS_TTL_MINUTES = int(os.getenv("EVIDENCE_SAS_TTL_MINUTES", "5"))

# Allowed MIME types for evidence upload
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",        # .xlsx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation", # .pptx
    "text/plain",
    "text/csv",
    "image/png",
    "image/jpeg",
    "image/gif",
    "application/zip",
    "application/x-zip-compressed"
}

class SASRequest(BaseModel):
    """Request model for SAS token generation"""
    engagement_id: str = Field(..., description="Engagement ID")
    filename: str = Field(..., description="Original filename")
    mime_type: str = Field(..., description="Content type")
    size_bytes: int = Field(..., description="File size in bytes")

class SASResponse(BaseModel):
    """Response model for SAS token"""
    upload_url: str = Field(..., description="Pre-signed URL for upload")
    blob_path: str = Field(..., description="Blob storage path")
    expires_at: datetime = Field(..., description="Expiration timestamp")
    max_size: int = Field(..., description="Maximum allowed size in bytes")
    allowed_types: List[str] = Field(..., description="Allowed MIME types")

class CompleteRequest(BaseModel):
    """Request model for finalizing evidence upload"""
    engagement_id: str = Field(..., description="Engagement ID")
    blob_path: str = Field(..., description="Blob storage path")
    filename: str = Field(..., description="Original filename")
    mime_type: str = Field(..., description="Content type")
    size_bytes: int = Field(..., description="File size in bytes")
    client_checksum: Optional[str] = Field(None, description="Client-computed SHA-256 checksum")

class LinkRequest(BaseModel):
    """Request model for linking evidence to assessment items"""
    item_type: str = Field(..., description="Type of item (e.g., 'assessment')")
    item_id: str = Field(..., description="ID of the item")

async def _get_storage_config(correlation_id: str = None) -> dict:
    """Get storage configuration from secret provider"""
    account = await get_secret("azure-storage-account", correlation_id)
    key = await get_secret("azure-storage-key", correlation_id)
    container = await get_secret("azure-storage-container", correlation_id)
    
    # Fallback to environment variables for local development
    if not account:
        account = os.getenv("AZURE_STORAGE_ACCOUNT")
    if not key:
        key = os.getenv("AZURE_STORAGE_KEY")
    if not container:
        container = os.getenv("AZURE_STORAGE_CONTAINER", "evidence")
    
    return {
        "account": account,
        "key": key,
        "container": container
    }

def _safe_filename(filename: str) -> str:
    """Sanitize filename for blob storage"""
    # Remove directory traversal attempts and illegal characters
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    safe_name = safe_name.replace('..', '_')
    # Limit length
    if len(safe_name) > 255:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:250] + ext
    return safe_name

def _validate_mime_type(mime_type: str) -> bool:
    """Validate MIME type against allowed list"""
    return mime_type.lower() in ALLOWED_MIME_TYPES

def _validate_file_size(size_bytes: int) -> bool:
    """Validate file size against limit"""
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    return size_bytes <= max_bytes

async def _check_engagement_membership(user_email: str, engagement_id: str) -> bool:
    """Check if user is a member of the engagement (placeholder for actual check)"""
    # TODO: Implement actual membership check via repository
    # For now, return True for development
    return True

@router.post("/sas", response_model=SASResponse)
async def generate_evidence_sas(
    request: SASRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role(["Member", "LEM", "Admin"]))
):
    """
    Generate a short-lived SAS token for evidence upload.
    
    Requires Member+ role and engagement membership.
    Returns write-only SAS with ≤5 min TTL.
    """
    correlation_id = current_user.get("correlation_id")
    user_email = current_user["email"]
    
    logger.info(
        "Evidence SAS request",
        extra={
            "correlation_id": correlation_id,
            "user_email": user_email,
            "engagement_id": request.engagement_id,
            "filename": request.filename,
            "size_bytes": request.size_bytes,
            "mime_type": request.mime_type
        }
    )
    
    # Check engagement membership
    is_member = await _check_engagement_membership(user_email, request.engagement_id)
    if not is_member:
        logger.warning(
            "Evidence SAS denied - not a member",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email,
                "engagement_id": request.engagement_id
            }
        )
        raise HTTPException(status_code=403, detail="Access denied: not a member of this engagement")
    
    # Validate MIME type
    if not _validate_mime_type(request.mime_type):
        logger.warning(
            "Evidence SAS denied - invalid MIME type",
            extra={
                "correlation_id": correlation_id,
                "mime_type": request.mime_type,
                "allowed_types": list(ALLOWED_MIME_TYPES)
            }
        )
        raise HTTPException(
            status_code=415, 
            detail=f"Unsupported media type: {request.mime_type}. Allowed types: {list(ALLOWED_MIME_TYPES)}"
        )
    
    # Validate file size
    if not _validate_file_size(request.size_bytes):
        logger.warning(
            "Evidence SAS denied - file too large",
            extra={
                "correlation_id": correlation_id,
                "size_bytes": request.size_bytes,
                "max_mb": MAX_FILE_SIZE_MB
            }
        )
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {request.size_bytes} bytes. Maximum: {MAX_FILE_SIZE_MB}MB"
        )
    
    try:
        # Get storage configuration
        storage_config = await _get_storage_config(correlation_id)
        
        if not storage_config["account"]:
            raise HTTPException(
                status_code=501,
                detail="Evidence uploads not configured"
            )
        
        # Generate unique blob path
        evidence_uuid = str(uuid.uuid4())
        safe_filename = _safe_filename(request.filename)
        blob_path = f"engagements/{request.engagement_id}/evidence/{evidence_uuid}/{safe_filename}"
        
        # Generate SAS token (simplified for development - will use actual Azure SDK)
        expires_at = datetime.utcnow() + timedelta(minutes=SAS_TTL_MINUTES)
        
        # For development, create a mock SAS URL
        # In production, this would use Azure SDK to generate actual SAS
        upload_url = f"https://{storage_config['account']}.blob.core.windows.net/{storage_config['container']}/{blob_path}?sv=mock-sas-token"
        
        logger.info(
            "Evidence SAS generated",
            extra={
                "correlation_id": correlation_id,
                "blob_path": blob_path,
                "expires_at": expires_at.isoformat(),
                "ttl_minutes": SAS_TTL_MINUTES
            }
        )
        
        return SASResponse(
            upload_url=upload_url,
            blob_path=blob_path,
            expires_at=expires_at,
            max_size=MAX_FILE_SIZE_MB * 1024 * 1024,
            allowed_types=list(ALLOWED_MIME_TYPES)
        )
        
    except Exception as e:
        logger.error(
            "Failed to generate evidence SAS",
            extra={
                "correlation_id": correlation_id,
                "error": str(e),
                "engagement_id": request.engagement_id
            }
        )
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")

@router.post("/complete")
async def complete_evidence_upload(
    request: CompleteRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role(["Member", "LEM", "Admin"]))
):
    """
    Finalize evidence upload and create Evidence record.
    
    Computes server-side checksum and PII detection.
    """
    correlation_id = current_user.get("correlation_id")
    user_email = current_user["email"]
    
    logger.info(
        "Evidence complete request",
        extra={
            "correlation_id": correlation_id,
            "user_email": user_email,
            "engagement_id": request.engagement_id,
            "blob_path": request.blob_path,
            "size_bytes": request.size_bytes
        }
    )
    
    # Check engagement membership
    is_member = await _check_engagement_membership(user_email, request.engagement_id)
    if not is_member:
        logger.warning(
            "Evidence complete denied - not a member",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email,
                "engagement_id": request.engagement_id
            }
        )
        raise HTTPException(status_code=403, detail="Access denied: not a member of this engagement")
    
    try:
        # Initialize evidence processor and repository
        processor = EvidenceProcessor(correlation_id)
        repository = create_cosmos_repository(correlation_id)
        
        # Verify blob exists and get actual size
        blob_exists, actual_size = await processor.verify_blob_exists(request.blob_path)
        if not blob_exists:
            logger.warning(
                "Blob not found for evidence completion",
                extra={
                    "correlation_id": correlation_id,
                    "blob_path": request.blob_path
                }
            )
            raise HTTPException(status_code=404, detail="Uploaded file not found")
        
        # Validate size matches
        if abs(actual_size - request.size_bytes) > 1024:  # Allow 1KB tolerance
            logger.warning(
                "Size mismatch in evidence completion",
                extra={
                    "correlation_id": correlation_id,
                    "reported_size": request.size_bytes,
                    "actual_size": actual_size
                }
            )
            raise HTTPException(
                status_code=422, 
                detail=f"Size mismatch: reported {request.size_bytes}, actual {actual_size}"
            )
        
        # Compute server-side checksum
        server_checksum = await processor.compute_checksum(request.blob_path)
        if not server_checksum:
            raise HTTPException(status_code=500, detail="Failed to compute file checksum")
        
        # Validate client checksum if provided
        if request.client_checksum and request.client_checksum.lower() != server_checksum.lower():
            logger.warning(
                "Checksum mismatch in evidence completion",
                extra={
                    "correlation_id": correlation_id,
                    "client_checksum": request.client_checksum,
                    "server_checksum": server_checksum[:16] + "..."
                }
            )
            raise HTTPException(
                status_code=422,
                detail="Checksum mismatch: file may be corrupted"
            )
        
        # Detect PII
        pii_detected = await processor.detect_pii(request.blob_path, request.mime_type)
        
        # Create Evidence record
        evidence = Evidence(
            engagement_id=request.engagement_id,
            blob_path=request.blob_path,
            filename=request.filename,
            checksum_sha256=server_checksum,
            size=actual_size,
            mime_type=request.mime_type,
            uploaded_by=user_email,
            pii_flag=pii_detected
        )
        
        # Save to repository
        stored_evidence = await repository.store_evidence(evidence)
        
        logger.info(
            "Evidence record created",
            extra={
                "correlation_id": correlation_id,
                "evidence_id": stored_evidence.id,
                "checksum": server_checksum[:16] + "...",
                "pii_flag": pii_detected,
                "size": actual_size
            }
        )
        
        return {
            "evidence_id": stored_evidence.id, 
            "checksum": server_checksum, 
            "pii_flag": pii_detected,
            "size": actual_size
        }
        
    except Exception as e:
        logger.error(
            "Failed to complete evidence upload",
            extra={
                "correlation_id": correlation_id,
                "error": str(e),
                "blob_path": request.blob_path
            }
        )
        raise HTTPException(status_code=500, detail="Failed to complete upload")

@router.get("", response_model=List[Evidence])
async def list_evidence(
    response: Response,
    engagement_id: str = Query(..., description="Engagement ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role(["Member", "LEM", "Admin"]))
):
    """
    List evidence for an engagement with pagination.
    
    Enforces engagement membership isolation.
    """
    correlation_id = current_user.get("correlation_id")
    user_email = current_user["email"]
    
    # Check engagement membership
    is_member = await _check_engagement_membership(user_email, engagement_id)
    if not is_member:
        logger.warning(
            "Evidence list denied - not a member",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email,
                "engagement_id": engagement_id
            }
        )
        raise HTTPException(status_code=403, detail="Access denied: not a member of this engagement")
    
    try:
        # Initialize repository
        repository = create_cosmos_repository(correlation_id)
        
        # Get evidence list with pagination
        evidence_list, total_count = await repository.list_evidence(
            engagement_id=engagement_id,
            page=page,
            page_size=page_size
        )
        
        # Add pagination headers
        total_pages = (total_count + page_size - 1) // page_size
        response.headers["X-Total-Count"] = str(total_count)
        response.headers["X-Page"] = str(page)
        response.headers["X-Page-Size"] = str(page_size)
        response.headers["X-Total-Pages"] = str(total_pages)
        response.headers["X-Has-Next"] = str(page < total_pages).lower()
        response.headers["X-Has-Previous"] = str(page > 1).lower()
        
        logger.info(
            "Evidence list request completed",
            extra={
                "correlation_id": correlation_id,
                "engagement_id": engagement_id,
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "returned_count": len(evidence_list)
            }
        )
        
        return evidence_list
        
    except Exception as e:
        logger.error(
            "Failed to list evidence",
            extra={
                "correlation_id": correlation_id,
                "engagement_id": engagement_id,
                "error": str(e)
            }
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve evidence list")

@router.post("/{evidence_id}/links")
async def link_evidence(
    evidence_id: str,
    request: LinkRequest,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role(["Member", "LEM", "Admin"]))
):
    """
    Link evidence to an assessment item (many-to-many).
    
    Placeholder for assessment item linking.
    """
    correlation_id = current_user.get("correlation_id")
    user_email = current_user["email"]
    
    try:
        # Initialize repository
        repository = create_cosmos_repository(correlation_id)
        
        # Get existing evidence to verify ownership and get current links
        # Note: We don't have engagement_id here, so we'll need to get it from the evidence record
        evidence = await repository.get_evidence_by_id(evidence_id)
        if not evidence:
            raise HTTPException(status_code=404, detail="Evidence not found")
        
        # Check engagement membership for the evidence
        is_member = await _check_engagement_membership(user_email, evidence.engagement_id)
        if not is_member:
            logger.warning(
                "Evidence link denied - not a member",
                extra={
                    "correlation_id": correlation_id,
                    "user_email": user_email,
                    "evidence_id": evidence_id,
                    "engagement_id": evidence.engagement_id
                }
            )
            raise HTTPException(status_code=403, detail="Access denied: not a member of this engagement")
        
        # Add new link to existing links
        new_link = {"item_type": request.item_type, "item_id": request.item_id}
        updated_links = evidence.linked_items.copy()
        
        # Check if link already exists
        if new_link not in updated_links:
            updated_links.append(new_link)
            
            # Update evidence record
            success = await repository.update_evidence_links(
                evidence_id, 
                evidence.engagement_id, 
                updated_links
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to update evidence links")
        
        logger.info(
            "Evidence link created",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email,
                "evidence_id": evidence_id,
                "item_type": request.item_type,
                "item_id": request.item_id,
                "total_links": len(updated_links)
            }
        )
        
        return {
            "message": "Link created", 
            "evidence_id": evidence_id, 
            "item_type": request.item_type, 
            "item_id": request.item_id,
            "total_links": len(updated_links)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to link evidence",
            extra={
                "correlation_id": correlation_id,
                "evidence_id": evidence_id,
                "error": str(e)
            }
        )
        raise HTTPException(status_code=500, detail="Failed to create evidence link")

@router.delete("/{evidence_id}/links/{link_id}")
async def unlink_evidence(
    evidence_id: str,
    link_id: str,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role(["Member", "LEM", "Admin"]))
):
    """
    Remove a link between evidence and an assessment item.
    
    link_id format: "{item_type}:{item_id}"
    """
    correlation_id = current_user.get("correlation_id")
    user_email = current_user["email"]
    
    logger.info(
        "Evidence unlink request",
        extra={
            "correlation_id": correlation_id,
            "user_email": user_email,
            "evidence_id": evidence_id,
            "link_id": link_id
        }
    )
    
    try:
        # Parse link_id format: "item_type:item_id"
        if ":" not in link_id:
            raise HTTPException(
                status_code=400, 
                detail="Invalid link_id format. Expected: 'item_type:item_id'"
            )
        
        item_type, item_id = link_id.split(":", 1)
        target_link = {"item_type": item_type, "item_id": item_id}
        
        # Initialize repository
        repository = create_cosmos_repository(correlation_id)
        
        # Get existing evidence to verify ownership and get current links
        evidence = await repository.get_evidence_by_id(evidence_id)
        if not evidence:
            raise HTTPException(status_code=404, detail="Evidence not found")
        
        # Check engagement membership for the evidence
        is_member = await _check_engagement_membership(user_email, evidence.engagement_id)
        if not is_member:
            logger.warning(
                "Evidence unlink denied - not a member",
                extra={
                    "correlation_id": correlation_id,
                    "user_email": user_email,
                    "evidence_id": evidence_id,
                    "engagement_id": evidence.engagement_id
                }
            )
            raise HTTPException(status_code=403, detail="Access denied: not a member of this engagement")
        
        # Remove link from existing links
        updated_links = evidence.linked_items.copy()
        link_found = False
        
        # Find and remove the matching link
        for i, link in enumerate(updated_links):
            if link.get("item_type") == item_type and link.get("item_id") == item_id:
                updated_links.pop(i)
                link_found = True
                break
        
        if not link_found:
            logger.warning(
                "Evidence link not found for removal",
                extra={
                    "correlation_id": correlation_id,
                    "evidence_id": evidence_id,
                    "item_type": item_type,
                    "item_id": item_id,
                    "existing_links": len(evidence.linked_items)
                }
            )
            raise HTTPException(status_code=404, detail="Evidence link not found")
        
        # Update evidence record
        success = await repository.update_evidence_links(
            evidence_id, 
            evidence.engagement_id, 
            updated_links
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update evidence links")
        
        logger.info(
            "Evidence link removed",
            extra={
                "correlation_id": correlation_id,
                "user_email": user_email,
                "evidence_id": evidence_id,
                "item_type": item_type,
                "item_id": item_id,
                "remaining_links": len(updated_links)
            }
        )
        
        return {
            "message": "Link removed", 
            "evidence_id": evidence_id, 
            "item_type": item_type, 
            "item_id": item_id,
            "remaining_links": len(updated_links)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to unlink evidence",
            extra={
                "correlation_id": correlation_id,
                "evidence_id": evidence_id,
                "link_id": link_id,
                "error": str(e)
            }
        )
        raise HTTPException(status_code=500, detail="Failed to remove evidence link")