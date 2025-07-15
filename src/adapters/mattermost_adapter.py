"""
Mattermost Adapter - Team Communication and Agent Escalation for MedinovAI
Handles agent notifications, escalation workflows, and team coordination
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable

import structlog
import httpx
from pydantic import BaseModel

from utils.config import Settings
from utils.security import SecurityManager

logger = structlog.get_logger(__name__)


class MattermostMessage(BaseModel):
    """Mattermost message model."""
    channel_id: str
    message: str
    file_ids: List[str] = []
    props: Dict[str, Any] = {}


class MattermostPost(BaseModel):
    """Mattermost post response model."""
    id: str
    create_at: int
    update_at: int
    delete_at: int
    user_id: str
    channel_id: str
    message: str
    type: str
    props: Dict[str, Any]


class AgentStatus(BaseModel):
    """Agent status in Mattermost."""
    user_id: str
    username: str
    status: str  # online, away, offline, dnd
    last_activity_at: int
    manual: bool


class MattermostAdapter:
    """
    Mattermost integration adapter for healthcare team communication.
    Handles agent escalation, notifications, and workflow management.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.mattermost_url.rstrip('/')
        self.bot_token = settings.mattermost_bot_token.get_secret_value()
        self.team_id = settings.mattermost_team_id
        self.escalation_channel_id = settings.mattermost_escalation_channel_id
        
        # HTTP client for API calls
        self.client: Optional[httpx.AsyncClient] = None
        
        # Bot user info
        self.bot_user_id: Optional[str] = None
        self.bot_username: Optional[str] = None
        
        # Event handlers
        self.message_handlers: List[Callable] = []
        self.status_handlers: List[Callable] = []
        
        # Agent tracking
        self.agents: Dict[str, AgentStatus] = {}
        self.agent_workload: Dict[str, int] = {}
        
        logger.info("Mattermost adapter initialized")
    
    async def initialize(self) -> None:
        """Initialize Mattermost client and bot user."""
        try:
            if not self.settings.mattermost_enabled:
                logger.info("Mattermost integration disabled")
                return
            
            # Create HTTP client
            self.client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self.bot_token}",
                    "Content-Type": "application/json"
                }
            )
            
            # Get bot user info
            await self._get_bot_user_info()
            
            # Verify team and channel access
            await self._verify_team_access()
            await self._verify_channel_access()
            
            # Load initial agent statuses
            await self._load_agent_statuses()
            
            logger.info(
                "Mattermost client initialized successfully",
                bot_user_id=self.bot_user_id,
                bot_username=self.bot_username
            )
            
        except Exception as e:
            logger.error("Failed to initialize Mattermost client", error=str(e))
            raise
    
    async def send_escalation_notification(
        self,
        escalation_data: Dict[str, Any],
        priority: str = "normal"
    ) -> Optional[str]:
        """Send escalation notification to the team."""
        if not self.client:
            logger.error("Mattermost client not initialized")
            return None
        
        try:
            # Format escalation message
            message = self._format_escalation_message(escalation_data, priority)
            
            # Send to escalation channel
            post_data = {
                "channel_id": self.escalation_channel_id,
                "message": message,
                "props": {
                    "escalation_id": escalation_data.get("escalation_id"),
                    "conversation_id": escalation_data.get("conversation_id"),
                    "priority": priority,
                    "created_at": datetime.utcnow().isoformat()
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v4/posts",
                json=post_data
            )
            response.raise_for_status()
            
            post = response.json()
            post_id = post["id"]
            
            logger.info(
                "Escalation notification sent",
                post_id=post_id,
                escalation_id=escalation_data.get("escalation_id"),
                priority=priority
            )
            
            # Add reactions based on priority
            if priority in ["high", "urgent"]:
                await self._add_reaction(post_id, "warning")
            
            return post_id
            
        except Exception as e:
            logger.error("Failed to send escalation notification", error=str(e))
            return None
    
    async def send_agent_message(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None
    ) -> Optional[str]:
        """Send direct message to specific agent."""
        if not self.client:
            logger.error("Mattermost client not initialized")
            return None
        
        try:
            # Create or get direct channel
            dm_channel = await self._get_or_create_dm_channel(user_id)
            if not dm_channel:
                return None
            
            post_data = {
                "channel_id": dm_channel["id"],
                "message": message,
                "props": {
                    "conversation_id": conversation_id,
                    "sent_at": datetime.utcnow().isoformat()
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v4/posts",
                json=post_data
            )
            response.raise_for_status()
            
            post = response.json()
            logger.info(
                "Direct message sent to agent",
                user_id=user_id,
                post_id=post["id"]
            )
            
            return post["id"]
            
        except Exception as e:
            logger.error(
                "Failed to send agent message",
                user_id=user_id,
                error=str(e)
            )
            return None
    
    async def get_available_agents(
        self,
        specialties: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get list of available agents with optional specialty filtering."""
        if not self.client:
            return []
        
        try:
            # Get team members
            response = await self.client.get(
                f"{self.base_url}/api/v4/teams/{self.team_id}/members"
            )
            response.raise_for_status()
            
            members = response.json()
            available_agents = []
            
            for member in members:
                user_id = member["user_id"]
                
                # Get user details
                user_response = await self.client.get(
                    f"{self.base_url}/api/v4/users/{user_id}"
                )
                
                if user_response.status_code != 200:
                    continue
                
                user = user_response.json()
                
                # Skip bots and inactive users
                if user.get("is_bot") or user.get("delete_at", 0) > 0:
                    continue
                
                # Get status
                status_response = await self.client.get(
                    f"{self.base_url}/api/v4/users/{user_id}/status"
                )
                
                if status_response.status_code != 200:
                    continue
                
                status = status_response.json()
                
                # Only include online/away agents
                if status.get("status") not in ["online", "away"]:
                    continue
                
                agent_info = {
                    "user_id": user_id,
                    "username": user["username"],
                    "first_name": user.get("first_name", ""),
                    "last_name": user.get("last_name", ""),
                    "email": user.get("email", ""),
                    "status": status.get("status"),
                    "last_activity": status.get("last_activity_at", 0),
                    "workload": self.agent_workload.get(user_id, 0),
                    "specialties": self._get_agent_specialties(user_id)
                }
                
                # Filter by specialties if specified
                if specialties:
                    agent_specialties = agent_info["specialties"]
                    if not any(spec in agent_specialties for spec in specialties):
                        continue
                
                available_agents.append(agent_info)
            
            # Sort by workload (ascending) and status priority
            available_agents.sort(key=lambda x: (
                0 if x["status"] == "online" else 1,  # Online agents first
                x["workload"]  # Then by workload
            ))
            
            return available_agents
            
        except Exception as e:
            logger.error("Failed to get available agents", error=str(e))
            return []
    
    async def assign_conversation_to_agent(
        self,
        conversation_id: str,
        agent_user_id: str,
        escalation_data: Dict[str, Any]
    ) -> bool:
        """Assign conversation to specific agent."""
        try:
            # Send assignment notification
            message = self._format_assignment_message(conversation_id, escalation_data)
            
            post_id = await self.send_agent_message(
                agent_user_id,
                message,
                conversation_id
            )
            
            if post_id:
                # Update agent workload
                self.agent_workload[agent_user_id] = self.agent_workload.get(agent_user_id, 0) + 1
                
                # Send confirmation to escalation channel
                confirmation = f"Conversation {conversation_id[:8]} assigned to <@{agent_user_id}>"
                await self.send_channel_message(self.escalation_channel_id, confirmation)
                
                logger.info(
                    "Conversation assigned to agent",
                    conversation_id=conversation_id,
                    agent_user_id=agent_user_id
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(
                "Failed to assign conversation to agent",
                conversation_id=conversation_id,
                agent_user_id=agent_user_id,
                error=str(e)
            )
            return False
    
    async def send_channel_message(
        self,
        channel_id: str,
        message: str,
        props: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Send message to channel."""
        if not self.client:
            return None
        
        try:
            post_data = {
                "channel_id": channel_id,
                "message": message,
                "props": props or {}
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v4/posts",
                json=post_data
            )
            response.raise_for_status()
            
            post = response.json()
            return post["id"]
            
        except Exception as e:
            logger.error("Failed to send channel message", error=str(e))
            return None
    
    async def create_escalation_thread(
        self,
        escalation_data: Dict[str, Any]
    ) -> Optional[str]:
        """Create threaded discussion for escalation."""
        try:
            # Create main escalation post
            post_id = await self.send_escalation_notification(
                escalation_data,
                escalation_data.get("priority", "normal")
            )
            
            if not post_id:
                return None
            
            # Add initial context as reply
            context_message = self._format_escalation_context(escalation_data)
            
            context_post_data = {
                "channel_id": self.escalation_channel_id,
                "message": context_message,
                "root_id": post_id,
                "props": {
                    "type": "escalation_context",
                    "escalation_id": escalation_data.get("escalation_id")
                }
            }
            
            await self.client.post(
                f"{self.base_url}/api/v4/posts",
                json=context_post_data
            )
            
            return post_id
            
        except Exception as e:
            logger.error("Failed to create escalation thread", error=str(e))
            return None
    
    async def update_agent_workload(self, agent_user_id: str, delta: int) -> None:
        """Update agent workload counter."""
        current = self.agent_workload.get(agent_user_id, 0)
        new_workload = max(0, current + delta)
        self.agent_workload[agent_user_id] = new_workload
        
        logger.debug(
            "Agent workload updated",
            agent_user_id=agent_user_id,
            old_workload=current,
            new_workload=new_workload
        )
    
    def register_message_handler(self, handler: Callable) -> None:
        """Register handler for incoming messages."""
        self.message_handlers.append(handler)
        logger.info("Message handler registered")
    
    def register_status_handler(self, handler: Callable) -> None:
        """Register handler for status changes."""
        self.status_handlers.append(handler)
        logger.info("Status handler registered")
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> None:
        """Process incoming webhook from Mattermost."""
        try:
            event_type = webhook_data.get("event")
            
            if event_type == "posted":
                await self._handle_message_event(webhook_data)
            elif event_type == "status_change":
                await self._handle_status_event(webhook_data)
            else:
                logger.debug("Unhandled webhook event", event_type=event_type)
            
        except Exception as e:
            logger.error("Failed to process webhook", error=str(e))
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Mattermost service health."""
        if not self.client:
            return {"status": "unhealthy", "reason": "Client not initialized"}
        
        try:
            # Test API access
            response = await self.client.get(f"{self.base_url}/api/v4/system/ping")
            response.raise_for_status()
            
            # Get server status
            status_response = await self.client.get(f"{self.base_url}/api/v4/system/status")
            status_response.raise_for_status()
            
            return {
                "status": "healthy",
                "server_status": status_response.json(),
                "bot_user_id": self.bot_user_id,
                "team_id": self.team_id,
                "available_agents": len(await self.get_available_agents())
            }
            
        except Exception as e:
            logger.error("Mattermost health check failed", error=str(e))
            return {"status": "unhealthy", "error": str(e)}
    
    async def cleanup(self) -> None:
        """Cleanup Mattermost adapter."""
        logger.info("Cleaning up Mattermost adapter...")
        
        if self.client:
            await self.client.aclose()
        
        # Clear handlers
        self.message_handlers.clear()
        self.status_handlers.clear()
        
        # Clear tracking data
        self.agents.clear()
        self.agent_workload.clear()
        
        logger.info("Mattermost adapter cleanup complete")
    
    # Private methods
    
    async def _get_bot_user_info(self) -> None:
        """Get bot user information."""
        response = await self.client.get(f"{self.base_url}/api/v4/users/me")
        response.raise_for_status()
        
        user_info = response.json()
        self.bot_user_id = user_info["id"]
        self.bot_username = user_info["username"]
    
    async def _verify_team_access(self) -> None:
        """Verify bot has access to the team."""
        response = await self.client.get(f"{self.base_url}/api/v4/teams/{self.team_id}")
        response.raise_for_status()
        
        team_info = response.json()
        logger.info("Team access verified", team_name=team_info["display_name"])
    
    async def _verify_channel_access(self) -> None:
        """Verify bot has access to escalation channel."""
        response = await self.client.get(
            f"{self.base_url}/api/v4/channels/{self.escalation_channel_id}"
        )
        response.raise_for_status()
        
        channel_info = response.json()
        logger.info("Channel access verified", channel_name=channel_info["display_name"])
    
    async def _load_agent_statuses(self) -> None:
        """Load initial agent status information."""
        agents = await self.get_available_agents()
        for agent in agents:
            self.agents[agent["user_id"]] = AgentStatus(
                user_id=agent["user_id"],
                username=agent["username"],
                status=agent["status"],
                last_activity_at=agent["last_activity"],
                manual=False
            )
        
        logger.info("Agent statuses loaded", count=len(self.agents))
    
    async def _get_or_create_dm_channel(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get or create direct message channel with user."""
        try:
            # Try to create DM channel
            dm_data = [self.bot_user_id, user_id]
            
            response = await self.client.post(
                f"{self.base_url}/api/v4/channels/direct",
                json=dm_data
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error("Failed to get/create DM channel", user_id=user_id, error=str(e))
            return None
    
    async def _add_reaction(self, post_id: str, emoji_name: str) -> None:
        """Add reaction to post."""
        try:
            reaction_data = {
                "user_id": self.bot_user_id,
                "post_id": post_id,
                "emoji_name": emoji_name
            }
            
            await self.client.post(
                f"{self.base_url}/api/v4/reactions",
                json=reaction_data
            )
            
        except Exception as e:
            logger.error("Failed to add reaction", post_id=post_id, error=str(e))
    
    def _format_escalation_message(self, escalation_data: Dict[str, Any], priority: str) -> str:
        """Format escalation notification message."""
        priority_emoji = {
            "low": ":information_source:",
            "normal": ":warning:",
            "high": ":exclamation:",
            "urgent": ":rotating_light:"
        }
        
        emoji = priority_emoji.get(priority, ":warning:")
        
        return f"""{emoji} **Healthcare Conversation Escalation** {emoji}
        
**Priority:** {priority.upper()}
**Conversation ID:** {escalation_data.get('conversation_id', 'N/A')[:8]}
**Reason:** {escalation_data.get('reason', 'N/A')}
**Patient Channel:** {escalation_data.get('channel', 'N/A')}
**Queue Position:** {escalation_data.get('queue_position', 'N/A')}

**User Context:**
- Language: {escalation_data.get('language', 'en')}
- Previous Messages: {escalation_data.get('message_count', 0)}

Who can take this conversation? React with :raised_hand: to claim it!
"""
    
    def _format_assignment_message(self, conversation_id: str, escalation_data: Dict[str, Any]) -> str:
        """Format conversation assignment message."""
        return f"""You've been assigned a healthcare conversation that needs attention.

**Conversation ID:** {conversation_id[:8]}
**Priority:** {escalation_data.get('priority', 'normal').upper()}
**Reason for Escalation:** {escalation_data.get('reason', 'N/A')}

**Context:**
- Channel: {escalation_data.get('channel', 'N/A')}
- Language: {escalation_data.get('language', 'en')}
- Message Count: {escalation_data.get('message_count', 0)}

Please review the conversation history and respond promptly. 
Use the MedinovAI dashboard to view full context and begin assisting the patient.
"""
    
    def _format_escalation_context(self, escalation_data: Dict[str, Any]) -> str:
        """Format escalation context information."""
        return f"""**Additional Context:**

**Conversation Summary:**
{escalation_data.get('summary', 'No summary available')}

**User Profile:**
- Preferred Language: {escalation_data.get('language', 'en')}
- Communication Style: {escalation_data.get('communication_style', 'professional')}
- Accessibility Needs: {escalation_data.get('accessibility_needs', 'None specified')}

**Conversation History:**
- Started: {escalation_data.get('started_at', 'N/A')}
- Last Activity: {escalation_data.get('last_activity', 'N/A')}
- Total Messages: {escalation_data.get('message_count', 0)}

**SLA Information:**
- Response Target: 15 minutes
- Resolution Target: 60 minutes
"""
    
    def _get_agent_specialties(self, user_id: str) -> List[str]:
        """Get agent specialties from user profile."""
        # In production, this would come from user custom fields or database
        # For now, return default specialties
        return ["general", "billing", "clinical"]
    
    async def _handle_message_event(self, webhook_data: Dict[str, Any]) -> None:
        """Handle incoming message event."""
        try:
            post_data = webhook_data.get("data", {}).get("post")
            if not post_data:
                return
            
            # Skip bot messages
            if post_data.get("user_id") == self.bot_user_id:
                return
            
            # Process through handlers
            for handler in self.message_handlers:
                try:
                    await handler({
                        "post_id": post_data.get("id"),
                        "user_id": post_data.get("user_id"),
                        "channel_id": post_data.get("channel_id"),
                        "message": post_data.get("message", ""),
                        "props": post_data.get("props", {}),
                        "timestamp": post_data.get("create_at")
                    })
                except Exception as e:
                    logger.error("Message handler error", handler=handler.__name__, error=str(e))
        
        except Exception as e:
            logger.error("Failed to handle message event", error=str(e))
    
    async def _handle_status_event(self, webhook_data: Dict[str, Any]) -> None:
        """Handle user status change event."""
        try:
            data = webhook_data.get("data", {})
            user_id = data.get("user_id")
            status = data.get("status")
            
            if user_id and status:
                # Update agent status
                if user_id in self.agents:
                    self.agents[user_id].status = status
                    self.agents[user_id].last_activity_at = int(datetime.utcnow().timestamp() * 1000)
                
                # Process through handlers
                for handler in self.status_handlers:
                    try:
                        await handler({
                            "user_id": user_id,
                            "status": status,
                            "timestamp": datetime.utcnow()
                        })
                    except Exception as e:
                        logger.error("Status handler error", handler=handler.__name__, error=str(e))
        
        except Exception as e:
            logger.error("Failed to handle status event", error=str(e)) 