"""
GDPR Data Governance API Routes

Provides RESTful endpoints for GDPR compliance operations:
- Data export for engagement data (Lead/Admin only)
- Data purge initiation with background processing
- Background job management and monitoring
- Audit log access and compliance reporting
- TTL policy management
- Admin dashboard for GDPR operations

All endpoints include proper authentication guards and audit logging.
"""

import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from datetime import datetime

from api.schemas.gdpr import (
    GDPRDataExportRequest, GDPRDataExportResponse,
    GDPRDataPurgeRequest, GDPRDataPurgeResponse,
    BackgroundJobListResponse, BackgroundJobResponse,
    TTLPolicyResponse, TTLPolicy,
    DataRetentionReportResponse,
    GDPRDashboardResponse,
    AuditLogResponse, AuditActionType
)
from api.security import current_context, require_member, require_admin
from domain.repository import Repository
from services.gdpr import create_gdpr_service
from services.audit import create_audit_service
from services.background_jobs import create_background_job_service
from util.logging import get_correlation_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gdpr", tags=["GDPR Data Governance"])


# Dependency injection
async def get_services(
    request: Request,
    ctx: Dict = Depends(current_context)
) -> Dict:
    """Get service dependencies with current context"""
    # This would be properly injected in a real application
    # For now, create mock services
    repository = None  # Would be injected
    audit_service = create_audit_service(repository)
    background_job_service = create_background_job_service(repository, audit_service)
    gdpr_service = create_gdpr_service(repository, audit_service, background_job_service)
    
    return {
        "repository": repository,
        "audit_service": audit_service,
        "background_job_service": background_job_service,
        "gdpr_service": gdpr_service,
        "correlation_id": request.headers.get("X-Correlation-ID", get_correlation_id()),
        "ctx": ctx
    }


# Data Export Endpoints
@router.post("/engagements/{engagement_id}/export", response_model=GDPRDataExportResponse)
async def export_engagement_data(
    engagement_id: str,
    request: GDPRDataExportRequest,
    services: Dict = Depends(get_services)
) -> GDPRDataExportResponse:
    """
    Export complete engagement data for GDPR compliance (Lead/Admin only)
    
    Exports all data associated with an engagement including:
    - Engagement details and memberships
    - All assessments, questions, and responses
    - Findings and recommendations
    - Documents and metadata
    - Optional: Vector embeddings
    
    Returns a complete JSON bundle with all engagement data.
    
    **Required Role:** Lead or Admin
    **Legal Basis:** GDPR Article 15 - Right of access
    """
    try:
        ctx = services["ctx"]
        repository = services["repository"]
        gdpr_service = services["gdpr_service"]
        correlation_id = services["correlation_id"]
        
        # Validate engagement_id matches header
        if ctx["engagement_id"] != engagement_id:
            raise HTTPException(400, "Engagement ID mismatch")
        
        # Ensure request has correct engagement_id
        request.engagement_id = engagement_id
        
        # Require Lead or Admin role
        require_member(repository, ctx, min_role="lead")
        
        logger.info(
            f"GDPR data export requested for engagement {engagement_id}",
            extra={
                'engagement_id': engagement_id,
                'user_email': ctx['user_email'],
                'correlation_id': correlation_id,
                'export_format': request.export_format
            }
        )
        
        # Perform data export
        export_response = await gdpr_service.export_engagement_data(
            request=request,
            user_email=ctx["user_email"],
            correlation_id=correlation_id
        )
        
        return export_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"GDPR data export failed: {str(e)}",
            extra={
                'engagement_id': engagement_id,
                'user_email': ctx.get('user_email'),
                'correlation_id': correlation_id,
                'error': str(e)
            }
        )
        raise HTTPException(500, f"Data export failed: {str(e)}")


# Data Purge Endpoints
@router.post("/engagements/{engagement_id}/purge", response_model=GDPRDataPurgeResponse)
async def initiate_data_purge(
    engagement_id: str,
    request: GDPRDataPurgeRequest,
    services: Dict = Depends(get_services)
) -> GDPRDataPurgeResponse:
    """
    Initiate data purge for GDPR compliance (Lead/Admin only)
    
    Initiates soft or hard delete of all engagement data:
    - **Soft Delete:** Marks data for deletion with configurable retention period
    - **Hard Delete:** Permanently removes data (requires confirmation)
    
    Data purge is processed asynchronously via background jobs.
    
    **Required Role:** Lead or Admin
    **Legal Basis:** GDPR Article 17 - Right to erasure
    """
    try:
        ctx = services["ctx"]
        repository = services["repository"]
        gdpr_service = services["gdpr_service"]
        correlation_id = services["correlation_id"]
        
        # Validate engagement_id matches header
        if ctx["engagement_id"] != engagement_id:
            raise HTTPException(400, "Engagement ID mismatch")
        
        # Ensure request has correct engagement_id
        request.engagement_id = engagement_id
        
        # Require Lead or Admin role
        require_member(repository, ctx, min_role="lead")
        
        # Additional validation for hard delete
        if request.purge_type == "hard_delete" and not request.confirm_purge:
            raise HTTPException(400, "Hard delete requires explicit confirmation")
        
        logger.info(
            f"GDPR data purge requested for engagement {engagement_id}",
            extra={
                'engagement_id': engagement_id,
                'user_email': ctx['user_email'],
                'purge_type': request.purge_type,
                'retention_days': request.retention_days,
                'correlation_id': correlation_id
            }
        )
        
        # Initiate data purge
        purge_response = await gdpr_service.initiate_data_purge(
            request=request,
            user_email=ctx["user_email"],
            correlation_id=correlation_id
        )
        
        return purge_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"GDPR data purge failed: {str(e)}",
            extra={
                'engagement_id': engagement_id,
                'user_email': ctx.get('user_email'),
                'correlation_id': correlation_id,
                'error': str(e)
            }
        )
        raise HTTPException(500, f"Data purge failed: {str(e)}")


