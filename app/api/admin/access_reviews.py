"""
Access Reviews API for compliance and governance
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Any
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class AccessReviewService:
    """Service for managing access reviews and membership exports"""
    
    @staticmethod
    async def export_membership_by_engagement(
        engagement_id: str = None
    ) -> Dict[str, Any]:
        """Export current membership by engagement for access review"""
        
        # Mock data - replace with actual database queries
        memberships = {
            "report_id": f"access-review-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "review_period": {
                "start": (datetime.now() - timedelta(days=90)).isoformat(),
                "end": datetime.now().isoformat()
            },
            "engagements": []
        }
        
        # Sample engagement data
        sample_engagements = [
            {
                "engagement_id": "eng-001",
                "client_name": "TechCorp Inc",
                "members": [
                    {
                        "user_id": "user123",
                        "email": "consultant@example.com",
                        "roles": ["consultant", "analyst"],
                        "permissions": ["read", "analyze", "report"],
                        "last_active": "2024-01-15T10:30:00Z",
                        "access_granted": "2024-01-01T09:00:00Z"
                    }
                ],
                "status": "active",
                "last_review": "2024-01-01T00:00:00Z",
                "next_review": "2024-04-01T00:00:00Z"
            }
        ]
        
        if engagement_id:
            # Filter for specific engagement
            memberships["engagements"] = [
                eng for eng in sample_engagements 
                if eng["engagement_id"] == engagement_id
            ]
        else:
            # Return all engagements
            memberships["engagements"] = sample_engagements
        
        return memberships
    
    @staticmethod
    async def get_review_status() -> Dict[str, Any]:
        """Get access review status for admin dashboard"""
        return {
            "last_review": "2024-01-01T00:00:00Z",
            "next_scheduled": "2024-04-01T00:00:00Z", 
            "overdue_reviews": 0,
            "pending_approvals": 2,
            "total_engagements": 5,
            "compliance_status": "compliant"
        }

@router.get("/export")
async def export_access_review(
    engagement_id: str = None,
    format: str = "json"
):
    """Export membership data for access review"""
    try:
        membership_data = await AccessReviewService.export_membership_by_engagement(
            engagement_id
        )
        
        if format.lower() == "csv":
            # Convert to CSV format for compliance tools
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Headers
            writer.writerow([
                "engagement_id", "client_name", "user_id", "email", 
                "roles", "permissions", "last_active", "access_granted"
            ])
            
            # Data rows
            for eng in membership_data["engagements"]:
                for member in eng["members"]:
                    writer.writerow([
                        eng["engagement_id"],
                        eng["client_name"], 
                        member["user_id"],
                        member["email"],
                        ",".join(member["roles"]),
                        ",".join(member["permissions"]),
                        member["last_active"],
                        member["access_granted"]
                    ])
            
            return {
                "format": "csv",
                "data": output.getvalue(),
                "report_id": membership_data["report_id"]
            }
        
        return membership_data
        
    except Exception as e:
        logger.error(f"Access review export failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate access review export"
        )

@router.get("/status")
async def get_access_review_status():
    """Get current access review status for admin dashboard"""
    try:
        return await AccessReviewService.get_review_status()
    except Exception as e:
        logger.error(f"Failed to get review status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve access review status"
        )