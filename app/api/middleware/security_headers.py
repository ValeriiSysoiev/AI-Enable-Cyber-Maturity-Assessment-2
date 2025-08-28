"""
Security Headers Middleware

Adds comprehensive security headers to all HTTP responses to protect against
common web vulnerabilities and improve security posture.
"""

import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from config import config

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all responses
    
    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Content-Security-Policy: Restrictive policy for API
    - Strict-Transport-Security: HSTS for HTTPS
    - Permissions-Policy: Restrictive permissions
    """
    
    def __init__(self, app, enable_hsts: bool = True, enable_csp: bool = True):
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.enable_csp = enable_csp
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # X-Content-Type-Options: Prevents MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-Frame-Options: Prevents clickjacking (API shouldn't be framed)
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-XSS-Protection: Enable XSS filtering (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy: Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy: Restrict browser features
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), magnetometer=(), "
            "accelerometer=(), gyroscope=(), "
            "clipboard-read=(), clipboard-write=()"
        )
        
        # Content Security Policy for API
        if self.enable_csp:
            # Restrictive CSP for API endpoints - no scripts, styles, or objects allowed
            csp_directives = [
                "default-src 'none'",           # Block all by default
                "connect-src 'self'",           # Only allow connections to same origin
                "frame-ancestors 'none'",       # No framing allowed
                "base-uri 'self'",             # Restrict base URI
                "form-action 'none'",          # No forms
                "object-src 'none'",           # No objects/embeds
                "script-src 'none'",           # No scripts
                "style-src 'none'",            # No styles
                "img-src 'none'",              # No images
                "media-src 'none'",            # No media
                "font-src 'none'"              # No fonts
            ]
            
            # For API documentation endpoints, allow some content
            if request.url.path in ['/docs', '/redoc', '/openapi.json']:
                csp_directives = [
                    "default-src 'self'",
                    "script-src 'self' 'unsafe-inline'",  # Swagger UI needs inline scripts
                    "style-src 'self' 'unsafe-inline'",   # Swagger UI needs inline styles
                    "img-src 'self' data:",               # Allow data URIs for icons
                    "font-src 'self'",
                    "connect-src 'self'"
                ]
            
            response.headers["Content-Security-Policy"] = "; ".join(csp_directives)
        
        # HSTS (HTTP Strict Transport Security) - only add if HTTPS
        if self.enable_hsts and request.url.scheme == "https":
            # 1 year, include subdomains, preload
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        # Server identification (security by obscurity - optional)
        # Remove or modify server headers to avoid fingerprinting
        if "server" in response.headers:
            response.headers["server"] = "WebServer/1.0"
        
        return response


def create_security_headers_middleware(
    enable_hsts: bool = None, 
    enable_csp: bool = None
) -> SecurityHeadersMiddleware:
    """
    Create security headers middleware with configuration
    
    Args:
        enable_hsts: Enable HSTS header (default from config)
        enable_csp: Enable Content Security Policy (default from config)
    
    Returns:
        Configured SecurityHeadersMiddleware instance
    """
    if enable_hsts is None:
        enable_hsts = getattr(config, 'security', {}).get('enable_hsts', True)
    
    if enable_csp is None:
        enable_csp = getattr(config, 'security', {}).get('enable_csp', True)
    
    return SecurityHeadersMiddleware(
        app=None,  # Will be set by FastAPI
        enable_hsts=enable_hsts,
        enable_csp=enable_csp
    )