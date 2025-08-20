"""
Tests for MCP Connectors integration.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from services.orchestrator.mcp_connectors import MCPConnectors, create_mcp_connectors


class TestMCPConnectors:
    """Test suite for MCP Connectors functionality."""
    
    @pytest.fixture
    def mock_mcp_client(self):
        """Create mock MCP client."""
        client = Mock()
        client.call = AsyncMock()
        return client
    
    @pytest.fixture
    def mcp_connectors(self, mock_mcp_client):
        """Create MCP connectors instance with mock client."""
        with patch.dict('os.environ', {
            'MCP_CONNECTORS_AUDIO': 'true',
            'MCP_CONNECTORS_PPTX': 'true',
            'MCP_CONNECTORS_PII_SCRUB': 'true'
        }):
            return MCPConnectors(mock_mcp_client)
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_success(self, mcp_connectors, mock_mcp_client):
        """Test successful audio transcription."""
        # Arrange
        mock_response = {
            "success": True,
            "transcription": {
                "text": "This is a test transcription",
                "timestamps": [{"start": 0.0, "end": 2.5, "text": "This is a test transcription"}]
            },
            "call_id": "test-call-123"
        }
        mock_mcp_client.call.return_value = mock_response
        
        # Act
        result = await mcp_connectors.transcribe_audio(
            audio_data="base64audiodata",
            mime_type="audio/wav",
            engagement_id="test-engagement",
            consent_type="workshop"
        )
        
        # Assert
        assert result["success"] is True
        assert "transcription" in result
        assert result["transcription"]["text"] == "This is a test transcription"
        mock_mcp_client.call.assert_called_once_with(
            "audio.transcribe",
            {
                "consent": True,
                "consent_type": "workshop",
                "audio_data": "base64audiodata",
                "mime_type": "audio/wav",
                "options": {"language": "auto", "include_timestamps": True},
                "pii_scrub": {"enabled": True}
            },
            "test-engagement"
        )
    
    @pytest.mark.asyncio
    async def test_transcribe_audio_disabled(self, mock_mcp_client):
        """Test audio transcription when feature is disabled."""
        # Arrange
        with patch.dict('os.environ', {'MCP_CONNECTORS_AUDIO': 'false'}):
            connectors = MCPConnectors(mock_mcp_client)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Audio transcription connector is disabled"):
            await connectors.transcribe_audio(
                audio_data="base64audiodata",
                mime_type="audio/wav",
                engagement_id="test-engagement"
            )
    
    @pytest.mark.asyncio
    async def test_scrub_pii_content_success(self, mcp_connectors, mock_mcp_client):
        """Test successful PII scrubbing."""
        # Arrange
        mock_response = {
            "success": True,
            "scrubbed_content": "This is text with [REDACTED] information",
            "redaction_report": {
                "total_redactions": 1,
                "patterns_found": ["email_address"]
            }
        }
        mock_mcp_client.call.return_value = mock_response
        
        # Act
        result = await mcp_connectors.scrub_pii_content(
            content="This is text with john@example.com information",
            engagement_id="test-engagement",
            content_type="text"
        )
        
        # Assert
        assert result["success"] is True
        assert result["scrubbed_content"] == "This is text with [REDACTED] information"
        assert result["redaction_report"]["total_redactions"] == 1
        mock_mcp_client.call.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_scrub_pii_content_disabled(self, mock_mcp_client):
        """Test PII scrubbing when feature is disabled."""
        # Arrange
        with patch.dict('os.environ', {'MCP_CONNECTORS_PII_SCRUB': 'false'}):
            connectors = MCPConnectors(mock_mcp_client)
        
        # Act
        result = await connectors.scrub_pii_content(
            content="This is test content",
            engagement_id="test-engagement"
        )
        
        # Assert
        assert result["success"] is True
        assert result["scrubbed_content"] == "This is test content"
        assert result["redaction_report"]["total_redactions"] == 0
        assert result["pii_scrub_enabled"] is False
        mock_mcp_client.call.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_generate_roadmap_pptx_success(self, mcp_connectors, mock_mcp_client):
        """Test successful PPTX generation."""
        # Arrange
        roadmap_data = {
            "current_maturity": "Level 2",
            "target_maturity": "Level 4",
            "initiative_count": 12,
            "investment_required": "$500K",
            "initiatives": [
                {"title": "Implement MFA", "priority": "high"},
                {"title": "Security Training", "priority": "medium"}
            ],
            "timeline": {
                "Q1 2024": ["Implement MFA", "Security Assessment"],
                "Q2 2024": ["Security Training", "Policy Updates"]
            }
        }
        
        mock_response = {
            "success": True,
            "presentation": {
                "format": "base64",
                "data": "base64pptxdata",
                "size_bytes": 2048000
            }
        }
        mock_mcp_client.call.return_value = mock_response
        
        # Act
        result = await mcp_connectors.generate_roadmap_pptx(
            roadmap_data=roadmap_data,
            engagement_id="test-engagement",
            output_format="base64"
        )
        
        # Assert
        assert result["success"] is True
        assert "presentation" in result
        assert result["presentation"]["size_bytes"] == 2048000
        mock_mcp_client.call.assert_called_once_with(
            "pptx.render",
            {"presentation": pytest.any, "output_format": "base64"},
            "test-engagement"
        )
        
        # Verify presentation structure was built correctly
        call_args = mock_mcp_client.call.call_args[0][1]
        presentation = call_args["presentation"]
        assert presentation["title"] == "Cyber Maturity Roadmap"
        assert len(presentation["slides"]) >= 2  # Executive summary + Priority initiatives
        assert any(slide["title"] == "Executive Summary" for slide in presentation["slides"])
        assert any(slide["title"] == "Priority Initiatives" for slide in presentation["slides"])
    
    @pytest.mark.asyncio
    async def test_generate_roadmap_pptx_disabled(self, mock_mcp_client):
        """Test PPTX generation when feature is disabled."""
        # Arrange
        with patch.dict('os.environ', {'MCP_CONNECTORS_PPTX': 'false'}):
            connectors = MCPConnectors(mock_mcp_client)
        
        # Act & Assert
        with pytest.raises(ValueError, match="PPTX generation connector is disabled"):
            await connectors.generate_roadmap_pptx(
                roadmap_data={},
                engagement_id="test-engagement"
            )
    
    @pytest.mark.asyncio
    async def test_process_workshop_minutes_to_maturity(self, mcp_connectors, mock_mcp_client):
        """Test workshop minutes processing."""
        # Arrange
        minutes_text = """
        Workshop minutes from cyber security assessment meeting.
        We discussed identity management gaps and missing vulnerability assessments.
        Stakeholders are concerned about incident response capabilities.
        Training needs were identified for the security team.
        """
        
        mock_scrub_response = {
            "success": True,
            "scrubbed_content": minutes_text,  # No PII to scrub in this example
            "redaction_report": {"total_redactions": 0}
        }
        mock_mcp_client.call.return_value = mock_scrub_response
        
        # Act
        result = await mcp_connectors.process_workshop_minutes_to_maturity(
            minutes_text=minutes_text,
            engagement_id="test-engagement"
        )
        
        # Assert
        assert result["success"] is True
        assert "maturity_data" in result
        maturity_data = result["maturity_data"]
        assert maturity_data["source"] == "workshop_minutes"
        assert maturity_data["engagement_id"] == "test-engagement"
        assert len(maturity_data["suggested_assessments"]) > 0
        assert len(maturity_data["identified_gaps"]) > 0
        assert len(maturity_data["stakeholder_concerns"]) > 0
        
        # Verify some expected extractions
        assessment_categories = [item["category"] for item in maturity_data["suggested_assessments"]]
        assert "identity" in assessment_categories
        assert "vulnerability" in assessment_categories
        assert "incident" in assessment_categories
        assert "training" in assessment_categories
    
    def test_build_presentation_from_roadmap(self, mcp_connectors):
        """Test presentation structure building from roadmap data."""
        # Arrange
        roadmap_data = {
            "current_maturity": "Level 2",
            "target_maturity": "Level 4",
            "initiative_count": 8,
            "investment_required": "$300K",
            "initiatives": [
                {"title": "Multi-Factor Authentication", "priority": "high"},
                {"title": "Security Awareness Training", "priority": "high"},
                {"title": "Vulnerability Management", "priority": "medium"},
                {"title": "Incident Response Plan", "priority": "medium"}
            ],
            "timeline": {
                "Q1 2024": ["Multi-Factor Authentication", "Security Assessment"],
                "Q2 2024": ["Security Awareness Training"],
                "Q3 2024": ["Vulnerability Management", "Policy Updates"]
            },
            "sources": [
                {"title": "NIST CSF 2.0", "author": "NIST", "date": "2024"}
            ]
        }
        
        config = {
            "title": "Custom Security Roadmap",
            "author": "Security Team"
        }
        
        # Act
        presentation = mcp_connectors._build_presentation_from_roadmap(roadmap_data, config)
        
        # Assert
        assert presentation["title"] == "Custom Security Roadmap"
        assert presentation["author"] == "Security Team"
        assert len(presentation["slides"]) >= 3  # Executive + Priority + Timeline
        
        # Check executive summary slide
        exec_slide = next(slide for slide in presentation["slides"] if slide["title"] == "Executive Summary")
        assert "Current maturity level: Level 2" in exec_slide["content"]
        assert "Target maturity level: Level 4" in exec_slide["content"]
        assert "Total initiatives: 8" in exec_slide["content"]
        
        # Check priority initiatives slide
        priority_slide = next(slide for slide in presentation["slides"] if slide["title"] == "Priority Initiatives")
        assert priority_slide["type"] == "two_content"
        assert any("Multi-Factor Authentication" in item for item in priority_slide["left_content"])
        assert any("Vulnerability Management" in item for item in priority_slide["right_content"])
        
        # Check timeline slide
        timeline_slide = next(slide for slide in presentation["slides"] if slide["title"] == "Implementation Timeline")
        timeline_content = " ".join(timeline_slide["content"])
        assert "Q1 2024" in timeline_content
        assert "Q2 2024" in timeline_content
        
        # Check citations
        assert len(presentation["citations"]) >= 1
        assert any(citation["title"] == "NIST CSF 2.0" for citation in presentation["citations"])
    
    def test_extract_assessment_suggestions(self, mcp_connectors):
        """Test assessment suggestion extraction from text."""
        # Arrange
        text = """
        During our security review, we identified several areas needing attention:
        - Identity and access management requires strengthening
        - Incident response procedures need updating
        - Vulnerability scanning is not comprehensive
        - Staff training on security awareness is lacking
        - Compliance with regulations needs verification
        """
        
        # Act
        suggestions = mcp_connectors._extract_assessment_suggestions(text)
        
        # Assert
        assert len(suggestions) <= 5  # Limited to top 5
        categories = [item["category"] for item in suggestions]
        assert "identity" in categories
        assert "incident" in categories
        assert "vulnerability" in categories
        assert "training" in categories
        assert "compliance" in categories
        
        for suggestion in suggestions:
            assert suggestion["priority"] == "medium"
            assert suggestion["extracted_from"] == "workshop_minutes"
    
    def test_extract_gaps_from_minutes(self, mcp_connectors):
        """Test security gap extraction from minutes."""
        # Arrange
        text = """
        The assessment revealed several gaps in our security posture:
        - Missing endpoint protection
        - Insufficient backup procedures
        - Weak password policies
        """
        
        # Act
        gaps = mcp_connectors._extract_gaps_from_minutes(text)
        
        # Assert
        assert len(gaps) <= 3  # Limited to top 3
        gap_indicators = [item["indicator"] for item in gaps]
        assert "missing" in gap_indicators
        assert "insufficient" in gap_indicators
        assert "weak" in gap_indicators
        
        for gap in gaps:
            assert gap["context"] == "mentioned in workshop discussion"
            assert gap["priority"] == "review_required"
    
    def test_extract_concerns_from_minutes(self, mcp_connectors):
        """Test stakeholder concern extraction from minutes."""
        # Arrange
        text = """
        Stakeholders expressed several concerns during the meeting:
        - Worried about potential data breaches
        - Risk of regulatory non-compliance
        - Challenges in implementing new security tools
        """
        
        # Act
        concerns = mcp_connectors._extract_concerns_from_minutes(text)
        
        # Assert
        assert len(concerns) <= 3  # Limited to top 3
        concern_types = [item["type"] for item in concerns]
        assert "worried" in concern_types
        assert "risk" in concern_types
        assert "challenge" in concern_types
        
        for concern in concerns:
            assert concern["source"] == "stakeholder_discussion"
            assert concern["requires_attention"] is True
    
    def test_create_mcp_connectors_factory(self, mock_mcp_client):
        """Test factory function for creating MCP connectors."""
        # Act
        connectors = create_mcp_connectors(mock_mcp_client)
        
        # Assert
        assert isinstance(connectors, MCPConnectors)
        assert connectors.mcp_client == mock_mcp_client
    
    def test_feature_flags_initialization(self, mock_mcp_client):
        """Test feature flag initialization from environment variables."""
        # Test with all flags enabled
        with patch.dict('os.environ', {
            'MCP_CONNECTORS_AUDIO': 'true',
            'MCP_CONNECTORS_PPTX': 'true',
            'MCP_CONNECTORS_PII_SCRUB': 'true'
        }):
            connectors = MCPConnectors(mock_mcp_client)
            assert connectors.audio_enabled is True
            assert connectors.pptx_enabled is True
            assert connectors.pii_scrub_enabled is True
        
        # Test with all flags disabled
        with patch.dict('os.environ', {
            'MCP_CONNECTORS_AUDIO': 'false',
            'MCP_CONNECTORS_PPTX': 'false',
            'MCP_CONNECTORS_PII_SCRUB': 'false'
        }):
            connectors = MCPConnectors(mock_mcp_client)
            assert connectors.audio_enabled is False
            assert connectors.pptx_enabled is False
            assert connectors.pii_scrub_enabled is False
        
        # Test with default values (no env vars set)
        with patch.dict('os.environ', {}, clear=True):
            connectors = MCPConnectors(mock_mcp_client)
            assert connectors.audio_enabled is False  # Default false
            assert connectors.pptx_enabled is False   # Default false
            assert connectors.pii_scrub_enabled is True  # Default true


if __name__ == "__main__":
    pytest.main([__file__])