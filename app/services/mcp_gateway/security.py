"""
Security utilities for MCP Gateway operations.
Provides path validation, content redaction, and sanitization.
"""
import sys
sys.path.append("/app")
import re
import fnmatch
from pathlib import Path, PurePath
from typing import Dict, Any, Optional, List, Set, Union
from util.logging import get_correlated_logger, log_security_event

from services.mcp_gateway.config import MCPConfig, MCPOperationContext


class SecurityError(Exception):
    """Base exception for security violations"""
    pass


class PathTraversalError(SecurityError):
    """Exception for path traversal attempts"""
    pass


class FileTypeError(SecurityError):
    """Exception for disallowed file types"""
    pass


class FileSizeError(SecurityError):
    """Exception for oversized files"""
    pass


def sanitize_path(path: Union[str, Path], sandbox: Path) -> Path:
    """
    Sanitize and validate a path within the given sandbox.
    
    Args:
        path: User-provided path (can be relative or absolute)
        sandbox: Sandbox directory to jail the path within
        
    Returns:
        Validated absolute path within sandbox
        
    Raises:
        PathTraversalError: If path attempts to escape sandbox
    """
    if isinstance(path, str):
        path = Path(path)
    
    # Convert to absolute path relative to sandbox
    if not path.is_absolute():
        resolved_path = (sandbox / path).resolve()
    else:
        resolved_path = path.resolve()
    
    # Ensure resolved path is within sandbox
    try:
        resolved_path.relative_to(sandbox.resolve())
    except ValueError:
        raise PathTraversalError(f"Path escape attempt: {path} -> {resolved_path}")
    
    return resolved_path


def validate_file_type(file_path: Path, allowed_extensions: Set[str]) -> None:
    """
    Validate file type against allowed extensions.
    
    Args:
        file_path: Path to validate
        allowed_extensions: Set of allowed file extensions (e.g., {'.txt', '.pdf'})
        
    Raises:
        FileTypeError: If file type is not allowed
    """
    if file_path.suffix.lower() not in {ext.lower() for ext in allowed_extensions}:
        raise FileTypeError(f"File type {file_path.suffix} not allowed")


def validate_file_size(file_path: Path, max_size_mb: int) -> None:
    """
    Validate file size against maximum allowed size.
    
    Args:
        file_path: Path to file to check
        max_size_mb: Maximum file size in MB
        
    Raises:
        FileSizeError: If file exceeds size limit
    """
    if file_path.exists():
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            raise FileSizeError(f"File size {size_mb:.1f}MB exceeds limit of {max_size_mb}MB")


def check_blocked_patterns(file_path: Path, blocked_patterns: List[str]) -> None:
    """
    Check if file matches any blocked patterns.
    
    Args:
        file_path: Path to check
        blocked_patterns: List of glob patterns to block
        
    Raises:
        SecurityError: If file matches blocked pattern
    """
    filename = file_path.name.lower()
    for pattern in blocked_patterns:
        if fnmatch.fnmatch(filename, pattern.lower()):
            raise SecurityError(f"File matches blocked pattern: {pattern}")


def redact_sensitive_content(content: str, max_length: int = 1000) -> str:
    """
    Redact potentially sensitive content from text for logging.
    
    Args:
        content: Text content to redact
        max_length: Maximum length to include in logs
        
    Returns:
        Redacted content safe for logging
    """
    if not content:
        return "<empty>"
    
    # Truncate if too long
    if len(content) > max_length:
        content = content[:max_length] + "...[truncated]"
    
    # Redact common sensitive patterns
    patterns = [
        # Email addresses
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]'),
        # Phone numbers
        (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]'),
        # Credit card numbers (basic pattern)
        (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD_REDACTED]'),
        # SSN patterns
        (r'\b\d{3}[-]?\d{2}[-]?\d{4}\b', '[SSN_REDACTED]'),
        # API keys (common patterns)
        (r'\b[A-Za-z0-9]{20,}\b', '[API_KEY_REDACTED]'),
        # IP addresses
        (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_REDACTED]')
    ]
    
    redacted_content = content
    for pattern, replacement in patterns:
        redacted_content = re.sub(pattern, replacement, redacted_content)
    
    return redacted_content


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    # Remove path separators and dangerous characters
    sanitized = re.sub(r'[<>:"|?*\\/]', '_', filename)
    
    # Remove leading dots and spaces
    sanitized = sanitized.lstrip('. ')
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = Path(sanitized).stem, Path(sanitized).suffix
        sanitized = name[:200] + ext
    
    # Ensure not empty
    if not sanitized:
        sanitized = "unnamed_file"
    
    return sanitized


