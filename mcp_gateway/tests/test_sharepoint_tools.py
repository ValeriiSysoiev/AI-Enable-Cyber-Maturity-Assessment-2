"""
Tests for SharePoint MCP tools
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from mcp_tools.sharepoint_tools import SharePointFetchTool, register_sharepoint_tools, ALLOWED_FILE_TYPES
from mcp_tools import McpToolRegistry
from security import SecurityValidator


@pytest.fixture
def temp_data_root():
    """Create temporary data directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def security_validator(temp_data_root):
    """Create security validator for tests"""
    return SecurityValidator(
        data_root=temp_data_root,
        max_file_size_mb=10,
        max_request_size_mb=50
    )


@pytest.fixture
def sharepoint_tool(security_validator):
    """Create SharePoint fetch tool for tests"""
    return SharePointFetchTool(security_validator)


@pytest.fixture
def demo_documents(temp_data_root):
    """Create demo SharePoint documents for testing"""
    demo_dir = Path(temp_data_root) / "sharepoint_demo" / "test-engagement"
    demo_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test files
    (demo_dir / "policy.pdf").write_text("Demo PDF content")
    (demo_dir / "assessment.docx").write_text("Demo Word content")
    (demo_dir / "matrix.xlsx").write_text("Demo Excel content")
    (demo_dir / "readme.txt").write_text("Demo text content")
    (demo_dir / "notes.md").write_text("# Demo Markdown")
    
    # Create invalid file type
    (demo_dir / "script.exe").write_text("Invalid executable")
    
    return demo_dir


