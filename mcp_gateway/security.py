"""
Security validation for MCP Gateway

Implements path validation, size limits, engagement isolation, mime type validation,
and other security measures to prevent directory traversal and other security issues.
"""

import os
import re
import mimetypes
from pathlib import Path
from typing import Union, Optional, Set, Dict, Any
import logging

logger = logging.getLogger(__name__)

class PathSecurityError(Exception):
    """Raised when a path security validation fails"""
    pass

class CrossTenantError(Exception):
    """Raised when cross-tenant access is attempted"""
    pass

class MimeTypeError(Exception):
    """Raised when disallowed mime type is detected"""
    pass

class SecurityValidator:
    """Security validator for MCP operations"""
    
    def __init__(self, data_root: str, max_file_size_mb: int = 10, max_request_size_mb: int = 50):
        self.data_root = Path(data_root).resolve()
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.max_request_size_bytes = max_request_size_mb * 1024 * 1024
        
        # Allowed MIME types for file operations
        self.allowed_mime_types = {
            'text/plain',
            'text/csv',
            'text/markdown',
            'text/html',
            'application/json',
            'application/xml',
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'image/png',
            'image/jpeg',
            'image/gif',
            'image/webp'
        }
        
        # Engagement-specific tool allowlists
        self.engagement_allowlists: Dict[str, Set[str]] = {}
        
        # Default tools available to all engagements
        self.default_allowed_tools = {
            'fs.read',
            'fs.write', 
            'fs.list',
            'search.vector',
            'search.semantic'
        }
        
        # Ensure data root exists
        self.data_root.mkdir(parents=True, exist_ok=True)
        
        # Dangerous patterns to reject
        self.dangerous_patterns = [
            r'\.\./',          # Parent directory traversal
            r'\.\.\.',         # Multiple dots
            r'~/',             # Home directory
            r'/etc/',          # System directory
            r'/proc/',         # Process directory
            r'/sys/',          # System directory
            r'\\',             # Windows path separators (in Unix context)
            r'\$\{.*\}',       # Variable expansion
            r'`.*`',           # Command substitution
        ]
        
        # Compile patterns for efficiency
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.dangerous_patterns]
        
        logger.info(f"SecurityValidator initialized with data_root: {self.data_root}")
    
    def validate_tool_access(self, tool_name: str, engagement_id: str) -> None:
        """Validate that an engagement can access a specific tool"""
        if not tool_name or not engagement_id:
            raise CrossTenantError("Tool name and engagement ID are required")
        
        # Get engagement-specific allowlist, fallback to default
        allowed_tools = self.engagement_allowlists.get(engagement_id, self.default_allowed_tools)
        
        if tool_name not in allowed_tools:
            raise CrossTenantError(f"Tool '{tool_name}' not allowed for engagement '{engagement_id}'")
        
        logger.debug(f"Tool access validated: {tool_name} for engagement {engagement_id}")
    
    def set_engagement_allowlist(self, engagement_id: str, allowed_tools: Set[str]) -> None:
        """Set the tool allowlist for a specific engagement"""
        if not engagement_id:
            raise ValueError("Engagement ID cannot be empty")
        
        # Validate all tools are in our default set (for security)
        invalid_tools = allowed_tools - self.default_allowed_tools
        if invalid_tools:
            raise ValueError(f"Invalid tools not in default allowlist: {invalid_tools}")
        
        self.engagement_allowlists[engagement_id] = allowed_tools.copy()
        logger.info(f"Updated allowlist for engagement {engagement_id}: {allowed_tools}")
    
    def get_engagement_allowlist(self, engagement_id: str) -> Set[str]:
        """Get the tool allowlist for a specific engagement"""
        return self.engagement_allowlists.get(engagement_id, self.default_allowed_tools.copy())
    
    def validate_mime_type(self, file_path: Path, allow_unknown: bool = False) -> str:
        """Validate file MIME type against allowlist"""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        if mime_type is None:
            if allow_unknown:
                # Treat unknown as text/plain for now
                mime_type = 'text/plain'
            else:
                raise MimeTypeError(f"Cannot determine MIME type for: {file_path}")
        
        if mime_type not in self.allowed_mime_types:
            raise MimeTypeError(f"MIME type '{mime_type}' not allowed for file: {file_path}")
        
        logger.debug(f"MIME type validated: {mime_type} for {file_path}")
        return mime_type
    
    def validate_request_size(self, data: Union[str, bytes, Dict[str, Any]]) -> None:
        """Validate request/response size against limits"""
        if isinstance(data, str):
            size = len(data.encode('utf-8'))
        elif isinstance(data, bytes):
            size = len(data)
        elif isinstance(data, dict):
            # Estimate size for dict objects
            import json
            size = len(json.dumps(data, default=str).encode('utf-8'))
        else:
            # For other types, convert to string and measure
            size = len(str(data).encode('utf-8'))
        
        if size > self.max_request_size_bytes:
            raise PathSecurityError(
                f"Request/response size ({size} bytes) exceeds limit ({self.max_request_size_bytes} bytes)"
            )
    
    def get_safe_engagement_path(self, engagement_id: str) -> Path:
        """Get the safe path for an engagement's data directory"""
        # Validate engagement_id format
        if not engagement_id or not isinstance(engagement_id, str):
            raise PathSecurityError("Invalid engagement_id: must be a non-empty string")
        
        # Sanitize engagement_id
        clean_engagement_id = self._sanitize_path_component(engagement_id)
        if not clean_engagement_id:
            raise PathSecurityError("Invalid engagement_id: contains only invalid characters")
        
        # Create engagement-specific path
        engagement_path = self.data_root / clean_engagement_id
        
        # Ensure the path is within data_root
        try:
            engagement_path = engagement_path.resolve()
        except (OSError, ValueError) as e:
            raise PathSecurityError(f"Path resolution failed: {e}")
        
        if not self._is_within_data_root(engagement_path):
            raise PathSecurityError("Engagement path outside of allowed data root")
        
        return engagement_path
    
    def validate_file_path(self, file_path: str, engagement_id: str, operation: str = "read") -> Path:
        """
        Validate and resolve a file path within an engagement's directory
        
        Args:
            file_path: The file path to validate
            engagement_id: The engagement ID for scoping
            operation: The operation type (read/write) for logging
            
        Returns:
            Resolved safe path
            
        Raises:
            PathSecurityError: If path validation fails
        """
        if not file_path or not isinstance(file_path, str):
            raise PathSecurityError("Invalid file_path: must be a non-empty string")
        
        # Check for dangerous patterns
        for pattern in self.compiled_patterns:
            if pattern.search(file_path):
                raise PathSecurityError(f"Dangerous pattern detected in path: {file_path}")
        
        # Get engagement base path
        engagement_path = self.get_safe_engagement_path(engagement_id)
        
        # Sanitize file path components
        path_parts = [self._sanitize_path_component(part) for part in file_path.split('/')]
        path_parts = [part for part in path_parts if part]  # Remove empty parts
        
        if not path_parts:
            raise PathSecurityError("Invalid file_path: no valid path components")
        
        # Build safe path
        try:
            safe_path = engagement_path
            for part in path_parts:
                safe_path = safe_path / part
            safe_path = safe_path.resolve()
        except (OSError, ValueError) as e:
            raise PathSecurityError(f"Path construction failed: {e}")
        
        # Ensure path is within engagement directory
        if not self._is_within_path(safe_path, engagement_path):
            raise PathSecurityError("File path outside of engagement directory")
        
        # Check if it's a symlink (security risk)
        if safe_path.is_symlink():
            raise PathSecurityError("Symlinks are not allowed")
        
        logger.debug(f"Path validated for {operation}: {safe_path}")
        return safe_path
    
    def validate_file_size(self, file_path: Path, operation: str = "read") -> None:
        """Validate file size against limits"""
        if not file_path.exists():
            if operation == "read":
                raise PathSecurityError(f"File does not exist: {file_path}")
            return  # For write operations, file may not exist yet
        
        if file_path.is_file():
            size = file_path.stat().st_size
            if size > self.max_file_size_bytes:
                raise PathSecurityError(
                    f"File size ({size} bytes) exceeds limit ({self.max_file_size_bytes} bytes)"
                )
    
    def validate_content_size(self, content: Union[str, bytes]) -> None:
        """Validate content size against limits"""
        if isinstance(content, str):
            size = len(content.encode('utf-8'))
        else:
            size = len(content)
        
        if size > self.max_file_size_bytes:
            raise PathSecurityError(
                f"Content size ({size} bytes) exceeds limit ({self.max_file_size_bytes} bytes)"
            )
    
    def _sanitize_path_component(self, component: str) -> str:
        """Sanitize a single path component"""
        if not component:
            return ""
        
        # Remove dangerous characters and normalize
        # Allow alphanumeric, hyphens, underscores, and dots (but not .. or ...)
        sanitized = re.sub(r'[^a-zA-Z0-9._-]', '', component.strip())
        
        # Reject if it's just dots or empty
        if not sanitized or sanitized in ['.', '..', '...']:
            return ""
        
        # Reject if it starts/ends with dots (hidden files and potential traversal)
        if sanitized.startswith('.') or sanitized.endswith('.'):
            # Allow single dot in the middle (for extensions)
            if '.' in sanitized[1:-1]:
                pass  # Has extension, might be OK
            else:
                return ""
        
        return sanitized
    
    def _is_within_data_root(self, path: Path) -> bool:
        """Check if path is within the data root directory"""
        return self._is_within_path(path, self.data_root)
    
    def _is_within_path(self, path: Path, base_path: Path) -> bool:
        """Check if path is within base_path"""
        try:
            path.resolve().relative_to(base_path.resolve())
            return True
        except ValueError:
            return False
    
    def ensure_directory_exists(self, dir_path: Path) -> None:
        """Safely create directory if it doesn't exist"""
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Directory ensured: {dir_path}")
        except (OSError, ValueError) as e:
            raise PathSecurityError(f"Failed to create directory {dir_path}: {e}")
    
    def secure_file_write(self, file_path: Path, content: Union[str, bytes], engagement_id: str) -> None:
        """Securely write file with proper permissions and validation"""
        # Validate MIME type before writing
        self.validate_mime_type(file_path, allow_unknown=True)
        
        # Validate content size
        self.validate_content_size(content)
        
        # Write the file
        if isinstance(content, str):
            file_path.write_text(content, encoding='utf-8')
        else:
            file_path.write_bytes(content)
        
        # Set secure permissions (no execute, owner read/write only)
        # 0o644 = rw-r--r-- (owner: read/write, group/others: read-only)
        file_path.chmod(0o644)
        
        logger.info(f"File written securely: {file_path} for engagement {engagement_id}")
    
    def prevent_cross_tenant_access(self, requesting_engagement: str, target_engagement: str) -> None:
        """Prevent cross-tenant access between engagements"""
        if requesting_engagement != target_engagement:
            raise CrossTenantError(
                f"Cross-tenant access denied: {requesting_engagement} cannot access {target_engagement}"
            )
    
    def get_mcp_index_path(self, engagement_id: str) -> Path:
        """Get the safe path for MCP vector index data"""
        engagement_path = self.get_safe_engagement_path(engagement_id)
        mcp_index_path = engagement_path / "mcp_index"
        
        # Ensure it's still within our safe boundaries
        if not self._is_within_path(mcp_index_path, self.data_root):
            raise PathSecurityError("MCP index path outside of data root")
        
        return mcp_index_path