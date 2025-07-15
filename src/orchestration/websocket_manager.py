"""
WebSocket Manager - Real-time communication for MedinovAI
Handles WebSocket connections, real-time messaging, and agent handoffs
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Set

import structlog
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from utils.config import Settings

logger = structlog.get_logger(__name__)


class ConnectionInfo(BaseModel):
    """WebSocket connection information."""
    connection_id: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    channel: str = "web"
    agent_id: Optional[str] = None
    connected_at: datetime
    last_activity: datetime
    
    class Config:
        arbitrary_types_allowed = True


class WebSocketManager:
    """
    Manages WebSocket connections for real-time communication.
    Handles patient-AI chat and agent handoffs.
    """
    
    def __init__(self):
        # Active WebSocket connections
        self.connections: Dict[str, WebSocket] = {}
        self.connection_info: Dict[str, ConnectionInfo] = {}
        
        # Conversation to connection mapping
        self.conversation_connections: Dict[str, Set[str]] = {}
        
        # Agent connections
        self.agent_connections: Dict[str, Set[str]] = {}
        
        logger.info("WebSocket manager initialized")
    
    async def initialize(self) -> None:
        """Initialize WebSocket manager."""
        # Start background cleanup task
        asyncio.create_task(self._cleanup_stale_connections())
        logger.info("WebSocket manager background tasks started")
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> str:
        """Accept and register new WebSocket connection."""
        await websocket.accept()
        
        connection_id = str(uuid.uuid4())
        
        # Store connection
        self.connections[connection_id] = websocket
        
        # Create connection info
        info = ConnectionInfo(
            connection_id=connection_id,
            user_id=user_id,
            conversation_id=conversation_id,
            agent_id=agent_id,
            connected_at=datetime.utcnow(),
            last_activity=datetime.utcnow()
        )
        self.connection_info[connection_id] = info
        
        # Map conversation to connection
        if conversation_id:
            if conversation_id not in self.conversation_connections:
                self.conversation_connections[conversation_id] = set()
            self.conversation_connections[conversation_id].add(connection_id)
        
        # Map agent to connection
        if agent_id:
            if agent_id not in self.agent_connections:
                self.agent_connections[agent_id] = set()
            self.agent_connections[agent_id].add(connection_id)
        
        logger.info(
            "WebSocket connection established",
            connection_id=connection_id,
            user_id=user_id,
            conversation_id=conversation_id,
            agent_id=agent_id
        )
        
        # Send connection confirmation
        await self.send_to_connection(connection_id, {
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return connection_id
    
    async def disconnect(self, connection_id: str) -> None:
        """Disconnect and cleanup WebSocket connection."""
        if connection_id not in self.connections:
            return
        
        info = self.connection_info.get(connection_id)
        
        # Remove from conversation mapping
        if info and info.conversation_id:
            conv_connections = self.conversation_connections.get(
                info.conversation_id, set()
            )
            conv_connections.discard(connection_id)
            if not conv_connections:
                del self.conversation_connections[info.conversation_id]
        
        # Remove from agent mapping
        if info and info.agent_id:
            agent_connections = self.agent_connections.get(
                info.agent_id, set()
            )
            agent_connections.discard(connection_id)
            if not agent_connections:
                del self.agent_connections[info.agent_id]
        
        # Remove connection
        del self.connections[connection_id]
        if connection_id in self.connection_info:
            del self.connection_info[connection_id]
        
        logger.info(
            "WebSocket connection closed",
            connection_id=connection_id,
            user_id=info.user_id if info else None
        )
    
    async def send_to_connection(
        self,
        connection_id: str,
        message: Dict[str, Any]
    ) -> bool:
        """Send message to specific connection."""
        if connection_id not in self.connections:
            return False
        
        try:
            websocket = self.connections[connection_id]
            await websocket.send_text(json.dumps(message))
            
            # Update last activity
            if connection_id in self.connection_info:
                self.connection_info[connection_id].last_activity = datetime.utcnow()
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to send message to connection",
                connection_id=connection_id,
                error=str(e)
            )
            # Remove failed connection
            await self.disconnect(connection_id)
            return False
    
    async def send_to_conversation(
        self,
        conversation_id: str,
        message: Dict[str, Any],
        exclude_connection: Optional[str] = None
    ) -> int:
        """Send message to all connections in a conversation."""
        connections = self.conversation_connections.get(conversation_id, set())
        sent_count = 0
        
        for connection_id in connections.copy():
            if exclude_connection and connection_id == exclude_connection:
                continue
            
            success = await self.send_to_connection(connection_id, message)
            if success:
                sent_count += 1
        
        return sent_count
    
    async def send_to_agent(
        self,
        agent_id: str,
        message: Dict[str, Any]
    ) -> int:
        """Send message to all agent connections."""
        connections = self.agent_connections.get(agent_id, set())
        sent_count = 0
        
        for connection_id in connections.copy():
            success = await self.send_to_connection(connection_id, message)
            if success:
                sent_count += 1
        
        return sent_count
    
    async def handle_message(
        self,
        connection_id: str,
        message_data: Dict[str, Any]
    ) -> None:
        """Handle incoming WebSocket message."""
        try:
            info = self.connection_info.get(connection_id)
            if not info:
                return
            
            message_type = message_data.get("type")
            
            if message_type == "chat_message":
                await self._handle_chat_message(connection_id, message_data)
            elif message_type == "typing_start":
                await self._handle_typing_indicator(connection_id, True)
            elif message_type == "typing_stop":
                await self._handle_typing_indicator(connection_id, False)
            elif message_type == "agent_join":
                await self._handle_agent_join(connection_id, message_data)
            elif message_type == "agent_status":
                await self._handle_agent_status(connection_id, message_data)
            else:
                logger.warning(
                    "Unknown message type",
                    connection_id=connection_id,
                    message_type=message_type
                )
            
        except Exception as e:
            logger.error(
                "Error handling WebSocket message",
                connection_id=connection_id,
                error=str(e),
                exc_info=True
            )
    
    async def notify_agent_available(
        self,
        conversation_id: str,
        agent_info: Dict[str, Any]
    ) -> None:
        """Notify conversation participants that agent is available."""
        message = {
            "type": "agent_available",
            "agent": agent_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_to_conversation(conversation_id, message)
    
    async def notify_agent_joined(
        self,
        conversation_id: str,
        agent_info: Dict[str, Any]
    ) -> None:
        """Notify conversation participants that agent joined."""
        message = {
            "type": "agent_joined",
            "agent": agent_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_to_conversation(conversation_id, message)
    
    async def notify_conversation_transferred(
        self,
        conversation_id: str,
        from_ai: bool = True
    ) -> None:
        """Notify about conversation transfer."""
        message = {
            "type": "conversation_transferred",
            "from_ai": from_ai,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_to_conversation(conversation_id, message)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return len(self.connections)
    
    def get_conversation_connections(self, conversation_id: str) -> int:
        """Get number of connections for a conversation."""
        return len(self.conversation_connections.get(conversation_id, set()))
    
    def is_agent_online(self, agent_id: str) -> bool:
        """Check if agent has active connections."""
        return len(self.agent_connections.get(agent_id, set())) > 0
    
    # Private methods
    
    async def _handle_chat_message(
        self,
        connection_id: str,
        message_data: Dict[str, Any]
    ) -> None:
        """Handle chat message from WebSocket."""
        info = self.connection_info.get(connection_id)
        if not info or not info.conversation_id:
            return
        
        # Import here to avoid circular imports
        from main import chat_orchestrator
        
        if chat_orchestrator:
            # Process message through chat orchestrator
            response = await chat_orchestrator.process_message(
                info.conversation_id,
                message_data.get("content", ""),
                user_id=info.user_id
            )
            
            # Send AI response back to conversation
            response_message = {
                "type": "ai_response",
                "content": response.content,
                "message_id": response.id,
                "timestamp": response.timestamp.isoformat()
            }
            
            await self.send_to_conversation(
                info.conversation_id,
                response_message,
                exclude_connection=connection_id
            )
    
    async def _handle_typing_indicator(
        self,
        connection_id: str,
        is_typing: bool
    ) -> None:
        """Handle typing indicator."""
        info = self.connection_info.get(connection_id)
        if not info or not info.conversation_id:
            return
        
        message = {
            "type": "typing_indicator",
            "is_typing": is_typing,
            "user_id": info.user_id,
            "agent_id": info.agent_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_to_conversation(
            info.conversation_id,
            message,
            exclude_connection=connection_id
        )
    
    async def _handle_agent_join(
        self,
        connection_id: str,
        message_data: Dict[str, Any]
    ) -> None:
        """Handle agent joining conversation."""
        info = self.connection_info.get(connection_id)
        if not info or not info.agent_id:
            return
        
        conversation_id = message_data.get("conversation_id")
        if not conversation_id:
            return
        
        # Update connection info
        info.conversation_id = conversation_id
        
        # Add to conversation connections
        if conversation_id not in self.conversation_connections:
            self.conversation_connections[conversation_id] = set()
        self.conversation_connections[conversation_id].add(connection_id)
        
        # Notify conversation participants
        await self.notify_agent_joined(conversation_id, {
            "id": info.agent_id,
            "name": message_data.get("agent_name", "Support Agent")
        })
    
    async def _handle_agent_status(
        self,
        connection_id: str,
        message_data: Dict[str, Any]
    ) -> None:
        """Handle agent status update."""
        info = self.connection_info.get(connection_id)
        if not info or not info.agent_id:
            return
        
        status = message_data.get("status")
        if not status:
            return
        
        # Broadcast status to relevant conversations
        for conv_id in self.conversation_connections:
            if connection_id in self.conversation_connections[conv_id]:
                message = {
                    "type": "agent_status_update",
                    "agent_id": info.agent_id,
                    "status": status,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await self.send_to_conversation(
                    conv_id,
                    message,
                    exclude_connection=connection_id
                )
    
    async def _cleanup_stale_connections(self) -> None:
        """Background task to cleanup stale connections."""
        while True:
            try:
                current_time = datetime.utcnow()
                stale_connections = []
                
                for connection_id, info in self.connection_info.items():
                    # Check if connection is stale (no activity for 30 minutes)
                    if (current_time - info.last_activity).total_seconds() > 1800:
                        stale_connections.append(connection_id)
                
                for connection_id in stale_connections:
                    await self.disconnect(connection_id)
                
                if stale_connections:
                    logger.info(
                        "Cleaned up stale connections",
                        count=len(stale_connections)
                    )
                
                # Sleep for 5 minutes
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(
                    "Error in connection cleanup",
                    error=str(e),
                    exc_info=True
                )
                await asyncio.sleep(60)
    
    async def cleanup(self) -> None:
        """Cleanup WebSocket manager."""
        logger.info("Cleaning up WebSocket manager...")
        
        # Close all connections
        for connection_id in list(self.connections.keys()):
            try:
                websocket = self.connections[connection_id]
                await websocket.close()
            except Exception:
                pass
            
            await self.disconnect(connection_id)
        
        logger.info("WebSocket manager cleanup complete") 