"""
Filesystem tools for MCP Gateway

Provides secure file read/write operations jailed to engagement directories.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from . import McpTool, McpCallResult, McpError, McpToolRegistry
from security import SecurityValidator, PathSecurityError, MimeTypeError

logger = logging.getLogger(__name__)

class FsReadTool(McpTool):
    """Tool for reading files from engagement directories"""
    
    def __init__(self, security_validator: SecurityValidator):
        super().__init__(
            name="fs.read",
            description="Read file content from engagement directory",
            schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to file within engagement directory"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding (default: utf-8)",
                        "default": "utf-8"
                    },
                    "max_size": {
                        "type": "integer",
                        "description": "Maximum file size to read in bytes",
                        "default": 1048576  # 1MB
                    }
                },
                "required": ["path"]
            }
        )
        self.security_validator = security_validator
    
    async def execute(self, payload: Dict[str, Any], engagement_id: str) -> McpCallResult:
        """Execute file read operation"""
        try:
            self.validate_payload(payload, ["path"])
            
            file_path = payload["path"]
            encoding = payload.get("encoding", "utf-8")
            max_size = payload.get("max_size", 1048576)  # 1MB default
            
            # Validate and resolve path
            safe_path = self.security_validator.validate_file_path(
                file_path, engagement_id, "read"
            )
            
            # Check file exists
            if not safe_path.exists():
                raise McpError(f"File not found: {file_path}", "FILE_NOT_FOUND")
            
            if not safe_path.is_file():
                raise McpError(f"Path is not a file: {file_path}", "NOT_A_FILE")
            
            # Validate file size
            file_size = safe_path.stat().st_size
            if file_size > max_size:
                raise McpError(
                    f"File size ({file_size}) exceeds maximum ({max_size})",
                    "FILE_TOO_LARGE"
                )
            
            # Validate MIME type for security
            try:
                mime_type = self.security_validator.validate_mime_type(safe_path, allow_unknown=True)
            except MimeTypeError as e:
                raise McpError(f"MIME type validation failed: {e}", "INVALID_MIME_TYPE")
            
            # Read file content
            try:
                content = safe_path.read_text(encoding=encoding)
            except UnicodeDecodeError as e:
                raise McpError(f"Failed to decode file with {encoding}: {e}", "ENCODING_ERROR")
            except Exception as e:
                raise McpError(f"Failed to read file: {e}", "READ_ERROR")
            
            self.logger.info(
                f"File read successfully: {file_path} ({file_size} bytes)",
                extra={"engagement_id": engagement_id, "file_size": file_size}
            )
            
            return McpCallResult(
                success=True,
                result={
                    "content": content,
                    "size": file_size,
                    "encoding": encoding,
                    "path": file_path,
                    "mime_type": mime_type
                }
            )
            
        except PathSecurityError as e:
            raise McpError(f"Security validation failed: {e}", "SECURITY_ERROR")
        except McpError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in fs.read: {e}", exc_info=True)
            raise McpError(f"Internal error: {e}", "INTERNAL_ERROR")

class FsWriteTool(McpTool):
    """Tool for writing files to engagement directories"""
    
    def __init__(self, security_validator: SecurityValidator):
        super().__init__(
            name="fs.write",
            description="Write content to file in engagement directory",
            schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to file within engagement directory"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to file"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding (default: utf-8)",
                        "default": "utf-8"
                    },
                    "create_dirs": {
                        "type": "boolean",
                        "description": "Create parent directories if they don't exist",
                        "default": True
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "Allow overwriting existing files",
                        "default": False
                    }
                },
                "required": ["path", "content"]
            }
        )
        self.security_validator = security_validator
    
    async def execute(self, payload: Dict[str, Any], engagement_id: str) -> McpCallResult:
        """Execute file write operation"""
        try:
            self.validate_payload(payload, ["path", "content"])
            
            file_path = payload["path"]
            content = payload["content"]
            encoding = payload.get("encoding", "utf-8")
            create_dirs = payload.get("create_dirs", True)
            overwrite = payload.get("overwrite", False)
            
            # Validate and resolve path
            safe_path = self.security_validator.validate_file_path(
                file_path, engagement_id, "write"
            )
            
            # Check if file exists and overwrite policy
            if safe_path.exists() and not overwrite:
                raise McpError(f"File exists and overwrite=False: {file_path}", "FILE_EXISTS")
            
            # Create parent directories if needed
            if create_dirs:
                try:
                    safe_path.parent.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    raise McpError(f"Failed to create directories: {e}", "MKDIR_ERROR")
            elif not safe_path.parent.exists():
                raise McpError(f"Parent directory does not exist: {safe_path.parent}", "PARENT_NOT_FOUND")
            
            # Use secure file write with MIME validation and permission setting
            try:
                self.security_validator.secure_file_write(safe_path, content, engagement_id)
            except MimeTypeError as e:
                raise McpError(f"MIME type validation failed: {e}", "INVALID_MIME_TYPE")
            except Exception as e:
                raise McpError(f"Failed to write file securely: {e}", "WRITE_ERROR")
            
            # Get final file size
            file_size = safe_path.stat().st_size
            
            self.logger.info(
                f"File written successfully: {file_path} ({file_size} bytes)",
                extra={"engagement_id": engagement_id, "file_size": file_size}
            )
            
            return McpCallResult(
                success=True,
                result={
                    "path": file_path,
                    "size": file_size,
                    "encoding": encoding,
                    "created": not payload.get("overwrite", False)
                }
            )
            
        except PathSecurityError as e:
            raise McpError(f"Security validation failed: {e}", "SECURITY_ERROR")
        except McpError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in fs.write: {e}", exc_info=True)
            raise McpError(f"Internal error: {e}", "INTERNAL_ERROR")

class FsListTool(McpTool):
    """Tool for listing files in engagement directories"""
    
    def __init__(self, security_validator: SecurityValidator):
        super().__init__(
            name="fs.list",
            description="List files and directories in engagement directory",
            schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path within engagement directory (default: root)",
                        "default": "."
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "List files recursively",
                        "default": False
                    },
                    "include_hidden": {
                        "type": "boolean",
                        "description": "Include hidden files (starting with .)",
                        "default": False
                    }
                },
                "required": []
            }
        )
        self.security_validator = security_validator
    
    async def execute(self, payload: Dict[str, Any], engagement_id: str) -> McpCallResult:
        """Execute file listing operation"""
        try:
            dir_path = payload.get("path", ".")
            recursive = payload.get("recursive", False)
            include_hidden = payload.get("include_hidden", False)
            
            # Validate and resolve path
            safe_path = self.security_validator.validate_file_path(
                dir_path, engagement_id, "list"
            )
            
            # Ensure it's a directory (or create engagement dir if it doesn't exist)
            if not safe_path.exists():
                if dir_path == ".":
                    # Create engagement directory if listing root
                    self.security_validator.ensure_directory_exists(safe_path)
                else:
                    raise McpError(f"Directory not found: {dir_path}", "DIRECTORY_NOT_FOUND")
            elif not safe_path.is_dir():
                raise McpError(f"Path is not a directory: {dir_path}", "NOT_A_DIRECTORY")
            
            # List files
            files = []
            directories = []
            
            try:
                if recursive:
                    for item in safe_path.rglob("*"):
                        if not include_hidden and item.name.startswith('.'):
                            continue
                        
                        relative_path = item.relative_to(safe_path)
                        if item.is_file():
                            files.append({
                                "name": item.name,
                                "path": str(relative_path),
                                "size": item.stat().st_size,
                                "modified": item.stat().st_mtime
                            })
                        elif item.is_dir():
                            directories.append({
                                "name": item.name,
                                "path": str(relative_path)
                            })
                else:
                    for item in safe_path.iterdir():
                        if not include_hidden and item.name.startswith('.'):
                            continue
                        
                        if item.is_file():
                            files.append({
                                "name": item.name,
                                "path": item.name,
                                "size": item.stat().st_size,
                                "modified": item.stat().st_mtime
                            })
                        elif item.is_dir():
                            directories.append({
                                "name": item.name,
                                "path": item.name
                            })
            except Exception as e:
                raise McpError(f"Failed to list directory: {e}", "LIST_ERROR")
            
            self.logger.info(
                f"Directory listed: {dir_path} ({len(files)} files, {len(directories)} dirs)",
                extra={"engagement_id": engagement_id}
            )
            
            return McpCallResult(
                success=True,
                result={
                    "path": dir_path,
                    "files": files,
                    "directories": directories,
                    "total_files": len(files),
                    "total_directories": len(directories)
                }
            )
            
        except PathSecurityError as e:
            raise McpError(f"Security validation failed: {e}", "SECURITY_ERROR")
        except McpError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in fs.list: {e}", exc_info=True)
            raise McpError(f"Internal error: {e}", "INTERNAL_ERROR")

def register_fs_tools(registry: McpToolRegistry, security_validator: SecurityValidator):
    """Register filesystem tools with the registry"""
    registry.register(FsReadTool(security_validator))
    registry.register(FsWriteTool(security_validator))
    registry.register(FsListTool(security_validator))
    
    logger.info("Filesystem tools registered")