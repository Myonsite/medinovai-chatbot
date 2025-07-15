"""
Chat API Router - Handles conversation and messaging endpoints
Provides REST and WebSocket APIs for real-time healthcare conversations
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any

import structlog
from fastapi import (
    APIRouter, WebSocket, WebSocketDisconnect, Depends, 
    HTTPException, status, Query, Path
)
from pydantic import BaseModel, Field

from orchestration.chat_orchestrator import ChatOrchestrator, Conversation, ConversationMessage
from orchestration.websocket_manager import WebSocketManager
from utils.security import SecurityManager
from utils.config import get_settings

logger = structlog.get_logger(__name__)

router = APIRouter()

# Global instances (would be injected in production)
chat_orchestrator: Optional[ChatOrchestrator] = None
websocket_manager: Optional[WebSocketManager] = None
security_manager: Optional[SecurityManager] = None


# Request/Response Models
class StartConversationRequest(BaseModel):
    """Request model for starting a new conversation."""
    initial_message: str = Field(..., min_length=1, max_length=4096)
    user_id: Optional[str] = None
    channel: str = Field(default="web")
    metadata: Optional[Dict[str, Any]] = None


class SendMessageRequest(BaseModel):
    """Request model for sending a message."""
    message: str = Field(..., min_length=1, max_length=4096)
    message_type: str = Field(default="user")


class ConversationResponse(BaseModel):
    """Response model for conversation data."""
    id: str
    user_id: str
    channel: str
    state: str
    language: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    escalated: bool
    assigned_agent_id: Optional[str] = None
    satisfaction_score: Optional[int] = None


class MessageResponse(BaseModel):
    """Response model for message data."""
    id: str
    conversation_id: str
    type: str
    content: str
    timestamp: datetime
    phi_detected: bool = False
    user_id: Optional[str] = None
    agent_id: Optional[str] = None


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history."""
    conversation: ConversationResponse
    messages: List[MessageResponse]


# Dependency injection helpers
def get_chat_orchestrator() -> ChatOrchestrator:
    """Get chat orchestrator instance."""
    global chat_orchestrator
    if not chat_orchestrator:
        # In production, this would be properly injected
        from main import chat_orchestrator as main_orchestrator
        chat_orchestrator = main_orchestrator
    return chat_orchestrator


def get_websocket_manager() -> WebSocketManager:
    """Get WebSocket manager instance."""
    global websocket_manager
    if not websocket_manager:
        from main import websocket_manager as main_ws_manager
        websocket_manager = main_ws_manager
    return websocket_manager


def get_security_manager() -> SecurityManager:
    """Get security manager instance."""
    global security_manager
    if not security_manager:
        from main import security_manager as main_security
        security_manager = main_security
    return security_manager


# REST API Endpoints

@router.post("/chat/start", response_model=ConversationResponse)
async def start_conversation(
    request: StartConversationRequest,
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator),
    security: SecurityManager = Depends(get_security_manager)
):
    """Start a new conversation."""
    try:
        # Validate input
        if not security.validate_input(request.initial_message):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid message content"
            )
        
        # Sanitize input
        sanitized_message = security.sanitize_input(request.initial_message)
        
        # Start conversation
        conversation = await orchestrator.start_conversation(
            user_id=request.user_id or "anonymous",
            channel=request.channel,
            initial_message=sanitized_message,
            metadata=request.metadata
        )
        
        logger.info(
            "Conversation started via API",
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            channel=conversation.channel
        )
        
        return ConversationResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            channel=conversation.channel,
            state=conversation.state.value,
            language=conversation.language,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=len(conversation.messages),
            escalated=conversation.state.value == "escalated",
            assigned_agent_id=conversation.assigned_agent_id,
            satisfaction_score=conversation.satisfaction_score
        )
        
    except Exception as e:
        logger.error("Failed to start conversation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start conversation"
        )


@router.post("/chat/{conversation_id}/message", response_model=MessageResponse)
async def send_message(
    conversation_id: str = Path(...),
    request: SendMessageRequest = ...,
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator),
    security: SecurityManager = Depends(get_security_manager)
):
    """Send a message to an existing conversation."""
    try:
        # Validate input
        if not security.validate_input(request.message):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid message content"
            )
        
        # Sanitize input
        sanitized_message = security.sanitize_input(request.message)
        
        # Process message
        response_message = await orchestrator.process_message(
            conversation_id=conversation_id,
            message=sanitized_message
        )
        
        return MessageResponse(
            id=response_message.id,
            conversation_id=response_message.conversation_id,
            type=response_message.type.value,
            content=response_message.content,
            timestamp=response_message.timestamp,
            phi_detected=response_message.phi_detected,
            user_id=response_message.user_id,
            agent_id=response_message.agent_id
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to send message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )


