"""
Minimal version and health check endpoint to avoid import issues.
"""
import os
import logging
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(tags=["system"])
logger = logging.getLogger(__name__)


class VersionResponse(BaseModel):
    """Minimal version response"""
    app_name: str
    app_version: str
    timestamp: str
    status: str


@router.get("/health")
async def health_check():
    """
    Simple health check endpoint for load balancers and monitoring.
    """
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("Health check failed", extra={"error": str(e)})
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/version", response_model=VersionResponse)
async def get_version():
    """
    Minimal version endpoint.
    """
    try:
        return VersionResponse(
            app_name="AI-Enabled Cyber Maturity Assessment",
            app_version=os.getenv("APP_VERSION", "dev"),
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="operational"
        )
    except Exception as e:
        logger.error("Version check failed", extra={"error": str(e)})
        return VersionResponse(
            app_name="AI-Enabled Cyber Maturity Assessment",
            app_version="unknown",
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="error"
        )