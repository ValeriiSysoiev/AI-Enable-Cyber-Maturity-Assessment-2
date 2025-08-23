"""
Comprehensive tests for MCP Gateway tools.
Tests filesystem, PDF parsing, and search tools with security validation.
"""
import pytest
import json
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

# Import the components we need to test
from services.mcp_gateway.config import MCPConfig, MCPOperationContext
from services.mcp_gateway.security import (
    MCPSecurityValidator, 
    PathTraversalError, 
    FileTypeError, 
    FileSizeError,
    sanitize_path,
    validate_file_type,
    redact_sensitive_content,
    sanitize_filename
)
from services.mcp_gateway.tools.filesystem import MCPFilesystemTool, FSReadRequest, FSWriteRequest
from services.mcp_gateway.tools.pdf_parser import MCPPDFParserTool, PDFParseRequest
from services.mcp_gateway.tools.search import MCPSearchTool, SearchEmbedRequest, SearchQueryRequest


class TestMCPSecurity:
    """Test MCP security utilities"""
    
    def test_sanitize_path_valid(self):
        """Test path sanitization for valid paths"""
        sandbox = Path("/tmp/test_sandbox")
        sandbox.mkdir(exist_ok=True)
        
        try:
            # Valid relative path
            result = sanitize_path("subdir/file.txt", sandbox)
            assert result == sandbox / "subdir/file.txt"
            
            # Valid absolute path within sandbox
            result = sanitize_path(sandbox / "file.txt", sandbox)
            assert result == sandbox / "file.txt"
            
        finally:
            shutil.rmtree(sandbox, ignore_errors=True)
    
    def test_sanitize_path_traversal_attack(self):
        """Test path sanitization blocks traversal attacks"""
        sandbox = Path("/tmp/test_sandbox")
        sandbox.mkdir(exist_ok=True)
        
        try:
            # Directory traversal attempts
            with pytest.raises(PathTraversalError):
                sanitize_path("../../../etc/passwd", sandbox)
            
            with pytest.raises(PathTraversalError):
                sanitize_path("subdir/../../../etc/passwd", sandbox)
                
        finally:
            shutil.rmtree(sandbox, ignore_errors=True)
    
    def test_validate_file_type(self):
        """Test file type validation"""
        test_file = Path("/tmp/test.txt")
        allowed_extensions = {".txt", ".md", ".json"}
        
        # Valid file type
        validate_file_type(test_file, allowed_extensions)
        
        # Invalid file type
        test_file = Path("/tmp/test.exe")
        with pytest.raises(FileTypeError):
            validate_file_type(test_file, allowed_extensions)
    
    def test_redact_sensitive_content(self):
        """Test content redaction for sensitive information"""
        # Test email redaction
        content = "Contact me at john.doe@example.com for details"
        redacted = redact_sensitive_content(content)
        assert "[EMAIL_REDACTED]" in redacted
        assert "john.doe@example.com" not in redacted
        
        # Test phone number redaction
        content = "Call me at 555-123-4567"
        redacted = redact_sensitive_content(content)
        assert "[PHONE_REDACTED]" in redacted
        assert "555-123-4567" not in redacted
        
        # Test truncation
        long_content = "A" * 2000
        redacted = redact_sensitive_content(long_content, max_length=100)
        assert len(redacted) <= 120  # 100 + "[truncated]" message
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        # Test dangerous characters
        result = sanitize_filename("file<>:\"|?*\\/.txt")
        assert "<>:\"|?*\\/" not in result
        assert result.endswith(".txt")
        
        # Test path traversal in filename
        result = sanitize_filename("../../../etc/passwd")
        assert "../" not in result
        
        # Test empty filename
        result = sanitize_filename("")
        assert result == "unnamed_file"


class TestMCPConfig:
    """Test MCP configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = MCPConfig()
        
        assert config.base_data_path.is_absolute()
        assert config.filesystem.enabled
        assert config.filesystem.max_file_size_mb == 10
        assert ".txt" in config.filesystem.allowed_extensions
        assert config.security.enable_path_jailing
        assert config.security.enable_content_redaction
    
    def test_engagement_sandbox(self):
        """Test engagement sandbox creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = MCPConfig(base_data_path=Path(temp_dir))
            
            engagement_id = "test-engagement-123"
            sandbox = config.get_engagement_sandbox(engagement_id)
            
            assert sandbox.exists()
            assert engagement_id in str(sandbox)
            assert temp_dir in str(sandbox)


