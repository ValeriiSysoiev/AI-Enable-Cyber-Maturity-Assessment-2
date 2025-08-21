"""
Tests for Jira MCP tools
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch

from mcp_tools.jira_tools import JiraCreateIssueTool, JiraUpdateIssueTool, register_jira_tools
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
def jira_create_tool(security_validator):
    """Create Jira create issue tool for tests"""
    return JiraCreateIssueTool(security_validator)


@pytest.fixture
def jira_update_tool(security_validator):
    """Create Jira update issue tool for tests"""
    return JiraUpdateIssueTool(security_validator)


@pytest.fixture
def artifacts_dir(temp_data_root):
    """Create artifacts directory for dry-run mode"""
    artifacts_dir = Path(temp_data_root) / "../artifacts/jira_dryrun"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


class TestJiraCreateIssueTool:
    """Test Jira create issue tool functionality"""
    
    def test_tool_initialization(self, jira_create_tool):
        """Test tool is properly initialized"""
        assert jira_create_tool.name == "jira.createIssue"
        assert "Jira issue" in jira_create_tool.description
        assert "project_key" in jira_create_tool.schema["properties"]
        assert "external_key" in jira_create_tool.schema["properties"]
    
    def test_schema_validation(self, jira_create_tool):
        """Test tool schema is valid"""
        schema = jira_create_tool.schema
        assert schema["type"] == "object"
        required_fields = {"project_key", "summary", "description", "external_key"}
        assert set(schema["required"]) == required_fields
        
        # Check mode enum
        mode_prop = schema["properties"]["mode"]
        assert mode_prop["enum"] == ["REAL", "DRY-RUN"]
        assert mode_prop["default"] == "DRY-RUN"
        
        # Check priority enum
        priority_prop = schema["properties"]["priority"]
        expected_priorities = ["Highest", "High", "Medium", "Low", "Lowest"]
        assert priority_prop["enum"] == expected_priorities
    
    @pytest.mark.asyncio
    async def test_dry_run_create_success(self, jira_create_tool, artifacts_dir):
        """Test successful dry-run issue creation"""
        payload = {
            "project_key": "CYBER",
            "summary": "Critical security vulnerability found",
            "description": "SQL injection vulnerability in user login form requires immediate remediation",
            "priority": "High",
            "labels": ["security", "vulnerability", "urgent"],
            "external_key": "engagement-123_finding-456",
            "mode": "DRY-RUN"
        }
        
        result = await jira_create_tool.execute(payload, "test-engagement")
        
        assert result.success is True
        assert result.error is None
        
        data = result.result
        assert data["status"] == "created"
        assert data["external_key"] == "engagement-123_finding-456"
        assert data["mode"] == "DRY-RUN"
        assert "CYBER-" in data["issue_key"]
        assert "your-org.atlassian.net" in data["issue_url"]
        assert "artifact_path" in data
        
        # Verify artifact file was created
        artifact_path = Path(data["artifact_path"])
        assert artifact_path.exists()
        
        # Verify artifact content
        with open(artifact_path, 'r') as f:
            artifact_data = json.load(f)
        
        assert artifact_data["project_key"] == "CYBER"
        assert artifact_data["summary"] == payload["summary"]
        assert artifact_data["description"] == payload["description"]
        assert artifact_data["priority"] == "High"
        assert artifact_data["labels"] == ["security", "vulnerability", "urgent"]
        assert artifact_data["external_key"] == "engagement-123_finding-456"
        assert artifact_data["engagement_id"] == "test-engagement"
        assert artifact_data["created_by"] == "mcp.jira.createIssue"
    
    @pytest.mark.asyncio
    async def test_idempotency_check(self, jira_create_tool, artifacts_dir):
        """Test idempotency - same external_key should return existing issue"""
        payload = {
            "project_key": "CYBER",
            "summary": "Test issue",
            "description": "Test description",
            "external_key": "test-external-key",
            "mode": "DRY-RUN"
        }
        
        # First call - should create new issue
        result1 = await jira_create_tool.execute(payload, "test-engagement")
        assert result1.success is True
        assert result1.result["status"] == "created"
        original_issue_key = result1.result["issue_key"]
        
        # Second call with same external_key - should return existing
        result2 = await jira_create_tool.execute(payload, "test-engagement")
        assert result2.success is True
        assert result2.result["status"] == "existing"
        assert result2.result["issue_key"] == original_issue_key
    
    @pytest.mark.asyncio
    async def test_real_mode_missing_credentials(self, jira_create_tool):
        """Test real mode fails gracefully without credentials"""
        payload = {
            "project_key": "CYBER",
            "summary": "Test issue",
            "description": "Test description",
            "external_key": "test-key",
            "mode": "REAL"
        }
        
        with patch.dict('os.environ', {}, clear=True):
            result = await jira_create_tool.execute(payload, "test-engagement")
            
            assert result.success is False
            assert result.error_code == "MISSING_CREDENTIALS"
            assert "JIRA_URL" in result.error
    
    @pytest.mark.asyncio
    async def test_payload_validation(self, jira_create_tool):
        """Test payload validation catches missing required fields"""
        payload = {
            "project_key": "CYBER"
            # Missing required fields
        }
        
        result = await jira_create_tool.execute(payload, "test-engagement")
        
        assert result.success is False
        assert result.error_code == "INVALID_PAYLOAD"
        assert "Missing required fields" in result.error
    
    @pytest.mark.asyncio
    async def test_default_values(self, jira_create_tool, artifacts_dir):
        """Test default values are applied correctly"""
        payload = {
            "project_key": "CYBER",
            "summary": "Test issue",
            "description": "Test description",
            "external_key": "test-key",
            # mode defaults to DRY-RUN
            # issue_type defaults to Task
            # priority defaults to Medium
            # labels defaults to []
        }
        
        result = await jira_create_tool.execute(payload, "test-engagement")
        
        assert result.success is True
        
        # Check artifact for defaults
        artifact_path = Path(result.result["artifact_path"])
        with open(artifact_path, 'r') as f:
            artifact_data = json.load(f)
        
        assert artifact_data["issue_type"] == "Task"
        assert artifact_data["priority"] == "Medium"
        assert artifact_data["labels"] == []


class TestJiraUpdateIssueTool:
    """Test Jira update issue tool functionality"""
    
    def test_tool_initialization(self, jira_update_tool):
        """Test tool is properly initialized"""
        assert jira_update_tool.name == "jira.updateIssue"
        assert "Update existing Jira issue" in jira_update_tool.description
        assert "issue_key" in jira_update_tool.schema["properties"]
        assert "external_key" in jira_update_tool.schema["properties"]
    
    def test_schema_validation(self, jira_update_tool):
        """Test tool schema is valid"""
        schema = jira_update_tool.schema
        assert schema["type"] == "object"
        assert set(schema["required"]) == {"issue_key", "external_key"}
        
        # Check status enum
        status_prop = schema["properties"]["status"]
        expected_statuses = ["Open", "In Progress", "Done", "Closed"]
        assert status_prop["enum"] == expected_statuses
    
    async def _create_test_issue(self, jira_create_tool, artifacts_dir):
        """Helper to create a test issue for update tests"""
        payload = {
            "project_key": "CYBER",
            "summary": "Original summary",
            "description": "Original description",
            "external_key": "test-update-key",
            "mode": "DRY-RUN"
        }
        
        result = await jira_create_tool.execute(payload, "test-engagement")
        return result.result["issue_key"]
    
    @pytest.mark.asyncio
    async def test_dry_run_update_success(self, jira_create_tool, jira_update_tool, artifacts_dir):
        """Test successful dry-run issue update"""
        # First create an issue
        issue_key = await self._create_test_issue(jira_create_tool, artifacts_dir)
        
        # Now update it
        update_payload = {
            "issue_key": issue_key,
            "external_key": "test-update-key",
            "summary": "Updated summary",
            "description": "Updated description",
            "status": "In Progress",
            "priority": "High",
            "labels": ["updated", "in-progress"],
            "comment": "This issue has been updated with new information",
            "mode": "DRY-RUN"
        }
        
        result = await jira_update_tool.execute(update_payload, "test-engagement")
        
        assert result.success is True
        assert result.error is None
        
        data = result.result
        assert data["status"] == "updated"
        assert data["external_key"] == "test-update-key"
        assert data["issue_key"] == issue_key
        assert data["mode"] == "DRY-RUN"
        
        # Verify updated artifact content
        artifact_path = Path(data["artifact_path"])
        with open(artifact_path, 'r') as f:
            artifact_data = json.load(f)
        
        assert artifact_data["summary"] == "Updated summary"
        assert artifact_data["description"] == "Updated description"
        assert artifact_data["status"] == "In Progress"
        assert artifact_data["priority"] == "High"
        assert artifact_data["labels"] == ["updated", "in-progress"]
        
        # Check update history
        assert "updates" in artifact_data
        assert len(artifact_data["updates"]) == 1
        update_record = artifact_data["updates"][0]
        assert update_record["updated_by"] == "mcp.jira.updateIssue"
        assert update_record["comment"] == "This issue has been updated with new information"
        assert update_record["external_key"] == "test-update-key"
    
    @pytest.mark.asyncio
    async def test_partial_update(self, jira_create_tool, jira_update_tool, artifacts_dir):
        """Test partial update - only some fields provided"""
        # First create an issue
        issue_key = await self._create_test_issue(jira_create_tool, artifacts_dir)
        
        # Update only status and add comment
        update_payload = {
            "issue_key": issue_key,
            "external_key": "test-partial-key",
            "status": "Done",
            "comment": "Marking as done",
            "mode": "DRY-RUN"
        }
        
        result = await jira_update_tool.execute(update_payload, "test-engagement")
        
        assert result.success is True
        
        # Verify only status was updated, other fields unchanged
        artifact_path = Path(result.result["artifact_path"])
        with open(artifact_path, 'r') as f:
            artifact_data = json.load(f)
        
        assert artifact_data["status"] == "Done"
        assert artifact_data["summary"] == "Original summary"  # Unchanged
        assert artifact_data["description"] == "Original description"  # Unchanged
        
        # Check update history
        update_record = artifact_data["updates"][0]
        assert update_record["comment"] == "Marking as done"
    
    @pytest.mark.asyncio
    async def test_issue_not_found(self, jira_update_tool, artifacts_dir):
        """Test update fails when issue doesn't exist"""
        update_payload = {
            "issue_key": "CYBER-999999",
            "external_key": "nonexistent-key",
            "summary": "Updated summary",
            "mode": "DRY-RUN"
        }
        
        result = await jira_update_tool.execute(update_payload, "test-engagement")
        
        assert result.success is False
        assert result.error_code == "ISSUE_NOT_FOUND"
        assert "CYBER-999999 not found" in result.error
    
    @pytest.mark.asyncio
    async def test_real_mode_missing_credentials(self, jira_update_tool):
        """Test real mode fails gracefully without credentials"""
        payload = {
            "issue_key": "CYBER-1001",
            "external_key": "test-key",
            "summary": "Updated summary",
            "mode": "REAL"
        }
        
        with patch.dict('os.environ', {}, clear=True):
            result = await jira_update_tool.execute(payload, "test-engagement")
            
            assert result.success is False
            assert result.error_code == "MISSING_CREDENTIALS"
            assert "JIRA_URL" in result.error


