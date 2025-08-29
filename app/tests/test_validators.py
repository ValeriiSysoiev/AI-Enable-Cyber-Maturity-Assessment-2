"""
Tests for input validation utilities
"""

import pytest
from fastapi import HTTPException
from api.validators import (
    validate_email,
    validate_engagement_id,
    validate_tenant_id,
    validate_name,
    validate_description,
    validate_url,
    validate_safe_string,
    sanitize_dict,
    MAX_EMAIL_LENGTH,
    MAX_ENGAGEMENT_ID_LENGTH,
    MAX_NAME_LENGTH,
    MAX_DESCRIPTION_LENGTH
)


class TestEmailValidation:
    def test_valid_email(self):
        assert validate_email("user@example.com") == "user@example.com"
        assert validate_email("USER@EXAMPLE.COM") == "user@example.com"
        assert validate_email("  user@example.com  ") == "user@example.com"
        assert validate_email("user+tag@example.co.uk") == "user+tag@example.co.uk"
    
    def test_invalid_email(self):
        with pytest.raises(HTTPException) as exc:
            validate_email("")
        assert exc.value.status_code == 422
        
        with pytest.raises(HTTPException) as exc:
            validate_email("not-an-email")
        assert exc.value.status_code == 422
        
        with pytest.raises(HTTPException) as exc:
            validate_email("@example.com")
        assert exc.value.status_code == 422
        
        with pytest.raises(HTTPException) as exc:
            validate_email("user@")
        assert exc.value.status_code == 422
    
    def test_email_length_limit(self):
        # MAX_EMAIL_LENGTH is 254, so create an email longer than that
        long_email = "a" * 250 + "@example.com"  # This will be 262 chars total
        with pytest.raises(HTTPException) as exc:
            validate_email(long_email)
        assert exc.value.status_code == 422
        assert "exceeds maximum length" in str(exc.value.detail)
    
    def test_email_injection_prevention(self):
        # Test various injection attempts
        with pytest.raises(HTTPException):
            validate_email("user@example.com<script>alert(1)</script>")
        
        with pytest.raises(HTTPException):
            validate_email("user'; DROP TABLE users--@example.com")


class TestEngagementIdValidation:
    def test_valid_engagement_id(self):
        assert validate_engagement_id("eng-123") == "eng-123"
        assert validate_engagement_id("ENG_2023_PROD") == "ENG_2023_PROD"
        assert validate_engagement_id("a1b2c3") == "a1b2c3"
    
    def test_invalid_engagement_id(self):
        # Empty or wrong type
        with pytest.raises(HTTPException):
            validate_engagement_id("")
        
        with pytest.raises(HTTPException):
            validate_engagement_id(None)
        
        # Invalid characters
        with pytest.raises(HTTPException) as exc:
            validate_engagement_id("eng 123")  # Contains space
        assert "alphanumeric" in str(exc.value.detail)
        
        with pytest.raises(HTTPException):
            validate_engagement_id("eng@123")  # Contains @
        
        with pytest.raises(HTTPException):
            validate_engagement_id("-eng123")  # Starts with hyphen
        
        with pytest.raises(HTTPException):
            validate_engagement_id("eng123-")  # Ends with hyphen
    
    def test_engagement_id_length_limit(self):
        long_id = "a" * (MAX_ENGAGEMENT_ID_LENGTH + 1)
        with pytest.raises(HTTPException) as exc:
            validate_engagement_id(long_id)
        assert "exceeds maximum length" in str(exc.value.detail)
    
    def test_engagement_id_injection_prevention(self):
        with pytest.raises(HTTPException):
            validate_engagement_id("'; DROP TABLE engagements--")
        
        with pytest.raises(HTTPException):
            validate_engagement_id("../../../etc/passwd")


