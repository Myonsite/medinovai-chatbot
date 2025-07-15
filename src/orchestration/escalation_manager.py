"""
Escalation Manager - Handles conversation escalation and human agent assignment
Manages escalation to human agents, Mattermost integration, and CSR workflows
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

import structlog
from pydantic import BaseModel

from utils.config import Settings
from adapters.mattermost_adapter import MattermostAdapter

logger = structlog.get_logger(__name__)


class EscalationPriority(str, Enum):
    """Escalation priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AgentStatus(str, Enum):
    """Agent availability status."""
    AVAILABLE = "available"
    BUSY = "busy"
    AWAY = "away"
    OFFLINE = "offline"


class EscalationTicket(BaseModel):
    """Escalation ticket model."""
    id: str
    conversation_id: str
    user_id: str
    priority: EscalationPriority
    reason: str
    category: str
    description: str
    channel: str
    language: str
    
    # Assignment information
    assigned_agent_id: Optional[str] = None
    assigned_at: Optional[datetime] = None
    queue_position: Optional[int] = None
    
    # Context information
    conversation_summary: Dict[str, Any] = {}
    user_context: Dict[str, Any] = {}
    
    # Timing information
    created_at: datetime
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # SLA tracking
    response_sla_minutes: int = 15  # Default 15 minutes
    resolution_sla_minutes: int = 60  # Default 1 hour
    
    # Status tracking
    status: str = "pending"  # pending, assigned, in_progress, resolved, escalated
    tags: List[str] = []
    notes: List[str] = []


class Agent(BaseModel):
    """Healthcare agent model."""
    id: str
    name: str
    email: str
    mattermost_user_id: Optional[str] = None
    
    # Availability
    status: AgentStatus = AgentStatus.OFFLINE
    last_activity: Optional[datetime] = None
    
    # Capabilities
    languages: List[str] = ["en"]
    specialties: List[str] = []  # e.g., ["billing", "clinical", "pharmacy"]
    max_concurrent_chats: int = 5
    
    # Current workload
    active_conversations: List[str] = []
    current_load: int = 0
    
    # Performance metrics
    avg_response_time_minutes: float = 0.0
    resolution_rate: float = 0.0
    satisfaction_score: float = 0.0
    total_conversations: int = 0


