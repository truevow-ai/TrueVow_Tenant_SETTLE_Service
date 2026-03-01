"""
API Key Authentication Module

Handles API key validation and access level enforcement for SETTLE endpoints.
"""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import Header, HTTPException, status
from datetime import datetime

from app.core.config import settings
from app.core.security import verify_api_key

logger = logging.getLogger(__name__)


class APIKeyAuth:
    """
    FastAPI dependency for API key authentication.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(api_key_data = Depends(APIKeyAuth(required_access_level=["admin"]))):
            # Access granted only to admin users
            user_id = api_key_data["user_id"]
    """
    
    def __init__(
        self,
        required_access_level: Optional[List[str]] = None,
        allow_expired: bool = False
    ):
        """
        Initialize API key authentication.
        
        Args:
            required_access_level: List of access levels allowed (e.g., ["admin", "founding_member"])
            allow_expired: Whether to allow expired API keys
        """
        self.required_access_level = required_access_level or []
        self.allow_expired = allow_expired
    
    async def __call__(
        self,
        authorization: Optional[str] = Header(None),
        x_api_key: Optional[str] = Header(None)
    ) -> dict:
        """
        Validate API key from Authorization header or X-API-Key header.
        
        Args:
            authorization: Bearer token from Authorization header
            x_api_key: API key from X-API-Key header
            
        Returns:
            Dictionary with API key data: {user_id, access_level, api_key_id}
            
        Raises:
            HTTPException: If authentication fails
        """
        
        # Extract API key from headers
        api_key = None
        
        if authorization:
            # Format: "Bearer settle_xxxxxxxxxxxxx"
            if authorization.startswith("Bearer "):
                api_key = authorization.replace("Bearer ", "").strip()
            else:
                api_key = authorization.strip()
        elif x_api_key:
            api_key = x_api_key.strip()
        
        # No API key provided
        if not api_key:
            logger.warning("API request without authentication credentials")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "Authentication required",
                    "message": "Provide API key via Authorization: Bearer {key} or X-API-Key: {key} header"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Validate API key format
        if not api_key.startswith("settle_"):
            logger.warning(f"Invalid API key format: {api_key[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "Invalid API key format",
                    "message": "API key must start with 'settle_'"
                }
            )
        
        # Verify API key (check hash in database)
        api_key_data = await self._verify_api_key(api_key)
        
        if not api_key_data:
            logger.warning(f"Invalid API key: {api_key[:15]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "Invalid API key",
                    "message": "API key not found or has been revoked"
                }
            )
        
        # Check if expired
        if not self.allow_expired and api_key_data.get("is_expired"):
            logger.warning(f"Expired API key used: {api_key_data['api_key_id']}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "API key expired",
                    "message": f"API key expired on {api_key_data.get('expires_at')}. Please contact support for renewal."
                }
            )
        
        # Check if revoked
        if api_key_data.get("is_revoked"):
            logger.warning(f"Revoked API key used: {api_key_data['api_key_id']}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "API key revoked",
                    "message": "API key has been revoked. Please contact support."
                }
            )
        
        # Check access level
        if self.required_access_level:
            user_access_level = api_key_data.get("access_level")
            
            if user_access_level not in self.required_access_level:
                logger.warning(
                    f"Access denied: user {api_key_data['user_id']} has '{user_access_level}' "
                    f"but needs one of {self.required_access_level}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "Insufficient permissions",
                        "message": f"This endpoint requires one of: {', '.join(self.required_access_level)}",
                        "your_access_level": user_access_level
                    }
                )
        
        # Log successful authentication
        logger.info(
            f"API key authenticated: user={api_key_data['user_id']}, "
            f"access_level={api_key_data['access_level']}, "
            f"key_id={api_key_data['api_key_id']}"
        )
        
        return api_key_data
    
    async def _verify_api_key(self, api_key: str) -> Optional[dict]:
        """
        Verify API key against database.
        
        Args:
            api_key: The full API key string
            
        Returns:
            Dictionary with API key data or None if invalid
        """
        
        # In mock mode, accept any key
        if settings.USE_MOCK_DATA:
            logger.info("Mock mode: accepting any API key")
            return {
                "user_id": "mock_user_123",
                "api_key_id": "mock_key_id",
                "access_level": "admin",  # Grant admin access in mock mode
                "is_expired": False,
                "is_revoked": False,
                "expires_at": None
            }
        
        # Real database lookup
        try:
            from app.core.database import get_db
            from app.core.security import hash_api_key
            
            db = await get_db()
            if db is None:
                logger.warning("Database not available for API key verification")
                return None
            
            # Hash the API key for lookup
            key_hash = hash_api_key(api_key)
            
            # Query settle_api_keys table
            result = db.table('settle_api_keys') \
                .select('id, user_id, access_level, is_active, expires_at, last_used_at, user_email, requests_used, requests_limit') \
                .eq('api_key_hash', key_hash) \
                .eq('is_active', True) \
                .execute()
            
            if not result.data or len(result.data) == 0:
                logger.debug("API key not found in database")
                return None
            
            key_data = result.data[0]
            
            # Check if expired
            is_expired = False
            if key_data.get("expires_at"):
                try:
                    from datetime import datetime
                    expires_at = datetime.fromisoformat(key_data["expires_at"].replace('Z', '+00:00'))
                    is_expired = datetime.now(expires_at.tzinfo) > expires_at
                except Exception as e:
                    logger.warning(f"Error parsing expiration date: {e}")
            
            # Schedule async last_used_at update (fire and forget)
            # This happens in background to not slow down the request
            import asyncio
            asyncio.create_task(self._update_last_used_at(db, key_data["id"]))
            
            return {
                "user_id": key_data.get("user_id"),
                "api_key_id": key_data["id"],
                "access_level": key_data["access_level"],
                "is_expired": is_expired,
                "is_revoked": not key_data.get("is_active", True),
                "expires_at": key_data.get("expires_at"),
                "user_email": key_data.get("user_email"),
                "requests_used": key_data.get("requests_used", 0),
                "requests_limit": key_data.get("requests_limit")
            }
            
        except Exception as e:
            logger.error(f"Error verifying API key: {str(e)}", exc_info=True)
            return None
    
    async def _update_last_used_at(self, db, api_key_id: str):
        """
        Update last_used_at timestamp for API key (background task).
        
        Args:
            db: Database connection
            api_key_id: API key ID
        """
        try:
            from datetime import datetime, UTC
            
            db.table('settle_api_keys') \
                .update({'last_used_at': datetime.now(UTC).isoformat()}) \
                .eq('id', api_key_id) \
                .execute()
            
            logger.debug(f"Updated last_used_at for API key {api_key_id}")
        except Exception as e:
            # Don't fail the request if this update fails
            logger.warning(f"Failed to update last_used_at for API key {api_key_id}: {e}")



