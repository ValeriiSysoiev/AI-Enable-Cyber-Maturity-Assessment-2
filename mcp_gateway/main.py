"""
MCP Gateway Service - Sprint v1.3

A FastAPI sidecar that provides Model Context Protocol (MCP) tools
scoped by engagement_id with security validation and comprehensive logging.
"""

import os
import time
import uuid
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Set
import uvicorn

from mcp_tools import McpToolRegistry, McpCallResult, McpError
from security import SecurityValidator, PathSecurityError, CrossTenantError, MimeTypeError
from vector_store import VectorStoreManager
from secret_redactor import SecretRedactor, redact_for_logs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MCP Gateway",
    description="Model Context Protocol Gateway for AI-Enabled Cyber Maturity Assessment",
    version="1.3.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
MCP_DATA_ROOT = os.getenv("MCP_DATA_ROOT", "./data")
MCP_ENABLED = os.getenv("MCP_ENABLED", "false").lower() == "true"
MAX_FILE_SIZE_MB = int(os.getenv("MCP_MAX_FILE_SIZE_MB", "10"))
MAX_REQUEST_SIZE_MB = int(os.getenv("MCP_MAX_REQUEST_SIZE_MB", "50"))
MAX_SEARCH_RESULTS = int(os.getenv("MCP_MAX_SEARCH_RESULTS", "20"))

# Global components
tool_registry = McpToolRegistry()
security_validator = SecurityValidator(
    data_root=MCP_DATA_ROOT, 
    max_file_size_mb=MAX_FILE_SIZE_MB,
    max_request_size_mb=MAX_REQUEST_SIZE_MB
)
vector_store_manager = VectorStoreManager(data_root=MCP_DATA_ROOT)
secret_redactor = SecretRedactor()

