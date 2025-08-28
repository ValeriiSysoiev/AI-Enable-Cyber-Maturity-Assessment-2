#!/usr/bin/env python3
"""
Minimal FastAPI app for health checks in Azure App Service
Works with basic Python without heavy dependencies
"""
import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Only use standard library for basic HTTP server
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path in ['/api/health', '/health']:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat() + 'Z',
                "message": "Azure App Service API is running",
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "working_directory": os.getcwd()
            }
            
            self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))
            
        elif parsed_path.path in ['/api/features', '/features']:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "s4_enabled": True,
                "features": {
                    "csf": True,
                    "workshops": True,
                    "minutes": True,
                    "chat": True,
                    "service_bus": False
                },
                "environment": "production_minimal",
                "mode": "basic_health_check"
            }
            
            self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))
            
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            error_response = {
                "error": "Not found",
                "path": parsed_path.path,
                "available_endpoints": ["/api/health", "/health", "/api/features", "/features"]
            }
            
            self.wfile.write(json.dumps(error_response, indent=2).encode('utf-8'))

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def log_message(self, format, *args):
        """Custom logging to avoid timestamp duplication"""
        sys.stderr.write(f"[{datetime.utcnow().isoformat()}Z] {format % args}\n")

def main():
    """Start the minimal health check server"""
    port = int(os.environ.get('PORT', '8000'))
    
    print(f"Starting minimal health check server on port {port}")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Available endpoints:")
    print(f"  - GET /api/health")
    print(f"  - GET /health") 
    print(f"  - GET /api/features")
    print(f"  - GET /features")
    
    try:
        server = ThreadingHTTPServer(('0.0.0.0', port), HealthHandler)
        print(f"Server listening on http://0.0.0.0:{port}")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()