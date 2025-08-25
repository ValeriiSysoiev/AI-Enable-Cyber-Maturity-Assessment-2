import os
import io
from typing import Tuple, Optional
from pydantic import BaseModel

class ExtractResult(BaseModel):
    text: str
    page_count: Optional[int] = None
    note: Optional[str] = None

def safe_join(*parts: str) -> str:
    """Safely join path parts preventing directory traversal attacks"""
    if not parts:
        raise ValueError("At least one path part is required")
    
    base = parts[0]
    # Resolve base to absolute path
    abs_base = os.path.abspath(base)
    
    # Join all parts
    joined_path = os.path.join(*parts)
    # Resolve the final path to absolute (resolving symlinks for security)
    abs_joined = os.path.abspath(os.path.realpath(joined_path))
    
    # Verify the resulting path is within the base directory
    try:
        # Get the common path between base and result
        common = os.path.commonpath([abs_base, abs_joined])
        # If common path is not the base directory or a parent of it, it's a traversal attempt
        if not (abs_joined.startswith(abs_base + os.sep) or abs_joined == abs_base):
            raise ValueError(f"Path traversal detected: resulting path '{abs_joined}' is outside base directory '{abs_base}'")
    except ValueError as e:
        if "Path traversal detected" in str(e):
            raise
        # os.path.commonpath can raise ValueError for paths on different drives (Windows)
        raise ValueError(f"Invalid path operation: {e}")
    
    return abs_joined

def extract_text(path: str, content_type: Optional[str], max_chars: int = 20000) -> ExtractResult:
    # simple heuristics by extension; avoid heavy deps
    ext = os.path.splitext(path)[1].lower()
    text = ""
    pages = None
    note = None
    try:
        if ext == ".pdf":
            try:
                from pypdf import PdfReader
            except Exception as e:
                return ExtractResult(text="", page_count=None, note=f"PDF parser missing: {e}")
            r = PdfReader(path)
            pages = len(r.pages)
            for i, pg in enumerate(r.pages):
                text += (pg.extract_text() or "") + "\n"
                if len(text) >= max_chars:
                    note = "Truncated"
                    break
        elif ext in (".docx",):
            try:
                import docx
            except Exception as e:
                return ExtractResult(text="", page_count=None, note=f"DOCX parser missing: {e}")
            d = docx.Document(path)
            text = "\n".join(p.text for p in d.paragraphs if p.text)
            if len(text) > max_chars:
                text = text[:max_chars]
                note = "Truncated"
        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read(max_chars)
                if f.read(1):
                    note = "Truncated"
    except Exception as e:
        return ExtractResult(text="", page_count=None, note=f"Extract error: {e}")
    return ExtractResult(text=text, page_count=pages, note=note)
