"""
Application Configuration

Loads environment variables and provides configuration settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application (supports both SETTLE_ prefix and unprefixed)
    SETTLE_APP_NAME: Optional[str] = None
    SETTLE_APP_VERSION: Optional[str] = None
    SETTLE_ENVIRONMENT: Optional[str] = None
    SETTLE_DEBUG: Optional[bool] = None
    SETTLE_LOG_LEVEL: Optional[str] = None
    
    APP_NAME: str = "TrueVow SETTLE Service"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Server (supports both SETTLE_ prefix and unprefixed)
    SETTLE_HOST: Optional[str] = None
    SETTLE_PORT: Optional[int] = None
    SETTLE_RELOAD: Optional[bool] = None
    
    HOST: str = "0.0.0.0"
    PORT: int = 3008
    RELOAD: bool = True
    
    @property
    def app_name(self) -> str:
        """Get app name (prefers SETTLE_ prefix)"""
        return self.SETTLE_APP_NAME or self.APP_NAME
    
    @property
    def environment(self) -> str:
        """Get environment (prefers SETTLE_ prefix)"""
        return self.SETTLE_ENVIRONMENT or self.ENVIRONMENT
    
    @property
    def debug(self) -> bool:
        """Get debug flag (prefers SETTLE_ prefix)"""
        if self.SETTLE_DEBUG is not None:
            return self.SETTLE_DEBUG
        return self.DEBUG
    
    @property
    def host(self) -> str:
        """Get host (prefers SETTLE_ prefix)"""
        return self.SETTLE_HOST or self.HOST
    
    @property
    def port(self) -> int:
        """Get port (prefers SETTLE_ prefix)"""
        return self.SETTLE_PORT or self.PORT
    
    # Database
    DATABASE_URL: Optional[str] = None
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Database Configuration (Provider-Agnostic Abstraction)
    # Supports multiple naming conventions for flexibility:
    # 1. SETTLE_DATABASE_* (recommended - provider-agnostic, prefixed)
    # 2. SETTLE_SUPABASE_* (specific to Supabase, prefixed)
    # 3. DATABASE_* (provider-agnostic, unprefixed)
    # 4. SUPABASE_* (specific to Supabase, unprefixed)
    
    # Provider-agnostic names (recommended for future flexibility)
    SETTLE_DATABASE_URL: Optional[str] = None
    SETTLE_DATABASE_ANON_KEY: Optional[str] = None
    SETTLE_DATABASE_SERVICE_KEY: Optional[str] = None
    
    # Provider-specific names (Supabase)
    SETTLE_SUPABASE_URL: Optional[str] = None
    SETTLE_SUPABASE_ANON_KEY: Optional[str] = None
    SETTLE_SUPABASE_SERVICE_KEY: Optional[str] = None
    
    # Unprefixed provider-agnostic (backwards compatibility)
    DATABASE_URL: Optional[str] = None
    DATABASE_ANON_KEY: Optional[str] = None
    DATABASE_SERVICE_KEY: Optional[str] = None
    
    # Unprefixed provider-specific (backwards compatibility)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None
    
    @property
    def supabase_url(self) -> Optional[str]:
        """
        Get database URL (provider-agnostic abstraction)
        Priority: SETTLE_DATABASE_URL > SETTLE_SUPABASE_URL > DATABASE_URL > SUPABASE_URL
        """
        return (
            self.SETTLE_DATABASE_URL or 
            self.SETTLE_SUPABASE_URL or 
            self.DATABASE_URL or 
            self.SUPABASE_URL
        )
    
    @property
    def supabase_key(self) -> Optional[str]:
        """
        Get database anon key (provider-agnostic abstraction)
        Priority: SETTLE_DATABASE_ANON_KEY > SETTLE_SUPABASE_ANON_KEY > DATABASE_ANON_KEY > SUPABASE_KEY
        """
        return (
            self.SETTLE_DATABASE_ANON_KEY or 
            self.SETTLE_SUPABASE_ANON_KEY or 
            self.DATABASE_ANON_KEY or 
            self.SUPABASE_KEY
        )
    
    @property
    def supabase_service_key(self) -> Optional[str]:
        """
        Get database service key (provider-agnostic abstraction)
        Priority: SETTLE_DATABASE_SERVICE_KEY > SETTLE_SUPABASE_SERVICE_KEY > DATABASE_SERVICE_KEY > SUPABASE_SERVICE_KEY
        """
        return (
            self.SETTLE_DATABASE_SERVICE_KEY or 
            self.SETTLE_SUPABASE_SERVICE_KEY or 
            self.DATABASE_SERVICE_KEY or 
            self.SUPABASE_SERVICE_KEY
        )
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""
    
    # Security (supports both prefixed and unprefixed)
    SETTLE_SECRET_KEY: Optional[str] = None
    SETTLE_API_KEY_SALT: Optional[str] = None
    SECRET_KEY: str = "change-me-in-production"
    API_KEY_SALT: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    @property
    def secret_key(self) -> str:
        """Get secret key (prefers SETTLE_ prefix)"""
        return self.SETTLE_SECRET_KEY or self.SECRET_KEY
    
    @property
    def api_key_salt(self) -> str:
        """Get API key salt (prefers SETTLE_ prefix)"""
        return self.SETTLE_API_KEY_SALT or self.API_KEY_SALT
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,https://truevow.law"
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # OpenTimestamps
    OTS_ENABLED: bool = True
    OTS_CALENDAR_URL: str = "https://alice.btc.calendar.opentimestamps.org"
    
    # Founding Member Program
    FOUNDING_MEMBER_LIMIT: int = 2100
    FOUNDING_MEMBER_UNLIMITED_ACCESS: bool = True
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Logging
    LOG_FILE: str = "logs/settle_service.log"
    LOG_MAX_BYTES: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    # Email - Resend API
    RESEND_CS_SUPPORT_API_KEY: Optional[str] = None
    RESEND_FROM_EMAIL: str = "support@intakely.xyz"
    RESEND_FROM_NAME: str = "TrueVow SETTLE"
    
    # Email - SMTP (legacy/fallback)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "noreply@truevow.law"
    
    # Slack
    SLACK_WEBHOOK_URL: Optional[str] = None
    SLACK_ALERTS_ENABLED: bool = False
    
    # Stripe
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # AWS S3
    S3_BUCKET_NAME: str = "settle-reports"
    S3_REGION: str = "us-west-2"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    
    # Performance
    MAX_QUERY_RESPONSE_TIME_MS: int = 1000
    MAX_REPORT_GENERATION_TIME_MS: int = 2000
    
    # Feature Flags
    FEATURE_PDF_GENERATION: bool = True
    FEATURE_BLOCKCHAIN_VERIFICATION: bool = True
    FEATURE_AUTO_APPROVAL: bool = False
    
    # Monitoring
    SENTRY_DSN: Optional[str] = None
    SENTRY_ENVIRONMENT: str = "development"
    
    # Admin
    ADMIN_API_KEY: str = "change-me-in-production"
    SETTLE_ADMIN_API_KEY: Optional[str] = None
    
    @property
    def admin_api_key(self) -> str:
        """Get admin API key (prefers SETTLE_ prefix)"""
        return self.SETTLE_ADMIN_API_KEY or self.ADMIN_API_KEY
    
    # ============================================================================
    # SERVICE-TO-SERVICE INTEGRATION (5-Service Architecture)
    # ============================================================================
    
    # Service Configuration
    SERVICE_NAME: str = "truevow-settle-service"
    SERVICE_PORT: int = 8002
    SERVICE_VERSION: str = "1.0.0"
    
    # Platform Service (Tenant Management, Billing, Integration Gateway)
    PLATFORM_SERVICE_URL: str = "http://localhost:3000"
    PLATFORM_SERVICE_API_KEY: Optional[str] = None
    SAAS_ADMIN_API_KEY: Optional[str] = None  # Backwards compatibility
    PLATFORM_SERVICE_TIMEOUT: int = 30
    
    @property
    def platform_service_api_key(self) -> Optional[str]:
        """Get Platform Service API key (supports multiple names)"""
        return self.PLATFORM_SERVICE_API_KEY or self.SAAS_ADMIN_API_KEY
    
    # Internal Ops Service (Task Management, Time Tracking, Notifications)
    INTERNAL_OPS_SERVICE_URL: str = "http://localhost:3001"
    INTERNAL_OPS_SERVICE_API_KEY: Optional[str] = None
    INTERNAL_OPS_TIMEOUT: int = 30
    
    # Sales Service (Pipeline Management, Lead Qualification, Demos)
    SALES_SERVICE_URL: str = "http://localhost:3002"
    SALES_SERVICE_API_KEY: Optional[str] = None
    SALES_CRM_API_KEY: Optional[str] = None  # Backwards compatibility
    SALES_SERVICE_TIMEOUT: int = 30
    
    @property
    def sales_service_api_key(self) -> Optional[str]:
        """Get Sales Service API key (supports multiple names)"""
        return self.SALES_SERVICE_API_KEY or self.SALES_CRM_API_KEY
    
    # Support Service (Tickets, Shared Inbox, Knowledge Base)
    SUPPORT_SERVICE_URL: str = "http://localhost:3003"
    SUPPORT_SERVICE_API_KEY: Optional[str] = None
    CS_SUPPORT_API_KEY: Optional[str] = None  # Backwards compatibility
    SUPPORT_SERVICE_TIMEOUT: int = 30
    
    @property
    def support_service_api_key(self) -> Optional[str]:
        """Get Support Service API key (supports multiple names)"""
        return self.SUPPORT_SERVICE_API_KEY or self.CS_SUPPORT_API_KEY
    
    # Tenant Service (INTAKE, DRAFT, BILLING, Appointments, Leads)
    TENANT_SERVICE_URL: str = "http://localhost:8000"
    TENANT_SERVICE_API_KEY: Optional[str] = None
    TENANT_APP_API_KEY: Optional[str] = None  # Backwards compatibility
    TENANT_SERVICE_TIMEOUT: int = 30
    
    @property
    def tenant_service_api_key(self) -> Optional[str]:
        """Get Tenant Service API key (supports multiple names)"""
        return self.TENANT_SERVICE_API_KEY or self.TENANT_APP_API_KEY
    
    # Service-to-Service Authentication
    ENABLE_SERVICE_AUTH: bool = True
    SERVICE_AUTH_REQUIRED_HEADERS: List[str] = ["X-Service-Name", "X-Request-ID"]
    
    # ============================================================================
    
    # Development/Testing (supports both SETTLE_ prefix and unprefixed)
    SETTLE_USE_MOCK_DATA: Optional[bool] = None
    SETTLE_SKIP_AUTH: Optional[bool] = None
    
    USE_MOCK_DATA: bool = True
    SKIP_AUTH: bool = False
    
    @property
    def use_mock_data(self) -> bool:
        """Get mock data flag (prefers SETTLE_ prefix)"""
        if self.SETTLE_USE_MOCK_DATA is not None:
            return self.SETTLE_USE_MOCK_DATA
        return self.USE_MOCK_DATA
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    model_config = SettingsConfigDict(
        # Check .env.local first (for multi-service setups), then .env
        env_file=".env.local" if os.path.exists(".env.local") else ".env",
        case_sensitive=True,
        extra="ignore",  # Ignore extra fields from other services in shared .env.local
    )


# Global settings instance
settings = Settings()

