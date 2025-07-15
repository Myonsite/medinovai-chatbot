"""
Twilio Adapter - SMS and Voice Integration for MedinovAI
Handles SMS messaging, voice calls, and TwiML webhook processing
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from urllib.parse import parse_qs

import structlog
import httpx
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from twilio.twiml.voice_response import VoiceResponse
from twilio.base.exceptions import TwilioException

from utils.config import Settings
from utils.phi_protection import PHIProtector
from utils.metrics import MetricsCollector

logger = structlog.get_logger(__name__)


class TwilioAdapter:
    """
    Twilio integration adapter for healthcare communication.
    Handles SMS, voice calls, and TwiML responses.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client: Optional[Client] = None
        self.phi_protector: Optional[PHIProtector] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        
        # Webhook handlers
        self.sms_handlers: List[Callable] = []
        self.voice_handlers: List[Callable] = []
        self.status_handlers: List[Callable] = []
        
        # Message tracking
        self.sent_messages: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Twilio adapter initialized")
    
    async def initialize(self) -> None:
        """Initialize Twilio client and verify configuration."""
        try:
            if not self.settings.twilio_enabled:
                logger.info("Twilio integration disabled")
                return
            
            # Initialize Twilio client
            self.client = Client(
                self.settings.twilio_account_sid,
                self.settings.twilio_auth_token.get_secret_value()
            )
            
            # Verify account
            account = self.client.api.accounts(self.settings.twilio_account_sid).fetch()
            logger.info(
                "Twilio client initialized successfully",
                account_sid=account.sid,
                status=account.status
            )
            
            # Get PHI protector and metrics collector
            from main import phi_protector, metrics_collector
            self.phi_protector = phi_protector
            self.metrics_collector = metrics_collector
            
        except Exception as e:
            logger.error("Failed to initialize Twilio client", error=str(e))
            raise
    
    async def send_sms(
        self,
        to_number: str,
        message: str,
        from_number: Optional[str] = None,
        media_urls: Optional[List[str]] = None
    ) -> bool:
        """Send SMS message via Twilio."""
        if not self.client:
            logger.error("Twilio client not initialized")
            return False
        
        try:
            # Use PHI protection if available
            protected_message = message
            if self.phi_protector:
                phi_detected, protected_message = await self.phi_protector.detect_and_redact(
                    message,
                    context={"channel": "sms", "recipient": to_number[-4:]}
                )
                
                if phi_detected:
                    logger.warning(
                        "PHI detected in SMS message",
                        recipient=to_number[-4:]
                    )
            
            # Send SMS
            twilio_message = self.client.messages.create(
                body=protected_message,
                from_=from_number or self.settings.twilio_phone_number,
                to=to_number,
                media_url=media_urls
            )
            
            # Track message
            self.sent_messages[twilio_message.sid] = {
                "to": to_number,
                "message": protected_message,
                "status": twilio_message.status,
                "created_at": datetime.utcnow(),
                "type": "sms"
            }
            
            logger.info(
                "SMS sent successfully",
                message_sid=twilio_message.sid,
                to=to_number[-4:],
                status=twilio_message.status
            )
            
            # Record metrics
            if self.metrics_collector:
                self.metrics_collector.record_message_processed(
                    channel="sms",
                    response_time_ms=0,  # SMS is async
                    phi_detected=phi_detected if self.phi_protector else False
                )
            
            return True
            
        except TwilioException as e:
            logger.error(
                "Twilio SMS error",
                error_code=e.code,
                error_message=e.msg,
                to=to_number[-4:]
            )
            return False
        except Exception as e:
            logger.error("Failed to send SMS", error=str(e), to=to_number[-4:])
            return False
    
    async def make_voice_call(
        self,
        to_number: str,
        twiml_url: str,
        from_number: Optional[str] = None
    ) -> Optional[str]:
        """Initiate voice call via Twilio."""
        if not self.client:
            logger.error("Twilio client not initialized")
            return None
        
        try:
            call = self.client.calls.create(
                twiml=f'<Response><Redirect>{twiml_url}</Redirect></Response>',
                to=to_number,
                from_=from_number or self.settings.twilio_phone_number
            )
            
            logger.info(
                "Voice call initiated",
                call_sid=call.sid,
                to=to_number[-4:],
                status=call.status
            )
            
            return call.sid
            
        except TwilioException as e:
            logger.error(
                "Twilio voice call error",
                error_code=e.code,
                error_message=e.msg,
                to=to_number[-4:]
            )
            return None
        except Exception as e:
            logger.error("Failed to make voice call", error=str(e))
            return None
    
    def generate_sms_twiml_response(
        self,
        response_message: str,
        media_urls: Optional[List[str]] = None
    ) -> str:
        """Generate TwiML response for SMS."""
        try:
            resp = MessagingResponse()
            message = resp.message(response_message)
            
            if media_urls:
                for url in media_urls:
                    message.media(url)
            
            return str(resp)
            
        except Exception as e:
            logger.error("Failed to generate SMS TwiML", error=str(e))
            return str(MessagingResponse())
    
    def generate_voice_twiml_response(
        self,
        message: str,
        gather_input: bool = False,
        action_url: Optional[str] = None
    ) -> str:
        """Generate TwiML response for voice calls."""
        try:
            resp = VoiceResponse()
            
            if gather_input and action_url:
                gather = resp.gather(
                    action=action_url,
                    method="POST",
                    timeout=10,
                    num_digits=1
                )
                gather.say(message, voice="alice")
                resp.say("We didn't receive any input. Goodbye!", voice="alice")
            else:
                resp.say(message, voice="alice")
            
            return str(resp)
            
        except Exception as e:
            logger.error("Failed to generate voice TwiML", error=str(e))
            return str(VoiceResponse().say("An error occurred. Please try again."))
    
    def register_sms_handler(self, handler: Callable) -> None:
        """Register handler for incoming SMS messages."""
        self.sms_handlers.append(handler)
        logger.info("SMS handler registered")
    
    def register_voice_handler(self, handler: Callable) -> None:
        """Register handler for incoming voice calls."""
        self.voice_handlers.append(handler)
        logger.info("Voice handler registered")
    
    def register_status_handler(self, handler: Callable) -> None:
        """Register handler for message status updates."""
        self.status_handlers.append(handler)
        logger.info("Status handler registered")
    
    async def handle_sms_webhook(self, webhook_data: Dict[str, Any]) -> str:
        """Process incoming SMS webhook from Twilio."""
        try:
            from_number = webhook_data.get("From", "")
            to_number = webhook_data.get("To", "")
            message_body = webhook_data.get("Body", "")
            message_sid = webhook_data.get("MessageSid", "")
            
            logger.info(
                "Incoming SMS received",
                message_sid=message_sid,
                from_number=from_number[-4:],
                to_number=to_number[-4:]
            )
            
            # Process through registered handlers
            response_message = None
            for handler in self.sms_handlers:
                try:
                    result = await handler({
                        "from_number": from_number,
                        "to_number": to_number,
                        "message": message_body,
                        "message_sid": message_sid,
                        "channel": "sms"
                    })
                    
                    if result and result.get("response"):
                        response_message = result["response"]
                        break
                        
                except Exception as e:
                    logger.error(
                        "SMS handler error",
                        handler=handler.__name__,
                        error=str(e)
                    )
            
            # Generate TwiML response
            if response_message:
                return self.generate_sms_twiml_response(response_message)
            else:
                # Default response
                return self.generate_sms_twiml_response(
                    "Thank you for contacting MedinovAI. We'll respond shortly."
                )
            
        except Exception as e:
            logger.error("Failed to process SMS webhook", error=str(e))
            return self.generate_sms_twiml_response(
                "We're experiencing technical difficulties. Please try again later."
            )
    
    async def handle_voice_webhook(self, webhook_data: Dict[str, Any]) -> str:
        """Process incoming voice webhook from Twilio."""
        try:
            from_number = webhook_data.get("From", "")
            to_number = webhook_data.get("To", "")
            call_sid = webhook_data.get("CallSid", "")
            call_status = webhook_data.get("CallStatus", "")
            
            logger.info(
                "Incoming voice call",
                call_sid=call_sid,
                from_number=from_number[-4:],
                to_number=to_number[-4:],
                status=call_status
            )
            
            # Process through registered handlers
            response_message = None
            gather_input = False
            action_url = None
            
            for handler in self.voice_handlers:
                try:
                    result = await handler({
                        "from_number": from_number,
                        "to_number": to_number,
                        "call_sid": call_sid,
                        "call_status": call_status,
                        "channel": "voice"
                    })
                    
                    if result:
                        response_message = result.get("message")
                        gather_input = result.get("gather_input", False)
                        action_url = result.get("action_url")
                        break
                        
                except Exception as e:
                    logger.error(
                        "Voice handler error",
                        handler=handler.__name__,
                        error=str(e)
                    )
            
            # Generate TwiML response
            if response_message:
                return self.generate_voice_twiml_response(
                    response_message,
                    gather_input,
                    action_url
                )
            else:
                # Default voice response
                return self.generate_voice_twiml_response(
                    "Thank you for calling MedinovAI. "
                    "Please hold while we connect you to an agent."
                )
            
        except Exception as e:
            logger.error("Failed to process voice webhook", error=str(e))
            return self.generate_voice_twiml_response(
                "We're experiencing technical difficulties. Please try again later."
            )
    
    async def handle_status_webhook(self, webhook_data: Dict[str, Any]) -> None:
        """Process message status webhook from Twilio."""
        try:
            message_sid = webhook_data.get("MessageSid", "")
            message_status = webhook_data.get("MessageStatus", "")
            error_code = webhook_data.get("ErrorCode")
            error_message = webhook_data.get("ErrorMessage")
            
            logger.info(
                "Message status update",
                message_sid=message_sid,
                status=message_status,
                error_code=error_code
            )
            
            # Update tracked message
            if message_sid in self.sent_messages:
                self.sent_messages[message_sid]["status"] = message_status
                self.sent_messages[message_sid]["updated_at"] = datetime.utcnow()
                
                if error_code:
                    self.sent_messages[message_sid]["error"] = {
                        "code": error_code,
                        "message": error_message
                    }
            
            # Process through registered handlers
            for handler in self.status_handlers:
                try:
                    await handler({
                        "message_sid": message_sid,
                        "status": message_status,
                        "error_code": error_code,
                        "error_message": error_message
                    })
                except Exception as e:
                    logger.error(
                        "Status handler error",
                        handler=handler.__name__,
                        error=str(e)
                    )
            
        except Exception as e:
            logger.error("Failed to process status webhook", error=str(e))
    
    async def get_message_status(self, message_sid: str) -> Optional[Dict[str, Any]]:
        """Get status of sent message."""
        if not self.client:
            return None
        
        try:
            message = self.client.messages(message_sid).fetch()
            
            return {
                "sid": message.sid,
                "status": message.status,
                "direction": message.direction,
                "from": message.from_,
                "to": message.to,
                "body": message.body,
                "date_created": message.date_created,
                "date_updated": message.date_updated,
                "error_code": message.error_code,
                "error_message": message.error_message
            }
            
        except Exception as e:
            logger.error(
                "Failed to get message status",
                message_sid=message_sid,
                error=str(e)
            )
            return None
    
    async def get_phone_number_info(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get information about a phone number."""
        if not self.client:
            return None
        
        try:
            lookup = self.client.lookups.v1.phone_numbers(phone_number).fetch()
            
            return {
                "phone_number": lookup.phone_number,
                "country_code": lookup.country_code,
                "national_format": lookup.national_format,
                "valid": True
            }
            
        except Exception as e:
            logger.error(
                "Failed to lookup phone number",
                phone_number=phone_number[-4:],
                error=str(e)
            )
            return {"valid": False, "error": str(e)}
    
    def get_webhook_signature_header(self) -> str:
        """Get webhook signature header name."""
        return "X-Twilio-Signature"
    
    def verify_webhook_signature(
        self,
        signature: str,
        url: str,
        post_data: bytes
    ) -> bool:
        """Verify Twilio webhook signature."""
        try:
            from twilio.request_validator import RequestValidator
            
            validator = RequestValidator(
                self.settings.twilio_auth_token.get_secret_value()
            )
            
            return validator.validate(url, post_data, signature)
            
        except Exception as e:
            logger.error("Failed to verify webhook signature", error=str(e))
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Twilio service health."""
        if not self.client:
            return {"status": "unhealthy", "reason": "Client not initialized"}
        
        try:
            # Test account access
            account = self.client.api.accounts(self.settings.twilio_account_sid).fetch()
            
            return {
                "status": "healthy",
                "account_sid": account.sid,
                "account_status": account.status,
                "phone_number": self.settings.twilio_phone_number,
                "capabilities": ["sms", "voice"]
            }
            
        except Exception as e:
            logger.error("Twilio health check failed", error=str(e))
            return {"status": "unhealthy", "error": str(e)}
    
    async def cleanup(self) -> None:
        """Cleanup Twilio adapter."""
        logger.info("Cleaning up Twilio adapter...")
        
        # Clear handlers
        self.sms_handlers.clear()
        self.voice_handlers.clear()
        self.status_handlers.clear()
        
        # Clear message tracking
        self.sent_messages.clear()
        
        logger.info("Twilio adapter cleanup complete") 