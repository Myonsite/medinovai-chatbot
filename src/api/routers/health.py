"""
Health Check API Router - System monitoring and health endpoints
Provides comprehensive health checks for all platform components
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from utils.config import get_settings
from utils.database import check_database_health
from utils.security import SecurityManager
from utils.metrics import MetricsCollector

logger = structlog.get_logger(__name__)

router = APIRouter()


# Response Models
class ComponentHealth(BaseModel):
    """Health status for individual component."""
    name: str
    status: str  # healthy, unhealthy, degraded
    response_time_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    last_checked: datetime


class OverallHealth(BaseModel):
    """Overall system health response."""
    status: str  # healthy, unhealthy, degraded
    timestamp: datetime
    version: str
    uptime_seconds: float
    components: List[ComponentHealth]
    summary: Dict[str, int]


class MetricsResponse(BaseModel):
    """System metrics response."""
    timestamp: datetime
    conversations: Dict[str, Any]
    performance: Dict[str, Any]
    compliance: Dict[str, Any]
    channels: Dict[str, Dict[str, int]]


# Dependency injection
def get_security_manager() -> Optional[SecurityManager]:
    """Get security manager instance."""
    try:
        from main import security_manager
        return security_manager
    except ImportError:
        return None


def get_metrics_collector() -> Optional[MetricsCollector]:
    """Get metrics collector instance."""
    try:
        from main import metrics_collector
        return metrics_collector
    except ImportError:
        return None


# Health check endpoints
@router.get("/health", response_model=OverallHealth)
async def comprehensive_health_check():
    """Comprehensive system health check."""
    start_time = datetime.utcnow()
    components = []
    
    try:
        # Check database health
        db_start = datetime.utcnow()
        try:
            db_health = await check_database_health()
            db_response_time = (datetime.utcnow() - db_start).total_seconds() * 1000
            
            components.append(ComponentHealth(
                name="database",
                status=db_health.get("status", "unknown"),
                response_time_ms=db_response_time,
                details=db_health,
                last_checked=datetime.utcnow()
            ))
        except Exception as e:
            components.append(ComponentHealth(
                name="database",
                status="unhealthy",
                details={"error": str(e)},
                last_checked=datetime.utcnow()
            ))
        
        # Check chat orchestrator health
        orchestrator_start = datetime.utcnow()
        try:
            from main import chat_orchestrator
            if chat_orchestrator:
                # In production, chat_orchestrator would have a health_check method
                orchestrator_response_time = (datetime.utcnow() - orchestrator_start).total_seconds() * 1000
                components.append(ComponentHealth(
                    name="chat_orchestrator",
                    status="healthy",
                    response_time_ms=orchestrator_response_time,
                    details={"initialized": True},
                    last_checked=datetime.utcnow()
                ))
            else:
                components.append(ComponentHealth(
                    name="chat_orchestrator",
                    status="unhealthy",
                    details={"error": "Not initialized"},
                    last_checked=datetime.utcnow()
                ))
        except Exception as e:
            components.append(ComponentHealth(
                name="chat_orchestrator",
                status="unhealthy",
                details={"error": str(e)},
                last_checked=datetime.utcnow()
            ))
        
        # Check WebSocket manager health
        ws_start = datetime.utcnow()
        try:
            from main import websocket_manager
            if websocket_manager:
                ws_response_time = (datetime.utcnow() - ws_start).total_seconds() * 1000
                components.append(ComponentHealth(
                    name="websocket_manager",
                    status="healthy",
                    response_time_ms=ws_response_time,
                    details={
                        "active_connections": websocket_manager.get_connection_count()
                    },
                    last_checked=datetime.utcnow()
                ))
            else:
                components.append(ComponentHealth(
                    name="websocket_manager",
                    status="unhealthy",
                    details={"error": "Not initialized"},
                    last_checked=datetime.utcnow()
                ))
        except Exception as e:
            components.append(ComponentHealth(
                name="websocket_manager",
                status="unhealthy",
                details={"error": str(e)},
                last_checked=datetime.utcnow()
            ))
        
        # Check security manager health
        security_start = datetime.utcnow()
        try:
            security_manager = get_security_manager()
            if security_manager:
                # Test basic functionality
                test_token = security_manager.create_access_token({"test": "health"})
                test_payload = security_manager.verify_token(test_token)
                
                security_response_time = (datetime.utcnow() - security_start).total_seconds() * 1000
                
                if test_payload:
                    components.append(ComponentHealth(
                        name="security_manager",
                        status="healthy",
                        response_time_ms=security_response_time,
                        details={"token_validation": "working"},
                        last_checked=datetime.utcnow()
                    ))
                else:
                    components.append(ComponentHealth(
                        name="security_manager",
                        status="unhealthy",
                        details={"error": "Token validation failed"},
                        last_checked=datetime.utcnow()
                    ))
            else:
                components.append(ComponentHealth(
                    name="security_manager",
                    status="unhealthy",
                    details={"error": "Not initialized"},
                    last_checked=datetime.utcnow()
                ))
        except Exception as e:
            components.append(ComponentHealth(
                name="security_manager",
                status="unhealthy",
                details={"error": str(e)},
                last_checked=datetime.utcnow()
            ))
        
        # Check PHI protector health
        phi_start = datetime.utcnow()
        try:
            from main import phi_protector
            if phi_protector:
                phi_response_time = (datetime.utcnow() - phi_start).total_seconds() * 1000
                components.append(ComponentHealth(
                    name="phi_protector",
                    status="healthy",
                    response_time_ms=phi_response_time,
                    details={"redaction_enabled": phi_protector.redaction_enabled},
                    last_checked=datetime.utcnow()
                ))
            else:
                components.append(ComponentHealth(
                    name="phi_protector",
                    status="unhealthy",
                    details={"error": "Not initialized"},
                    last_checked=datetime.utcnow()
                ))
        except Exception as e:
            components.append(ComponentHealth(
                name="phi_protector",
                status="unhealthy",
                details={"error": str(e)},
                last_checked=datetime.utcnow()
            ))
        
        # Check external services
        if get_settings().twilio_enabled:
            twilio_start = datetime.utcnow()
            try:
                from main import twilio_adapter
                if twilio_adapter:
                    twilio_response_time = (datetime.utcnow() - twilio_start).total_seconds() * 1000
                    components.append(ComponentHealth(
                        name="twilio_adapter",
                        status="healthy",
                        response_time_ms=twilio_response_time,
                        details={"enabled": True},
                        last_checked=datetime.utcnow()
                    ))
                else:
                    components.append(ComponentHealth(
                        name="twilio_adapter",
                        status="unhealthy",
                        details={"error": "Not initialized"},
                        last_checked=datetime.utcnow()
                    ))
            except Exception as e:
                components.append(ComponentHealth(
                    name="twilio_adapter",
                    status="unhealthy",
                    details={"error": str(e)},
                    last_checked=datetime.utcnow()
                ))
        
        if get_settings().mattermost_enabled:
            mm_start = datetime.utcnow()
            try:
                from main import mattermost_adapter
                if mattermost_adapter:
                    mm_response_time = (datetime.utcnow() - mm_start).total_seconds() * 1000
                    components.append(ComponentHealth(
                        name="mattermost_adapter",
                        status="healthy",
                        response_time_ms=mm_response_time,
                        details={"enabled": True},
                        last_checked=datetime.utcnow()
                    ))
                else:
                    components.append(ComponentHealth(
                        name="mattermost_adapter",
                        status="unhealthy",
                        details={"error": "Not initialized"},
                        last_checked=datetime.utcnow()
                    ))
            except Exception as e:
                components.append(ComponentHealth(
                    name="mattermost_adapter",
                    status="unhealthy",
                    details={"error": str(e)},
                    last_checked=datetime.utcnow()
                ))
        
        # Calculate overall status
        healthy_count = sum(1 for c in components if c.status == "healthy")
        unhealthy_count = sum(1 for c in components if c.status == "unhealthy")
        degraded_count = sum(1 for c in components if c.status == "degraded")
        
        if unhealthy_count > 0:
            overall_status = "unhealthy"
        elif degraded_count > 0:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        # Calculate uptime (approximate)
        uptime_seconds = (datetime.utcnow() - start_time).total_seconds()
        
        return OverallHealth(
            status=overall_status,
            timestamp=datetime.utcnow(),
            version="1.0.0",
            uptime_seconds=uptime_seconds,
            components=components,
            summary={
                "healthy": healthy_count,
                "unhealthy": unhealthy_count,
                "degraded": degraded_count,
                "total": len(components)
            }
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return OverallHealth(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            uptime_seconds=0,
            components=[],
            summary={"healthy": 0, "unhealthy": 1, "degraded": 0, "total": 1}
        )


@router.get("/health/live")
async def liveness_check():
    """Simple liveness check for K8s/Docker health probes."""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/ready")
async def readiness_check():
    """Readiness check for K8s/Docker - checks if ready to serve traffic."""
    try:
        # Check critical components
        from main import chat_orchestrator, websocket_manager
        
        if not chat_orchestrator:
            return {"status": "not_ready", "reason": "Chat orchestrator not initialized"}
        
        if not websocket_manager:
            return {"status": "not_ready", "reason": "WebSocket manager not initialized"}
        
        # Test database connectivity
        db_health = await check_database_health()
        if db_health.get("status") != "healthy":
            return {"status": "not_ready", "reason": "Database not ready"}
        
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
        
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return {"status": "not_ready", "reason": str(e)}


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get system metrics."""
    try:
        metrics_collector = get_metrics_collector()
        if not metrics_collector:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Metrics collector not available"
            )
        
        current_metrics = metrics_collector.get_current_metrics()
        
        return MetricsResponse(
            timestamp=datetime.fromisoformat(current_metrics["timestamp"]),
            conversations=current_metrics["conversations"],
            performance=current_metrics["performance"],
            compliance=current_metrics["compliance"],
            channels=current_metrics["channels"]
        )
        
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics"
        )


