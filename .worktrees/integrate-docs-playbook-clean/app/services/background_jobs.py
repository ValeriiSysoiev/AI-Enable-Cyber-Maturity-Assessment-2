"""
Background Job System for GDPR Operations

Provides async job processing for:
- Data export operations
- Data purge operations
- TTL cleanup tasks
- Audit log retention
- System maintenance

Uses Cosmos DB as task store for simplicity and consistency.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from api.schemas.gdpr import BackgroundJob, JobType, JobStatus, BackgroundJobResponse, BackgroundJobListResponse
from domain.repository import Repository
from services.audit import AuditService
from util.logging import get_correlation_id

logger = logging.getLogger(__name__)


class JobExecutionError(Exception):
    """Exception raised during job execution"""
    pass


class BackgroundJobService:
    """Service for managing background jobs and async task processing"""
    
    def __init__(self, repository: Repository, audit_service: AuditService):
        self.repository = repository
        self.audit_service = audit_service
        self._job_handlers: Dict[JobType, Callable] = {}
        self._register_default_handlers()
        self._running_jobs: Dict[str, asyncio.Task] = {}
    
    def _register_default_handlers(self):
        """Register default job handlers"""
        self._job_handlers.update({
            "data_export": self._handle_data_export,
            "data_purge": self._handle_data_purge,
            "ttl_cleanup": self._handle_ttl_cleanup,
            "audit_retention": self._handle_audit_retention
        })
    
    def register_job_handler(self, job_type: JobType, handler: Callable):
        """Register a custom job handler"""
        self._job_handlers[job_type] = handler
        logger.info(f"Registered job handler for type: {job_type}")
    
    async def create_job(
        self,
        job_type: JobType,
        created_by: str,
        parameters: Dict[str, Any],
        engagement_id: Optional[str] = None,
        priority: int = 0
    ) -> BackgroundJob:
        """
        Create a new background job
        
        Args:
            job_type: Type of job to create
            created_by: Email of user creating the job
            parameters: Job-specific parameters
            engagement_id: Optional engagement ID for scoped jobs
            priority: Job priority (higher numbers = higher priority)
            
        Returns:
            Created background job
        """
        try:
            job = BackgroundJob(
                job_type=job_type,
                created_by=created_by.lower().strip(),
                engagement_id=engagement_id,
                parameters=parameters
            )
            
            # Set TTL based on job type
            job.ttl = self._get_job_ttl(job_type)
            
            # Store job (would be implemented in repository)
            stored_job = await self._store_job(job)
            
            # Log audit event
            await self.audit_service.log_audit_event(
                action_type="admin_action",
                user_email=created_by,
                action_description=f"Background job created: {job_type}",
                engagement_id=engagement_id,
                resource_type="background_job",
                resource_id=job.id,
                metadata={"job_type": job_type, "parameters": parameters}
            )
            
            logger.info(
                f"Background job created: {job_type}",
                extra={
                    'job_id': job.id,
                    'job_type': job_type,
                    'created_by': created_by,
                    'engagement_id': engagement_id
                }
            )
            
            return stored_job
            
        except Exception as e:
            logger.error(
                f"Failed to create background job: {str(e)}",
                extra={
                    'job_type': job_type,
                    'created_by': created_by,
                    'engagement_id': engagement_id,
                    'error': str(e)
                }
            )
            raise
    
    def _get_job_ttl(self, job_type: JobType) -> int:
        """Get TTL for job based on type"""
        ttl_mapping = {
            "data_export": 2592000,    # 30 days
            "data_purge": 7776000,     # 90 days
            "ttl_cleanup": 604800,     # 7 days
            "audit_retention": 604800  # 7 days
        }
        return ttl_mapping.get(job_type, 2592000)
    
    async def _store_job(self, job: BackgroundJob) -> BackgroundJob:
        """Store job in repository"""
        # This would be implemented as a repository method
        # For now, just return the job
        return job
    
    async def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        """Get job by ID"""
        # This would be implemented as a repository method
        return None
    
    async def list_jobs(
        self,
        user_email: Optional[str] = None,
        engagement_id: Optional[str] = None,
        job_type: Optional[JobType] = None,
        status: Optional[JobStatus] = None,
        page: int = 1,
        page_size: int = 50
    ) -> BackgroundJobListResponse:
        """
        List background jobs with filtering and pagination
        
        Args:
            user_email: Filter by creator email
            engagement_id: Filter by engagement ID
            job_type: Filter by job type
            status: Filter by job status
            page: Page number
            page_size: Number of jobs per page
            
        Returns:
            Paginated job list response
        """
        try:
            # This would be implemented as a repository method
            jobs: List[BackgroundJob] = []
            total_count = 0
            
            has_more = total_count > (page * page_size)
            
            return BackgroundJobListResponse(
                jobs=jobs,
                total_count=total_count,
                page=page,
                page_size=page_size,
                has_more=has_more
            )
            
        except Exception as e:
            logger.error(
                f"Failed to list background jobs: {str(e)}",
                extra={
                    'user_email': user_email,
                    'engagement_id': engagement_id,
                    'job_type': job_type,
                    'status': status,
                    'error': str(e)
                }
            )
            raise
    
    async def execute_job(self, job_id: str) -> bool:
        """
        Execute a background job
        
        Args:
            job_id: ID of job to execute
            
        Returns:
            True if job was started successfully
        """
        try:
            job = await self.get_job(job_id)
            if not job:
                logger.error(f"Job not found: {job_id}")
                return False
            
            if job.status != "pending":
                logger.warning(f"Job {job_id} is not in pending status: {job.status}")
                return False
            
            # Check if job is already running
            if job_id in self._running_jobs:
                logger.warning(f"Job {job_id} is already running")
                return False
            
            # Get job handler
            handler = self._job_handlers.get(job.job_type)
            if not handler:
                logger.error(f"No handler registered for job type: {job.job_type}")
                await self._mark_job_failed(job, "No handler registered for job type")
                return False
            
            # Start job execution in background
            task = asyncio.create_task(self._execute_job_with_error_handling(job, handler))
            self._running_jobs[job_id] = task
            
            logger.info(
                f"Background job execution started: {job.job_type}",
                extra={
                    'job_id': job_id,
                    'job_type': job.job_type,
                    'created_by': job.created_by
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to execute background job: {str(e)}",
                extra={'job_id': job_id, 'error': str(e)}
            )
            return False
    
    async def _execute_job_with_error_handling(
        self,
        job: BackgroundJob,
        handler: Callable
    ):
        """Execute job with comprehensive error handling and retry logic"""
        try:
            # Mark job as processing
            await self._mark_job_processing(job)
            
            # Execute the job handler
            result = await handler(job)
            
            # Mark job as completed
            await self._mark_job_completed(job, result)
            
        except Exception as e:
            logger.error(
                f"Job execution failed: {str(e)}",
                extra={
                    'job_id': job.id,
                    'job_type': job.job_type,
                    'retry_count': job.retry_count,
                    'error': str(e)
                }
            )
            
            # Handle retry logic
            if job.retry_count < job.max_retries:
                await self._schedule_retry(job, str(e))
            else:
                await self._mark_job_failed(job, str(e))
        
        finally:
            # Remove from running jobs
            self._running_jobs.pop(job.id, None)
    
    async def _mark_job_processing(self, job: BackgroundJob):
        """Mark job as processing"""
        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        job.last_heartbeat = datetime.now(timezone.utc)
        await self._update_job(job)
    
    async def _mark_job_completed(self, job: BackgroundJob, result: Any):
        """Mark job as completed with result"""
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.progress_percent = 100
        job.result = result if isinstance(result, dict) else {"result": str(result)}
        await self._update_job(job)
        
        # Log audit event
        await self.audit_service.log_audit_event(
            action_type="admin_action",
            user_email=job.created_by,
            action_description=f"Background job completed: {job.job_type}",
            engagement_id=job.engagement_id,
            resource_type="background_job",
            resource_id=job.id,
            metadata={"job_type": job.job_type, "result": job.result}
        )
    
    async def _mark_job_failed(self, job: BackgroundJob, error_message: str):
        """Mark job as failed with error message"""
        job.status = "failed"
        job.completed_at = datetime.now(timezone.utc)
        job.error_message = error_message
        await self._update_job(job)
        
        # Log audit event
        await self.audit_service.log_audit_event(
            action_type="admin_action",
            user_email=job.created_by,
            action_description=f"Background job failed: {job.job_type}",
            engagement_id=job.engagement_id,
            resource_type="background_job",
            resource_id=job.id,
            metadata={"job_type": job.job_type, "error": error_message}
        )
    
    async def _schedule_retry(self, job: BackgroundJob, error_message: str):
        """Schedule job retry"""
        job.retry_count += 1
        job.status = "pending"
        job.error_message = f"Retry {job.retry_count}/{job.max_retries}: {error_message}"
        job.last_heartbeat = datetime.now(timezone.utc)
        await self._update_job(job)
        
        # Schedule retry after exponential backoff
        retry_delay = min(300, 30 * (2 ** job.retry_count))  # Max 5 minutes
        await asyncio.sleep(retry_delay)
        await self.execute_job(job.id)
    
    async def _update_job(self, job: BackgroundJob):
        """Update job in repository"""
        # This would be implemented as a repository method
        pass
    
    async def update_job_progress(
        self,
        job_id: str,
        progress_percent: int,
        progress_message: Optional[str] = None
    ):
        """Update job progress"""
        job = await self.get_job(job_id)
        if job:
            job.progress_percent = max(0, min(100, progress_percent))
            job.progress_message = progress_message
            job.last_heartbeat = datetime.now(timezone.utc)
            await self._update_job(job)
    
    # Job Handlers
    async def _handle_data_export(self, job: BackgroundJob) -> Dict[str, Any]:
        """Handle data export job"""
        try:
            engagement_id = job.parameters.get("engagement_id")
            export_format = job.parameters.get("export_format", "json")
            include_documents = job.parameters.get("include_documents", True)
            include_embeddings = job.parameters.get("include_embeddings", False)
            
            if not engagement_id:
                raise JobExecutionError("Missing engagement_id parameter")
            
            await self.update_job_progress(job.id, 10, "Starting data export")
            
            # This would call the GDPR service to perform the actual export
            # For now, return a mock result
            result = {
                "engagement_id": engagement_id,
                "export_format": export_format,
                "records_exported": 0,
                "export_size_bytes": 0,
                "export_completed_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.update_job_progress(job.id, 100, "Data export completed")
            
            return result
            
        except Exception as e:
            raise JobExecutionError(f"Data export failed: {str(e)}")
    
    async def _handle_data_purge(self, job: BackgroundJob) -> Dict[str, Any]:
        """Handle data purge job"""
        try:
            engagement_id = job.parameters.get("engagement_id")
            purge_type = job.parameters.get("purge_type", "soft_delete")
            
            if not engagement_id:
                raise JobExecutionError("Missing engagement_id parameter")
            
            await self.update_job_progress(job.id, 10, "Starting data purge")
            
            # This would call the GDPR service to perform the actual purge
            # For now, return a mock result
            result = {
                "engagement_id": engagement_id,
                "purge_type": purge_type,
                "records_purged": 0,
                "storage_freed_bytes": 0,
                "purge_completed_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.update_job_progress(job.id, 100, "Data purge completed")
            
            return result
            
        except Exception as e:
            raise JobExecutionError(f"Data purge failed: {str(e)}")
    
    async def _handle_ttl_cleanup(self, job: BackgroundJob) -> Dict[str, Any]:
        """Handle TTL cleanup job"""
        try:
            await self.update_job_progress(job.id, 10, "Starting TTL cleanup")
            
            # This would perform system-wide TTL cleanup
            # For now, return a mock result
            result = {
                "cleanup_type": "ttl",
                "records_cleaned": 0,
                "storage_freed_bytes": 0,
                "cleanup_completed_at": datetime.now(timezone.utc).isoformat()
            }
            
            await self.update_job_progress(job.id, 100, "TTL cleanup completed")
            
            return result
            
        except Exception as e:
            raise JobExecutionError(f"TTL cleanup failed: {str(e)}")
    
    async def _handle_audit_retention(self, job: BackgroundJob) -> Dict[str, Any]:
        """Handle audit log retention job"""
        try:
            retention_years = job.parameters.get("retention_years", 7)
            
            await self.update_job_progress(job.id, 10, "Starting audit retention cleanup")
            
            # Call audit service cleanup
            cleanup_result = await self.audit_service.cleanup_expired_audit_logs(retention_years)
            
            await self.update_job_progress(job.id, 100, "Audit retention cleanup completed")
            
            return cleanup_result
            
        except Exception as e:
            raise JobExecutionError(f"Audit retention cleanup failed: {str(e)}")
    
    async def cleanup_completed_jobs(self, max_age_days: int = 30) -> Dict[str, Any]:
        """Clean up completed jobs older than max_age_days"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            
            # This would be implemented as a repository method
            cleanup_result = {
                "cutoff_date": cutoff_date.isoformat(),
                "jobs_cleaned": 0,
                "cleanup_completed_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(
                "Completed job cleanup finished",
                extra={
                    'max_age_days': max_age_days,
                    'jobs_cleaned': cleanup_result['jobs_cleaned']
                }
            )
            
            return cleanup_result
            
        except Exception as e:
            logger.error(
                f"Failed to cleanup completed jobs: {str(e)}",
                extra={'max_age_days': max_age_days, 'error': str(e)}
            )
            raise


# Factory function for background job service
def create_background_job_service(
    repository: Repository,
    audit_service: AuditService
) -> BackgroundJobService:
    """Create background job service with dependencies"""
    return BackgroundJobService(repository, audit_service)