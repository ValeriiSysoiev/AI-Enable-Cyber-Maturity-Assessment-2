"""
Comprehensive security tests for MCP Gateway v1.3
Tests for Sprint v1.3 security requirements including:
- Tool allowlist per engagement with cross-tenant isolation
- Path traversal prevention
- Oversize payload protection
- MIME type validation
- Secret redaction
- Request/response size limits
"""

import pytest
import tempfile
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, patch

from security import (
    SecurityValidator, 
    PathSecurityError, 
    CrossTenantError, 
    MimeTypeError
)
from secret_redactor import SecretRedactor, RedactionStats
from mcp_tools.fs_tools import FsReadTool, FsWriteTool, FsListTool
from mcp_tools import McpError

class TestCrossTenantIsolation:
    """Test engagement isolation and cross-tenant access prevention"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.validator = SecurityValidator(self.temp_dir, max_file_size_mb=1)
        
        # Set up test engagements
        self.engagement_a = "engagement_alpha"
        self.engagement_b = "engagement_beta"
        
        # Configure different allowlists for each engagement
        self.validator.set_engagement_allowlist(self.engagement_a, {'fs.read', 'fs.write'})
        self.validator.set_engagement_allowlist(self.engagement_b, {'fs.read', 'search.vector'})
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_engagement_tool_allowlist_enforcement(self):
        """Test that engagements can only access allowed tools"""
        # Engagement A should be able to access fs.write
        self.validator.validate_tool_access('fs.write', self.engagement_a)
        
        # Engagement B should NOT be able to access fs.write
        with pytest.raises(CrossTenantError, match="not allowed for engagement"):
            self.validator.validate_tool_access('fs.write', self.engagement_b)
        
        # Engagement B should be able to access search.vector
        self.validator.validate_tool_access('search.vector', self.engagement_b)
        
        # Engagement A should NOT be able to access search.vector
        with pytest.raises(CrossTenantError, match="not allowed for engagement"):
            self.validator.validate_tool_access('search.vector', self.engagement_a)
    
    def test_cross_tenant_data_access_prevention(self):
        """Test that engagements cannot access each other's data"""
        with pytest.raises(CrossTenantError, match="Cross-tenant access denied"):
            self.validator.prevent_cross_tenant_access(self.engagement_a, self.engagement_b)
    
    def test_engagement_path_isolation(self):
        """Test that engagement paths are properly isolated"""
        path_a = self.validator.get_safe_engagement_path(self.engagement_a)
        path_b = self.validator.get_safe_engagement_path(self.engagement_b)
        
        # Paths should be different
        assert path_a != path_b
        
        # Both should be under data root
        assert str(path_a).startswith(str(self.validator.data_root))
        assert str(path_b).startswith(str(self.validator.data_root))
        
        # Neither should be able to access the other's parent
        assert not str(path_a).startswith(str(path_b))
        assert not str(path_b).startswith(str(path_a))

class TestPathTraversalAttacks:
    """Test path traversal attack prevention (should fail attacks)"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.validator = SecurityValidator(self.temp_dir, max_file_size_mb=1)
        self.engagement_id = "test_engagement"
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.parametrize("malicious_path", [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "file.txt/../../../etc/shadow",
        "folder/../../../home/user/.ssh/id_rsa",
        "~/../../etc/passwd",
        "/etc/passwd",
        "/proc/self/environ",
        "/sys/class/net/eth0/address",
        "${HOME}/../../../etc/passwd",
        "`cat /etc/passwd`",
        "$(cat /etc/passwd)",
        "file.txt\x00/etc/passwd",  # Null byte injection
        "....//....//etc/passwd",   # Double encoding
        "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoding
    ])
    def test_path_traversal_attacks_blocked(self, malicious_path):
        """Test that various path traversal attacks are blocked"""
        with pytest.raises(PathSecurityError, match="Dangerous pattern detected|outside"):
            self.validator.validate_file_path(malicious_path, self.engagement_id)
    
    def test_symbolic_link_attacks_blocked(self):
        """Test that symbolic link attacks are blocked"""
        # Create engagement directory
        eng_path = self.validator.get_safe_engagement_path(self.engagement_id)
        eng_path.mkdir(parents=True, exist_ok=True)
        
        # Create a regular file
        regular_file = eng_path / "regular.txt"
        regular_file.write_text("safe content")
        
        # Create a symbolic link (if supported)
        symlink_file = eng_path / "malicious_link.txt"
        try:
            symlink_file.symlink_to("/etc/passwd")
            
            # Validation should detect and block the symlink
            with pytest.raises(PathSecurityError, match="Symlinks are not allowed"):
                self.validator.validate_file_path("malicious_link.txt", self.engagement_id)
        except OSError:
            # Skip if symlinks not supported
            pytest.skip("Symlinks not supported on this system")

class TestOversizePayloadProtection:
    """Test protection against oversized payloads"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        # Set very small limits for testing
        self.validator = SecurityValidator(
            self.temp_dir, 
            max_file_size_mb=1,  # 1MB file limit
            max_request_size_mb=2  # 2MB request limit
        )
        self.engagement_id = "test_engagement"
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_oversized_file_content_blocked(self):
        """Test that oversized file content is blocked"""
        # Create content larger than limit (1MB)
        large_content = "x" * (2 * 1024 * 1024)  # 2MB
        
        with pytest.raises(PathSecurityError, match="Content size.*exceeds limit"):
            self.validator.validate_content_size(large_content)
    
    def test_oversized_request_payload_blocked(self):
        """Test that oversized request payloads are blocked"""
        # Create a large dictionary
        large_payload = {
            "data": "x" * (3 * 1024 * 1024),  # 3MB of data
            "metadata": {"key": "value"}
        }
        
        with pytest.raises(PathSecurityError, match="Request/response size.*exceeds limit"):
            self.validator.validate_request_size(large_payload)
    
    @pytest.mark.asyncio
    async def test_oversized_file_write_blocked(self):
        """Test that oversized file writes are blocked through fs.write tool"""
        write_tool = FsWriteTool(self.validator)
        
        # Try to write a file larger than the limit
        large_content = "x" * (2 * 1024 * 1024)  # 2MB
        
        with pytest.raises(McpError, match="Content size.*exceeds limit"):
            await write_tool.execute({
                "path": "large_file.txt",
                "content": large_content
            }, self.engagement_id)

