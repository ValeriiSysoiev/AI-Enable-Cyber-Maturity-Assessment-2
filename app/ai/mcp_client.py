"""
MCP Client Interface and Implementation

Provides a client interface for calling MCP Gateway tools with feature flag support.
"""

import os
import uuid
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from datetime import datetime
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class McpClientError(Exception):
    """Exception raised by MCP client operations"""
    def __init__(self, message: str, error_code: str = "UNKNOWN"):
        super().__init__(message)
        self.error_code = error_code

class McpCallResult(BaseModel):
    """Result of an MCP call"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    call_id: str
    execution_time_ms: float

class IMcpClient(ABC):
    """Interface for MCP client implementations"""
    
    @abstractmethod
    async def call(self, tool: str, payload: Dict[str, Any], engagement_id: str, 
                   call_id: Optional[str] = None) -> McpCallResult:
        """Call an MCP tool"""
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if MCP is enabled"""
        pass
    
    @abstractmethod
    async def list_tools(self) -> Dict[str, Any]:
        """List available MCP tools"""
        pass

class HttpMcpClient(IMcpClient):
    """HTTP-based MCP client implementation"""
    
    def __init__(self, gateway_url: str, timeout: float = 30.0):
        self.gateway_url = gateway_url.rstrip('/')
        self.timeout = timeout
        self.enabled = True
        
        # Configure HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True
        )
    
    async def call(self, tool: str, payload: Dict[str, Any], engagement_id: str,
                   call_id: Optional[str] = None) -> McpCallResult:
        """Call an MCP tool via HTTP"""
        if not self.enabled:
            raise McpClientError("MCP client is disabled", "CLIENT_DISABLED")
        
        if not call_id:
            call_id = str(uuid.uuid4())
        
        request_data = {
            "tool": tool,
            "payload": payload,
            "engagement_id": engagement_id,
            "call_id": call_id
        }
        
        try:
            logger.debug(
                f"Making MCP call: {tool}",
                extra={
                    "call_id": call_id,
                    "engagement_id": engagement_id,
                    "tool": tool
                }
            )
            
            response = await self.client.post(
                f"{self.gateway_url}/mcp/call",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 503:
                # MCP is disabled on server side
                raise McpClientError("MCP is disabled on server", "SERVER_DISABLED")
            
            response.raise_for_status()
            response_data = response.json()
            
            return McpCallResult(**response_data)
            
        except httpx.TimeoutException:
            logger.error(f"MCP call timeout: {tool}", extra={"call_id": call_id})
            raise McpClientError(f"Call timeout for tool {tool}", "TIMEOUT")
        except httpx.HTTPStatusError as e:
            logger.error(
                f"MCP call HTTP error: {e.response.status_code}",
                extra={"call_id": call_id, "status_code": e.response.status_code}
            )
            raise McpClientError(f"HTTP error {e.response.status_code}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"MCP call failed: {e}", extra={"call_id": call_id}, exc_info=True)
            raise McpClientError(f"MCP call failed: {e}", "NETWORK_ERROR")
    
    def is_enabled(self) -> bool:
        """Check if MCP client is enabled"""
        return self.enabled
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available MCP tools"""
        if not self.enabled:
            raise McpClientError("MCP client is disabled", "CLIENT_DISABLED")
        
        try:
            response = await self.client.get(f"{self.gateway_url}/mcp/tools")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to list MCP tools: {e}", exc_info=True)
            raise McpClientError(f"Failed to list tools: {e}", "LIST_ERROR")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check MCP Gateway health"""
        try:
            response = await self.client.get(f"{self.gateway_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"MCP health check failed: {e}", exc_info=True)
            raise McpClientError(f"Health check failed: {e}", "HEALTH_ERROR")
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

class NoOpMcpClient(IMcpClient):
    """No-op MCP client for when MCP is disabled"""
    
    async def call(self, tool: str, payload: Dict[str, Any], engagement_id: str,
                   call_id: Optional[str] = None) -> McpCallResult:
        """Always returns disabled error"""
        raise McpClientError("MCP is disabled", "DISABLED")
    
    def is_enabled(self) -> bool:
        """Always returns False"""
        return False
    
    async def list_tools(self) -> Dict[str, Any]:
        """Returns empty tools list"""
        return {"tools": [], "count": 0}

class McpClientFactory:
    """Factory for creating MCP clients based on configuration"""
    
    @staticmethod
    def create_client(enabled: bool = None, gateway_url: str = None) -> IMcpClient:
        """Create an MCP client based on configuration"""
        
        # Check configuration
        if enabled is None:
            enabled = os.getenv("MCP_ENABLED", "false").lower() == "true"
        
        if not enabled:
            logger.info("MCP is disabled, using no-op client")
            return NoOpMcpClient()
        
        if gateway_url is None:
            gateway_url = os.getenv("MCP_GATEWAY_URL", "http://localhost:8200")
        
        logger.info(f"MCP is enabled, using gateway at {gateway_url}")
        return HttpMcpClient(gateway_url)

# Global client instance
_mcp_client: Optional[IMcpClient] = None
_client_initialized = False

def get_mcp_client() -> IMcpClient:
    """Get the global MCP client instance"""
    global _mcp_client, _client_initialized
    
    if not _client_initialized:
        _mcp_client = McpClientFactory.create_client()
        _client_initialized = True
    
    return _mcp_client

def reset_mcp_client():
    """Reset the global MCP client (useful for testing)"""
    global _mcp_client, _client_initialized
    _mcp_client = None
    _client_initialized = False

# Convenience wrapper functions for common operations
async def mcp_call(tool: str, payload: Dict[str, Any], engagement_id: str) -> McpCallResult:
    """Convenience function for making MCP calls"""
    client = get_mcp_client()
    return await client.call(tool, payload, engagement_id)

async def mcp_fs_read(file_path: str, engagement_id: str, encoding: str = "utf-8") -> str:
    """Read file content via MCP"""
    result = await mcp_call("fs.read", {
        "path": file_path,
        "encoding": encoding
    }, engagement_id)
    
    if not result.success:
        raise McpClientError(result.error or "Read failed", result.error_code or "READ_ERROR")
    
    return result.result["content"]

async def mcp_fs_write(file_path: str, content: str, engagement_id: str, 
                       encoding: str = "utf-8", overwrite: bool = False) -> Dict[str, Any]:
    """Write file content via MCP"""
    result = await mcp_call("fs.write", {
        "path": file_path,
        "content": content,
        "encoding": encoding,
        "overwrite": overwrite
    }, engagement_id)
    
    if not result.success:
        raise McpClientError(result.error or "Write failed", result.error_code or "WRITE_ERROR")
    
    return result.result

async def mcp_pdf_parse(file_path: str, engagement_id: str, 
                        chunk_size: int = 1000, chunk_overlap: int = 100) -> Dict[str, Any]:
    """Parse PDF via MCP"""
    result = await mcp_call("pdf.parse", {
        "path": file_path,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap
    }, engagement_id)
    
    if not result.success:
        raise McpClientError(result.error or "Parse failed", result.error_code or "PARSE_ERROR")
    
    return result.result

async def mcp_search_embed(text: str, engagement_id: str, text_id: str = None,
                          metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Embed text via MCP"""
    payload = {"text": text}
    if text_id:
        payload["id"] = text_id
    if metadata:
        payload["metadata"] = metadata
    
    result = await mcp_call("search.embed", payload, engagement_id)
    
    if not result.success:
        raise McpClientError(result.error or "Embed failed", result.error_code or "EMBED_ERROR")
    
    return result.result

async def mcp_search_query(query: str, engagement_id: str, top_k: int = 10,
                          score_threshold: float = 0.0) -> List[Dict[str, Any]]:
    """Search via MCP"""
    result = await mcp_call("search.query", {
        "query": query,
        "top_k": top_k,
        "score_threshold": score_threshold
    }, engagement_id)
    
    if not result.success:
        raise McpClientError(result.error or "Search failed", result.error_code or "SEARCH_ERROR")
    
    return result.result["results"]