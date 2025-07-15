"""
Context Manager - Manages conversation context and user profiles for MedinovAI
Handles user profiles, conversation context, preferences, and session management
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

import structlog
from pydantic import BaseModel

from utils.config import Settings
from utils.database import get_database

logger = structlog.get_logger(__name__)


class UserProfile(BaseModel):
    """User profile model with healthcare-specific information."""
    user_id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    date_of_birth: Optional[str] = None
    preferred_language: str = "en"
    communication_preferences: Dict[str, bool] = {
        "sms": True,
        "voice": True,
        "email": False
    }
    
    # Healthcare-specific fields (anonymized/aggregated)
    age_group: Optional[str] = None  # e.g., "18-25", "26-35"
    general_conditions: List[str] = []  # e.g., ["diabetes_management", "hypertension"]
    care_team_ids: List[str] = []
    insurance_provider: Optional[str] = None
    
    # Conversation preferences
    preferred_communication_style: str = "professional"  # professional, casual, detailed
    needs_interpreter: bool = False
    accessibility_needs: List[str] = []
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    last_conversation_at: Optional[datetime] = None
    total_conversations: int = 0
    satisfaction_scores: List[int] = []


class ConversationContext(BaseModel):
    """Conversation context model."""
    conversation_id: str
    current_topic: Optional[str] = None
    intent_history: List[str] = []
    mentioned_conditions: List[str] = []
    mentioned_medications: List[str] = []
    mentioned_symptoms: List[str] = []
    escalation_reasons: List[str] = []
    
    # Conversation flow tracking
    questions_asked: List[str] = []
    information_provided: List[str] = []
    next_suggested_actions: List[str] = []
    
    # Sentiment and urgency tracking
    sentiment_scores: List[float] = []
    urgency_level: str = "normal"  # low, normal, high, urgent
    
    # Session information
    session_start: datetime
    last_activity: datetime
    total_messages: int = 0
    avg_response_time: float = 0.0


class ContextManager:
    """
    Manages conversation context and user profiles for personalized healthcare interactions.
    Provides context-aware responses while maintaining HIPAA compliance.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.database = None
        
        # In-memory context cache for active conversations
        self.conversation_contexts: Dict[str, ConversationContext] = {}
        self.user_profiles: Dict[str, UserProfile] = {}
        
        # Context retention settings
        self.context_retention_hours = 24
        self.profile_cache_hours = 6
        
        logger.info("Context manager initialized")
    
    async def initialize(self) -> None:
        """Initialize context manager."""
        try:
            # Initialize database connection
            self.database = await get_database()
            
            # Load frequently accessed user profiles
            await self._preload_active_profiles()
            
            logger.info("Context manager initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize context manager", error=str(e))
            raise
    
    async def load_user_context(self, conversation: Any) -> None:
        """Load user context for conversation."""
        try:
            user_id = conversation.user_id
            
            # Load or create user profile
            user_profile = await self._get_user_profile(user_id)
            if not user_profile:
                user_profile = await self._create_user_profile(user_id, conversation)
            
            # Create conversation context
            context = ConversationContext(
                conversation_id=conversation.id,
                session_start=datetime.utcnow(),
                last_activity=datetime.utcnow()
            )
            
            # Store in cache
            self.conversation_contexts[conversation.id] = context
            
            # Update conversation object with context
            conversation.context = {
                "user_profile": user_profile.dict(),
                "conversation_context": context.dict()
            }
            
            # Update user profile last conversation
            user_profile.last_conversation_at = datetime.utcnow()
            user_profile.total_conversations += 1
            await self._save_user_profile(user_profile)
            
            logger.info(
                "User context loaded",
                conversation_id=conversation.id,
                user_id=user_id,
                language=user_profile.preferred_language
            )
            
        except Exception as e:
            logger.error(
                "Failed to load user context",
                conversation_id=conversation.id,
                error=str(e)
            )
            # Continue with empty context
            conversation.context = {}
    
    async def update_context(self, conversation: Any, message: Any) -> None:
        """Update conversation context with new message."""
        try:
            context = self.conversation_contexts.get(conversation.id)
            if not context:
                logger.warning(
                    "No context found for conversation",
                    conversation_id=conversation.id
                )
                return
            
            # Update activity tracking
            context.last_activity = datetime.utcnow()
            context.total_messages += 1
            
            # Extract and track intents from message
            if message.type.value == "user":
                intent = await self._extract_intent(message.content)
                if intent:
                    context.intent_history.append(intent)
                    context.current_topic = intent
                
                # Extract medical entities
                await self._extract_medical_entities(message.content, context)
                
                # Analyze sentiment and urgency
                sentiment = await self._analyze_sentiment(message.content)
                context.sentiment_scores.append(sentiment)
                
                urgency = await self._detect_urgency(message.content)
                if urgency > context.urgency_level:
                    context.urgency_level = urgency
            
            # Update conversation object
            conversation.context["conversation_context"] = context.dict()
            
            logger.debug(
                "Context updated",
                conversation_id=conversation.id,
                current_topic=context.current_topic,
                urgency_level=context.urgency_level
            )
            
        except Exception as e:
            logger.error(
                "Failed to update context",
                conversation_id=conversation.id,
                error=str(e)
            )
    
    async def get_conversation_summary(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation summary for handoff or escalation."""
        context = self.conversation_contexts.get(conversation_id)
        if not context:
            return None
        
        summary = {
            "conversation_id": conversation_id,
            "duration_minutes": (
                datetime.utcnow() - context.session_start
            ).total_seconds() / 60,
            "total_messages": context.total_messages,
            "current_topic": context.current_topic,
            "intent_history": context.intent_history[-5:],  # Last 5 intents
            "urgency_level": context.urgency_level,
            "key_conditions": context.mentioned_conditions,
            "key_symptoms": context.mentioned_symptoms,
            "escalation_reasons": context.escalation_reasons,
            "avg_sentiment": (
                sum(context.sentiment_scores) / len(context.sentiment_scores)
                if context.sentiment_scores else 0.5
            )
        }
        
        return summary
    
    async def update_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> bool:
        """Update user preferences."""
        try:
            user_profile = await self._get_user_profile(user_id)
            if not user_profile:
                return False
            
            # Update allowed preferences
            if "preferred_language" in preferences:
                user_profile.preferred_language = preferences["preferred_language"]
            
            if "communication_preferences" in preferences:
                user_profile.communication_preferences.update(
                    preferences["communication_preferences"]
                )
            
            if "preferred_communication_style" in preferences:
                user_profile.preferred_communication_style = preferences["preferred_communication_style"]
            
            user_profile.updated_at = datetime.utcnow()
            await self._save_user_profile(user_profile)
            
            logger.info(
                "User preferences updated",
                user_id=user_id,
                preferences=preferences
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to update user preferences",
                user_id=user_id,
                error=str(e)
            )
            return False
    
    async def record_satisfaction(
        self,
        conversation_id: str,
        satisfaction_score: int
    ) -> None:
        """Record conversation satisfaction score."""
        try:
            context = self.conversation_contexts.get(conversation_id)
            if not context:
                return
            
            # Find user profile from active conversations
            for user_id, profile in self.user_profiles.items():
                if profile.last_conversation_at:
                    # Update satisfaction scores
                    profile.satisfaction_scores.append(satisfaction_score)
                    
                    # Keep only last 20 scores
                    if len(profile.satisfaction_scores) > 20:
                        profile.satisfaction_scores = profile.satisfaction_scores[-20:]
                    
                    await self._save_user_profile(profile)
                    break
            
            logger.info(
                "Satisfaction recorded",
                conversation_id=conversation_id,
                score=satisfaction_score
            )
            
        except Exception as e:
            logger.error(
                "Failed to record satisfaction",
                conversation_id=conversation_id,
                error=str(e)
            )
    
    # Private methods
    
    async def _get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile from cache or database."""
        # Check cache first
        if user_id in self.user_profiles:
            profile = self.user_profiles[user_id]
            
            # Check if cache is still valid
            if (datetime.utcnow() - profile.updated_at).hours < self.profile_cache_hours:
                return profile
        
        # Load from database
        # In production, this would query the actual database
        # For now, return None if not in cache
        return None
    
    async def _create_user_profile(
        self,
        user_id: str,
        conversation: Any
    ) -> UserProfile:
        """Create new user profile."""
        profile = UserProfile(
            user_id=user_id,
            preferred_language=conversation.language,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Cache the profile
        self.user_profiles[user_id] = profile
        
        # Save to database
        await self._save_user_profile(profile)
        
        logger.info("New user profile created", user_id=user_id)
        
        return profile
    
    async def _save_user_profile(self, profile: UserProfile) -> None:
        """Save user profile to database."""
        # Update cache
        self.user_profiles[profile.user_id] = profile
        
        # In production, save to database
        # await self.database.save_user_profile(profile)
        pass
    
    async def _preload_active_profiles(self) -> None:
        """Preload frequently accessed user profiles."""
        # In production, this would load recent active users
        # For now, this is a placeholder
        pass
    
    async def _extract_intent(self, message: str) -> Optional[str]:
        """Extract intent from user message."""
        # Simple intent extraction - in production, use NLU models
        intents = {
            "appointment": ["appointment", "schedule", "book", "reschedule"],
            "prescription": ["prescription", "medication", "refill", "drug"],
            "symptoms": ["symptom", "pain", "hurt", "feel", "sick"],
            "billing": ["bill", "payment", "insurance", "cost", "charge"],
            "results": ["result", "test", "lab", "report"],
            "general_info": ["what", "how", "when", "where", "why"]
        }
        
        message_lower = message.lower()
        
        for intent, keywords in intents.items():
            if any(keyword in message_lower for keyword in keywords):
                return intent
        
        return None
    
    async def _extract_medical_entities(
        self,
        message: str,
        context: ConversationContext
    ) -> None:
        """Extract medical entities from message."""
        # Simple medical entity extraction
        # In production, use medical NER models
        
        # Common symptoms
        symptoms = [
            "headache", "fever", "cough", "pain", "nausea", "fatigue",
            "dizziness", "shortness of breath", "chest pain", "rash"
        ]
        
        # Common conditions
        conditions = [
            "diabetes", "hypertension", "asthma", "arthritis", "depression",
            "anxiety", "migraine", "allergies", "back pain"
        ]
        
        message_lower = message.lower()
        
        # Extract symptoms
        for symptom in symptoms:
            if symptom in message_lower and symptom not in context.mentioned_symptoms:
                context.mentioned_symptoms.append(symptom)
        
        # Extract conditions
        for condition in conditions:
            if condition in message_lower and condition not in context.mentioned_conditions:
                context.mentioned_conditions.append(condition)
    
    async def _analyze_sentiment(self, message: str) -> float:
        """Analyze sentiment of message (0.0 = negative, 1.0 = positive)."""
        # Simple sentiment analysis - in production, use sentiment models
        positive_words = ["good", "great", "excellent", "happy", "satisfied", "better"]
        negative_words = ["bad", "terrible", "awful", "frustrated", "angry", "worse"]
        
        message_lower = message.lower()
        
        positive_count = sum(1 for word in positive_words if word in message_lower)
        negative_count = sum(1 for word in negative_words if word in message_lower)
        
        if positive_count > negative_count:
            return 0.7
        elif negative_count > positive_count:
            return 0.3
        else:
            return 0.5
    
    async def _detect_urgency(self, message: str) -> str:
        """Detect urgency level from message."""
        urgent_keywords = [
            "emergency", "urgent", "severe", "serious", "critical",
            "chest pain", "can't breathe", "bleeding", "unconscious"
        ]
        
        high_keywords = [
            "pain", "hurt", "worried", "concerned", "problem",
            "getting worse", "need help"
        ]
        
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in urgent_keywords):
            return "urgent"
        elif any(keyword in message_lower for keyword in high_keywords):
            return "high"
        else:
            return "normal"
    
    async def cleanup(self) -> None:
        """Cleanup context manager resources."""
        logger.info("Cleaning up context manager...")
        
        # Save all cached profiles
        for profile in self.user_profiles.values():
            await self._save_user_profile(profile)
        
        # Clear caches
        self.conversation_contexts.clear()
        self.user_profiles.clear()
        
        logger.info("Context manager cleanup complete") 