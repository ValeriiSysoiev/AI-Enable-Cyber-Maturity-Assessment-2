"""
PDF parsing tools for MCP Gateway

Provides PDF text extraction with page/offset metadata and chunking support.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import re

from . import McpTool, McpCallResult, McpError, McpToolRegistry
from security import SecurityValidator, PathSecurityError

logger = logging.getLogger(__name__)

class PdfParseChunk:
    """Represents a chunk of text from a PDF with source metadata"""
    
    def __init__(self, text: str, page_number: int, chunk_index: int, 
                 start_offset: int, end_offset: int):
        self.text = text
        self.page_number = page_number
        self.chunk_index = chunk_index
        self.start_offset = start_offset
        self.end_offset = end_offset
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "length": len(self.text)
        }

class PdfParseTool(McpTool):
    """Tool for parsing PDF files and extracting text with metadata"""
    
    def __init__(self, security_validator: SecurityValidator):
        super().__init__(
            name="pdf.parse",
            description="Parse PDF file and extract text with page/offset metadata",
            schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to PDF file within engagement directory"
                    },
                    "chunk_size": {
                        "type": "integer",
                        "description": "Maximum size of text chunks in characters",
                        "default": 1000,
                        "minimum": 100,
                        "maximum": 5000
                    },
                    "chunk_overlap": {
                        "type": "integer", 
                        "description": "Number of characters to overlap between chunks",
                        "default": 100,
                        "minimum": 0,
                        "maximum": 500
                    },
                    "pages": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Specific page numbers to parse (1-indexed). If not provided, all pages are parsed"
                    },
                    "include_metadata": {
                        "type": "boolean",
                        "description": "Include PDF metadata in response",
                        "default": True
                    }
                },
                "required": ["path"]
            }
        )
        self.security_validator = security_validator
    
    async def execute(self, payload: Dict[str, Any], engagement_id: str) -> McpCallResult:
        """Execute PDF parsing operation"""
        try:
            self.validate_payload(payload, ["path"])
            
            file_path = payload["path"]
            chunk_size = payload.get("chunk_size", 1000)
            chunk_overlap = payload.get("chunk_overlap", 100)
            specific_pages = payload.get("pages")
            include_metadata = payload.get("include_metadata", True)
            
            # Validate parameters
            if chunk_overlap >= chunk_size:
                raise McpError("chunk_overlap must be less than chunk_size", "INVALID_PARAMETERS")
            
            # Validate and resolve path
            safe_path = self.security_validator.validate_file_path(
                file_path, engagement_id, "read"
            )
            
            # Check file exists and is PDF
            if not safe_path.exists():
                raise McpError(f"File not found: {file_path}", "FILE_NOT_FOUND")
            
            if not safe_path.is_file():
                raise McpError(f"Path is not a file: {file_path}", "NOT_A_FILE")
            
            if safe_path.suffix.lower() != '.pdf':
                raise McpError(f"File is not a PDF: {file_path}", "NOT_A_PDF")
            
            # Validate file size
            self.security_validator.validate_file_size(safe_path, "read")
            
            # Parse PDF
            try:
                parse_result = await self._parse_pdf(
                    safe_path, chunk_size, chunk_overlap, specific_pages, include_metadata
                )
            except Exception as e:
                self.logger.error(f"PDF parsing failed for {file_path}: {e}", exc_info=True)
                raise McpError(f"Failed to parse PDF: {e}", "PARSE_ERROR")
            
            self.logger.info(
                f"PDF parsed successfully: {file_path} ({parse_result['total_pages']} pages, {len(parse_result['chunks'])} chunks)",
                extra={"engagement_id": engagement_id}
            )
            
            return McpCallResult(
                success=True,
                result=parse_result
            )
            
        except PathSecurityError as e:
            raise McpError(f"Security validation failed: {e}", "SECURITY_ERROR")
        except McpError:
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in pdf.parse: {e}", exc_info=True)
            raise McpError(f"Internal error: {e}", "INTERNAL_ERROR")
    
    async def _parse_pdf(self, pdf_path: Path, chunk_size: int, chunk_overlap: int,
                        specific_pages: Optional[List[int]], include_metadata: bool) -> Dict[str, Any]:
        """Parse PDF and extract text with chunking"""
        
        # Try to import PDF library
        try:
            from pypdf import PdfReader
        except ImportError:
            raise McpError("PyPDF library not available", "DEPENDENCY_ERROR")
        
        # Open and read PDF
        try:
            reader = PdfReader(str(pdf_path))
        except Exception as e:
            raise McpError(f"Failed to open PDF: {e}", "PDF_READ_ERROR")
        
        total_pages = len(reader.pages)
        
        # Determine which pages to process
        if specific_pages:
            # Validate page numbers (convert from 1-indexed to 0-indexed)
            pages_to_process = []
            for page_num in specific_pages:
                if page_num < 1 or page_num > total_pages:
                    raise McpError(f"Invalid page number: {page_num} (PDF has {total_pages} pages)", "INVALID_PAGE")
                pages_to_process.append(page_num - 1)  # Convert to 0-indexed
        else:
            pages_to_process = list(range(total_pages))
        
        # Extract text from pages
        pages_text = []
        for page_idx in pages_to_process:
            try:
                page = reader.pages[page_idx]
                text = page.extract_text() or ""
                pages_text.append({
                    "page_number": page_idx + 1,  # 1-indexed for user
                    "text": text,
                    "length": len(text)
                })
            except Exception as e:
                self.logger.warning(f"Failed to extract text from page {page_idx + 1}: {e}")
                pages_text.append({
                    "page_number": page_idx + 1,
                    "text": "",
                    "length": 0
                })
        
        # Create chunks with metadata
        chunks = []
        chunk_index = 0
        
        for page_data in pages_text:
            if not page_data["text"]:
                continue
                
            page_chunks = self._create_chunks(
                page_data["text"], 
                page_data["page_number"],
                chunk_size,
                chunk_overlap,
                chunk_index
            )
            chunks.extend(page_chunks)
            chunk_index += len(page_chunks)
        
        # Collect PDF metadata if requested
        pdf_metadata = {}
        if include_metadata:
            try:
                info = reader.metadata
                if info:
                    pdf_metadata = {
                        "title": info.get("/Title", ""),
                        "author": info.get("/Author", ""),
                        "subject": info.get("/Subject", ""),
                        "creator": info.get("/Creator", ""),
                        "producer": info.get("/Producer", ""),
                        "creation_date": str(info.get("/CreationDate", "")),
                        "modification_date": str(info.get("/ModDate", ""))
                    }
            except Exception as e:
                self.logger.warning(f"Failed to extract PDF metadata: {e}")
        
        return {
            "path": str(pdf_path.name),
            "total_pages": total_pages,
            "pages_processed": len(pages_to_process),
            "pages": pages_text,
            "chunks": [chunk.to_dict() for chunk in chunks],
            "total_chunks": len(chunks),
            "metadata": pdf_metadata
        }
    
    def _create_chunks(self, text: str, page_number: int, chunk_size: int, 
                      chunk_overlap: int, starting_chunk_index: int) -> List[PdfParseChunk]:
        """Create overlapping text chunks from page text"""
        if not text:
            return []
        
        chunks = []
        chunk_index = starting_chunk_index
        start = 0
        
        while start < len(text):
            # Calculate end position
            end = start + chunk_size
            
            # If this would be the last chunk and it's very small, extend to include all remaining text
            if end >= len(text):
                end = len(text)
            else:
                # Try to break at word boundary near the chunk end
                # Look backwards from end position to find a good break point
                break_point = end
                for i in range(end, max(start + chunk_size // 2, start + 1), -1):
                    if text[i - 1] in ' \n\t.!?;':
                        break_point = i
                        break
                end = break_point
            
            # Extract chunk text
            chunk_text = text[start:end].strip()
            
            if chunk_text:  # Only create chunk if it has content
                chunk = PdfParseChunk(
                    text=chunk_text,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    start_offset=start,
                    end_offset=end
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # Calculate next start position with overlap
            start = end - chunk_overlap
            
            # Ensure we make progress
            if start <= chunks[-1].start_offset if chunks else True:
                start = end
        
        return chunks

def register_pdf_tools(registry: McpToolRegistry, security_validator: SecurityValidator):
    """Register PDF tools with the registry"""
    registry.register(PdfParseTool(security_validator))
    
    logger.info("PDF tools registered")