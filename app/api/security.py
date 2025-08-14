import os
import re
import email.utils
from fastapi import Header, HTTPException, Depends
from typing import Dict
from ..domain.repository import Repository


def is_admin(user_email: str) -> bool:
    """Check if user is an admin based on ADMIN_EMAILS env var"""
    # Validate email format first
    if not user_email or not isinstance(user_email, str):
        return False
    
    # Parse and normalize email
    parsed = email.utils.parseaddr(user_email.strip())
    if not parsed[1] or '@' not in parsed[1]:
        return False
    
    canonical_email = parsed[1].strip().lower()
    
    admins = [e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()]
    return canonical_email in admins


async def current_context(
    x_user_email: str = Header(..., alias="X-User-Email"),
    x_engagement_id: str = Header(..., alias="X-Engagement-ID")
) -> Dict[str, str]:
    """Extract current user and engagement context from headers"""
    # Validate and sanitize email
    if not x_user_email or not x_user_email.strip():
        raise HTTPException(422, "X-User-Email header is required")
    
    parsed = email.utils.parseaddr(x_user_email.strip())
    if not parsed[1] or '@' not in parsed[1]:
        raise HTTPException(422, "X-User-Email header must be a valid email address")
    
    canonical_email = parsed[1].strip().lower()
    
    # Validate and sanitize engagement ID
    if not x_engagement_id or not x_engagement_id.strip():
        raise HTTPException(422, "X-Engagement-ID header is required")
    
    engagement_id_normalized = x_engagement_id.strip()
    # Basic validation - alphanumeric, hyphens, underscores allowed
    if not re.match(r'^[a-zA-Z0-9_-]+$', engagement_id_normalized):
        raise HTTPException(422, "X-Engagement-ID header must contain only alphanumeric characters, hyphens, and underscores")
    
    return {"user_email": canonical_email, "engagement_id": engagement_id_normalized}


def require_member(repo: Repository, ctx: Dict[str, str], min_role: str = "member"):
    """Ensure user has required role in the engagement"""
    m = repo.get_membership(ctx["engagement_id"], ctx["user_email"])
    
    # Admin users have access to everything
    if is_admin(ctx["user_email"]):
        return
    
    # Check membership exists
    if m is None:
        raise HTTPException(403, "Not a member of this engagement")
    
    # Check role hierarchy
    if min_role == "lead" and m.role != "lead":
        raise HTTPException(403, "Lead role required")


def require_admin(repo: Repository, ctx: Dict[str, str]):
    """Ensure user is an admin"""
    if not is_admin(ctx["user_email"]):
        raise HTTPException(403, "Admin access required")