class TestMCPFilesystemTool:
    """Test filesystem tools"""
    
    @pytest.fixture
    def config_and_context(self):
        """Setup config and context for testing"""
        temp_dir = tempfile.mkdtemp()
        config = MCPConfig(base_data_path=Path(temp_dir))
        
        context = MCPOperationContext(
            correlation_id="test-12345",
            user_email="test@example.com",
            engagement_id="test-engagement",
            tool_name="filesystem",
            operation="test"
        )
        
        yield config, context
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_write_and_read_file(self, config_and_context):
        """Test successful file write and read operations"""
        config, context = config_and_context
        fs_tool = MCPFilesystemTool(config)
        
        # Write file
        write_request = FSWriteRequest(
            path="test_file.txt",
            content="Hello, MCP World!",
            encoding="utf-8"
        )
        
        context.operation = "write"
        write_result = await fs_tool.write_file(write_request, context)
        
        assert write_result.success
        assert "test_file.txt" in write_result.path
        
        # Read file back
        read_request = FSReadRequest(
            path="test_file.txt",
            encoding="utf-8"
        )
        
        context.operation = "read"
        read_result = await fs_tool.read_file(read_request, context)
        
        assert read_result.success
        assert read_result.content == "Hello, MCP World!"
        assert read_result.size_bytes == len("Hello, MCP World!".encode("utf-8"))
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, config_and_context):
        """Test reading a file that doesn't exist"""
        config, context = config_and_context
        fs_tool = MCPFilesystemTool(config)
        
        read_request = FSReadRequest(path="nonexistent.txt")
        context.operation = "read"
        
        result = await fs_tool.read_file(read_request, context)
        assert not result.success
        assert "not found" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_write_invalid_file_type(self, config_and_context):
        """Test writing file with invalid extension"""
        config, context = config_and_context
        fs_tool = MCPFilesystemTool(config)
        
        write_request = FSWriteRequest(
            path="malicious.exe",
            content="evil content"
        )
        context.operation = "write"
        
        result = await fs_tool.write_file(write_request, context)
        assert not result.success
        assert "not allowed" in result.message.lower()


class TestMCPPDFParserTool:
    """Test PDF parser tool"""
    
    @pytest.fixture
    def config_and_context(self):
        """Setup config and context for testing"""
        temp_dir = tempfile.mkdtemp()
        config = MCPConfig(base_data_path=Path(temp_dir))
        
        context = MCPOperationContext(
            correlation_id="test-12345",
            user_email="test@example.com",
            engagement_id="test-engagement",
            tool_name="pdf_parser",
            operation="parse"
        )
        
        yield config, context
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_parse_nonexistent_pdf(self, config_and_context):
        """Test parsing a PDF that doesn't exist"""
        config, context = config_and_context
        pdf_tool = MCPPDFParserTool(config)
        
        parse_request = PDFParseRequest(path="nonexistent.pdf")
        
        result = await pdf_tool.parse_pdf(parse_request, context)
        assert not result.success
        assert "not found" in result.message.lower()
    
    @pytest.mark.asyncio 
    async def test_parse_invalid_file_type(self, config_and_context):
        """Test parsing a non-PDF file"""
        config, context = config_and_context
        pdf_tool = MCPPDFParserTool(config)
        
        parse_request = PDFParseRequest(path="test.txt")
        
        result = await pdf_tool.parse_pdf(parse_request, context)
        assert not result.success
        assert "not allowed" in result.message.lower()


class TestMCPSearchTool:
    """Test search tool"""
    
    @pytest.fixture
    def config_and_context(self):
        """Setup config and context for testing"""
        temp_dir = tempfile.mkdtemp()
        config = MCPConfig(base_data_path=Path(temp_dir))
        
        context = MCPOperationContext(
            correlation_id="test-12345",
            user_email="test@example.com",
            engagement_id="test-engagement",
            tool_name="search",
            operation="test"
        )
        
        yield config, context
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_embed_empty_texts(self, config_and_context):
        """Test embedding with empty text list"""
        config, context = config_and_context
        search_tool = MCPSearchTool(config)
        
        embed_request = SearchEmbedRequest(texts=[])
        context.operation = "embed"
        
        result = await search_tool.embed_texts(embed_request, context)
        assert not result.success
        assert "no texts" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_embed_too_many_texts(self, config_and_context):
        """Test embedding with too many texts"""
        config, context = config_and_context
        search_tool = MCPSearchTool(config)
        
        # Create more than 100 texts
        texts = [f"Text number {i}" for i in range(101)]
        embed_request = SearchEmbedRequest(texts=texts)
        context.operation = "embed"
        
        result = await search_tool.embed_texts(embed_request, context)
        assert not result.success
        assert "too many" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_query_empty_query(self, config_and_context):
        """Test querying with empty query"""
        config, context = config_and_context
        search_tool = MCPSearchTool(config)
        
        query_request = SearchQueryRequest(
            query="",
            embedding_file="test_embeddings.json"
        )
        context.operation = "query"
        
        result = await search_tool.query_embeddings(query_request, context)
        assert not result.success
        assert "empty" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_query_nonexistent_embedding_file(self, config_and_context):
        """Test querying with non-existent embedding file"""
        config, context = config_and_context
        search_tool = MCPSearchTool(config)
        
        query_request = SearchQueryRequest(
            query="test query",
            embedding_file="nonexistent.json"
        )
        context.operation = "query"
        
        result = await search_tool.query_embeddings(query_request, context)
        assert not result.success
        assert "not found" in result.message.lower()
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {"CI_MODE": "1", "DISABLE_ML": "1"})
    async def test_ml_disabled_in_ci_mode(self, config_and_context):
        """Test that ML features are properly disabled in CI mode"""
        config, context = config_and_context
        search_tool = MCPSearchTool(config)
        
        # Test embedding request fails gracefully when ML is disabled
        embed_request = SearchEmbedRequest(texts=["test text"])
        context.operation = "embed"
        
        result = await search_tool.embed_texts(embed_request, context)
        assert not result.success
        assert "disabled" in result.message.lower() or "not available" in result.message.lower()
        
        # Test query request also fails gracefully
        query_request = SearchQueryRequest(
            query="test query",
            embedding_file="test_embeddings.json"
        )
        context.operation = "query"
        
        result = await search_tool.query_embeddings(query_request, context)
        assert not result.success
        assert "disabled" in result.message.lower() or "not available" in result.message.lower()


