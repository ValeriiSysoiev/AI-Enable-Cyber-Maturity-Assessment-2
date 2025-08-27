"""
MCP Gateway main router.
Provides REST API endpoints for MCP tools with comprehensive security and logging.
"""
import sys
sys.path.append("/app")
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any
from util.logging import get_correlated_logger
from api.security import current_context, require_member
from domain.repository import Repository

from api.config import MCPConfig, MCPOperationContext, get_mcp_config
from .tools.filesystem import MCPFilesystemTool, FSReadRequest, FSWriteRequest, FSResponse
from .tools.pdf_parser import MCPPDFParserTool, PDFParseRequest, PDFParseResponse
from .tools.search import MCPSearchTool, SearchEmbedRequest, SearchQueryRequest, SearchEmbedResponse, SearchQueryResponse
from api.security import SecurityError


# Create router
router = APIRouter(prefix="/api/mcp", tags=["MCP Gateway"])


def get_repository() -> Repository:
    """Get repository dependency"""
    from api.main import app
    return app.state.repo


def create_operation_context(
    request: Request,
    ctx: Dict[str, Any],
    tool_name: str,
    operation: str
) -> MCPOperationContext:
    """Create MCP operation context from request"""
    return MCPOperationContext(
        correlation_id=request.headers.get("X-Correlation-ID", "unknown"),
        user_email=ctx["user_email"],
        engagement_id=ctx["engagement_id"],
        tool_name=tool_name,
        operation=operation,
        tenant_id=ctx.get("tenant_id")
    )


# Filesystem Tools Endpoints

@router.post("/fs/read", response_model=FSResponse)
async def fs_read(
    request_body: FSReadRequest,
    request: Request,
    ctx: Dict[str, Any] = Depends(current_context),
    repo: Repository = Depends(get_repository),
    config: MCPConfig = Depends(get_mcp_config)
):
    """
    Read a file from the engagement sandbox.
    
    Provides secure file reading with:
    - Path jailing within engagement sandbox
    - File type validation
    - Size limits
    - Content redaction in logs
    """
    # Check engagement membership
    require_member(repo, ctx, min_role="member")
    
    # Validate tool allowlist
    if not config.validate_allowlist(ctx["engagement_id"], "filesystem"):
        raise HTTPException(403, "Filesystem tool not allowed for this engagement")
    
    # Create operation context
    operation_ctx = create_operation_context(request, ctx, "filesystem", "read")
    
    # Initialize tool
    fs_tool = MCPFilesystemTool(config)
    
    try:
        result = await fs_tool.read_file(request_body, operation_ctx)
        return result
    except SecurityError as e:
        raise HTTPException(403, f"Security violation: {str(e)}")
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Internal error: {str(e)}")


@router.post("/fs/write", response_model=FSResponse)
async def fs_write(
    request_body: FSWriteRequest,
    request: Request,
    ctx: Dict[str, Any] = Depends(current_context),
    repo: Repository = Depends(get_repository),
    config: MCPConfig = Depends(get_mcp_config)
):
    """
    Write a file to the engagement sandbox.
    
    Provides secure file writing with:
    - Path jailing within engagement sandbox
    - File type validation
    - Size limits
    - Filename sanitization
    """
    # Check engagement membership
    require_member(repo, ctx, min_role="member")
    
    # Validate tool allowlist
    if not config.validate_allowlist(ctx["engagement_id"], "filesystem"):
        raise HTTPException(403, "Filesystem tool not allowed for this engagement")
    
    # Create operation context
    operation_ctx = create_operation_context(request, ctx, "filesystem", "write")
    
    # Initialize tool
    fs_tool = MCPFilesystemTool(config)
    
    try:
        result = await fs_tool.write_file(request_body, operation_ctx)
        return result
    except SecurityError as e:
        raise HTTPException(403, f"Security violation: {str(e)}")
    except PermissionError as e:
        raise HTTPException(403, f"Permission denied: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Internal error: {str(e)}")


# PDF Parser Tools Endpoints