class TestMimeTypeValidation:
    """Test MIME type validation and disallowed type blocking"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.validator = SecurityValidator(self.temp_dir, max_file_size_mb=1)
        self.engagement_id = "test_engagement"
        
        # Create engagement directory
        self.eng_path = self.validator.get_safe_engagement_path(self.engagement_id)
        self.eng_path.mkdir(parents=True, exist_ok=True)
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.parametrize("filename,expected_mime", [
        ("document.txt", "text/plain"),
        ("data.json", "application/json"),
        ("report.pdf", "application/pdf"),
        ("image.png", "image/png"),
        ("spreadsheet.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ])
    def test_allowed_mime_types_accepted(self, filename, expected_mime):
        """Test that allowed MIME types are accepted"""
        file_path = self.eng_path / filename
        mime_type = self.validator.validate_mime_type(file_path, allow_unknown=True)
        assert mime_type == expected_mime
    
    @pytest.mark.parametrize("filename", [
        "malicious.exe",
        "script.sh",
        "program.bat",
        "library.dll",
        "archive.zip",
        "compressed.tar.gz",
        "video.mp4",
        "audio.mp3",
    ])
    def test_disallowed_mime_types_blocked(self, filename):
        """Test that disallowed MIME types are blocked"""
        file_path = self.eng_path / filename
        
        with pytest.raises(MimeTypeError, match="MIME type.*not allowed"):
            self.validator.validate_mime_type(file_path, allow_unknown=False)
    
    @pytest.mark.asyncio
    async def test_disallowed_mime_type_write_blocked(self):
        """Test that writing disallowed MIME types is blocked"""
        write_tool = FsWriteTool(self.validator)
        
        # Try to write an executable file
        with pytest.raises(McpError, match="MIME type validation failed"):
            await write_tool.execute({
                "path": "malicious.exe",
                "content": "fake executable content"
            }, self.engagement_id)

class TestSecretRedaction:
    """Test comprehensive secret redaction functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.redactor = SecretRedactor(max_field_length=100, max_total_size=1000)
    
    def test_sensitive_field_redaction(self):
        """Test that sensitive fields are properly redacted"""
        sensitive_data = {
            "username": "john_doe",
            "password": "super_secret_123",
            "api_key": "sk_live_abcdef123456",
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "email": "user@example.com",
            "normal_field": "this should not be redacted"
        }
        
        redacted, stats = self.redactor.redact_data(sensitive_data, "test")
        
        # Sensitive fields should be redacted
        assert redacted["password"] == "[REDACTED]"
        assert redacted["api_key"] == "[REDACTED]"
        assert redacted["access_token"] == "[REDACTED]"
        
        # Normal fields should remain
        assert redacted["username"] == "john_doe"
        assert redacted["normal_field"] == "this should not be redacted"
        
        # Stats should reflect redactions
        assert stats.fields_redacted > 0
    
    def test_pattern_based_redaction(self):
        """Test that sensitive patterns are detected and redacted"""
        data_with_patterns = {
            "message": "Here's your token: sk_live_1234567890abcdef",
            "log": "Database connection: postgres://user:pass@host/db",
            "note": "JWT: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"
        }
        
        redacted, stats = self.redactor.redact_data(data_with_patterns, "test")
        
        # Patterns should be detected and redacted
        assert "[REDACTED_POTENTIAL_TOKEN]" in redacted["message"]
        assert "[REDACTED_URL_WITH_CREDENTIALS]" in redacted["log"]
        assert "[REDACTED_JWT_TOKEN]" in redacted["note"]
        
        # Stats should reflect pattern matches
        assert stats.patterns_matched > 0
    
    def test_oversized_content_truncation(self):
        """Test that oversized content is truncated"""
        large_data = {
            "big_field": "x" * 200,  # Exceeds max_field_length of 100
            "normal_field": "small content"
        }
        
        redacted, stats = self.redactor.redact_data(large_data, "test")
        
        # Large field should be truncated
        assert len(redacted["big_field"]) < len(large_data["big_field"])
        assert "[TRUNCATED" in redacted["big_field"]
        
        # Normal field should remain unchanged
        assert redacted["normal_field"] == "small content"
        
        # Stats should reflect truncation
        assert stats.content_truncated > 0
    
    def test_nested_data_redaction(self):
        """Test redaction of nested data structures"""
        nested_data = {
            "user": {
                "name": "John",
                "credentials": {
                    "password": "secret123",
                    "api_key": "sk_test_123"
                }
            },
            "logs": [
                {"message": "Login successful"},
                {"message": "Token: abc123def456", "sensitive": True}
            ]
        }
        
        redacted, stats = self.redactor.redact_data(nested_data, "test")
        
        # Nested sensitive fields should be redacted
        assert redacted["user"]["credentials"]["password"] == "[REDACTED]"
        assert redacted["user"]["credentials"]["api_key"] == "[REDACTED]"
        
        # Normal nested fields should remain
        assert redacted["user"]["name"] == "John"
        assert redacted["logs"][0]["message"] == "Login successful"