# Background Job Management Endpoints
@router.get("/admin/jobs", response_model=BackgroundJobListResponse)
async def list_background_jobs(
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    engagement_id: Optional[str] = Query(None, description="Filter by engagement ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    services: Dict = Depends(get_services)
) -> BackgroundJobListResponse:
    """
    List background jobs (Admin only)
    
    Returns paginated list of background jobs with optional filtering.
    Useful for monitoring GDPR operations and system maintenance.
    
    **Required Role:** Admin
    """
    try:
        ctx = services["ctx"]
        repository = services["repository"]
        background_job_service = services["background_job_service"]
        correlation_id = services["correlation_id"]
        
        # Require Admin role
        require_admin(repository, ctx)
        
        logger.info(
            "Background jobs list requested",
            extra={
                'user_email': ctx['user_email'],
                'job_type': job_type,
                'status': status,
                'page': page,
                'correlation_id': correlation_id
            }
        )
        
        # List background jobs
        jobs_response = await background_job_service.list_jobs(
            user_email=None,  # Admin can see all jobs
            engagement_id=engagement_id,
            job_type=job_type,
            status=status,
            page=page,
            page_size=page_size
        )
        
        return jobs_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to list background jobs: {str(e)}",
            extra={
                'user_email': ctx.get('user_email'),
                'correlation_id': correlation_id,
                'error': str(e)
            }
        )
        raise HTTPException(500, f"Failed to list jobs: {str(e)}")


@router.post("/admin/cleanup", response_model=dict)
async def trigger_manual_cleanup(
    cleanup_type: str = Query(..., description="Type of cleanup: ttl, jobs, audit"),
    services: Dict = Depends(get_services)
) -> dict:
    """
    Trigger manual cleanup operations (Admin only)
    
    Initiates various cleanup operations:
    - **ttl:** TTL-based data cleanup
    - **jobs:** Completed job cleanup
    - **audit:** Audit log retention cleanup
    
    **Required Role:** Admin
    """
    try:
        ctx = services["ctx"]
        repository = services["repository"]
        background_job_service = services["background_job_service"]
        audit_service = services["audit_service"]
        correlation_id = services["correlation_id"]
        
        # Require Admin role
        require_admin(repository, ctx)
        
        logger.info(
            f"Manual cleanup triggered: {cleanup_type}",
            extra={
                'user_email': ctx['user_email'],
                'cleanup_type': cleanup_type,
                'correlation_id': correlation_id
            }
        )
        
        result = {}
        
        if cleanup_type == "ttl":
            # Create TTL cleanup job
            job = await background_job_service.create_job(
                job_type="ttl_cleanup",
                created_by=ctx["user_email"],
                parameters={"cleanup_type": "manual", "correlation_id": correlation_id}
            )
            result = {"job_id": job.id, "status": "cleanup_job_created"}
            
        elif cleanup_type == "jobs":
            # Clean up completed jobs
            cleanup_result = await background_job_service.cleanup_completed_jobs()
            result = cleanup_result
            
        elif cleanup_type == "audit":
            # Create audit retention job
            job = await background_job_service.create_job(
                job_type="audit_retention",
                created_by=ctx["user_email"],
                parameters={"retention_years": 7, "correlation_id": correlation_id}
            )
            result = {"job_id": job.id, "status": "audit_cleanup_job_created"}
            
        else:
            raise HTTPException(400, f"Unknown cleanup type: {cleanup_type}")
        
        return {"cleanup_type": cleanup_type, "result": result}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Manual cleanup failed: {str(e)}",
            extra={
                'user_email': ctx.get('user_email'),
                'cleanup_type': cleanup_type,
                'correlation_id': correlation_id,
                'error': str(e)
            }
        )
        raise HTTPException(500, f"Cleanup failed: {str(e)}")


# TTL Policy Management Endpoints
@router.get("/admin/ttl-policies", response_model=TTLPolicyResponse)
async def get_ttl_policies(
    services: Dict = Depends(get_services)
) -> TTLPolicyResponse:
    """
    Get TTL policies (Admin only)
    
    Returns current TTL policies for different data types.
    
    **Required Role:** Admin
    """
    try:
        ctx = services["ctx"]
        repository = services["repository"]
        gdpr_service = services["gdpr_service"]
        
        # Require Admin role
        require_admin(repository, ctx)
        
        policies_response = await gdpr_service.get_ttl_policies()
        return policies_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get TTL policies: {str(e)}",
            extra={'error': str(e)}
        )
        raise HTTPException(500, f"Failed to get TTL policies: {str(e)}")