class SecurityPolicy:
    """Security policy configuration for MCP tools"""
    
    def __init__(self, max_file_size_mb: int = 10, allowed_extensions: Optional[Set[str]] = None):
        self.max_file_size_mb = max_file_size_mb
        self.allowed_extensions = allowed_extensions or {".txt", ".md", ".json", ".csv", ".pdf"}
        self.enable_redaction = True
        self.enable_path_jailing = True
    
    def validate_file_size(self, size_bytes: int) -> bool:
        """Check if file size is within limits"""
        size_mb = size_bytes / (1024 * 1024)
        return size_mb <= self.max_file_size_mb
    
    def validate_extension(self, filepath: str) -> bool:
        """Check if file extension is allowed"""
        path = Path(filepath)
        return path.suffix.lower() in self.allowed_extensions


class MCPSecurityValidator:
    """Security validator for MCP operations"""
    
    def __init__(self, config: MCPConfig, context: MCPOperationContext):
        self.config = config
        self.context = context
        self.logger = get_correlated_logger(f"mcp.security.{context.tool_name}", context.correlation_id)
        self.logger.set_context(
            engagement_id=context.engagement_id,
            user_email=context.user_email,
            tool_name=context.tool_name,
            operation=context.operation
        )
    
    def validate_file_operation(
        self,
        file_path: Union[str, Path],
        operation: str,
        tool_config: Any,
        content_size_bytes: Optional[int] = None
    ) -> Path:
        """
        Comprehensive validation for file operations.
        
        Args:
            file_path: Path to validate
            operation: Operation type ('read', 'write', etc.)
            tool_config: Tool-specific configuration
            content_size_bytes: Size of content for write operations
            
        Returns:
            Validated and sanitized path
            
        Raises:
            SecurityError: For any security violation
        """
        # Get engagement sandbox
        sandbox = self.config.get_engagement_sandbox(self.context.engagement_id)
        
        try:
            # Sanitize and validate path
            validated_path = sanitize_path(file_path, sandbox)
            
            # Validate file type
            validate_file_type(validated_path, tool_config.allowed_extensions)
            
            # Check blocked patterns
            if self.config.security.blocked_patterns:
                check_blocked_patterns(validated_path, self.config.security.blocked_patterns)
            
            # For read operations, validate existing file size
            if operation == 'read' and validated_path.exists():
                validate_file_size(validated_path, tool_config.max_file_size_mb)
            
            # For write operations, validate content size
            if operation == 'write' and content_size_bytes:
                size_mb = content_size_bytes / (1024 * 1024)
                if size_mb > tool_config.max_file_size_mb:
                    raise FileSizeError(f"Content size {size_mb:.1f}MB exceeds limit")
            
            # Log successful validation
            log_security_event(
                self.logger,
                event_type="file_validation_success",
                user_email=self.context.user_email,
                engagement_id=self.context.engagement_id,
                success=True,
                operation=operation,
                file_path=str(validated_path.relative_to(sandbox)),
                tool_name=self.context.tool_name
            )
            
            return validated_path
            
        except SecurityError as e:
            # Log security violation
            log_security_event(
                self.logger,
                event_type="file_validation_failure",
                user_email=self.context.user_email,
                engagement_id=self.context.engagement_id,
                success=False,
                operation=operation,
                file_path=str(file_path),
                tool_name=self.context.tool_name,
                error=str(e),
                violation_type=type(e).__name__
            )
            raise
    
    def log_operation_start(self, **details):
        """Log the start of an MCP operation"""
        log_security_event(
            self.logger,
            event_type="mcp_operation_start",
            user_email=self.context.user_email,
            engagement_id=self.context.engagement_id,
            success=True,
            tool_name=self.context.tool_name,
            operation=self.context.operation,
            **details
        )
    
    def log_operation_complete(self, success: bool, **details):
        """Log the completion of an MCP operation"""
        log_security_event(
            self.logger,
            event_type="mcp_operation_complete",
            user_email=self.context.user_email,
            engagement_id=self.context.engagement_id,
            success=success,
            tool_name=self.context.tool_name,
            operation=self.context.operation,
            **details
        )