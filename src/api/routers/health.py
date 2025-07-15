"""
Health Check Router for MedinovAI Chatbot API
Provides system health status and monitoring endpoints
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from utils.config import get_settings
from utils.database import check_database_health
from utils.logging_config import log_api_request

router = APIRouter()


class HealthStatus(BaseModel):
    """Health status response model."""
    status: str
    timestamp: str
    version: str
    environment: str
    uptime_seconds: float
    services: Dict[str, Any]
    compliance: Dict[str, bool]


class ServiceHealth(BaseModel):
    """Individual service health model."""
    name: str
    status: str
    response_time_ms: float
    details: Dict[str, Any] = {}


# Track application start time for uptime calculation
app_start_time = datetime.utcnow()


async def check_ai_service_health() -> ServiceHealth:
    """Check AI service health."""
    start_time = datetime.utcnow()
    
    try:
        # Simple health check - in production, test actual AI model
        await asyncio.sleep(0.1)  # Simulate AI call
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return ServiceHealth(
            name="ai_service",
            status="healthy",
            response_time_ms=response_time,
            details={
                "model": "gpt-4",
                "provider": "openai",
                "available": True
            }
        )
    except Exception as e:
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return ServiceHealth(
            name="ai_service",
            status="unhealthy",
            response_time_ms=response_time,
            details={
                "error": str(e),
                "available": False
            }
        )


async def check_vector_db_health() -> ServiceHealth:
    """Check vector database health."""
    start_time = datetime.utcnow()
    settings = get_settings()
    
    try:
        # Test vector database connection
        if settings.rag_enabled:
            # In production, test actual vector DB connection
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.vector_db_url}/api/v1/heartbeat",
                    timeout=5.0
                )
                response.raise_for_status()
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return ServiceHealth(
            name="vector_database",
            status="healthy" if settings.rag_enabled else "disabled",
            response_time_ms=response_time,
            details={
                "provider": settings.vector_db_provider,
                "collection": settings.vector_db_collection,
                "enabled": settings.rag_enabled
            }
        )
    except Exception as e:
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return ServiceHealth(
            name="vector_database",
            status="unhealthy",
            response_time_ms=response_time,
            details={
                "error": str(e),
                "enabled": settings.rag_enabled
            }
        )


async def check_mattermost_health() -> ServiceHealth:
    """Check Mattermost integration health."""
    start_time = datetime.utcnow()
    settings = get_settings()
    
    try:
        if settings.mattermost_enabled:
            # Test Mattermost connection
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.mattermost_url}/api/v4/system/ping",
                    timeout=5.0
                )
                response.raise_for_status()
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return ServiceHealth(
            name="mattermost",
            status="healthy" if settings.mattermost_enabled else "disabled",
            response_time_ms=response_time,
            details={
                "url": settings.mattermost_url if settings.mattermost_enabled else None,
                "enabled": settings.mattermost_enabled
            }
        )
    except Exception as e:
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return ServiceHealth(
            name="mattermost",
            status="unhealthy",
            response_time_ms=response_time,
            details={
                "error": str(e),
                "enabled": settings.mattermost_enabled
            }
        )


async def check_redis_health() -> ServiceHealth:
    """Check Redis cache health."""
    start_time = datetime.utcnow()
    settings = get_settings()
    
    try:
        # Test Redis connection
        import redis.asyncio as redis
        
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return ServiceHealth(
            name="redis",
            status="healthy",
            response_time_ms=response_time,
            details={
                "url": settings.redis_url,
                "connected": True
            }
        )
    except Exception as e:
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return ServiceHealth(
            name="redis",
            status="unhealthy",
            response_time_ms=response_time,
            details={
                "error": str(e),
                "connected": False
            }
        )


@router.get("/health", response_model=HealthStatus)
async def get_health_status():
    """Get comprehensive system health status."""
    settings = get_settings()
    current_time = datetime.utcnow()
    uptime = (current_time - app_start_time).total_seconds()
    
    # Check all services in parallel
    database_health_task = asyncio.create_task(check_database_health())
    ai_health_task = asyncio.create_task(check_ai_service_health())
    vector_db_health_task = asyncio.create_task(check_vector_db_health())
    mattermost_health_task = asyncio.create_task(check_mattermost_health())
    redis_health_task = asyncio.create_task(check_redis_health())
    
    # Wait for all health checks
    database_health = await database_health_task
    ai_health = await ai_health_task
    vector_db_health = await vector_db_health_task
    mattermost_health = await mattermost_health_task
    redis_health = await redis_health_task
    
    # Compile services status
    services = {
        "database": database_health,
        "ai_service": ai_health.dict(),
        "vector_database": vector_db_health.dict(),
        "mattermost": mattermost_health.dict(),
        "redis": redis_health.dict()
    }
    
    # Determine overall status
    unhealthy_services = [
        name for name, service in services.items()
        if (isinstance(service, dict) and service.get("status") == "unhealthy")
        or (isinstance(service, dict) and service.get("status") == "unhealthy")
    ]
    
    overall_status = "unhealthy" if unhealthy_services else "healthy"
    
    # Compliance status
    compliance = {
        "hipaa": settings.phi_redaction_enabled and settings.audit_logging_enabled,
        "gdpr": settings.gdpr_enabled and settings.consent_required,
        "encryption": bool(settings.encryption_key),
        "audit_logging": settings.audit_logging_enabled,
        "phi_redaction": settings.phi_redaction_enabled
    }
    
    return HealthStatus(
        status=overall_status,
        timestamp=current_time.isoformat(),
        version="1.0.0",
        environment=settings.environment,
        uptime_seconds=uptime,
        services=services,
        compliance=compliance
    )


@router.get("/health/database")
async def get_database_health():
    """Get database-specific health status."""
    return await check_database_health()


@router.get("/health/ai")
async def get_ai_health():
    """Get AI service health status."""
    return await check_ai_service_health()


@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe endpoint."""
    settings = get_settings()
    
    # Check critical services for readiness
    try:
        # Quick database check
        db_health = await check_database_health()
        if db_health["status"] != "healthy":
            raise HTTPException(status_code=503, detail="Database not ready")
        
        # Quick Redis check
        redis_health = await check_redis_health()
        if redis_health.status != "healthy":
            raise HTTPException(status_code=503, detail="Redis not ready")
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service not ready: {str(e)}"
        )