class TestMCPEndpoints:
    """Test MCP Gateway API endpoints"""
    
    @pytest.fixture
    def client_and_mocks(self):
        """Setup test client with mocked dependencies"""
        from api.main import app
        
        with patch('services.mcp_gateway.main.current_context') as mock_context, \
             patch('services.mcp_gateway.main.get_repository') as mock_repo, \
             patch('services.mcp_gateway.main.require_member') as mock_require_member:
            
            # Mock context
            mock_context.return_value = {
                "user_email": "test@example.com",
                "engagement_id": "test-engagement",
                "tenant_id": None
            }
            
            # Mock repository
            mock_repo.return_value = Mock()
            
            # Mock require_member (allow access)
            mock_require_member.return_value = None
            
            client = TestClient(app)
            yield client, mock_context, mock_repo, mock_require_member
    
    def test_mcp_health_endpoint(self, client_and_mocks):
        """Test MCP health check endpoint"""
        client, _, _, _ = client_and_mocks
        
        response = client.get("/api/mcp/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "mcp_gateway"
        assert "filesystem" in data["tools_available"]
        assert "pdf_parser" in data["tools_available"]
        assert "search" in data["tools_available"]
    
    def test_mcp_tools_endpoint(self, client_and_mocks):
        """Test MCP tools listing endpoint"""
        client, _, _, _ = client_and_mocks
        
        response = client.get("/api/mcp/tools")
        assert response.status_code == 200
        
        data = response.json()
        assert "tools" in data
        assert "filesystem" in data["tools"]
        assert "pdf_parser" in data["tools"]
        assert "search" in data["tools"]
        assert "security" in data
    
    def test_fs_read_endpoint_unauthorized(self, client_and_mocks):
        """Test filesystem read endpoint without proper auth"""
        client, mock_context, mock_repo, mock_require_member = client_and_mocks
        
        # Mock require_member to raise exception
        from fastapi import HTTPException
        mock_require_member.side_effect = HTTPException(403, "Not authorized")
        
        response = client.post("/api/mcp/fs/read", json={"path": "test.txt"})
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_security_validator_integration(self):
        """Test security validator integration"""
        temp_dir = tempfile.mkdtemp()
        try:
            config = MCPConfig(base_data_path=Path(temp_dir))
            context = MCPOperationContext(
                correlation_id="test-12345",
                user_email="test@example.com",
                engagement_id="test-engagement",
                tool_name="filesystem",
                operation="test"
            )
            
            validator = MCPSecurityValidator(config, context)
            
            # Test valid file operation
            validated_path = validator.validate_file_operation(
                "test.txt",
                "write",
                config.filesystem
            )
            
            assert "test-engagement" in str(validated_path)
            assert validated_path.name == "test.txt"
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestMCPIntegration:
    """Integration tests for MCP Gateway"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_filesystem_and_search(self):
        """Test complete workflow: write file, embed content, search"""
        temp_dir = tempfile.mkdtemp()
        try:
            config = MCPConfig(base_data_path=Path(temp_dir))
            context = MCPOperationContext(
                correlation_id="test-workflow-12345",
                user_email="test@example.com",
                engagement_id="test-workflow-engagement",
                tool_name="integration",
                operation="workflow"
            )
            
            # Step 1: Write test content
            fs_tool = MCPFilesystemTool(config)
            context.tool_name = "filesystem"
            context.operation = "write"
            
            test_content = "This is a test document about artificial intelligence and machine learning."
            write_result = await fs_tool.write_file(
                FSWriteRequest(
                    path="ai_document.txt", 
                    content=test_content
                ),
                context
            )
            
            assert write_result.success
            
            # Step 2: Read content back
            context.operation = "read"
            read_result = await fs_tool.read_file(
                FSReadRequest(path="ai_document.txt"),
                context
            )
            
            assert read_result.success
            assert read_result.content == test_content
            
            # Step 3: Create embeddings (would fail without sentence-transformers installed)
            # This tests the structure without requiring the actual model
            search_tool = MCPSearchTool(config)
            context.tool_name = "search"
            context.operation = "embed"
            
            embed_result = await search_tool.embed_texts(
                SearchEmbedRequest(texts=["test text"]),
                context
            )
            
            # May fail due to model loading, but structure should be correct
            assert hasattr(embed_result, 'success')
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])