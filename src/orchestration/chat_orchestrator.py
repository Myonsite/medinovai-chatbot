"""
Chat Orchestrator - Core conversation management for MedinovAI
Handles conversation flow, context management, AI responses, and escalation logic
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

import structlog
from pydantic import BaseModel

from .ai_engine import AIEngine
from .context_manager import ContextManager
from .escalation_manager import EscalationManager
from utils.config import Settings
from utils.phi_protection import PHIProtector
from utils.metrics import MetricsCollector

logger = structlog.get_logger(__name__)


class ConversationState(str, Enum):
    """Conversation state enumeration."""
    ACTIVE = "active"
    WAITING_FOR_USER = "waiting_for_user"
    ESCALATED = "escalated"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MessageType(str, Enum):
    """Message type enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    ESCALATION = "escalation"


class ConversationMessage(BaseModel):
    """Individual conversation message model."""
    id: str
    conversation_id: str
    type: MessageType
    content: str
    metadata: Dict[str, Any] = {}
    timestamp: datetime
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    phi_detected: bool = False
    redacted_content: Optional[str] = None


class Conversation(BaseModel):
    """Conversation model with full context and history."""
    id: str
    user_id: str
    channel: str  # web, sms, voice, mattermost
    state: ConversationState
    language: str = "en"
    messages: List[ConversationMessage] = []
    context: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    escalated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_agent_id: Optional[str] = None
    satisfaction_score: Optional[int] = None


