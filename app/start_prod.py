#!/usr/bin/env python3
"""
Production startup script for Azure App Service
Handles all edge cases and ensures proper module loading
"""
import os
import sys
import logging
import subprocess
from pathlib import Path

# Configure logging immediately
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check and log environment configuration"""
    logger.info("=" * 60)
    logger.info("ENVIRONMENT CHECK")
    logger.info("=" * 60)
    
    # Python version
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python executable: {sys.executable}")
    
    # Working directory
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Script location: {__file__}")
    
    # Python path
    logger.info(f"Python path: {sys.path}")
    
    # Environment variables
    important_vars = [
        'PORT', 'WEBSITE_INSTANCE_ID', 'WEBSITE_SITE_NAME',
        'AUTH_MODE', 'DATA_BACKEND', 'ENVIRONMENT',
        'AZURE_AD_TENANT_ID', 'COSMOS_DB_ENDPOINT'
    ]
    
    for var in important_vars:
        value = os.environ.get(var)
        if value and 'SECRET' not in var and 'KEY' not in var:
            logger.info(f"{var}: {value[:50]}..." if len(str(value)) > 50 else f"{var}: {value}")
        elif value:
            logger.info(f"{var}: [CONFIGURED]")
        else:
            logger.warning(f"{var}: [NOT SET]")
    
    logger.info("=" * 60)

def ensure_dependencies():
    """Ensure all required dependencies are installed"""
    logger.info("Checking dependencies...")
    
    try:
        import fastapi
        logger.info(f"FastAPI version: {fastapi.__version__}")
    except ImportError as e:
        logger.error(f"FastAPI not installed: {e}")
        return False
    
    try:
        import uvicorn
        logger.info(f"Uvicorn installed")
    except ImportError as e:
        logger.error(f"Uvicorn not installed: {e}")
        return False
    
    try:
        import azure.storage.blob
        logger.info("Azure Storage Blob installed")
    except ImportError as e:
        logger.error(f"Azure Storage not installed: {e}")
        # Try to install it
        logger.info("Attempting to install azure-storage-blob...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "azure-storage-blob"])
    
    try:
        import azure.cosmos
        logger.info("Azure Cosmos DB installed")
    except ImportError as e:
        logger.warning(f"Azure Cosmos DB not installed: {e}")
        # Not critical if using different backend
    
    return True

def start_server():
    """Start the server using the best available method"""
    port = os.environ.get('PORT', '8000')
    
    # Validate port
    try:
        port_int = int(port)
        if port_int < 1 or port_int > 65535:
            raise ValueError(f"Port {port_int} out of valid range")
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid PORT value: {port}, error: {e}")
        port = '8000'
    
    logger.info(f"Starting server on port {port}...")
    
    # Check if gunicorn is available and we're in production
    use_gunicorn = os.environ.get('ENVIRONMENT') == 'production'
    
    if use_gunicorn:
        try:
            import gunicorn
            logger.info("Using Gunicorn for production...")
            
            # Use gunicorn with configuration
            config_file = Path(__file__).parent / "gunicorn_config.py"
            if config_file.exists():
                cmd = [
                    sys.executable, "-m", "gunicorn",
                    "api.main:app",
                    "-c", str(config_file)
                ]
            else:
                cmd = [
                    sys.executable, "-m", "gunicorn",
                    "api.main:app",
                    "-w", "2",
                    "-k", "uvicorn.workers.UvicornWorker",
                    "--bind", f"0.0.0.0:{port}",
                    "--timeout", "120",
                    "--access-logfile", "-",
                    "--error-logfile", "-"
                ]
        except ImportError:
            logger.warning("Gunicorn not available, falling back to uvicorn...")
            use_gunicorn = False
    
    if not use_gunicorn:
        # Use uvicorn directly
        logger.info("Using Uvicorn...")
        cmd = [
            sys.executable, "-m", "uvicorn",
            "api.main:app",
            "--host", "0.0.0.0",
            "--port", port,
            "--log-level", os.environ.get('LOG_LEVEL', 'info').lower()
        ]
    
    logger.info(f"Executing command: {' '.join(cmd)}")
    
    # Execute the command
    try:
        os.execvp(cmd[0], cmd)
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)

def main():
    """Main entry point"""
    try:
        logger.info("Starting Cyber Maturity API...")
        
        # Check environment
        check_environment()
        
        # Ensure we're in the right directory
        app_dir = Path(__file__).parent
        if app_dir != Path.cwd():
            logger.info(f"Changing directory to {app_dir}")
            os.chdir(app_dir)
        
        # Ensure dependencies
        if not ensure_dependencies():
            logger.error("Dependency check failed!")
            sys.exit(1)
        
        # Start the server
        start_server()
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()