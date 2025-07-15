"""
Configuration Management for MedinovAI Chatbot
Handles all environment variables and settings with validation
"""

from functools import lru_cache
from typing import List, Optional, Dict, Any
from pydantic import BaseSettings, Field, validator, SecretStr


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # =============================================================================
    # ENVIRONMENT CONFIGURATION
    # =============================================================================
    environment: str = Field(default="development", env="NODE_ENV")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    debug: bool = Field(default=False, env="DEBUG")
    development_mode: bool = Field(default=True)
    
    # =============================================================================
    # AI MODEL CONFIGURATION
    # =============================================================================
    ai_provider: str = Field(default="openai", env="AI_PROVIDER")
    openai_api_key: SecretStr = Field(env="OPENAI_API_KEY")
    ai_model: str = Field(default="gpt-4", env="AI_MODEL")
    ai_temperature: float = Field(default=0.7, env="AI_TEMPERATURE")
    ai_max_tokens: int = Field(default=2048, env="AI_MAX_TOKENS")
    
    # Azure OpenAI Configuration
    azure_openai_endpoint: Optional[str] = Field(
        None, env="AZURE_OPENAI_ENDPOINT"
    )
    azure_openai_api_key: Optional[SecretStr] = Field(
        None, env="AZURE_OPENAI_API_KEY"
    )
    azure_openai_deployment_name: Optional[str] = Field(
        None, env="AZURE_OPENAI_DEPLOYMENT_NAME"
    )
    
    # Custom Model Configuration
    custom_model_endpoint: Optional[str] = Field(
        None, env="CUSTOM_MODEL_ENDPOINT"
    )
    custom_model_api_key: Optional[SecretStr] = Field(
        None, env="CUSTOM_MODEL_API_KEY"
    )
    
    # =============================================================================
    # LANGUAGE & LOCALIZATION
    # =============================================================================
    default_language: str = Field(default="en", env="DEFAULT_LANGUAGE")
    supported_languages: List[str] = Field(
        default=["en", "es", "zh", "hi"], env="SUPPORTED_LANGUAGES"
    )
    auto_detect_language: bool = Field(
        default=True, env="AUTO_DETECT_LANGUAGE"
    )
    translation_api_key: Optional[SecretStr] = Field(
        None, env="TRANSLATION_API_KEY"
    )
    
    # =============================================================================
    # TWILIO CONFIGURATION
    # =============================================================================
    twilio_account_sid: Optional[str] = Field(None, env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[SecretStr] = Field(None, env="TWILIO_AUTH_TOKEN")
    twilio_phone_number: Optional[str] = Field(None, env="TWILIO_PHONE_NUMBER")
    twilio_webhook_url: Optional[str] = Field(None, env="TWILIO_WEBHOOK_URL")
    
    # Voice Configuration
    twilio_voice_enabled: bool = Field(default=True, env="TWILIO_VOICE_ENABLED")
    twilio_tts_voice: str = Field(default="Polly.Joanna", env="TWILIO_TTS_VOICE")
    twilio_speech_timeout: int = Field(default=5, env="TWILIO_SPEECH_TIMEOUT")
    twilio_speech_model: str = Field(default="default", env="TWILIO_SPEECH_MODEL")
    
    # SMS Configuration
    twilio_sms_enabled: bool = Field(default=True, env="TWILIO_SMS_ENABLED")
    sms_otp_expiry: int = Field(default=300, env="SMS_OTP_EXPIRY")
    sms_max_retry: int = Field(default=3, env="SMS_MAX_RETRY")
    
    # =============================================================================
    # 3CX PHONE SYSTEM INTEGRATION
    # =============================================================================
    cx3_enabled: bool = Field(default=True, env="CX3_ENABLED")
    cx3_server_url: Optional[str] = Field(None, env="CX3_SERVER_URL")
    cx3_username: Optional[str] = Field(None, env="CX3_USERNAME")
    cx3_password: Optional[SecretStr] = Field(None, env="CX3_PASSWORD")
    cx3_sip_extension: Optional[str] = Field(None, env="CX3_SIP_EXTENSION")
    cx3_api_token: Optional[SecretStr] = Field(None, env="CX3_API_TOKEN")
    
    # =============================================================================
    # MATTERMOST INTEGRATION
    # =============================================================================
    mattermost_enabled: bool = Field(default=True, env="MATTERMOST_ENABLED")
    mattermost_url: Optional[str] = Field(None, env="MATTERMOST_URL")
    mattermost_token: Optional[SecretStr] = Field(None, env="MATTERMOST_TOKEN")
    mattermost_team_id: Optional[str] = Field(None, env="MATTERMOST_TEAM_ID")
    mattermost_bot_username: str = Field(default="medinovai-assistant", env="MATTERMOST_BOT_USERNAME")
    
    # Escalation Channels
    mattermost_escalation_channel: str = Field(default="support-escalation", env="MATTERMOST_ESCALATION_CHANNEL")
    mattermost_ai_console_channel: str = Field(default="ai-console", env="MATTERMOST_AI_CONSOLE_CHANNEL")
    mattermost_csr_ops_channel: str = Field(default="csr-ops", env="MATTERMOST_CSR_OPS_CHANNEL")
    
    # Presence Detection
    presence_check_interval: int = Field(default=60, env="PRESENCE_CHECK_INTERVAL")
    auto_reassign_timeout: int = Field(default=300, env="AUTO_REASSIGN_TIMEOUT")
    max_concurrent_chats: int = Field(default=5, env="MAX_CONCURRENT_CHATS")
    
    # =============================================================================
    # DATABASE CONFIGURATION
    # =============================================================================
    database_url: str = Field(env="DATABASE_URL")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_timeout: int = Field(default=30, env="DATABASE_TIMEOUT")
    
    # Vector Database for RAG
    vector_db_provider: str = Field(default="chroma", env="VECTOR_DB_PROVIDER")
    vector_db_url: str = Field(default="http://localhost:8000", env="VECTOR_DB_URL")
    vector_db_collection: str = Field(default="medinovai_docs", env="VECTOR_DB_COLLECTION")
    vector_embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", 
        env="VECTOR_EMBEDDING_MODEL"
    )
    
    # Redis for Caching
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_ttl: int = Field(default=3600, env="REDIS_TTL")
    
    # =============================================================================
    # AWS SERVICES CONFIGURATION
    # =============================================================================
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    aws_access_key_id: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[SecretStr] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    
    # KMS for Encryption
    aws_kms_key_id: Optional[str] = Field(None, env="AWS_KMS_KEY_ID")
    encryption_key: Optional[SecretStr] = Field(None, env="ENCRYPTION_KEY")
    
    # Secrets Manager
    aws_secrets_manager_arn: Optional[str] = Field(None, env="AWS_SECRETS_MANAGER_ARN")
    use_aws_secrets: bool = Field(default=False, env="USE_AWS_SECRETS")
    
    # S3 for Document Storage
    aws_s3_bucket: Optional[str] = Field(None, env="AWS_S3_BUCKET")
    aws_s3_region: Optional[str] = Field(None, env="AWS_S3_REGION")
    
    # CloudWatch Logging
    aws_cloudwatch_log_group: Optional[str] = Field(None, env="AWS_CLOUDWATCH_LOG_GROUP")
    aws_cloudwatch_enabled: bool = Field(default=False, env="AWS_CLOUDWATCH_ENABLED")
    
    # =============================================================================
    # AUTHENTICATION CONFIGURATION
    # =============================================================================
    auth_primary_method: str = Field(default="sms", env="AUTH_PRIMARY_METHOD")
    auth_fallback_enabled: bool = Field(default=True, env="AUTH_FALLBACK_ENABLED")
    auth_session_timeout: int = Field(default=3600, env="AUTH_SESSION_TIMEOUT")
    
    # SMS Authentication
    sms_verification_enabled: bool = Field(default=True, env="SMS_VERIFICATION_ENABLED")
    sms_otp_length: int = Field(default=6, env="SMS_OTP_LENGTH")
    
    # OAuth2 Configuration
    oauth2_enabled: bool = Field(default=True, env="OAUTH2_ENABLED")
    oauth2_provider: str = Field(default="google", env="OAUTH2_PROVIDER")
    oauth2_client_id: Optional[str] = Field(None, env="OAUTH2_CLIENT_ID")
    oauth2_client_secret: Optional[SecretStr] = Field(None, env="OAUTH2_CLIENT_SECRET")
    oauth2_redirect_uri: Optional[str] = Field(None, env="OAUTH2_REDIRECT_URI")
    
    # JWT Configuration
    jwt_secret: SecretStr = Field(env="JWT_SECRET")
    jwt_expiry: int = Field(default=3600, env="JWT_EXPIRY")
    jwt_refresh_expiry: int = Field(default=604800, env="JWT_REFRESH_EXPIRY")
    
    # =============================================================================
    # MCP API INTEGRATION
    # =============================================================================
    mcp_api_enabled: bool = Field(default=True, env="MCP_API_ENABLED")
    mcp_api_base_url: Optional[str] = Field(None, env="MCP_API_BASE_URL")
    mcp_api_key: Optional[SecretStr] = Field(None, env="MCP_API_KEY")
    mcp_api_version: str = Field(default="v1", env="MCP_API_VERSION")
    mcp_api_timeout: int = Field(default=30, env="MCP_API_TIMEOUT")
    
    # Specific MCP Endpoints
    mcp_orders_endpoint: str = Field(default="/api/v1/orders", env="MCP_ORDERS_ENDPOINT")
    mcp_appointments_endpoint: str = Field(default="/api/v1/appointments", env="MCP_APPOINTMENTS_ENDPOINT")
    mcp_patients_endpoint: str = Field(default="/api/v1/patients", env="MCP_PATIENTS_ENDPOINT")
    mcp_providers_endpoint: str = Field(default="/api/v1/providers", env="MCP_PROVIDERS_ENDPOINT")
    
    # =============================================================================
    # SECURITY & COMPLIANCE
    # =============================================================================
    # HIPAA Compliance
    phi_redaction_enabled: bool = Field(default=True, env="PHI_REDACTION_ENABLED")
    phi_detection_service: str = Field(default="aws-comprehend", env="PHI_DETECTION_SERVICE")
    audit_logging_enabled: bool = Field(default=True, env="AUDIT_LOGGING_ENABLED")
    audit_log_retention_days: int = Field(default=2555, env="AUDIT_LOG_RETENTION_DAYS")  # 7 years
    
    # GDPR Compliance
    gdpr_enabled: bool = Field(default=True, env="GDPR_ENABLED")
    consent_required: bool = Field(default=True, env="CONSENT_REQUIRED")
    data_retention_days: int = Field(default=365, env="DATA_RETENTION_DAYS")
    right_to_erasure_enabled: bool = Field(default=True, env="RIGHT_TO_ERASURE_ENABLED")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_burst_size: int = Field(default=10, env="RATE_LIMIT_BURST_SIZE")
    
    # Input Validation
    input_max_length: int = Field(default=4096, env="INPUT_MAX_LENGTH")
    input_validation_enabled: bool = Field(default=True, env="INPUT_VALIDATION_ENABLED")
    xss_protection_enabled: bool = Field(default=True, env="XSS_PROTECTION_ENABLED")
    
    # =============================================================================
    # MONITORING & ANALYTICS
    # =============================================================================
    # Prometheus Metrics
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")
    metrics_endpoint: str = Field(default="/metrics", env="METRICS_ENDPOINT")
    
    # Health Checks
    health_check_enabled: bool = Field(default=True, env="HEALTH_CHECK_ENABLED")
    health_check_interval: int = Field(default=60, env="HEALTH_CHECK_INTERVAL")
    health_check_timeout: int = Field(default=10, env="HEALTH_CHECK_TIMEOUT")
    
    # Performance Monitoring
    performance_monitoring_enabled: bool = Field(default=True, env="PERFORMANCE_MONITORING_ENABLED")
    response_time_threshold: int = Field(default=3000, env="RESPONSE_TIME_THRESHOLD")
    error_rate_threshold: int = Field(default=5, env="ERROR_RATE_THRESHOLD")
    
    # Analytics
    analytics_enabled: bool = Field(default=True, env="ANALYTICS_ENABLED")
    analytics_retention_days: int = Field(default=90, env="ANALYTICS_RETENTION_DAYS")
    daily_report_enabled: bool = Field(default=True, env="DAILY_REPORT_ENABLED")
    weekly_report_enabled: bool = Field(default=True, env="WEEKLY_REPORT_ENABLED")
    monthly_report_enabled: bool = Field(default=True, env="MONTHLY_REPORT_ENABLED")
    
    # =============================================================================
    # SERVER CONFIGURATION
    # =============================================================================
    # API Server
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=4, env="API_WORKERS")
    api_timeout: int = Field(default=60, env="API_TIMEOUT")
    
    # WebSocket Server
    websocket_enabled: bool = Field(default=True, env="WEBSOCKET_ENABLED")
    websocket_port: int = Field(default=8001, env="WEBSOCKET_PORT")
    websocket_max_connections: int = Field(default=1000, env="WEBSOCKET_MAX_CONNECTIONS")
    
    # Admin UI Server
    admin_ui_port: int = Field(default=3000, env="ADMIN_UI_PORT")
    admin_ui_host: str = Field(default="0.0.0.0", env="ADMIN_UI_HOST")
    
    # =============================================================================
    # FEATURE FLAGS
    # =============================================================================
    # Core Features
    chat_enabled: bool = Field(default=True, env="CHAT_ENABLED")
    sms_enabled: bool = Field(default=True, env="SMS_ENABLED")
    voice_enabled: bool = Field(default=True, env="VOICE_ENABLED")
    
    # Advanced Features
    rag_enabled: bool = Field(default=True, env="RAG_ENABLED")
    voice_biometrics_enabled: bool = Field(default=False, env="VOICE_BIOMETRICS_ENABLED")
    sentiment_analysis_enabled: bool = Field(default=True, env="SENTIMENT_ANALYSIS_ENABLED")
    auto_escalation_enabled: bool = Field(default=True, env="AUTO_ESCALATION_ENABLED")
    
    # Experimental Features
    ai_coaching_enabled: bool = Field(default=False, env="AI_COACHING_ENABLED")
    predictive_routing_enabled: bool = Field(default=False, env="PREDICTIVE_ROUTING_ENABLED")
    voice_cloning_enabled: bool = Field(default=False, env="VOICE_CLONING_ENABLED")
    
    # =============================================================================
    # COMPUTED PROPERTIES
    # =============================================================================
    @property
    def cors_origins(self) -> List[str]:
        """Get CORS origins based on environment."""
        if self.development_mode:
            return [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001"
            ]
        return [
            "https://chat.myonsitehealthcare.com",
            "https://admin.myonsitehealthcare.com"
        ]
    
    @property
    def allowed_hosts(self) -> List[str]:
        """Get allowed hosts based on environment."""
        if self.development_mode:
            return ["*"]
        return [
            "api.myonsitehealthcare.com",
            "chat.myonsitehealthcare.com",
            "admin.myonsitehealthcare.com"
        ]
    
    @property
    def session_secret_key(self) -> str:
        """Get session secret key."""
        return self.jwt_secret.get_secret_value()
    
    @property
    def session_max_age(self) -> int:
        """Get session max age."""
        return self.auth_session_timeout
    
    # =============================================================================
    # VALIDATORS
    # =============================================================================
    @validator("supported_languages", pre=True)
    def parse_supported_languages(cls, v):
        """Parse supported languages from string or list."""
        if isinstance(v, str):
            return [lang.strip() for lang in v.split(",")]
        return v
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v
    
    @validator("ai_provider")
    def validate_ai_provider(cls, v):
        """Validate AI provider."""
        allowed = ["openai", "azure", "anthropic", "custom"]
        if v not in allowed:
            raise ValueError(f"AI provider must be one of: {allowed}")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of: {allowed}")
        return v.upper()
    
    @validator("development_mode", always=True)
    def set_development_mode(cls, v, values):
        """Set development mode based on environment."""
        environment = values.get("environment", "development")
        return environment == "development"
    
    # =============================================================================
    # CONFIGURATION METHODS
    # =============================================================================
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration."""
        return {
            "url": self.database_url,
            "pool_size": self.database_pool_size,
            "timeout": self.database_timeout
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration."""
        return {
            "url": self.redis_url,
            "ttl": self.redis_ttl
        }
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration."""
        config = {
            "provider": self.ai_provider,
            "model": self.ai_model,
            "temperature": self.ai_temperature,
            "max_tokens": self.ai_max_tokens
        }
        
        if self.ai_provider == "openai":
            config["api_key"] = self.openai_api_key.get_secret_value()
        elif self.ai_provider == "azure":
            config.update({
                "endpoint": self.azure_openai_endpoint,
                "api_key": self.azure_openai_api_key.get_secret_value() if self.azure_openai_api_key else None,
                "deployment_name": self.azure_openai_deployment_name
            })
        elif self.ai_provider == "custom":
            config.update({
                "endpoint": self.custom_model_endpoint,
                "api_key": self.custom_model_api_key.get_secret_value() if self.custom_model_api_key else None
            })
        
        return config
    
    def get_twilio_config(self) -> Optional[Dict[str, Any]]:
        """Get Twilio configuration."""
        if not self.twilio_account_sid or not self.twilio_auth_token:
            return None
        
        return {
            "account_sid": self.twilio_account_sid,
            "auth_token": self.twilio_auth_token.get_secret_value(),
            "phone_number": self.twilio_phone_number,
            "webhook_url": self.twilio_webhook_url,
            "voice_enabled": self.twilio_voice_enabled,
            "sms_enabled": self.twilio_sms_enabled
        }
    
    def get_mattermost_config(self) -> Optional[Dict[str, Any]]:
        """Get Mattermost configuration."""
        if not self.mattermost_enabled or not self.mattermost_url or not self.mattermost_token:
            return None
        
        return {
            "url": self.mattermost_url,
            "token": self.mattermost_token.get_secret_value(),
            "team_id": self.mattermost_team_id,
            "bot_username": self.mattermost_bot_username,
            "channels": {
                "escalation": self.mattermost_escalation_channel,
                "ai_console": self.mattermost_ai_console_channel,
                "csr_ops": self.mattermost_csr_ops_channel
            }
        }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings() 