@router.get("/chat/{conversation_id}", response_model=ConversationHistoryResponse)
async def get_conversation(
    conversation_id: str = Path(...),
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator)
):
    """Get conversation details and message history."""
    try:
        conversation = await orchestrator.get_conversation(conversation_id)
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Convert messages to response format
        messages = [
            MessageResponse(
                id=msg.id,
                conversation_id=msg.conversation_id,
                type=msg.type.value,
                content=msg.content,
                timestamp=msg.timestamp,
                phi_detected=msg.phi_detected,
                user_id=msg.user_id,
                agent_id=msg.agent_id
            )
            for msg in conversation.messages
        ]
        
        conversation_response = ConversationResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            channel=conversation.channel,
            state=conversation.state.value,
            language=conversation.language,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=len(conversation.messages),
            escalated=conversation.state.value == "escalated",
            assigned_agent_id=conversation.assigned_agent_id,
            satisfaction_score=conversation.satisfaction_score
        )
        
        return ConversationHistoryResponse(
            conversation=conversation_response,
            messages=messages
        )
        
    except Exception as e:
        logger.error("Failed to get conversation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation"
        )


@router.get("/chat/user/{user_id}", response_model=List[ConversationResponse])
async def get_user_conversations(
    user_id: str = Path(...),
    limit: int = Query(10, ge=1, le=50),
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator)
):
    """Get user's conversation history."""
    try:
        conversations = await orchestrator.get_user_conversations(user_id, limit)
        
        return [
            ConversationResponse(
                id=conv.id,
                user_id=conv.user_id,
                channel=conv.channel,
                state=conv.state.value,
                language=conv.language,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=len(conv.messages),
                escalated=conv.state.value == "escalated",
                assigned_agent_id=conv.assigned_agent_id,
                satisfaction_score=conv.satisfaction_score
            )
            for conv in conversations
        ]
        
    except Exception as e:
        logger.error("Failed to get user conversations", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations"
        )


@router.post("/chat/{conversation_id}/escalate")
async def escalate_conversation(
    conversation_id: str = Path(...),
    reason: str = Query(..., min_length=1, max_length=255),
    priority: str = Query("normal", regex="^(low|normal|high|urgent)$"),
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator)
):
    """Escalate conversation to human agent."""
    try:
        success = await orchestrator.escalate_conversation(
            conversation_id=conversation_id,
            reason=reason,
            priority=priority
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found or already escalated"
            )
        
        return {"message": "Conversation escalated successfully"}
        
    except Exception as e:
        logger.error("Failed to escalate conversation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to escalate conversation"
        )


@router.post("/chat/{conversation_id}/complete")
async def complete_conversation(
    conversation_id: str = Path(...),
    satisfaction_score: Optional[int] = Query(None, ge=1, le=5),
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator)
):
    """Mark conversation as completed."""
    try:
        success = await orchestrator.complete_conversation(
            conversation_id=conversation_id,
            satisfaction_score=satisfaction_score
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        return {"message": "Conversation completed successfully"}
        
    except Exception as e:
        logger.error("Failed to complete conversation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete conversation"
        )


# WebSocket Endpoints

@router.websocket("/chat/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: Optional[str] = Query(None),
    conversation_id: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    ws_manager: WebSocketManager = Depends(get_websocket_manager)
):
    """WebSocket endpoint for real-time chat."""
    connection_id = None
    
    try:
        # Accept connection and register
        connection_id = await ws_manager.connect(
            websocket=websocket,
            user_id=user_id,
            conversation_id=conversation_id,
            agent_id=agent_id
        )
        
        logger.info(
            "WebSocket connection established",
            connection_id=connection_id,
            user_id=user_id,
            conversation_id=conversation_id,
            agent_id=agent_id
        )
        
        # Listen for messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Handle message through WebSocket manager
                await ws_manager.handle_message(connection_id, message_data)
                
            except WebSocketDisconnect:
                logger.info("WebSocket disconnected", connection_id=connection_id)
                break
                
            except json.JSONDecodeError:
                logger.warning("Invalid JSON received", connection_id=connection_id)
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
                
            except Exception as e:
                logger.error(
                    "Error handling WebSocket message",
                    connection_id=connection_id,
                    error=str(e)
                )
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Message processing failed"
                }))
                
    except Exception as e:
        logger.error("WebSocket connection failed", error=str(e))
        
    finally:
        # Clean up connection
        if connection_id:
            await ws_manager.disconnect(connection_id)


# Health check for chat system
@router.get("/chat/health")
async def chat_health_check():
    """Health check for chat system."""
    try:
        # Check orchestrator health
        orchestrator = get_chat_orchestrator()
        if not orchestrator:
            return {"status": "unhealthy", "reason": "Chat orchestrator not available"}
        
        # Check WebSocket manager
        ws_manager = get_websocket_manager()
        if not ws_manager:
            return {"status": "unhealthy", "reason": "WebSocket manager not available"}
        
        return {
            "status": "healthy",
            "active_connections": ws_manager.get_connection_count(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Chat health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)} 