@router.put("/admin/ttl-policies/{resource_type}", response_model=TTLPolicy)
async def update_ttl_policy(
    resource_type: str,
    ttl_seconds: int = Query(..., description="TTL in seconds"),
    description: str = Query(..., description="Policy description"),
    enabled: bool = Query(True, description="Enable/disable policy"),
    services: Dict = Depends(get_services)
) -> TTLPolicy:
    """
    Update TTL policy (Admin only)
    
    Updates TTL policy for a specific resource type.
    
    **Required Role:** Admin
    """
    try:
        ctx = services["ctx"]
        repository = services["repository"]
        gdpr_service = services["gdpr_service"]
        correlation_id = services["correlation_id"]
        
        # Require Admin role
        require_admin(repository, ctx)
        
        policy = await gdpr_service.update_ttl_policy(
            resource_type=resource_type,
            ttl_seconds=ttl_seconds,
            description=description,
            enabled=enabled,
            user_email=ctx["user_email"],
            correlation_id=correlation_id
        )
        
        return policy
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to update TTL policy: {str(e)}",
            extra={
                'resource_type': resource_type,
                'ttl_seconds': ttl_seconds,
                'error': str(e)
            }
        )
        raise HTTPException(500, f"Failed to update TTL policy: {str(e)}")


# Reporting and Dashboard Endpoints
@router.get("/admin/retention-report", response_model=DataRetentionReportResponse)
async def generate_retention_report(
    services: Dict = Depends(get_services)
) -> DataRetentionReportResponse:
    """
    Generate data retention report (Admin only)
    
    Generates comprehensive report on data retention and cleanup status.
    
    **Required Role:** Admin
    """
    try:
        ctx = services["ctx"]
        repository = services["repository"]
        gdpr_service = services["gdpr_service"]
        correlation_id = services["correlation_id"]
        
        # Require Admin role
        require_admin(repository, ctx)
        
        report_response = await gdpr_service.generate_retention_report(
            user_email=ctx["user_email"],
            correlation_id=correlation_id
        )
        
        return report_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to generate retention report: {str(e)}",
            extra={'error': str(e)}
        )
        raise HTTPException(500, f"Failed to generate retention report: {str(e)}")


@router.get("/admin/dashboard", response_model=GDPRDashboardResponse)
async def get_gdpr_dashboard(
    services: Dict = Depends(get_services)
) -> GDPRDashboardResponse:
    """
    Get GDPR admin dashboard (Admin only)
    
    Returns comprehensive dashboard with GDPR statistics, recent activity,
    and system health information.
    
    **Required Role:** Admin
    """
    try:
        ctx = services["ctx"]
        repository = services["repository"]
        gdpr_service = services["gdpr_service"]
        correlation_id = services["correlation_id"]
        
        # Require Admin role
        require_admin(repository, ctx)
        
        dashboard_response = await gdpr_service.get_gdpr_dashboard_stats(
            user_email=ctx["user_email"],
            correlation_id=correlation_id
        )
        
        return dashboard_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get GDPR dashboard: {str(e)}",
            extra={'error': str(e)}
        )
        raise HTTPException(500, f"Failed to get GDPR dashboard: {str(e)}")


# Audit Log Endpoints
@router.get("/admin/audit-logs", response_model=AuditLogResponse)
async def get_audit_logs(
    engagement_id: Optional[str] = Query(None, description="Filter by engagement ID"),
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    action_type: Optional[AuditActionType] = Query(None, description="Filter by action type"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=500, description="Page size"),
    services: Dict = Depends(get_services)
) -> AuditLogResponse:
    """
    Get audit logs (Admin only)
    
    Returns paginated audit logs with filtering capabilities.
    Essential for GDPR compliance monitoring and investigation.
    
    **Required Role:** Admin
    """
    try:
        ctx = services["ctx"]
        repository = services["repository"]
        audit_service = services["audit_service"]
        correlation_id = services["correlation_id"]
        
        # Require Admin role
        require_admin(repository, ctx)
        
        logger.info(
            "Audit logs requested",
            extra={
                'user_email': ctx['user_email'],
                'filter_engagement_id': engagement_id,
                'filter_user_email': user_email,
                'filter_action_type': action_type,
                'page': page,
                'correlation_id': correlation_id
            }
        )
        
        audit_response = await audit_service.get_audit_logs(
            engagement_id=engagement_id,
            user_email=user_email,
            action_type=action_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size
        )
        
        return audit_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get audit logs: {str(e)}",
            extra={
                'user_email': ctx.get('user_email'),
                'correlation_id': correlation_id,
                'error': str(e)
            }
        )
        raise HTTPException(500, f"Failed to get audit logs: {str(e)}")