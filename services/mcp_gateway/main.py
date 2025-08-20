"""
MCP Gateway Service - Sprint v1.3
A lightweight FastAPI service providing Model Context Protocol (MCP) integration
for AI-Enabled Cyber Maturity Assessment platform.

This service acts as a gateway for MCP lite functionality, enabling
structured AI tool integration and context management.
"""
import os
import json
import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn


# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Environment configuration
MCP_ENABLED = os.getenv("MCP_ENABLED", "true").lower() == "true"
MCP_DATA_ROOT = os.getenv("MCP_DATA_ROOT", "/app/data")
MCP_MAX_FILE_SIZE_MB = int(os.getenv("MCP_MAX_FILE_SIZE_MB", "10"))
MCP_MAX_SEARCH_RESULTS = int(os.getenv("MCP_MAX_SEARCH_RESULTS", "20"))
MCP_GATEWAY_PORT = int(os.getenv("MCP_GATEWAY_PORT", "8200"))


# Pydantic Models
class HealthResponse(BaseModel):
    """Health check response model"""
    ok: bool = Field(..., description="Service health status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = Field(default="0.1.0", description="Service version")
    mcp_enabled: bool = Field(..., description="MCP functionality enabled status")


class MCPContextRequest(BaseModel):
    """MCP context operation request"""
    operation: str = Field(..., description="MCP operation type", regex="^[a-z_]+$")
    context: Dict[str, Any] = Field(default_factory=dict, description="Operation context data")
    correlation_id: Optional[str] = Field(None, description="Request correlation ID")


class MCPContextResponse(BaseModel):
    """MCP context operation response"""
    success: bool = Field(..., description="Operation success status")
    operation: str = Field(..., description="Executed operation type")
    result: Dict[str, Any] = Field(default_factory=dict, description="Operation results")
    correlation_id: str = Field(..., description="Request correlation ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorResponse(BaseModel):
    """Standard error response model"""
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code")
    correlation_id: str = Field(..., description="Request correlation ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Correlation ID dependency
def get_correlation_id(
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID")
) -> str:
    """Generate or extract correlation ID for request tracking"""
    return x_correlation_id or str(uuid.uuid4())


# Structured logger with correlation ID
class CorrelatedLogger:
    """Logger with automatic correlation ID injection"""
    
    def __init__(self, logger_name: str, correlation_id: str):
        self.logger = logging.getLogger(logger_name)
        self.correlation_id = correlation_id
    
    def info(self, message: str, **kwargs):
        extra = {"correlation_id": self.correlation_id, **kwargs}
        self.logger.info(message, extra=extra)
    
    def error(self, message: str, **kwargs):
        extra = {"correlation_id": self.correlation_id, **kwargs}
        self.logger.error(message, extra=extra)
    
    def warning(self, message: str, **kwargs):
        extra = {"correlation_id": self.correlation_id, **kwargs}
        self.logger.warning(message, extra=extra)


# Application lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info(
        "MCP Gateway service starting",
        extra={
            "mcp_enabled": MCP_ENABLED,
            "data_root": MCP_DATA_ROOT,
            "max_file_size_mb": MCP_MAX_FILE_SIZE_MB,
            "max_search_results": MCP_MAX_SEARCH_RESULTS
        }
    )
    
    # Startup - ensure data directory exists
    if MCP_ENABLED:
        os.makedirs(MCP_DATA_ROOT, exist_ok=True)
        logger.info(f"MCP data directory initialized: {MCP_DATA_ROOT}")
    
    yield
    
    # Shutdown
    logger.info("MCP Gateway service shutting down")


# FastAPI application
app = FastAPI(
    title="MCP Gateway Service",
    description="Model Context Protocol gateway for AI-Enabled Cyber Maturity Assessment",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with correlation ID tracking"""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    corr_logger = CorrelatedLogger("mcp_gateway.exceptions", correlation_id)
    
    corr_logger.error(
        f"Unhandled exception: {str(exc)}",
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_ERROR",
            correlation_id=correlation_id
        ).model_dump()
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns service health status and configuration"
)
async def health_check(
    correlation_id: str = Depends(get_correlation_id)
) -> HealthResponse:
    """
    Health check endpoint returning service status and configuration.
    
    Returns:
        HealthResponse: Service health status with configuration details
    """
    corr_logger = CorrelatedLogger("mcp_gateway.health", correlation_id)
    corr_logger.info("Health check requested")
    
    return HealthResponse(
        ok=True,
        mcp_enabled=MCP_ENABLED
    )


@app.get(
    "/",
    response_model=Dict[str, Any],
    summary="Service Info",
    description="Returns basic service information and capabilities"
)
async def root(
    correlation_id: str = Depends(get_correlation_id)
) -> Dict[str, Any]:
    """
    Root endpoint providing service information.
    
    Returns:
        Dict containing service info and capabilities
    """
    corr_logger = CorrelatedLogger("mcp_gateway.root", correlation_id)
    corr_logger.info("Service info requested")
    
    return {
        "service": "MCP Gateway",
        "version": "0.1.0",
        "description": "Model Context Protocol gateway for AI-Enabled Cyber Maturity Assessment",
        "mcp_enabled": MCP_ENABLED,
        "capabilities": [
            "health_monitoring",
            "context_management",
            "structured_logging"
        ],
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "mcp_context": "/mcp/context"
        }
    }


@app.post(
    "/mcp/context",
    response_model=MCPContextResponse,
    summary="MCP Context Operations",
    description="Perform MCP context operations with structured input/output"
)
async def mcp_context(
    request: MCPContextRequest,
    correlation_id: str = Depends(get_correlation_id)
) -> MCPContextResponse:
    """
    Handle MCP context operations.
    
    This endpoint provides a foundation for MCP lite functionality,
    supporting various context operations for AI tool integration.
    
    Args:
        request: MCP context operation request
        correlation_id: Request correlation ID for tracking
    
    Returns:
        MCPContextResponse: Operation results
        
    Raises:
        HTTPException: For invalid operations or MCP disabled
    """
    # Use provided correlation ID if available, otherwise use dependency
    actual_correlation_id = request.correlation_id or correlation_id
    corr_logger = CorrelatedLogger("mcp_gateway.context", actual_correlation_id)
    
    corr_logger.info(
        f"MCP context operation requested",
        operation=request.operation,
        context_keys=list(request.context.keys())
    )
    
    if not MCP_ENABLED:
        corr_logger.error("MCP context operation attempted but MCP is disabled")
        raise HTTPException(
            status_code=503,
            detail="MCP functionality is disabled"
        )
    
    # Basic operation routing (foundation for expansion)
    result = {}
    
    if request.operation == "ping":
        result = {
            "status": "pong",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        corr_logger.info("MCP ping operation completed")
    
    elif request.operation == "get_capabilities":
        result = {
            "capabilities": [
                "ping",
                "get_capabilities",
                "context_validation"
            ],
            "max_file_size_mb": MCP_MAX_FILE_SIZE_MB,
            "max_search_results": MCP_MAX_SEARCH_RESULTS
        }
        corr_logger.info("MCP capabilities requested")
    
    elif request.operation == "context_validation":
        # Validate context structure
        result = {
            "valid": True,
            "context_size": len(str(request.context)),
            "keys_count": len(request.context),
            "validation_timestamp": datetime.now(timezone.utc).isoformat()
        }
        corr_logger.info("MCP context validation completed", valid=True)
    
    else:
        corr_logger.error(f"Unknown MCP operation requested: {request.operation}")
        raise HTTPException(
            status_code=400,
            detail=f"Unknown operation: {request.operation}"
        )
    
    return MCPContextResponse(
        success=True,
        operation=request.operation,
        result=result,
        correlation_id=actual_correlation_id
    )


@app.get(
    "/mcp/status",
    response_model=Dict[str, Any],
    summary="MCP Status",
    description="Get current MCP service status and metrics"
)
async def mcp_status(
    correlation_id: str = Depends(get_correlation_id)
) -> Dict[str, Any]:
    """
    Get MCP service status and basic metrics.
    
    Returns:
        Dict containing MCP service status and metrics
    """
    corr_logger = CorrelatedLogger("mcp_gateway.status", correlation_id)
    corr_logger.info("MCP status requested")
    
    return {
        "mcp_enabled": MCP_ENABLED,
        "data_root": MCP_DATA_ROOT if MCP_ENABLED else None,
        "configuration": {
            "max_file_size_mb": MCP_MAX_FILE_SIZE_MB,
            "max_search_results": MCP_MAX_SEARCH_RESULTS
        },
        "metrics": {
            "uptime_check": "ok",
            "data_directory_exists": os.path.exists(MCP_DATA_ROOT) if MCP_ENABLED else False
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Application entry point
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=MCP_GATEWAY_PORT,
        log_level="info",
        reload=False
    )