class EscalationManager:
    """
    Manages conversation escalation to human agents.
    Handles agent assignment, workload balancing, and SLA tracking.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.mattermost: Optional[MattermostAdapter] = None
        
        # Active escalation tracking
        self.escalation_queue: List[EscalationTicket] = []
        self.active_tickets: Dict[str, EscalationTicket] = {}
        self.agents: Dict[str, Agent] = {}
        
        # Queue management
        self.max_queue_size = 100
        self.auto_escalation_enabled = settings.auto_escalation_enabled
        
        logger.info("Escalation manager initialized")
    
    async def initialize(self) -> None:
        """Initialize escalation manager."""
        try:
            # Initialize Mattermost adapter if enabled
            if self.settings.mattermost_enabled:
                self.mattermost = MattermostAdapter(self.settings)
                await self.mattermost.initialize()
            
            # Load agent information
            await self._load_agents()
            
            # Start background tasks
            asyncio.create_task(self._monitor_agent_presence())
            asyncio.create_task(self._process_escalation_queue())
            asyncio.create_task(self._monitor_sla_breaches())
            
            logger.info("Escalation manager initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize escalation manager", error=str(e))
            raise
    
    async def request_agent(
        self,
        conversation: Any,
        reason: str,
        priority: str = "normal"
    ) -> bool:
        """Request human agent for conversation."""
        try:
            # Create escalation ticket
            ticket = EscalationTicket(
                id=str(uuid.uuid4()),
                conversation_id=conversation.id,
                user_id=conversation.user_id,
                priority=EscalationPriority(priority),
                reason=reason,
                category=self._categorize_escalation(reason),
                description=f"Escalation requested: {reason}",
                channel=conversation.channel,
                language=conversation.language,
                created_at=datetime.utcnow(),
                conversation_summary=conversation.context.get("conversation_context", {}),
                user_context=conversation.context.get("user_profile", {})
            )
            
            # Set SLA based on priority
            ticket.response_sla_minutes = self._get_response_sla(ticket.priority)
            ticket.resolution_sla_minutes = self._get_resolution_sla(ticket.priority)
            
            # Try immediate assignment for urgent cases
            if ticket.priority in [EscalationPriority.HIGH, EscalationPriority.URGENT]:
                agent = await self._find_available_agent(ticket)
                if agent:
                    await self._assign_ticket_to_agent(ticket, agent)
                    return True
            
            # Add to escalation queue
            await self._add_to_queue(ticket)
            
            # Notify Mattermost
            if self.mattermost:
                await self._notify_escalation_team(ticket)
            
            logger.info(
                "Agent requested",
                conversation_id=conversation.id,
                ticket_id=ticket.id,
                priority=priority,
                reason=reason
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to request agent",
                conversation_id=conversation.id,
                error=str(e)
            )
            return False
    
    async def assign_to_agent(
        self,
        conversation: Any,
        agent_id: str
    ) -> bool:
        """Assign conversation to specific agent."""
        try:
            # Find existing ticket or create new one
            ticket = next(
                (t for t in self.active_tickets.values() 
                 if t.conversation_id == conversation.id),
                None
            )
            
            if not ticket:
                # Create new ticket for manual assignment
                ticket = EscalationTicket(
                    id=str(uuid.uuid4()),
                    conversation_id=conversation.id,
                    user_id=conversation.user_id,
                    priority=EscalationPriority.NORMAL,
                    reason="Manual assignment",
                    category="manual",
                    description="Manually assigned to agent",
                    channel=conversation.channel,
                    language=conversation.language,
                    created_at=datetime.utcnow()
                )
            
            # Find agent
            agent = self.agents.get(agent_id)
            if not agent:
                logger.error("Agent not found", agent_id=agent_id)
                return False
            
            # Check agent availability
            if agent.status not in [AgentStatus.AVAILABLE, AgentStatus.BUSY]:
                logger.warning("Agent not available", agent_id=agent_id, status=agent.status)
                return False
            
            # Check agent capacity
            if agent.current_load >= agent.max_concurrent_chats:
                logger.warning("Agent at capacity", agent_id=agent_id, load=agent.current_load)
                return False
            
            # Assign ticket
            await self._assign_ticket_to_agent(ticket, agent)
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to assign to agent",
                conversation_id=conversation.id,
                agent_id=agent_id,
                error=str(e)
            )
            return False
    
    async def handle_escalation_timeout(self, conversation: Any) -> None:
        """Handle escalation timeout."""
        try:
            ticket = next(
                (t for t in self.active_tickets.values() 
                 if t.conversation_id == conversation.id),
                None
            )
            
            if not ticket:
                return
            
            # Escalate priority
            if ticket.priority == EscalationPriority.NORMAL:
                ticket.priority = EscalationPriority.HIGH
            elif ticket.priority == EscalationPriority.HIGH:
                ticket.priority = EscalationPriority.URGENT
            
            # Update SLA
            ticket.response_sla_minutes = self._get_response_sla(ticket.priority)
            
            # Try reassignment
            if not ticket.assigned_agent_id:
                agent = await self._find_available_agent(ticket)
                if agent:
                    await self._assign_ticket_to_agent(ticket, agent)
            
            # Notify escalation team
            if self.mattermost:
                await self._notify_escalation_timeout(ticket)
            
            logger.warning(
                "Escalation timeout handled",
                conversation_id=conversation.id,
                ticket_id=ticket.id,
                new_priority=ticket.priority
            )
            
        except Exception as e:
            logger.error(
                "Failed to handle escalation timeout",
                conversation_id=conversation.id,
                error=str(e)
            )
    
    async def update_agent_status(
        self,
        agent_id: str,
        status: AgentStatus
    ) -> bool:
        """Update agent availability status."""
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                return False
            
            old_status = agent.status
            agent.status = status
            agent.last_activity = datetime.utcnow()
            
            # If agent went offline, reassign their tickets
            if status == AgentStatus.OFFLINE and old_status != AgentStatus.OFFLINE:
                await self._reassign_agent_tickets(agent_id)
            
            logger.info(
                "Agent status updated",
                agent_id=agent_id,
                old_status=old_status,
                new_status=status
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to update agent status",
                agent_id=agent_id,
                error=str(e)
            )
            return False
    
    async def get_escalation_status(
        self,
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get escalation status for conversation."""
        ticket = next(
            (t for t in self.active_tickets.values() 
             if t.conversation_id == conversation_id),
            None
        )
        
        if not ticket:
            return None
        
        # Calculate wait times
        wait_time = (
            datetime.utcnow() - ticket.created_at
        ).total_seconds() / 60
        
        response_sla_remaining = max(
            0, ticket.response_sla_minutes - wait_time
        )
        
        return {
            "ticket_id": ticket.id,
            "status": ticket.status,
            "priority": ticket.priority,
            "queue_position": ticket.queue_position,
            "assigned_agent": ticket.assigned_agent_id,
            "wait_time_minutes": round(wait_time, 1),
            "response_sla_remaining_minutes": round(response_sla_remaining, 1),
            "estimated_wait_minutes": await self._estimate_wait_time(ticket)
        }
    
    # Private methods
    
    async def _load_agents(self) -> None:
        """Load agent information."""
        # In production, load from database
        # For now, create sample agents
        sample_agents = [
            Agent(
                id="agent_001",
                name="Sarah Johnson",
                email="sarah.johnson@myonsitehealthcare.com",
                status=AgentStatus.AVAILABLE,
                languages=["en", "es"],
                specialties=["general", "billing"],
                max_concurrent_chats=5
            ),
            Agent(
                id="agent_002",
                name="Dr. Michael Chen",
                email="michael.chen@myonsitehealthcare.com",
                status=AgentStatus.AVAILABLE,
                languages=["en", "zh"],
                specialties=["clinical", "pharmacy"],
                max_concurrent_chats=3
            )
        ]
        
        for agent in sample_agents:
            self.agents[agent.id] = agent
        
        logger.info(f"Loaded {len(self.agents)} agents")
    
    async def _find_available_agent(
        self,
        ticket: EscalationTicket
    ) -> Optional[Agent]:
        """Find best available agent for ticket."""
        available_agents = []
        
        for agent in self.agents.values():
            # Check availability
            if agent.status != AgentStatus.AVAILABLE:
                continue
            
            # Check capacity
            if agent.current_load >= agent.max_concurrent_chats:
                continue
            
            # Check language compatibility
            if ticket.language not in agent.languages:
                continue
            
            # Calculate score based on specialties and workload
            score = 0
            
            # Specialty match bonus
            if ticket.category in agent.specialties:
                score += 10
            
            # Lower workload bonus
            score += (agent.max_concurrent_chats - agent.current_load) * 2
            
            # Performance bonus
            score += agent.satisfaction_score * 5
            
            available_agents.append((agent, score))
        
        # Sort by score and return best agent
        if available_agents:
            available_agents.sort(key=lambda x: x[1], reverse=True)
            return available_agents[0][0]
        
        return None
    
    async def _assign_ticket_to_agent(
        self,
        ticket: EscalationTicket,
        agent: Agent
    ) -> None:
        """Assign ticket to agent."""
        # Update ticket
        ticket.assigned_agent_id = agent.id
        ticket.assigned_at = datetime.utcnow()
        ticket.status = "assigned"
        
        # Update agent
        agent.current_load += 1
        agent.active_conversations.append(ticket.conversation_id)
        
        # Add to active tickets
        self.active_tickets[ticket.id] = ticket
        
        # Remove from queue if present
        self.escalation_queue = [
            t for t in self.escalation_queue 
            if t.id != ticket.id
        ]
        
        # Notify agent via Mattermost
        if self.mattermost:
            await self._notify_agent_assignment(ticket, agent)
        
        logger.info(
            "Ticket assigned to agent",
            ticket_id=ticket.id,
            agent_id=agent.id,
            conversation_id=ticket.conversation_id
        )
    
    async def _add_to_queue(self, ticket: EscalationTicket) -> None:
        """Add ticket to escalation queue."""
        if len(self.escalation_queue) >= self.max_queue_size:
            logger.warning("Escalation queue full, dropping oldest ticket")
            self.escalation_queue.pop(0)
        
        # Insert based on priority
        priority_order = {
            EscalationPriority.URGENT: 0,
            EscalationPriority.HIGH: 1,
            EscalationPriority.NORMAL: 2,
            EscalationPriority.LOW: 3
        }
        
        insert_index = len(self.escalation_queue)
        for i, queued_ticket in enumerate(self.escalation_queue):
            if priority_order[ticket.priority] < priority_order[queued_ticket.priority]:
                insert_index = i
                break
        
        self.escalation_queue.insert(insert_index, ticket)
        
        # Update queue positions
        for i, queued_ticket in enumerate(self.escalation_queue):
            queued_ticket.queue_position = i + 1
        
        logger.info(
            "Ticket added to queue",
            ticket_id=ticket.id,
            position=ticket.queue_position,
            queue_size=len(self.escalation_queue)
        )
    
    async def _process_escalation_queue(self) -> None:
        """Background task to process escalation queue."""
        while True:
            try:
                if not self.escalation_queue:
                    await asyncio.sleep(30)
                    continue
                
                # Process tickets in queue
                for ticket in self.escalation_queue[:]:
                    agent = await self._find_available_agent(ticket)
                    if agent:
                        await self._assign_ticket_to_agent(ticket, agent)
                
                await asyncio.sleep(15)  # Check every 15 seconds
                
            except Exception as e:
                logger.error("Error in escalation queue processing", error=str(e))
                await asyncio.sleep(60)
    
    async def _monitor_agent_presence(self) -> None:
        """Monitor agent presence and update status."""
        while True:
            try:
                if self.mattermost:
                    # Get agent presence from Mattermost
                    for agent in self.agents.values():
                        if agent.mattermost_user_id:
                            presence = await self.mattermost.get_user_status(
                                agent.mattermost_user_id
                            )
                            
                            # Map Mattermost status to agent status
                            status_mapping = {
                                "online": AgentStatus.AVAILABLE,
                                "busy": AgentStatus.BUSY,
                                "away": AgentStatus.AWAY,
                                "offline": AgentStatus.OFFLINE
                            }
                            
                            new_status = status_mapping.get(presence, AgentStatus.OFFLINE)
                            if new_status != agent.status:
                                await self.update_agent_status(agent.id, new_status)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error("Error in agent presence monitoring", error=str(e))
                await asyncio.sleep(120)
    
    async def _monitor_sla_breaches(self) -> None:
        """Monitor and handle SLA breaches."""
        while True:
            try:
                current_time = datetime.utcnow()
                
                for ticket in list(self.active_tickets.values()) + self.escalation_queue:
                    # Check response SLA
                    if not ticket.first_response_at:
                        wait_time = (current_time - ticket.created_at).total_seconds() / 60
                        
                        if wait_time > ticket.response_sla_minutes:
                            await self._handle_sla_breach(ticket, "response")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error("Error in SLA monitoring", error=str(e))
                await asyncio.sleep(120)
    
    async def _handle_sla_breach(
        self,
        ticket: EscalationTicket,
        breach_type: str
    ) -> None:
        """Handle SLA breach."""
        logger.warning(
            "SLA breach detected",
            ticket_id=ticket.id,
            breach_type=breach_type,
            priority=ticket.priority
        )
        
        # Escalate priority if possible
        if ticket.priority == EscalationPriority.NORMAL:
            ticket.priority = EscalationPriority.HIGH
        elif ticket.priority == EscalationPriority.HIGH:
            ticket.priority = EscalationPriority.URGENT
        
        # Notify management
        if self.mattermost:
            await self._notify_sla_breach(ticket, breach_type)
    
    def _categorize_escalation(self, reason: str) -> str:
        """Categorize escalation reason."""
        categories = {
            "billing": ["billing", "payment", "insurance", "cost"],
            "clinical": ["medical", "doctor", "diagnosis", "treatment"],
            "pharmacy": ["prescription", "medication", "drug", "pharmacy"],
            "technical": ["not working", "error", "bug", "broken"],
            "complaint": ["complaint", "frustrated", "angry", "dissatisfied"]
        }
        
        reason_lower = reason.lower()
        
        for category, keywords in categories.items():
            if any(keyword in reason_lower for keyword in keywords):
                return category
        
        return "general"
    
    def _get_response_sla(self, priority: EscalationPriority) -> int:
        """Get response SLA minutes based on priority."""
        sla_mapping = {
            EscalationPriority.URGENT: 5,
            EscalationPriority.HIGH: 10,
            EscalationPriority.NORMAL: 15,
            EscalationPriority.LOW: 30
        }
        return sla_mapping[priority]
    
    def _get_resolution_sla(self, priority: EscalationPriority) -> int:
        """Get resolution SLA minutes based on priority."""
        sla_mapping = {
            EscalationPriority.URGENT: 30,
            EscalationPriority.HIGH: 60,
            EscalationPriority.NORMAL: 120,
            EscalationPriority.LOW: 240
        }
        return sla_mapping[priority]
    
    async def _estimate_wait_time(self, ticket: EscalationTicket) -> int:
        """Estimate wait time for ticket."""
        if ticket.assigned_agent_id:
            return 0
        
        # Simple estimation based on queue position and average handling time
        position = ticket.queue_position or len(self.escalation_queue)
        avg_handling_time = 15  # minutes
        
        return position * avg_handling_time
    
    async def _reassign_agent_tickets(self, agent_id: str) -> None:
        """Reassign tickets when agent goes offline."""
        agent = self.agents.get(agent_id)
        if not agent:
            return
        
        # Find tickets assigned to this agent
        agent_tickets = [
            ticket for ticket in self.active_tickets.values()
            if ticket.assigned_agent_id == agent_id
        ]
        
        for ticket in agent_tickets:
            # Unassign from agent
            ticket.assigned_agent_id = None
            ticket.assigned_at = None
            ticket.status = "pending"
            
            # Add back to queue
            await self._add_to_queue(ticket)
        
        # Update agent workload
        agent.current_load = 0
        agent.active_conversations.clear()
        
        logger.info(
            "Reassigned agent tickets",
            agent_id=agent_id,
            tickets_reassigned=len(agent_tickets)
        )
    
    # Mattermost notification methods
    
    async def _notify_escalation_team(self, ticket: EscalationTicket) -> None:
        """Notify escalation team about new ticket."""
        if not self.mattermost:
            return
        
        message = f"""
🚨 **New Escalation Ticket**
- **ID**: {ticket.id[:8]}
- **Priority**: {ticket.priority.upper()}
- **Category**: {ticket.category}
- **Channel**: {ticket.channel}
- **Language**: {ticket.language}
- **Reason**: {ticket.reason}
- **Queue Position**: #{ticket.queue_position}

**Patient Context**:
- Previous conversations: {ticket.user_context.get('total_conversations', 0)}
- Satisfaction score: {ticket.user_context.get('satisfaction_scores', [])[-1:]}

To assign: `/assign {ticket.id[:8]} @agent`
        """
        
        await self.mattermost.send_message(
            self.settings.mattermost_escalation_channel,
            message
        )
    
    async def _notify_agent_assignment(
        self,
        ticket: EscalationTicket,
        agent: Agent
    ) -> None:
        """Notify agent about ticket assignment."""
        if not self.mattermost:
            return
        
        message = f"""
👋 **New Conversation Assigned**
- **Ticket**: {ticket.id[:8]}
- **Priority**: {ticket.priority.upper()}
- **Channel**: {ticket.channel}
- **Wait time**: {(datetime.utcnow() - ticket.created_at).total_seconds() / 60:.1f} minutes

**Summary**: {ticket.conversation_summary.get('current_topic', 'General inquiry')}
**Urgency**: {ticket.conversation_summary.get('urgency_level', 'normal')}

Click to join conversation: [Link](conversation/{ticket.conversation_id})
        """
        
        # Send direct message to agent
        if agent.mattermost_user_id:
            await self.mattermost.send_direct_message(
                agent.mattermost_user_id,
                message
            )
    
    async def _notify_escalation_timeout(self, ticket: EscalationTicket) -> None:
        """Notify about escalation timeout."""
        if not self.mattermost:
            return
        
        message = f"""
⏰ **Escalation Timeout**
- **Ticket**: {ticket.id[:8]}
- **Priority upgraded to**: {ticket.priority.upper()}
- **Wait time**: {(datetime.utcnow() - ticket.created_at).total_seconds() / 60:.1f} minutes

Immediate attention required!
        """
        
        await self.mattermost.send_message(
            self.settings.mattermost_escalation_channel,
            message
        )
    
    async def _notify_sla_breach(
        self,
        ticket: EscalationTicket,
        breach_type: str
    ) -> None:
        """Notify about SLA breach."""
        if not self.mattermost:
            return
        
        message = f"""
🚨 **SLA BREACH ALERT**
- **Ticket**: {ticket.id[:8]}
- **Breach Type**: {breach_type.upper()}
- **Priority**: {ticket.priority.upper()}
- **Time elapsed**: {(datetime.utcnow() - ticket.created_at).total_seconds() / 60:.1f} minutes

URGENT ACTION REQUIRED!
        """
        
        await self.mattermost.send_message(
            self.settings.mattermost_csr_ops_channel,
            message
        )
    
    async def cleanup(self) -> None:
        """Cleanup escalation manager resources."""
        logger.info("Cleaning up escalation manager...")
        
        if self.mattermost:
            await self.mattermost.cleanup()
        
        logger.info("Escalation manager cleanup complete") 