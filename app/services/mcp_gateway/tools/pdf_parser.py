"""
MCP PDF Parser tool implementation.
Provides secure PDF text extraction using PyMuPDF (fitz).
"""
import sys
sys.path.append("/app")
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from util.logging import get_correlated_logger, log_operation

from config import MCPConfig, MCPOperationContext
from api.security import MCPSecurityValidator, redact_sensitive_content


class PDFParseRequest(BaseModel):
    """Request model for pdf.parse operation"""
    path: str = Field(..., description="PDF file path to parse")
    max_pages: Optional[int] = Field(default=None, description="Maximum number of pages to parse")
    extract_images: bool = Field(default=False, description="Extract image metadata")
    extract_links: bool = Field(default=False, description="Extract hyperlinks")


class PDFPageInfo(BaseModel):
    """Information about a PDF page"""
    page_number: int
    width: float
    height: float
    rotation: int
    text_length: int
    image_count: Optional[int] = None
    link_count: Optional[int] = None


class PDFMetadata(BaseModel):
    """PDF document metadata"""
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    keywords: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    pages: int
    encrypted: bool
    file_size_bytes: int


class PDFParseResponse(BaseModel):
    """Response model for PDF parsing operations"""
    success: bool
    path: str
    message: str
    metadata: Optional[PDFMetadata] = None
    pages: Optional[List[Dict[str, Any]]] = None
    full_text: Optional[str] = None
    page_info: Optional[List[PDFPageInfo]] = None


