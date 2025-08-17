"""
Version and system status endpoint for monitoring and debugging.
Provides git SHA, build time, app version, and RAG status information.
"""
import os
import subprocess
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel

from ...config import config
from ...services.rag_service import create_rag_service


router = APIRouter(tags=["system"])
logger = logging.getLogger(__name__)


class VersionResponse(BaseModel):
    """Version and system status response"""
    app_name: str
    app_version: str
    git_sha: str
    git_branch: str
    build_time: str
    build_environment: str
    
    # RAG status
    rag_status: Dict[str, Any]
    
    # System info
    python_version: str
    platform: str
    
    # Health checks
    timestamp: str
    uptime_seconds: Optional[float] = None


def get_git_info() -> Dict[str, str]:
    """Get git information safely"""
    git_info = {
        "sha": "unknown",
        "branch": "unknown"
    }
    
    try:
        # Get git SHA
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info["sha"] = result.stdout.strip()[:12]  # Short SHA
            
    except Exception as e:
        logger.debug(f"Failed to get git SHA: {e}")
    
    try:
        # Get git branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info["branch"] = result.stdout.strip()
            
    except Exception as e:
        logger.debug(f"Failed to get git branch: {e}")
    
    return git_info


def get_build_info() -> Dict[str, str]:
    """Get build information from environment variables"""
    return {
        "time": os.getenv("BUILD_TIME", "unknown"),
        "environment": os.getenv("BUILD_ENV", os.getenv("ENVIRONMENT", "development")),
        "version": os.getenv("APP_VERSION", "dev")
    }


def get_system_info() -> Dict[str, str]:
    """Get system information"""
    import sys
    import platform
    
    return {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.system().lower()
    }


# Store startup time for uptime calculation
_startup_time = datetime.now(timezone.utc)


