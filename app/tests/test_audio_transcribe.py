"""
Unit tests for Audio Transcription MCP Tool.
"""
import pytest
import base64
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from services.mcp_gateway.tools.audio_transcribe import AudioTranscriptionTool
from services.mcp_gateway.config import MCPConfig


@pytest.fixture
def mock_config():
    """Mock MCP configuration for testing."""
    config = Mock(spec=MCPConfig)
    config.max_audio_file_size_mb = 50
    config.max_audio_duration_minutes = 60
    return config


@pytest.fixture
def audio_tool(mock_config):
    """Audio transcription tool instance for testing."""
    return AudioTranscriptionTool(mock_config)


@pytest.fixture
def sample_audio_payload():
    """Sample valid audio payload for testing."""
    # Create a small mock audio file (just some bytes)
    mock_audio_data = b"mock_audio_data_here" * 100
    return {
        "consent": True,
        "consent_type": "workshop",
        "audio_data": base64.b64encode(mock_audio_data).decode(),
        "mime_type": "audio/wav",
        "options": {
            "language": "en-US",
            "include_timestamps": True
        }
    }


class TestAudioTranscriptionConsent:
    """Test consent validation functionality."""
    
    def test_valid_consent_accepted(self, audio_tool):
        """Test that valid consent is accepted."""
        payload = {
            "consent": True,
            "consent_type": "workshop"
        }
        
        assert audio_tool.validate_consent(payload) is True
    
    def test_missing_consent_rejected(self, audio_tool):
        """Test that missing consent is rejected."""
        payload = {"consent": False}
        
        with pytest.raises(ValueError) as exc_info:
            audio_tool.validate_consent(payload)
        
        assert "explicit consent" in str(exc_info.value)
    
    def test_invalid_consent_type_rejected(self, audio_tool):
        """Test that invalid consent types are rejected."""
        payload = {
            "consent": True,
            "consent_type": "invalid_type"
        }
        
        with pytest.raises(ValueError) as exc_info:
            audio_tool.validate_consent(payload)
        
        assert "Invalid consent_type" in str(exc_info.value)
    
    def test_valid_consent_types_accepted(self, audio_tool):
        """Test that all valid consent types are accepted."""
        valid_types = ["workshop", "interview", "meeting", "general"]
        
        for consent_type in valid_types:
            payload = {
                "consent": True,
                "consent_type": consent_type
            }
            
            assert audio_tool.validate_consent(payload) is True


class TestAudioFileValidation:
    """Test audio file validation functionality."""
    
    def test_supported_mime_types_accepted(self, audio_tool):
        """Test that supported MIME types are accepted."""
        supported_types = [
            "audio/wav", "audio/mp3", "audio/mpeg", 
            "audio/mp4", "audio/m4a", "audio/flac", "audio/ogg"
        ]
        
        small_audio_data = b"test_audio" * 10
        
        for mime_type in supported_types:
            metadata = audio_tool.validate_audio_file(small_audio_data, mime_type)
            assert metadata["mime_type"] == mime_type
            assert metadata["file_size_mb"] > 0
    
    def test_unsupported_mime_type_rejected(self, audio_tool):
        """Test that unsupported MIME types are rejected."""
        audio_data = b"test_audio"
        
        with pytest.raises(ValueError) as exc_info:
            audio_tool.validate_audio_file(audio_data, "audio/unsupported")
        
        assert "Unsupported audio MIME type" in str(exc_info.value)
    
    def test_oversized_file_rejected(self, audio_tool):
        """Test that oversized files are rejected."""
        # Create a file larger than the limit (50MB)
        large_audio_data = b"x" * (60 * 1024 * 1024)  # 60MB
        
        with pytest.raises(ValueError) as exc_info:
            audio_tool.validate_audio_file(large_audio_data, "audio/wav")
        
        assert "Audio file too large" in str(exc_info.value)
    
    def test_file_size_calculation(self, audio_tool):
        """Test accurate file size calculation."""
        audio_data = b"x" * (1024 * 1024)  # 1MB
        
        metadata = audio_tool.validate_audio_file(audio_data, "audio/wav")
        
        assert metadata["file_size_mb"] == 1.0