class TestFilePermissionSecurity:
    """Test that files are written with secure permissions"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.validator = SecurityValidator(self.temp_dir, max_file_size_mb=1)
        self.engagement_id = "test_engagement"
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_secure_file_permissions(self):
        """Test that files are written with secure permissions (no execute)"""
        write_tool = FsWriteTool(self.validator)
        
        # Write a file
        result = await write_tool.execute({
            "path": "test_file.txt",
            "content": "test content"
        }, self.engagement_id)
        
        assert result.success
        
        # Check file permissions
        file_path = self.validator.get_safe_engagement_path(self.engagement_id) / "test_file.txt"
        file_mode = file_path.stat().st_mode
        
        # File should be readable and writable by owner, but not executable
        # 0o644 = rw-r--r-- (owner: read/write, group/others: read-only)
        assert oct(file_mode)[-3:] == "644"
        
        # Specifically check that execute bit is NOT set
        import stat
        assert not (file_mode & stat.S_IXUSR)  # Owner execute
        assert not (file_mode & stat.S_IXGRP)  # Group execute
        assert not (file_mode & stat.S_IXOTH)  # Other execute

class TestRequestResponseSizeLimits:
    """Test request and response size limits"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        # Very small limits for testing
        self.validator = SecurityValidator(
            self.temp_dir,
            max_file_size_mb=1,
            max_request_size_mb=1  # 1MB request limit
        )
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_large_string_request_blocked(self):
        """Test that large string requests are blocked"""
        large_string = "x" * (2 * 1024 * 1024)  # 2MB
        
        with pytest.raises(PathSecurityError, match="Request/response size.*exceeds limit"):
            self.validator.validate_request_size(large_string)
    
    def test_large_bytes_request_blocked(self):
        """Test that large byte requests are blocked"""
        large_bytes = b"x" * (2 * 1024 * 1024)  # 2MB
        
        with pytest.raises(PathSecurityError, match="Request/response size.*exceeds limit"):
            self.validator.validate_request_size(large_bytes)
    
    def test_large_dict_request_blocked(self):
        """Test that large dictionary requests are blocked"""
        large_dict = {
            "data": "x" * (1 * 1024 * 1024),  # 1MB of data
            "more_data": "y" * (1 * 1024 * 1024),  # Another 1MB
        }
        
        with pytest.raises(PathSecurityError, match="Request/response size.*exceeds limit"):
            self.validator.validate_request_size(large_dict)

class TestSecurityIntegration:
    """Integration tests combining multiple security features"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.validator = SecurityValidator(self.temp_dir, max_file_size_mb=1)
        self.engagement_id = "test_engagement"
        
        # Configure limited allowlist
        self.validator.set_engagement_allowlist(self.engagement_id, {'fs.read', 'fs.write'})
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_comprehensive_attack_simulation(self):
        """Simulate a comprehensive attack combining multiple vectors"""
        write_tool = FsWriteTool(self.validator)
        
        # Attempt 1: Path traversal with oversized content
        with pytest.raises(McpError, match="Security validation failed|Content size.*exceeds limit"):
            await write_tool.execute({
                "path": "../../../etc/passwd",
                "content": "x" * (2 * 1024 * 1024)  # 2MB
            }, self.engagement_id)
        
        # Attempt 2: Malicious file type
        with pytest.raises(McpError, match="MIME type validation failed"):
            await write_tool.execute({
                "path": "malware.exe",
                "content": "fake malware content"
            }, self.engagement_id)
        
        # Attempt 3: Cross-tenant access
        other_engagement = "other_engagement"
        with pytest.raises(CrossTenantError):
            self.validator.validate_tool_access('fs.write', other_engagement)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])