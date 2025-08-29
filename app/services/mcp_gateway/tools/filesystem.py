"""
MCP Filesystem tools implementation.
Provides secure fs.read and fs.write operations with path jailing.
"""
import sys
sys.path.append("/app")
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from util.logging import get_correlated_logger, log_operation

from services.mcp_gateway.config import MCPConfig, MCPOperationContext
from services.mcp_gateway.security import MCPSecurityValidator, redact_sensitive_content, sanitize_filename


class FSReadRequest(BaseModel):
    """Request model for fs.read operation"""
    path: str = Field(..., description="File path to read")
    encoding: str = Field(default="utf-8", description="Text encoding")
    max_size_mb: Optional[int] = Field(default=None, description="Override max file size")


class FSWriteRequest(BaseModel):
    """Request model for fs.write operation"""
    path: str = Field(..., description="File path to write")
    content: str = Field(..., description="Content to write")
    encoding: str = Field(default="utf-8", description="Text encoding")
    create_dirs: bool = Field(default=True, description="Create parent directories if needed")


class FSResponse(BaseModel):
    """Response model for filesystem operations"""
    success: bool
    path: str
    message: str
    size_bytes: Optional[int] = None
    content: Optional[str] = None


class MCPFilesystemTool:
    """Secure filesystem operations tool for MCP Gateway"""
    
    def __init__(self, config: MCPConfig):
        self.config = config
        self.tool_config = config.filesystem
    
    async def read_file(self, request: FSReadRequest, context: MCPOperationContext) -> FSResponse:
        """
        Securely read a file from the engagement sandbox.
        
        Args:
            request: File read parameters
            context: Operation context with security info
            
        Returns:
            File content and metadata
            
        Raises:
            SecurityError: For security violations
            FileNotFoundError: If file doesn't exist
            PermissionError: For access issues
        """
        logger = get_correlated_logger(f"mcp.filesystem.read", context.correlation_id)
        logger.set_context(
            engagement_id=context.engagement_id,
            user_email=context.user_email
        )
        
        # Create security validator
        validator = MCPSecurityValidator(self.config, context)
        
        with log_operation(logger, "fs_read_operation", file_path=request.path):
            validator.log_operation_start(operation="read", file_path=request.path)
            
            try:
                # Validate and sanitize path
                max_size = request.max_size_mb or self.tool_config.max_file_size_mb
                tool_config_override = type(self.tool_config)(
                    **self.tool_config.dict(),
                    max_file_size_mb=max_size
                )
                
                validated_path = validator.validate_file_operation(
                    request.path, 
                    "read", 
                    tool_config_override
                )
                
                # Check file exists
                if not validated_path.exists():
                    raise FileNotFoundError(f"File not found: {request.path}")
                
                # Read file content
                try:
                    content = validated_path.read_text(encoding=request.encoding)
                    size_bytes = len(content.encode(request.encoding))
                    
                    logger.info(
                        "File read successful",
                        file_size_bytes=size_bytes,
                        encoding=request.encoding,
                        path_relative=str(validated_path.relative_to(self.config.get_engagement_sandbox(context.engagement_id)))
                    )
                    
                    validator.log_operation_complete(
                        success=True,
                        operation="read",
                        file_size_bytes=size_bytes
                    )
                    
                    return FSResponse(
                        success=True,
                        path=str(validated_path.relative_to(self.config.get_engagement_sandbox(context.engagement_id))),
                        message="File read successfully",
                        size_bytes=size_bytes,
                        content=content
                    )
                    
                except UnicodeDecodeError as e:
                    error_msg = f"Encoding error reading file: {e}"
                    logger.error(error_msg, encoding=request.encoding)
                    validator.log_operation_complete(success=False, error=error_msg)
                    raise ValueError(error_msg)
                    
            except Exception as e:
                error_msg = f"Failed to read file: {str(e)}"
                logger.error(error_msg, error_type=type(e).__name__)
                validator.log_operation_complete(success=False, error=error_msg)
                
                return FSResponse(
                    success=False,
                    path=request.path,
                    message=error_msg
                )
    
    async def write_file(self, request: FSWriteRequest, context: MCPOperationContext) -> FSResponse:
        """
        Securely write a file to the engagement sandbox.
        
        Args:
            request: File write parameters
            context: Operation context with security info
            
        Returns:
            Write operation result
            
        Raises:
            SecurityError: For security violations
            PermissionError: For access issues
        """
        logger = get_correlated_logger(f"mcp.filesystem.write", context.correlation_id)
        logger.set_context(
            engagement_id=context.engagement_id,
            user_email=context.user_email
        )
        
        # Create security validator
        validator = MCPSecurityValidator(self.config, context)
        
        with log_operation(
            logger, 
            "fs_write_operation", 
            file_path=request.path,
            content_preview=redact_sensitive_content(request.content, max_length=200)
        ):
            validator.log_operation_start(
                operation="write", 
                file_path=request.path,
                content_size_bytes=len(request.content.encode(request.encoding))
            )
            
            try:
                # Sanitize filename
                path = Path(request.path)
                if path.name != sanitize_filename(path.name):
                    sanitized_path = path.parent / sanitize_filename(path.name)
                    logger.warning(
                        "Filename sanitized",
                        original=request.path,
                        sanitized=str(sanitized_path)
                    )
                    path = sanitized_path
                
                # Validate and sanitize path
                content_size_bytes = len(request.content.encode(request.encoding))
                validated_path = validator.validate_file_operation(
                    str(path),
                    "write", 
                    self.tool_config,
                    content_size_bytes=content_size_bytes
                )
                
                # Create parent directories if needed
                if request.create_dirs:
                    validated_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write file content
                try:
                    validated_path.write_text(request.content, encoding=request.encoding)
                    
                    # Verify write was successful
                    actual_size = validated_path.stat().st_size
                    
                    logger.info(
                        "File write successful",
                        file_size_bytes=actual_size,
                        encoding=request.encoding,
                        path_relative=str(validated_path.relative_to(self.config.get_engagement_sandbox(context.engagement_id))),
                        created_dirs=request.create_dirs
                    )
                    
                    validator.log_operation_complete(
                        success=True,
                        operation="write",
                        file_size_bytes=actual_size
                    )
                    
                    return FSResponse(
                        success=True,
                        path=str(validated_path.relative_to(self.config.get_engagement_sandbox(context.engagement_id))),
                        message="File written successfully",
                        size_bytes=actual_size
                    )
                    
                except PermissionError as e:
                    error_msg = f"Permission denied writing file: {e}"
                    logger.error(error_msg)
                    validator.log_operation_complete(success=False, error=error_msg)
                    raise
                    
            except Exception as e:
                error_msg = f"Failed to write file: {str(e)}"
                logger.error(error_msg, error_type=type(e).__name__)
                validator.log_operation_complete(success=False, error=error_msg)
                
                return FSResponse(
                    success=False,
                    path=request.path,
                    message=error_msg
                )