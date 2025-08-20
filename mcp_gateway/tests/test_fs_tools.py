"""
Filesystem tools tests for MCP Gateway
"""

import pytest
import tempfile
import asyncio
from pathlib import Path

from mcp_tools.fs_tools import FsReadTool, FsWriteTool, FsListTool
from mcp_tools import McpError
from security import SecurityValidator

class TestFsTools:
    """Test filesystem tools functionality"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.validator = SecurityValidator(self.temp_dir, max_file_size_mb=1)
        self.engagement_id = "test_engagement"
        
        # Create engagement directory
        self.eng_path = self.validator.get_safe_engagement_path(self.engagement_id)
        self.eng_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize tools
        self.read_tool = FsReadTool(self.validator)
        self.write_tool = FsWriteTool(self.validator)
        self.list_tool = FsListTool(self.validator)
    
    def teardown_method(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_write_and_read_file(self):
        """Test writing and reading a file"""
        file_path = "test_document.txt"
        content = "This is test content for the MCP filesystem tools."
        
        # Write file
        write_result = await self.write_tool.execute({
            "path": file_path,
            "content": content,
            "overwrite": True
        }, self.engagement_id)
        
        assert write_result.success
        assert write_result.result["path"] == file_path
        assert write_result.result["size"] > 0
        
        # Read file
        read_result = await self.read_tool.execute({
            "path": file_path
        }, self.engagement_id)
        
        assert read_result.success
        assert read_result.result["content"] == content
        assert read_result.result["path"] == file_path
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist"""
        with pytest.raises(McpError, match="FILE_NOT_FOUND"):
            await self.read_tool.execute({
                "path": "nonexistent.txt"
            }, self.engagement_id)
    
    @pytest.mark.asyncio
    async def test_write_without_overwrite(self):
        """Test writing when file exists and overwrite=False"""
        file_path = "existing.txt"
        
        # Write first time
        await self.write_tool.execute({
            "path": file_path,
            "content": "original content"
        }, self.engagement_id)
        
        # Try to write again without overwrite
        with pytest.raises(McpError, match="FILE_EXISTS"):
            await self.write_tool.execute({
                "path": file_path,
                "content": "new content",
                "overwrite": False
            }, self.engagement_id)
    
    @pytest.mark.asyncio
    async def test_write_with_overwrite(self):
        """Test overwriting an existing file"""
        file_path = "overwrite.txt"
        original_content = "original content"
        new_content = "new content"
        
        # Write first time
        await self.write_tool.execute({
            "path": file_path,
            "content": original_content
        }, self.engagement_id)
        
        # Overwrite
        await self.write_tool.execute({
            "path": file_path,
            "content": new_content,
            "overwrite": True
        }, self.engagement_id)
        
        # Read and verify
        read_result = await self.read_tool.execute({
            "path": file_path
        }, self.engagement_id)
        
        assert read_result.result["content"] == new_content
    
    @pytest.mark.asyncio
    async def test_write_with_subdirectory(self):
        """Test writing to subdirectory with create_dirs=True"""
        file_path = "subdir/nested/file.txt"
        content = "nested file content"
        
        # Write with directory creation
        write_result = await self.write_tool.execute({
            "path": file_path,
            "content": content,
            "create_dirs": True
        }, self.engagement_id)
        
        assert write_result.success
        
        # Verify file exists and can be read
        read_result = await self.read_tool.execute({
            "path": file_path
        }, self.engagement_id)
        
        assert read_result.result["content"] == content
    
    @pytest.mark.asyncio
    async def test_write_without_create_dirs(self):
        """Test writing to nonexistent directory with create_dirs=False"""
        file_path = "nonexistent/file.txt"
        
        with pytest.raises(McpError, match="PARENT_NOT_FOUND"):
            await self.write_tool.execute({
                "path": file_path,
                "content": "content",
                "create_dirs": False
            }, self.engagement_id)
    
    @pytest.mark.asyncio
    async def test_list_empty_directory(self):
        """Test listing an empty directory"""
        list_result = await self.list_tool.execute({}, self.engagement_id)
        
        assert list_result.success
        assert list_result.result["total_files"] == 0
        assert list_result.result["total_directories"] == 0
    
    @pytest.mark.asyncio
    async def test_list_directory_with_files(self):
        """Test listing a directory with files"""
        # Create some test files
        await self.write_tool.execute({
            "path": "file1.txt",
            "content": "content1"
        }, self.engagement_id)
        
        await self.write_tool.execute({
            "path": "file2.txt",
            "content": "content2"
        }, self.engagement_id)
        
        await self.write_tool.execute({
            "path": "subdir/file3.txt",
            "content": "content3",
            "create_dirs": True
        }, self.engagement_id)
        
        # List root directory
        list_result = await self.list_tool.execute({}, self.engagement_id)
        
        assert list_result.success
        assert list_result.result["total_files"] == 2
        assert list_result.result["total_directories"] == 1
        
        # Check file names
        file_names = [f["name"] for f in list_result.result["files"]]
        assert "file1.txt" in file_names
        assert "file2.txt" in file_names
        
        # Check directory names
        dir_names = [d["name"] for d in list_result.result["directories"]]
        assert "subdir" in dir_names
    
    @pytest.mark.asyncio
    async def test_list_recursive(self):
        """Test recursive directory listing"""
        # Create nested structure
        await self.write_tool.execute({
            "path": "root.txt",
            "content": "root content"
        }, self.engagement_id)
        
        await self.write_tool.execute({
            "path": "level1/file1.txt",
            "content": "level1 content",
            "create_dirs": True
        }, self.engagement_id)
        
        await self.write_tool.execute({
            "path": "level1/level2/file2.txt",
            "content": "level2 content",
            "create_dirs": True
        }, self.engagement_id)
        
        # List recursively
        list_result = await self.list_tool.execute({
            "recursive": True
        }, self.engagement_id)
        
        assert list_result.success
        assert list_result.result["total_files"] == 3  # root.txt, file1.txt, file2.txt
        
        # Check that nested files are included
        file_paths = [f["path"] for f in list_result.result["files"]]
        assert "root.txt" in file_paths
        assert "level1/file1.txt" in file_paths
        assert "level1/level2/file2.txt" in file_paths
    
    @pytest.mark.asyncio
    async def test_file_size_limit(self):
        """Test file size limits"""
        large_content = "x" * (2 * 1024 * 1024)  # 2MB (exceeds 1MB limit)
        
        with pytest.raises(McpError, match="Content size.*exceeds limit"):
            await self.write_tool.execute({
                "path": "large_file.txt",
                "content": large_content
            }, self.engagement_id)
    
    @pytest.mark.asyncio
    async def test_read_size_limit(self):
        """Test read size limits"""
        file_path = "test_size.txt"
        content = "test content"
        
        # Write normal file
        await self.write_tool.execute({
            "path": file_path,
            "content": content
        }, self.engagement_id)
        
        # Read with size limit
        read_result = await self.read_tool.execute({
            "path": file_path,
            "max_size": 5  # Very small limit
        }, self.engagement_id)
        
        assert read_result.success
        assert len(read_result.result["content"]) <= len(content)
    
    @pytest.mark.asyncio
    async def test_invalid_encoding(self):
        """Test handling of encoding errors"""
        # Write binary content as text file
        file_path = self.eng_path / "binary.txt"
        binary_content = bytes([0xFF, 0xFE, 0x00, 0x01, 0x80, 0x90])
        file_path.write_bytes(binary_content)
        
        # Try to read with UTF-8 encoding
        with pytest.raises(McpError, match="ENCODING_ERROR"):
            await self.read_tool.execute({
                "path": "binary.txt",
                "encoding": "utf-8"
            }, self.engagement_id)

if __name__ == "__main__":
    pytest.main([__file__])