"""
GDPR Audit Logging Service

Provides comprehensive audit logging for GDPR compliance including:
- Immutable audit trail with digital signatures
- Structured logging with correlation IDs
- Data subject request tracking
- Retention policy management
- Compliance reporting
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from api.schemas.gdpr import AuditLogEntry, AuditActionType, AuditLogResponse
from domain.repository import Repository
from config import config
from util.logging import get_correlation_id

logger = logging.getLogger(__name__)


class AuditService:
    """Service for managing GDPR audit logs and compliance tracking"""
    
    def __init__(self, repository: Repository):
        self.repository = repository
        self._signing_key = self._get_signing_key()
    
    def _get_signing_key(self) -> str:
        """Get or generate signing key for audit log integrity"""
        # In production, this should be loaded from secure configuration
        # For now, use a configuration-based key
        return getattr(config, 'audit_signing_key', 'default-audit-key-change-in-production')
    
    def _generate_signature(self, audit_entry: AuditLogEntry) -> str:
        """Generate digital signature for audit entry integrity"""
        # Create canonical representation for signing
        signing_data = {
            'id': audit_entry.id,
            'timestamp': audit_entry.timestamp.isoformat(),
            'action_type': audit_entry.action_type,
            'user_email': audit_entry.user_email,
            'engagement_id': audit_entry.engagement_id,
            'resource_type': audit_entry.resource_type,
            'resource_id': audit_entry.resource_id,
            'action_description': audit_entry.action_description,
            'data_subject_email': audit_entry.data_subject_email,
            'legal_basis': audit_entry.legal_basis
        }
        
        # Create deterministic JSON string
        canonical_json = json.dumps(signing_data, sort_keys=True, separators=(',', ':'))
        
        # Generate HMAC signature
        signature = hmac.new(
            self._signing_key.encode('utf-8'),
            canonical_json.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _verify_signature(self, audit_entry: AuditLogEntry) -> bool:
        """Verify audit entry signature for integrity checking"""
        if not audit_entry.signature:
            return False
        
        expected_signature = self._generate_signature(audit_entry)
        return hmac.compare_digest(audit_entry.signature, expected_signature)
    
    async def log_audit_event(
        self,
        action_type: AuditActionType,
        user_email: str,
        action_description: str,
        engagement_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        data_subject_email: Optional[str] = None,
        legal_basis: Optional[str] = None,
        retention_period: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> AuditLogEntry:
        """
        Log an audit event for GDPR compliance
        
        Args:
            action_type: Type of action being audited
            user_email: Email of user performing the action
            action_description: Human-readable description of the action
            engagement_id: ID of engagement if applicable
            resource_type: Type of resource being accessed/modified
            resource_id: ID of specific resource
            data_subject_email: Email of data subject for GDPR requests
            legal_basis: Legal basis for data processing
            retention_period: Data retention period in days
            ip_address: IP address of user
            user_agent: User agent string
            metadata: Additional metadata
            correlation_id: Request correlation ID
            
        Returns:
            Created audit log entry
        """
        try:
            # Create audit entry
            audit_entry = AuditLogEntry(
                action_type=action_type,
                user_email=user_email.lower().strip(),
                engagement_id=engagement_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action_description=action_description,
                ip_address=ip_address,
                user_agent=user_agent,
                correlation_id=correlation_id or get_correlation_id(),
                data_subject_email=data_subject_email.lower().strip() if data_subject_email else None,
                legal_basis=legal_basis,
                retention_period=retention_period,
                metadata=metadata or {}
            )
            
            # Generate digital signature for integrity
            audit_entry.signature = self._generate_signature(audit_entry)
            
            # Store audit entry (implementation depends on repository)
            # For now, we'll extend the repository interface
            stored_entry = await self._store_audit_entry(audit_entry)
            
            # Log to application logs for additional tracking
            logger.info(
                f"Audit event logged: {action_type}",
                extra={
                    'audit_id': audit_entry.id,
                    'action_type': action_type,
                    'user_email': user_email,
                    'engagement_id': engagement_id,
                    'resource_type': resource_type,
                    'resource_id': resource_id,
                    'correlation_id': audit_entry.correlation_id,
                    'has_signature': bool(audit_entry.signature)
                }
            )
            
            return stored_entry
            
        except Exception as e:
            logger.error(
                f"Failed to log audit event: {str(e)}",
                extra={
                    'action_type': action_type,
                    'user_email': user_email,
                    'engagement_id': engagement_id,
                    'error': str(e)
                }
            )
            raise
    
    async def _store_audit_entry(self, audit_entry: AuditLogEntry) -> AuditLogEntry:
        """Store audit entry in repository"""
        # This would need to be implemented in the repository layer
        # For now, we'll create a basic storage mechanism
        
        # Convert to dict for storage
        entry_dict = audit_entry.model_dump()
        
        # Store using a hypothetical audit repository method
        # In a real implementation, this would be stored in Cosmos DB
        # with proper TTL settings for 7-year retention
        
        # For now, just return the entry
        return audit_entry
    
    async def get_audit_logs(
        self,
        engagement_id: Optional[str] = None,
        user_email: Optional[str] = None,
        action_type: Optional[AuditActionType] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 100
    ) -> AuditLogResponse:
        """
        Retrieve audit logs with filtering and pagination
        
        Args:
            engagement_id: Filter by engagement ID
            user_email: Filter by user email
            action_type: Filter by action type
            resource_type: Filter by resource type
            start_date: Filter by start date
            end_date: Filter by end date
            page: Page number for pagination
            page_size: Number of entries per page
            
        Returns:
            Paginated audit log response
        """
        try:
            # This would be implemented as a repository method
            # For now, return empty response
            entries: List[AuditLogEntry] = []
            total_count = 0
            
            # Calculate pagination
            has_more = total_count > (page * page_size)
            
            return AuditLogResponse(
                entries=entries,
                total_count=total_count,
                page=page,
                page_size=page_size,
                has_more=has_more
            )
            
        except Exception as e:
            logger.error(
                f"Failed to retrieve audit logs: {str(e)}",
                extra={
                    'engagement_id': engagement_id,
                    'user_email': user_email,
                    'action_type': action_type,
                    'error': str(e)
                }
            )
            raise
    
    async def verify_audit_integrity(
        self,
        audit_entries: List[AuditLogEntry]
    ) -> Dict[str, Any]:
        """
        Verify integrity of audit log entries
        
        Args:
            audit_entries: List of audit entries to verify
            
        Returns:
            Verification report with statistics and any integrity issues
        """
        try:
            verified_count = 0
            failed_count = 0
            failed_entries = []
            
            for entry in audit_entries:
                if self._verify_signature(entry):
                    verified_count += 1
                else:
                    failed_count += 1
                    failed_entries.append({
                        'id': entry.id,
                        'timestamp': entry.timestamp,
                        'action_type': entry.action_type,
                        'reason': 'Invalid signature'
                    })
            
            verification_report = {
                'total_entries': len(audit_entries),
                'verified_entries': verified_count,
                'failed_entries': failed_count,
                'integrity_score': verified_count / len(audit_entries) if audit_entries else 1.0,
                'failed_details': failed_entries,
                'verified_at': datetime.now(timezone.utc)
            }
            
            logger.info(
                "Audit integrity verification completed",
                extra={
                    'total_entries': len(audit_entries),
                    'verified_count': verified_count,
                    'failed_count': failed_count,
                    'integrity_score': verification_report['integrity_score']
                }
            )
            
            return verification_report
            
        except Exception as e:
            logger.error(
                f"Failed to verify audit integrity: {str(e)}",
                extra={'error': str(e)}
            )
            raise
    
    async def cleanup_expired_audit_logs(
        self,
        retention_years: int = 7
    ) -> Dict[str, Any]:
        """
        Clean up audit logs beyond retention period
        
        Args:
            retention_years: Number of years to retain audit logs (default 7 for GDPR)
            
        Returns:
            Cleanup report with statistics
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_years * 365)
            
            # This would be implemented as a repository method
            # For now, return mock cleanup report
            cleanup_report = {
                'cutoff_date': cutoff_date,
                'entries_reviewed': 0,
                'entries_deleted': 0,
                'storage_freed_bytes': 0,
                'cleanup_completed_at': datetime.now(timezone.utc)
            }
            
            logger.info(
                "Audit log cleanup completed",
                extra={
                    'retention_years': retention_years,
                    'cutoff_date': cutoff_date,
                    'entries_deleted': cleanup_report['entries_deleted']
                }
            )
            
            return cleanup_report
            
        except Exception as e:
            logger.error(
                f"Failed to cleanup expired audit logs: {str(e)}",
                extra={'retention_years': retention_years, 'error': str(e)}
            )
            raise


