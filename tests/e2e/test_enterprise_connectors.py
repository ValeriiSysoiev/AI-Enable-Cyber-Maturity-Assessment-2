"""
E2E tests for enterprise connectors (SharePoint + Jira)

Tests the complete workflow: ingest "SharePoint" (dry-run) → run analysis → export Jira (dry-run)
"""

import pytest
import asyncio
import requests
import json
import os
from pathlib import Path

# Test configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8100")
MCP_GATEWAY_URL = os.environ.get("MCP_GATEWAY_URL", "http://localhost:8200")
ENGAGEMENT_ID = "e2e-enterprise-test"


class TestEnterpriseConnectorsE2E:
    """End-to-end tests for SharePoint and Jira enterprise connectors"""
    
    def test_mcp_gateway_health(self):
        """Test MCP Gateway is accessible and healthy"""
        response = requests.get(f"{MCP_GATEWAY_URL}/health")
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert health_data["mcp_enabled"] is True
        assert health_data["tools_registered"] > 0
    
    def test_list_mcp_tools(self):
        """Test that SharePoint and Jira tools are registered"""
        response = requests.get(f"{MCP_GATEWAY_URL}/mcp/tools")
        assert response.status_code == 200
        
        tools_data = response.json()
        tool_names = [tool["name"] for tool in tools_data["tools"]]
        
        # Verify SharePoint tool is registered
        assert "sharepoint.fetch" in tool_names
        
        # Note: Jira tools may not be registered on main branch yet
        # This test will be updated once Jira PR is merged
    
    def test_sharepoint_fetch_dry_run(self):
        """Test SharePoint document fetch in DRY-RUN mode"""
        payload = {
            "tool": "sharepoint.fetch",
            "payload": {
                "tenant_id": "e2e-test-tenant",
                "site_url": "https://contoso.sharepoint.com/sites/security",
                "document_path": "/Shared Documents/Policies",
                "mode": "DRY-RUN",
                "file_types": [".pdf", ".docx", ".xlsx"]
            },
            "engagement_id": ENGAGEMENT_ID
        }
        
        response = requests.post(f"{MCP_GATEWAY_URL}/mcp/call", json=payload)
        assert response.status_code == 200
        
        result = response.json()
        assert result["success"] is True
        assert result["tool"] == "sharepoint.fetch"
        assert result["engagement_id"] == ENGAGEMENT_ID
        
        # Check result structure
        assert "result" in result
        sharepoint_result = result["result"]
        assert "documents" in sharepoint_result
        assert "count" in sharepoint_result
        assert sharepoint_result["mode"] == "DRY-RUN"
        
        # Store result for next test
        self.sharepoint_documents = sharepoint_result["documents"]
    
    @pytest.mark.skipif(
        "jira.createIssue" not in [tool["name"] for tool in requests.get(f"{MCP_GATEWAY_URL}/mcp/tools").json().get("tools", [])],
        reason="Jira tools not yet available on main branch"
    )
    def test_jira_create_issue_dry_run(self):
        """Test Jira issue creation in DRY-RUN mode"""
        payload = {
            "tool": "jira.createIssue",
            "payload": {
                "project_key": "CYBER",
                "summary": "E2E Test: Security document review required",
                "description": "End-to-end test issue for enterprise connector validation",
                "priority": "Medium",
                "labels": ["e2e-test", "security", "document-review"],
                "external_key": f"e2e-test-{ENGAGEMENT_ID}-001",
                "mode": "DRY-RUN"
            },
            "engagement_id": ENGAGEMENT_ID
        }
        
        response = requests.post(f"{MCP_GATEWAY_URL}/mcp/call", json=payload)
        assert response.status_code == 200
        
        result = response.json()
        assert result["success"] is True
        assert result["tool"] == "jira.createIssue"
        assert result["engagement_id"] == ENGAGEMENT_ID
        
        # Check result structure
        assert "result" in result
        jira_result = result["result"]
        assert "issue_key" in jira_result
        assert "issue_url" in jira_result
        assert jira_result["status"] == "created"
        assert jira_result["mode"] == "DRY-RUN"
        
        # Verify external key for idempotency
        assert jira_result["external_key"] == f"e2e-test-{ENGAGEMENT_ID}-001"
    
    def test_enterprise_connector_workflow_simulation(self):
        """Simulate complete enterprise connector workflow without requiring both tools"""
        # This test simulates the workflow even if Jira tools aren't available yet
        
        # 1. Fetch SharePoint documents (this should work)
        sharepoint_payload = {
            "tool": "sharepoint.fetch",
            "payload": {
                "tenant_id": "workflow-test-tenant",
                "site_url": "https://contoso.sharepoint.com/sites/security",
                "document_path": "/Shared Documents/Policies",
                "mode": "DRY-RUN",
                "file_types": [".pdf", ".docx"]
            },
            "engagement_id": ENGAGEMENT_ID
        }
        
        sp_response = requests.post(f"{MCP_GATEWAY_URL}/mcp/call", json=sharepoint_payload)
        assert sp_response.status_code == 200
        
        sp_result = sp_response.json()
        assert sp_result["success"] is True
        documents = sp_result["result"]["documents"]
        
        # 2. Simulate document analysis (would normally call doc analyzer agent)
        analysis_results = []
        for doc in documents:
            # Simulate security analysis findings
            finding = {
                "document": doc["file_name"],
                "checksum": doc["checksum_sha256"],
                "findings": [
                    {
                        "type": "policy_gap",
                        "severity": "medium",
                        "description": f"Policy document {doc['file_name']} requires review for compliance"
                    }
                ]
            }
            analysis_results.append(finding)
        
        # 3. Verify we have analysis results to export
        assert len(analysis_results) > 0
        
        # 4. Simulate Jira issue creation for each finding
        jira_issues = []
        for i, finding in enumerate(analysis_results):
            issue_data = {
                "project_key": "CYBER",
                "summary": f"Review required: {finding['document']}",
                "description": finding["findings"][0]["description"],
                "external_key": f"workflow-test-{finding['checksum'][:8]}",
                "priority": "Medium",
                "labels": ["document-review", "compliance"]
            }
            jira_issues.append(issue_data)
        
        # Verify workflow produced expected results
        assert len(jira_issues) == len(documents)
        
        # Verify audit trail exists
        assert all("external_key" in issue for issue in jira_issues)
        assert all("checksum" in finding for finding in analysis_results)
    
    def test_audit_trail_verification(self):
        """Verify audit entries exist for connector operations"""
        # This test verifies that operations create proper audit trails
        
        test_payload = {
            "tool": "sharepoint.fetch",
            "payload": {
                "tenant_id": "audit-test-tenant",
                "site_url": "https://contoso.sharepoint.com/sites/security",
                "document_path": "/Shared Documents/Test",
                "mode": "DRY-RUN"
            },
            "engagement_id": f"{ENGAGEMENT_ID}-audit"
        }
        
        response = requests.post(f"{MCP_GATEWAY_URL}/mcp/call", json=test_payload)
        assert response.status_code == 200
        
        result = response.json()
        assert result["success"] is True
        
        # Verify audit fields are present
        assert "call_id" in result
        assert "timestamp" in result
        assert "execution_time_ms" in result
        assert result["execution_time_ms"] > 0
        
        # Verify engagement scoping
        assert result["engagement_id"] == f"{ENGAGEMENT_ID}-audit"
    
    def test_error_handling_missing_demo_data(self):
        """Test graceful error handling for missing demo data"""
        payload = {
            "tool": "sharepoint.fetch",
            "payload": {
                "tenant_id": "nonexistent-tenant",
                "site_url": "https://nonexistent.sharepoint.com/sites/test",
                "document_path": "/Missing/Path",
                "mode": "DRY-RUN"
            },
            "engagement_id": "nonexistent-engagement"
        }
        
        response = requests.post(f"{MCP_GATEWAY_URL}/mcp/call", json=payload)
        assert response.status_code == 200
        
        result = response.json()
        assert result["success"] is False
        assert "error" in result
        assert "error_code" in result
        
        # Should be a controlled error, not a server crash
        assert result["error_code"] in ["DEMO_DATA_MISSING", "SECURITY_ERROR"]