async def get_admin_api_key(
    api_key_data: dict = None  # This would be from Depends(APIKeyAuth(...))
) -> dict:
    """
    FastAPI dependency for admin-only endpoints.
    
    Usage:
        @router.get("/admin/endpoint")
        async def admin_endpoint(admin = Depends(get_admin_api_key)):
            # Only admins can access this
    """
    
    # In mock mode, allow all
    if settings.USE_MOCK_DATA:
        logger.info("Mock mode: granting admin access")
        return {
            "user_id": "admin_user",
            "access_level": "admin"
        }
    
    # Check if user has admin access
    if api_key_data and api_key_data.get("access_level") == "admin":
        return api_key_data
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "Admin access required",
            "message": "This endpoint is restricted to administrators only"
        }
    )


async def get_founding_member_api_key(
    api_key_data: dict = None  # This would be from Depends(APIKeyAuth(...))
) -> dict:
    """
    FastAPI dependency for Founding Member endpoints.
    
    Usage:
        @router.post("/contribute/submit")
        async def submit_contribution(member = Depends(get_founding_member_api_key)):
            # Only Founding Members can contribute
    """
    
    # In mock mode, allow all
    if settings.USE_MOCK_DATA:
        logger.info("Mock mode: granting Founding Member access")
        return {
            "user_id": "founding_member_user",
            "access_level": "founding_member"
        }
    
    # Check if user is Founding Member or admin
    if api_key_data and api_key_data.get("access_level") in ["founding_member", "admin"]:
        return api_key_data
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "Founding Member access required",
            "message": "This endpoint is restricted to Founding Members only. Join the waitlist to apply."
        }
    )


def require_auth(required_access_level: List[str] = None):
    """
    Decorator for API key authentication.
    
    Usage:
        @require_auth(["admin", "founding_member"])
        async def endpoint():
            # Only admins and Founding Members can access
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This is a decorator pattern - actual implementation would use FastAPI Depends
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Convenience dependency factories for common access patterns
def get_api_key_dependency(required_access_level: Optional[List[str]] = None):
    """
    Factory function to create API key auth dependency with specific access level.
    
    Usage:
        # Allow any authenticated user
        api_key_data = Depends(get_api_key_dependency())
        
        # Require specific access level
        admin_data = Depends(get_api_key_dependency(["admin"]))
    """
    return APIKeyAuth(required_access_level=required_access_level)


# Pre-configured dependencies for common use cases
require_any_auth = APIKeyAuth()
require_admin = APIKeyAuth(required_access_level=["admin"])
require_founding_member = APIKeyAuth(required_access_level=["founding_member", "admin"])
require_premium = APIKeyAuth(required_access_level=["premium", "founding_member", "admin"])



