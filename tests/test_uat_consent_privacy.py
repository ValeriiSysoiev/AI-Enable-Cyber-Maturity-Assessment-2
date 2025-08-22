"""
Test suite for UAT consent and privacy enforcement in audio transcription.
Validates enhanced consent requirements and PII scrubbing in staging/UAT environments.
"""

import os
import pytest
import base64
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.services.mcp_gateway.tools.audio_transcribe import AudioTranscriptionTool
from app.services.mcp_gateway.config import MCPConfig


class TestUATConsentPrivacy:
    """Test UAT-specific consent and privacy enforcement."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock MCP configuration for testing."""
        config = MagicMock(spec=MCPConfig)
        config.max_audio_file_size_mb = 50
        config.max_audio_duration_minutes = 60
        return config
    
    @pytest.fixture
    def audio_tool(self, mock_config):
        """Audio transcription tool instance for testing."""
        return AudioTranscriptionTool(mock_config)
    
    @pytest.fixture
    def mock_audio_data(self):
        """Mock audio data for testing."""
        # Simple mock audio data as base64
        mock_audio = b"mock_audio_data_for_testing"
        return base64.b64encode(mock_audio).decode('utf-8')
    
    @pytest.fixture
    def base_payload(self, mock_audio_data):
        """Base payload for audio transcription testing."""
        return {
            "audio_data": mock_audio_data,
            "mime_type": "audio/wav",
            "consent": True,
            "consent_type": "workshop",
            "options": {
                "language": "en-US",
                "include_timestamps": True
            }
        }
    
    def test_standard_consent_validation(self, audio_tool, base_payload):
        """Test standard consent validation in non-UAT environment."""
        # Remove UAT environment variables
        with patch.dict(os.environ, {}, clear=True):
            # Should pass with basic consent
            assert audio_tool.validate_consent(base_payload) is True
            
            # Should fail without consent
            no_consent_payload = base_payload.copy()
            no_consent_payload["consent"] = False
            
            with pytest.raises(ValueError, match="Audio transcription requires explicit consent"):
                audio_tool.validate_consent(no_consent_payload)
    
    def test_uat_enhanced_consent_validation(self, audio_tool, base_payload):
        """Test enhanced consent validation in UAT mode."""
        uat_env = {
            "UAT_MODE": "true",
            "UAT_CONSENT_REQUIRED": "true"
        }
        
        with patch.dict(os.environ, uat_env, clear=True):
            # Should pass with full UAT consent
            uat_payload = base_payload.copy()
            uat_payload.update({
                "participant_consent": {
                    "documented": True,
                    "participants": ["participant1@example.com", "participant2@example.com"]
                }
            })
            
            assert audio_tool.validate_consent(uat_payload) is True
            
            # Should fail without consent_type in UAT
            no_type_payload = base_payload.copy()
            del no_type_payload["consent_type"]
            
            with pytest.raises(ValueError, match="UAT environment requires consent_type"):
                audio_tool.validate_consent(no_type_payload)
            
            # Should fail without documented participant consent
            no_participant_consent = base_payload.copy()
            with pytest.raises(ValueError, match="UAT environment requires documented participant consent"):
                audio_tool.validate_consent(no_participant_consent)
    
    def test_staging_enhanced_consent_validation(self, audio_tool, base_payload):
        """Test enhanced consent validation in staging environment."""
        staging_env = {
            "STAGING_ENV": "true",
            "UAT_CONSENT_REQUIRED": "true"
        }
        
        with patch.dict(os.environ, staging_env, clear=True):
            # Should require stricter consent in staging
            with pytest.raises(ValueError, match="UAT environment requires documented participant consent"):
                audio_tool.validate_consent(base_payload)
            
            # Should pass with full staging consent
            staging_payload = base_payload.copy()
            staging_payload.update({
                "participant_consent": {
                    "documented": True,
                    "participants": ["test.user@staging.local"]
                }
            })
            
            assert audio_tool.validate_consent(staging_payload) is True
    
    def test_pii_scrubbing_enforcement_uat(self, audio_tool, base_payload):
        """Test automatic PII scrubbing enforcement in UAT environments."""
        uat_env = {
            "UAT_MODE": "true",
            "PII_SCRUB_ENABLED": "true"
        }
        
        with patch.dict(os.environ, uat_env, clear=True):
            # Mock the transcribe_audio method to return test data with PII
            mock_transcription = {
                "text": "Hi, my name is John Doe and my email is john.doe@example.com",
                "timestamps": [
                    {
                        "text": "Hi, my name is John Doe",
                        "start_time": 0.0,
                        "end_time": 2.0,
                        "confidence": 0.95
                    },
                    {
                        "text": "and my email is john.doe@example.com",
                        "start_time": 2.0,
                        "end_time": 4.0,
                        "confidence": 0.92
                    }
                ],
                "confidence": 0.93,
                "language": "en-US"
            }
            
            with patch.object(audio_tool, 'transcribe_audio', return_value=mock_transcription):
                # Execute transcription without explicit PII scrubbing
                result = audio_tool._apply_pii_scrubbing(mock_transcription, {"enabled": True, "auto_enabled_uat": True})
                
                # Verify PII was scrubbed
                assert "[EMAIL_REDACTED]" in result["text"]
                assert "[NAME_REDACTED]" in result["text"]
                assert "john.doe@example.com" not in result["text"]
                
                # Verify PII scrubbing metadata
                assert result["pii_scrubbing"]["applied"] is True
                assert result["pii_scrubbing"]["auto_enabled_uat"] is True
                assert len(result["pii_scrubbing"]["patterns_used"]) > 0
    
    def test_pii_pattern_detection(self, audio_tool):
        """Test comprehensive PII pattern detection and scrubbing."""
        test_transcription = {
            "text": "Contact me at john.doe@company.com or call 555-123-4567. My SSN is 123-45-6789.",
            "timestamps": [
                {
                    "text": "Contact me at john.doe@company.com",
                    "start_time": 0.0,
                    "end_time": 2.0,
                    "confidence": 0.95
                }
            ]
        }
        
        result = audio_tool._apply_pii_scrubbing(test_transcription, {"enabled": True})
        
        # Verify all PII types are scrubbed
        scrubbed_text = result["text"]
        assert "[EMAIL_REDACTED]" in scrubbed_text
        assert "[PHONE_REDACTED]" in scrubbed_text
        assert "[SSN_REDACTED]" in scrubbed_text
        
        # Verify original PII is removed
        assert "john.doe@company.com" not in scrubbed_text
        assert "555-123-4567" not in scrubbed_text
        assert "123-45-6789" not in scrubbed_text
        
        # Verify timestamps are also scrubbed
        assert "[EMAIL_REDACTED]" in result["timestamps"][0]["text"]
    
    @pytest.mark.asyncio
    async def test_full_uat_workflow(self, audio_tool, base_payload):
        """Test complete UAT workflow with consent and PII scrubbing."""
        uat_env = {
            "UAT_MODE": "true",
            "UAT_CONSENT_REQUIRED": "true",
            "PII_SCRUB_ENABLED": "true"
        }
        
        # Prepare UAT-compliant payload
        uat_payload = base_payload.copy()
        uat_payload.update({
            "participant_consent": {
                "documented": True,
                "participants": ["participant1@uat.local", "participant2@uat.local"]
            },
            "pii_scrub": {
                "enabled": False  # Should be auto-enabled by UAT
            }
        })
        
        with patch.dict(os.environ, uat_env, clear=True):
            with patch.object(audio_tool, 'validate_audio_file') as mock_validate:
                mock_validate.return_value = {
                    "file_size_mb": 5.0,
                    "mime_type": "audio/wav",
                    "duration_seconds": 30.0
                }
                
                with patch.object(audio_tool, 'transcribe_audio') as mock_transcribe:
                    mock_transcribe.return_value = {
                        "text": "This is a test transcription with email test@example.com",
                        "timestamps": [],
                        "confidence": 0.95,
                        "language": "en-US"
                    }
                    
                    # Execute full workflow
                    result = await audio_tool.execute(uat_payload, "test-engagement", "test-call-001")
                    
                    # Verify UAT compliance
                    assert result["success"] is True
                    assert result["uat_enhanced_validation"] is True
                    assert result["pii_scrub_enabled"] is True
                    assert result["pii_scrub_config"]["auto_enabled_uat"] is True
                    
                    # Verify consent metadata
                    assert result["consent"]["provided"] is True
                    assert result["consent"]["type"] == "workshop"
                    
                    # Verify PII was scrubbed in transcription
                    transcription = result["transcription"]
                    assert "[EMAIL_REDACTED]" in transcription["text"]
                    assert "test@example.com" not in transcription["text"]
    
    def test_invalid_consent_types(self, audio_tool, base_payload):
        """Test validation of consent types."""
        invalid_payload = base_payload.copy()
        invalid_payload["consent_type"] = "invalid_type"
        
        with pytest.raises(ValueError, match="Invalid consent_type"):
            audio_tool.validate_consent(invalid_payload)
    
    def test_consent_type_validation_uat(self, audio_tool, base_payload):
        """Test that UAT requires valid consent types."""
        uat_env = {
            "UAT_MODE": "true",
            "UAT_CONSENT_REQUIRED": "true"
        }
        
        with patch.dict(os.environ, uat_env, clear=True):
            # Test all valid consent types
            valid_types = ["workshop", "interview", "meeting", "general"]
            
            for consent_type in valid_types:
                test_payload = base_payload.copy()
                test_payload["consent_type"] = consent_type
                test_payload["participant_consent"] = {
                    "documented": True,
                    "participants": ["test@example.com"]
                }
                
                # Should not raise exception
                assert audio_tool.validate_consent(test_payload) is True
    
    def test_pii_scrubbing_metadata(self, audio_tool):
        """Test PII scrubbing metadata generation."""
        test_transcription = {
            "text": "Original text with email@test.com",
            "timestamps": []
        }
        
        result = audio_tool._apply_pii_scrubbing(test_transcription, {"enabled": True})
        
        # Verify metadata structure
        pii_meta = result["pii_scrubbing"]
        assert pii_meta["applied"] is True
        assert isinstance(pii_meta["patterns_used"], list)
        assert pii_meta["original_length"] == len("Original text with email@test.com")
        assert pii_meta["scrubbed_length"] == len(result["text"])
        assert "timestamp" in pii_meta
        
        # Verify timestamp format
        timestamp = datetime.fromisoformat(pii_meta["timestamp"].replace('Z', '+00:00'))
        assert isinstance(timestamp, datetime)
    
    def test_environment_detection_logging(self, audio_tool, base_payload, caplog):
        """Test that UAT/staging environment detection is properly logged."""
        uat_env = {
            "UAT_MODE": "true",
            "STAGING_ENV": "true"
        }
        
        with patch.dict(os.environ, uat_env, clear=True):
            # Add required UAT fields
            uat_payload = base_payload.copy()
            uat_payload["participant_consent"] = {
                "documented": True,
                "participants": ["test@example.com"]
            }
            
            audio_tool.validate_consent(uat_payload)
            
            # Check logging
            assert "UAT/Staging mode detected" in caplog.text
            assert "UAT consent validation completed" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])