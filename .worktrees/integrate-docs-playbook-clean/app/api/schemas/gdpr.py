"""
GDPR Data Governance Schemas

Provides comprehensive data models for GDPR compliance including:
- Data export requests and responses
- Data purge operations
- Background job management
- Audit logging for compliance tracking
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid


# GDPR Data Export Models
class GDPRDataExportRequest(BaseModel):
    """Request model for GDPR data export"""
    engagement_id: str
    include_documents: bool = Field(default=True, description="Include document metadata in export")
    include_embeddings: bool = Field(default=False, description="Include vector embeddings in export")
    export_format: Literal["json", "csv"] = Field(default="json", description="Export format")


class GDPRDataBundle(BaseModel):
    """Complete data bundle for GDPR export"""
    engagement: Dict[str, Any]
    assessments: List[Dict[str, Any]]
    questions: List[Dict[str, Any]]
    responses: List[Dict[str, Any]]
    findings: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    documents: List[Dict[str, Any]]
    runlogs: List[Dict[str, Any]]
    memberships: List[Dict[str, Any]]
    embeddings: Optional[List[Dict[str, Any]]] = None


class GDPRDataExportResponse(BaseModel):
    """Response model for GDPR data export"""
    export_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    engagement_id: str
    requested_by: str
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Literal["pending", "processing", "completed", "failed"] = "completed"
    data_bundle: Optional[GDPRDataBundle] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    size_bytes: Optional[int] = None
    record_count: int = 0
    error_message: Optional[str] = None


# GDPR Data Purge Models
class GDPRDataPurgeRequest(BaseModel):
    """Request model for GDPR data purge"""
    engagement_id: str
    purge_type: Literal["soft_delete", "hard_delete"] = Field(default="soft_delete")
    retention_days: int = Field(default=30, description="Days to retain soft-deleted data")
    confirm_purge: bool = Field(default=False, description="Confirmation flag for destructive operations")


class GDPRDataPurgeResponse(BaseModel):
    """Response model for GDPR data purge"""
    purge_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    engagement_id: str
    requested_by: str
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    purge_type: Literal["soft_delete", "hard_delete"]
    status: Literal["pending", "processing", "completed", "failed"] = "pending"
    scheduled_deletion: Optional[datetime] = None
    records_affected: int = 0
    job_id: Optional[str] = None
    error_message: Optional[str] = None


# Background Job Models
JobType = Literal["data_export", "data_purge", "ttl_cleanup", "audit_retention"]
JobStatus = Literal["pending", "processing", "completed", "failed", "cancelled"]


class BackgroundJob(BaseModel):
    """Background job model for async operations"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_type: JobType
    status: JobStatus = "pending"
    engagement_id: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_heartbeat: Optional[datetime] = None
    
    # Job configuration
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    # Progress tracking
    progress_percent: int = Field(default=0, ge=0, le=100)
    progress_message: Optional[str] = None
    
    # Results and errors
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # TTL for job cleanup
    ttl: Optional[int] = Field(default=7776000, description="TTL in seconds (default 90 days)")


class BackgroundJobResponse(BaseModel):
    """Response model for background job operations"""
    job: BackgroundJob
    estimated_duration_minutes: Optional[int] = None


class BackgroundJobListResponse(BaseModel):
    """Response model for listing background jobs"""
    jobs: List[BackgroundJob]
    total_count: int
    page: int = 1
    page_size: int = 50
    has_more: bool = False


# Audit Log Models
AuditActionType = Literal[
    "data_export_requested", "data_export_completed", "data_export_failed",
    "data_purge_requested", "data_purge_completed", "data_purge_failed",
    "data_access", "data_modification", "user_authentication",
    "admin_action", "system_maintenance"
]


class AuditLogEntry(BaseModel):
    """Audit log entry for GDPR compliance tracking"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action_type: AuditActionType
    user_email: str
    engagement_id: Optional[str] = None
    resource_type: Optional[str] = None  # "engagement", "assessment", "document", etc.
    resource_id: Optional[str] = None
    
    # Action details
    action_description: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    correlation_id: Optional[str] = None
    
    # GDPR-specific fields
    data_subject_email: Optional[str] = None  # For data subject requests
    legal_basis: Optional[str] = None  # Legal basis for processing
    retention_period: Optional[int] = None  # Retention period in days
    
    # Metadata and context
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Digital signature for integrity
    signature: Optional[str] = None
    
    # TTL for audit log retention (7 years for GDPR compliance)
    ttl: Optional[int] = Field(default=220752000, description="TTL in seconds (default 7 years)")


class AuditLogResponse(BaseModel):
    """Response model for audit log queries"""
    entries: List[AuditLogEntry]
    total_count: int
    page: int = 1
    page_size: int = 100
    has_more: bool = False


# TTL Configuration Models
class TTLPolicy(BaseModel):
    """TTL policy configuration for different data types"""
    resource_type: str  # "runlog", "temp_file", "job", "audit", etc.
    ttl_seconds: int
    description: str
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TTLPolicyResponse(BaseModel):
    """Response model for TTL policy operations"""
    policies: List[TTLPolicy]


# Data Retention and Cleanup Models
class DataRetentionReport(BaseModel):
    """Report on data retention and cleanup operations"""
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    generated_by: str
    
    # Retention statistics
    total_records_reviewed: int = 0
    records_eligible_for_cleanup: int = 0
    records_cleaned_up: int = 0
    storage_freed_bytes: int = 0
    
    # Breakdown by resource type
    cleanup_summary: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    
    # Errors and warnings
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class DataRetentionReportResponse(BaseModel):
    """Response model for data retention reports"""
    report: DataRetentionReport
    next_cleanup_scheduled: Optional[datetime] = None


# GDPR Admin Dashboard Models
class GDPRDashboardStats(BaseModel):
    """GDPR dashboard statistics"""
    total_engagements: int = 0
    total_data_exports: int = 0
    total_data_purges: int = 0
    active_background_jobs: int = 0
    
    # Recent activity (last 30 days)
    recent_exports: int = 0
    recent_purges: int = 0
    recent_audit_entries: int = 0
    
    # Storage statistics
    total_storage_bytes: int = 0
    storage_by_type: Dict[str, int] = Field(default_factory=dict)
    
    # Compliance metrics
    average_export_time_minutes: Optional[float] = None
    oldest_data_retention_days: Optional[int] = None
    
    # System health
    failed_jobs_last_24h: int = 0
    system_status: Literal["healthy", "degraded", "critical"] = "healthy"


class GDPRDashboardResponse(BaseModel):
    """Response model for GDPR admin dashboard"""
    stats: GDPRDashboardStats
    recent_jobs: List[BackgroundJob] = Field(default_factory=list)
    recent_audit_entries: List[AuditLogEntry] = Field(default_factory=list)
    active_ttl_policies: List[TTLPolicy] = Field(default_factory=list)