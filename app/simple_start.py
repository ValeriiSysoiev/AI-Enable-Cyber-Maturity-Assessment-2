#!/usr/bin/env python3
"""
Simple startup script for Azure App Service
Handles PORT environment variable properly with enhanced debugging
"""
import os
import sys
import subprocess
import traceback

def main():
    # Get port from environment, default to 8000
    port = os.environ.get('PORT', '8000')
    
    # Validate port is numeric
    try:
        port_int = int(port)
        if port_int < 1 or port_int > 65535:
            raise ValueError("Port out of range")
    except ValueError:
        print(f"Invalid PORT value: {port}, using default 8000")
        port = "8000"
    
    print(f"Starting uvicorn on port {port}...")
    print(f"Python version: {sys.version}")
    print(f"Python path: {sys.path}")
    
    # Test if we can import the main app
    print("Testing API import...")
    try:
        from api.main import app
        print("✓ Successfully imported api.main:app")
        
        # Check available routes
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        print(f"✓ Found {len(routes)} routes: {routes[:10]}...")
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        print("Attempting to start anyway...")
    except Exception as e:
        print(f"✗ Unexpected error during import test: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        print("Attempting to start anyway...")
    
    # Start uvicorn with proper arguments
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "api.main:app", 
        "--host", "0.0.0.0", 
        "--port", port,
        "--log-level", "info"  # Add verbose logging
    ]
    
    print(f"Executing: {' '.join(cmd)}")
    
    # Execute uvicorn
    os.execvp(sys.executable, cmd)

if __name__ == "__main__":
    main()