@router.get("/version", response_model=VersionResponse)
async def get_version(request: Request):
    """
    Get application version and system status information.
    
    Returns comprehensive system information including:
    - Application version and build details
    - Git information (SHA, branch)
    - RAG service status and configuration
    - System information
    - Health check timestamp
    """
    try:
        # Get basic info
        git_info = get_git_info()
        build_info = get_build_info()
        system_info = get_system_info()
        
        # Get RAG status with graceful error handling
        rag_status = {"error": "RAG service unavailable"}
        try:
            # Create a correlation ID for this status check
            correlation_id = request.headers.get("X-Correlation-ID", "version-check")
            rag_service = create_rag_service(correlation_id)
            rag_status = rag_service.get_status()
            
            # Add metrics if available
            metrics = rag_service.get_metrics()
            if metrics:
                # Summarize recent metrics
                recent_metrics = metrics[-10:]  # Last 10 operations
                rag_status["recent_operations"] = len(recent_metrics)
                rag_status["recent_success_rate"] = sum(1 for m in recent_metrics if m.success) / len(recent_metrics)
                rag_status["avg_duration_seconds"] = sum(m.duration_seconds for m in recent_metrics) / len(recent_metrics)
            
        except Exception as e:
            logger.warning(
                "Failed to get RAG status for version endpoint",
                extra={"error": str(e)}
            )
            rag_status = {
                "error": f"Failed to get RAG status: {str(e)}",
                "config_mode": config.rag.mode,
                "config_enabled": config.rag.enabled
            }
        
        # Calculate uptime
        current_time = datetime.now(timezone.utc)
        uptime_seconds = (current_time - _startup_time).total_seconds()
        
        response = VersionResponse(
            app_name="AI-Enabled Cyber Maturity Assessment",
            app_version=build_info["version"],
            git_sha=git_info["sha"],
            git_branch=git_info["branch"],
            build_time=build_info["time"],
            build_environment=build_info["environment"],
            rag_status=rag_status,
            python_version=system_info["python_version"],
            platform=system_info["platform"],
            timestamp=current_time.isoformat(),
            uptime_seconds=uptime_seconds
        )
        
        logger.info(
            "Version endpoint accessed",
            extra={
                "app_version": response.app_version,
                "git_sha": response.git_sha,
                "rag_operational": rag_status.get("operational", False),
                "uptime_seconds": uptime_seconds
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Failed to generate version response",
            extra={"error": str(e)}
        )
        
        # Return minimal response on error
        current_time = datetime.now(timezone.utc)
        return VersionResponse(
            app_name="AI-Enabled Cyber Maturity Assessment",
            app_version="unknown",
            git_sha="unknown",
            git_branch="unknown",
            build_time="unknown",
            build_environment="unknown",
            rag_status={"error": f"Version endpoint error: {str(e)}"},
            python_version="unknown",
            platform="unknown",
            timestamp=current_time.isoformat(),
            uptime_seconds=(current_time - _startup_time).total_seconds()
        )


@router.get("/health")
async def health_check():
    """
    Simple health check endpoint for load balancers and monitoring.
    
    Returns basic status without detailed system information.
    """
    try:
        # Quick RAG health check
        rag_healthy = False
        try:
            if config.is_rag_enabled():
                rag_service = create_rag_service("health-check")
                rag_healthy = rag_service.is_operational()
            else:
                rag_healthy = True  # RAG disabled is considered healthy
        except Exception:
            rag_healthy = False
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rag_operational": rag_healthy
        }
        
    except Exception as e:
        logger.error("Health check failed", extra={"error": str(e)})
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/rag/metrics")
async def rag_metrics(request: Request):
    """
    Get aggregated RAG metrics for monitoring and observability.
    
    Returns performance metrics, success rates, and operational statistics
    for RAG operations across all engagements.
    """
    try:
        correlation_id = request.headers.get("X-Correlation-ID", "metrics-check")
        
        # Get basic RAG status
        rag_service = create_rag_service(correlation_id)
        status = rag_service.get_status()
        metrics = rag_service.get_metrics()
        
        # Aggregate metrics by operation type
        operation_stats = {}
        total_operations = len(metrics)
        
        for metric in metrics:
            op_type = metric.operation
            if op_type not in operation_stats:
                operation_stats[op_type] = {
                    "count": 0,
                    "success_count": 0,
                    "total_duration": 0,
                    "avg_duration": 0,
                    "success_rate": 0,
                    "min_duration": float('inf'),
                    "max_duration": 0,
                    "recent_errors": []
                }
            
            stats = operation_stats[op_type]
            stats["count"] += 1
            stats["total_duration"] += metric.duration_seconds
            stats["min_duration"] = min(stats["min_duration"], metric.duration_seconds)
            stats["max_duration"] = max(stats["max_duration"], metric.duration_seconds)
            
            if metric.success:
                stats["success_count"] += 1
            elif metric.error_message:
                stats["recent_errors"].append({
                    "error": metric.error_message,
                    "engagement_id": metric.engagement_id
                })
        
        # Calculate derived metrics
        for stats in operation_stats.values():
            if stats["count"] > 0:
                stats["success_rate"] = stats["success_count"] / stats["count"]
                stats["avg_duration"] = stats["total_duration"] / stats["count"]
                if stats["min_duration"] == float('inf'):
                    stats["min_duration"] = 0
                # Limit recent errors to last 5
                stats["recent_errors"] = stats["recent_errors"][-5:]
            del stats["total_duration"]  # Remove intermediate calculation
        
        # Overall system metrics
        overall_success_rate = sum(1 for m in metrics if m.success) / total_operations if total_operations > 0 else 0
        avg_duration = sum(m.duration_seconds for m in metrics) / total_operations if total_operations > 0 else 0
        
        response = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rag_operational": status.get("operational", False),
            "rag_mode": status.get("mode", "unknown"),
            "total_operations": total_operations,
            "overall_success_rate": round(overall_success_rate, 3),
            "overall_avg_duration_seconds": round(avg_duration, 3),
            "operation_stats": operation_stats,
            "config": status.get("config", {})
        }
        
        logger.info(
            "RAG metrics endpoint accessed",
            extra={
                "correlation_id": correlation_id,
                "total_operations": total_operations,
                "overall_success_rate": overall_success_rate
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Failed to get RAG metrics",
            extra={"error": str(e)}
        )
        return {
            "error": f"Failed to get RAG metrics: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/rag/status")
async def rag_status(request: Request):
    """
    Detailed RAG service status endpoint for monitoring and debugging.
    
    Returns comprehensive RAG configuration and operational status.
    """
    try:
        correlation_id = request.headers.get("X-Correlation-ID", "rag-status-check")
        
        # Get detailed RAG status
        rag_service = create_rag_service(correlation_id)
        status = rag_service.get_status()
        
        # Add detailed metrics
        metrics = rag_service.get_metrics()
        status["metrics"] = {
            "total_operations": len(metrics),
            "operations_by_type": {},
            "recent_errors": []
        }
        
        # Analyze metrics
        for metric in metrics:
            op_type = metric.operation
            if op_type not in status["metrics"]["operations_by_type"]:
                status["metrics"]["operations_by_type"][op_type] = {
                    "count": 0,
                    "success_count": 0,
                    "avg_duration": 0
                }
            
            status["metrics"]["operations_by_type"][op_type]["count"] += 1
            if metric.success:
                status["metrics"]["operations_by_type"][op_type]["success_count"] += 1
            
            # Collect recent errors
            if not metric.success and metric.error_message:
                status["metrics"]["recent_errors"].append({
                    "operation": metric.operation,
                    "error": metric.error_message,
                    "engagement_id": metric.engagement_id
                })
        
        # Calculate success rates and average durations
        for op_type, stats in status["metrics"]["operations_by_type"].items():
            if stats["count"] > 0:
                stats["success_rate"] = stats["success_count"] / stats["count"]
                # Calculate average duration for this operation type
                op_metrics = [m for m in metrics if m.operation == op_type]
                stats["avg_duration"] = sum(m.duration_seconds for m in op_metrics) / len(op_metrics)
        
        # Limit recent errors
        status["metrics"]["recent_errors"] = status["metrics"]["recent_errors"][-10:]
        
        logger.info(
            "RAG status endpoint accessed",
            extra={
                "correlation_id": correlation_id,
                "operational": status.get("operational", False),
                "total_operations": len(metrics)
            }
        )
        
        return status
        
    except Exception as e:
        logger.error(
            "Failed to get RAG status",
            extra={"error": str(e)}
        )
        return {
            "error": f"Failed to get RAG status: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }