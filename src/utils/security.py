"""
Security Manager - Authentication, encryption, and security controls for MedinovAI
Handles JWT tokens, encryption, rate limiting, and security audit logging
"""

import secrets
import hashlib
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import structlog
import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet

from utils.config import Settings

logger = structlog.get_logger(__name__)


class SecurityManager:
    """
    Manages security aspects of MedinovAI including authentication,
    encryption, and security audit logging.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Password hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # JWT configuration
        self.jwt_secret = settings.jwt_secret.get_secret_value()
        self.jwt_algorithm = "HS256"
        self.jwt_expiry = settings.jwt_expiry
        
        # Encryption
        self.encryption_key = None
        if settings.encryption_key:
            self.encryption_key = settings.encryption_key.get_secret_value()
            # Ensure key is proper length for Fernet
            key_hash = hashlib.sha256(self.encryption_key.encode()).digest()
            import base64
            self.fernet = Fernet(base64.urlsafe_b64encode(key_hash))
        
        # Rate limiting storage (in production, use Redis)
        self.rate_limit_store: Dict[str, List[float]] = {}
        
        # Security audit log
        self.security_events: List[Dict[str, Any]] = []
        
        logger.info("Security manager initialized")
    
    def generate_request_id(self) -> str:
        """Generate unique request ID for tracing."""
        return str(uuid.uuid4())
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(seconds=self.jwt_expiry)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        return jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token."""
        to_encode = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(seconds=self.settings.jwt_refresh_expiry),
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        return jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            self.log_security_event("token_expired", {"token_type": "access"})
            return None
        except jwt.JWTError as e:
            self.log_security_event("token_invalid", {"error": str(e)})
            return None
    
    def encrypt_data(self, data: str) -> Optional[str]:
        """Encrypt sensitive data."""
        if not self.fernet:
            logger.warning("Encryption not configured")
            return data
        
        try:
            return self.fernet.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error("Encryption failed", error=str(e))
            return None
    
    def decrypt_data(self, encrypted_data: str) -> Optional[str]:
        """Decrypt sensitive data."""
        if not self.fernet:
            logger.warning("Encryption not configured")
            return encrypted_data
        
        try:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error("Decryption failed", error=str(e))
            return None
    
    def check_rate_limit(
        self,
        identifier: str,
        requests_per_minute: int = 60,
        window_minutes: int = 1
    ) -> bool:
        """Check if request is within rate limit."""
        current_time = time.time()
        window_start = current_time - (window_minutes * 60)
        
        # Get request history for identifier
        if identifier not in self.rate_limit_store:
            self.rate_limit_store[identifier] = []
        
        request_times = self.rate_limit_store[identifier]
        
        # Remove old requests outside window
        request_times[:] = [t for t in request_times if t > window_start]
        
        # Check if under limit
        if len(request_times) >= requests_per_minute:
            self.log_security_event("rate_limit_exceeded", {
                "identifier": identifier,
                "requests": len(request_times),
                "limit": requests_per_minute
            })
            return False
        
        # Add current request
        request_times.append(current_time)
        return True
    
    def validate_input(self, input_data: str, max_length: int = 4096) -> bool:
        """Validate user input for security."""
        if not input_data:
            return True
        
        # Check length
        if len(input_data) > max_length:
            self.log_security_event("input_too_long", {
                "length": len(input_data),
                "max_length": max_length
            })
            return False
        
        # Check for potential XSS
        xss_patterns = [
            "<script", "</script>", "javascript:", "onload=", "onerror=",
            "onclick=", "onmouseover=", "onfocus=", "<iframe", "</iframe>"
        ]
        
        input_lower = input_data.lower()
        for pattern in xss_patterns:
            if pattern in input_lower:
                self.log_security_event("xss_attempt", {
                    "pattern": pattern,
                    "input_length": len(input_data)
                })
                return False
        
        # Check for SQL injection patterns
        sql_patterns = [
            "union select", "drop table", "delete from", "insert into",
            "update set", "'or'1'='1", "';--", "/*", "*/"
        ]
        
        for pattern in sql_patterns:
            if pattern in input_lower:
                self.log_security_event("sql_injection_attempt", {
                    "pattern": pattern,
                    "input_length": len(input_data)
                })
                return False
        
        return True
    
    def sanitize_input(self, input_data: str) -> str:
        """Sanitize user input."""
        if not input_data:
            return input_data
        
        # Remove potential XSS characters
        sanitized = input_data.replace("<", "&lt;").replace(">", "&gt;")
        sanitized = sanitized.replace("\"", "&quot;").replace("'", "&#x27;")
        sanitized = sanitized.replace("&", "&amp;")
        
        return sanitized
    
    def generate_session_id(self) -> str:
        """Generate secure session ID."""
        return secrets.token_urlsafe(32)
    
    def generate_otp(self, length: int = 6) -> str:
        """Generate numeric OTP code."""
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])
    
    def hash_otp(self, otp: str, phone_number: str) -> str:
        """Create hash of OTP with phone number for verification."""
        combined = f"{otp}{phone_number}{self.jwt_secret}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def verify_otp_hash(self, otp: str, phone_number: str, otp_hash: str) -> bool:
        """Verify OTP against stored hash."""
        expected_hash = self.hash_otp(otp, phone_number)
        return secrets.compare_digest(expected_hash, otp_hash)
    
    def log_security_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """Log security event for audit."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "details": details,
            "user_id": user_id,
            "ip_address": ip_address,
            "severity": self._get_event_severity(event_type)
        }
        
        # Store in memory (in production, use secure audit database)
        self.security_events.append(event)
        
        # Log based on severity
        if event["severity"] == "high":
            logger.error("High severity security event", event=event)
        elif event["severity"] == "medium":
            logger.warning("Security event", event=event)
        else:
            logger.info("Security event", event=event)
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security events summary."""
        current_time = datetime.utcnow()
        
        # Count events by type in last 24 hours
        recent_events = [
            event for event in self.security_events
            if (current_time - datetime.fromisoformat(event["timestamp"])).total_seconds() < 86400
        ]
        
        event_counts = {}
        severity_counts = {"low": 0, "medium": 0, "high": 0}
        
        for event in recent_events:
            event_type = event["event_type"]
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            severity = event["severity"]
            severity_counts[severity] += 1
        
        return {
            "total_events_24h": len(recent_events),
            "event_types": event_counts,
            "severity_breakdown": severity_counts,
            "last_high_severity": self._get_last_high_severity_event(),
            "security_score": self._calculate_security_score()
        }
    
    def _get_event_severity(self, event_type: str) -> str:
        """Determine severity level for security event."""
        high_severity = [
            "sql_injection_attempt", "xss_attempt", "token_invalid",
            "multiple_login_failures", "unauthorized_access"
        ]
        
        medium_severity = [
            "rate_limit_exceeded", "token_expired", "input_too_long"
        ]
        
        if event_type in high_severity:
            return "high"
        elif event_type in medium_severity:
            return "medium"
        else:
            return "low"
    
    def _get_last_high_severity_event(self) -> Optional[Dict[str, Any]]:
        """Get most recent high severity security event."""
        high_severity_events = [
            event for event in self.security_events
            if event["severity"] == "high"
        ]
        
        if high_severity_events:
            return max(high_severity_events, key=lambda x: x["timestamp"])
        
        return None
    
    def _calculate_security_score(self) -> int:
        """Calculate security score based on recent events."""
        current_time = datetime.utcnow()
        
        # Events in last 24 hours
        recent_events = [
            event for event in self.security_events
            if (current_time - datetime.fromisoformat(event["timestamp"])).total_seconds() < 86400
        ]
        
        # Start with perfect score
        score = 100
        
        # Deduct points for security events
        for event in recent_events:
            if event["severity"] == "high":
                score -= 10
            elif event["severity"] == "medium":
                score -= 3
            else:
                score -= 1
        
        return max(0, score)  # Don't go below 0 