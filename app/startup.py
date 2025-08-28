#!/usr/bin/env python3
"""Ultra-minimal startup script with no external dependencies."""

import json
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests."""
        if self.path in ['/api/health', '/health', '/']:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "server": "minimal-api",
                "port": os.environ.get('PORT', '8000')
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Override to reduce logging."""
        return

if __name__ == "__main__":
    port = int(os.environ.get('PORT', '8000'))
    print(f"Starting minimal server on port {port}...")
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"Server running at http://0.0.0.0:{port}")
    server.serve_forever()
