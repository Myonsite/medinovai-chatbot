"""
Main Application - MedinovAI Healthcare Chatbot Platform
Production-ready FastAPI application with full healthcare AI capabilities
"""

import asyncio
import signal
import sys
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any

import structlog
import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Core components
from orchestration.chat_orchestrator import ChatOrchestrator
from orchestration.websocket_manager import WebSocketManager
from utils.config import get_settings, Settings
from utils.database import init_database, check_database_health
from utils.security import SecurityManager
from utils.metrics import MetricsCollector
from utils.phi_protection import PHIProtector

# API routers
from api.routers.chat import router as chat_router
from api.routers.auth import router as auth_router
from api.routers.health import router as health_router

# External adapters
from adapters.twilio_adapter import TwilioAdapter
from adapters.mattermost_adapter import MattermostAdapter

# Configure logging
logger = structlog.get_logger(__name__)

# Global component instances
chat_orchestrator: ChatOrchestrator = None
websocket_manager: WebSocketManager = None
security_manager: SecurityManager = None
metrics_collector: MetricsCollector = None
phi_protector: PHIProtector = None
twilio_adapter: TwilioAdapter = None
mattermost_adapter: MattermostAdapter = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting MedinovAI Healthcare Platform...")
    
    try:
        await startup_components()
        logger.info("MedinovAI Healthcare Platform started successfully")
        yield
    except Exception as e:
        logger.error("Failed to start application", error=str(e))
        sys.exit(1)
    finally:
        # Shutdown
        logger.info("Shutting down MedinovAI Healthcare Platform...")
        await shutdown_components()
        logger.info("MedinovAI Healthcare Platform shutdown complete")


async def startup_components():
    """Initialize all application components."""
    global chat_orchestrator, websocket_manager, security_manager
    global metrics_collector, phi_protector, twilio_adapter, mattermost_adapter
    
    settings = get_settings()
    
    # Initialize metrics collector first (needed by other components)
    metrics_collector = MetricsCollector()
    logger.info("Metrics collector initialized")
    
    # Initialize security manager
    security_manager = SecurityManager(settings)
    logger.info("Security manager initialized")
    
    # Initialize PHI protector
    phi_protector = PHIProtector(settings)
    await phi_protector.initialize()
    logger.info("PHI protector initialized")
    
    # Initialize database
    await init_database()
    logger.info("Database initialized")
    
    # Initialize external adapters
    if settings.twilio_enabled:
        twilio_adapter = TwilioAdapter(settings)
        await twilio_adapter.initialize()
        logger.info("Twilio adapter initialized")
    
    if settings.mattermost_enabled:
        mattermost_adapter = MattermostAdapter(settings)
        await mattermost_adapter.initialize()
        logger.info("Mattermost adapter initialized")
    
    # Initialize WebSocket manager
    websocket_manager = WebSocketManager()
    await websocket_manager.initialize()
    logger.info("WebSocket manager initialized")
    
    # Initialize chat orchestrator (depends on all above components)
    chat_orchestrator = ChatOrchestrator(
        settings=settings,
        phi_protector=phi_protector,
        metrics_collector=metrics_collector
    )
    await chat_orchestrator.initialize()
    logger.info("Chat orchestrator initialized")


async def shutdown_components():
    """Cleanup all application components."""
    global chat_orchestrator, websocket_manager, security_manager
    global metrics_collector, phi_protector, twilio_adapter, mattermost_adapter
    
    try:
        # Shutdown in reverse order
        if chat_orchestrator:
            await chat_orchestrator.cleanup()
            logger.info("Chat orchestrator cleaned up")
        
        if websocket_manager:
            await websocket_manager.cleanup()
            logger.info("WebSocket manager cleaned up")
        
        if mattermost_adapter:
            await mattermost_adapter.cleanup()
            logger.info("Mattermost adapter cleaned up")
        
        if twilio_adapter:
            await twilio_adapter.cleanup()
            logger.info("Twilio adapter cleaned up")
        
        logger.info("All components cleaned up successfully")
        
    except Exception as e:
        logger.error("Error during component cleanup", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="MedinovAI Healthcare Platform",
    description="HIPAA-compliant AI-powered healthcare conversation platform",
    version="1.0.0",
    docs_url="/docs" if get_settings().development_mode else None,
    redoc_url="/redoc" if get_settings().development_mode else None,
    lifespan=lifespan
)

