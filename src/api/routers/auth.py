"""
Authentication API Router - Handles user authentication and authorization
Provides SMS OTP, JWT tokens, and multi-factor authentication for healthcare
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import structlog
from fastapi import (
    APIRouter, Depends, HTTPException, status, 
    Request, Response, Header, BackgroundTasks
)
from pydantic import BaseModel, Field, validator
import phonenumbers
from phonenumbers import NumberParseException

from utils.security import SecurityManager
from utils.config import get_settings
from adapters.twilio_adapter import TwilioAdapter

logger = structlog.get_logger(__name__)

router = APIRouter()

# Global instances
security_manager: Optional[SecurityManager] = None
twilio_adapter: Optional[TwilioAdapter] = None


# Request/Response Models
class SMSOTPRequest(BaseModel):
    """Request model for SMS OTP authentication."""
    phone_number: str = Field(..., min_length=10, max_length=20)
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        try:
            parsed = phonenumbers.parse(v, "US")
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Invalid phone number")
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except NumberParseException:
            raise ValueError("Invalid phone number format")


class VerifyOTPRequest(BaseModel):
    """Request model for OTP verification."""
    phone_number: str = Field(..., min_length=10, max_length=20)
    otp_code: str = Field(..., min_length=4, max_length=8, regex=r'^\d+$')
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        """Validate phone number format."""
        try:
            parsed = phonenumbers.parse(v, "US")
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Invalid phone number")
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except NumberParseException:
            raise ValueError("Invalid phone number format")


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str = Field(..., min_length=1)


class AuthResponse(BaseModel):
    """Response model for authentication."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    phone_number: str
    phone_verified: bool


class UserProfileRequest(BaseModel):
    """Request model for user profile update."""
    preferred_language: str = Field(default="en", regex=r'^[a-z]{2}$')
    communication_preferences: Dict[str, bool] = Field(default_factory=dict)
    accessibility_needs: List[str] = Field(default_factory=list)


class UserProfileResponse(BaseModel):
    """Response model for user profile."""
    user_id: str
    phone_number: str
    preferred_language: str
    communication_preferences: Dict[str, bool]
    accessibility_needs: List[str]
    phone_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime]


# Dependency injection
def get_security_manager() -> SecurityManager:
    """Get security manager instance."""
    global security_manager
    if not security_manager:
        from main import security_manager as main_security
        security_manager = main_security
    return security_manager


def get_twilio_adapter() -> TwilioAdapter:
    """Get Twilio adapter instance."""
    global twilio_adapter
    if not twilio_adapter:
        from main import twilio_adapter as main_twilio
        twilio_adapter = main_twilio
    return twilio_adapter


# In-memory storage for OTP codes (use Redis in production)
otp_storage: Dict[str, Dict[str, Any]] = {}
rate_limit_storage: Dict[str, List[datetime]] = {}


def check_rate_limit(phone_number: str, max_requests: int = 3, window_minutes: int = 15) -> bool:
    """Check if phone number is within rate limit for OTP requests."""
    current_time = datetime.utcnow()
    window_start = current_time - timedelta(minutes=window_minutes)
    
    if phone_number not in rate_limit_storage:
        rate_limit_storage[phone_number] = []
    
    # Remove old requests
    rate_limit_storage[phone_number] = [
        req_time for req_time in rate_limit_storage[phone_number]
        if req_time > window_start
    ]
    
    # Check limit
    if len(rate_limit_storage[phone_number]) >= max_requests:
        return False
    
    # Add current request
    rate_limit_storage[phone_number].append(current_time)
    return True