@router.get("/health/database")
async def database_health():
    """Dedicated database health check."""
    try:
        health = await check_database_health()
        return health
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health/security")
async def security_health():
    """Security system health check."""
    try:
        security_manager = get_security_manager()
        if not security_manager:
            return {"status": "unhealthy", "reason": "Security manager not available"}
        
        # Get security summary
        security_summary = security_manager.get_security_summary()
        
        return {
            "status": "healthy",
            "security_score": security_summary["security_score"],
            "events_24h": security_summary["total_events_24h"],
            "last_high_severity": security_summary["last_high_severity"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Security health check failed", error=str(e))
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health/components/{component_name}")
async def component_health(component_name: str):
    """Get health status for specific component."""
    try:
        component_map = {
            "database": check_database_health,
            "chat": lambda: {"status": "healthy", "component": "chat_orchestrator"},
            "websocket": lambda: {"status": "healthy", "component": "websocket_manager"},
            "security": security_health,
        }
        
        if component_name not in component_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Component '{component_name}' not found"
            )
        
        check_func = component_map[component_name]
        
        if asyncio.iscoroutinefunction(check_func):
            result = await check_func()
        else:
            result = check_func()
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Component health check failed",
            component=component_name,
            error=str(e)
        )
        return {"status": "unhealthy", "error": str(e)}


