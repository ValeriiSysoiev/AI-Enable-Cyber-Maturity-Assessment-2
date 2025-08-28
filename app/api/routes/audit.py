"""
API endpoints for audit logging and export functionality.
Provides REST endpoints for managing audit logs and compliance reporting.
"""
import os
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field, validator
import aiofiles

from services.audit_logger import (
    AuditLogger, 
    AuditEventType, 
    AuditSeverity,
    get_audit_logger
)
from core.security import get_current_user, require_permissions
from core.logging import get_correlation_id


router = APIRouter(prefix="/audit", tags=["audit"])


class AuditExportRequest(BaseModel):
    """Request model for audit log export."""
    start_date: datetime = Field(..., description="Start date for export (ISO 8601)")
    end_date: datetime = Field(..., description="End date for export (ISO 8601)")
    event_types: Optional[List[AuditEventType]] = Field(None, description="Filter by event types")
    engagement_ids: Optional[List[str]] = Field(None, description="Filter by engagement IDs")
    format: str = Field("jsonl", description="Export format (jsonl, json, csv)")
    include_pii: bool = Field(False, description="Include PII data in export (requires elevated permissions)")
    
    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
    
    @validator('format')
    def valid_format(cls, v):
        if v not in ['jsonl', 'json', 'csv']:
            raise ValueError('format must be one of: jsonl, json, csv')
        return v