# Authentication endpoints
@router.post("/auth/sms/send-otp")
async def send_sms_otp(
    request: SMSOTPRequest,
    background_tasks: BackgroundTasks,
    security: SecurityManager = Depends(get_security_manager),
    twilio: TwilioAdapter = Depends(get_twilio_adapter)
):
    """Send SMS OTP for authentication."""
    try:
        # Rate limiting
        if not check_rate_limit(request.phone_number):
            logger.warning(
                "OTP rate limit exceeded",
                phone_number=request.phone_number[-4:]  # Log last 4 digits only
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many OTP requests. Please try again later."
            )
        
        # Generate OTP
        otp_code = security.generate_otp(length=6)
        otp_hash = security.hash_otp(otp_code, request.phone_number)
        
        # Store OTP with expiration (5 minutes)
        otp_storage[request.phone_number] = {
            "otp_hash": otp_hash,
            "expires_at": datetime.utcnow() + timedelta(minutes=5),
            "attempts": 0,
            "max_attempts": 3
        }
        
        # Send SMS in background
        background_tasks.add_task(
            send_otp_sms,
            twilio,
            request.phone_number,
            otp_code
        )
        
        # Log security event
        security.log_security_event(
            "otp_requested",
            {"phone_number_hash": security.hash_otp("", request.phone_number)},
            ip_address=None  # Would get from request in production
        )
        
        logger.info(
            "OTP sent successfully",
            phone_number=request.phone_number[-4:]
        )
        
        return {
            "message": "OTP sent successfully",
            "expires_in_minutes": 5
        }
        
    except Exception as e:
        logger.error("Failed to send OTP", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP"
        )


@router.post("/auth/sms/verify-otp", response_model=AuthResponse)
async def verify_sms_otp(
    request: VerifyOTPRequest,
    security: SecurityManager = Depends(get_security_manager)
):
    """Verify SMS OTP and return JWT tokens."""
    try:
        # Check if OTP exists
        if request.phone_number not in otp_storage:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No OTP found for this phone number"
            )
        
        otp_data = otp_storage[request.phone_number]
        
        # Check expiration
        if datetime.utcnow() > otp_data["expires_at"]:
            del otp_storage[request.phone_number]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired"
            )
        
        # Check attempt limit
        if otp_data["attempts"] >= otp_data["max_attempts"]:
            del otp_storage[request.phone_number]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum verification attempts exceeded"
            )
        
        # Verify OTP
        if not security.verify_otp_hash(
            request.otp_code,
            request.phone_number,
            otp_data["otp_hash"]
        ):
            otp_data["attempts"] += 1
            
            security.log_security_event(
                "otp_verification_failed",
                {"phone_number_hash": security.hash_otp("", request.phone_number)},
                ip_address=None
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP code"
            )
        
        # OTP verified successfully - clean up
        del otp_storage[request.phone_number]
        
        # Generate user ID (in production, create/lookup user in database)
        user_id = security.hash_otp("user", request.phone_number)[:16]
        
        # Create JWT tokens
        access_token = security.create_access_token(
            data={"sub": user_id, "phone": request.phone_number, "verified": True}
        )
        refresh_token = security.create_refresh_token(user_id)
        
        # Log successful authentication
        security.log_security_event(
            "authentication_success",
            {"phone_number_hash": security.hash_otp("", request.phone_number)},
            user_id=user_id,
            ip_address=None
        )
        
        logger.info(
            "OTP verification successful",
            user_id=user_id,
            phone_number=request.phone_number[-4:]
        )
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=get_settings().jwt_expiry,
            user_id=user_id,
            phone_number=request.phone_number,
            phone_verified=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("OTP verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OTP verification failed"
        )