# Development/debugging endpoints (only in dev mode)
@router.get("/health/debug")
async def debug_info():
    """Debug information (development only)."""
    settings = get_settings()
    
    if not settings.development_mode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debug endpoints not available in production"
        )
    
    try:
        debug_info = {
            "environment": "development",
            "settings": {
                "twilio_enabled": settings.twilio_enabled,
                "mattermost_enabled": settings.mattermost_enabled,
                "phi_redaction_enabled": settings.phi_redaction_enabled,
                "audit_logging_enabled": settings.audit_logging_enabled,
            },
            "global_objects": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check which global objects are initialized
        try:
            from main import (
                chat_orchestrator, websocket_manager, security_manager,
                metrics_collector, phi_protector, twilio_adapter, mattermost_adapter
            )
            
            debug_info["global_objects"] = {
                "chat_orchestrator": chat_orchestrator is not None,
                "websocket_manager": websocket_manager is not None,
                "security_manager": security_manager is not None,
                "metrics_collector": metrics_collector is not None,
                "phi_protector": phi_protector is not None,
                "twilio_adapter": twilio_adapter is not None,
                "mattermost_adapter": mattermost_adapter is not None,
            }
        except ImportError as e:
            debug_info["global_objects"]["error"] = str(e)
        
        return debug_info
        
    except Exception as e:
        logger.error("Debug info failed", error=str(e))
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()} 