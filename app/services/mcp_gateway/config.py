"""
MCP Gateway configuration and security policies.
"""
import os
from pathlib import Path
from typing import Dict, List, Set, Optional
from pydantic import BaseModel, Field, validator
from dataclasses import dataclass


class MCPToolConfig(BaseModel):
    """Configuration for individual MCP tools"""
    enabled: bool = True
    max_file_size_mb: int = Field(default=10, ge=1, le=100)
    allowed_extensions: Set[str] = Field(default={".txt", ".md", ".json", ".csv", ".yml", ".yaml"})
    rate_limit_per_minute: int = Field(default=60, ge=1)
    

class MCPSecurityConfig(BaseModel):
    """Security configuration for MCP operations"""
    enable_path_jailing: bool = True
    enable_content_redaction: bool = True
    max_path_depth: int = Field(default=10, ge=1, le=50)
    blocked_patterns: List[str] = Field(default=[
        "*.env", "*.key", "*.pem", "*.p12", "*.pfx", 
        "id_rsa", "id_dsa", "*.secret", "password*"
    ])
    

class MCPConfig(BaseModel):
    """Main MCP Gateway configuration"""
    base_data_path: Path = Field(default=Path("/app/data"))
    
    # Tool configurations
    filesystem: MCPToolConfig = Field(default_factory=MCPToolConfig)
    pdf_parser: MCPToolConfig = Field(default_factory=lambda: MCPToolConfig(
        max_file_size_mb=50,
        allowed_extensions={".pdf"}
    ))
    search: MCPToolConfig = Field(default_factory=lambda: MCPToolConfig(
        rate_limit_per_minute=30
    ))
    
    # Security settings
    security: MCPSecurityConfig = Field(default_factory=MCPSecurityConfig)
    
    @validator('base_data_path')
    def validate_base_path(cls, v):
        """Ensure base data path exists and is absolute"""
        if not v.is_absolute():
            v = Path("/app") / v
        return v.resolve()
    
    def get_engagement_sandbox(self, engagement_id: str) -> Path:
        """Get sandboxed path for engagement data"""
        sandbox = self.base_data_path / "engagements" / engagement_id
        sandbox.mkdir(parents=True, exist_ok=True)
        return sandbox.resolve()
    
    def validate_allowlist(self, engagement_id: str, tool_name: str) -> bool:
        """Validate if tool is allowed for engagement (placeholder for future ACL)"""
        # For MVP, all tools are allowed for all engagements
        # Future: implement engagement-specific tool allowlists
        return True


@dataclass
class MCPOperationContext:
    """Context information for MCP operations"""
    correlation_id: str
    user_email: str
    engagement_id: str
    tool_name: str
    operation: str
    tenant_id: Optional[str] = None


# Global configuration instance
_mcp_config: Optional[MCPConfig] = None


def get_mcp_config() -> MCPConfig:
    """Get global MCP configuration instance"""
    global _mcp_config
    if _mcp_config is None:
        _mcp_config = MCPConfig()
    return _mcp_config


def init_mcp_config(config_override: Optional[Dict] = None) -> MCPConfig:
    """Initialize MCP configuration with optional overrides"""
    global _mcp_config
    if config_override:
        _mcp_config = MCPConfig(**config_override)
    else:
        _mcp_config = MCPConfig()
    return _mcp_config