@router.post("/pdf/parse", response_model=PDFParseResponse)
async def pdf_parse(
    request_body: PDFParseRequest,
    request: Request,
    ctx: Dict[str, Any] = Depends(current_context),
    repo: Repository = Depends(get_repository),
    config: MCPConfig = Depends(get_mcp_config)
):
    """
    Parse a PDF file from the engagement sandbox.
    
    Provides secure PDF parsing with:
    - Path jailing within engagement sandbox
    - File type validation (PDF only)
    - Size limits (up to 50MB)
    - Content extraction and metadata
    """
    # Check engagement membership
    require_member(repo, ctx, min_role="member")
    
    # Validate tool allowlist
    if not config.validate_allowlist(ctx["engagement_id"], "pdf_parser"):
        raise HTTPException(403, "PDF parser tool not allowed for this engagement")
    
    # Create operation context
    operation_ctx = create_operation_context(request, ctx, "pdf_parser", "parse")
    
    # Initialize tool
    pdf_tool = MCPPDFParserTool(config)
    
    try:
        result = await pdf_tool.parse_pdf(request_body, operation_ctx)
        return result
    except SecurityError as e:
        raise HTTPException(403, f"Security violation: {str(e)}")
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Internal error: {str(e)}")


# Search Tools Endpoints

@router.post("/search/embed", response_model=SearchEmbedResponse)
async def search_embed(
    request_body: SearchEmbedRequest,
    request: Request,
    ctx: Dict[str, Any] = Depends(current_context),
    repo: Repository = Depends(get_repository),
    config: MCPConfig = Depends(get_mcp_config)
):
    """
    Generate embeddings for text content.
    
    Provides text embedding with:
    - Rate limiting per engagement
    - Content redaction in logs
    - Model caching
    - Secure embedding storage
    """
    # Check engagement membership
    require_member(repo, ctx, min_role="member")
    
    # Validate tool allowlist
    if not config.validate_allowlist(ctx["engagement_id"], "search"):
        raise HTTPException(403, "Search tool not allowed for this engagement")
    
    # Create operation context
    operation_ctx = create_operation_context(request, ctx, "search", "embed")
    
    # Initialize tool
    search_tool = MCPSearchTool(config)
    
    try:
        result = await search_tool.embed_texts(request_body, operation_ctx)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Internal error: {str(e)}")


@router.post("/search/query", response_model=SearchQueryResponse)
async def search_query(
    request_body: SearchQueryRequest,
    request: Request,
    ctx: Dict[str, Any] = Depends(current_context),
    repo: Repository = Depends(get_repository),
    config: MCPConfig = Depends(get_mcp_config)
):
    """
    Query embeddings using vector similarity search.
    
    Provides vector search with:
    - Similarity threshold filtering
    - Ranking by relevance score
    - Secure embedding access
    - Query result logging
    """
    # Check engagement membership
    require_member(repo, ctx, min_role="member")
    
    # Validate tool allowlist
    if not config.validate_allowlist(ctx["engagement_id"], "search"):
        raise HTTPException(403, "Search tool not allowed for this engagement")
    
    # Create operation context
    operation_ctx = create_operation_context(request, ctx, "search", "query")
    
    # Initialize tool
    search_tool = MCPSearchTool(config)
    
    try:
        result = await search_tool.query_embeddings(request_body, operation_ctx)
        return result
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Internal error: {str(e)}")


# Health and Status Endpoints

@router.get("/health")
async def mcp_health():
    """MCP Gateway health check endpoint"""
    try:
        config = get_mcp_config()
        
        return {
            "status": "healthy",
            "service": "mcp_gateway",
            "tools_available": ["filesystem", "pdf_parser", "search"],
            "config": {
                "base_data_path": str(config.base_data_path),
                "security_enabled": config.security.enable_path_jailing,
                "content_redaction": config.security.enable_content_redaction
            }
        }
    except Exception as e:
        raise HTTPException(500, f"Health check failed: {str(e)}")


@router.get("/tools")
async def list_tools():
    """List available MCP tools and their configurations"""
    config = get_mcp_config()
    
    return {
        "tools": {
            "filesystem": {
                "enabled": config.filesystem.enabled,
                "max_file_size_mb": config.filesystem.max_file_size_mb,
                "allowed_extensions": list(config.filesystem.allowed_extensions),
                "operations": ["read", "write"]
            },
            "pdf_parser": {
                "enabled": config.pdf_parser.enabled,
                "max_file_size_mb": config.pdf_parser.max_file_size_mb,
                "allowed_extensions": list(config.pdf_parser.allowed_extensions),
                "operations": ["parse"]
            },
            "search": {
                "enabled": config.search.enabled,
                "rate_limit_per_minute": config.search.rate_limit_per_minute,
                "operations": ["embed", "query"],
                "default_model": "all-MiniLM-L6-v2"
            }
        },
        "security": {
            "path_jailing_enabled": config.security.enable_path_jailing,
            "content_redaction_enabled": config.security.enable_content_redaction,
            "max_path_depth": config.security.max_path_depth,
            "blocked_patterns_count": len(config.security.blocked_patterns)
        }
    }