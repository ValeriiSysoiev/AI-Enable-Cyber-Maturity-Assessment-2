#!/usr/bin/env python3
"""
Simplified startup script for Azure App Service
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main startup function"""
    try:
        # Get port from environment
        port = os.environ.get('PORT', '8000')
        host = '0.0.0.0'
        
        logger.info(f"Starting API server on {host}:{port}")
        
        # Import and run uvicorn programmatically
        import uvicorn
        uvicorn.run(
            "api.main:app",
            host=host,
            port=int(port),
            log_level="info",
            access_log=True
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()