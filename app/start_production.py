#!/usr/bin/env python3
"""
Production startup script for Azure App Service.

This script provides a robust startup mechanism that:
1. Attempts to start the full FastAPI application
2. Falls back to minimal health check server if dependencies are missing
3. Handles CI mode and graceful dependency failures
4. Provides comprehensive logging and error handling
"""
import os
import sys
import logging
import traceback
from datetime import datetime, timezone
from typing import Optional

# Configure early logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("startup")


def get_port() -> int:
    """Get port from environment with validation."""
    port_str = os.environ.get('PORT', '8000')
    try:
        port = int(port_str)
        if port < 1 or port > 65535:
            raise ValueError("Port out of range")
        return port
    except ValueError:
        logger.warning(f"Invalid PORT value: {port_str}, using default 8000")
        return 8000


def check_critical_dependencies() -> tuple[bool, list[str]]:
    """Check if critical dependencies are available."""
    missing_deps = []
    
    # Check for FastAPI
    try:
        import fastapi
        logger.info(f"FastAPI available: {fastapi.__version__}")
    except ImportError as e:
        missing_deps.append(f"fastapi: {str(e)}")
    
    # Check for uvicorn
    try:
        import uvicorn
        logger.info(f"Uvicorn available: {uvicorn.__version__}")
    except ImportError as e:
        missing_deps.append(f"uvicorn: {str(e)}")
    
    # Check for SQLModel (database)
    try:
        import sqlmodel
        logger.info(f"SQLModel available: {sqlmodel.__version__}")
    except ImportError as e:
        missing_deps.append(f"sqlmodel: {str(e)}")
    
    return len(missing_deps) == 0, missing_deps


def test_app_import() -> tuple[bool, Optional[str]]:
    """Test if the FastAPI app can be imported."""
    try:
        # Add current directory to path
        if "/app" not in sys.path:
            sys.path.insert(0, "/app")
        
        # Test import
        from api.main import app
        logger.info("FastAPI app imported successfully")
        return True, None
    except Exception as e:
        error_msg = f"Failed to import FastAPI app: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return False, error_msg


def start_full_app(port: int) -> None:
    """Start the full FastAPI application with uvicorn."""
    logger.info("Starting full FastAPI application...")
    
    # Set environment for graceful startup
    os.environ.setdefault('CI_MODE', '0')
    os.environ.setdefault('DISABLE_ML', '0')
    os.environ.setdefault('GRACEFUL_STARTUP', '1')  # Enable graceful startup by default
    
    # Import and configure uvicorn
    import uvicorn
    
    # Configure uvicorn with production settings
    config = uvicorn.Config(
        app="api.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True,
        server_header=False,  # Don't expose uvicorn version
        date_header=True,
        timeout_keep_alive=5,
        timeout_notify=30,
        limit_max_requests=1000,
        limit_concurrency=1000,
    )
    
    server = uvicorn.Server(config)
    
    logger.info(f"Full FastAPI server starting on port {port}")
    logger.info(f"Endpoints available:")
    logger.info(f"  - GET /api/health")
    logger.info(f"  - GET /api/version")
    logger.info(f"  - GET /api/features")
    logger.info(f"  - GET /api/presets")
    logger.info(f"  - POST /api/assessments")
    logger.info(f"  - GET /api/engagements") 
    logger.info(f"  - GET /api/admin/status")
    
    # Run the server
    server.run()


def start_minimal_app(port: int) -> None:
    """Start the minimal health check server."""
    logger.info("Starting minimal health check server as fallback...")
    
    # Import the minimal app
    from minimal_app import main as minimal_main
    
    # Set the port
    os.environ['PORT'] = str(port)
    
    # Start minimal server
    minimal_main()


def main():
    """Main startup function with intelligent fallback strategy."""
    start_time = datetime.now(timezone.utc)
    port = get_port()
    
    logger.info("=" * 60)
    logger.info("AI-Enabled Cyber Maturity Assessment API - Production Startup")
    logger.info("=" * 60)
    logger.info(f"Startup time: {start_time.isoformat()}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Port: {port}")
    logger.info(f"CI_MODE: {os.getenv('CI_MODE', 'not set')}")
    logger.info(f"DISABLE_ML: {os.getenv('DISABLE_ML', 'not set')}")
    
    # Check if we're in CI mode (prefer minimal for speed)
    ci_mode = os.getenv('CI_MODE', '0') == '1'
    if ci_mode:
        logger.info("CI_MODE detected - using minimal server for speed")
        start_minimal_app(port)
        return
    
    # Check critical dependencies
    deps_ok, missing_deps = check_critical_dependencies()
    if not deps_ok:
        logger.warning("Critical dependencies missing:")
        for dep in missing_deps:
            logger.warning(f"  - {dep}")
        logger.warning("Falling back to minimal health check server")
        start_minimal_app(port)
        return
    
    # Test app import
    app_ok, import_error = test_app_import()
    if not app_ok:
        logger.error("FastAPI app import failed:")
        logger.error(import_error)
        logger.warning("Falling back to minimal health check server")
        start_minimal_app(port)
        return
    
    # Try to start full app
    try:
        start_full_app(port)
    except Exception as e:
        logger.error(f"Failed to start full FastAPI app: {str(e)}")
        logger.error(traceback.format_exc())
        logger.warning("Attempting fallback to minimal server...")
        
        try:
            start_minimal_app(port)
        except Exception as fallback_error:
            logger.critical(f"Minimal server also failed: {str(fallback_error)}")
            logger.critical("All startup options exhausted")
            sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Startup script failed: {str(e)}")
        logger.critical(traceback.format_exc())
        sys.exit(1)