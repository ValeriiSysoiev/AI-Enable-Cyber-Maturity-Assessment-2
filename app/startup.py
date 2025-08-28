#!/usr/bin/env python3
"""Ultra-minimal startup script with no external dependencies for Azure App Service."""

import json
import os
import sys
import traceback
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests."""
        try:
            if self.path in ['/api/health', '/health', '/', '/ready', '/status']:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                
                response = {
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "server": "azure-app-service-minimal",
                    "port": os.environ.get('PORT', '8000'),
                    "python_version": sys.version.split()[0],
                    "path_requested": self.path,
                    "deployment_type": "app-service"
                }
                self.wfile.write(json.dumps(response, indent=2).encode())
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {
                    "error": "Not Found",
                    "path": self.path,
                    "available_endpoints": ["/api/health", "/health", "/"]
                }
                self.wfile.write(json.dumps(error_response).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {
                "error": "Internal Server Error",
                "details": str(e),
                "traceback": traceback.format_exc()
            }
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_HEAD(self):
        """Handle HEAD requests for health checks."""
        if self.path in ['/api/health', '/health', '/']:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Log to stdout for Azure App Service logs."""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {format % args}")

def main():
    """Main function to start the server."""
    try:
        # Get port from environment - Azure App Service sets this
        port_str = os.environ.get('PORT', os.environ.get('WEBSITES_PORT', '8000'))
        port = int(port_str)
        
        # Validate port range
        if port < 1 or port > 65535:
            print(f"Invalid port {port}, using default 8000")
            port = 8000
            
        print(f"Python version: {sys.version}")
        print(f"Starting minimal health server on port {port}...")
        print(f"Available endpoints: /api/health, /health, /")
        print(f"Environment PORT: {os.environ.get('PORT', 'not set')}")
        print(f"Environment WEBSITES_PORT: {os.environ.get('WEBSITES_PORT', 'not set')}")
        
        server = HTTPServer(('0.0.0.0', port), Handler)
        print(f"Server successfully started at http://0.0.0.0:{port}")
        print("Waiting for requests...")
        server.serve_forever()
        
    except Exception as e:
        print(f"FATAL ERROR starting server: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()
