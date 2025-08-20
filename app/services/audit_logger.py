"""
Audit logging service for Sprint v1.4 compliance and replay capabilities.
Provides comprehensive logging, export, and replay functionality for MCP operations.
"""
import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

import aiofiles
from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """Audit event types for categorization."""
    MCP_CALL_START = "mcp_call_start"
    MCP_CALL_SUCCESS = "mcp_call_success" 
    MCP_CALL_FAILURE = "mcp_call_failure"
    AUDIO_TRANSCRIPTION = "audio_transcription"
    PII_SCRUBBING = "pii_scrubbing"
    PPTX_GENERATION = "pptx_generation"
    ORCHESTRATION_START = "orchestration_start"
    ORCHESTRATION_COMPLETE = "orchestration_complete"
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"
    SECURITY_EVENT = "security_event"
    COMPLIANCE_EVENT = "compliance_event"


class AuditSeverity(str, Enum):
    """Audit event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Structured audit event with comprehensive metadata."""
    event_id: str
    event_type: AuditEventType
    timestamp: str
    correlation_id: str
    engagement_id: str
    severity: AuditSeverity
    
    # Core event data
    operation: str
    status: str
    duration_ms: Optional[float] = None
    
    # Context information
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Request/response data
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    
    # Security and compliance
    pii_detected: bool = False
    pii_scrubbed: bool = False
    consent_verified: bool = False
    data_classification: Optional[str] = None
    
    # Business context
    project_id: Optional[str] = None
    business_unit: Optional[str] = None
    
    # Technical metadata
    service_name: str = "mcp-gateway"
    service_version: Optional[str] = None
    environment: str = "production"
    
    # Additional metadata
    tags: Optional[Dict[str, str]] = None
    custom_fields: Optional[Dict[str, Any]] = None


class AuditEventModel(BaseModel):
    """Pydantic model for audit event validation."""
    event_id: str = Field(..., description="Unique event identifier")
    event_type: AuditEventType = Field(..., description="Type of audit event")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    correlation_id: str = Field(..., description="Request correlation ID")
    engagement_id: str = Field(..., description="Business engagement ID")
    severity: AuditSeverity = Field(..., description="Event severity level")
    
    operation: str = Field(..., description="Operation being performed")
    status: str = Field(..., description="Operation status")
    duration_ms: Optional[float] = Field(None, description="Operation duration in milliseconds")
    
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    source_ip: Optional[str] = Field(None, description="Source IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    
    request_data: Optional[Dict[str, Any]] = Field(None, description="Request payload")
    response_data: Optional[Dict[str, Any]] = Field(None, description="Response payload")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Error information")
    
    pii_detected: bool = Field(False, description="Whether PII was detected")
    pii_scrubbed: bool = Field(False, description="Whether PII was scrubbed")
    consent_verified: bool = Field(False, description="Whether user consent was verified")
    data_classification: Optional[str] = Field(None, description="Data classification level")
    
    project_id: Optional[str] = Field(None, description="Project identifier")
    business_unit: Optional[str] = Field(None, description="Business unit")
    
    service_name: str = Field("mcp-gateway", description="Service name")
    service_version: Optional[str] = Field(None, description="Service version")
    environment: str = Field("production", description="Environment name")
    
    tags: Optional[Dict[str, str]] = Field(None, description="Event tags")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="Custom metadata")


