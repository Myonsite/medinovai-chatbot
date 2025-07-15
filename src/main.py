"""
MedinovAI Chatbot - Main Application Entry Point
HIPAA/GDPR Compliant AI-Powered Healthcare Assistant
"""

import asyncio
import sys
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from starlette.middleware.sessions import SessionMiddleware

# Import application modules
from orchestration.chat_orchestrator import ChatOrchestrator
from orchestration.websocket_manager import WebSocketManager
from api.routers import chat, health, webhooks, auth, admin
from utils.config import get_settings
from utils.database import init_database
from utils.logging_config import setup_logging
from utils.security import SecurityManager
from utils.phi_protection import PHIProtector
from utils.metrics import MetricsCollector

# Initialize logging
setup_logging()
logger = structlog.get_logger(__name__)

# Global instances
chat_orchestrator: ChatOrchestrator = None
websocket_manager: WebSocketManager = None
security_manager: SecurityManager = None
phi_protector: PHIProtector = None
metrics_collector: MetricsCollector = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown."""
    logger.info("🚀 Starting MedinovAI Chatbot...")
    
    global chat_orchestrator, websocket_manager, security_manager, \
        phi_protector, metrics_collector
    
    try:
        # Load configuration
        settings = get_settings()
        logger.info("✅ Configuration loaded", env=settings.environment)
        
        # Initialize database
        await init_database()
        logger.info("✅ Database initialized")
        
        # Initialize security manager
        security_manager = SecurityManager(settings)
        logger.info("✅ Security manager initialized")
        
        # Initialize PHI protector for HIPAA compliance
        phi_protector = PHIProtector(settings)
        await phi_protector.initialize()
        logger.info("✅ PHI protection initialized")
        
        # Initialize metrics collector
        metrics_collector = MetricsCollector()
        logger.info("✅ Metrics collector initialized")
        
        # Initialize WebSocket manager
        websocket_manager = WebSocketManager()
        logger.info("✅ WebSocket manager initialized")
        
        # Initialize chat orchestrator
        chat_orchestrator = ChatOrchestrator(
            settings=settings,
            phi_protector=phi_protector,
            metrics_collector=metrics_collector
        )
        await chat_orchestrator.initialize()
        logger.info("✅ Chat orchestrator initialized")
        
        # Verify external service connections
        await verify_external_services(settings)
        logger.info("✅ External services verified")
        
        logger.info("🎉 MedinovAI Chatbot started successfully!")
        
        yield  # Application is running
        
    except Exception as e:
        logger.error("❌ Failed to start application", error=str(e))
        raise
    
    finally:
        # Cleanup
        logger.info("🔄 Shutting down MedinovAI Chatbot...")
        
        if chat_orchestrator:
            await chat_orchestrator.cleanup()
        
        if websocket_manager:
            await websocket_manager.cleanup()
        
        logger.info("✅ MedinovAI Chatbot shutdown complete")


async def verify_external_services(settings) -> None:
    """Verify connectivity to external services."""
    try:
        # Test vector database connection
        if settings.rag_enabled:
            from retrieval.vector_store import VectorStore
            vector_store = VectorStore(settings)
            await vector_store.health_check()
            logger.info("✅ Vector database connection verified")
        
        # Test Mattermost connection
        if settings.mattermost_enabled:
            from adapters.mattermost_adapter import MattermostAdapter
            mattermost = MattermostAdapter(settings)
            await mattermost.health_check()
            logger.info("✅ Mattermost connection verified")
        
        # Test AI model connection
        from orchestration.ai_engine import AIEngine
        ai_engine = AIEngine(settings)
        await ai_engine.health_check()
        logger.info("✅ AI model connection verified")
        
    except Exception as e:
        logger.warning("⚠️ External service check failed", error=str(e))


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    # Create FastAPI app with lifespan
    app = FastAPI(
        title="MedinovAI Chatbot API",
        description="HIPAA-compliant AI-powered healthcare assistant",
        version="1.0.0",
        docs_url="/docs" if settings.development_mode else None,
        redoc_url="/redoc" if settings.development_mode else None,
        openapi_url="/openapi.json" if settings.development_mode else None,
        lifespan=lifespan
    )
    
    # Add security middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Add session middleware for authentication
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
        max_age=settings.session_max_age,
        same_site="strict",
        https_only=not settings.development_mode
    )
    
    # Add custom middleware for security and logging
    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        """Security and logging middleware."""
        # Generate request ID for tracing
        request_id = security_manager.generate_request_id()
        request.state.request_id = request_id
        
        # Log request start
        logger.info(
            "📥 Request started",
            request_id=request_id,
            method=request.method,
            url=str(request.url),
            user_agent=request.headers.get("user-agent", ""),
            client_ip=request.client.host
        )
        
        # Record metrics
        metrics_collector.record_request_start(
            request.method, str(request.url.path)
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Log successful response
            response_time = getattr(
                request.state, "response_time_ms", 0
            )
            logger.info(
                "📤 Request completed",
                request_id=request_id,
                status_code=response.status_code,
                response_time_ms=response_time
            )
            
            # Record metrics
            metrics_collector.record_request_end(
                request.method,
                str(request.url.path),
                response.status_code
            )
            
            return response
            
        except Exception as e:
            # Log error
            logger.error(
                "❌ Request failed",
                request_id=request_id,
                error=str(e),
                exc_info=True
            )
            
            # Record error metrics
            metrics_collector.record_request_error(
                request.method,
                str(request.url.path),
                type(e).__name__
            )
            
            # Return HIPAA-compliant error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "message": "An error occurred while processing your request"
                }
            )
    
    # Include API routers
    app.include_router(health.router, prefix="/api", tags=["Health"])
    app.include_router(chat.router, prefix="/api", tags=["Chat"])
    app.include_router(auth.router, prefix="/api", tags=["Authentication"])
    app.include_router(webhooks.router, prefix="/api", tags=["Webhooks"])
    app.include_router(admin.router, prefix="/api", tags=["Admin"])
    
    # Add Prometheus metrics endpoint
    if settings.prometheus_enabled:
        metrics_app = make_asgi_app()
        app.mount("/metrics", metrics_app)
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler for HIPAA-compliant error responses."""
        request_id = getattr(request.state, "request_id", "unknown")
        
        logger.error(
            "🚨 Unhandled exception",
            request_id=request_id,
            error=str(exc),
            exc_info=True
        )
        
        # Never expose internal details in production
        if settings.development_mode:
            detail = str(exc)
        else:
            detail = "An internal error occurred"
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": detail,
                "request_id": request_id
            }
        )
    
    # Health check endpoints
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "service": "MedinovAI Chatbot",
            "version": "1.0.0",
            "status": "healthy",
            "environment": settings.environment
        }
    
    @app.get("/api/health")
    async def health_check():
        """Health check endpoint."""
        return await health.get_health_status()
    
    return app


# Create the FastAPI application
app = create_app()


async def main():
    """Main entry point for running the application."""
    settings = get_settings()
    
    logger.info(
        "🚀 Starting MedinovAI Chatbot server",
        host=settings.api_host,
        port=settings.api_port,
        environment=settings.environment
    )
    
    # Configure uvicorn
    config = uvicorn.Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        access_log=settings.development_mode,
        reload=settings.development_mode,
        workers=1 if settings.development_mode else settings.api_workers
    )
    
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error("❌ Server error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    # Run the application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Goodbye!")
    except Exception as e:
        logger.error("❌ Application failed to start", error=str(e))
        sys.exit(1) 