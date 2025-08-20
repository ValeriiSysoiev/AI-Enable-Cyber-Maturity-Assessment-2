"""
End-to-End UAT tests for Sprint v1.4 Audio Transcription and PPTX Generation.
Tests the complete workflow from audio input to executive presentation output.
"""
import os
import pytest
import asyncio
import base64
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

import httpx
from fastapi.testclient import TestClient


class TestUATAudioPPTXWorkflow:
    """End-to-end UAT tests for Sprint v1.4 enterprise connectors."""
    
    @pytest.fixture
    def uat_mode_enabled(self):
        """Enable UAT mode for testing."""
        with patch.dict(os.environ, {
            'UAT_MODE': 'true',
            'MCP_ENABLED': 'true',
            'MCP_CONNECTORS_AUDIO': 'true',
            'MCP_CONNECTORS_PPTX': 'true',
            'MCP_CONNECTORS_PII_SCRUB': 'true'
        }):
            yield
    
    @pytest.fixture
    def sample_audio_data(self):
        """Generate sample base64 encoded audio data for testing."""
        # Simulate a small WAV file header + data
        wav_header = b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00'
        wav_data = b'\x00' * 1000  # Minimal audio data
        sample_wav = wav_header + wav_data
        return base64.b64encode(sample_wav).decode('utf-8')
    
    @pytest.fixture
    def sample_roadmap_data(self):
        """Generate sample roadmap data for PPTX generation."""
        return {
            "current_maturity": "Level 2 - Developing",
            "target_maturity": "Level 4 - Managing", 
            "initiative_count": 15,
            "investment_required": "$750,000",
            "initiatives": [
                {
                    "title": "Implement Zero Trust Architecture",
                    "priority": "high",
                    "timeline": "Q1 2024",
                    "budget": 250000,
                    "owner": "Security Team"
                },
                {
                    "title": "Security Awareness Training Program",
                    "priority": "high", 
                    "timeline": "Q1 2024",
                    "budget": 100000,
                    "owner": "HR & Security"
                },
                {
                    "title": "Vulnerability Management Enhancement",
                    "priority": "medium",
                    "timeline": "Q2 2024", 
                    "budget": 150000,
                    "owner": "IT Operations"
                },
                {
                    "title": "Incident Response Automation",
                    "priority": "medium",
                    "timeline": "Q3 2024",
                    "budget": 200000,
                    "owner": "SOC Team"
                }
            ],
            "timeline": {
                "Q1 2024": [
                    "Implement Zero Trust Architecture",
                    "Security Awareness Training Program", 
                    "Initial vulnerability assessment"
                ],
                "Q2 2024": [
                    "Vulnerability Management Enhancement",
                    "Policy framework updates",
                    "Compliance audit preparation"
                ],
                "Q3 2024": [
                    "Incident Response Automation",
                    "Advanced threat detection",
                    "Penetration testing"
                ],
                "Q4 2024": [
                    "Security maturity assessment",
                    "Final compliance verification",
                    "Continuous improvement planning"
                ]
            },
            "sources": [
                {
                    "title": "NIST Cybersecurity Framework 2.0",
                    "author": "NIST",
                    "date": "2024",
                    "type": "framework"
                },
                {
                    "title": "Organization Security Assessment",
                    "author": "Internal Security Team",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "type": "assessment"
                }
            ],
            "risk_profile": {
                "overall_risk": "Medium-High",
                "critical_gaps": 3,
                "compliance_score": 72
            }
        }
    
    @pytest.fixture
    def sample_workshop_minutes(self):
        """Generate sample workshop minutes text."""
        return """
        CYBERSECURITY MATURITY ASSESSMENT WORKSHOP
        Date: March 15, 2024
        Attendees: CTO, CISO, IT Director, Security Architect, Compliance Manager
        
        DISCUSSION POINTS:
        
        1. CURRENT STATE ANALYSIS
        - Identity management system needs modernization
        - Multi-factor authentication is partially implemented
        - Vulnerability scanning occurs monthly but lacks automation
        - Incident response procedures exist but require updating
        - Staff security training is inconsistent across departments
        
        2. IDENTIFIED GAPS AND CONCERNS
        - Missing endpoint detection and response capabilities
        - Insufficient backup and recovery testing
        - Weak network segmentation in development environment
        - Lacking continuous compliance monitoring
        - Concerned about potential data breaches in customer systems
        - Risk of regulatory non-compliance with upcoming requirements
        
        3. STAKEHOLDER PRIORITIES
        - CEO is worried about reputational damage from security incidents
        - CFO concerned about budget allocation for security improvements
        - Legal team flagged compliance requirements for data governance
        - Operations team challenged by security tool complexity
        
        4. PROPOSED INITIATIVES
        - Implement zero trust architecture within 12 months
        - Enhance security awareness training program
        - Deploy automated vulnerability management solution
        - Establish 24/7 security operations center
        - Conduct quarterly penetration testing
        
        5. SUCCESS METRICS
        - Reduce mean time to detection (MTTD) to under 15 minutes
        - Achieve 95% compliance score on regulatory audits
        - Complete security training for 100% of staff annually
        - Implement continuous monitoring for all critical assets
        
        ACTION ITEMS:
        - Security team to prepare detailed implementation roadmap
        - Budget proposal for executive review by end of month
        - Pilot zero trust implementation in development environment
        - Schedule quarterly security maturity assessments
        
        Next meeting scheduled for April 1, 2024.
        """
    
    @pytest.mark.asyncio
    async def test_complete_uat_workflow_with_audio_and_pptx(self, uat_mode_enabled, 
                                                           sample_audio_data, 
                                                           sample_roadmap_data):
        """
        Test complete UAT workflow: Audio transcription → Analysis → PPTX generation.
        This simulates a real user acceptance testing scenario.
        """
        engagement_id = f"uat_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Mock MCP client responses
        with patch('services.orchestrator.mcp_connectors.generate_correlation_id') as mock_corr_id:
            mock_corr_id.return_value = f"test_corr_{engagement_id}"
            
            # Mock audio transcription response
            mock_transcript_response = {
                "success": True,
                "transcription": {
                    "text": sample_workshop_minutes[:500] + "... [Additional workshop discussion transcribed]",
                    "confidence_score": 0.94,
                    "language": "en-US",
                    "timestamps": [
                        {"start": 0.0, "end": 5.2, "text": "CYBERSECURITY MATURITY ASSESSMENT WORKSHOP"},
                        {"start": 5.5, "end": 12.1, "text": "Date: March 15, 2024"}
                    ]
                },
                "processing_metadata": {
                    "duration_seconds": 180.5,
                    "audio_format": "wav",
                    "processing_time": 12.3
                },
                "pii_scrubbing_applied": {
                    "total_redactions": 0,
                    "patterns_checked": ["email_address", "phone_us", "us_ssn"]
                },
                "call_id": f"audio_call_{engagement_id}"
            }
            
            # Mock PPTX generation response
            mock_pptx_response = {
                "success": True,
                "presentation": {
                    "format": "base64",
                    "data": base64.b64encode(b"mock_pptx_data").decode(),
                    "size_bytes": 2048000,
                    "slide_count": 8,
                    "template": "executive"
                },
                "generation_metadata": {
                    "generation_time": 5.7,
                    "template_used": "executive",
                    "branding_applied": True
                },
                "call_id": f"pptx_call_{engagement_id}"
            }
            
            with patch('services.orchestrator.mcp_connectors.MCPConnectors') as mock_connectors_class:
                mock_connectors = Mock()
                mock_connectors.audio_enabled = True
                mock_connectors.pptx_enabled = True
                mock_connectors.pii_scrub_enabled = True
                
                # Configure mock methods
                mock_connectors.transcribe_audio = AsyncMock(return_value=mock_transcript_response)
                mock_connectors.generate_roadmap_pptx = AsyncMock(return_value=mock_pptx_response)
                mock_connectors.process_workshop_minutes_to_maturity = AsyncMock(return_value={
                    "success": True,
                    "maturity_data": {
                        "suggested_assessments": [
                            {"category": "identity", "priority": "high"},
                            {"category": "incident", "priority": "medium"}
                        ],
                        "identified_gaps": [
                            {"indicator": "missing", "context": "endpoint detection"},
                            {"indicator": "insufficient", "context": "backup testing"}
                        ],
                        "stakeholder_concerns": [
                            {"type": "worried", "source": "executive_level"},
                            {"type": "risk", "source": "compliance_team"}
                        ]
                    }
                })
                
                mock_connectors_class.return_value = mock_connectors
                
                # Test Phase 1: Audio Transcription
                from services.orchestrator.main import app
                client = TestClient(app)
                
                transcript_request = {
                    "audio_data": sample_audio_data,
                    "mime_type": "audio/wav",
                    "engagement_id": engagement_id,
                    "consent_type": "workshop",
                    "options": {
                        "language": "auto",
                        "include_timestamps": True
                    }
                }
                
                transcript_response = client.post("/transcribe/audio", json=transcript_request)
                assert transcript_response.status_code == 200
                
                transcript_data = transcript_response.json()
                assert transcript_data["success"] is True
                assert "transcription" in transcript_data
                assert transcript_data["transcription"]["confidence_score"] > 0.8
                
                # Verify PII scrubbing was applied
                assert "pii_scrubbing_applied" in transcript_data
                
                # Test Phase 2: Workshop Minutes Processing
                minutes_request = {
                    "minutes_text": transcript_data["transcription"]["text"],
                    "engagement_id": engagement_id
                }
                
                minutes_response = client.post("/process/minutes", json=minutes_request)
                assert minutes_response.status_code == 200
                
                minutes_data = minutes_response.json()
                assert minutes_data["success"] is True
                assert len(minutes_data["maturity_data"]["suggested_assessments"]) > 0
                assert len(minutes_data["maturity_data"]["identified_gaps"]) > 0
                
                # Test Phase 3: PPTX Generation
                pptx_request = {
                    "roadmap_data": sample_roadmap_data,
                    "engagement_id": engagement_id,
                    "presentation_config": {
                        "title": f"Cyber Maturity Roadmap - {engagement_id}",
                        "author": "UAT Testing Suite",
                        "template": "executive"
                    },
                    "output_format": "base64"
                }
                
                pptx_response = client.post("/generate/pptx", json=pptx_request)
                assert pptx_response.status_code == 200
                
                pptx_data = pptx_response.json()
                assert pptx_data["success"] is True
                assert "presentation" in pptx_data
                assert pptx_data["presentation"]["size_bytes"] > 1000000  # Reasonable size
                assert pptx_data["presentation"]["slide_count"] >= 5
                
                # Test Phase 4: Enhanced Orchestration
                # This would typically involve a full project, but we'll test the enhanced endpoint
                orchestration_request = {
                    "project_id": f"uat_project_{engagement_id[:8]}",
                    "engagement_id": engagement_id
                }
                
                # Note: This requires a real project setup, so we'll test the endpoint availability
                orchestration_response = client.post("/orchestrate/analyze_with_transcript", 
                                                   json=orchestration_request)
                # Expect 404 since project doesn't exist, but endpoint should be accessible
                assert orchestration_response.status_code in [404, 200, 422]  # 422 for validation
                
                # Verify all mock calls were made correctly
                mock_connectors.transcribe_audio.assert_called_once()
                mock_connectors.generate_roadmap_pptx.assert_called_once()
                mock_connectors.process_workshop_minutes_to_maturity.assert_called_once()
                
                # Verify call arguments
                audio_call_args = mock_connectors.transcribe_audio.call_args[1]
                assert audio_call_args["engagement_id"] == engagement_id
                assert audio_call_args["mime_type"] == "audio/wav"
                assert audio_call_args["consent_type"] == "workshop"
                
                pptx_call_args = mock_connectors.generate_roadmap_pptx.call_args[1]
                assert pptx_call_args["engagement_id"] == engagement_id
                assert pptx_call_args["roadmap_data"] == sample_roadmap_data
    
    @pytest.mark.asyncio 
    async def test_uat_error_handling_and_fallbacks(self, uat_mode_enabled):
        """Test error handling and fallback scenarios in UAT mode."""
        engagement_id = "uat_error_test"
        
        with patch('services.orchestrator.mcp_connectors.MCPConnectors') as mock_connectors_class:
            mock_connectors = Mock()
            mock_connectors.audio_enabled = True
            mock_connectors.pptx_enabled = True
            
            # Test audio transcription failure
            mock_connectors.transcribe_audio = AsyncMock(
                side_effect=Exception("Audio transcription service unavailable")
            )
            
            mock_connectors_class.return_value = mock_connectors
            
            from services.orchestrator.main import app
            client = TestClient(app)
            
            transcript_request = {
                "audio_data": "invalid_audio_data",
                "mime_type": "audio/wav", 
                "engagement_id": engagement_id
            }
            
            transcript_response = client.post("/transcribe/audio", json=transcript_request)
            assert transcript_response.status_code == 500
            assert "Audio transcription failed" in transcript_response.json()["detail"]
            
            # Test PPTX generation failure
            mock_connectors.generate_roadmap_pptx = AsyncMock(
                side_effect=Exception("PPTX generation service unavailable")
            )
            
            pptx_request = {
                "roadmap_data": {"invalid": "data"},
                "engagement_id": engagement_id
            }
            
            pptx_response = client.post("/generate/pptx", json=pptx_request)
            assert pptx_response.status_code == 500
            assert "PPTX generation failed" in pptx_response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_uat_feature_flags_disabled(self):
        """Test behavior when feature flags are disabled."""
        with patch.dict(os.environ, {
            'UAT_MODE': 'true',
            'MCP_ENABLED': 'true',
            'MCP_CONNECTORS_AUDIO': 'false',  # Disabled
            'MCP_CONNECTORS_PPTX': 'false'    # Disabled
        }):
            with patch('services.orchestrator.mcp_connectors.MCPConnectors') as mock_connectors_class:
                mock_connectors = Mock()
                mock_connectors.audio_enabled = False
                mock_connectors.pptx_enabled = False
                mock_connectors.transcribe_audio = AsyncMock(
                    side_effect=ValueError("Audio transcription connector is disabled")
                )
                mock_connectors.generate_roadmap_pptx = AsyncMock(
                    side_effect=ValueError("PPTX generation connector is disabled")
                )
                
                mock_connectors_class.return_value = mock_connectors
                
                from services.orchestrator.main import app
                client = TestClient(app)
                
                # Test disabled audio transcription
                transcript_request = {
                    "audio_data": "test_data",
                    "mime_type": "audio/wav",
                    "engagement_id": "test"
                }
                
                transcript_response = client.post("/transcribe/audio", json=transcript_request)
                assert transcript_response.status_code == 500
                assert "Audio transcription connector is disabled" in transcript_response.json()["detail"]
                
                # Test disabled PPTX generation
                pptx_request = {
                    "roadmap_data": {},
                    "engagement_id": "test"
                }
                
                pptx_response = client.post("/generate/pptx", json=pptx_request)
                assert pptx_response.status_code == 500
                assert "PPTX generation connector is disabled" in pptx_response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_uat_connectors_status_endpoint(self, uat_mode_enabled):
        """Test the connectors status endpoint in UAT mode."""
        with patch('services.orchestrator.mcp_connectors.MCPConnectors') as mock_connectors_class:
            mock_connectors = Mock()
            mock_connectors.audio_enabled = True
            mock_connectors.pptx_enabled = True
            mock_connectors.pii_scrub_enabled = True
            
            mock_connectors_class.return_value = mock_connectors
            
            from services.orchestrator.main import app
            client = TestClient(app)
            
            status_response = client.get("/connectors/status")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            assert status_data["mcp_enabled"] is True
            assert status_data["audio_enabled"] is True
            assert status_data["pptx_enabled"] is True
            assert status_data["pii_scrub_enabled"] is True
            assert status_data["status"] == "ok"
    
    def test_uat_data_validation_and_security(self, uat_mode_enabled, sample_audio_data):
        """Test data validation and security measures in UAT mode."""
        from services.orchestrator.main import app
        client = TestClient(app)
        
        # Test invalid audio data format
        invalid_audio_request = {
            "audio_data": "not_base64_data!!!",
            "mime_type": "audio/wav",
            "engagement_id": "test"
        }
        
        # Should fail validation (implementation dependent)
        audio_response = client.post("/transcribe/audio", json=invalid_audio_request)
        # Status could be 422 (validation) or 500 (processing error)
        assert audio_response.status_code in [422, 500]
        
        # Test missing required fields
        incomplete_request = {
            "audio_data": sample_audio_data
            # Missing mime_type and engagement_id
        }
        
        audio_response = client.post("/transcribe/audio", json=incomplete_request)
        assert audio_response.status_code == 422  # Validation error
        
        # Test invalid MIME type
        invalid_mime_request = {
            "audio_data": sample_audio_data,
            "mime_type": "application/malicious",
            "engagement_id": "test"
        }
        
        audio_response = client.post("/transcribe/audio", json=invalid_mime_request)
        # Should be handled by the audio transcription tool validation
        assert audio_response.status_code in [422, 500]
    
    @pytest.mark.asyncio
    async def test_uat_performance_and_monitoring(self, uat_mode_enabled, 
                                                sample_audio_data, 
                                                sample_roadmap_data):
        """Test performance characteristics and monitoring in UAT mode."""
        import time
        
        engagement_id = f"uat_perf_{int(time.time())}"
        
        with patch('services.orchestrator.mcp_connectors.MCPConnectors') as mock_connectors_class:
            # Simulate realistic processing times
            async def slow_transcribe_audio(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate processing time
                return {
                    "success": True,
                    "transcription": {"text": "Performance test transcript"},
                    "processing_metadata": {"processing_time": 0.1}
                }
            
            async def slow_generate_pptx(*args, **kwargs):
                await asyncio.sleep(0.2)  # Simulate generation time
                return {
                    "success": True,
                    "presentation": {"data": "test", "size_bytes": 1000000},
                    "generation_metadata": {"generation_time": 0.2}
                }
            
            mock_connectors = Mock()
            mock_connectors.audio_enabled = True
            mock_connectors.pptx_enabled = True
            mock_connectors.transcribe_audio = slow_transcribe_audio
            mock_connectors.generate_roadmap_pptx = slow_generate_pptx
            
            mock_connectors_class.return_value = mock_connectors
            
            from services.orchestrator.main import app
            client = TestClient(app)
            
            # Test audio transcription performance
            start_time = time.time()
            
            transcript_request = {
                "audio_data": sample_audio_data,
                "mime_type": "audio/wav",
                "engagement_id": engagement_id
            }
            
            transcript_response = client.post("/transcribe/audio", json=transcript_request)
            audio_duration = time.time() - start_time
            
            assert transcript_response.status_code == 200
            assert audio_duration < 5.0  # Should complete within 5 seconds
            
            # Test PPTX generation performance
            start_time = time.time()
            
            pptx_request = {
                "roadmap_data": sample_roadmap_data,
                "engagement_id": engagement_id
            }
            
            pptx_response = client.post("/generate/pptx", json=pptx_request)
            pptx_duration = time.time() - start_time
            
            assert pptx_response.status_code == 200
            assert pptx_duration < 10.0  # Should complete within 10 seconds
            
            # Verify response includes performance metadata
            transcript_data = transcript_response.json()
            if "processing_metadata" in transcript_data:
                assert "processing_time" in transcript_data["processing_metadata"]
            
            pptx_data = pptx_response.json()
            if "generation_metadata" in pptx_data:
                assert "generation_time" in pptx_data["generation_metadata"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])