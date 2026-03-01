"""
Application Monitoring & Error Tracking

Integrates Sentry for error tracking, performance monitoring, and alerting.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def initialize_sentry(
    environment: str = "development",
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.1
) -> bool:
    """
    Initialize Sentry error tracking and performance monitoring.
    
    Args:
        environment: Environment name (development, staging, production)
        traces_sample_rate: Percentage of transactions to profile (0.0-1.0)
        profiles_sample_rate: Percentage of profiles to collect (0.0-1.0)
        
    Returns:
        True if initialized successfully
    """
    sentry_dsn = os.getenv("SETTLE_SENTRY_DSN")
    
    if not sentry_dsn:
        logger.warning("Sentry DSN not configured. Error tracking disabled.")
        return False
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            
            # Performance Monitoring
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            
            # Integrations
            integrations=[
                FastApiIntegration(
                    transaction_style="endpoint"  # Group by endpoint
                ),
                StarletteIntegration(),
                LoggingIntegration(
                    level=logging.INFO,  # Capture info and above
                    event_level=logging.ERROR  # Send events for errors
                ),
            ],
            
            # Additional options
            send_default_pii=False,  # Don't send PII (IMPORTANT for bar compliance)
            attach_stacktrace=True,
            max_breadcrumbs=50,
            
            # Before send hook to filter sensitive data
            before_send=_before_send_hook,
            
            # Release tracking (set via environment variable)
            release=os.getenv("SETTLE_VERSION", "unknown")
        )
        
        logger.info(f"Sentry initialized: environment={environment}, dsn={sentry_dsn[:20]}...")
        return True
        
    except ImportError:
        logger.error("sentry-sdk not installed. Error tracking disabled.")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {str(e)}", exc_info=True)
        return False


def _before_send_hook(event, hint):
    """
    Filter sensitive data before sending to Sentry.
    
    This is CRITICAL for bar compliance - we must never send PHI or attorney data.
    
    Args:
        event: Sentry event dictionary
        hint: Additional context
        
    Returns:
        Modified event or None to drop
    """
    # Remove sensitive request data
    if 'request' in event:
        request = event['request']
        
        # Remove headers that might contain API keys
        if 'headers' in request:
            sensitive_headers = ['authorization', 'x-api-key', 'cookie']
            for header in sensitive_headers:
                if header in request['headers']:
                    request['headers'][header] = '[REDACTED]'
        
        # Remove query parameters that might contain sensitive data
        if 'query_string' in request:
            request['query_string'] = '[REDACTED]'
        
        # Remove request body (could contain PHI)
        if 'data' in request:
            request['data'] = '[REDACTED FOR COMPLIANCE]'
    
    # Remove user data (email, etc.)
    if 'user' in event:
        user = event['user']
        if 'email' in user:
            user['email'] = '[REDACTED]'
        if 'username' in user:
            user['username'] = '[REDACTED]'
    
    # Remove extra context that might contain sensitive data
    if 'extra' in event:
        sensitive_keys = ['api_key', 'password', 'token', 'ssn', 'email', 'phone']
        for key in list(event['extra'].keys()):
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                event['extra'][key] = '[REDACTED]'
    
    return event


def capture_exception(
    error: Exception,
    context: Optional[dict] = None,
    level: str = "error"
) -> Optional[str]:
    """
    Capture an exception and send to Sentry.
    
    Args:
        error: Exception to capture
        context: Additional context dictionary
        level: Error level (error, warning, info)
        
    Returns:
        Sentry event ID
    """
    try:
        import sentry_sdk
        
        # Add context
        if context:
            with sentry_sdk.push_scope() as scope:
                for key, value in context.items():
                    scope.set_context(key, value)
                scope.level = level
                event_id = sentry_sdk.capture_exception(error)
        else:
            event_id = sentry_sdk.capture_exception(error)
        
        logger.info(f"Exception captured in Sentry: {event_id}")
        return event_id
        
    except Exception as e:
        logger.error(f"Failed to capture exception in Sentry: {str(e)}")
        return None


def capture_message(
    message: str,
    level: str = "info",
    context: Optional[dict] = None
) -> Optional[str]:
    """
    Capture a message and send to Sentry.
    
    Args:
        message: Message to capture
        level: Message level (error, warning, info)
        context: Additional context
        
    Returns:
        Sentry event ID
    """
    try:
        import sentry_sdk
        
        if context:
            with sentry_sdk.push_scope() as scope:
                for key, value in context.items():
                    scope.set_context(key, value)
                scope.level = level
                event_id = sentry_sdk.capture_message(message, level=level)
        else:
            event_id = sentry_sdk.capture_message(message, level=level)
        
        return event_id
        
    except Exception as e:
        logger.error(f"Failed to capture message in Sentry: {str(e)}")
        return None


def set_user_context(
    user_id: str,
    access_level: Optional[str] = None
):
    """
    Set user context for Sentry (WITHOUT PII).
    
    Args:
        user_id: Anonymized user ID
        access_level: User access level
    """
    try:
        import sentry_sdk
        
        # Only set non-PII user data
        sentry_sdk.set_user({
            "id": user_id,  # Hashed/anonymized ID only
            "access_level": access_level
        })
        
    except Exception as e:
        logger.error(f"Failed to set user context: {str(e)}")


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: str = "info",
    data: Optional[dict] = None
):
    """
    Add a breadcrumb for debugging context.
    
    Args:
        message: Breadcrumb message
        category: Category (e.g., "api", "database", "auth")
        level: Level (info, warning, error)
        data: Additional data
    """
    try:
        import sentry_sdk
        
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {}
        )
        
    except Exception as e:
        logger.error(f"Failed to add breadcrumb: {str(e)}")


def configure_logging_integration():
    """
    Configure logging to automatically send errors to Sentry.
    """
    import logging
    
    class SentryHandler(logging.Handler):
        """Custom handler to send logs to Sentry."""
        
        def emit(self, record):
            try:
                if record.levelno >= logging.ERROR:
                    capture_message(
                        message=record.getMessage(),
                        level="error",
                        context={
                            "logger": record.name,
                            "pathname": record.pathname,
                            "lineno": record.lineno
                        }
                    )
            except Exception:
                pass
    
    # Add Sentry handler to root logger
    sentry_handler = SentryHandler()
    sentry_handler.setLevel(logging.ERROR)
    logging.getLogger().addHandler(sentry_handler)


def get_monitoring_stats() -> dict:
    """
    Get monitoring service status.
    
    Returns:
        Dictionary with monitoring stats
    """
    sentry_dsn = os.getenv("SETTLE_SENTRY_DSN")
    
    return {
        "sentry_enabled": bool(sentry_dsn),
        "environment": os.getenv("SETTLE_ENVIRONMENT", "development"),
        "version": os.getenv("SETTLE_VERSION", "unknown")
    }