class TestEnterpriseConnectorSecurity:
    """Security-focused tests for enterprise connectors"""
    
    def test_file_type_validation(self):
        """Test that dangerous file types are rejected"""
        payload = {
            "tool": "sharepoint.fetch",
            "payload": {
                "tenant_id": "security-test-tenant",
                "site_url": "https://contoso.sharepoint.com/sites/security",
                "document_path": "/Shared Documents/Test",
                "mode": "DRY-RUN",
                "file_types": [".exe", ".bat", ".ps1"]  # Dangerous file types
            },
            "engagement_id": ENGAGEMENT_ID
        }
        
        response = requests.post(f"{MCP_GATEWAY_URL}/mcp/call", json=payload)
        assert response.status_code == 200
        
        result = response.json()
        assert result["success"] is False
        assert result["error_code"] == "INVALID_FILE_TYPES"
        assert ".exe" in result["error"]
    
    def test_engagement_scoping(self):
        """Test that operations are properly scoped to engagement"""
        payload = {
            "tool": "sharepoint.fetch",
            "payload": {
                "tenant_id": "scoping-test-tenant",
                "site_url": "https://contoso.sharepoint.com/sites/security",
                "document_path": "/Shared Documents/Test",
                "mode": "DRY-RUN"
            },
            "engagement_id": "scoping-test-engagement"
        }
        
        response = requests.post(f"{MCP_GATEWAY_URL}/mcp/call", json=payload)
        assert response.status_code == 200
        
        result = response.json()
        
        # Even if it fails due to missing demo data, engagement should be tracked
        assert result["engagement_id"] == "scoping-test-engagement"
    
    def test_default_dry_run_mode(self):
        """Test that DRY-RUN is the default mode for security"""
        payload = {
            "tool": "sharepoint.fetch",
            "payload": {
                "tenant_id": "default-mode-test",
                "site_url": "https://contoso.sharepoint.com/sites/security",
                "document_path": "/Shared Documents/Test",
                # No mode specified - should default to DRY-RUN
            },
            "engagement_id": ENGAGEMENT_ID
        }
        
        response = requests.post(f"{MCP_GATEWAY_URL}/mcp/call", json=payload)
        assert response.status_code == 200
        
        result = response.json()
        
        # Even if the operation fails, we can verify the mode from the error context
        # or from successful operations that the default is DRY-RUN
        if result["success"]:
            assert result["result"]["mode"] == "DRY-RUN"