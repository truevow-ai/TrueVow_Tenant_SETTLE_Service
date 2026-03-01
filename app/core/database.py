"""
Database Connection Module

Provides database connection utilities for the SETTLE Service.
Includes retry logic and monitoring.
"""

import logging
import asyncio
from typing import Optional, Any
from contextlib import asynccontextmanager
from functools import wraps

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global client cache
_db_client = None


def with_retry(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator for retry logic on database operations.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}. "
                            f"Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"Database operation failed after {max_retries + 1} attempts: {str(e)}",
                            exc_info=True
                        )
            
            raise last_exception
        return wrapper
    return decorator


async def get_db() -> Optional[Any]:
    """
    Get database connection with retry logic.
    
    Returns:
        Supabase client or None in mock mode
    """
    global _db_client
    
    if settings.USE_MOCK_DATA:
        logger.debug("Mock mode: returning None for database connection")
        return None
    
    # Return cached client if available
    if _db_client is not None:
        return _db_client
    
    try:
        from supabase import create_client
        
        # Get settings dynamically
        supabase_url = getattr(settings, 'SUPABASE_URL', None)
        supabase_key = getattr(settings, 'SUPABASE_SERVICE_KEY', None)
        
        if not supabase_url or not supabase_key:
            logger.warning("Supabase credentials not configured - returning None")
            return None
        
        _db_client = create_client(supabase_url, supabase_key)
        logger.info("Database connection established")
        return _db_client
        
    except ImportError:
        logger.warning("Supabase package not installed - returning None")
        return None
    except Exception as e:
        logger.error(f"Failed to create database connection: {str(e)}", exc_info=True)
        return None


async def get_db_with_retry(retries: int = 3) -> Optional[Any]:
    """
    Get database connection with explicit retry.
    
    Args:
        retries: Number of retry attempts
        
    Returns:
        Supabase client or None
    """
    # In mock mode, skip retries entirely
    if settings.USE_MOCK_DATA:
        return await get_db()
    
    for attempt in range(retries):
        db = await get_db()
        if db is not None:
            return db
        
        if attempt < retries - 1:
            logger.info(f"Retrying database connection (attempt {attempt + 2}/{retries})")
            await asyncio.sleep(1 * (attempt + 1))
    
    return None


@asynccontextmanager
async def get_db_session():
    """
    Get database session context manager.
    
    Usage:
        async with get_db_session() as db:
            # Use db connection
            pass
    """
    db = await get_db()
    try:
        yield db
    finally:
        # Supabase client doesn't need explicit cleanup
        pass


async def health_check() -> dict:
    """
    Check database health.
    
    Returns:
        Dict with health status
    """
    try:
        db = await get_db_with_retry(retries=1)
        
        if db is None:
            return {
                "status": "degraded",
                "message": "Database not configured or mock mode"
            }
        
        # Simple query to verify connection
        result = db.table("settle_contributions").select("id").limit(1).execute()
        
        return {
            "status": "healthy",
            "message": "Database connection successful"
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "message": str(e)
        }


def reset_client():
    """
    Reset the cached database client.
    Used for testing or reconnection scenarios.
    """
    global _db_client
    _db_client = None
    logger.info("Database client cache reset")
