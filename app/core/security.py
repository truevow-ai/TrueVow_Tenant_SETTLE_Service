"""
Security and Authentication

API key authentication and authorization for SETTLE service.
"""

import hashlib
import secrets
from typing import Optional, Tuple
from uuid import UUID
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# API Key header
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


def generate_api_key() -> Tuple[str, str]:
    """
    Generate a new API key.
    
    Returns:
        Tuple of (api_key, api_key_hash)
    """
    # Generate random API key (32 bytes = 64 hex characters)
    api_key = secrets.token_urlsafe(32)
    
    # Hash for storage
    api_key_hash = hash_api_key(api_key)
    
    return api_key, api_key_hash


def hash_api_key(api_key: str) -> str:
    """
    Hash API key for storage.
    
    Args:
        api_key: Plain text API key
        
    Returns:
        Hashed API key
    """
    salted = f"{settings.api_key_salt}{api_key}".encode()
    return hashlib.sha256(salted).hexdigest()


def verify_api_key(api_key: str, api_key_hash: str) -> bool:
    """
    Verify API key against stored hash.
    
    Args:
        api_key: Plain text API key
        api_key_hash: Stored hash
        
    Returns:
        True if valid
    """
    computed_hash = hash_api_key(api_key)
    return secrets.compare_digest(computed_hash, api_key_hash)


async def get_api_key(
    api_key_header_value: Optional[str] = Security(api_key_header)
) -> str:
    """
    Extract and validate API key from request header.
    
    Header format: "Authorization: Bearer <api_key>"
    
    Args:
        api_key_header_value: Value from Authorization header
        
    Returns:
        Valid API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    # Skip auth in development if configured
    if settings.SKIP_AUTH:
        logger.warning("SKIPPING AUTH - Development mode only!")
        return "dev-api-key"
    
    if not api_key_header_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Include 'Authorization: Bearer <api_key>' header."
        )
    
    # Extract Bearer token
    try:
        scheme, api_key = api_key_header_value.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use: 'Bearer <api_key>'"
        )
    
    # TODO: Validate API key against database
    # For now, accept any non-empty key in development
    if settings.ENVIRONMENT == "development":
        logger.info(f"API key validated (development mode): {api_key[:8]}...")
        return api_key
    
    # Production: Validate against database
    # is_valid = await validate_api_key_from_db(api_key)
    # if not is_valid:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Invalid API key"
    #     )
    
    return api_key


async def get_api_key_info(api_key: str) -> dict:
    """
    Get API key information from database.
    
    Args:
        api_key: API key
        
    Returns:
        Dict with API key info (id, access_level, user_email, etc.)
    """
    # TODO: Implement database query
    # For now, return mock data
    return {
        "api_key_id": "00000000-0000-0000-0000-000000000000",
        "access_level": "standard",
        "user_email": "test@example.com",
        "is_founding_member": False,
        "requests_used": 0,
        "requests_limit": 1000
    }


async def check_founding_member(api_key: str) -> bool:
    """
    Check if API key belongs to a Founding Member.
    
    Args:
        api_key: API key
        
    Returns:
        True if Founding Member
    """
    api_key_info = await get_api_key_info(api_key)
    return api_key_info.get("is_founding_member", False)


async def check_rate_limit(api_key: str) -> bool:
    """
    Check if API key has exceeded rate limit.
    
    Args:
        api_key: API key
        
    Returns:
        True if within rate limit
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    if not settings.RATE_LIMIT_ENABLED:
        return True
    
    # TODO: Implement Redis-based rate limiting
    # For now, return True
    
    api_key_info = await get_api_key_info(api_key)
    
    # Founding Members have unlimited access
    if api_key_info.get("is_founding_member"):
        return True
    
    # Check requests limit
    requests_used = api_key_info.get("requests_used", 0)
    requests_limit = api_key_info.get("requests_limit")
    
    if requests_limit and requests_used >= requests_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {requests_limit} requests."
        )
    
    return True


async def increment_request_count(api_key: str):
    """
    Increment request count for API key.
    
    Args:
        api_key: API key
    """
    # TODO: Implement database update
    pass