class McpCallRequest(BaseModel):
    """Request model for MCP tool calls"""
    tool: str = Field(..., description="Tool name to call")
    payload: Dict[str, Any] = Field(..., description="Tool-specific payload")
    engagement_id: str = Field(..., description="Engagement ID for scoping")
    call_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique call identifier")

    @validator('tool')
    def tool_must_be_registered(cls, v):
        # We'll validate this at runtime since registry may not be initialized yet
        if not v or len(v.strip()) == 0:
            raise ValueError("Tool name cannot be empty")
        return v.strip()

    @validator('engagement_id')
    def engagement_id_must_be_valid(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Engagement ID cannot be empty")
        # Basic validation - alphanumeric and underscores/hyphens only
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Engagement ID must contain only alphanumeric characters, hyphens, and underscores")
        return v.strip()

class McpCallResponse(BaseModel):
    """Response model for MCP tool calls"""
    call_id: str
    tool: str
    engagement_id: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    execution_time_ms: float
    timestamp: str

class McpHealthResponse(BaseModel):
    """Health check response"""
    status: str
    mcp_enabled: bool
    tools_registered: int
    data_root: str
    timestamp: str

class EngagementAllowlistRequest(BaseModel):
    """Request to update engagement tool allowlist"""
    engagement_id: str = Field(..., description="Engagement ID")
    allowed_tools: Set[str] = Field(..., description="Set of allowed tool names")
    
    @validator('engagement_id')
    def engagement_id_must_be_valid(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Engagement ID cannot be empty")
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Engagement ID must contain only alphanumeric characters, hyphens, and underscores")
        return v.strip()

class EngagementAllowlistResponse(BaseModel):
    """Response for engagement allowlist operations"""
    engagement_id: str
    allowed_tools: Set[str]
    success: bool
    message: str
    timestamp: str

def get_call_logger(call_id: str, tool: str, engagement_id: str):
    """Get a call-specific logger with context"""
    return logging.LoggerAdapter(logger, {
        'call_id': call_id,
        'tool': tool,
        'engagement_id': engagement_id
    })

def redact_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive information from logs using enhanced redactor"""
    redacted_data, _ = secret_redactor.redact_data(data, "mcp_call_payload")
    return redacted_data if isinstance(redacted_data, dict) else {"redacted": redacted_data}

@app.on_event("startup")
async def startup_event():
    """Initialize MCP Gateway on startup"""
    logger.info("Starting MCP Gateway service")
    
    # Ensure data directory exists
    data_path = Path(MCP_DATA_ROOT)
    data_path.mkdir(parents=True, exist_ok=True)
    
    # Register core tools
    from mcp_tools.fs_tools import register_fs_tools
    from mcp_tools.pdf_tools import register_pdf_tools  
    from mcp_tools.search_tools import register_search_tools
    from mcp_tools.jira_tools import register_jira_tools
    
    register_fs_tools(tool_registry, security_validator)
    register_pdf_tools(tool_registry, security_validator)
    register_search_tools(tool_registry, vector_store_manager)
    register_jira_tools(tool_registry, security_validator)
    
    logger.info(f"MCP Gateway started with {len(tool_registry.tools)} tools registered")
    logger.info(f"MCP enabled: {MCP_ENABLED}")
    logger.info(f"Data root: {MCP_DATA_ROOT}")

@app.get("/health", response_model=McpHealthResponse)
async def health_check():
    """Health check endpoint"""
    return McpHealthResponse(
        status="healthy",
        mcp_enabled=MCP_ENABLED,
        tools_registered=len(tool_registry.tools),
        data_root=MCP_DATA_ROOT,
        timestamp=datetime.utcnow().isoformat()
    )

@app.get("/mcp/tools")
async def list_tools():
    """List available MCP tools"""
    if not MCP_ENABLED:
        raise HTTPException(status_code=503, detail="MCP is disabled")
    
    return {
        "tools": [
            {
                "name": name,
                "description": tool.description,
                "schema": tool.schema
            }
            for name, tool in tool_registry.tools.items()
        ],
        "count": len(tool_registry.tools)
    }

@app.post("/mcp/call", response_model=McpCallResponse)
async def mcp_call(request: McpCallRequest, http_request: Request):
    """Execute an MCP tool call"""
    start_time = time.time()
    call_logger = get_call_logger(request.call_id, request.tool, request.engagement_id)
    
    if not MCP_ENABLED:
        raise HTTPException(status_code=503, detail="MCP is disabled")
    
    try:
        # Validate request size
        security_validator.validate_request_size(request.dict())
        
        # Validate tool access for engagement (cross-tenant protection)
        security_validator.validate_tool_access(request.tool, request.engagement_id)
        
        # Log the call initiation (with redacted payload)
        call_logger.info(
            "MCP call initiated",
            extra={
                "payload_preview": redact_sensitive_data(request.payload),
                "client_ip": http_request.client.host if http_request.client else "unknown"
            }
        )
        
        # Validate tool exists
        if request.tool not in tool_registry.tools:
            raise McpError(f"Tool '{request.tool}' not found", "TOOL_NOT_FOUND")
        
        # Execute the tool
        tool = tool_registry.tools[request.tool]
        result = await tool.execute(request.payload, request.engagement_id)
        
        execution_time_ms = (time.time() - start_time) * 1000
        
        # Validate response size
        if result.result:
            security_validator.validate_request_size(result.result)
        
        # Log successful execution (with redacted result)
        call_logger.info(
            "MCP call completed successfully",
            extra={
                "execution_time_ms": execution_time_ms,
                "result_size": len(str(result.result)) if result.result else 0,
                "result_preview": redact_for_logs(result.result, "mcp_result") if result.result else None
            }
        )
        
        return McpCallResponse(
            call_id=request.call_id,
            tool=request.tool,
            engagement_id=request.engagement_id,
            success=True,
            result=result.result,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.utcnow().isoformat()
        )
    
    except (CrossTenantError, MimeTypeError) as e:
        execution_time_ms = (time.time() - start_time) * 1000
        
        call_logger.warning(
            "MCP call failed with security error",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "execution_time_ms": execution_time_ms
            }
        )
        
        return McpCallResponse(
            call_id=request.call_id,
            tool=request.tool,
            engagement_id=request.engagement_id,
            success=False,
            error=str(e),
            error_code="SECURITY_ERROR",
            execution_time_ms=execution_time_ms,
            timestamp=datetime.utcnow().isoformat()
        )
    
    except McpError as e:
        execution_time_ms = (time.time() - start_time) * 1000
        
        call_logger.warning(
            "MCP call failed with application error",
            extra={
                "error_code": e.code,
                "error_message": str(e),
                "execution_time_ms": execution_time_ms
            }
        )
        
        return McpCallResponse(
            call_id=request.call_id,
            tool=request.tool,
            engagement_id=request.engagement_id,
            success=False,
            error=str(e),
            error_code=e.code,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.utcnow().isoformat()
        )
    
    except Exception as e:
        execution_time_ms = (time.time() - start_time) * 1000
        
        call_logger.error(
            "MCP call failed with unexpected error",
            extra={
                "error_message": str(e),
                "execution_time_ms": execution_time_ms
            },
            exc_info=True
        )
        
        return McpCallResponse(
            call_id=request.call_id,
            tool=request.tool,
            engagement_id=request.engagement_id,
            success=False,
            error="Internal server error",
            error_code="INTERNAL_ERROR",
            execution_time_ms=execution_time_ms,
            timestamp=datetime.utcnow().isoformat()
        )

@app.post("/mcp/engagement/allowlist", response_model=EngagementAllowlistResponse)
async def update_engagement_allowlist(request: EngagementAllowlistRequest):
    """Update tool allowlist for a specific engagement"""
    if not MCP_ENABLED:
        raise HTTPException(status_code=503, detail="MCP is disabled")
    
    try:
        # Validate and set the allowlist
        security_validator.set_engagement_allowlist(request.engagement_id, request.allowed_tools)
        
        logger.info(f"Updated allowlist for engagement {request.engagement_id}: {request.allowed_tools}")
        
        return EngagementAllowlistResponse(
            engagement_id=request.engagement_id,
            allowed_tools=request.allowed_tools,
            success=True,
            message=f"Allowlist updated successfully for engagement {request.engagement_id}",
            timestamp=datetime.utcnow().isoformat()
        )
    
    except ValueError as e:
        logger.warning(f"Invalid allowlist update request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update allowlist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/mcp/engagement/{engagement_id}/allowlist", response_model=EngagementAllowlistResponse)
async def get_engagement_allowlist(engagement_id: str):
    """Get tool allowlist for a specific engagement"""
    if not MCP_ENABLED:
        raise HTTPException(status_code=503, detail="MCP is disabled")
    
    try:
        # Validate engagement ID format
        if not engagement_id or not engagement_id.replace("-", "").replace("_", "").isalnum():
            raise HTTPException(status_code=400, detail="Invalid engagement ID format")
        
        allowed_tools = security_validator.get_engagement_allowlist(engagement_id)
        
        return EngagementAllowlistResponse(
            engagement_id=engagement_id,
            allowed_tools=allowed_tools,
            success=True,
            message=f"Retrieved allowlist for engagement {engagement_id}",
            timestamp=datetime.utcnow().isoformat()
        )
    
    except Exception as e:
        logger.error(f"Failed to get allowlist for engagement {engagement_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    port = int(os.getenv("MCP_GATEWAY_PORT", "8200"))
    uvicorn.run(app, host="0.0.0.0", port=port)