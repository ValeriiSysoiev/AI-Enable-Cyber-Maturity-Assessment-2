"""
MCP Tools - Core tool registry and base classes for Model Context Protocol
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class McpError(Exception):
    """Custom exception for MCP tool errors"""
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR"):
        super().__init__(message)
        self.code = code

@dataclass
class McpCallResult:
    """Result of an MCP tool call"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    execution_time_ms: Optional[float] = None

class McpTool(ABC):
    """Base class for MCP tools"""
    
    def __init__(self, name: str, description: str, schema: Dict[str, Any]):
        self.name = name
        self.description = description
        self.schema = schema
        self.logger = logging.LoggerAdapter(logger, {'tool': name})

    @abstractmethod
    async def execute(self, payload: Dict[str, Any], engagement_id: str) -> McpCallResult:
        """Execute the tool with the given payload"""
        pass

    def validate_payload(self, payload: Dict[str, Any], required_fields: list[str]) -> None:
        """Validate that payload contains required fields"""
        missing_fields = [field for field in required_fields if field not in payload]
        if missing_fields:
            raise McpError(
                f"Missing required fields: {', '.join(missing_fields)}",
                "INVALID_PAYLOAD"
            )

class McpToolRegistry:
    """Registry for MCP tools"""
    
    def __init__(self):
        self.tools: Dict[str, McpTool] = {}
        self.allowlist: set[str] = set()
        
    def register(self, tool: McpTool, allowed_by_default: bool = True) -> None:
        """Register an MCP tool"""
        if tool.name in self.tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        
        self.tools[tool.name] = tool
        
        if allowed_by_default:
            self.allowlist.add(tool.name)
            
        logger.info(f"Registered MCP tool: {tool.name}")
    
    def is_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed to be executed"""
        return tool_name in self.allowlist
    
    def add_to_allowlist(self, tool_name: str) -> None:
        """Add a tool to the allowlist"""
        if tool_name in self.tools:
            self.allowlist.add(tool_name)
        else:
            raise ValueError(f"Tool '{tool_name}' is not registered")
    
    def remove_from_allowlist(self, tool_name: str) -> None:
        """Remove a tool from the allowlist"""
        self.allowlist.discard(tool_name)
    
    def get_tool(self, tool_name: str) -> Optional[McpTool]:
        """Get a tool by name"""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> Dict[str, McpTool]:
        """Get all registered tools"""
        return self.tools.copy()
    
    def list_allowed_tools(self) -> Dict[str, McpTool]:
        """Get all allowed tools"""
        return {name: tool for name, tool in self.tools.items() if name in self.allowlist}