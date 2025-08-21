"""
Jira tools for MCP Gateway

Provides Jira issue creation and update operations with idempotency support,
comprehensive error handling, and both real and dry-run modes.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from . import McpTool, McpCallResult, McpError, McpToolRegistry
from security import SecurityValidator

logger = logging.getLogger(__name__)

class JiraCreateIssueTool(McpTool):
    """Tool for creating Jira issues with idempotency support"""
    
    def __init__(self, security_validator: SecurityValidator):
        super().__init__(
            name="jira.createIssue",
            description="Create Jira issue with idempotency and audit tracking",
            schema={
                "type": "object",
                "properties": {
                    "project_key": {
                        "type": "string",
                        "description": "Jira project key (e.g., 'CYBER', 'SEC')"
                    },
                    "issue_type": {
                        "type": "string",
                        "description": "Issue type (e.g., 'Task', 'Bug', 'Story')",
                        "default": "Task"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Issue summary/title"
                    },
                    "description": {
                        "type": "string",
                        "description": "Issue description/body"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["Highest", "High", "Medium", "Low", "Lowest"],
                        "description": "Issue priority",
                        "default": "Medium"
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Issue labels",
                        "default": []
                    },
                    "external_key": {
                        "type": "string",
                        "description": "External identifier for idempotency (e.g., engagement_id + finding_id)"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["REAL", "DRY-RUN"],
                        "description": "Execution mode: REAL uses env creds, DRY-RUN writes JSON",
                        "default": "DRY-RUN"
                    }
                },
                "required": ["project_key", "summary", "description", "external_key"]
            }
        )
        self.security_validator = security_validator
        self._issue_cache = {}  # Simple in-memory cache for idempotency
    
    async def execute(self, payload: Dict[str, Any], engagement_id: str) -> McpCallResult:
        """Execute Jira issue creation"""
        try:
            self.validate_payload(payload, ["project_key", "summary", "description", "external_key"])
            
            mode = payload.get("mode", "DRY-RUN")
            project_key = payload["project_key"]
            summary = payload["summary"]
            description = payload["description"]
            external_key = payload["external_key"]
            issue_type = payload.get("issue_type", "Task")
            priority = payload.get("priority", "Medium")
            labels = payload.get("labels", [])
            
            # Check for idempotency
            cache_key = f"{engagement_id}:{external_key}"
            if cache_key in self._issue_cache:
                existing_issue = self._issue_cache[cache_key]
                self.logger.info(f"Returning existing issue for external_key: {external_key}")
                return McpCallResult(
                    success=True,
                    result={
                        "issue_key": existing_issue["issue_key"],
                        "issue_url": existing_issue["issue_url"],
                        "status": "existing",
                        "external_key": external_key,
                        "created_at": existing_issue["created_at"]
                    }
                )
            
            self.logger.info(
                f"Creating Jira issue",
                extra={
                    "mode": mode,
                    "project_key": project_key,
                    "external_key": external_key,
                    "engagement_id": engagement_id
                }
            )
            
            if mode == "REAL":
                return await self._create_real(project_key, issue_type, summary, description,
                                             priority, labels, external_key, engagement_id)
            else:
                return await self._create_dryrun(project_key, issue_type, summary, description,
                                               priority, labels, external_key, engagement_id)
                
        except Exception as e:
            self.logger.error(f"Jira issue creation failed: {e}", exc_info=True)
            if isinstance(e, McpError):
                return McpCallResult(success=False, error=str(e), error_code=e.code)
            return McpCallResult(success=False, error="Jira issue creation failed", error_code="CREATE_ERROR")
    
    async def _create_real(self, project_key: str, issue_type: str, summary: str, description: str,
                          priority: str, labels: list, external_key: str, engagement_id: str) -> McpCallResult:
        """Create issue in real Jira using environment credentials"""
        
        # Check for required environment variables
        required_env_vars = ["JIRA_URL", "JIRA_USERNAME", "JIRA_API_TOKEN"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            self.logger.warning(f"Missing Jira credentials: {missing_vars}")
            raise McpError(
                f"Missing required environment variables: {missing_vars}",
                "MISSING_CREDENTIALS"
            )
        
        # TODO: Implement real Jira REST API integration
        # This would use Jira REST API with the credentials to:
        # 1. Authenticate with Jira
        # 2. Create issue with proper field mapping
        # 3. Handle API errors and rate limiting
        # 4. Return actual Jira issue key and URL
        
        # For now, return placeholder indicating real mode would be implemented
        return McpCallResult(
            success=False,
            error="Real Jira integration not yet implemented in this demo",
            error_code="NOT_IMPLEMENTED"
        )
    
    async def _create_dryrun(self, project_key: str, issue_type: str, summary: str, description: str,
                           priority: str, labels: list, external_key: str, engagement_id: str) -> McpCallResult:
        """Create issue in dry-run mode by writing JSON to artifacts"""
        
        # Generate mock Jira issue data
        issue_key = f"{project_key}-{len(os.listdir(Path(self.security_validator.data_root) / '../artifacts/jira_dryrun')) + 1001}"
        timestamp = datetime.utcnow().isoformat()
        
        issue_data = {
            "issue_key": issue_key,
            "project_key": project_key,
            "issue_type": issue_type,
            "summary": summary,
            "description": description,
            "priority": priority,
            "labels": labels,
            "external_key": external_key,
            "engagement_id": engagement_id,
            "status": "Open",
            "created_at": timestamp,
            "created_by": "mcp.jira.createIssue",
            "mode": "DRY-RUN",
            "issue_url": f"https://your-org.atlassian.net/browse/{issue_key}"
        }
        
        # Write to dry-run artifacts directory
        artifacts_dir = Path(self.security_validator.data_root) / "../artifacts/jira_dryrun"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        artifact_file = artifacts_dir / f"{issue_key}_{external_key}.json"
        with open(artifact_file, 'w') as f:
            json.dump(issue_data, f, indent=2)
        
        # Cache for idempotency
        cache_key = f"{engagement_id}:{external_key}"
        self._issue_cache[cache_key] = issue_data
        
        self.logger.info(f"Created dry-run Jira issue: {issue_key} -> {artifact_file}")
        
        return McpCallResult(
            success=True,
            result={
                "issue_key": issue_key,
                "issue_url": issue_data["issue_url"],
                "status": "created",
                "external_key": external_key,
                "created_at": timestamp,
                "artifact_path": str(artifact_file),
                "mode": "DRY-RUN"
            }
        )


class JiraUpdateIssueTool(McpTool):
    """Tool for updating existing Jira issues"""
    
    def __init__(self, security_validator: SecurityValidator):
        super().__init__(
            name="jira.updateIssue",
            description="Update existing Jira issue with audit tracking",
            schema={
                "type": "object",
                "properties": {
                    "issue_key": {
                        "type": "string",
                        "description": "Jira issue key to update (e.g., 'CYBER-1001')"
                    },
                    "external_key": {
                        "type": "string",
                        "description": "External identifier for tracking"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Updated issue summary/title"
                    },
                    "description": {
                        "type": "string",
                        "description": "Updated issue description/body"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["Open", "In Progress", "Done", "Closed"],
                        "description": "Issue status"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["Highest", "High", "Medium", "Low", "Lowest"],
                        "description": "Updated issue priority"
                    },
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Updated issue labels"
                    },
                    "comment": {
                        "type": "string",
                        "description": "Comment to add to the issue"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["REAL", "DRY-RUN"],
                        "description": "Execution mode: REAL uses env creds, DRY-RUN writes JSON",
                        "default": "DRY-RUN"
                    }
                },
                "required": ["issue_key", "external_key"]
            }
        )
        self.security_validator = security_validator
    
    async def execute(self, payload: Dict[str, Any], engagement_id: str) -> McpCallResult:
        """Execute Jira issue update"""
        try:
            self.validate_payload(payload, ["issue_key", "external_key"])
            
            mode = payload.get("mode", "DRY-RUN")
            issue_key = payload["issue_key"]
            external_key = payload["external_key"]
            
            # Optional update fields
            summary = payload.get("summary")
            description = payload.get("description")
            status = payload.get("status")
            priority = payload.get("priority")
            labels = payload.get("labels")
            comment = payload.get("comment")
            
            self.logger.info(
                f"Updating Jira issue",
                extra={
                    "mode": mode,
                    "issue_key": issue_key,
                    "external_key": external_key,
                    "engagement_id": engagement_id
                }
            )
            
            if mode == "REAL":
                return await self._update_real(issue_key, external_key, summary, description,
                                             status, priority, labels, comment, engagement_id)
            else:
                return await self._update_dryrun(issue_key, external_key, summary, description,
                                               status, priority, labels, comment, engagement_id)
                
        except Exception as e:
            self.logger.error(f"Jira issue update failed: {e}", exc_info=True)
            if isinstance(e, McpError):
                return McpCallResult(success=False, error=str(e), error_code=e.code)
            return McpCallResult(success=False, error="Jira issue update failed", error_code="UPDATE_ERROR")
    
    async def _update_real(self, issue_key: str, external_key: str, summary: Optional[str],
                          description: Optional[str], status: Optional[str], priority: Optional[str],
                          labels: Optional[list], comment: Optional[str], engagement_id: str) -> McpCallResult:
        """Update issue in real Jira using environment credentials"""
        
        # Check for required environment variables
        required_env_vars = ["JIRA_URL", "JIRA_USERNAME", "JIRA_API_TOKEN"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            self.logger.warning(f"Missing Jira credentials: {missing_vars}")
            raise McpError(
                f"Missing required environment variables: {missing_vars}",
                "MISSING_CREDENTIALS"
            )
        
        # TODO: Implement real Jira REST API integration
        # This would use Jira REST API with the credentials to:
        # 1. Authenticate with Jira
        # 2. Update issue fields and add comments
        # 3. Handle API errors and validation
        # 4. Return updated issue data
        
        # For now, return placeholder indicating real mode would be implemented
        return McpCallResult(
            success=False,
            error="Real Jira integration not yet implemented in this demo",
            error_code="NOT_IMPLEMENTED"
        )
    
    async def _update_dryrun(self, issue_key: str, external_key: str, summary: Optional[str],
                           description: Optional[str], status: Optional[str], priority: Optional[str],
                           labels: Optional[list], comment: Optional[str], engagement_id: str) -> McpCallResult:
        """Update issue in dry-run mode by writing JSON to artifacts"""
        
        artifacts_dir = Path(self.security_validator.data_root) / "../artifacts/jira_dryrun"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Look for existing issue file
        existing_files = list(artifacts_dir.glob(f"{issue_key}_*.json"))
        if not existing_files:
            raise McpError(f"Issue {issue_key} not found in dry-run artifacts", "ISSUE_NOT_FOUND")
        
        issue_file = existing_files[0]
        
        # Load existing issue data
        with open(issue_file, 'r') as f:
            issue_data = json.load(f)
        
        # Update fields if provided
        timestamp = datetime.utcnow().isoformat()
        
        if summary:
            issue_data["summary"] = summary
        if description:
            issue_data["description"] = description
        if status:
            issue_data["status"] = status
        if priority:
            issue_data["priority"] = priority
        if labels is not None:
            issue_data["labels"] = labels
        
        # Add update history
        if "updates" not in issue_data:
            issue_data["updates"] = []
        
        update_record = {
            "updated_at": timestamp,
            "updated_by": "mcp.jira.updateIssue",
            "engagement_id": engagement_id,
            "external_key": external_key
        }
        
        if comment:
            update_record["comment"] = comment
            
        issue_data["updates"].append(update_record)
        issue_data["last_updated"] = timestamp
        
        # Write updated data back
        with open(issue_file, 'w') as f:
            json.dump(issue_data, f, indent=2)
        
        self.logger.info(f"Updated dry-run Jira issue: {issue_key} -> {issue_file}")
        
        return McpCallResult(
            success=True,
            result={
                "issue_key": issue_key,
                "issue_url": issue_data["issue_url"],
                "status": "updated",
                "external_key": external_key,
                "updated_at": timestamp,
                "artifact_path": str(issue_file),
                "mode": "DRY-RUN"
            }
        )


def register_jira_tools(registry: McpToolRegistry, security_validator: SecurityValidator):
    """Register Jira tools with the MCP registry"""
    
    jira_create = JiraCreateIssueTool(security_validator)
    jira_update = JiraUpdateIssueTool(security_validator)
    
    registry.register(jira_create, allowed_by_default=True)
    registry.register(jira_update, allowed_by_default=True)
    
    logger.info("Jira tools registered successfully")