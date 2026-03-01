"""
Service-to-Service Authentication Module

Handles authentication and authorization for service-to-service communication
in the TrueVow 5-service enterprise architecture.
"""

import logging
from typing import Optional, Dict
from datetime import datetime
from uuid import uuid4
from fastapi import Header, HTTPException, status
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ServiceAuth:
    """
    FastAPI dependency for service-to-service authentication.
    
    Validates that incoming requests are from authorized TrueVow services.
    
    Usage:
        @router.post("/endpoint")
        async def endpoint(service_context = Depends(ServiceAuth())):
            # Access granted only to authorized services
            service_name = service_context["service_name"]
            request_id = service_context["request_id"]
    """
    
    # Authorized service names
    AUTHORIZED_SERVICES = [
        "truevow-platform-service",
        "truevow-internal-ops-service",
        "truevow-sales-service",
        "truevow-support-service",
        "truevow-tenant-service"
    ]
    
    def __init__(self, required_services: Optional[list] = None):
        """
        Initialize service authentication.
        
        Args:
            required_services: List of service names allowed (e.g., ["truevow-platform-service"])
                              If None, all authorized services are allowed.
        """
        self.required_services = required_services
    
    async def __call__(
        self,
        authorization: Optional[str] = Header(None),
        x_service_name: Optional[str] = Header(None, alias="X-Service-Name"),
        x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
        x_request_timestamp: Optional[str] = Header(None, alias="X-Request-Timestamp")
    ) -> Dict:
        """
        Validate service-to-service authentication.
        
        Args:
            authorization: Bearer token (service API key)
            x_service_name: Name of calling service
            x_request_id: Unique request ID (UUID)
            x_request_timestamp: ISO-8601 timestamp
            
        Returns:
            Dictionary with service context
            
        Raises:
            HTTPException: If authentication fails
        """
        
        # Skip auth in development mode if configured
        if settings.SKIP_AUTH or not settings.ENABLE_SERVICE_AUTH:
            logger.warning("Service authentication disabled - allowing all requests")
            return {
                "service_name": x_service_name or "unknown",
                "request_id": x_request_id or str(uuid4()),
                "authenticated": False,
                "bypass_mode": True
            }
        
        # Validate required headers
        if not x_service_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Missing X-Service-Name header",
                    "message": "Service-to-service requests must include X-Service-Name header"
                }
            )
        
        if not x_request_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Missing X-Request-ID header",
                    "message": "Service-to-service requests must include X-Request-ID header (UUID)"
                }
            )
        
        # Validate service name
        if x_service_name not in self.AUTHORIZED_SERVICES:
            logger.warning(f"Unauthorized service attempted access: {x_service_name}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Unauthorized service",
                    "message": f"Service '{x_service_name}' is not authorized to access SETTLE Service",
                    "authorized_services": self.AUTHORIZED_SERVICES
                }
            )
        
        # Check if service is in required list
        if self.required_services and x_service_name not in self.required_services:
            logger.warning(
                f"Service {x_service_name} attempted to access endpoint requiring {self.required_services}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Insufficient permissions",
                    "message": f"This endpoint requires one of: {', '.join(self.required_services)}",
                    "your_service": x_service_name
                }
            )
        
        # Extract and validate API key
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "Missing Authorization header",
                    "message": "Service-to-service requests must include Authorization: Bearer {api_key}"
                }
            )
        
        # Extract API key from Bearer token
        api_key = None
        if authorization.startswith("Bearer "):
            api_key = authorization.replace("Bearer ", "").strip()
        else:
            api_key = authorization.strip()
        
        # Validate API key format
        if not api_key or not api_key.startswith("settle_"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "Invalid API key format",
                    "message": "API key must start with 'settle_'"
                }
            )
        
        # Verify API key (in production, this would check database)
        # For now, we'll accept any properly formatted key in development
        if settings.USE_MOCK_DATA:
            logger.info(f"Mock mode: accepting service request from {x_service_name}")
        else:
            # TODO: Implement actual API key verification
            # This would check the settle_api_keys table for a valid admin-level key
            logger.warning("Production API key verification not yet implemented")
        
        # Log successful authentication
        logger.info(
            f"Service authenticated: {x_service_name}, "
            f"request_id={x_request_id}, "
            f"timestamp={x_request_timestamp}"
        )
        
        return {
            "service_name": x_service_name,
            "request_id": x_request_id,
            "request_timestamp": x_request_timestamp,
            "authenticated": True,
            "api_key_valid": True
        }