class TestSharePointFetchTool:
    """Test SharePoint fetch tool functionality"""
    
    def test_tool_initialization(self, sharepoint_tool):
        """Test tool is properly initialized"""
        assert sharepoint_tool.name == "sharepoint.fetch"
        assert "SharePoint" in sharepoint_tool.description
        assert "tenant_id" in sharepoint_tool.schema["properties"]
        assert "site_url" in sharepoint_tool.schema["properties"]
        assert "document_path" in sharepoint_tool.schema["properties"]
    
    def test_schema_validation(self, sharepoint_tool):
        """Test tool schema is valid"""
        schema = sharepoint_tool.schema
        assert schema["type"] == "object"
        assert set(schema["required"]) == {"tenant_id", "site_url", "document_path"}
        
        # Check mode enum
        mode_prop = schema["properties"]["mode"]
        assert mode_prop["enum"] == ["REAL", "DRY-RUN"]
        assert mode_prop["default"] == "DRY-RUN"
    
    @pytest.mark.asyncio
    async def test_dry_run_fetch_success(self, sharepoint_tool, demo_documents):
        """Test successful dry-run document fetch"""
        payload = {
            "tenant_id": "test-tenant",
            "site_url": "https://contoso.sharepoint.com/sites/security",
            "document_path": "/Shared Documents/Policies",
            "mode": "DRY-RUN"
        }
        
        result = await sharepoint_tool.execute(payload, "test-engagement")
        
        assert result.success is True
        assert result.error is None
        
        data = result.result
        assert data["count"] > 0
        assert data["mode"] == "DRY-RUN"
        assert data["tenant_id"] == "test-tenant"
        assert len(data["documents"]) > 0
        
        # Check first document has proper provenance
        doc = data["documents"][0]
        assert "file_name" in doc
        assert "checksum_sha256" in doc
        assert "source" in doc
        assert "provenance" in doc
        assert "security" in doc
        
        # Verify source metadata
        assert doc["source"]["type"] == "sharepoint"
        assert doc["source"]["tenant_id"] == "test-tenant"
        assert doc["security"]["validated"] is True
    
    @pytest.mark.asyncio
    async def test_dry_run_file_type_filtering(self, sharepoint_tool, demo_documents):
        """Test file type filtering works correctly"""
        payload = {
            "tenant_id": "test-tenant",
            "site_url": "https://contoso.sharepoint.com/sites/security",
            "document_path": "/Shared Documents/Policies",
            "mode": "DRY-RUN",
            "file_types": [".pdf", ".docx"]
        }
        
        result = await sharepoint_tool.execute(payload, "test-engagement")
        
        assert result.success is True
        data = result.result
        
        # Should only find PDF and DOCX files
        file_types = {doc["file_type"] for doc in data["documents"]}
        assert file_types.issubset({".pdf", ".docx"})
        assert ".txt" not in file_types  # Should be filtered out
    
    @pytest.mark.asyncio
    async def test_invalid_file_types_rejected(self, sharepoint_tool, demo_documents):
        """Test invalid file types are rejected"""
        payload = {
            "tenant_id": "test-tenant", 
            "site_url": "https://contoso.sharepoint.com/sites/security",
            "document_path": "/Shared Documents/Policies",
            "mode": "DRY-RUN",
            "file_types": [".exe", ".bat"]  # Invalid types
        }
        
        result = await sharepoint_tool.execute(payload, "test-engagement")
        
        assert result.success is False
        assert result.error_code == "INVALID_FILE_TYPES"
        assert ".exe" in result.error
    
    @pytest.mark.asyncio
    async def test_missing_demo_data(self, sharepoint_tool):
        """Test graceful handling when demo data is missing"""
        payload = {
            "tenant_id": "test-tenant",
            "site_url": "https://contoso.sharepoint.com/sites/security", 
            "document_path": "/Shared Documents/Policies",
            "mode": "DRY-RUN"
        }
        
        result = await sharepoint_tool.execute(payload, "nonexistent-engagement")
        
        assert result.success is False
        assert result.error_code == "DEMO_DATA_MISSING"
        assert "Demo SharePoint data not found" in result.error
    
    @pytest.mark.asyncio
    async def test_real_mode_missing_credentials(self, sharepoint_tool):
        """Test real mode fails gracefully without credentials"""
        payload = {
            "tenant_id": "test-tenant",
            "site_url": "https://contoso.sharepoint.com/sites/security",
            "document_path": "/Shared Documents/Policies", 
            "mode": "REAL"
        }
        
        with patch.dict('os.environ', {}, clear=True):
            result = await sharepoint_tool.execute(payload, "test-engagement")
            
            assert result.success is False
            assert result.error_code == "MISSING_CREDENTIALS"
            assert "SHAREPOINT_CLIENT_ID" in result.error
    
    @pytest.mark.asyncio
    async def test_payload_validation(self, sharepoint_tool):
        """Test payload validation catches missing required fields"""
        payload = {
            "tenant_id": "test-tenant"
            # Missing required fields
        }
        
        result = await sharepoint_tool.execute(payload, "test-engagement")
        
        assert result.success is False
        assert result.error_code == "INVALID_PAYLOAD"
        assert "Missing required fields" in result.error
    
    @pytest.mark.asyncio
    async def test_provenance_metadata_complete(self, sharepoint_tool, demo_documents):
        """Test provenance metadata is comprehensive"""
        payload = {
            "tenant_id": "test-tenant",
            "site_url": "https://contoso.sharepoint.com/sites/security",
            "document_path": "/Shared Documents/Policies",
            "mode": "DRY-RUN"
        }
        
        result = await sharepoint_tool.execute(payload, "test-engagement")
        
        assert result.success is True
        doc = result.result["documents"][0]
        
        # Check all required provenance fields
        required_fields = {
            "file_name", "file_size", "file_type", "checksum_sha256"
        }
        assert required_fields.issubset(set(doc.keys()))
        
        # Check source metadata
        source = doc["source"]
        required_source_fields = {
            "type", "tenant_id", "site_url", "document_path", "full_path"
        }
        assert required_source_fields.issubset(set(source.keys()))
        assert source["type"] == "sharepoint"
        
        # Check provenance metadata
        provenance = doc["provenance"]
        required_prov_fields = {
            "ingested_at", "ingested_by", "mode", "local_path"
        }
        assert required_prov_fields.issubset(set(provenance.keys()))
        assert provenance["ingested_by"] == "mcp.sharepoint.fetch"
        
        # Check security metadata
        security = doc["security"]
        assert security["validated"] is True
        assert security["allowed_file_type"] is True
        assert security["checksum_verified"] is True


class TestSharePointToolRegistry:
    """Test SharePoint tool registration"""
    
    def test_register_sharepoint_tools(self, security_validator):
        """Test SharePoint tools register correctly"""
        registry = McpToolRegistry()
        
        # Should start empty
        assert len(registry.tools) == 0
        
        register_sharepoint_tools(registry, security_validator)
        
        # Should have SharePoint tool registered
        assert "sharepoint.fetch" in registry.tools
        assert registry.is_allowed("sharepoint.fetch")
        
        tool = registry.get_tool("sharepoint.fetch")
        assert tool is not None
        assert isinstance(tool, SharePointFetchTool)


class TestFileTypeValidation:
    """Test file type allowlist validation"""
    
    def test_allowed_file_types_constant(self):
        """Test ALLOWED_FILE_TYPES contains expected types"""
        expected_types = {'.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.md'}
        assert ALLOWED_FILE_TYPES == expected_types
    
    def test_file_type_security(self):
        """Test dangerous file types are not allowed"""
        dangerous_types = {'.exe', '.bat', '.sh', '.ps1', '.scr', '.com'}
        assert dangerous_types.isdisjoint(ALLOWED_FILE_TYPES)