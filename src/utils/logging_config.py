"""
Logging Configuration for MedinovAI Chatbot
HIPAA-compliant structured logging with PHI redaction
"""

import logging
import logging.config
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import structlog
from pythonjsonlogger import jsonlogger


class PHIRedactionFilter(logging.Filter):
    """Filter to redact PHI from log messages."""
    
    # Common PHI patterns (basic implementation)
    PHI_PATTERNS = {
        "ssn": r"\b\d{3}-?\d{2}-?\d{4}\b",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "mrn": r"\bMRN[:\s]*\d+\b",
        "dob": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",
    }
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and redact PHI from log record."""
        if hasattr(record, 'msg'):
            message = str(record.msg)
            
            # Basic PHI redaction (in production, use more sophisticated tools)
            for phi_type, pattern in self.PHI_PATTERNS.items():
                import re
                message = re.sub(pattern, f"[REDACTED_{phi_type.upper()}]", message)
            
            record.msg = message
        
        return True


class HIPAAFormatter(jsonlogger.JsonFormatter):
    """HIPAA-compliant JSON formatter."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, 
                   message_dict: Dict[str, Any]) -> None:
        """Add HIPAA-required fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add HIPAA audit fields
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['service'] = 'medinovai-chatbot'
        log_record['environment'] = os.getenv('NODE_ENV', 'development')
        log_record['user_id'] = getattr(record, 'user_id', 'anonymous')
        log_record['session_id'] = getattr(record, 'session_id', None)
        log_record['request_id'] = getattr(record, 'request_id', None)
        log_record['ip_address'] = getattr(record, 'ip_address', None)
        log_record['action'] = getattr(record, 'action', None)
        log_record['resource'] = getattr(record, 'resource', None)
        log_record['outcome'] = getattr(record, 'outcome', None)
        
        # Add compliance metadata
        log_record['compliance'] = {
            'hipaa': True,
            'gdpr': True,
            'phi_redacted': True,
            'audit_trail': True
        }


def setup_logging() -> None:
    """Setup comprehensive logging configuration."""
    
    # Get environment variables
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    environment = os.getenv('NODE_ENV', 'development')
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Logging configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'hipaa_json': {
                '()': HIPAAFormatter,
                'format': '%(timestamp)s %(level)s %(name)s %(message)s'
            },
            'console': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'filters': {
            'phi_redaction': {
                '()': PHIRedactionFilter,
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'console' if environment == 'development' else 'hipaa_json',
                'filters': ['phi_redaction'],
                'stream': sys.stdout
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/medinovai-chatbot.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'formatter': 'hipaa_json',
                'filters': ['phi_redaction']
            },
            'audit': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/audit.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 50,  # Keep more audit logs
                'formatter': 'hipaa_json',
                'filters': ['phi_redaction']
            },
            'security': {
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': 'logs/security.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 20,
                'formatter': 'hipaa_json',
                'filters': ['phi_redaction']
            }
        },
        'loggers': {
            'medinovai': {
                'level': log_level,
                'handlers': ['console', 'file'],
                'propagate': False
            },
            'audit': {
                'level': 'INFO',
                'handlers': ['audit'],
                'propagate': False
            },
            'security': {
                'level': 'WARNING',
                'handlers': ['security', 'console'],
                'propagate': False
            },
            'uvicorn': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            },
            'fastapi': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            }
        },
        'root': {
            'level': log_level,
            'handlers': ['console']
        }
    }
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Setup additional loggers for specific components
    setup_component_loggers()


def setup_component_loggers() -> None:
    """Setup specialized loggers for different components."""
    
    # Chat interaction logger
    chat_logger = logging.getLogger('chat')
    chat_logger.setLevel(logging.INFO)
    
    # PHI access logger
    phi_logger = logging.getLogger('phi_access')
    phi_logger.setLevel(logging.WARNING)
    
    # API access logger
    api_logger = logging.getLogger('api')
    api_logger.setLevel(logging.INFO)
    
    # Database logger
    db_logger = logging.getLogger('database')
    db_logger.setLevel(logging.INFO)
    
    # External service logger
    external_logger = logging.getLogger('external')
    external_logger.setLevel(logging.INFO)


def get_audit_logger() -> logging.Logger:
    """Get the audit logger for HIPAA compliance."""
    return logging.getLogger('audit')


def get_security_logger() -> logging.Logger:
    """Get the security logger for security events."""
    return logging.getLogger('security')


def log_phi_access(user_id: str, action: str, resource: str, 
                   outcome: str, session_id: Optional[str] = None,
                   ip_address: Optional[str] = None) -> None:
    """Log PHI access for HIPAA audit trail."""
    audit_logger = get_audit_logger()
    
    audit_logger.info(
        "PHI Access Event",
        extra={
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'outcome': outcome,
            'session_id': session_id,
            'ip_address': ip_address,
            'event_type': 'phi_access',
            'compliance_category': 'hipaa_audit'
        }
    )


def log_security_event(event_type: str, description: str, 
                      severity: str = 'medium',
                      user_id: Optional[str] = None,
                      ip_address: Optional[str] = None,
                      additional_data: Optional[Dict[str, Any]] = None) -> None:
    """Log security events for monitoring and compliance."""
    security_logger = get_security_logger()
    
    log_data = {
        'event_type': event_type,
        'description': description,
        'severity': severity,
        'user_id': user_id,
        'ip_address': ip_address,
        'compliance_category': 'security_event'
    }
    
    if additional_data:
        log_data['additional_data'] = additional_data
    
    # Log at appropriate level based on severity
    if severity == 'critical':
        security_logger.critical(description, extra=log_data)
    elif severity == 'high':
        security_logger.error(description, extra=log_data)
    elif severity == 'medium':
        security_logger.warning(description, extra=log_data)
    else:
        security_logger.info(description, extra=log_data)


def log_chat_interaction(session_id: str, user_id: str, message_type: str,
                        channel: str, response_time_ms: Optional[int] = None,
                        escalated: bool = False) -> None:
    """Log chat interactions for analytics and compliance."""
    chat_logger = logging.getLogger('chat')
    
    chat_logger.info(
        "Chat Interaction",
        extra={
            'session_id': session_id,
            'user_id': user_id,
            'message_type': message_type,
            'channel': channel,
            'response_time_ms': response_time_ms,
            'escalated': escalated,
            'event_type': 'chat_interaction',
            'compliance_category': 'user_interaction'
        }
    )


def log_api_request(method: str, endpoint: str, status_code: int,
                   response_time_ms: int, user_id: Optional[str] = None,
                   request_id: Optional[str] = None,
                   ip_address: Optional[str] = None) -> None:
    """Log API requests for monitoring and compliance."""
    api_logger = logging.getLogger('api')
    
    api_logger.info(
        "API Request",
        extra={
            'method': method,
            'endpoint': endpoint,
            'status_code': status_code,
            'response_time_ms': response_time_ms,
            'user_id': user_id,
            'request_id': request_id,
            'ip_address': ip_address,
            'event_type': 'api_request',
            'compliance_category': 'system_access'
        }
    )


def log_database_operation(operation: str, table: str, success: bool,
                          execution_time_ms: Optional[int] = None,
                          error_message: Optional[str] = None) -> None:
    """Log database operations for monitoring."""
    db_logger = logging.getLogger('database')
    
    log_data = {
        'operation': operation,
        'table': table,
        'success': success,
        'execution_time_ms': execution_time_ms,
        'event_type': 'database_operation'
    }
    
    if error_message:
        log_data['error_message'] = error_message
    
    if success:
        db_logger.info("Database Operation", extra=log_data)
    else:
        db_logger.error("Database Operation Failed", extra=log_data)


def log_external_service_call(service: str, endpoint: str, success: bool,
                             response_time_ms: Optional[int] = None,
                             status_code: Optional[int] = None,
                             error_message: Optional[str] = None) -> None:
    """Log external service calls for monitoring."""
    external_logger = logging.getLogger('external')
    
    log_data = {
        'service': service,
        'endpoint': endpoint,
        'success': success,
        'response_time_ms': response_time_ms,
        'status_code': status_code,
        'event_type': 'external_service_call'
    }
    
    if error_message:
        log_data['error_message'] = error_message
    
    if success:
        external_logger.info("External Service Call", extra=log_data)
    else:
        external_logger.error("External Service Call Failed", extra=log_data) 