class ServiceClient:
    """
    Base client for making service-to-service requests.
    
    Handles authentication headers and error handling for outgoing requests.
    """
    
    def __init__(
        self,
        service_name: str,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize service client.
        
        Args:
            service_name: Name of the target service
            base_url: Base URL of the target service
            api_key: API key for authentication
            timeout: Request timeout in seconds
        """
        self.service_name = service_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get standard service-to-service headers.
        
        Returns:
            Dictionary of headers
        """
        headers = {
            "Content-Type": "application/json",
            "X-Service-Name": settings.SERVICE_NAME,
            "X-Request-ID": str(uuid4()),
            "X-Request-Timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    async def get(self, endpoint: str, **kwargs) -> Dict:
        """
        Make GET request to service.
        
        Args:
            endpoint: API endpoint (e.g., "/api/v1/resource")
            **kwargs: Additional arguments for httpx.get()
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            HTTPException: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            response = await self.client.get(url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Service request failed: {self.service_name} GET {endpoint} - "
                f"Status {e.response.status_code}"
            )
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Service {self.service_name} error: {e.response.text}"
            )
        except httpx.TimeoutException:
            logger.error(f"Service request timeout: {self.service_name} GET {endpoint}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Service {self.service_name} timeout"
            )
        except Exception as e:
            logger.error(f"Service request error: {self.service_name} GET {endpoint} - {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Service {self.service_name} error: {str(e)}"
            )
    
    async def post(self, endpoint: str, json: Dict = None, **kwargs) -> Dict:
        """
        Make POST request to service.
        
        Args:
            endpoint: API endpoint (e.g., "/api/v1/resource")
            json: Request body as dictionary
            **kwargs: Additional arguments for httpx.post()
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            HTTPException: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            response = await self.client.post(url, json=json, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Service request failed: {self.service_name} POST {endpoint} - "
                f"Status {e.response.status_code}"
            )
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Service {self.service_name} error: {e.response.text}"
            )
        except httpx.TimeoutException:
            logger.error(f"Service request timeout: {self.service_name} POST {endpoint}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Service {self.service_name} timeout"
            )
        except Exception as e:
            logger.error(f"Service request error: {self.service_name} POST {endpoint} - {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Service {self.service_name} error: {str(e)}"
            )
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# ============================================================================
# SERVICE CLIENT INSTANCES
# ============================================================================

def get_platform_service_client() -> ServiceClient:
    """Get Platform Service client"""
    return ServiceClient(
        service_name="truevow-platform-service",
        base_url=settings.PLATFORM_SERVICE_URL,
        api_key=settings.platform_service_api_key,
        timeout=settings.PLATFORM_SERVICE_TIMEOUT
    )


def get_internal_ops_service_client() -> ServiceClient:
    """Get Internal Ops Service client"""
    return ServiceClient(
        service_name="truevow-internal-ops-service",
        base_url=settings.INTERNAL_OPS_SERVICE_URL,
        api_key=settings.INTERNAL_OPS_SERVICE_API_KEY,
        timeout=settings.INTERNAL_OPS_TIMEOUT
    )


def get_sales_service_client() -> ServiceClient:
    """Get Sales Service client"""
    return ServiceClient(
        service_name="truevow-sales-service",
        base_url=settings.SALES_SERVICE_URL,
        api_key=settings.sales_service_api_key,
        timeout=settings.SALES_SERVICE_TIMEOUT
    )


def get_support_service_client() -> ServiceClient:
    """Get Support Service client"""
    return ServiceClient(
        service_name="truevow-support-service",
        base_url=settings.SUPPORT_SERVICE_URL,
        api_key=settings.support_service_api_key,
        timeout=settings.SUPPORT_SERVICE_TIMEOUT
    )


def get_tenant_service_client() -> ServiceClient:
    """Get Tenant Service client"""
    return ServiceClient(
        service_name="truevow-tenant-service",
        base_url=settings.TENANT_SERVICE_URL,
        api_key=settings.tenant_service_api_key,
        timeout=settings.TENANT_SERVICE_TIMEOUT
    )