class AuditSearchRequest(BaseModel):
    """Request model for audit log search."""
    query: str = Field(..., description="Search query")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    event_types: Optional[List[AuditEventType]] = Field(None, description="Event type filter")
    severity: Optional[AuditSeverity] = Field(None, description="Severity filter")
    limit: int = Field(100, ge=1, le=1000, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Results offset for pagination")


class AuditEventResponse(BaseModel):
    """Response model for audit events."""
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    correlation_id: str
    engagement_id: str
    severity: AuditSeverity
    operation: str
    status: str
    duration_ms: Optional[float]
    service_name: str
    environment: str


class AuditExportResponse(BaseModel):
    """Response model for audit export."""
    export_id: str = Field(..., description="Export job identifier")
    status: str = Field(..., description="Export status")
    file_path: Optional[str] = Field(None, description="Path to exported file")
    event_count: Optional[int] = Field(None, description="Number of events exported")
    file_size_bytes: Optional[int] = Field(None, description="Export file size")
    created_at: datetime = Field(..., description="Export creation time")
    completed_at: Optional[datetime] = Field(None, description="Export completion time")


class AuditStatsResponse(BaseModel):
    """Response model for audit statistics."""
    total_events: int
    events_by_type: Dict[str, int]
    events_by_severity: Dict[str, int]
    date_range: Dict[str, datetime]
    top_operations: List[Dict[str, Union[str, int]]]
    error_rate: float
    avg_duration_ms: float


@router.get("/events", response_model=List[AuditEventResponse])
async def get_audit_events(
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    event_type: Optional[AuditEventType] = Query(None, description="Event type filter"),
    engagement_id: Optional[str] = Query(None, description="Engagement ID filter"),
    severity: Optional[AuditSeverity] = Query(None, description="Severity filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    current_user: dict = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Retrieve audit events with filtering and pagination.
    Requires 'audit:read' permission.
    """
    # Check permissions
    require_permissions(current_user, ["audit:read"])
    
    # Set default date range if not provided
    if not end_date:
        end_date = datetime.now(timezone.utc)
    if not start_date:
        start_date = end_date - timedelta(days=7)  # Default to last 7 days
    
    try:
        # Read events from audit logs
        event_types = [event_type] if event_type else None
        engagement_ids = [engagement_id] if engagement_id else None
        
        events = await audit_logger._read_audit_events(
            start_date, end_date, event_types, engagement_ids
        )
        
        # Apply additional filters
        if severity:
            events = [e for e in events if e.get('severity') == severity.value]
        
        # Apply pagination
        total_events = len(events)
        paginated_events = events[offset:offset + limit]
        
        # Convert to response model
        response_events = []
        for event in paginated_events:
            response_events.append(AuditEventResponse(
                event_id=event['event_id'],
                event_type=AuditEventType(event['event_type']),
                timestamp=datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')),
                correlation_id=event['correlation_id'],
                engagement_id=event['engagement_id'],
                severity=AuditSeverity(event['severity']),
                operation=event['operation'],
                status=event['status'],
                duration_ms=event.get('duration_ms'),
                service_name=event.get('service_name', 'unknown'),
                environment=event.get('environment', 'unknown')
            ))
        
        return response_events
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve audit events: {str(e)}"
        )


@router.get("/events/{event_id}")
async def get_audit_event_detail(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Get detailed information for a specific audit event.
    Requires 'audit:read' permission.
    """
    require_permissions(current_user, ["audit:read"])
    
    try:
        # Search for event across all log files (last 90 days)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=90)
        
        events = await audit_logger._read_audit_events(start_date, end_date)
        
        # Find specific event
        event = next((e for e in events if e['event_id'] == event_id), None)
        
        if not event:
            raise HTTPException(status_code=404, detail="Audit event not found")
        
        return event
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve audit event: {str(e)}"
        )


@router.post("/export", response_model=AuditExportResponse)
async def export_audit_logs(
    request: AuditExportRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    corr_id: str = Depends(get_correlation_id)
):
    """
    Export audit logs for a specified date range and filters.
    Requires 'audit:export' permission, or 'audit:export:pii' for PII data.
    """
    # Check permissions
    required_perms = ["audit:export"]
    if request.include_pii:
        required_perms.append("audit:export:pii")
    
    require_permissions(current_user, required_perms)
    
    # Generate export ID
    export_id = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{corr_id[:8]}"
    
    # Create export response
    export_response = AuditExportResponse(
        export_id=export_id,
        status="started",
        created_at=datetime.now(timezone.utc)
    )
    
    # Start background export task
    background_tasks.add_task(
        _perform_audit_export,
        audit_logger,
        export_id,
        request,
        current_user['user_id'],
        corr_id
    )
    
    return export_response


async def _perform_audit_export(
    audit_logger: AuditLogger,
    export_id: str,
    request: AuditExportRequest,
    user_id: str,
    correlation_id: str
):
    """Background task to perform audit log export."""
    try:
        # Log export start
        await audit_logger.log_event({
            'event_type': AuditEventType.SYSTEM_EVENT,
            'operation': 'audit_export_start',
            'status': 'started',
            'correlation_id': correlation_id,
            'engagement_id': f'export_{export_id}',
            'severity': AuditSeverity.INFO,
            'user_id': user_id,
            'request_data': {
                'export_id': export_id,
                'date_range': {
                    'start': request.start_date.isoformat(),
                    'end': request.end_date.isoformat()
                },
                'filters': {
                    'event_types': [et.value for et in request.event_types] if request.event_types else None,
                    'engagement_ids': request.engagement_ids,
                    'include_pii': request.include_pii
                },
                'format': request.format
            }
        })
        
        # Perform export
        export_path = await audit_logger.export_audit_logs(
            request.start_date,
            request.end_date,
            request.event_types,
            request.engagement_ids,
            request.format
        )
        
        # Get file stats
        file_stats = export_path.stat()
        
        # Log export completion
        await audit_logger.log_event({
            'event_type': AuditEventType.SYSTEM_EVENT,
            'operation': 'audit_export_complete',
            'status': 'success',
            'correlation_id': correlation_id,
            'engagement_id': f'export_{export_id}',
            'severity': AuditSeverity.INFO,
            'user_id': user_id,
            'response_data': {
                'export_id': export_id,
                'file_path': str(export_path),
                'file_size_bytes': file_stats.st_size,
                'export_completed_at': datetime.now(timezone.utc).isoformat()
            }
        })
        
    except Exception as e:
        # Log export failure
        await audit_logger.log_event({
            'event_type': AuditEventType.SYSTEM_EVENT,
            'operation': 'audit_export_error',
            'status': 'error',
            'correlation_id': correlation_id,
            'engagement_id': f'export_{export_id}',
            'severity': AuditSeverity.ERROR,
            'user_id': user_id,
            'error_details': {
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
        })


@router.get("/export/{export_id}/status")
async def get_export_status(
    export_id: str,
    current_user: dict = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Get status of an audit log export job.
    Requires 'audit:export' permission.
    """
    require_permissions(current_user, ["audit:export"])
    
    try:
        # Search for export events
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=1)  # Search last 24 hours
        
        events = await audit_logger._read_audit_events(start_date, end_date)
        
        # Find export events for this export_id
        export_events = [
            e for e in events 
            if e.get('engagement_id') == f'export_{export_id}'
        ]
        
        if not export_events:
            raise HTTPException(status_code=404, detail="Export job not found")
        
        # Determine status from events
        start_event = next((e for e in export_events if e['operation'] == 'audit_export_start'), None)
        complete_event = next((e for e in export_events if e['operation'] == 'audit_export_complete'), None)
        error_event = next((e for e in export_events if e['operation'] == 'audit_export_error'), None)
        
        if error_event:
            status = "failed"
            completed_at = datetime.fromisoformat(error_event['timestamp'].replace('Z', '+00:00'))
        elif complete_event:
            status = "completed"
            completed_at = datetime.fromisoformat(complete_event['timestamp'].replace('Z', '+00:00'))
        else:
            status = "running"
            completed_at = None
        
        response = AuditExportResponse(
            export_id=export_id,
            status=status,
            created_at=datetime.fromisoformat(start_event['timestamp'].replace('Z', '+00:00')) if start_event else None,
            completed_at=completed_at
        )
        
        if complete_event and complete_event.get('response_data'):
            response.file_path = complete_event['response_data'].get('file_path')
            response.file_size_bytes = complete_event['response_data'].get('file_size_bytes')
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get export status: {str(e)}"
        )


@router.get("/export/{export_id}/download")
async def download_export_file(
    export_id: str,
    current_user: dict = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Download an exported audit log file.
    Requires 'audit:export' permission.
    """
    require_permissions(current_user, ["audit:export"])
    
    try:
        # Get export status to find file path
        export_status = await get_export_status(export_id, current_user, audit_logger)
        
        if export_status.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Export is not completed. Current status: {export_status.status}"
            )
        
        if not export_status.file_path:
            raise HTTPException(status_code=404, detail="Export file not found")
        
        file_path = Path(export_status.file_path)
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Export file no longer exists")
        
        # Determine media type based on file extension
        media_type_map = {
            '.jsonl': 'application/jsonl',
            '.json': 'application/json',
            '.csv': 'text/csv'
        }
        media_type = media_type_map.get(file_path.suffix, 'application/octet-stream')
        
        # Log download access
        await audit_logger.log_event({
            'event_type': AuditEventType.USER_ACTION,
            'operation': 'audit_export_download',
            'status': 'accessed',
            'correlation_id': get_correlation_id(),
            'engagement_id': f'export_{export_id}',
            'severity': AuditSeverity.INFO,
            'user_id': current_user['user_id'],
            'request_data': {
                'export_id': export_id,
                'file_path': str(file_path),
                'file_size_bytes': file_path.stat().st_size
            }
        })
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=f"audit_export_{export_id}{file_path.suffix}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download export file: {str(e)}"
        )


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_statistics(
    start_date: Optional[datetime] = Query(None, description="Start date for statistics"),
    end_date: Optional[datetime] = Query(None, description="End date for statistics"),
    current_user: dict = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Get audit log statistics and analytics.
    Requires 'audit:read' permission.
    """
    require_permissions(current_user, ["audit:read"])
    
    # Set default date range if not provided
    if not end_date:
        end_date = datetime.now(timezone.utc)
    if not start_date:
        start_date = end_date - timedelta(days=30)  # Default to last 30 days
    
    try:
        events = await audit_logger._read_audit_events(start_date, end_date)
        
        # Calculate statistics
        total_events = len(events)
        
        # Events by type
        events_by_type = {}
        for event in events:
            event_type = event.get('event_type', 'unknown')
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
        
        # Events by severity
        events_by_severity = {}
        for event in events:
            severity = event.get('severity', 'unknown')
            events_by_severity[severity] = events_by_severity.get(severity, 0) + 1
        
        # Top operations
        operation_counts = {}
        durations = []
        error_count = 0
        
        for event in events:
            operation = event.get('operation', 'unknown')
            operation_counts[operation] = operation_counts.get(operation, 0) + 1
            
            if event.get('duration_ms'):
                durations.append(event['duration_ms'])
            
            if event.get('status') in ['error', 'failure']:
                error_count += 1
        
        top_operations = [
            {'operation': op, 'count': count}
            for op, count in sorted(operation_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
        
        # Calculate averages
        avg_duration_ms = sum(durations) / len(durations) if durations else 0
        error_rate = (error_count / total_events) if total_events > 0 else 0
        
        return AuditStatsResponse(
            total_events=total_events,
            events_by_type=events_by_type,
            events_by_severity=events_by_severity,
            date_range={
                'start': start_date,
                'end': end_date
            },
            top_operations=top_operations,
            error_rate=error_rate,
            avg_duration_ms=avg_duration_ms
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate audit statistics: {str(e)}"
        )


@router.post("/replay/{correlation_id}")
async def replay_audit_events(
    correlation_id: str,
    current_user: dict = Depends(get_current_user),
    audit_logger: AuditLogger = Depends(get_audit_logger)
):
    """
    Replay audit events for a specific correlation ID.
    Useful for debugging and troubleshooting.
    Requires 'audit:replay' permission.
    """
    require_permissions(current_user, ["audit:replay"])
    
    try:
        # Search for events with this correlation ID
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)  # Search last 30 days
        
        events = await audit_logger._read_audit_events(start_date, end_date)
        
        # Filter events by correlation ID
        related_events = [
            e for e in events 
            if e.get('correlation_id') == correlation_id
        ]
        
        if not related_events:
            raise HTTPException(
                status_code=404,
                detail="No events found for this correlation ID"
            )
        
        # Sort events by timestamp
        related_events.sort(key=lambda x: x['timestamp'])
        
        # Log replay action
        await audit_logger.log_event({
            'event_type': AuditEventType.USER_ACTION,
            'operation': 'audit_replay',
            'status': 'initiated',
            'correlation_id': get_correlation_id(),
            'engagement_id': f'replay_{correlation_id}',
            'severity': AuditSeverity.INFO,
            'user_id': current_user['user_id'],
            'request_data': {
                'original_correlation_id': correlation_id,
                'event_count': len(related_events),
                'date_range': {
                    'first_event': related_events[0]['timestamp'],
                    'last_event': related_events[-1]['timestamp']
                }
            }
        })
        
        return {
            'correlation_id': correlation_id,
            'event_count': len(related_events),
            'events': related_events,
            'replay_summary': {
                'first_event': related_events[0]['timestamp'],
                'last_event': related_events[-1]['timestamp'],
                'duration_span': 'calculated_from_events',
                'operations': list(set(e.get('operation', 'unknown') for e in related_events))
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to replay audit events: {str(e)}"
        )