class ChatOrchestrator:
    """
    Core chat orchestrator managing conversation flow and AI responses.
    Handles multi-channel conversations with HIPAA compliance and escalation logic.
    """
    
    def __init__(
        self,
        settings: Settings,
        phi_protector: PHIProtector,
        metrics_collector: MetricsCollector
    ):
        self.settings = settings
        self.phi_protector = phi_protector
        self.metrics_collector = metrics_collector
        
        # Core components
        self.ai_engine: Optional[AIEngine] = None
        self.context_manager: Optional[ContextManager] = None
        self.escalation_manager: Optional[EscalationManager] = None
        
        # Active conversations cache
        self.active_conversations: Dict[str, Conversation] = {}
        
        # Conversation timeouts
        self.conversation_timeout = timedelta(hours=1)
        self.escalation_timeout = timedelta(minutes=15)
        
        logger.info("Chat orchestrator initialized")
    
    async def initialize(self) -> None:
        """Initialize all orchestrator components."""
        try:
            # Initialize AI engine
            self.ai_engine = AIEngine(self.settings)
            await self.ai_engine.initialize()
            
            # Initialize context manager
            self.context_manager = ContextManager(self.settings)
            await self.context_manager.initialize()
            
            # Initialize escalation manager
            self.escalation_manager = EscalationManager(self.settings)
            await self.escalation_manager.initialize()
            
            # Start background tasks
            asyncio.create_task(self._cleanup_abandoned_conversations())
            asyncio.create_task(self._monitor_escalation_timeouts())
            
            logger.info("Chat orchestrator components initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize chat orchestrator", error=str(e))
            raise
    
    async def start_conversation(
        self,
        user_id: str,
        channel: str,
        initial_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """Start a new conversation."""
        conversation_id = str(uuid.uuid4())
        
        # Detect language
        language = await self._detect_language(initial_message)
        
        # Create conversation
        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            channel=channel,
            state=ConversationState.ACTIVE,
            language=language,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        # Store in active conversations
        self.active_conversations[conversation_id] = conversation
        
        # Load user context
        await self.context_manager.load_user_context(conversation)
        
        # Process initial message
        response = await self.process_message(
            conversation_id,
            initial_message,
            MessageType.USER
        )
        
        # Record metrics
        self.metrics_collector.record_conversation_started(channel, language)
        
        logger.info(
            "New conversation started",
            conversation_id=conversation_id,
            user_id=user_id,
            channel=channel,
            language=language
        )
        
        return conversation
    
    async def process_message(
        self,
        conversation_id: str,
        message: str,
        message_type: MessageType = MessageType.USER,
        user_id: Optional[str] = None
    ) -> ConversationMessage:
        """Process an incoming message and generate AI response."""
        start_time = datetime.utcnow()
        
        try:
            # Get conversation
            conversation = await self._get_conversation(conversation_id)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            # Check if conversation is in valid state
            if conversation.state not in [ConversationState.ACTIVE, ConversationState.WAITING_FOR_USER]:
                raise ValueError(f"Cannot process message in conversation state: {conversation.state}")
            
            # Detect and redact PHI
            phi_detected, redacted_message = await self.phi_protector.detect_and_redact(message)
            
            # Create user message
            user_message = ConversationMessage(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                type=message_type,
                content=message,
                redacted_content=redacted_message if phi_detected else None,
                phi_detected=phi_detected,
                timestamp=datetime.utcnow(),
                user_id=user_id
            )
            
            # Add to conversation
            conversation.messages.append(user_message)
            
            # Update context with user message
            await self.context_manager.update_context(conversation, user_message)
            
            # Check for escalation triggers
            should_escalate = await self._check_escalation_triggers(conversation, message)
            
            if should_escalate:
                return await self._escalate_conversation(conversation, "AI triggered escalation")
            
            # Generate AI response
            ai_response = await self.ai_engine.generate_response(
                conversation=conversation,
                user_message=user_message,
                context=conversation.context
            )
            
            # Detect PHI in AI response
            ai_phi_detected, ai_redacted = await self.phi_protector.detect_and_redact(ai_response)
            
            # Create AI response message
            assistant_message = ConversationMessage(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                type=MessageType.ASSISTANT,
                content=ai_response,
                redacted_content=ai_redacted if ai_phi_detected else None,
                phi_detected=ai_phi_detected,
                timestamp=datetime.utcnow()
            )
            
            # Add AI response to conversation
            conversation.messages.append(assistant_message)
            
            # Update conversation state
            conversation.updated_at = datetime.utcnow()
            conversation.state = ConversationState.WAITING_FOR_USER
            
            # Update context with AI response
            await self.context_manager.update_context(conversation, assistant_message)
            
            # Save conversation
            await self._save_conversation(conversation)
            
            # Record metrics
            response_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.metrics_collector.record_message_processed(
                channel=conversation.channel,
                response_time_ms=response_time_ms,
                phi_detected=phi_detected or ai_phi_detected
            )
            
            logger.info(
                "Message processed successfully",
                conversation_id=conversation_id,
                response_time_ms=response_time_ms,
                phi_detected=phi_detected
            )
            
            return assistant_message
            
        except Exception as e:
            logger.error(
                "Failed to process message",
                conversation_id=conversation_id,
                error=str(e),
                exc_info=True
            )
            
            # Record error metrics
            self.metrics_collector.record_message_error(
                conversation_id, str(e)
            )
            
            # Return error response
            return ConversationMessage(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                type=MessageType.SYSTEM,
                content="I apologize, but I'm experiencing technical difficulties. Please try again or contact our support team.",
                timestamp=datetime.utcnow()
            )
    
    async def escalate_conversation(
        self,
        conversation_id: str,
        reason: str,
        priority: str = "normal"
    ) -> bool:
        """Manually escalate a conversation to human agent."""
        conversation = await self._get_conversation(conversation_id)
        if not conversation:
            return False
        
        return await self._escalate_conversation(conversation, reason, priority)
    
    async def transfer_to_agent(
        self,
        conversation_id: str,
        agent_id: str
    ) -> bool:
        """Transfer conversation to specific agent."""
        conversation = await self._get_conversation(conversation_id)
        if not conversation:
            return False
        
        try:
            # Update conversation state
            conversation.state = ConversationState.ESCALATED
            conversation.assigned_agent_id = agent_id
            conversation.escalated_at = datetime.utcnow()
            
            # Notify escalation manager
            await self.escalation_manager.assign_to_agent(conversation, agent_id)
            
            # Save conversation
            await self._save_conversation(conversation)
            
            logger.info(
                "Conversation transferred to agent",
                conversation_id=conversation_id,
                agent_id=agent_id
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to transfer conversation to agent",
                conversation_id=conversation_id,
                agent_id=agent_id,
                error=str(e)
            )
            return False
    
    async def complete_conversation(
        self,
        conversation_id: str,
        satisfaction_score: Optional[int] = None
    ) -> bool:
        """Mark conversation as completed."""
        conversation = await self._get_conversation(conversation_id)
        if not conversation:
            return False
        
        try:
            conversation.state = ConversationState.COMPLETED
            conversation.completed_at = datetime.utcnow()
            conversation.satisfaction_score = satisfaction_score
            
            # Remove from active conversations
            if conversation_id in self.active_conversations:
                del self.active_conversations[conversation_id]
            
            # Save conversation
            await self._save_conversation(conversation)
            
            # Record metrics
            self.metrics_collector.record_conversation_completed(
                conversation.channel,
                len(conversation.messages),
                satisfaction_score
            )
            
            logger.info(
                "Conversation completed",
                conversation_id=conversation_id,
                satisfaction_score=satisfaction_score
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to complete conversation",
                conversation_id=conversation_id,
                error=str(e)
            )
            return False
    
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID."""
        return await self._get_conversation(conversation_id)
    
    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Conversation]:
        """Get user's recent conversations."""
        # In production, this would query the database
        user_conversations = [
            conv for conv in self.active_conversations.values()
            if conv.user_id == user_id
        ]
        
        return sorted(
            user_conversations,
            key=lambda x: x.updated_at,
            reverse=True
        )[:limit]
    
    # Private methods
    
    async def _get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation from cache or database."""
        # Check active conversations cache first
        if conversation_id in self.active_conversations:
            return self.active_conversations[conversation_id]
        
        # In production, load from database
        # For now, return None if not in active conversations
        return None
    
    async def _save_conversation(self, conversation: Conversation) -> None:
        """Save conversation to database."""
        # Update in cache
        self.active_conversations[conversation.id] = conversation
        
        # In production, save to database
        # await self.database.save_conversation(conversation)
        pass
    
    async def _detect_language(self, text: str) -> str:
        """Detect language of input text."""
        if not self.settings.auto_detect_language:
            return self.settings.default_language
        
        try:
            from langdetect import detect
            detected = detect(text)
            
            # Map detected language to supported languages
            if detected in self.settings.supported_languages:
                return detected
            
            # Default to configured default language
            return self.settings.default_language
            
        except Exception:
            # Fallback to default language
            return self.settings.default_language
    
    async def _check_escalation_triggers(
        self,
        conversation: Conversation,
        message: str
    ) -> bool:
        """Check if conversation should be escalated based on triggers."""
        # Escalation triggers
        escalation_keywords = [
            "emergency", "urgent", "complaint", "speak to human",
            "talk to person", "this isn't working", "frustrated",
            "angry", "lawsuit", "sue", "terrible service"
        ]
        
        message_lower = message.lower()
        
        # Check for escalation keywords
        if any(keyword in message_lower for keyword in escalation_keywords):
            return True
        
        # Check conversation length (too many back-and-forth)
        if len(conversation.messages) > 20:
            return True
        
        # Check for repeated similar questions
        if len(conversation.messages) >= 6:
            recent_messages = [msg.content for msg in conversation.messages[-6:] if msg.type == MessageType.USER]
            if len(set(recent_messages)) <= 2:  # Repeated similar questions
                return True
        
        return False
    
    async def _escalate_conversation(
        self,
        conversation: Conversation,
        reason: str,
        priority: str = "normal"
    ) -> ConversationMessage:
        """Escalate conversation to human agent."""
        try:
            # Update conversation state
            conversation.state = ConversationState.ESCALATED
            conversation.escalated_at = datetime.utcnow()
            
            # Request agent assignment
            agent_assigned = await self.escalation_manager.request_agent(
                conversation, reason, priority
            )
            
            if agent_assigned:
                escalation_message = "I'm connecting you with one of our healthcare specialists who can better assist you. Please wait a moment."
            else:
                escalation_message = "I'm placing you in queue for our next available healthcare specialist. Someone will be with you shortly."
            
            # Create escalation message
            escalation_msg = ConversationMessage(
                id=str(uuid.uuid4()),
                conversation_id=conversation.id,
                type=MessageType.ESCALATION,
                content=escalation_message,
                timestamp=datetime.utcnow(),
                metadata={"reason": reason, "priority": priority}
            )
            
            conversation.messages.append(escalation_msg)
            
            # Save conversation
            await self._save_conversation(conversation)
            
            # Record metrics
            self.metrics_collector.record_conversation_escalated(
                conversation.channel, reason
            )
            
            logger.info(
                "Conversation escalated",
                conversation_id=conversation.id,
                reason=reason,
                priority=priority
            )
            
            return escalation_msg
            
        except Exception as e:
            logger.error(
                "Failed to escalate conversation",
                conversation_id=conversation.id,
                error=str(e)
            )
            raise
    
    async def _cleanup_abandoned_conversations(self) -> None:
        """Background task to cleanup abandoned conversations."""
        while True:
            try:
                current_time = datetime.utcnow()
                abandoned_conversations = []
                
                for conv_id, conversation in self.active_conversations.items():
                    # Check if conversation has been inactive
                    if (current_time - conversation.updated_at) > self.conversation_timeout:
                        abandoned_conversations.append(conv_id)
                
                # Mark as abandoned and remove from active
                for conv_id in abandoned_conversations:
                    conversation = self.active_conversations[conv_id]
                    conversation.state = ConversationState.ABANDONED
                    await self._save_conversation(conversation)
                    del self.active_conversations[conv_id]
                
                if abandoned_conversations:
                    logger.info(
                        "Cleaned up abandoned conversations",
                        count=len(abandoned_conversations)
                    )
                
                # Sleep for 5 minutes before next cleanup
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error("Error in conversation cleanup", error=str(e))
                await asyncio.sleep(60)  # Shorter sleep on error
    
    async def _monitor_escalation_timeouts(self) -> None:
        """Background task to monitor escalation timeouts."""
        while True:
            try:
                current_time = datetime.utcnow()
                
                for conversation in self.active_conversations.values():
                    if (conversation.state == ConversationState.ESCALATED and 
                        conversation.escalated_at and
                        (current_time - conversation.escalated_at) > self.escalation_timeout):
                        
                        # Notify escalation manager of timeout
                        await self.escalation_manager.handle_escalation_timeout(conversation)
                
                # Check every minute
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error("Error in escalation timeout monitoring", error=str(e))
                await asyncio.sleep(60)
    
    async def cleanup(self) -> None:
        """Cleanup orchestrator resources."""
        logger.info("Cleaning up chat orchestrator...")
        
        # Save all active conversations
        for conversation in self.active_conversations.values():
            await self._save_conversation(conversation)
        
        # Cleanup components
        if self.ai_engine:
            await self.ai_engine.cleanup()
        
        if self.context_manager:
            await self.context_manager.cleanup()
        
        if self.escalation_manager:
            await self.escalation_manager.cleanup()
        
        logger.info("Chat orchestrator cleanup complete") 