class MCPPDFParserTool:
    """Secure PDF parsing tool for MCP Gateway"""
    
    def __init__(self, config: MCPConfig):
        self.config = config
        self.tool_config = config.pdf_parser
    
    async def parse_pdf(self, request: PDFParseRequest, context: MCPOperationContext) -> PDFParseResponse:
        """
        Securely parse a PDF file from the engagement sandbox.
        
        Args:
            request: PDF parsing parameters
            context: Operation context with security info
            
        Returns:
            PDF content, metadata, and structure information
            
        Raises:
            SecurityError: For security violations
            FileNotFoundError: If PDF doesn't exist
            ValueError: For invalid or corrupted PDFs
        """
        logger = get_correlated_logger(f"mcp.pdf.parse", context.correlation_id)
        logger.set_context(
            engagement_id=context.engagement_id,
            user_email=context.user_email
        )
        
        # Create security validator
        validator = MCPSecurityValidator(self.config, context)
        
        with log_operation(logger, "pdf_parse_operation", file_path=request.path):
            validator.log_operation_start(operation="parse", file_path=request.path)
            
            try:
                # Validate and sanitize path
                validated_path = validator.validate_file_operation(
                    request.path, 
                    "read", 
                    self.tool_config
                )
                
                # Check file exists
                if not validated_path.exists():
                    raise FileNotFoundError(f"PDF file not found: {request.path}")
                
                # Parse PDF document
                try:
                    doc = fitz.open(validated_path)
                    
                    # Extract basic metadata
                    file_size = validated_path.stat().st_size
                    metadata = self._extract_metadata(doc, file_size)
                    
                    # Check page limit
                    max_pages = request.max_pages or doc.page_count
                    pages_to_process = min(max_pages, doc.page_count)
                    
                    if max_pages < doc.page_count:
                        logger.info(
                            "PDF page limit applied",
                            total_pages=doc.page_count,
                            pages_to_process=pages_to_process,
                            limit=max_pages
                        )
                    
                    # Extract content page by page
                    pages_content = []
                    page_info = []
                    full_text_parts = []
                    
                    for page_num in range(pages_to_process):
                        page = doc[page_num]
                        
                        # Extract text
                        text = page.get_text()
                        full_text_parts.append(text)
                        
                        # Build page content
                        page_content = {
                            "page_number": page_num + 1,
                            "text": text,
                            "char_count": len(text)
                        }
                        
                        # Extract links if requested
                        if request.extract_links:
                            links = page.get_links()
                            page_content["links"] = [
                                {
                                    "uri": link.get("uri", ""),
                                    "page": link.get("page", -1),
                                    "rect": link.get("rect", [])
                                }
                                for link in links
                                if link.get("kind") == fitz.LINK_URI or link.get("kind") == fitz.LINK_GOTO
                            ]
                        
                        # Extract images if requested
                        if request.extract_images:
                            image_list = page.get_images(full=True)
                            page_content["images"] = [
                                {
                                    "xref": img[0],
                                    "smask": img[1],
                                    "width": img[2],
                                    "height": img[3],
                                    "bpc": img[4],
                                    "colorspace": img[5],
                                    "alt": img[6],
                                    "name": img[7],
                                    "filter": img[8]
                                }
                                for img in image_list
                            ]
                        
                        pages_content.append(page_content)
                        
                        # Create page info
                        rect = page.rect
                        page_info.append(PDFPageInfo(
                            page_number=page_num + 1,
                            width=rect.width,
                            height=rect.height,
                            rotation=page.rotation,
                            text_length=len(text),
                            image_count=len(page.get_images()) if request.extract_images else None,
                            link_count=len(page.get_links()) if request.extract_links else None
                        ))
                    
                    # Combine full text
                    full_text = "\n\n".join(full_text_parts)
                    
                    # Close document
                    doc.close()
                    
                    logger.info(
                        "PDF parsing successful",
                        total_pages=doc.page_count if 'doc' in locals() else 0,
                        pages_processed=pages_to_process,
                        text_length=len(full_text),
                        file_size_bytes=file_size,
                        path_relative=str(validated_path.relative_to(self.config.get_engagement_sandbox(context.engagement_id))),
                        extract_images=request.extract_images,
                        extract_links=request.extract_links
                    )
                    
                    validator.log_operation_complete(
                        success=True,
                        operation="parse",
                        pages_processed=pages_to_process,
                        text_length=len(full_text)
                    )
                    
                    return PDFParseResponse(
                        success=True,
                        path=str(validated_path.relative_to(self.config.get_engagement_sandbox(context.engagement_id))),
                        message=f"PDF parsed successfully ({pages_to_process} pages)",
                        metadata=metadata,
                        pages=pages_content,
                        full_text=full_text,
                        page_info=page_info
                    )
                    
                except fitz.FileDataError as e:
                    error_msg = f"Invalid or corrupted PDF file: {e}"
                    logger.error(error_msg)
                    validator.log_operation_complete(success=False, error=error_msg)
                    raise ValueError(error_msg)
                    
                except fitz.FileNotFoundError as e:
                    error_msg = f"PDF file access error: {e}"
                    logger.error(error_msg)
                    validator.log_operation_complete(success=False, error=error_msg)
                    raise FileNotFoundError(error_msg)
                    
            except Exception as e:
                error_msg = f"Failed to parse PDF: {str(e)}"
                logger.error(error_msg, error_type=type(e).__name__)
                validator.log_operation_complete(success=False, error=error_msg)
                
                return PDFParseResponse(
                    success=False,
                    path=request.path,
                    message=error_msg
                )
    
    def _extract_metadata(self, doc: fitz.Document, file_size_bytes: int) -> PDFMetadata:
        """
        Extract metadata from PDF document.
        
        Args:
            doc: PyMuPDF document object
            file_size_bytes: File size in bytes
            
        Returns:
            Structured PDF metadata
        """
        metadata_dict = doc.metadata
        
        # Sanitize metadata for logging/storage
        return PDFMetadata(
            title=self._sanitize_metadata_field(metadata_dict.get("title")),
            author=self._sanitize_metadata_field(metadata_dict.get("author")),
            subject=self._sanitize_metadata_field(metadata_dict.get("subject")),
            keywords=self._sanitize_metadata_field(metadata_dict.get("keywords")),
            creator=self._sanitize_metadata_field(metadata_dict.get("creator")),
            producer=self._sanitize_metadata_field(metadata_dict.get("producer")),
            creation_date=self._sanitize_metadata_field(metadata_dict.get("creationDate")),
            modification_date=self._sanitize_metadata_field(metadata_dict.get("modDate")),
            pages=doc.page_count,
            encrypted=doc.needs_pass,
            file_size_bytes=file_size_bytes
        )
    
    def _sanitize_metadata_field(self, value: Any) -> Optional[str]:
        """
        Sanitize metadata field value.
        
        Args:
            value: Raw metadata value
            
        Returns:
            Sanitized string or None
        """
        if not value:
            return None
        
        # Convert to string and limit length
        str_value = str(value).strip()
        if len(str_value) > 1000:
            str_value = str_value[:1000] + "...[truncated]"
        
        # Apply basic content redaction for sensitive patterns
        return redact_sensitive_content(str_value, max_length=1000)