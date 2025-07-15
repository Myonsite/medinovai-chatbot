"""
Database Models and Operations for MedinovAI
HIPAA-compliant database schema with audit logging and encryption
"""

import asyncio
from datetime import datetime
from typing import List, Optional, Any, Dict

import structlog
from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, JSON, 
    ForeignKey, Enum as SQLEnum, Index, BigInteger, Float
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID
import uuid

from utils.config import get_settings

logger = structlog.get_logger(__name__)

Base = declarative_base()


class User(Base):
    """User model for patients and staff."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(20), unique=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    encrypted_name = Column(Text, nullable=True)  # Encrypted PHI
    
    # Demographics (anonymized)
    age_group = Column(String(20), nullable=True)  # e.g., "18-25"
    preferred_language = Column(String(10), default="en")
    
    # Authentication
    phone_verified = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    last_login_at = Column(DateTime, nullable=True)
    
    # Preferences
    communication_preferences = Column(JSON, default=dict)
    accessibility_needs = Column(JSON, default=list)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user")
    
    __table_args__ = (
        Index('idx_users_phone', 'phone_number'),
        Index('idx_users_email', 'email'),
    )


class Agent(Base):
    """Agent model for healthcare staff."""
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(String(50), unique=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True)
    
    # Agent capabilities
    languages = Column(JSON, default=["en"])
    specialties = Column(JSON, default=list)  # billing, clinical, pharmacy
    max_concurrent_chats = Column(Integer, default=5)
    
    # Status and availability
    status = Column(SQLEnum("available", "busy", "away", "offline", name="agent_status"), default="offline")
    last_activity = Column(DateTime, nullable=True)
    
    # Integration IDs
    mattermost_user_id = Column(String(50), nullable=True)
    
    # Performance tracking
    total_conversations = Column(Integer, default=0)
    avg_response_time_minutes = Column(Float, default=0.0)
    satisfaction_score = Column(Float, default=0.0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    assigned_conversations = relationship("Conversation", back_populates="assigned_agent")
    escalation_tickets = relationship("EscalationTicket", back_populates="assigned_agent")


class Conversation(Base):
    """Conversation model with full audit trail."""
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    
    # Conversation details
    channel = Column(SQLEnum("web", "sms", "voice", "mattermost", name="conversation_channel"))
    language = Column(String(10), default="en")
    state = Column(
        SQLEnum("active", "waiting_for_user", "escalated", "completed", "abandoned", name="conversation_state"),
        default="active"
    )
    
    # Context and metadata
    context_data = Column(JSON, default=dict)
    metadata = Column(JSON, default=dict)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    escalated_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Quality metrics
    satisfaction_score = Column(Integer, nullable=True)
    total_messages = Column(Integer, default=0)
    ai_resolution = Column(Boolean, default=True)  # False if escalated
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    assigned_agent = relationship("Agent", back_populates="assigned_conversations")
    messages = relationship("ConversationMessage", back_populates="conversation")
    escalation_tickets = relationship("EscalationTicket", back_populates="conversation")
    
    __table_args__ = (
        Index('idx_conversations_user', 'user_id'),
        Index('idx_conversations_agent', 'assigned_agent_id'),
        Index('idx_conversations_state', 'state'),
        Index('idx_conversations_created', 'created_at'),
    )


class ConversationMessage(Base):
    """Individual messages within conversations."""
    __tablename__ = "conversation_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    
    # Message details
    message_type = Column(SQLEnum("user", "assistant", "system", "escalation", name="message_type"))
    content = Column(Text, nullable=False)
    encrypted_content = Column(Text, nullable=True)  # Encrypted version if PHI detected
    
    # PHI tracking
    phi_detected = Column(Boolean, default=False)
    redacted_content = Column(Text, nullable=True)
    
    # Attribution
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    __table_args__ = (
        Index('idx_messages_conversation', 'conversation_id'),
        Index('idx_messages_timestamp', 'timestamp'),
        Index('idx_messages_phi', 'phi_detected'),
    )


class EscalationTicket(Base):
    """Escalation tickets for human agent assignment."""
    __tablename__ = "escalation_tickets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    assigned_agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    
    # Escalation details
    priority = Column(SQLEnum("low", "normal", "high", "urgent", name="escalation_priority"), default="normal")
    reason = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status tracking
    status = Column(SQLEnum("pending", "assigned", "in_progress", "resolved", "escalated", name="ticket_status"), default="pending")
    queue_position = Column(Integer, nullable=True)
    
    # SLA tracking
    response_sla_minutes = Column(Integer, default=15)
    resolution_sla_minutes = Column(Integer, default=60)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    assigned_at = Column(DateTime, nullable=True)
    first_response_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Context
    conversation_summary = Column(JSON, default=dict)
    user_context = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    notes = Column(JSON, default=list)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="escalation_tickets")
    assigned_agent = relationship("Agent", back_populates="escalation_tickets")
    
    __table_args__ = (
        Index('idx_tickets_conversation', 'conversation_id'),
        Index('idx_tickets_agent', 'assigned_agent_id'),
        Index('idx_tickets_status', 'status'),
        Index('idx_tickets_priority', 'priority'),
        Index('idx_tickets_created', 'created_at'),
    )


class AuditLog(Base):
    """HIPAA-compliant audit logging."""
    __tablename__ = "audit_logs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Event details
    event_type = Column(String(100), nullable=False)
    event_category = Column(String(50), nullable=False)  # access, modification, security
    severity = Column(SQLEnum("low", "medium", "high", "critical", name="audit_severity"), default="low")
    
    # Context
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    
    # Technical details
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(100), nullable=True)
    
    # Event data
    event_data = Column(JSON, default=dict)
    affected_resources = Column(JSON, default=list)
    
    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Compliance
    phi_accessed = Column(Boolean, default=False)
    retention_until = Column(DateTime, nullable=True)  # For compliance retention
    
    __table_args__ = (
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_event_type', 'event_type'),
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_agent', 'agent_id'),
        Index('idx_audit_phi', 'phi_accessed'),
        Index('idx_audit_severity', 'severity'),
    )


class UserProfile(Base):
    """Extended user profile with healthcare-specific data."""
    __tablename__ = "user_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    
    # Healthcare context (anonymized/aggregated)
    general_conditions = Column(JSON, default=list)  # Aggregated categories
    care_team_ids = Column(JSON, default=list)
    insurance_provider = Column(String(100), nullable=True)
    
    # Communication preferences
    preferred_communication_style = Column(String(50), default="professional")
    needs_interpreter = Column(Boolean, default=False)
    
    # Conversation history summary
    total_conversations = Column(Integer, default=0)
    avg_satisfaction_score = Column(Float, nullable=True)
    last_conversation_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_profile_user', 'user_id'),
    )


class SystemConfiguration(Base):
    """System configuration and feature flags."""
    __tablename__ = "system_configuration"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(200), unique=True, nullable=False)
    value = Column(JSON, nullable=False)
    value_type = Column(String(50), nullable=False)  # string, int, bool, json
    
    # Metadata
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    is_encrypted = Column(Boolean, default=False)
    
    # Change tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(255), nullable=True)
    
    __table_args__ = (
        Index('idx_config_key', 'key'),
        Index('idx_config_category', 'category'),
    )


# Database session management
async_engine = None
AsyncSessionLocal = None


async def init_database():
    """Initialize database connection and create tables."""
    global async_engine, AsyncSessionLocal
    
    settings = get_settings()
    
    try:
        # Create async engine
        async_engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=20,
            pool_timeout=settings.database_timeout,
            echo=settings.development_mode
        )
        
        # Create session factory
        AsyncSessionLocal = sessionmaker(
            bind=async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create all tables
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


async def get_database() -> AsyncSession:
    """Get database session."""
    if not AsyncSessionLocal:
        await init_database()
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_database_health() -> Dict[str, Any]:
    """Check database health for monitoring."""
    try:
        async with AsyncSessionLocal() as session:
            # Test basic connectivity
            result = await session.execute("SELECT 1")
            result.scalar()
            
            # Get some basic stats
            users_count = await session.execute("SELECT COUNT(*) FROM users")
            conversations_count = await session.execute("SELECT COUNT(*) FROM conversations")
            
            return {
                "status": "healthy",
                "connected": True,
                "response_time_ms": 0,  # Would measure actual response time
                "stats": {
                    "total_users": users_count.scalar(),
                    "total_conversations": conversations_count.scalar()
                }
            }
            
    except Exception as e:
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e)
        }


async def create_audit_entry(
    event_type: str,
    event_category: str,
    severity: str = "low",
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    event_data: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None,
    phi_accessed: bool = False
) -> None:
    """Create audit log entry for HIPAA compliance."""
    try:
        async with AsyncSessionLocal() as session:
            audit_entry = AuditLog(
                event_type=event_type,
                event_category=event_category,
                severity=severity,
                user_id=user_id,
                agent_id=agent_id,
                conversation_id=conversation_id,
                event_data=event_data or {},
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
                phi_accessed=phi_accessed,
                retention_until=datetime.utcnow().replace(year=datetime.utcnow().year + 7)  # 7 year retention
            )
            
            session.add(audit_entry)
            await session.commit()
            
    except Exception as e:
        logger.error("Failed to create audit entry", error=str(e))


async def cleanup_old_data():
    """Cleanup old data based on retention policies."""
    try:
        async with AsyncSessionLocal() as session:
            current_time = datetime.utcnow()
            
            # Delete old audit logs past retention period
            await session.execute(
                "DELETE FROM audit_logs WHERE retention_until < :current_time",
                {"current_time": current_time}
            )
            
            # Archive old conversations (older than 2 years)
            cutoff_date = current_time.replace(year=current_time.year - 2)
            await session.execute(
                "UPDATE conversations SET archived = true WHERE created_at < :cutoff_date AND archived = false",
                {"cutoff_date": cutoff_date}
            )
            
            await session.commit()
            logger.info("Database cleanup completed")
            
    except Exception as e:
        logger.error("Database cleanup failed", error=str(e)) 