class TestTenantIdValidation:
    def test_valid_tenant_id(self):
        valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
        assert validate_tenant_id(valid_uuid) == valid_uuid
        
        # Should handle uppercase
        upper_uuid = "123E4567-E89B-12D3-A456-426614174000"
        assert validate_tenant_id(upper_uuid) == valid_uuid
    
    def test_invalid_tenant_id(self):
        # Not a UUID
        with pytest.raises(HTTPException):
            validate_tenant_id("not-a-uuid")
        
        # Wrong length
        with pytest.raises(HTTPException):
            validate_tenant_id("123e4567-e89b")
        
        # Invalid format
        with pytest.raises(HTTPException):
            validate_tenant_id("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
    
    def test_optional_tenant_id(self):
        assert validate_tenant_id(None) is None
        assert validate_tenant_id("") is None


class TestNameValidation:
    def test_valid_name(self):
        assert validate_name("John Doe") == "John Doe"
        assert validate_name("Project-2023_v1.0") == "Project-2023_v1.0"
        assert validate_name("Assessment Name") == "Assessment Name"
    
    def test_invalid_name(self):
        # Too short
        with pytest.raises(HTTPException) as exc:
            validate_name("a")
        assert "at least 2 characters" in str(exc.value.detail)
        
        # Invalid characters
        with pytest.raises(HTTPException):
            validate_name("Name<script>")
        
        with pytest.raises(HTTPException):
            validate_name("Name'; DROP--")
        
        # Wrong start/end
        with pytest.raises(HTTPException):
            validate_name("-Name")
        
        with pytest.raises(HTTPException):
            validate_name("Name-")
    
    def test_name_length_limit(self):
        long_name = "a" * (MAX_NAME_LENGTH + 1)
        with pytest.raises(HTTPException) as exc:
            validate_name(long_name)
        assert "exceeds maximum length" in str(exc.value.detail)


class TestDescriptionValidation:
    def test_valid_description(self):
        assert validate_description("This is a valid description.") == "This is a valid description."
        assert validate_description("Description with punctuation: yes, it's valid!") == "Description with punctuation: yes, it's valid!"
        assert validate_description("") is None
        assert validate_description(None) is None
    
    def test_invalid_description(self):
        # Invalid characters
        with pytest.raises(HTTPException):
            validate_description("Description<script>alert(1)</script>")
        
        with pytest.raises(HTTPException):
            validate_description("Description`rm -rf /`")
    
    def test_description_length_limit(self):
        long_desc = "a" * (MAX_DESCRIPTION_LENGTH + 1)
        with pytest.raises(HTTPException) as exc:
            validate_description(long_desc)
        assert "exceeds maximum length" in str(exc.value.detail)


class TestUrlValidation:
    def test_valid_url(self):
        assert validate_url("https://example.com") == "https://example.com"
        assert validate_url("http://sub.example.com/path") == "http://sub.example.com/path"
        assert validate_url("https://example.com:8080/path?query=1") == "https://example.com:8080/path?query=1"
    
    def test_invalid_url(self):
        # Not a URL
        with pytest.raises(HTTPException):
            validate_url("not-a-url")
        
        # No protocol
        with pytest.raises(HTTPException):
            validate_url("example.com")
        
        # Invalid protocol
        with pytest.raises(HTTPException):
            validate_url("ftp://example.com")
        
        with pytest.raises(HTTPException):
            validate_url("javascript:alert(1)")
    
    def test_url_injection_prevention(self):
        with pytest.raises(HTTPException):
            validate_url("https://example.com/<script>")
        
        with pytest.raises(HTTPException):
            validate_url("https://example.com/\\x00")


class TestSafeStringValidation:
    def test_valid_safe_string(self):
        assert validate_safe_string("valid string") == "valid string"
        assert validate_safe_string("string-with_special.chars") == "string-with_special.chars"
        assert validate_safe_string("123") == "123"
    
    def test_invalid_safe_string(self):
        # Invalid characters
        with pytest.raises(HTTPException):
            validate_safe_string("string<script>")
        
        with pytest.raises(HTTPException):
            validate_safe_string("string'; DROP--")
        
        with pytest.raises(HTTPException):
            validate_safe_string("string@example")
        
        # Empty when not allowed
        with pytest.raises(HTTPException):
            validate_safe_string("", allow_empty=False)
    
    def test_safe_string_allow_empty(self):
        assert validate_safe_string("", allow_empty=True) == ""


class TestDictSanitization:
    def test_sanitize_simple_dict(self):
        input_dict = {
            "name": "John Doe",
            "age": 30,
            "active": True
        }
        result = sanitize_dict(input_dict)
        assert result == input_dict
    
    def test_sanitize_nested_dict(self):
        input_dict = {
            "user": {
                "name": "John",
                "email": "john@example.com"
            },
            "settings": {
                "theme": "dark"
            }
        }
        result = sanitize_dict(input_dict)
        assert result["user"]["name"] == "John"
        assert result["settings"]["theme"] == "dark"
    
    def test_sanitize_invalid_chars(self):
        input_dict = {
            "safe_key": "safe_value",
            "unsafe": "value<script>"
        }
        with pytest.raises(HTTPException):
            sanitize_dict(input_dict)
    
    def test_sanitize_deep_nesting(self):
        # Create deeply nested dict
        deep_dict = {"level1": {"level2": {"level3": {"level4": {"level5": {"level6": "value"}}}}}}
        
        with pytest.raises(HTTPException) as exc:
            sanitize_dict(deep_dict, max_depth=5)
        assert "too deeply nested" in str(exc.value.detail)
    
    def test_sanitize_list_values(self):
        input_dict = {
            "items": ["item1", "item2", "item3"],
            "nested": [{"name": "test"}]
        }
        result = sanitize_dict(input_dict)
        assert result["items"] == ["item1", "item2", "item3"]
        assert result["nested"][0]["name"] == "test"