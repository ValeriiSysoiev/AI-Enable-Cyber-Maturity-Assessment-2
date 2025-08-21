"""
Tests for SharePoint and Jira MCP connectors in orchestrator
"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from mcp_connectors import MCPConnectors


@pytest.fixture
def mock_mcp_client():
    """Create mock MCP client for testing"""
    client = Mock()
    client.call = AsyncMock()
    return client


@pytest.fixture
def mcp_connectors(mock_mcp_client):
    """Create MCP connectors with mock client"""
    with patch.dict('os.environ', {
        'MCP_CONNECTORS_SP': 'true',
        'MCP_CONNECTORS_JIRA': 'true'
    }):
        return MCPConnectors(mock_mcp_client)


class TestSharePointConnector:
    """Test SharePoint MCP connector functionality"""
    
    @pytest.mark.asyncio
    async def test_fetch_sharepoint_documents_dry_run(self, mcp_connectors, mock_mcp_client):
        """Test SharePoint document fetch in DRY-RUN mode"""
        # Mock MCP response
        mock_response = {
            "success": True,
            "result": {
                "documents": [
                    {
                        "file_name": "policy.pdf",
                        "file_type": ".pdf",
                        "checksum_sha256": "abc123",
                        "source": {
                            "type": "sharepoint",
                            "tenant_id": "test-tenant",
                            "site_url": "https://contoso.sharepoint.com/sites/security"
                        }
                    }
                ],
                "count": 1,
                "mode": "DRY-RUN"
            },
            "call_id": "test-call-123"
        }
        mock_mcp_client.call.return_value = mock_response
        
        # Test the connector
        result = await mcp_connectors.fetch_sharepoint_documents(
            tenant_id="test-tenant",
            site_url="https://contoso.sharepoint.com/sites/security",
            document_path="/Shared Documents/Policies",
            engagement_id="test-engagement"
        )
        
        # Verify MCP client was called correctly
        mock_mcp_client.call.assert_called_once()
        call_args = mock_mcp_client.call.call_args
        assert call_args[0][0] == "sharepoint.fetch"
        assert call_args[0][2] == "test-engagement"
        
        payload = call_args[0][1]
        assert payload["tenant_id"] == "test-tenant"
        assert payload["site_url"] == "https://contoso.sharepoint.com/sites/security"
        assert payload["document_path"] == "/Shared Documents/Policies"
        assert payload["mode"] == "DRY-RUN"
        assert payload["file_types"] == [".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".md"]
        
        # Verify response
        assert result == mock_response
    
    @pytest.mark.asyncio
    async def test_fetch_sharepoint_documents_real_mode(self, mcp_connectors, mock_mcp_client):
        """Test SharePoint document fetch switches to REAL mode with credentials"""
        mock_response = {
            "success": True,
            "result": {"documents": [], "count": 0, "mode": "REAL"}
        }
        mock_mcp_client.call.return_value = mock_response
        
        # Mock environment with SharePoint credentials
        with patch.dict('os.environ', {
            'SHAREPOINT_CLIENT_ID': 'test-client-id',
            'SHAREPOINT_CLIENT_SECRET': 'test-secret',
            'SHAREPOINT_TENANT': 'test-tenant'
        }):
            result = await mcp_connectors.fetch_sharepoint_documents(
                tenant_id="test-tenant",
                site_url="https://contoso.sharepoint.com/sites/security",
                document_path="/Shared Documents",
                engagement_id="test-engagement"
            )
        
        # Verify REAL mode was used
        payload = mock_mcp_client.call.call_args[0][1]
        assert payload["mode"] == "REAL"
    
    @pytest.mark.asyncio
    async def test_fetch_sharepoint_documents_disabled(self, mock_mcp_client):
        """Test SharePoint connector respects disabled flag"""
        with patch.dict('os.environ', {'MCP_CONNECTORS_SP': 'false'}):
            connectors = MCPConnectors(mock_mcp_client)
            
            with pytest.raises(ValueError, match="SharePoint connector is disabled"):
                await connectors.fetch_sharepoint_documents(
                    tenant_id="test-tenant",
                    site_url="https://contoso.sharepoint.com/sites/security",
                    document_path="/Shared Documents",
                    engagement_id="test-engagement"
                )
    
    @pytest.mark.asyncio
    async def test_fetch_sharepoint_documents_custom_file_types(self, mcp_connectors, mock_mcp_client):
        """Test SharePoint document fetch with custom file types"""
        mock_mcp_client.call.return_value = {"success": True}
        
        await mcp_connectors.fetch_sharepoint_documents(
            tenant_id="test-tenant",
            site_url="https://contoso.sharepoint.com/sites/security",
            document_path="/Shared Documents",
            engagement_id="test-engagement",
            file_types=[".pdf", ".docx"],
            recursive=True
        )
        
        # Verify custom parameters
        payload = mock_mcp_client.call.call_args[0][1]
        assert payload["file_types"] == [".pdf", ".docx"]
        assert payload["recursive"] is True


class TestJiraConnector:
    """Test Jira MCP connector functionality"""
    
    @pytest.mark.asyncio
    async def test_create_jira_issue_dry_run(self, mcp_connectors, mock_mcp_client):
        """Test Jira issue creation in DRY-RUN mode"""
        mock_response = {
            "success": True,
            "result": {
                "issue_key": "CYBER-1001",
                "issue_url": "https://your-org.atlassian.net/browse/CYBER-1001",
                "status": "created",
                "external_key": "engagement-123_finding-456",
                "mode": "DRY-RUN"
            },
            "call_id": "test-call-456"
        }
        mock_mcp_client.call.return_value = mock_response
        
        # Test the connector
        result = await mcp_connectors.create_jira_issue(
            project_key="CYBER",
            summary="Critical security vulnerability found",
            description="SQL injection vulnerability in user login form",
            external_key="engagement-123_finding-456",
            engagement_id="test-engagement",
            priority="High",
            labels=["security", "vulnerability"]
        )
        
        # Verify MCP client was called correctly
        mock_mcp_client.call.assert_called_once()
        call_args = mock_mcp_client.call.call_args
        assert call_args[0][0] == "jira.createIssue"
        assert call_args[0][2] == "test-engagement"
        
        payload = call_args[0][1]
        assert payload["project_key"] == "CYBER"
        assert payload["summary"] == "Critical security vulnerability found"
        assert payload["description"] == "SQL injection vulnerability in user login form"
        assert payload["external_key"] == "engagement-123_finding-456"
        assert payload["priority"] == "High"
        assert payload["labels"] == ["security", "vulnerability"]
        assert payload["issue_type"] == "Task"
        assert payload["mode"] == "DRY-RUN"
        
        # Verify response
        assert result == mock_response
    
    @pytest.mark.asyncio
    async def test_create_jira_issue_real_mode(self, mcp_connectors, mock_mcp_client):
        """Test Jira issue creation switches to REAL mode with credentials"""
        mock_response = {
            "success": True,
            "result": {"issue_key": "CYBER-1001", "mode": "REAL"}
        }
        mock_mcp_client.call.return_value = mock_response
        
        # Mock environment with Jira credentials
        with patch.dict('os.environ', {
            'JIRA_URL': 'https://your-org.atlassian.net',
            'JIRA_USERNAME': 'test@example.com',
            'JIRA_API_TOKEN': 'test-token'
        }):
            result = await mcp_connectors.create_jira_issue(
                project_key="CYBER",
                summary="Test issue",
                description="Test description",
                external_key="test-key",
                engagement_id="test-engagement"
            )
        
        # Verify REAL mode was used
        payload = mock_mcp_client.call.call_args[0][1]
        assert payload["mode"] == "REAL"
    
    @pytest.mark.asyncio
    async def test_create_jira_issue_disabled(self, mock_mcp_client):
        """Test Jira connector respects disabled flag"""
        with patch.dict('os.environ', {'MCP_CONNECTORS_JIRA': 'false'}):
            connectors = MCPConnectors(mock_mcp_client)
            
            with pytest.raises(ValueError, match="Jira connector is disabled"):
                await connectors.create_jira_issue(
                    project_key="CYBER",
                    summary="Test issue",
                    description="Test description",
                    external_key="test-key",
                    engagement_id="test-engagement"
                )
    
    @pytest.mark.asyncio
    async def test_update_jira_issue_dry_run(self, mcp_connectors, mock_mcp_client):
        """Test Jira issue update in DRY-RUN mode"""
        mock_response = {
            "success": True,
            "result": {
                "issue_key": "CYBER-1001",
                "status": "updated",
                "external_key": "test-key",
                "mode": "DRY-RUN"
            }
        }
        mock_mcp_client.call.return_value = mock_response
        
        # Test the connector
        result = await mcp_connectors.update_jira_issue(
            issue_key="CYBER-1001",
            external_key="test-key",
            engagement_id="test-engagement",
            status="In Progress",
            priority="High",
            comment="Investigation started"
        )
        
        # Verify MCP client was called correctly
        mock_mcp_client.call.assert_called_once()
        call_args = mock_mcp_client.call.call_args
        assert call_args[0][0] == "jira.updateIssue"
        assert call_args[0][2] == "test-engagement"
        
        payload = call_args[0][1]
        assert payload["issue_key"] == "CYBER-1001"
        assert payload["external_key"] == "test-key"
        assert payload["status"] == "In Progress"
        assert payload["priority"] == "High"
        assert payload["comment"] == "Investigation started"
        assert payload["mode"] == "DRY-RUN"
        
        # Verify response
        assert result == mock_response
    
    @pytest.mark.asyncio
    async def test_update_jira_issue_partial_fields(self, mcp_connectors, mock_mcp_client):
        """Test Jira issue update with only some fields"""
        mock_response = {"success": True, "result": {"issue_key": "CYBER-1001"}}
        mock_mcp_client.call.return_value = mock_response
        
        # Test with minimal fields
        result = await mcp_connectors.update_jira_issue(
            issue_key="CYBER-1001",
            external_key="test-key",
            engagement_id="test-engagement",
            status="Done"  # Only updating status
        )
        
        # Verify only provided fields are in payload
        payload = mock_mcp_client.call.call_args[0][1]
        assert payload["issue_key"] == "CYBER-1001"
        assert payload["external_key"] == "test-key"
        assert payload["status"] == "Done"
        assert "summary" not in payload
        assert "description" not in payload
        assert "priority" not in payload


class TestConnectorIntegration:
    """Test integration scenarios with SharePoint and Jira connectors"""
    
    @pytest.mark.asyncio
    async def test_sharepoint_to_jira_workflow(self, mcp_connectors, mock_mcp_client):
        """Test complete workflow: SharePoint fetch → Jira issue creation"""
        # Mock SharePoint response
        sharepoint_response = {
            "success": True,
            "result": {
                "documents": [
                    {
                        "file_name": "security-policy.pdf",
                        "file_type": ".pdf",
                        "checksum_sha256": "abc123",
                        "source": {"type": "sharepoint", "tenant_id": "test-tenant"}
                    }
                ],
                "count": 1
            }
        }
        
        # Mock Jira response
        jira_response = {
            "success": True,
            "result": {
                "issue_key": "CYBER-1001",
                "status": "created",
                "external_key": "doc-review-abc123"
            }
        }
        
        # Configure mock to return different responses
        mock_mcp_client.call.side_effect = [sharepoint_response, jira_response]
        
        # 1. Fetch documents from SharePoint
        sp_result = await mcp_connectors.fetch_sharepoint_documents(
            tenant_id="test-tenant",
            site_url="https://contoso.sharepoint.com/sites/security",
            document_path="/Shared Documents/Policies",
            engagement_id="test-engagement"
        )
        
        # 2. Create Jira issue for document review
        doc = sp_result["result"]["documents"][0]
        jira_result = await mcp_connectors.create_jira_issue(
            project_key="CYBER",
            summary=f"Review document: {doc['file_name']}",
            description=f"Security review required for {doc['file_name']} (checksum: {doc['checksum_sha256']})",
            external_key=f"doc-review-{doc['checksum_sha256']}",
            engagement_id="test-engagement",
            labels=["document-review", "security"]
        )
        
        # Verify both calls were made
        assert mock_mcp_client.call.call_count == 2
        
        # Verify SharePoint call
        sp_call_args = mock_mcp_client.call.call_args_list[0]
        assert sp_call_args[0][0] == "sharepoint.fetch"
        
        # Verify Jira call
        jira_call_args = mock_mcp_client.call.call_args_list[1]
        assert jira_call_args[0][0] == "jira.createIssue"
        jira_payload = jira_call_args[0][1]
        assert "security-policy.pdf" in jira_payload["summary"]
        assert "abc123" in jira_payload["description"]
        assert jira_payload["external_key"] == "doc-review-abc123"


class TestConnectorConfiguration:
    """Test connector configuration and feature flags"""
    
    def test_connectors_initialization_flags(self, mock_mcp_client):
        """Test connector initialization respects feature flags"""
        with patch.dict('os.environ', {
            'MCP_CONNECTORS_SP': 'true',
            'MCP_CONNECTORS_JIRA': 'false',
            'MCP_CONNECTORS_AUDIO': 'true'
        }):
            connectors = MCPConnectors(mock_mcp_client)
            
            assert connectors.sharepoint_enabled is True
            assert connectors.jira_enabled is False
            assert connectors.audio_enabled is True
    
    def test_connectors_default_flags(self, mock_mcp_client):
        """Test connector default feature flag values"""
        with patch.dict('os.environ', {}, clear=True):
            connectors = MCPConnectors(mock_mcp_client)
            
            # Defaults should be False for enterprise connectors
            assert connectors.sharepoint_enabled is False
            assert connectors.jira_enabled is False
            assert connectors.audio_enabled is False
            assert connectors.pptx_enabled is False
            assert connectors.pii_scrub_enabled is True  # PII scrub defaults to True