@router.post("/auth/refresh", response_model=AuthResponse)
async def refresh_access_token(
    request: RefreshTokenRequest,
    security: SecurityManager = Depends(get_security_manager)
):
    """Refresh access token using refresh token."""
    try:
        # Verify refresh token
        payload = security.verify_token(request.refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # In production, verify user still exists and is active
        # For now, assume user is valid
        
        # Create new access token
        access_token = security.create_access_token(
            data={"sub": user_id, "verified": True}
        )
        
        # Optionally create new refresh token (rotation)
        new_refresh_token = security.create_refresh_token(user_id)
        
        logger.info("Access token refreshed", user_id=user_id)
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=get_settings().jwt_expiry,
            user_id=user_id,
            phone_number="",  # Not available from refresh token
            phone_verified=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.get("/auth/me", response_model=UserProfileResponse)
async def get_current_user(
    authorization: Optional[str] = Header(None),
    security: SecurityManager = Depends(get_security_manager)
):
    """Get current user profile."""
    try:
        # Extract token from Authorization header
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        token = authorization[7:]  # Remove "Bearer " prefix
        
        # Verify token
        payload = security.verify_token(token)
        if not payload or payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token"
            )
        
        user_id = payload.get("sub")
        phone_number = payload.get("phone", "")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # In production, load user profile from database
        # For now, return mock profile
        return UserProfileResponse(
            user_id=user_id,
            phone_number=phone_number,
            preferred_language="en",
            communication_preferences={"sms": True, "voice": True},
            accessibility_needs=[],
            phone_verified=True,
            created_at=datetime.utcnow(),
            last_login_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get user profile", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user profile"
        )


@router.put("/auth/profile", response_model=UserProfileResponse)
async def update_user_profile(
    request: UserProfileRequest,
    authorization: Optional[str] = Header(None),
    security: SecurityManager = Depends(get_security_manager)
):
    """Update user profile."""
    try:
        # Extract and verify token (same as get_current_user)
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )
        
        token = authorization[7:]
        payload = security.verify_token(token)
        if not payload or payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # In production, update user profile in database
        # For now, return updated mock profile
        
        logger.info(
            "User profile updated",
            user_id=user_id,
            language=request.preferred_language
        )
        
        return UserProfileResponse(
            user_id=user_id,
            phone_number=payload.get("phone", ""),
            preferred_language=request.preferred_language,
            communication_preferences=request.communication_preferences,
            accessibility_needs=request.accessibility_needs,
            phone_verified=True,
            created_at=datetime.utcnow(),
            last_login_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update user profile", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )


@router.post("/auth/logout")
async def logout_user(
    authorization: Optional[str] = Header(None),
    security: SecurityManager = Depends(get_security_manager)
):
    """Logout user (invalidate tokens)."""
    try:
        # In production, add token to blacklist
        # For now, just log the logout
        
        if authorization and authorization.startswith("Bearer "):
            token = authorization[7:]
            payload = security.verify_token(token)
            if payload:
                user_id = payload.get("sub")
                
                security.log_security_event(
                    "user_logout",
                    {},
                    user_id=user_id,
                    ip_address=None
                )
                
                logger.info("User logged out", user_id=user_id)
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error("Logout failed", error=str(e))
        return {"message": "Logout completed"}


# Helper functions
async def send_otp_sms(twilio: TwilioAdapter, phone_number: str, otp_code: str):
    """Send OTP via SMS (background task)."""
    try:
        message = f"Your MedinovAI verification code is: {otp_code}. This code expires in 5 minutes."
        
        success = await twilio.send_sms(
            to_number=phone_number,
            message=message
        )
        
        if success:
            logger.info(
                "OTP SMS sent successfully",
                phone_number=phone_number[-4:]
            )
        else:
            logger.error(
                "Failed to send OTP SMS",
                phone_number=phone_number[-4:]
            )
            
    except Exception as e:
        logger.error(
            "Error sending OTP SMS",
            phone_number=phone_number[-4:],
            error=str(e)
        )


# Health check
@router.get("/auth/health")
async def auth_health_check():
    """Health check for authentication system."""
    try:
        security = get_security_manager()
        if not security:
            return {"status": "unhealthy", "reason": "Security manager not available"}
        
        # Test token generation
        test_token = security.create_access_token({"test": "health_check"})
        test_payload = security.verify_token(test_token)
        
        if not test_payload:
            return {"status": "unhealthy", "reason": "Token generation/verification failed"}
        
        return {
            "status": "healthy",
            "active_otp_sessions": len(otp_storage),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Auth health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)} 