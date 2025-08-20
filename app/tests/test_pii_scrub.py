"""
Unit tests for PII Scrubbing MCP Tool.
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timezone

from services.mcp_gateway.tools.pii_scrub import PIIScrubberTool
from services.mcp_gateway.config import MCPConfig


@pytest.fixture
def mock_config():
    """Mock MCP configuration for testing."""
    config = Mock(spec=MCPConfig)
    return config


@pytest.fixture
def pii_tool(mock_config):
    """PII scrubber tool instance for testing."""
    return PIIScrubberTool(mock_config)


@pytest.fixture
def sample_pii_text():
    """Sample text containing various PII patterns."""
    return """
    Contact John Doe at john.doe@company.com or call (555) 123-4567.
    His SSN is 123-45-6789 and credit card number is 4532-1234-5678-9012.
    Driver license: CA1234567. 
    AWS Key: AKIAIOSFODNN7EXAMPLE
    IP Address: 192.168.1.100
    """


class TestPIIPatternCompilation:
    """Test PII pattern compilation and validation."""
    
    def test_default_patterns_compile_successfully(self, pii_tool):
        """Test that all default patterns compile without errors."""
        assert len(pii_tool.compiled_patterns) > 0
        
        # Check that key patterns are present
        expected_patterns = [
            "email_address", "us_ssn", "credit_card", 
            "phone_us", "aws_access_key", "ip_address"
        ]
        
        for pattern in expected_patterns:
            assert pattern in pii_tool.compiled_patterns
            assert "regex" in pii_tool.compiled_patterns[pattern]
            assert "replacement" in pii_tool.compiled_patterns[pattern]
    
    def test_pattern_replacement_tokens(self, pii_tool):
        """Test that replacement tokens are properly configured."""
        expected_replacements = {
            "email_address": "[REDACTED-EMAIL]",
            "us_ssn": "[REDACTED-SSN]",
            "credit_card": "[REDACTED-CREDIT-CARD]",
            "phone_us": "[REDACTED-PHONE]",
            "aws_access_key": "[REDACTED-AWS-KEY]"
        }
        
        for pattern, expected_token in expected_replacements.items():
            assert pii_tool.compiled_patterns[pattern]["replacement"] == expected_token


class TestScrubConfigValidation:
    """Test scrub configuration validation."""
    
    def test_default_config_validation(self, pii_tool):
        """Test validation with default configuration."""
        payload = {}
        
        config = pii_tool.validate_scrub_config(payload)
        
        # Check defaults
        assert config["case_sensitive"] is False
        assert config["preserve_format"] is True
        assert config["audit_redactions"] is True
        assert config["replacement_strategy"] == "token"
        assert isinstance(config["enabled_patterns"], list)
        assert len(config["enabled_patterns"]) > 0
    
    def test_custom_config_validation(self, pii_tool):
        """Test validation with custom configuration."""
        payload = {
            "scrub_config": {
                "enabled_patterns": ["email_address", "us_ssn"],
                "case_sensitive": True,
                "audit_redactions": False,
                "custom_patterns": {
                    "employee_id": {
                        "pattern": r"EMP\d{6}",
                        "replacement": "[REDACTED-EMP-ID]",
                        "description": "Employee ID pattern"
                    }
                }
            }
        }
        
        config = pii_tool.validate_scrub_config(payload)
        
        assert config["enabled_patterns"] == ["email_address", "us_ssn"]
        assert config["case_sensitive"] is True
        assert config["audit_redactions"] is False
        assert "employee_id" in config["custom_patterns"]
    
    def test_invalid_pattern_names_rejected(self, pii_tool):
        """Test that invalid pattern names are rejected."""
        payload = {
            "scrub_config": {
                "enabled_patterns": ["email_address", "invalid_pattern"]
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            pii_tool.validate_scrub_config(payload)
        
        assert "Unknown PII patterns" in str(exc_info.value)
    
    def test_invalid_custom_pattern_structure(self, pii_tool):
        """Test that invalid custom pattern structures are rejected."""
        payload = {
            "scrub_config": {
                "custom_patterns": {
                    "invalid_pattern": "not_a_dict"
                }
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            pii_tool.validate_scrub_config(payload)
        
        assert "must be a dictionary" in str(exc_info.value)
    
    def test_custom_pattern_missing_fields(self, pii_tool):
        """Test that custom patterns missing required fields are rejected."""
        payload = {
            "scrub_config": {
                "custom_patterns": {
                    "incomplete_pattern": {
                        "pattern": r"\d+"
                        # Missing replacement field
                    }
                }
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            pii_tool.validate_scrub_config(payload)
        
        assert "missing required field" in str(exc_info.value)
    
    def test_invalid_regex_patterns_rejected(self, pii_tool):
        """Test that invalid regex patterns are rejected."""
        payload = {
            "scrub_config": {
                "custom_patterns": {
                    "bad_regex": {
                        "pattern": r"[unclosed_bracket",
                        "replacement": "[REDACTED]"
                    }
                }
            }
        }
        
        with pytest.raises(ValueError) as exc_info:
            pii_tool.validate_scrub_config(payload)
        
        assert "Invalid regex" in str(exc_info.value)


class TestTextScrubbing:
    """Test text scrubbing functionality."""
    
    def test_email_redaction(self, pii_tool):
        """Test email address redaction."""
        text = "Contact me at user@example.com or admin@company.org"
        config = {"enabled_patterns": ["email_address"], "custom_patterns": {}}
        
        scrubbed_text, counts = pii_tool.scrub_text(text, config)
        
        assert "user@example.com" not in scrubbed_text
        assert "admin@company.org" not in scrubbed_text
        assert "[REDACTED-EMAIL]" in scrubbed_text
        assert counts["email_address"] == 2
    
    def test_ssn_redaction(self, pii_tool):
        """Test SSN redaction."""
        text = "SSN: 123-45-6789 and also 987 65 4321"
        config = {"enabled_patterns": ["us_ssn", "us_ssn_spaces"], "custom_patterns": {}}
        
        scrubbed_text, counts = pii_tool.scrub_text(text, config)
        
        assert "123-45-6789" not in scrubbed_text
        assert "987 65 4321" not in scrubbed_text
        assert "[REDACTED-SSN]" in scrubbed_text
        assert counts["us_ssn"] == 1
        assert counts["us_ssn_spaces"] == 1
    
    def test_credit_card_redaction(self, pii_tool):
        """Test credit card redaction."""
        text = "Card numbers: 4532-1234-5678-9012 and 4532123456789012"
        config = {"enabled_patterns": ["credit_card"], "custom_patterns": {}}
        
        scrubbed_text, counts = pii_tool.scrub_text(text, config)
        
        assert "4532-1234-5678-9012" not in scrubbed_text
        assert "4532123456789012" not in scrubbed_text
        assert "[REDACTED-CREDIT-CARD]" in scrubbed_text
        assert counts["credit_card"] == 2
    
    def test_phone_redaction(self, pii_tool):
        """Test phone number redaction."""
        text = "Call me at 555-123-4567 or (555) 987-6543"
        config = {"enabled_patterns": ["phone_us", "phone_us_parentheses"], "custom_patterns": {}}
        
        scrubbed_text, counts = pii_tool.scrub_text(text, config)
        
        assert "555-123-4567" not in scrubbed_text
        assert "(555) 987-6543" not in scrubbed_text
        assert "[REDACTED-PHONE]" in scrubbed_text
        assert counts["phone_us"] == 1
        assert counts["phone_us_parentheses"] == 1
    
    def test_aws_key_redaction(self, pii_tool):
        """Test AWS access key redaction."""
        text = "AWS Key: AKIAIOSFODNN7EXAMPLE"
        config = {"enabled_patterns": ["aws_access_key"], "custom_patterns": {}}
        
        scrubbed_text, counts = pii_tool.scrub_text(text, config)
        
        assert "AKIAIOSFODNN7EXAMPLE" not in scrubbed_text
        assert "[REDACTED-AWS-KEY]" in scrubbed_text
        assert counts["aws_access_key"] == 1
    
    def test_ip_address_redaction(self, pii_tool):
        """Test IP address redaction."""
        text = "Server IP: 192.168.1.100 and public IP: 203.0.113.1"
        config = {"enabled_patterns": ["ip_address"], "custom_patterns": {}}
        
        scrubbed_text, counts = pii_tool.scrub_text(text, config)
        
        assert "192.168.1.100" not in scrubbed_text
        assert "203.0.113.1" not in scrubbed_text
        assert "[REDACTED-IP]" in scrubbed_text
        assert counts["ip_address"] == 2
    
    def test_custom_pattern_redaction(self, pii_tool):
        """Test custom pattern redaction."""
        text = "Employee IDs: EMP123456 and EMP654321"
        config = {
            "enabled_patterns": ["employee_id"],
            "custom_patterns": {
                "employee_id": {
                    "pattern": r"EMP\d{6}",
                    "replacement": "[REDACTED-EMP-ID]"
                }
            }
        }
        
        scrubbed_text, counts = pii_tool.scrub_text(text, config)
        
        assert "EMP123456" not in scrubbed_text
        assert "EMP654321" not in scrubbed_text
        assert "[REDACTED-EMP-ID]" in scrubbed_text
        assert counts["employee_id"] == 2
    
    def test_no_pii_text_unchanged(self, pii_tool):
        """Test that text without PII remains unchanged."""
        text = "This is a normal text without any sensitive information."
        config = {"enabled_patterns": ["email_address", "us_ssn"], "custom_patterns": {}}
        
        scrubbed_text, counts = pii_tool.scrub_text(text, config)
        
        assert scrubbed_text == text
        assert len(counts) == 0
    
    def test_empty_text_handling(self, pii_tool):
        """Test handling of empty or None text."""
        config = {"enabled_patterns": ["email_address"], "custom_patterns": {}}
        
        # Empty string
        scrubbed_text, counts = pii_tool.scrub_text("", config)
        assert scrubbed_text == ""
        assert len(counts) == 0
        
        # None
        scrubbed_text, counts = pii_tool.scrub_text(None, config)
        assert scrubbed_text is None
        assert len(counts) == 0


class TestStructuredDataScrubbing:
    """Test structured data scrubbing functionality."""
    
    def test_json_object_scrubbing(self, pii_tool):
        """Test scrubbing of JSON-like objects."""
        data = {
            "name": "John Doe",
            "email": "john.doe@company.com",
            "phone": "555-123-4567",
            "metadata": {
                "ip": "192.168.1.100",
                "ssn": "123-45-6789"
            }
        }
        config = {
            "enabled_patterns": ["email_address", "phone_us", "ip_address", "us_ssn"],
            "custom_patterns": {}
        }
        
        scrubbed_data, counts = pii_tool.scrub_structured_data(data, config)
        
        # Check that PII was redacted
        assert scrubbed_data["email"] == "[REDACTED-EMAIL]"
        assert scrubbed_data["phone"] == "[REDACTED-PHONE]"
        assert scrubbed_data["metadata"]["ip"] == "[REDACTED-IP]"
        assert scrubbed_data["metadata"]["ssn"] == "[REDACTED-SSN]"
        
        # Check that non-PII data remains
        assert scrubbed_data["name"] == "John Doe"
        
        # Check counts
        assert counts["email_address"] == 1
        assert counts["phone_us"] == 1
        assert counts["ip_address"] == 1
        assert counts["us_ssn"] == 1
    
    def test_nested_array_scrubbing(self, pii_tool):
        """Test scrubbing of nested arrays."""
        data = {
            "contacts": [
                {"email": "user1@example.com", "phone": "555-111-2222"},
                {"email": "user2@example.com", "phone": "555-333-4444"}
            ]
        }
        config = {"enabled_patterns": ["email_address", "phone_us"], "custom_patterns": {}}
        
        scrubbed_data, counts = pii_tool.scrub_structured_data(data, config)
        
        # Check that all emails and phones were redacted
        for contact in scrubbed_data["contacts"]:
            assert contact["email"] == "[REDACTED-EMAIL]"
            assert contact["phone"] == "[REDACTED-PHONE]"
        
        # Check total counts
        assert counts["email_address"] == 2
        assert counts["phone_us"] == 2


class TestRedactionReporting:
    """Test redaction reporting functionality."""
    
    def test_redaction_report_structure(self, pii_tool):
        """Test redaction report structure and content."""
        redaction_counts = {
            "email_address": 3,
            "us_ssn": 1,
            "credit_card": 2,
            "phone_us": 1
        }
        config = {"enabled_patterns": list(redaction_counts.keys()), "custom_patterns": {}}
        
        report = pii_tool.generate_redaction_report(redaction_counts, config)
        
        # Check basic structure
        assert "total_redactions" in report
        assert "redaction_counts" in report
        assert "category_breakdown" in report
        assert "patterns_used" in report
        assert "config_applied" in report
        assert "timestamp" in report
        
        # Check calculated values
        assert report["total_redactions"] == 7  # 3+1+2+1
        assert report["redaction_counts"] == redaction_counts
        assert set(report["patterns_used"]) == set(redaction_counts.keys())
    
    def test_category_breakdown(self, pii_tool):
        """Test category breakdown in redaction reports."""
        redaction_counts = {
            "email_address": 2,  # identity category
            "credit_card": 1,    # financial category
            "phone_us": 1,       # contact category
            "ip_address": 1      # technical category
        }
        config = {"enabled_patterns": list(redaction_counts.keys()), "custom_patterns": {}}
        
        report = pii_tool.generate_redaction_report(redaction_counts, config)
        
        category_breakdown = report["category_breakdown"]
        
        # Check expected categories
        assert category_breakdown["identity"] == 2  # email_address
        assert category_breakdown["financial"] == 1  # credit_card
        assert category_breakdown["contact"] == 1   # phone_us
        assert category_breakdown["technical"] == 1  # ip_address
    
    def test_empty_redaction_report(self, pii_tool):
        """Test redaction report with no redactions."""
        redaction_counts = {}
        config = {"enabled_patterns": ["email_address"], "custom_patterns": {}}
        
        report = pii_tool.generate_redaction_report(redaction_counts, config)
        
        assert report["total_redactions"] == 0
        assert report["redaction_counts"] == {}
        assert len(report["category_breakdown"]) == 0
        assert len(report["patterns_used"]) == 0


class TestPIIScrubberExecution:
    """Test full PII scrubber execution."""
    
    @pytest.mark.asyncio
    async def test_successful_text_scrubbing(self, pii_tool, sample_pii_text):
        """Test successful text scrubbing execution."""
        payload = {
            "content": sample_pii_text,
            "content_type": "text",
            "scrub_config": {
                "enabled_patterns": ["email_address", "phone_us_parentheses", "us_ssn", "credit_card", "aws_access_key", "ip_address"]
            }
        }
        
        result = await pii_tool.execute(payload, "test-engagement", "test-call")
        
        # Check success response
        assert result["success"] is True
        assert result["tool"] == "pii.scrub"
        assert "scrubbed_content" in result
        assert "redaction_report" in result
        
        # Check that PII was actually redacted
        scrubbed_content = result["scrubbed_content"]
        assert "john.doe@company.com" not in scrubbed_content
        assert "123-45-6789" not in scrubbed_content
        assert "4532-1234-5678-9012" not in scrubbed_content
        
        # Check redaction report
        report = result["redaction_report"]
        assert report["total_redactions"] > 0
        assert len(report["redaction_counts"]) > 0
    
    @pytest.mark.asyncio
    async def test_successful_json_scrubbing(self, pii_tool):
        """Test successful JSON scrubbing execution."""
        payload = {
            "content": {
                "user": {
                    "email": "user@example.com",
                    "ssn": "123-45-6789"
                }
            },
            "content_type": "json",
            "scrub_config": {
                "enabled_patterns": ["email_address", "us_ssn"]
            }
        }
        
        result = await pii_tool.execute(payload, "test-engagement", "test-call")
        
        assert result["success"] is True
        assert result["scrubbed_content"]["user"]["email"] == "[REDACTED-EMAIL]"
        assert result["scrubbed_content"]["user"]["ssn"] == "[REDACTED-SSN]"
    
    @pytest.mark.asyncio
    async def test_missing_content_error(self, pii_tool):
        """Test error handling for missing content."""
        payload = {
            "content_type": "text",
            "scrub_config": {}
        }
        
        result = await pii_tool.execute(payload, "test-engagement", "test-call")
        
        assert result["success"] is False
        assert "Missing required field: content" in result["error"]
    
    @pytest.mark.asyncio
    async def test_unsupported_content_type_error(self, pii_tool):
        """Test error handling for unsupported content types."""
        payload = {
            "content": "test content",
            "content_type": "unsupported_type"
        }
        
        result = await pii_tool.execute(payload, "test-engagement", "test-call")
        
        assert result["success"] is False
        assert "Unsupported content_type" in result["error"]
    
    @pytest.mark.asyncio
    async def test_invalid_content_for_type_error(self, pii_tool):
        """Test error handling for invalid content for specified type."""
        payload = {
            "content": {"not": "a string"},
            "content_type": "text"
        }
        
        result = await pii_tool.execute(payload, "test-engagement", "test-call")
        
        assert result["success"] is False
        assert "Content must be a string" in result["error"]


class TestToolRegistration:
    """Test tool registration functionality."""
    
    def test_tool_registration(self):
        """Test that PII scrubber tool can be registered properly."""
        from services.mcp_gateway.tools.pii_scrub import register_tool
        
        tool_registry = {}
        register_tool(tool_registry)
        
        assert "pii.scrub" in tool_registry
        assert tool_registry["pii.scrub"] == PIIScrubberTool