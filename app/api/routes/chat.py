"""
Chat API Endpoints

Provides orchestrator shell interface for chat messages and command execution.
"""

import sys
sys.path.append("/app")
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from domain.models import ChatMessage, RunCard
from domain.repository import Repository
from services.chat_commands import create_chat_command_parser
from services.audit import audit_log_async
from api.security import current_context, require_member

router = APIRouter(prefix="/api/chat", tags=["chat"])


# Request/Response Models
class ChatMessageCreate(BaseModel):
    """Request model for creating chat messages"""
    message: str = Field(..., min_length=1, max_length=2000)
    correlation_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    """Response model for chat messages"""
    id: str
    engagement_id: str
    message: str
    sender: str
    timestamp: datetime
    correlation_id: Optional[str] = None


class RunCardResponse(BaseModel):
    """Response model for run cards"""
    id: str
    engagement_id: str
    command: str
    inputs: Dict[str, any]
    outputs: Optional[Dict[str, any]] = None
    status: str
    created_at: datetime
    created_by: str
    citations: Optional[List[str]] = None


class ChatHistoryResponse(BaseModel):
    """Response model for paginated chat history"""
    messages: List[ChatMessageResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class RunCardHistoryResponse(BaseModel):
    """Response model for paginated run cards"""
    run_cards: List[RunCardResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


def get_repo(request: Request) -> Repository:
    """Get repository from app state"""
    return request.app.state.repo


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    msg: ChatMessageCreate,
    request: Request,
    repo: Repository = Depends(get_repo),
    ctx: Dict[str, str] = Depends(current_context)
):
    """
    Send a chat message, parse for commands, and create RunCard if needed
    """
    # Ensure user is a member of the engagement
    require_member(repo, ctx, "member")
    
    correlation_id = msg.correlation_id or request.headers.get("X-Correlation-ID", "unknown")
    
    # Create chat message
    chat_message = ChatMessage(
        engagement_id=ctx["engagement_id"],
        message=msg.message,
        sender="user",
        correlation_id=correlation_id
    )
    
    # Store chat message
    created_message = repo.create_chat_message(chat_message)
    
    # Parse message for commands
    parser = create_chat_command_parser()
    parsed_command = parser.parse_command(msg.message)
    
    if parsed_command:
        # Create RunCard for command execution
        run_card = RunCard(
            engagement_id=ctx["engagement_id"],
            command=parsed_command.raw_text,
            inputs=parsed_command.inputs,
            status="queued",
            created_by=ctx["user_email"]
        )
        
        # Store run card
        created_run_card = repo.create_run_card(run_card)
        
        # Audit log command creation
        await audit_log_async(
            repo=repo,
            user_email=ctx["user_email"],
            engagement_id=ctx["engagement_id"],
            action_type="chat_command_created",
            resource_id=created_run_card.id,
            details={
                "command": parsed_command.command,
                "inputs": parsed_command.inputs,
                "run_card_id": created_run_card.id
            },
            correlation_id=correlation_id
        )
    
    # Audit log message creation
    await audit_log_async(
        repo=repo,
        user_email=ctx["user_email"],
        engagement_id=ctx["engagement_id"],
        action_type="chat_message_sent",
        resource_id=created_message.id,
        details={
            "message_length": len(msg.message),
            "has_command": parsed_command is not None,
            "command_type": parsed_command.command if parsed_command else None
        },
        correlation_id=correlation_id
    )
    
    return ChatMessageResponse(
        id=created_message.id,
        engagement_id=created_message.engagement_id,
        message=created_message.message,
        sender=created_message.sender,
        timestamp=created_message.timestamp,
        correlation_id=created_message.correlation_id
    )


@router.get("/messages", response_model=ChatHistoryResponse)
def get_chat_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    repo: Repository = Depends(get_repo),
    ctx: Dict[str, str] = Depends(current_context)
):
    """
    Get paginated chat message history for engagement
    """
    # Ensure user is a member of the engagement
    require_member(repo, ctx, "member")
    
    # Get chat messages with pagination
    messages, total = repo.list_chat_messages(
        engagement_id=ctx["engagement_id"],
        page=page,
        page_size=page_size
    )
    
    # Convert to response models
    message_responses = [
        ChatMessageResponse(
            id=msg.id,
            engagement_id=msg.engagement_id,
            message=msg.message,
            sender=msg.sender,
            timestamp=msg.timestamp,
            correlation_id=msg.correlation_id
        )
        for msg in messages
    ]
    
    return ChatHistoryResponse(
        messages=message_responses,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total
    )


@router.get("/run-cards", response_model=RunCardHistoryResponse)
def get_run_cards(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    repo: Repository = Depends(get_repo),
    ctx: Dict[str, str] = Depends(current_context)
):
    """
    Get paginated run cards history for engagement
    """
    # Ensure user is a member of the engagement
    require_member(repo, ctx, "member")
    
    # Validate status filter if provided
    if status and status not in ["queued", "running", "done", "error"]:
        raise HTTPException(400, "Invalid status filter")
    
    # Get run cards with pagination and filtering
    run_cards, total = repo.list_run_cards(
        engagement_id=ctx["engagement_id"],
        status=status,
        page=page,
        page_size=page_size
    )
    
    # Convert to response models
    run_card_responses = [
        RunCardResponse(
            id=card.id,
            engagement_id=card.engagement_id,
            command=card.command,
            inputs=card.inputs,
            outputs=card.outputs,
            status=card.status,
            created_at=card.created_at,
            created_by=card.created_by,
            citations=card.citations
        )
        for card in run_cards
    ]
    
    return RunCardHistoryResponse(
        run_cards=run_card_responses,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total
    )