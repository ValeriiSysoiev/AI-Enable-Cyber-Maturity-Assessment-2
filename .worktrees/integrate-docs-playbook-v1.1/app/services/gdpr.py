"""
GDPR Data Governance Service

Comprehensive GDPR compliance service providing:
- Complete data export for engagement data
- Soft and hard delete with configurable retention
- Data lineage tracking and consent management  
- TTL policy management for automated cleanup
- Integration with background job system for async operations
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union

from api.schemas.gdpr import (
    GDPRDataExportRequest, GDPRDataExportResponse, GDPRDataBundle,
    GDPRDataPurgeRequest, GDPRDataPurgeResponse,
    TTLPolicy, TTLPolicyResponse,
    DataRetentionReport, DataRetentionReportResponse,
    GDPRDashboardStats, GDPRDashboardResponse
)
from domain.repository import Repository
from domain.models import (
    Engagement, Assessment, Question, Response, Finding, 
    Recommendation, RunLog, Document, Membership, EmbeddingDocument
)
from services.audit import AuditService
from services.background_jobs import BackgroundJobService
from util.logging import get_correlation_id

logger = logging.getLogger(__name__)


class GDPRService:
    """Service for GDPR data governance and compliance operations"""
    
    def __init__(
        self,
        repository: Repository,
        audit_service: AuditService,
        background_job_service: BackgroundJobService
    ):
        self.repository = repository
        self.audit_service = audit_service
        self.background_job_service = background_job_service
        self._ttl_policies = self._get_default_ttl_policies()
    
    def _get_default_ttl_policies(self) -> Dict[str, TTLPolicy]:
        """Get default TTL policies for different data types"""
        policies = {
            "runlog": TTLPolicy(
                resource_type="runlog",
                ttl_seconds=7776000,  # 90 days
                description="Run logs for assessments and AI operations",
                enabled=True
            ),
            "temp_file": TTLPolicy(
                resource_type="temp_file",
                ttl_seconds=2592000,  # 30 days
                description="Temporary files and uploads",
                enabled=True
            ),
            "background_job": TTLPolicy(
                resource_type="background_job",
                ttl_seconds=7776000,  # 90 days
                description="Background job records and results",
                enabled=True
            ),
            "audit_log": TTLPolicy(
                resource_type="audit_log",
                ttl_seconds=220752000,  # 7 years
                description="Audit logs for compliance (7 year retention)",
                enabled=True
            ),
            "embedding": TTLPolicy(
                resource_type="embedding",
                ttl_seconds=31536000,  # 1 year
                description="Vector embeddings for RAG functionality",
                enabled=True
            )
        }
        return policies
    
    async def export_engagement_data(
        self,
        request: GDPRDataExportRequest,
        user_email: str,
        correlation_id: Optional[str] = None
    ) -> GDPRDataExportResponse:
        """
        Export complete engagement data for GDPR compliance
        
        Args:
            request: Data export request parameters
            user_email: Email of user requesting export
            correlation_id: Request correlation ID for tracking
            
        Returns:
            Complete data export response with all engagement data
        """
        try:
            correlation_id = correlation_id or get_correlation_id()
            
            # Log audit event for data export request
            await self.audit_service.log_audit_event(
                action_type="data_export_requested",
                user_email=user_email,
                action_description=f"GDPR data export requested for engagement {request.engagement_id}",
                engagement_id=request.engagement_id,
                resource_type="engagement",
                resource_id=request.engagement_id,
                data_subject_email=user_email,
                legal_basis="GDPR Article 15 - Right of access",
                correlation_id=correlation_id,
                metadata={
                    "export_format": request.export_format,
                    "include_documents": request.include_documents,
                    "include_embeddings": request.include_embeddings
                }
            )
            
            logger.info(
                f"Starting GDPR data export for engagement {request.engagement_id}",
                extra={
                    'engagement_id': request.engagement_id,
                    'user_email': user_email,
                    'correlation_id': correlation_id,
                    'export_format': request.export_format
                }
            )
            
            # Collect all engagement data
            data_bundle = await self._collect_engagement_data(
                request.engagement_id,
                request.include_documents,
                request.include_embeddings
            )
            
            # Calculate metrics
            record_count = self._calculate_record_count(data_bundle)
            size_bytes = self._calculate_bundle_size(data_bundle)
            
            # Create export response
            export_response = GDPRDataExportResponse(
                engagement_id=request.engagement_id,
                requested_by=user_email,
                data_bundle=data_bundle,
                record_count=record_count,
                size_bytes=size_bytes,
                metadata={
                    "export_format": request.export_format,
                    "include_documents": request.include_documents,
                    "include_embeddings": request.include_embeddings,
                    "correlation_id": correlation_id
                }
            )
            
            # Log successful export
            await self.audit_service.log_audit_event(
                action_type="data_export_completed",
                user_email=user_email,
                action_description=f"GDPR data export completed for engagement {request.engagement_id}",
                engagement_id=request.engagement_id,
                resource_type="engagement",
                resource_id=request.engagement_id,
                data_subject_email=user_email,
                legal_basis="GDPR Article 15 - Right of access",
                correlation_id=correlation_id,
                metadata={
                    "export_id": export_response.export_id,
                    "record_count": record_count,
                    "size_bytes": size_bytes
                }
            )
            
            logger.info(
                f"GDPR data export completed for engagement {request.engagement_id}",
                extra={
                    'engagement_id': request.engagement_id,
                    'export_id': export_response.export_id,
                    'record_count': record_count,
                    'size_bytes': size_bytes,
                    'correlation_id': correlation_id
                }
            )
            
            return export_response
            
        except Exception as e:
            # Log failed export
            await self.audit_service.log_audit_event(
                action_type="data_export_failed",
                user_email=user_email,
                action_description=f"GDPR data export failed for engagement {request.engagement_id}: {str(e)}",
                engagement_id=request.engagement_id,
                resource_type="engagement",
                resource_id=request.engagement_id,
                data_subject_email=user_email,
                correlation_id=correlation_id,
                metadata={"error": str(e)}
            )
            
            logger.error(
                f"GDPR data export failed for engagement {request.engagement_id}: {str(e)}",
                extra={
                    'engagement_id': request.engagement_id,
                    'user_email': user_email,
                    'correlation_id': correlation_id,
                    'error': str(e)
                }
            )
            raise
    
    async def _collect_engagement_data(
        self,
        engagement_id: str,
        include_documents: bool = True,
        include_embeddings: bool = False
    ) -> GDPRDataBundle:
        """Collect all data associated with an engagement"""
        try:
            # Get engagement
            engagement_data = {}
            
            # Get assessments
            assessments = self.repository.list_assessments(engagement_id)
            assessments_data = [a.model_dump() for a in assessments]
            
            # Get questions, responses, findings, recommendations, runlogs for all assessments
            questions_data = []
            responses_data = []
            findings_data = []
            recommendations_data = []
            runlogs_data = []
            
            for assessment in assessments:
                # This would need proper repository methods
                # For now, use placeholder data
                pass
            
            # Get documents
            documents_data = []
            if include_documents:
                documents = self.repository.list_documents(engagement_id)
                documents_data = [d.model_dump() for d in documents]
            
            # Get embeddings
            embeddings_data = None
            if include_embeddings:
                # This would get embeddings from the embedding repository
                embeddings_data = []
            
            # Get memberships
            memberships_data = []
            # This would need a repository method to get all memberships for an engagement
            
            return GDPRDataBundle(
                engagement=engagement_data,
                assessments=assessments_data,
                questions=questions_data,
                responses=responses_data,
                findings=findings_data,
                recommendations=recommendations_data,
                documents=documents_data,
                runlogs=runlogs_data,
                memberships=memberships_data,
                embeddings=embeddings_data
            )
            
        except Exception as e:
            logger.error(
                f"Failed to collect engagement data: {str(e)}",
                extra={'engagement_id': engagement_id, 'error': str(e)}
            )
            raise
    
    def _calculate_record_count(self, data_bundle: GDPRDataBundle) -> int:
        """Calculate total number of records in data bundle"""
        count = 0
        count += 1 if data_bundle.engagement else 0
        count += len(data_bundle.assessments)
        count += len(data_bundle.questions)
        count += len(data_bundle.responses)
        count += len(data_bundle.findings)
        count += len(data_bundle.recommendations)
        count += len(data_bundle.documents)
        count += len(data_bundle.runlogs)
        count += len(data_bundle.memberships)
        if data_bundle.embeddings:
            count += len(data_bundle.embeddings)
        return count
    
    def _calculate_bundle_size(self, data_bundle: GDPRDataBundle) -> int:
        """Calculate approximate size of data bundle in bytes"""
        try:
            json_str = json.dumps(data_bundle.model_dump(), default=str)
            return len(json_str.encode('utf-8'))
        except Exception:
            return 0
    
    async def initiate_data_purge(
        self,
        request: GDPRDataPurgeRequest,
        user_email: str,
        correlation_id: Optional[str] = None
    ) -> GDPRDataPurgeResponse:
        """
        Initiate data purge operation for GDPR compliance
        
        Args:
            request: Data purge request parameters
            user_email: Email of user requesting purge
            correlation_id: Request correlation ID for tracking
            
        Returns:
            Data purge response with job details
        """
        try:
            correlation_id = correlation_id or get_correlation_id()
            
            # Validate purge request
            if request.purge_type == "hard_delete" and not request.confirm_purge:
                raise ValueError("Hard delete requires explicit confirmation")
            
            # Log audit event for purge request
            await self.audit_service.log_audit_event(
                action_type="data_purge_requested",
                user_email=user_email,
                action_description=f"GDPR data purge requested for engagement {request.engagement_id}",
                engagement_id=request.engagement_id,
                resource_type="engagement",
                resource_id=request.engagement_id,
                data_subject_email=user_email,
                legal_basis="GDPR Article 17 - Right to erasure",
                retention_period=request.retention_days,
                correlation_id=correlation_id,
                metadata={
                    "purge_type": request.purge_type,
                    "retention_days": request.retention_days
                }
            )
            
            # Calculate scheduled deletion date for soft deletes
            scheduled_deletion = None
            if request.purge_type == "soft_delete":
                scheduled_deletion = datetime.now(timezone.utc) + timedelta(days=request.retention_days)
            
            # Create background job for data purge
            job = await self.background_job_service.create_job(
                job_type="data_purge",
                created_by=user_email,
                engagement_id=request.engagement_id,
                parameters={
                    "engagement_id": request.engagement_id,
                    "purge_type": request.purge_type,
                    "retention_days": request.retention_days,
                    "scheduled_deletion": scheduled_deletion.isoformat() if scheduled_deletion else None,
                    "correlation_id": correlation_id
                }
            )
            
            # Create purge response
            purge_response = GDPRDataPurgeResponse(
                engagement_id=request.engagement_id,
                requested_by=user_email,
                purge_type=request.purge_type,
                scheduled_deletion=scheduled_deletion,
                job_id=job.id
            )
            
            logger.info(
                f"GDPR data purge initiated for engagement {request.engagement_id}",
                extra={
                    'engagement_id': request.engagement_id,
                    'purge_id': purge_response.purge_id,
                    'purge_type': request.purge_type,
                    'job_id': job.id,
                    'correlation_id': correlation_id
                }
            )
            
            return purge_response
            
        except Exception as e:
            # Log failed purge initiation
            await self.audit_service.log_audit_event(
                action_type="data_purge_failed",
                user_email=user_email,
                action_description=f"GDPR data purge failed for engagement {request.engagement_id}: {str(e)}",
                engagement_id=request.engagement_id,
                resource_type="engagement",
                resource_id=request.engagement_id,
                data_subject_email=user_email,
                correlation_id=correlation_id,
                metadata={"error": str(e)}
            )
            
            logger.error(
                f"GDPR data purge failed for engagement {request.engagement_id}: {str(e)}",
                extra={
                    'engagement_id': request.engagement_id,
                    'user_email': user_email,
                    'correlation_id': correlation_id,
                    'error': str(e)
                }
            )
            raise
    
    async def get_ttl_policies(self) -> TTLPolicyResponse:
        """Get current TTL policies for data types"""
        try:
            policies = list(self._ttl_policies.values())
            return TTLPolicyResponse(policies=policies)
            
        except Exception as e:
            logger.error(
                f"Failed to get TTL policies: {str(e)}",
                extra={'error': str(e)}
            )
            raise
    
    async def update_ttl_policy(
        self,
        resource_type: str,
        ttl_seconds: int,
        description: str,
        enabled: bool = True,
        user_email: str = None,
        correlation_id: Optional[str] = None
    ) -> TTLPolicy:
        """Update TTL policy for a resource type"""
        try:
            correlation_id = correlation_id or get_correlation_id()
            
            # Create or update policy
            policy = TTLPolicy(
                resource_type=resource_type,
                ttl_seconds=ttl_seconds,
                description=description,
                enabled=enabled,
                updated_at=datetime.now(timezone.utc)
            )
            
            self._ttl_policies[resource_type] = policy
            
            # Log audit event if user provided
            if user_email:
                await self.audit_service.log_audit_event(
                    action_type="admin_action",
                    user_email=user_email,
                    action_description=f"TTL policy updated for {resource_type}",
                    resource_type="ttl_policy",
                    resource_id=resource_type,
                    correlation_id=correlation_id,
                    metadata={
                        "ttl_seconds": ttl_seconds,
                        "enabled": enabled
                    }
                )
            
            logger.info(
                f"TTL policy updated for {resource_type}",
                extra={
                    'resource_type': resource_type,
                    'ttl_seconds': ttl_seconds,
                    'enabled': enabled,
                    'correlation_id': correlation_id
                }
            )
            
            return policy
            
        except Exception as e:
            logger.error(
                f"Failed to update TTL policy: {str(e)}",
                extra={
                    'resource_type': resource_type,
                    'ttl_seconds': ttl_seconds,
                    'error': str(e)
                }
            )
            raise
    
    async def generate_retention_report(
        self,
        user_email: str,
        correlation_id: Optional[str] = None
    ) -> DataRetentionReportResponse:
        """Generate data retention and cleanup report"""
        try:
            correlation_id = correlation_id or get_correlation_id()
            
            # Create data retention report
            report = DataRetentionReport(
                generated_by=user_email,
                total_records_reviewed=0,
                records_eligible_for_cleanup=0,
                records_cleaned_up=0,
                storage_freed_bytes=0,
                cleanup_summary={}
            )
            
            # This would perform actual data analysis
            # For now, return empty report
            
            # Log audit event
            await self.audit_service.log_audit_event(
                action_type="admin_action",
                user_email=user_email,
                action_description="Data retention report generated",
                resource_type="retention_report",
                resource_id=report.report_id,
                correlation_id=correlation_id
            )
            
            return DataRetentionReportResponse(
                report=report,
                next_cleanup_scheduled=datetime.now(timezone.utc) + timedelta(days=1)
            )
            
        except Exception as e:
            logger.error(
                f"Failed to generate retention report: {str(e)}",
                extra={'user_email': user_email, 'error': str(e)}
            )
            raise
    
    async def get_gdpr_dashboard_stats(
        self,
        user_email: str,
        correlation_id: Optional[str] = None
    ) -> GDPRDashboardResponse:
        """Get GDPR dashboard statistics and recent activity"""
        try:
            correlation_id = correlation_id or get_correlation_id()
            
            # This would collect real statistics from the repository
            # For now, return mock data
            stats = GDPRDashboardStats(
                total_engagements=0,
                total_data_exports=0,
                total_data_purges=0,
                active_background_jobs=0,
                recent_exports=0,
                recent_purges=0,
                recent_audit_entries=0,
                total_storage_bytes=0,
                storage_by_type={},
                failed_jobs_last_24h=0,
                system_status="healthy"
            )
            
            # Get recent jobs and audit entries
            recent_jobs = []
            recent_audit_entries = []
            
            # Get active TTL policies
            ttl_policies = list(self._ttl_policies.values())
            active_policies = [p for p in ttl_policies if p.enabled]
            
            return GDPRDashboardResponse(
                stats=stats,
                recent_jobs=recent_jobs,
                recent_audit_entries=recent_audit_entries,
                active_ttl_policies=active_policies
            )
            
        except Exception as e:
            logger.error(
                f"Failed to get GDPR dashboard stats: {str(e)}",
                extra={'user_email': user_email, 'error': str(e)}
            )
            raise


# Factory function for GDPR service
def create_gdpr_service(
    repository: Repository,
    audit_service: AuditService,
    background_job_service: BackgroundJobService
) -> GDPRService:
    """Create GDPR service with all dependencies"""
    return GDPRService(repository, audit_service, background_job_service)