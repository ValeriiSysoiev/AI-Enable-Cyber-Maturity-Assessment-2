#!/usr/bin/env python3
"""
Minimal test server to verify Azure App Service can run Python
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import json

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                'status': 'healthy',
                'timestamp': '2025-08-28T00:00:00Z'
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress logs for cleaner output
        pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', '8000'))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"Test server running on port {port}")
    server.serve_forever()