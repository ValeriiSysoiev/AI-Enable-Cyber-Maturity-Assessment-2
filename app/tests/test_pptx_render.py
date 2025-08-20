"""
Unit tests for PPTX Rendering MCP Tool.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from services.mcp_gateway.tools.pptx_render import PPTXRenderTool
from services.mcp_gateway.config import MCPConfig


@pytest.fixture
def mock_config():
    """Mock MCP configuration for testing."""
    config = Mock(spec=MCPConfig)
    return config


@pytest.fixture
def pptx_tool(mock_config):
    """PPTX render tool instance for testing."""
    return PPTXRenderTool(mock_config)


@pytest.fixture
def sample_presentation_data():
    """Sample presentation data for testing."""
    return {
        "presentation": {
            "title": "Cyber Maturity Roadmap",
            "subtitle": "Assessment Results and Recommendations",
            "author": "AI Cyber Assessment",
            "slides": [
                {
                    "type": "content",
                    "title": "Executive Summary",
                    "content": [
                        "Current maturity level: 2.3/5.0",
                        "Key gaps identified in 3 domains",
                        "12-month roadmap developed",
                        "Investment required: $250K"
                    ]
                },
                {
                    "type": "two_content",
                    "title": "Priority Initiatives",
                    "left_content": [
                        "High Priority:",
                        "• Identity Management",
                        "• Incident Response",
                        "• Security Training"
                    ],
                    "right_content": [
                        "Medium Priority:",
                        "• Vulnerability Management", 
                        "• Risk Assessment",
                        "• Compliance Framework"
                    ]
                }
            ],
            "citations": [
                {
                    "title": "NIST Cybersecurity Framework 2.0",
                    "source": "NIST",
                    "date": "2024"
                },
                {
                    "title": "Industry Benchmark Study",
                    "source": "Cybersecurity Ventures",
                    "date": "2024"
                }
            ],
            "branding": {
                "colors": {
                    "primary": (0, 102, 204),
                    "secondary": (102, 102, 102)
                }
            }
        }
    }


class TestPresentationDataValidation:
    """Test presentation data validation."""
    
    def test_valid_presentation_data_accepted(self, pptx_tool, sample_presentation_data):
        """Test that valid presentation data is accepted."""
        config = pptx_tool.validate_presentation_data(sample_presentation_data)
        
        assert config["title"] == "Cyber Maturity Roadmap"
        assert len(config["slides"]) == 2
        assert len(config["citations"]) == 2
        assert config["author"] == "AI Cyber Assessment"
    
    def test_missing_presentation_field_rejected(self, pptx_tool):
        """Test that missing presentation field is rejected."""
        payload = {"not_presentation": {}}
        
        with pytest.raises(ValueError) as exc_info:
            pptx_tool.validate_presentation_data(payload)
        
        assert "Missing required field: presentation" in str(exc_info.value)
    
    def test_missing_title_rejected(self, pptx_tool):
        """Test that missing title is rejected."""
        payload = {
            "presentation": {
                "slides": []
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            pptx_tool.validate_presentation_data(payload)
        
        assert "Missing required presentation field: title" in str(exc_info.value)
    
    def test_missing_slides_rejected(self, pptx_tool):
        """Test that missing slides are rejected."""
        payload = {
            "presentation": {
                "title": "Test Presentation"
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            pptx_tool.validate_presentation_data(payload)
        
        assert "Missing required presentation field: slides" in str(exc_info.value)
    
    def test_empty_slides_rejected(self, pptx_tool):
        """Test that empty slides array is rejected."""
        payload = {
            "presentation": {
                "title": "Test Presentation",
                "slides": []
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            pptx_tool.validate_presentation_data(payload)
        
        assert "must contain at least one slide" in str(exc_info.value)
    
    def test_invalid_slide_structure_rejected(self, pptx_tool):
        """Test that invalid slide structures are rejected."""
        payload = {
            "presentation": {
                "title": "Test Presentation",
                "slides": ["not_a_dict"]
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            pptx_tool.validate_presentation_data(payload)
        
        assert "Slide 0 must be a dictionary" in str(exc_info.value)
    
    def test_slide_missing_type_rejected(self, pptx_tool):
        """Test that slides missing type are rejected."""
        payload = {
            "presentation": {
                "title": "Test Presentation",
                "slides": [{"title": "Test Slide"}]
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            pptx_tool.validate_presentation_data(payload)
        
        assert "Slide 0 missing required field: type" in str(exc_info.value)
    
    def test_unsupported_slide_type_rejected(self, pptx_tool):
        """Test that unsupported slide types are rejected."""
        payload = {
            "presentation": {
                "title": "Test Presentation",
                "slides": [{"type": "unsupported_type"}]
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            pptx_tool.validate_presentation_data(payload)
        
        assert "unsupported type: unsupported_type" in str(exc_info.value)
    
    def test_default_values_applied(self, pptx_tool):
        """Test that default values are applied correctly."""
        payload = {
            "presentation": {
                "title": "Test Presentation",
                "slides": [{"type": "content"}]
            }
        }
        
        config = pptx_tool.validate_presentation_data(payload)
        
        assert config["subtitle"] == ""
        assert config["author"] == "AI Cyber Maturity Assessment"
        assert config["branding"] == {}
        assert config["citations"] == []
        assert config["template"] == "default"


class TestSlideTemplates:
    """Test slide template configuration."""
    
    def test_slide_templates_available(self, pptx_tool):
        """Test that expected slide templates are available."""
        expected_templates = ["title", "content", "two_content", "blank"]
        
        for template in expected_templates:
            assert template in pptx_tool.SLIDE_TEMPLATES
            assert "layout_index" in pptx_tool.SLIDE_TEMPLATES[template]
            assert "placeholders" in pptx_tool.SLIDE_TEMPLATES[template]
    
    def test_default_colors_configured(self, pptx_tool):
        """Test that default colors are properly configured."""
        colors = pptx_tool.DEFAULT_COLORS
        
        expected_colors = ["primary", "secondary", "accent", "text", "background"]
        for color in expected_colors:
            assert color in colors
            assert isinstance(colors[color], tuple)
            assert len(colors[color]) == 3  # RGB tuple


class TestMockMode:
    """Test mock mode functionality when PPTX dependencies unavailable."""
    
    def test_mock_presentation_creation(self, pptx_tool):
        """Test mock presentation creation."""
        config = {
            "title": "Test Presentation",
            "slides": [{"type": "content"}, {"type": "title"}],
            "citations": []
        }
        
        # Force mock mode
        with patch('services.mcp_gateway.tools.pptx_render.PPTX_DEPS_AVAILABLE', False):
            mock_prs = pptx_tool.create_presentation(config)
        
        assert mock_prs["mock_mode"] is True
        assert mock_prs["title"] == "Test Presentation"
        assert mock_prs["slide_count"] == 4  # 2 content + 1 title + 1 citations
    
    def test_mock_save_base64(self, pptx_tool):
        """Test mock save to base64 format."""
        with patch('services.mcp_gateway.tools.pptx_render.PPTX_DEPS_AVAILABLE', False):
            result = pptx_tool._mock_save_presentation("base64")
        
        assert result["format"] == "base64"
        assert "data" in result
        assert "filename" in result
        assert result["mock_mode"] is True
        assert result["filename"].endswith(".pptx")
    
    def test_mock_save_file(self, pptx_tool):
        """Test mock save to file format."""
        with patch('services.mcp_gateway.tools.pptx_render.PPTX_DEPS_AVAILABLE', False):
            result = pptx_tool._mock_save_presentation("file")
        
        assert result["format"] == "file"
        assert "path" in result
        assert "filename" in result
        assert result["mock_mode"] is True


class TestPPTXRenderExecution:
    """Test full PPTX render execution."""
    
    @pytest.mark.asyncio
    async def test_successful_presentation_render(self, pptx_tool, sample_presentation_data):
        """Test successful presentation rendering."""
        sample_presentation_data["output_format"] = "base64"
        
        result = await pptx_tool.execute(sample_presentation_data, "test-engagement", "test-call")
        
        # Check success response
        assert result["success"] is True
        assert result["tool"] == "pptx.render"
        assert result["call_id"] == "test-call"
        assert result["engagement_id"] == "test-engagement"
        
        # Check presentation data
        assert "presentation" in result
        presentation = result["presentation"]
        assert presentation["format"] == "base64"
        assert "data" in presentation
        assert presentation["filename"].endswith(".pptx")
        
        # Check metadata
        metadata = result["metadata"]
        assert metadata["title"] == "Cyber Maturity Roadmap"
        assert metadata["slide_count"] == 4  # 2 content + 1 title + 1 citations
        assert metadata["citations_count"] == 2
    
    @pytest.mark.asyncio
    async def test_file_output_format(self, pptx_tool, sample_presentation_data):
        """Test presentation rendering with file output format."""
        sample_presentation_data["output_format"] = "file"
        
        result = await pptx_tool.execute(sample_presentation_data, "test-engagement", "test-call")
        
        assert result["success"] is True
        presentation = result["presentation"]
        assert presentation["format"] == "file"
        assert "path" in presentation
    
    @pytest.mark.asyncio
    async def test_missing_presentation_data_fails(self, pptx_tool):
        """Test that missing presentation data causes failure."""
        payload = {"output_format": "base64"}
        
        result = await pptx_tool.execute(payload, "test-engagement", "test-call")
        
        assert result["success"] is False
        assert "Missing required field: presentation" in result["error"]
    
    @pytest.mark.asyncio
    async def test_invalid_output_format_fails(self, pptx_tool, sample_presentation_data):
        """Test that invalid output format causes failure."""
        sample_presentation_data["output_format"] = "invalid_format"
        
        result = await pptx_tool.execute(sample_presentation_data, "test-engagement", "test-call")
        
        assert result["success"] is False
        assert "output_format must be" in result["error"]
    
    @pytest.mark.asyncio
    async def test_processing_time_tracked(self, pptx_tool, sample_presentation_data):
        """Test that processing time is tracked."""
        result = await pptx_tool.execute(sample_presentation_data, "test-engagement", "test-call")
        
        assert result["success"] is True
        assert "processing_time_seconds" in result
        assert isinstance(result["processing_time_seconds"], (int, float))
        assert result["processing_time_seconds"] >= 0


class TestToolRegistration:
    """Test tool registration functionality."""
    
    def test_tool_registration(self):
        """Test that PPTX render tool can be registered properly."""
        from services.mcp_gateway.tools.pptx_render import register_tool
        
        tool_registry = {}
        register_tool(tool_registry)
        
        assert "pptx.render" in tool_registry
        assert tool_registry["pptx.render"] == PPTXRenderTool


class TestPresentationContent:
    """Test specific presentation content handling."""
    
    def test_minimal_presentation_valid(self, pptx_tool):
        """Test that minimal presentation data is valid."""
        payload = {
            "presentation": {
                "title": "Minimal Presentation",
                "slides": [
                    {"type": "content", "title": "Single Slide"}
                ]
            }
        }
        
        config = pptx_tool.validate_presentation_data(payload)
        
        assert config["title"] == "Minimal Presentation"
        assert len(config["slides"]) == 1
        assert config["citations"] == []
    
    def test_complex_presentation_valid(self, pptx_tool):
        """Test that complex presentation data is valid."""
        payload = {
            "presentation": {
                "title": "Complex Presentation",
                "subtitle": "Detailed Analysis",
                "author": "Security Team",
                "slides": [
                    {"type": "title"},
                    {"type": "content", "title": "Content Slide"},
                    {"type": "two_content", "title": "Two Column Slide"},
                    {"type": "blank"}
                ],
                "citations": [
                    {"title": "Source 1", "source": "Author 1"},
                    {"title": "Source 2", "source": "Author 2", "date": "2024"}
                ],
                "branding": {
                    "colors": {"primary": (255, 0, 0)}
                },
                "template": "executive"
            }
        }
        
        config = pptx_tool.validate_presentation_data(payload)
        
        assert config["title"] == "Complex Presentation"
        assert config["subtitle"] == "Detailed Analysis"
        assert config["author"] == "Security Team"
        assert len(config["slides"]) == 4
        assert len(config["citations"]) == 2
        assert config["template"] == "executive"