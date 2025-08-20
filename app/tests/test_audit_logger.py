"""
Tests for audit logging service.
"""
import os
import json
import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import shutil

from app.services.audit_logger import (
    AuditLogger,
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    AuditContext,
    get_audit_logger
)


class TestAuditLogger:
    """Test suite for AuditLogger functionality."""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary directory for test logs."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def audit_logger(self, temp_log_dir):
        """Create audit logger instance for testing."""
        return AuditLogger(
            log_directory=temp_log_dir,
            enable_file_logging=True,
            enable_structured_logging=True,
            log_retention_days=30,
            max_file_size_mb=10
        )
    
    @pytest.fixture
    def sample_audit_event(self):
        """Create sample audit event for testing."""
        return AuditEvent(
            event_id="test-event-123",
            event_type=AuditEventType.MCP_CALL_START,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id="test-corr-456",
            engagement_id="test-eng-789",
            severity=AuditSeverity.INFO,
            operation="test_operation",
            status="started",
            request_data={"test_param": "test_value"},
            user_id="test_user",
            project_id="test_project"
        )
    
    @pytest.mark.asyncio
    async def test_log_event_success(self, audit_logger, sample_audit_event):
        """Test successful event logging."""
        # Act
        event_id = await audit_logger.log_event(sample_audit_event)
        
        # Assert
        assert event_id == sample_audit_event.event_id
        
        # Verify file was created
        log_date = datetime.now().strftime('%Y%m%d')
        audit_file = Path(audit_logger.log_directory) / f"audit_events_{log_date}.jsonl"
        assert audit_file.exists()
        
        # Verify file content
        with open(audit_file, 'r') as f:
            logged_event = json.loads(f.read().strip())
        
        assert logged_event['event_id'] == sample_audit_event.event_id
        assert logged_event['event_type'] == sample_audit_event.event_type.value
        assert logged_event['operation'] == sample_audit_event.operation
        assert logged_event['service_name'] == audit_logger.service_name
    
    @pytest.mark.asyncio
    async def test_log_event_from_dict(self, audit_logger):
        """Test logging event from dictionary."""
        # Arrange
        event_dict = {
            "event_type": AuditEventType.AUDIO_TRANSCRIPTION,
            "correlation_id": "test-corr-dict",
            "engagement_id": "test-eng-dict",
            "severity": AuditSeverity.INFO,
            "operation": "audio_transcribe",
            "status": "completed"
        }
        
        # Act
        event_id = await audit_logger.log_event(event_dict)
        
        # Assert
        assert event_id is not None
        assert len(event_id) > 0  # UUID should be generated
    
    @pytest.mark.asyncio
    async def test_log_mcp_call_start(self, audit_logger):
        """Test MCP call start logging."""
        # Arrange
        operation = "audio.transcribe"
        correlation_id = "test-corr-start"
        engagement_id = "test-eng-start"
        request_data = {
            "audio_data": "base64audiodata",
            "mime_type": "audio/wav"
        }
        
        # Act
        event_id = await audit_logger.log_mcp_call_start(
            operation, correlation_id, engagement_id, request_data
        )
        
        # Assert
        assert event_id is not None
        
        # Verify logged data
        log_date = datetime.now().strftime('%Y%m%d')
        audit_file = Path(audit_logger.log_directory) / f"audit_events_{log_date}.jsonl"
        
        with open(audit_file, 'r') as f:
            logged_event = json.loads(f.read().strip())
        
        assert logged_event['event_type'] == AuditEventType.MCP_CALL_START.value
        assert logged_event['operation'] == operation
        assert logged_event['status'] == "started"
        assert logged_event['request_data']['mime_type'] == "audio/wav"
        # Audio data should be sanitized
        assert "[AUDIO_DATA:" in logged_event['request_data']['audio_data']
    
    @pytest.mark.asyncio
    async def test_log_mcp_call_success(self, audit_logger):
        """Test MCP call success logging."""
        # Arrange
        operation = "pptx.render"
        correlation_id = "test-corr-success"
        engagement_id = "test-eng-success"
        response_data = {
            "success": True,
            "presentation": {
                "data": "base64pptxdata",
                "size_bytes": 2048000
            }
        }
        duration_ms = 1500.5
        
        # Act
        event_id = await audit_logger.log_mcp_call_success(
            operation, correlation_id, engagement_id, response_data, duration_ms
        )
        
        # Assert
        assert event_id is not None
        
        # Verify logged data
        log_date = datetime.now().strftime('%Y%m%d')
        audit_file = Path(audit_logger.log_directory) / f"audit_events_{log_date}.jsonl"
        
        with open(audit_file, 'r') as f:
            logged_event = json.loads(f.read().strip())
        
        assert logged_event['event_type'] == AuditEventType.MCP_CALL_SUCCESS.value
        assert logged_event['operation'] == operation
        assert logged_event['status'] == "success"
        assert logged_event['duration_ms'] == duration_ms
        # PPTX data should be sanitized
        assert "[PPTX_DATA:" in logged_event['response_data']['presentation']['data']
    
    @pytest.mark.asyncio
    async def test_log_mcp_call_failure(self, audit_logger):
        """Test MCP call failure logging."""
        # Arrange
        operation = "pii.scrub"
        correlation_id = "test-corr-failure"
        engagement_id = "test-eng-failure"
        error = ValueError("Invalid content format")
        duration_ms = 250.0
        
        # Act
        event_id = await audit_logger.log_mcp_call_failure(
            operation, correlation_id, engagement_id, error, duration_ms
        )
        
        # Assert
        assert event_id is not None
        
        # Verify logged data
        log_date = datetime.now().strftime('%Y%m%d')
        audit_file = Path(audit_logger.log_directory) / f"audit_events_{log_date}.jsonl"
        
        with open(audit_file, 'r') as f:
            logged_event = json.loads(f.read().strip())
        
        assert logged_event['event_type'] == AuditEventType.MCP_CALL_FAILURE.value
        assert logged_event['operation'] == operation
        assert logged_event['status'] == "failure"
        assert logged_event['duration_ms'] == duration_ms
        assert logged_event['error_details']['error_type'] == "ValueError"
        assert logged_event['error_details']['error_message'] == "Invalid content format"
    
    @pytest.mark.asyncio
    async def test_log_audio_transcription(self, audit_logger):
        """Test audio transcription logging."""
        # Arrange
        correlation_id = "test-corr-audio"
        engagement_id = "test-eng-audio"
        audio_metadata = {
            "format": "wav",
            "duration_seconds": 180.5,
            "size_bytes": 2048000,
            "language": "en-US"
        }
        transcription_result = {
            "text": "This is the transcribed text",
            "confidence_score": 0.95,
            "timestamps": [{"start": 0.0, "end": 2.5, "text": "This is"}],
            "pii_detected": False
        }
        
        # Act
        event_id = await audit_logger.log_audio_transcription(
            correlation_id, engagement_id, audio_metadata, transcription_result,
            pii_scrubbed=True, consent_verified=True
        )
        
        # Assert
        assert event_id is not None
        
        # Verify logged data
        log_date = datetime.now().strftime('%Y%m%d')
        audit_file = Path(audit_logger.log_directory) / f"audit_events_{log_date}.jsonl"
        
        with open(audit_file, 'r') as f:
            logged_event = json.loads(f.read().strip())
        
        assert logged_event['event_type'] == AuditEventType.AUDIO_TRANSCRIPTION.value
        assert logged_event['operation'] == "audio_transcription"
        assert logged_event['pii_scrubbed'] is True
        assert logged_event['consent_verified'] is True
        assert logged_event['data_classification'] == "confidential"
        assert logged_event['request_data']['audio_format'] == "wav"
        assert logged_event['response_data']['transcript_length'] == len(transcription_result['text'])
    
    @pytest.mark.asyncio
    async def test_log_pptx_generation(self, audit_logger):
        """Test PPTX generation logging."""
        # Arrange
        correlation_id = "test-corr-pptx"
        engagement_id = "test-eng-pptx"
        roadmap_data = {
            "initiative_count": 15,
            "current_maturity": "Level 2",
            "target_maturity": "Level 4",
            "template": "executive"
        }
        presentation_result = {
            "slide_count": 8,
            "size_bytes": 3048000,
            "generation_time": 4.2
        }
        
        # Act
        event_id = await audit_logger.log_pptx_generation(
            correlation_id, engagement_id, roadmap_data, presentation_result
        )
        
        # Assert
        assert event_id is not None
        
        # Verify logged data
        log_date = datetime.now().strftime('%Y%m%d')
        audit_file = Path(audit_logger.log_directory) / f"audit_events_{log_date}.jsonl"
        
        with open(audit_file, 'r') as f:
            logged_event = json.loads(f.read().strip())
        
        assert logged_event['event_type'] == AuditEventType.PPTX_GENERATION.value
        assert logged_event['operation'] == "pptx_generation"
        assert logged_event['data_classification'] == "internal"
        assert logged_event['request_data']['initiative_count'] == 15
        assert logged_event['response_data']['slide_count'] == 8
    
    @pytest.mark.asyncio
    async def test_export_audit_logs_jsonl(self, audit_logger, temp_log_dir):
        """Test audit log export in JSONL format."""
        # Arrange - Create some test events
        events = []
        for i in range(5):
            event = AuditEvent(
                event_id=f"test-event-{i}",
                event_type=AuditEventType.MCP_CALL_SUCCESS,
                timestamp=datetime.now(timezone.utc).isoformat(),
                correlation_id=f"test-corr-{i}",
                engagement_id=f"test-eng-{i}",
                severity=AuditSeverity.INFO,
                operation="test_operation",
                status="success"
            )
            events.append(event)
            await audit_logger.log_event(event)
        
        # Act
        start_date = datetime.now(timezone.utc) - timedelta(hours=1)
        end_date = datetime.now(timezone.utc) + timedelta(hours=1)
        
        export_path = await audit_logger.export_audit_logs(
            start_date, end_date, format="jsonl"
        )
        
        # Assert
        assert export_path.exists()
        assert export_path.suffix == ".jsonl"
        
        # Verify content
        with open(export_path, 'r') as f:
            lines = f.readlines()
        
        assert len(lines) >= 5  # At least our 5 test events
        
        # Verify first line is valid JSON
        first_event = json.loads(lines[0])
        assert 'event_id' in first_event
        assert 'event_type' in first_event
    
    @pytest.mark.asyncio
    async def test_export_audit_logs_json(self, audit_logger):
        """Test audit log export in JSON format."""
        # Arrange - Create test event
        event = AuditEvent(
            event_id="test-event-json",
            event_type=AuditEventType.USER_ACTION,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id="test-corr-json",
            engagement_id="test-eng-json",
            severity=AuditSeverity.INFO,
            operation="test_operation",
            status="completed"
        )
        await audit_logger.log_event(event)
        
        # Act
        start_date = datetime.now(timezone.utc) - timedelta(hours=1)
        end_date = datetime.now(timezone.utc) + timedelta(hours=1)
        
        export_path = await audit_logger.export_audit_logs(
            start_date, end_date, format="json"
        )
        
        # Assert
        assert export_path.exists()
        assert export_path.suffix == ".json"
        
        # Verify content
        with open(export_path, 'r') as f:
            exported_events = json.load(f)
        
        assert isinstance(exported_events, list)
        assert len(exported_events) >= 1
        
        # Find our test event
        test_event = next((e for e in exported_events if e['event_id'] == 'test-event-json'), None)
        assert test_event is not None
        assert test_event['operation'] == 'test_operation'
    
    @pytest.mark.asyncio
    async def test_export_audit_logs_csv(self, audit_logger):
        """Test audit log export in CSV format."""
        # Arrange - Create test event
        event = AuditEvent(
            event_id="test-event-csv",
            event_type=AuditEventType.SYSTEM_EVENT,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id="test-corr-csv",
            engagement_id="test-eng-csv",
            severity=AuditSeverity.WARNING,
            operation="test_operation",
            status="warning"
        )
        await audit_logger.log_event(event)
        
        # Act
        start_date = datetime.now(timezone.utc) - timedelta(hours=1)
        end_date = datetime.now(timezone.utc) + timedelta(hours=1)
        
        export_path = await audit_logger.export_audit_logs(
            start_date, end_date, format="csv"
        )
        
        # Assert
        assert export_path.exists()
        assert export_path.suffix == ".csv"
        
        # Verify content
        import csv
        with open(export_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) >= 1
        
        # Verify headers
        fieldnames = reader.fieldnames
        assert 'event_id' in fieldnames
        assert 'event_type' in fieldnames
        assert 'operation' in fieldnames
        
        # Find our test event
        test_row = next((r for r in rows if r['event_id'] == 'test-event-csv'), None)
        assert test_row is not None
        assert test_row['severity'] == 'warning'
    
    @pytest.mark.asyncio
    async def test_export_with_filters(self, audit_logger):
        """Test audit log export with event type and engagement filters."""
        # Arrange - Create events of different types
        events = [
            AuditEvent(
                event_id="audio-event",
                event_type=AuditEventType.AUDIO_TRANSCRIPTION,
                timestamp=datetime.now(timezone.utc).isoformat(),
                correlation_id="test-corr-filter",
                engagement_id="test-eng-audio",
                severity=AuditSeverity.INFO,
                operation="audio_transcribe",
                status="success"
            ),
            AuditEvent(
                event_id="pptx-event",
                event_type=AuditEventType.PPTX_GENERATION,
                timestamp=datetime.now(timezone.utc).isoformat(),
                correlation_id="test-corr-filter",
                engagement_id="test-eng-pptx",
                severity=AuditSeverity.INFO,
                operation="pptx_generate",
                status="success"
            )
        ]
        
        for event in events:
            await audit_logger.log_event(event)
        
        # Act - Export only audio events
        start_date = datetime.now(timezone.utc) - timedelta(hours=1)
        end_date = datetime.now(timezone.utc) + timedelta(hours=1)
        
        export_path = await audit_logger.export_audit_logs(
            start_date, end_date,
            event_types=[AuditEventType.AUDIO_TRANSCRIPTION],
            format="json"
        )
        
        # Assert
        with open(export_path, 'r') as f:
            exported_events = json.load(f)
        
        # Should only contain audio events (and possibly others from previous tests)
        audio_events = [e for e in exported_events if e['event_type'] == AuditEventType.AUDIO_TRANSCRIPTION.value]
        assert len(audio_events) >= 1
        
        pptx_events = [e for e in exported_events if e['event_type'] == AuditEventType.PPTX_GENERATION.value]
        assert len(pptx_events) == 0  # Should be filtered out
    
    @pytest.mark.asyncio
    async def test_audit_context_success(self, audit_logger):
        """Test AuditContext context manager for successful operations."""
        # Arrange
        operation = "test_context_operation"
        correlation_id = "test-corr-context"
        engagement_id = "test-eng-context"
        
        # Act
        async with AuditContext(
            operation, correlation_id, engagement_id,
            logger=audit_logger,
            request_data={"test": "data"}
        ) as ctx:
            # Simulate some work
            await asyncio.sleep(0.01)
            ctx.context['response_data'] = {"result": "success"}
        
        # Assert - Check that both start and success events were logged
        log_date = datetime.now().strftime('%Y%m%d')
        audit_file = Path(audit_logger.log_directory) / f"audit_events_{log_date}.jsonl"
        
        with open(audit_file, 'r') as f:
            events = [json.loads(line) for line in f.readlines()]
        
        # Find our events
        context_events = [e for e in events if e['correlation_id'] == correlation_id]
        assert len(context_events) >= 2  # Start and success events
        
        start_event = next(e for e in context_events if e['event_type'] == AuditEventType.MCP_CALL_START.value)
        success_event = next(e for e in context_events if e['event_type'] == AuditEventType.MCP_CALL_SUCCESS.value)
        
        assert start_event['operation'] == operation
        assert start_event['status'] == "started"
        assert success_event['operation'] == operation
        assert success_event['status'] == "success"
        assert success_event['duration_ms'] > 0
    
    @pytest.mark.asyncio
    async def test_audit_context_failure(self, audit_logger):
        """Test AuditContext context manager for failed operations."""
        # Arrange
        operation = "test_context_failure"
        correlation_id = "test-corr-context-fail"
        engagement_id = "test-eng-context-fail"
        
        # Act & Assert
        with pytest.raises(ValueError):
            async with AuditContext(
                operation, correlation_id, engagement_id,
                logger=audit_logger
            ):
                raise ValueError("Test error for context")
        
        # Verify failure event was logged
        log_date = datetime.now().strftime('%Y%m%d')
        audit_file = Path(audit_logger.log_directory) / f"audit_events_{log_date}.jsonl"
        
        with open(audit_file, 'r') as f:
            events = [json.loads(line) for line in f.readlines()]
        
        context_events = [e for e in events if e['correlation_id'] == correlation_id]
        failure_event = next(e for e in context_events if e['event_type'] == AuditEventType.MCP_CALL_FAILURE.value)
        
        assert failure_event['operation'] == operation
        assert failure_event['status'] == "failure"
        assert failure_event['error_details']['error_message'] == "Test error for context"
    
    def test_get_audit_logger_singleton(self):
        """Test that get_audit_logger returns singleton instance."""
        # Act
        logger1 = get_audit_logger()
        logger2 = get_audit_logger()
        
        # Assert
        assert logger1 is logger2  # Same instance
        assert isinstance(logger1, AuditLogger)
    
    def test_sanitize_request_data(self, audit_logger):
        """Test request data sanitization."""
        # Arrange
        sensitive_data = {
            "audio_data": "base64encodedaudiodata" * 100,  # Large audio data
            "password": "secret123",
            "api_key": "sk-1234567890",
            "normal_field": "normal_value"
        }
        
        # Act
        sanitized = audit_logger._sanitize_request_data(sensitive_data)
        
        # Assert
        assert "[AUDIO_DATA:" in sanitized["audio_data"]
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["normal_field"] == "normal_value"
    
    def test_sanitize_response_data(self, audit_logger):
        """Test response data sanitization."""
        # Arrange
        response_data = {
            "success": True,
            "presentation": {
                "data": "base64pptxdata" * 1000,  # Large PPTX data
                "size_bytes": 2048000,
                "slide_count": 8
            },
            "metadata": {
                "processing_time": 5.2
            }
        }
        
        # Act
        sanitized = audit_logger._sanitize_response_data(response_data)
        
        # Assert
        assert "[PPTX_DATA:" in sanitized["presentation"]["data"]
        assert sanitized["presentation"]["size_bytes"] == 2048000  # Metadata preserved
        assert sanitized["success"] is True
        assert sanitized["metadata"]["processing_time"] == 5.2
    
    def test_flatten_dict(self, audit_logger):
        """Test dictionary flattening for CSV export."""
        # Arrange
        nested_dict = {
            "top_level": "value",
            "nested": {
                "level2": "value2",
                "deeper": {
                    "level3": "value3"
                }
            },
            "array": ["item1", "item2"]
        }
        
        # Act
        flattened = audit_logger._flatten_dict(nested_dict)
        
        # Assert
        assert flattened["top_level"] == "value"
        assert flattened["nested.level2"] == "value2"
        assert flattened["nested.deeper.level3"] == "value3"
        assert '"item1"' in flattened["array"]  # JSON encoded array
    
    @pytest.mark.asyncio
    async def test_read_audit_events_date_filtering(self, audit_logger):
        """Test audit event reading with date filtering."""
        # Arrange - Create events with different timestamps
        now = datetime.now(timezone.utc)
        old_event = AuditEvent(
            event_id="old-event",
            event_type=AuditEventType.SYSTEM_EVENT,
            timestamp=(now - timedelta(days=2)).isoformat(),
            correlation_id="old-corr",
            engagement_id="old-eng",
            severity=AuditSeverity.INFO,
            operation="old_operation",
            status="completed"
        )
        
        new_event = AuditEvent(
            event_id="new-event",
            event_type=AuditEventType.SYSTEM_EVENT,
            timestamp=now.isoformat(),
            correlation_id="new-corr",
            engagement_id="new-eng",
            severity=AuditSeverity.INFO,
            operation="new_operation",
            status="completed"
        )
        
        await audit_logger.log_event(old_event)
        await audit_logger.log_event(new_event)
        
        # Act - Read events from last 24 hours
        start_date = now - timedelta(hours=24)
        end_date = now + timedelta(hours=1)
        
        events = await audit_logger._read_audit_events(start_date, end_date)
        
        # Assert
        event_ids = [e['event_id'] for e in events]
        assert "new-event" in event_ids
        # old-event should not be included as it's older than 24 hours


if __name__ == "__main__":
    pytest.main([__file__, "-v"])