class TestJiraToolRegistry:
    """Test Jira tool registration"""
    
    def test_register_jira_tools(self, security_validator):
        """Test Jira tools register correctly"""
        registry = McpToolRegistry()
        
        # Should start empty
        assert len(registry.tools) == 0
        
        register_jira_tools(registry, security_validator)
        
        # Should have both Jira tools registered
        assert "jira.createIssue" in registry.tools
        assert "jira.updateIssue" in registry.tools
        assert registry.is_allowed("jira.createIssue")
        assert registry.is_allowed("jira.updateIssue")
        
        create_tool = registry.get_tool("jira.createIssue")
        update_tool = registry.get_tool("jira.updateIssue")
        assert isinstance(create_tool, JiraCreateIssueTool)
        assert isinstance(update_tool, JiraUpdateIssueTool)


class TestJiraIntegration:
    """Test Jira tools integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_create_update_workflow(self, jira_create_tool, jira_update_tool, artifacts_dir):
        """Test complete create -> update workflow"""
        # 1. Create issue
        create_payload = {
            "project_key": "CYBER",
            "summary": "Security finding from assessment",
            "description": "Detailed security finding description",
            "priority": "Medium",
            "labels": ["security", "assessment"],
            "external_key": "engagement-123_finding-789",
            "mode": "DRY-RUN"
        }
        
        create_result = await jira_create_tool.execute(create_payload, "test-engagement")
        assert create_result.success is True
        
        issue_key = create_result.result["issue_key"]
        
        # 2. Update issue
        update_payload = {
            "issue_key": issue_key,
            "external_key": "engagement-123_finding-789", 
            "status": "In Progress",
            "comment": "Investigation started",
            "mode": "DRY-RUN"
        }
        
        update_result = await jira_update_tool.execute(update_payload, "test-engagement")
        assert update_result.success is True
        
        # 3. Verify final state
        artifact_path = Path(update_result.result["artifact_path"])
        with open(artifact_path, 'r') as f:
            final_data = json.load(f)
        
        # Should have original creation data
        assert final_data["project_key"] == "CYBER"
        assert final_data["summary"] == "Security finding from assessment"
        assert final_data["external_key"] == "engagement-123_finding-789"
        
        # Should have updated status
        assert final_data["status"] == "In Progress"
        
        # Should have update history
        assert len(final_data["updates"]) == 1
        assert final_data["updates"][0]["comment"] == "Investigation started"
    
    @pytest.mark.asyncio
    async def test_multiple_updates(self, jira_create_tool, jira_update_tool, artifacts_dir):
        """Test multiple sequential updates maintain history"""
        # Create issue
        issue_key = await self._create_test_issue(jira_create_tool, artifacts_dir)
        
        # Multiple updates
        updates = [
            {"status": "In Progress", "comment": "Started working"},
            {"priority": "High", "comment": "Escalated priority"},
            {"status": "Done", "comment": "Completed resolution"}
        ]
        
        for i, update_data in enumerate(updates):
            update_payload = {
                "issue_key": issue_key,
                "external_key": f"test-multi-{i}",
                "mode": "DRY-RUN",
                **update_data
            }
            
            result = await jira_update_tool.execute(update_payload, "test-engagement")
            assert result.success is True
        
        # Verify final state has all updates
        artifact_path = Path(result.result["artifact_path"])
        with open(artifact_path, 'r') as f:
            final_data = json.load(f)
        
        assert len(final_data["updates"]) == 3
        assert final_data["status"] == "Done"
        assert final_data["priority"] == "High"
        
        # Check update history order
        comments = [update["comment"] for update in final_data["updates"]]
        expected_comments = ["Started working", "Escalated priority", "Completed resolution"]
        assert comments == expected_comments
    
    async def _create_test_issue(self, jira_create_tool, artifacts_dir):
        """Helper to create a test issue"""
        payload = {
            "project_key": "CYBER",
            "summary": "Test issue",
            "description": "Test description", 
            "external_key": "test-issue-key",
            "mode": "DRY-RUN"
        }
        
        result = await jira_create_tool.execute(payload, "test-engagement")
        return result.result["issue_key"]