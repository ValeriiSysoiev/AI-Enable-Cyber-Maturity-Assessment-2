"""
MCP Gateway service package.
Provides secure MCP tools with engagement-scoped access control.
"""
from .config import MCPConfig, MCPOperationContext, get_mcp_config, init_mcp_config
from .security import MCPSecurityValidator, SecurityError, PathTraversalError, FileTypeError, FileSizeError
from .tools import MCPFilesystemTool, MCPPDFParserTool, MCPSearchTool

__all__ = [
    "MCPConfig",
    "MCPOperationContext", 
    "get_mcp_config",
    "init_mcp_config",
    "MCPSecurityValidator",
    "SecurityError",
    "PathTraversalError", 
    "FileTypeError",
    "FileSizeError",
    "MCPFilesystemTool",
    "MCPPDFParserTool",
    "MCPSearchTool"
]