# Middleware configuration
def configure_middleware(app: FastAPI, settings: Settings):
    """Configure application middleware."""
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Trusted host middleware (security)
    if settings.trusted_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.trusted_hosts
        )
    
    # Security headers middleware
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        
        return response
    
    # Request logging and metrics middleware
    @app.middleware("http")
    async def logging_and_metrics(request: Request, call_next):
        start_time = datetime.utcnow()
        request_id = security_manager.generate_request_id() if security_manager else "unknown"
        
        # Add request ID to context
        request.state.request_id = request_id
        
        try:
            # Rate limiting check
            client_ip = request.client.host if request.client else "unknown"
            if security_manager and not security_manager.check_rate_limit(client_ip):
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Log request
            logger.info(
                "HTTP request processed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                response_time_ms=response_time,
                request_id=request_id,
                client_ip=client_ip
            )
            
            # Record metrics
            if metrics_collector:
                metrics_collector.record_request_end(
                    request.method,
                    request.url.path,
                    response.status_code
                )
            
            return response
            
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.error(
                "HTTP request failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                response_time_ms=response_time,
                request_id=request_id,
                client_ip=client_ip
            )
            
            # Record error metrics
            if metrics_collector:
                metrics_collector.record_request_error(
                    request.method,
                    request.url.path,
                    type(e).__name__
                )
            
            raise


# Configure middleware
configure_middleware(app, get_settings())

# Include API routers
app.include_router(auth_router, prefix="/api/v1", tags=["Authentication"])
app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])
app.include_router(health_router, prefix="/api/v1", tags=["Health"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "MedinovAI Healthcare Platform",
        "version": "1.0.0",
        "description": "HIPAA-compliant AI-powered healthcare conversation platform",
        "documentation": "/docs" if get_settings().development_mode else None,
        "health_check": "/api/v1/health",
        "timestamp": datetime.utcnow().isoformat()
    }


# Metrics endpoint for Prometheus
@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with security logging."""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    # Log the exception
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        request_id=request_id,
        exc_info=True
    )
    
    # Log security event for certain exceptions
    if security_manager and isinstance(exc, (HTTPException,)):
        if exc.status_code in [401, 403, 429]:
            security_manager.log_security_event(
                "security_exception",
                {
                    "status_code": exc.status_code,
                    "path": request.url.path,
                    "detail": str(exc.detail) if hasattr(exc, 'detail') else str(exc)
                },
                ip_address=request.client.host if request.client else None
            )
    
    # Return appropriate error response
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "HTTP Exception",
                "detail": exc.detail,
                "request_id": request_id
            }
        )
    
    # For unexpected errors, don't expose internal details
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred. Please try again later.",
            "request_id": request_id
        }
    )


# Signal handlers for graceful shutdown
def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        # The lifespan context manager will handle cleanup
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


# Development server runner
def run_development_server():
    """Run development server with auto-reload."""
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.development_mode,
        log_level="info" if settings.development_mode else "warning",
        access_log=settings.development_mode
    )


# Production server configuration
def get_production_config() -> Dict[str, Any]:
    """Get production server configuration."""
    settings = get_settings()
    
    return {
        "host": settings.server_host,
        "port": settings.server_port,
        "workers": settings.server_workers,
        "worker_class": "uvicorn.workers.UvicornWorker",
        "worker_connections": 1000,
        "max_requests": 1000,
        "max_requests_jitter": 100,
        "preload_app": True,
        "keepalive": 5,
        "timeout": 30,
        "graceful_timeout": 30,
        "log_level": "info",
        "access_log": True,
        "error_log": "-",
        "access_log_format": '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s',
        "bind": f"{settings.server_host}:{settings.server_port}"
    }


if __name__ == "__main__":
    # Setup signal handlers
    setup_signal_handlers()
    
    # Run appropriate server based on environment
    settings = get_settings()
    
    if settings.development_mode:
        logger.info("Starting development server...")
        run_development_server()
    else:
        logger.info("For production, use gunicorn with the configuration from get_production_config()")
        logger.info("Example: gunicorn main:app -c gunicorn.conf.py")
        # In production, this would be handled by gunicorn or similar WSGI server 