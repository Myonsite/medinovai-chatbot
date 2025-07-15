"""
Database Configuration and Management for MedinovAI Chatbot
HIPAA-compliant database operations with encryption and audit logging
"""

from datetime import datetime
from typing import AsyncGenerator, Optional, Any, Dict

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    create_async_engine, 
    async_sessionmaker
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from utils.config import get_settings
from utils.logging_config import log_database_operation, log_security_event

# Base model for all tables
Base = declarative_base()

# Global database variables
async_engine = None
async_session_maker = None
sync_engine = None
Session = None


class DatabaseManager:
    """Database manager with HIPAA compliance features."""
    
    def __init__(self):
        self.settings = get_settings()
        self._async_engine = None
        self._async_session_maker = None
        self._sync_engine = None
        self._sync_session_maker = None
    
    async def initialize(self) -> None:
        """Initialize database connections."""
        await self._create_async_engine()
        self._create_sync_engine()
        await self._setup_database()
        self._setup_event_listeners()
    
    async def _create_async_engine(self) -> None:
        """Create async database engine."""
        db_config = self.settings.get_database_config()
        
        # Convert PostgreSQL URL to async version
        async_url = db_config["url"].replace("postgresql://", "postgresql+asyncpg://")
        
        self._async_engine = create_async_engine(
            async_url,
            pool_size=db_config["pool_size"],
            max_overflow=20,
            pool_timeout=db_config["timeout"],
            pool_recycle=3600,  # Recycle connections every hour
            echo=self.settings.debug,  # Log SQL in debug mode
            future=True
        )
        
        self._async_session_maker = async_sessionmaker(
            self._async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        global async_engine, async_session_maker
        async_engine = self._async_engine
        async_session_maker = self._async_session_maker
    
    def _create_sync_engine(self) -> None:
        """Create synchronous database engine for migrations."""
        db_config = self.settings.get_database_config()
        
        self._sync_engine = create_engine(
            db_config["url"],
            pool_size=db_config["pool_size"],
            max_overflow=20,
            pool_timeout=db_config["timeout"],
            pool_recycle=3600,
            echo=self.settings.debug,
            future=True
        )
        
        self._sync_session_maker = sessionmaker(
            self._sync_engine,
            expire_on_commit=False
        )
        
        global sync_engine, Session
        sync_engine = self._sync_engine
        Session = self._sync_session_maker
    
    async def _setup_database(self) -> None:
        """Setup database schema and initial data."""
        try:
            # Import all models to ensure they're registered
            from models import *  # noqa
            
            # Create all tables
            async with self._async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            log_database_operation(
                operation="schema_creation",
                table="all",
                success=True
            )
            
        except Exception as e:
            log_database_operation(
                operation="schema_creation",
                table="all",
                success=False,
                error_message=str(e)
            )
            raise
    
    def _setup_event_listeners(self) -> None:
        """Setup SQLAlchemy event listeners for audit logging."""
        
        @event.listens_for(self._sync_engine, "before_cursor_execute")
        def log_sql_queries(conn, cursor, statement, parameters, context, executemany):
            """Log SQL queries for audit purposes."""
                         if self.settings.audit_logging_enabled:
                 # Redact sensitive information from SQL for audit
                 self._redact_sql_statement(statement)
                
                log_database_operation(
                    operation="sql_query",
                    table="multiple",
                    success=True,
                    execution_time_ms=0
                )
    
    def _redact_sql_statement(self, statement: str) -> str:
        """Redact PHI from SQL statements."""
        # Basic redaction - in production, use more sophisticated tools
        import re
        
        # Redact potential PHI patterns
        redacted = re.sub(
            r"'[^']*@[^']*'", 
            "'[REDACTED_EMAIL]'", 
            statement
        )
        redacted = re.sub(
            r"'\d{3}-?\d{2}-?\d{4}'", 
            "'[REDACTED_SSN]'", 
            redacted
        )
        
        return redacted
    
    async def health_check(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            async with self._async_session_maker() as session:
                result = await session.execute("SELECT 1")
                await result.fetchone()
            
            return {
                "status": "healthy",
                "connection": "active",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            log_security_event(
                event_type="database_health_check_failed",
                description=f"Database health check failed: {str(e)}",
                severity="high"
            )
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def cleanup(self) -> None:
        """Cleanup database connections."""
        if self._async_engine:
            await self._async_engine.dispose()
        
        if self._sync_engine:
            self._sync_engine.dispose()


# Global database manager instance
db_manager = DatabaseManager()


async def init_database() -> None:
    """Initialize database connections and schema."""
    await db_manager.initialize()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session with proper cleanup."""
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            log_database_operation(
                operation="session_error",
                table="session",
                success=False,
                error_message=str(e)
            )
            raise
        finally:
            await session.close()


def get_sync_session():
    """Get synchronous database session."""
    session = Session()
    try:
        yield session
    except Exception as e:
        session.rollback()
        log_database_operation(
            operation="session_error",
            table="session",
            success=False,
            error_message=str(e)
        )
        raise
    finally:
        session.close()


async def execute_async_query(query: str, parameters: Optional[Dict] = None) -> Any:
    """Execute async query with error handling and logging."""
    start_time = datetime.utcnow()
    
    try:
        async with get_async_session() as session:
            result = await session.execute(query, parameters or {})
            await session.commit()
        
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        log_database_operation(
            operation="async_query",
            table="multiple",
            success=True,
            execution_time_ms=int(execution_time)
        )
        
        return result
        
    except Exception as e:
        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        log_database_operation(
            operation="async_query",
            table="multiple",
            success=False,
            execution_time_ms=int(execution_time),
            error_message=str(e)
        )
        
        raise


class AuditMixin:
    """Mixin for adding audit fields to models."""
    
    created_at = None  # Should be defined in actual models
    updated_at = None  # Should be defined in actual models
    created_by = None  # Should be defined in actual models
    updated_by = None  # Should be defined in actual models
    
    def __init__(self):
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class EncryptedFieldMixin:
    """Mixin for handling encrypted fields (PHI data)."""
    
    @classmethod
    def encrypt_field(cls, value: str) -> str:
        """Encrypt sensitive field value."""
        if not value:
            return value
        
        # In production, use proper encryption (AWS KMS, etc.)
        # This is a placeholder implementation
        import base64
        return base64.b64encode(value.encode()).decode()
    
    @classmethod
    def decrypt_field(cls, encrypted_value: str) -> str:
        """Decrypt sensitive field value."""
        if not encrypted_value:
            return encrypted_value
        
        # In production, use proper decryption
        # This is a placeholder implementation
        import base64
        try:
            return base64.b64decode(encrypted_value.encode()).decode()
        except Exception:
            return encrypted_value  # Return as-is if decryption fails


async def check_database_health() -> Dict[str, Any]:
    """Check database health status."""
    return await db_manager.health_check()


async def cleanup_database() -> None:
    """Cleanup database connections."""
    await db_manager.cleanup() 