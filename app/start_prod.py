#!/usr/bin/env python3
"""
Minimal production startup script for Azure App Service.
Handles PORT environment variable and starts uvicorn with proper configuration.
"""
import os
import sys
import logging

# Configure logging early for startup diagnostics
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main startup function for production environment"""
    try:
        # Get port from environment (Azure App Service sets this)
        port = os.environ.get('PORT', '8000')
        
        # Validate port
        try:
            port_int = int(port)
            if port_int < 1 or port_int > 65535:
                raise ValueError("Port out of range")
        except ValueError:
            logger.warning(f"Invalid PORT value: {port}, using default 8000")
            port = "8000"
        
        logger.info(f"Starting production server on port {port}")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Working directory: {os.getcwd()}")
        
        # Import uvicorn and start server
        import uvicorn
        
        # Start uvicorn directly with production settings
        uvicorn.run(
            "api.main:app",
            host="0.0.0.0",
            port=int(port),
            log_level="info",
            access_log=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()