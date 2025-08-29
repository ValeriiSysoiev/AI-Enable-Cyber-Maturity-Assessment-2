"""
MCP Gateway service package.
Provides secure MCP tools with engagement-scoped access control.
"""
import sys
sys.path.append("/app")
from services.mcp_gateway.config import MCPConfig, MCPOperationContext, get_mcp_config, init_mcp_config
from services.mcp_gateway.security import MCPSecurityValidator, SecurityError, PathTraversalError, FileTypeError, FileSizeError
from services.mcp_gateway.tools import MCPFilesystemTool, MCPPDFParserTool, MCPSearchTool

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