class AuditLogger:
    """
    Comprehensive audit logging service for MCP operations.
    
    Provides structured logging, export capabilities, and replay functionality
    for compliance, debugging, and business intelligence purposes.
    """
    
    def __init__(self, 
                 log_directory: str = None,
                 enable_file_logging: bool = True,
                 enable_structured_logging: bool = True,
                 log_retention_days: int = 90,
                 max_file_size_mb: int = 100):
        """
        Initialize audit logger.
        
        Args:
            log_directory: Directory for audit log files
            enable_file_logging: Whether to write to files
            enable_structured_logging: Whether to use structured format
            log_retention_days: Number of days to retain logs
            max_file_size_mb: Maximum file size before rotation
        """
        self.log_directory = Path(log_directory or os.environ.get("AUDIT_LOG_DIR", "/app/logs/audit"))
        self.enable_file_logging = enable_file_logging
        self.enable_structured_logging = enable_structured_logging
        self.log_retention_days = log_retention_days
        self.max_file_size_mb = max_file_size_mb
        
        # Ensure log directory exists
        if self.enable_file_logging:
            self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Setup structured logger
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        if enable_structured_logging:
            self._setup_structured_logger()
        
        # Service metadata
        self.service_name = os.environ.get("SERVICE_NAME", "mcp-gateway")
        self.service_version = os.environ.get("SERVICE_VERSION", "1.4.0")
        self.environment = os.environ.get("ENVIRONMENT", "production")
    
    def _setup_structured_logger(self):
        """Setup structured logging configuration."""
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | AUDIT | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if enabled)
        if self.enable_file_logging:
            log_file = self.log_directory / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    async def log_event(self, event: Union[AuditEvent, Dict[str, Any]]) -> str:
        """
        Log an audit event.
        
        Args:
            event: AuditEvent instance or dictionary
            
        Returns:
            Event ID for tracking
        """
        if isinstance(event, dict):
            # Validate and convert to AuditEvent
            validated = AuditEventModel(**event)
            event = AuditEvent(**validated.dict())
        
        # Ensure event has required fields
        if not event.event_id:
            event.event_id = str(uuid.uuid4())
        
        if not event.timestamp:
            event.timestamp = datetime.now(timezone.utc).isoformat()
        
        # Add service metadata
        event.service_name = self.service_name
        event.service_version = self.service_version
        event.environment = self.environment
        
        # Log to structured logger
        if self.enable_structured_logging:
            log_data = asdict(event)
            self.logger.info(json.dumps(log_data, ensure_ascii=False))
        
        # Write to audit file
        if self.enable_file_logging:
            await self._write_audit_file(event)
        
        return event.event_id
    
    async def _write_audit_file(self, event: AuditEvent):
        """Write audit event to dedicated audit file."""
        audit_file = self.log_directory / f"audit_events_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        event_json = json.dumps(asdict(event), ensure_ascii=False, default=str)
        
        async with aiofiles.open(audit_file, 'a', encoding='utf-8') as f:
            await f.write(event_json + '\n')
    
    async def log_mcp_call_start(self, 
                                operation: str,
                                correlation_id: str,
                                engagement_id: str,
                                request_data: Dict[str, Any],
                                **context) -> str:
        """Log MCP call initiation."""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.MCP_CALL_START,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id,
            engagement_id=engagement_id,
            severity=AuditSeverity.INFO,
            operation=operation,
            status="started",
            request_data=self._sanitize_request_data(request_data),
            **context
        )
        
        return await self.log_event(event)
    
    async def log_mcp_call_success(self,
                                  operation: str,
                                  correlation_id: str,
                                  engagement_id: str,
                                  response_data: Dict[str, Any],
                                  duration_ms: float,
                                  **context) -> str:
        """Log successful MCP call completion."""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.MCP_CALL_SUCCESS,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id,
            engagement_id=engagement_id,
            severity=AuditSeverity.INFO,
            operation=operation,
            status="success",
            duration_ms=duration_ms,
            response_data=self._sanitize_response_data(response_data),
            **context
        )
        
        return await self.log_event(event)
    
    async def log_mcp_call_failure(self,
                                  operation: str,
                                  correlation_id: str,
                                  engagement_id: str,
                                  error: Exception,
                                  duration_ms: float,
                                  **context) -> str:
        """Log failed MCP call."""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.MCP_CALL_FAILURE,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id,
            engagement_id=engagement_id,
            severity=AuditSeverity.ERROR,
            operation=operation,
            status="failure",
            duration_ms=duration_ms,
            error_details={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "error_traceback": self._get_error_traceback(error)
            },
            **context
        )
        
        return await self.log_event(event)
    
    async def log_audio_transcription(self,
                                     correlation_id: str,
                                     engagement_id: str,
                                     audio_metadata: Dict[str, Any],
                                     transcription_result: Dict[str, Any],
                                     pii_scrubbed: bool = False,
                                     consent_verified: bool = False,
                                     **context) -> str:
        """Log audio transcription operation."""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.AUDIO_TRANSCRIPTION,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id,
            engagement_id=engagement_id,
            severity=AuditSeverity.INFO,
            operation="audio_transcription",
            status="completed",
            request_data={
                "audio_format": audio_metadata.get("format"),
                "audio_duration": audio_metadata.get("duration_seconds"),
                "audio_size": audio_metadata.get("size_bytes"),
                "language": audio_metadata.get("language", "auto")
            },
            response_data={
                "transcript_length": len(transcription_result.get("text", "")),
                "confidence_score": transcription_result.get("confidence_score"),
                "timestamp_count": len(transcription_result.get("timestamps", []))
            },
            pii_detected=transcription_result.get("pii_detected", False),
            pii_scrubbed=pii_scrubbed,
            consent_verified=consent_verified,
            data_classification="confidential",
            **context
        )
        
        return await self.log_event(event)
    
    async def log_pptx_generation(self,
                                 correlation_id: str,
                                 engagement_id: str,
                                 roadmap_data: Dict[str, Any],
                                 presentation_result: Dict[str, Any],
                                 **context) -> str:
        """Log PPTX generation operation."""
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=AuditEventType.PPTX_GENERATION,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id,
            engagement_id=engagement_id,
            severity=AuditSeverity.INFO,
            operation="pptx_generation",
            status="completed",
            request_data={
                "initiative_count": roadmap_data.get("initiative_count"),
                "current_maturity": roadmap_data.get("current_maturity"),
                "target_maturity": roadmap_data.get("target_maturity"),
                "template": roadmap_data.get("template", "executive")
            },
            response_data={
                "slide_count": presentation_result.get("slide_count"),
                "file_size_bytes": presentation_result.get("size_bytes"),
                "generation_time": presentation_result.get("generation_time")
            },
            data_classification="internal",
            **context
        )
        
        return await self.log_event(event)
    
    async def export_audit_logs(self,
                               start_date: datetime,
                               end_date: datetime,
                               event_types: Optional[List[AuditEventType]] = None,
                               engagement_ids: Optional[List[str]] = None,
                               format: str = "jsonl") -> Path:
        """
        Export audit logs for a date range.
        
        Args:
            start_date: Start of export range
            end_date: End of export range
            event_types: Filter by event types
            engagement_ids: Filter by engagement IDs
            format: Export format (jsonl, csv, json)
            
        Returns:
            Path to exported file
        """
        export_filename = f"audit_export_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.{format}"
        export_path = self.log_directory / "exports" / export_filename
        export_path.parent.mkdir(exist_ok=True)
        
        events = await self._read_audit_events(start_date, end_date, event_types, engagement_ids)
        
        if format == "jsonl":
            await self._export_jsonl(events, export_path)
        elif format == "json":
            await self._export_json(events, export_path)
        elif format == "csv":
            await self._export_csv(events, export_path)
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        self.logger.info(f"Exported {len(events)} audit events to {export_path}")
        return export_path
    
    async def _read_audit_events(self,
                                start_date: datetime,
                                end_date: datetime,
                                event_types: Optional[List[AuditEventType]] = None,
                                engagement_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Read audit events from log files within date range."""
        events = []
        
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            log_file = self.log_directory / f"audit_events_{current_date.strftime('%Y%m%d')}.jsonl"
            
            if log_file.exists():
                async with aiofiles.open(log_file, 'r', encoding='utf-8') as f:
                    async for line in f:
                        try:
                            event = json.loads(line.strip())
                            event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                            
                            # Filter by date range
                            if not (start_date <= event_time <= end_date):
                                continue
                            
                            # Filter by event types
                            if event_types and event['event_type'] not in [et.value for et in event_types]:
                                continue
                            
                            # Filter by engagement IDs
                            if engagement_ids and event.get('engagement_id') not in engagement_ids:
                                continue
                            
                            events.append(event)
                        except (json.JSONDecodeError, KeyError, ValueError) as e:
                            self.logger.warning(f"Skipping malformed audit event: {e}")
            
            current_date = current_date.replace(day=current_date.day + 1) if current_date.day < 28 else \
                          current_date.replace(month=current_date.month + 1, day=1) if current_date.month < 12 else \
                          current_date.replace(year=current_date.year + 1, month=1, day=1)
        
        return events
    
    async def _export_jsonl(self, events: List[Dict[str, Any]], export_path: Path):
        """Export events as JSON Lines format."""
        async with aiofiles.open(export_path, 'w', encoding='utf-8') as f:
            for event in events:
                await f.write(json.dumps(event, ensure_ascii=False, default=str) + '\n')
    
    async def _export_json(self, events: List[Dict[str, Any]], export_path: Path):
        """Export events as JSON array."""
        async with aiofiles.open(export_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(events, ensure_ascii=False, indent=2, default=str))
    
    async def _export_csv(self, events: List[Dict[str, Any]], export_path: Path):
        """Export events as CSV format."""
        import csv
        
        if not events:
            return
        
        # Get all unique field names
        all_fields = set()
        for event in events:
            all_fields.update(event.keys())
        
        fieldnames = sorted(all_fields)
        
        # Write CSV using regular file I/O (aiofiles doesn't support csv module)
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for event in events:
                # Flatten nested objects for CSV
                flattened = self._flatten_dict(event)
                writer.writerow(flattened)
    
    def _flatten_dict(self, d: Dict[str, Any], prefix: str = '') -> Dict[str, str]:
        """Flatten nested dictionary for CSV export."""
        flattened = {}
        
        for key, value in d.items():
            new_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                flattened.update(self._flatten_dict(value, new_key))
            elif isinstance(value, list):
                flattened[new_key] = json.dumps(value)
            else:
                flattened[new_key] = str(value) if value is not None else ''
        
        return flattened
    
    def _sanitize_request_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize request data for logging (remove sensitive fields)."""
        if not data:
            return {}
        
        sanitized = data.copy()
        
        # Remove or mask sensitive fields
        sensitive_fields = ['audio_data', 'password', 'token', 'key', 'secret']
        
        for field in sensitive_fields:
            if field in sanitized:
                if field == 'audio_data':
                    sanitized[field] = f"[AUDIO_DATA:{len(str(sanitized[field]))} chars]"
                else:
                    sanitized[field] = "[REDACTED]"
        
        return sanitized
    
    def _sanitize_response_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize response data for logging."""
        if not data:
            return {}
        
        sanitized = data.copy()
        
        # Remove large binary data but keep metadata
        if 'presentation' in sanitized and isinstance(sanitized['presentation'], dict):
            if 'data' in sanitized['presentation']:
                data_size = len(str(sanitized['presentation']['data']))
                sanitized['presentation']['data'] = f"[PPTX_DATA:{data_size} chars]"
        
        return sanitized
    
    def _get_error_traceback(self, error: Exception) -> str:
        """Get error traceback string."""
        import traceback
        return traceback.format_exc()


# Global audit logger instance
audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create global audit logger instance."""
    global audit_logger
    if audit_logger is None:
        audit_logger = AuditLogger()
    return audit_logger


# Context manager for audit logging
class AuditContext:
    """Context manager for automatic audit logging of operations."""
    
    def __init__(self,
                 operation: str,
                 correlation_id: str,
                 engagement_id: str,
                 logger: AuditLogger = None,
                 **context):
        self.operation = operation
        self.correlation_id = correlation_id
        self.engagement_id = engagement_id
        self.logger = logger or get_audit_logger()
        self.context = context
        self.start_time = None
        self.event_id = None
    
    async def __aenter__(self):
        """Start audit logging."""
        self.start_time = datetime.now()
        self.event_id = await self.logger.log_mcp_call_start(
            self.operation,
            self.correlation_id,
            self.engagement_id,
            self.context.get('request_data', {}),
            **{k: v for k, v in self.context.items() if k != 'request_data'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Complete audit logging."""
        duration_ms = (datetime.now() - self.start_time).total_seconds() * 1000
        
        if exc_type is None:
            # Success
            await self.logger.log_mcp_call_success(
                self.operation,
                self.correlation_id,
                self.engagement_id,
                self.context.get('response_data', {}),
                duration_ms,
                **{k: v for k, v in self.context.items() if k != 'response_data'}
            )
        else:
            # Failure
            await self.logger.log_mcp_call_failure(
                self.operation,
                self.correlation_id,
                self.engagement_id,
                exc_val,
                duration_ms,
                **self.context
            )