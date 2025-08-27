#!/usr/bin/env python3
"""
Simple startup script for Azure App Service
Handles PORT environment variable properly
"""
import os
import sys
import subprocess

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
    
    # Start uvicorn with proper arguments
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "api.main:app", 
        "--host", "0.0.0.0", 
        "--port", port
    ]
    
    # Execute uvicorn
    os.execvp(sys.executable, cmd)

if __name__ == "__main__":
    main()