@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe endpoint."""
    # Simple liveness check - if this endpoint responds, the app is alive
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": (datetime.utcnow() - app_start_time).total_seconds()
    }


@router.get("/health/metrics")
async def get_health_metrics():
    """Get detailed health metrics for monitoring."""
    settings = get_settings()
    
    # Get all service health in parallel
    tasks = {
        "database": check_database_health(),
        "ai_service": check_ai_service_health(),
        "vector_db": check_vector_db_health(),
        "mattermost": check_mattermost_health(),
        "redis": check_redis_health()
    }
    
    results = {}
    for name, task in tasks.items():
        try:
            result = await task
            if isinstance(result, ServiceHealth):
                results[name] = {
                    "status": result.status,
                    "response_time_ms": result.response_time_ms,
                    "last_check": datetime.utcnow().isoformat()
                }
            else:
                results[name] = {
                    "status": result.get("status", "unknown"),
                    "response_time_ms": 0,
                    "last_check": datetime.utcnow().isoformat()
                }
        except Exception as e:
            results[name] = {
                "status": "error",
                "error": str(e),
                "response_time_ms": 0,
                "last_check": datetime.utcnow().isoformat()
            }
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.environment,
        "version": "1.0.0",
        "services": results,
        "system": {
            "uptime_seconds": (datetime.utcnow() - app_start_time).total_seconds(),
            "memory_usage": "N/A",  # In production, add actual memory metrics
            "cpu_usage": "N/A"      # In production, add actual CPU metrics
        }
    } 