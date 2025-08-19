"""
Admin Settings API Routes

Provides demo admin management endpoints and system status information.
Only available in demo mode for security.
"""

import os
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from config import config
from api.security import current_context
from domain.admin_repository import create_admin_repository

router = APIRouter(prefix="/admin", tags=["admin-settings"])
logger = logging.getLogger(__name__)


class DemoAdminsResponse(BaseModel):
    """Response model for demo admin list"""
    emails: List[str]
    total_count: int


class StatusResponse(BaseModel):
    """System status response model"""
    auth_mode: str
    data_backend: str
    storage_mode: str
    rag_mode: str
    orchestrator_mode: str
    version: str
    environment: str


def _ensure_demo_mode():
    """Ensure we're in demo mode, raise 404 if not"""
    auth_mode = os.getenv("AUTH_MODE", "demo").lower()
    if auth_mode != "demo":
        raise HTTPException(
            status_code=404, 
            detail="Demo admin endpoints only available in AUTH_MODE=demo"
        )


@router.get("/demo-admins", response_model=DemoAdminsResponse)
async def get_demo_admins(
    request: Request,
    ctx: Dict[str, Any] = Depends(current_context)
):
    """
    Get list of demo admin emails (demo mode only)
    
    Returns the current list of emails that have demo admin privileges.
    Only available when AUTH_MODE=demo.
    """
    _ensure_demo_mode()
    
    correlation_id = request.headers.get("X-Correlation-ID", "demo-admins-get")
    
    logger.info(
        "Demo admins list requested",
        extra={
            "correlation_id": correlation_id,
            "user_email": ctx.get("user_email"),
            "auth_mode": os.getenv("AUTH_MODE")
        }
    )
    
    try:
        # Get repository and admin repository
        from api.main import app
        repository = getattr(app.state, 'repo', None)
        
        admin_repo = create_admin_repository(
            data_backend=os.getenv("DATA_BACKEND", "local"),
            repository=repository
        )
        
        demo_admins = await admin_repo.get_demo_admins()
        admin_list = sorted(list(demo_admins))
        
        logger.info(
            "Demo admins list retrieved",
            extra={
                "correlation_id": correlation_id,
                "admin_count": len(admin_list)
            }
        )
        
        return DemoAdminsResponse(
            emails=admin_list,
            total_count=len(admin_list)
        )
        
    except Exception as e:
        logger.error(
            "Failed to get demo admins list",
            extra={
                "correlation_id": correlation_id,
                "error": str(e),
                "user_email": ctx.get("user_email")
            }
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve demo admins: {str(e)}"
        )


@router.post("/demo-admins/self")
async def add_self_as_demo_admin(
    request: Request,
    ctx: Dict[str, Any] = Depends(current_context)
):
    """
    Add current user to demo admin list (demo mode only)
    
    Allows the currently signed-in user to grant themselves admin privileges
    in demo mode. This is safe because it only works in demo mode and provides
    a convenient way to test admin features without redeployment.
    """
    _ensure_demo_mode()
    
    correlation_id = request.headers.get("X-Correlation-ID", "demo-admin-self")
    user_email = ctx.get("user_email")
    
    if not user_email:
        raise HTTPException(
            status_code=400,
            detail="User email not found in context"
        )
    
    logger.info(
        "Self demo admin grant requested",
        extra={
            "correlation_id": correlation_id,
            "user_email": user_email,
            "auth_mode": os.getenv("AUTH_MODE")
        }
    )
    
    try:
        # Get repository and admin repository
        from api.main import app
        repository = getattr(app.state, 'repo', None)
        
        admin_repo = create_admin_repository(
            data_backend=os.getenv("DATA_BACKEND", "local"),
            repository=repository
        )
        
        # Add current user as demo admin
        was_added = await admin_repo.add_demo_admin(user_email)
        
        if was_added:
            logger.info(
                "User added as demo admin",
                extra={
                    "correlation_id": correlation_id,
                    "user_email": user_email
                }
            )
            message = f"Successfully granted demo admin privileges to {user_email}"
        else:
            logger.info(
                "User already demo admin",
                extra={
                    "correlation_id": correlation_id,
                    "user_email": user_email
                }
            )
            message = f"User {user_email} already has demo admin privileges"
        
        return {
            "success": True,
            "message": message,
            "user_email": user_email,
            "was_added": was_added
        }
        
    except Exception as e:
        logger.error(
            "Failed to add self as demo admin",
            extra={
                "correlation_id": correlation_id,
                "error": str(e),
                "user_email": user_email
            }
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to grant demo admin privileges: {str(e)}"
        )


@router.get("/status", response_model=StatusResponse)
async def get_system_status(request: Request):
    """
    Get system configuration status
    
    Returns current mode flags and system information for display
    in admin interfaces and troubleshooting.
    """
    correlation_id = request.headers.get("X-Correlation-ID", "status")
    
    logger.info(
        "System status requested",
        extra={"correlation_id": correlation_id}
    )
    
    try:
        status = StatusResponse(
            auth_mode=os.getenv("AUTH_MODE", "demo"),
            data_backend=os.getenv("DATA_BACKEND", "local"),
            storage_mode=os.getenv("STORAGE_MODE", "local"),
            rag_mode=os.getenv("RAG_MODE", "off"),
            orchestrator_mode=os.getenv("ORCHESTRATOR_MODE", "stub"),
            version=os.getenv("APP_VERSION", "dev"),
            environment=os.getenv("BUILD_ENV", os.getenv("ENVIRONMENT", "development"))
        )
        
        logger.info(
            "System status retrieved",
            extra={
                "correlation_id": correlation_id,
                "auth_mode": status.auth_mode,
                "data_backend": status.data_backend,
                "environment": status.environment
            }
        )
        
        return status
        
    except Exception as e:
        logger.error(
            "Failed to get system status",
            extra={
                "correlation_id": correlation_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve system status: {str(e)}"
        )