class TestMockTranscription:
    """Test mock transcription functionality."""
    
    def test_mock_transcription_structure(self, audio_tool):
        """Test that mock transcription returns expected structure."""
        audio_data = b"test_audio_data"
        options = {"language": "en-US"}
        
        result = audio_tool._mock_transcription(audio_data, "audio/wav", options)
        
        # Check required fields
        assert "text" in result
        assert "timestamps" in result
        assert "confidence" in result
        assert "language" in result
        assert result["mock_mode"] is True
        
        # Check timestamps structure
        assert isinstance(result["timestamps"], list)
        for timestamp in result["timestamps"]:
            assert "text" in timestamp
            assert "start_time" in timestamp
            assert "end_time" in timestamp
            assert "confidence" in timestamp
    
    def test_mock_transcription_confidence_scores(self, audio_tool):
        """Test that mock transcription provides reasonable confidence scores."""
        audio_data = b"test_audio_data"
        
        result = audio_tool._mock_transcription(audio_data, "audio/wav", {})
        
        # Overall confidence should be reasonable
        assert 0.0 <= result["confidence"] <= 1.0
        
        # Individual timestamp confidences should be reasonable
        for timestamp in result["timestamps"]:
            assert 0.0 <= timestamp["confidence"] <= 1.0


class TestAudioTranscriptionExecution:
    """Test full audio transcription execution."""
    
    @pytest.mark.asyncio
    async def test_successful_transcription_mock_mode(self, audio_tool, sample_audio_payload):
        """Test successful transcription in mock mode."""
        engagement_id = "test-engagement-123"
        call_id = "test-call-456"
        
        # Execute transcription
        result = await audio_tool.execute(sample_audio_payload, engagement_id, call_id)
        
        # Check success response structure
        assert result["success"] is True
        assert result["tool"] == "audio.transcribe"
        assert result["call_id"] == call_id
        assert result["engagement_id"] == engagement_id
        
        # Check transcription data
        assert "transcription" in result
        transcription = result["transcription"]
        assert "text" in transcription
        assert "timestamps" in transcription
        assert "confidence" in transcription
        
        # Check file metadata
        assert "file_metadata" in result
        assert "consent" in result
        assert result["consent"]["provided"] is True
    
    @pytest.mark.asyncio
    async def test_missing_consent_fails(self, audio_tool, sample_audio_payload):
        """Test that missing consent causes failure."""
        sample_audio_payload["consent"] = False
        
        result = await audio_tool.execute(sample_audio_payload, "test-eng", "test-call")
        
        assert result["success"] is False
        assert "consent" in result["error"]
    
    @pytest.mark.asyncio
    async def test_missing_audio_data_fails(self, audio_tool):
        """Test that missing audio data causes failure."""
        payload = {
            "consent": True,
            "mime_type": "audio/wav"
            # Missing audio_data
        }
        
        result = await audio_tool.execute(payload, "test-eng", "test-call")
        
        assert result["success"] is False
        assert "audio_data" in result["error"]
    
    @pytest.mark.asyncio
    async def test_invalid_base64_fails(self, audio_tool):
        """Test that invalid base64 audio data causes failure."""
        payload = {
            "consent": True,
            "audio_data": "invalid_base64_data!!!",
            "mime_type": "audio/wav"
        }
        
        result = await audio_tool.execute(payload, "test-eng", "test-call")
        
        assert result["success"] is False
        assert "base64" in result["error"]
    
    @pytest.mark.asyncio
    async def test_pii_scrub_flag_preserved(self, audio_tool, sample_audio_payload):
        """Test that PII scrubbing flag is preserved in results."""
        sample_audio_payload["pii_scrub"] = {"enabled": True}
        
        result = await audio_tool.execute(sample_audio_payload, "test-eng", "test-call")
        
        assert result["success"] is True
        assert result["pii_scrub_enabled"] is True


class TestToolRegistration:
    """Test tool registration functionality."""
    
    def test_tool_registration(self):
        """Test that tool can be registered properly."""
        from services.mcp_gateway.tools.audio_transcribe import register_tool
        
        tool_registry = {}
        register_tool(tool_registry)
        
        assert "audio.transcribe" in tool_registry
        assert tool_registry["audio.transcribe"] == AudioTranscriptionTool


class TestAudioProcessingConfiguration:
    """Test audio processing configuration and limits."""
    
    def test_default_configuration(self, audio_tool):
        """Test default configuration values."""
        assert audio_tool.max_file_size_mb == 50
        assert audio_tool.max_duration_minutes == 60
        assert audio_tool.chunk_size_ms == 30000
        assert audio_tool.sample_rate == 16000
    
    def test_mime_type_mapping(self, audio_tool):
        """Test MIME type to extension mapping."""
        assert audio_tool.MIME_TO_EXTENSION["audio/wav"] == ".wav"
        assert audio_tool.MIME_TO_EXTENSION["audio/mp3"] == ".mp3"
        assert audio_tool.MIME_TO_EXTENSION["audio/flac"] == ".flac"
    
    def test_allowed_mime_types_coverage(self, audio_tool):
        """Test that all allowed MIME types have extension mappings."""
        for mime_type in audio_tool.ALLOWED_MIME_TYPES:
            assert mime_type in audio_tool.MIME_TO_EXTENSION