"""
Security validation tests for MCP Gateway
"""

import pytest
import tempfile
import os
from pathlib import Path

from security import SecurityValidator, PathSecurityError

class TestSecurityValidator:
    """Test security validation functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.validator = SecurityValidator(self.temp_dir, max_file_size_mb=1)
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_safe_engagement_path(self):
        """Test engagement path creation and validation"""
        # Valid engagement ID
        path = self.validator.get_safe_engagement_path("engagement_123")
        assert path.parent == Path(self.temp_dir)
        assert path.name == "engagement_123"
        
        # Invalid engagement IDs should raise errors
        with pytest.raises(PathSecurityError):
            self.validator.get_safe_engagement_path("")
        
        with pytest.raises(PathSecurityError):
            self.validator.get_safe_engagement_path("../escape")
        
        with pytest.raises(PathSecurityError):
            self.validator.get_safe_engagement_path("path/with/slashes")
    
    def test_validate_file_path_traversal_prevention(self):
        """Test path traversal attack prevention"""
        engagement_id = "test_engagement"
        
        # These should all raise PathSecurityError
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "~/sensitive_file",
            "/etc/passwd",
            "file.txt/../../../escape",
            "file.txt\\..\\..\\escape",
            "${HOME}/escape",
            "`whoami`/escape"
        ]
        
        for dangerous_path in dangerous_paths:
            with pytest.raises(PathSecurityError, match="Dangerous pattern detected|outside"):
                self.validator.validate_file_path(dangerous_path, engagement_id)
    
    def test_validate_file_path_valid_paths(self):
        """Test that valid paths are accepted"""
        engagement_id = "test_engagement"
        
        valid_paths = [
            "document.txt",
            "folder/document.txt",
            "reports/quarterly-report.pdf",
            "data-file_v2.json"
        ]
        
        for valid_path in valid_paths:
            # Should not raise an exception
            result_path = self.validator.validate_file_path(valid_path, engagement_id)
            assert isinstance(result_path, Path)
            assert str(result_path).startswith(str(self.validator.data_root))
    
    def test_sanitize_path_component(self):
        """Test path component sanitization"""
        # Valid components
        assert self.validator._sanitize_path_component("file.txt") == "file.txt"
        assert self.validator._sanitize_path_component("report_2024") == "report_2024"
        assert self.validator._sanitize_path_component("doc-v1.pdf") == "doc-v1.pdf"
        
        # Invalid components (should return empty or sanitized)
        assert self.validator._sanitize_path_component("..") == ""
        assert self.validator._sanitize_path_component("...") == ""
        assert self.validator._sanitize_path_component(".hidden") == ""
        assert self.validator._sanitize_path_component("file<>:") == "file"
    
    def test_file_size_validation(self):
        """Test file size limits"""
        engagement_id = "test_engagement"
        
        # Create test directory
        eng_path = self.validator.get_safe_engagement_path(engagement_id)
        eng_path.mkdir(parents=True, exist_ok=True)
        
        # Create a small file (should pass)
        small_file = eng_path / "small.txt"
        small_file.write_text("small content")
        self.validator.validate_file_size(small_file)  # Should not raise
        
        # Create a large file (should fail)
        large_file = eng_path / "large.txt"
        large_content = "x" * (2 * 1024 * 1024)  # 2MB (exceeds 1MB limit)
        large_file.write_text(large_content)
        
        with pytest.raises(PathSecurityError, match="exceeds limit"):
            self.validator.validate_file_size(large_file)
    
    def test_content_size_validation(self):
        """Test content size validation"""
        # Small content should pass
        small_content = "small content"
        self.validator.validate_content_size(small_content)  # Should not raise
        
        # Large content should fail
        large_content = "x" * (2 * 1024 * 1024)  # 2MB
        with pytest.raises(PathSecurityError, match="exceeds limit"):
            self.validator.validate_content_size(large_content)
        
        # Test with bytes
        large_bytes = b"x" * (2 * 1024 * 1024)
        with pytest.raises(PathSecurityError, match="exceeds limit"):
            self.validator.validate_content_size(large_bytes)
    
    def test_symlink_prevention(self):
        """Test symlink detection and prevention"""
        engagement_id = "test_engagement"
        
        # Create test directory
        eng_path = self.validator.get_safe_engagement_path(engagement_id)
        eng_path.mkdir(parents=True, exist_ok=True)
        
        # Create a regular file
        regular_file = eng_path / "regular.txt"
        regular_file.write_text("content")
        
        # Create a symlink (if supported by OS)
        symlink_file = eng_path / "symlink.txt"
        try:
            symlink_file.symlink_to(regular_file)
            
            # Validation should fail for symlink
            with pytest.raises(PathSecurityError, match="Symlinks are not allowed"):
                self.validator.validate_file_path("symlink.txt", engagement_id)
        except OSError:
            # Skip if symlinks not supported (e.g., Windows without admin rights)
            pytest.skip("Symlinks not supported on this system")
    
    def test_mcp_index_path(self):
        """Test MCP index path generation"""
        engagement_id = "test_engagement"
        
        index_path = self.validator.get_mcp_index_path(engagement_id)
        
        assert index_path.name == "mcp_index"
        assert index_path.parent.name == "test_engagement"
        assert str(index_path).startswith(str(self.validator.data_root))
    
    def test_directory_creation(self):
        """Test safe directory creation"""
        engagement_id = "test_engagement"
        
        eng_path = self.validator.get_safe_engagement_path(engagement_id)
        test_dir = eng_path / "subdir" / "deepdir"
        
        # Should create directories safely
        self.validator.ensure_directory_exists(test_dir)
        assert test_dir.exists()
        assert test_dir.is_dir()

if __name__ == "__main__":
    pytest.main([__file__])