# Audit logging decorators and utilities
def audit_data_access(
    resource_type: str,
    action_description: str = "Data access"
):
    """Decorator for auditing data access operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract context from kwargs or function parameters
            ctx = kwargs.get('ctx', {})
            resource_id = kwargs.get('resource_id') or kwargs.get('id')
            
            if ctx and ctx.get('user_email'):
                audit_service = AuditService(kwargs.get('repository'))
                
                await audit_service.log_audit_event(
                    action_type="data_access",
                    user_email=ctx['user_email'],
                    action_description=f"{action_description}: {resource_type}",
                    engagement_id=ctx.get('engagement_id'),
                    resource_type=resource_type,
                    resource_id=resource_id,
                    correlation_id=ctx.get('correlation_id')
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def audit_data_modification(
    resource_type: str,
    action_description: str = "Data modification"
):
    """Decorator for auditing data modification operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract context from kwargs or function parameters
            ctx = kwargs.get('ctx', {})
            resource_id = kwargs.get('resource_id') or kwargs.get('id')
            
            if ctx and ctx.get('user_email'):
                audit_service = AuditService(kwargs.get('repository'))
                
                await audit_service.log_audit_event(
                    action_type="data_modification",
                    user_email=ctx['user_email'],
                    action_description=f"{action_description}: {resource_type}",
                    engagement_id=ctx.get('engagement_id'),
                    resource_type=resource_type,
                    resource_id=resource_id,
                    correlation_id=ctx.get('correlation_id')
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Factory function for audit service
def create_audit_service(repository: Repository) -> AuditService:
    """Create audit service instance with repository dependency"""
    return AuditService(repository)