"""MCP Client interface and implementation for orchestrator service."""

import os
import json
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import requests
from datetime import datetime


logger = logging.getLogger(__name__)


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracing."""
    return f"corr_{uuid.uuid4().hex[:12]}"


class IMcpClient(ABC):
    """Abstract interface for MCP client operations."""
    
    @abstractmethod
    async def call(self, tool: str, payload: Dict[str, Any], engagement_id: str) -> Dict[str, Any]:
        """
        Call an MCP tool with the given payload.
        
        Args:
            tool: The tool name to call (e.g., 'analyze_documents', 'gap_analysis')
            payload: The request payload to send to the tool
            engagement_id: The engagement ID for tracking
            
        Returns:
            Dict containing the tool response
            
        Raises:
            Exception: If the MCP call fails
        """
        pass


class McpGatewayClient(IMcpClient):
    """HTTP client for calling MCP Gateway tools."""
    
    def __init__(self, gateway_url: str, timeout: int = 30):
        """
        Initialize the MCP Gateway client.
        
        Args:
            gateway_url: Base URL of the MCP Gateway service
            timeout: Request timeout in seconds
        """
        self.gateway_url = gateway_url.rstrip('/')
        self.timeout = timeout
        
    async def call(self, tool: str, payload: Dict[str, Any], engagement_id: str) -> Dict[str, Any]:
        """
        Call an MCP tool via the gateway.
        
        Args:
            tool: The tool name to call
            payload: The request payload
            engagement_id: The engagement ID for tracking
            
        Returns:
            Dict containing the tool response with mcp_call_id added
            
        Raises:
            Exception: If the MCP call fails
        """
        corr_id = generate_correlation_id()
        call_id = f"mcp_{uuid.uuid4().hex[:12]}"
        
        logger.info(
            "MCP call initiated",
            extra={
                "corr_id": corr_id,
                "mcp_call_id": call_id,
                "tool": tool,
                "engagement_id": engagement_id,
                "gateway_url": self.gateway_url
            }
        )
        
        try:
            # Prepare the request to MCP Gateway
            request_payload = {
                "tool": tool,
                "payload": payload,
                "engagement_id": engagement_id,
                "correlation_id": corr_id,
                "call_id": call_id
            }
            
            start_time = datetime.utcnow()
            
            # Make the HTTP call to MCP Gateway
            response = requests.post(
                f"{self.gateway_url}/tools/call",
                json=request_payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            response.raise_for_status()
            result = response.json()
            
            # Add mcp_call_id to the response for tracking
            result["mcp_call_id"] = call_id
            
            logger.info(
                "MCP call completed successfully",
                extra={
                    "corr_id": corr_id,
                    "mcp_call_id": call_id,
                    "tool": tool,
                    "engagement_id": engagement_id,
                    "duration_ms": duration_ms,
                    "status_code": response.status_code
                }
            )
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(
                "MCP call failed",
                extra={
                    "corr_id": corr_id,
                    "mcp_call_id": call_id,
                    "tool": tool,
                    "engagement_id": engagement_id,
                    "error": str(e)
                }
            )
            raise Exception(f"MCP call to {tool} failed: {str(e)}")
            
        except Exception as e:
            logger.error(
                "Unexpected error in MCP call",
                extra={
                    "corr_id": corr_id,
                    "mcp_call_id": call_id,
                    "tool": tool,
                    "engagement_id": engagement_id,
                    "error": str(e)
                }
            )
            raise


class MockMcpClient(IMcpClient):
    """Mock MCP client for testing and fallback scenarios."""
    
    async def call(self, tool: str, payload: Dict[str, Any], engagement_id: str) -> Dict[str, Any]:
        """
        Mock implementation that returns empty results.
        
        This is used when MCP is disabled or for testing purposes.
        """
        call_id = f"mock_{uuid.uuid4().hex[:12]}"
        
        logger.info(
            "Mock MCP call",
            extra={
                "mcp_call_id": call_id,
                "tool": tool,
                "engagement_id": engagement_id
            }
        )
        
        # Return minimal structure that matches expected format
        return {
            "mcp_call_id": call_id,
            "mock": True,
            "tool": tool,
            "engagement_id": engagement_id
        }


def create_mcp_client() -> IMcpClient:
    """
    Factory function to create the appropriate MCP client based on configuration.
    
    Returns:
        IMcpClient: The configured MCP client implementation
    """
    mcp_enabled = os.environ.get("MCP_ENABLED", "false").lower() == "true"
    
    if not mcp_enabled:
        logger.info("MCP disabled, using mock client")
        return MockMcpClient()
    
    gateway_url = os.environ.get("MCP_GATEWAY_URL")
    if not gateway_url:
        logger.warning("MCP enabled but MCP_GATEWAY_URL not set, using mock client")
        return MockMcpClient()
    
    timeout = int(os.environ.get("MCP_TIMEOUT", "30"))
    
    logger.info(
        "MCP enabled, creating gateway client",
        extra={
            "gateway_url": gateway_url,
            "timeout": timeout
        }
    )
    
    return McpGatewayClient(gateway_url, timeout)