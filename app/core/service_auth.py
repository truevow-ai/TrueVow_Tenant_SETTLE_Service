"""
Service-to-Service Authentication Module

Handles authentication and authorization for service-to-service communication
in the TrueVow 5-service enterprise architecture.

HMAC webhook signing (WebhookSignature v1.0 — frozen contract):
  Signing string:  timestamp:method:path:body_hash
  Headers:         X-TrueVow-Key-Id, X-TrueVow-Timestamp, X-TrueVow-Signature
  Algorithm:       HMAC-SHA256, constant-time comparison
  Replay window:   5 minutes
  Key rotation:    TRUEVOW_WEBHOOK_SECONDARY_KEYS env var

This Python implementation MUST produce byte-identical signatures to the
TypeScript reference at lib/security/webhook-auth.ts in SaaS Admin.
"""

import hashlib
import hmac
import json
import logging
import os
import time as time_module
from typing import Optional, Dict
from datetime import datetime
from uuid import uuid4
from fastapi import Header, HTTPException, Request, status
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS = 300
WEBHOOK_HASH_ALGORITHM = "sha256"


def _load_webhook_secrets() -> Dict[str, str]:
    """Load webhook secrets from env vars — matches SaaS Admin TypeScript.

    TRUEVOW_WEBHOOK_KEY_ID=tv-primary
    TRUEVOW_WEBHOOK_SECRET=<shared-secret>
    TRUEVOW_WEBHOOK_SECONDARY_KEYS=[{"key_id":"tv-secondary","secret":"..."}]
    """
    secrets: Dict[str, str] = {}
    key_id = os.getenv("TRUEVOW_WEBHOOK_KEY_ID", "settle-service")
    secret = os.getenv("TRUEVOW_WEBHOOK_SECRET", "settle-dev-secret")
    secrets[key_id] = secret

    secondary = os.getenv("TRUEVOW_WEBHOOK_SECONDARY_KEYS")
    if secondary:
        try:
            for entry in json.loads(secondary):
                secrets[entry["key_id"]] = entry["secret"]
        except (json.JSONDecodeError, KeyError):
            logger.warning("Failed to parse TRUEVOW_WEBHOOK_SECONDARY_KEYS")

    return secrets


class WebhookSigner:
    """Signs outgoing webhook requests with HMAC-SHA256.

    Signing string format (matches TypeScript lib/security/webhook-auth.ts):
      timestamp:method:path:body_hash

    The path is the URL path only — no host, no query string.
    This prevents malicious replay to a different endpoint.
    """

    def __init__(self, key_id: str, secret: str):
        self.key_id = key_id
        self._secret = secret.encode()

    def sign(
        self,
        method: str,
        path: str,
        body_bytes: bytes,
        timestamp: Optional[int] = None,
    ) -> Dict[str, str]:
        ts = str(timestamp or int(time_module.time()))
        body_hash = hashlib.sha256(body_bytes).hexdigest()
        signing_string = f"{ts}:{method.upper()}:{path}:{body_hash}"
        signature = hmac.new(self._secret, signing_string.encode(), hashlib.sha256).hexdigest()

        return {
            "X-TrueVow-Key-Id": self.key_id,
            "X-TrueVow-Timestamp": ts,
            "X-TrueVow-Signature": signature,
        }

    def sign_request(self, method: str, path: str, body: Optional[bytes] = None) -> Dict[str, str]:
        """Sign a request. path is URL path only (no host, no query string)."""
        return self.sign(method=method, path=path, body_bytes=body or b"")


class WebhookVerifier:
    """Verifies incoming webhook signatures.

    Usage as FastAPI dependency:
        verifier = get_webhook_verifier()

        @router.post("/webhook/matter-activated")
        async def handle_webhook(
            request: Request,
            verified = Depends(verifier),
        ):
            ...
    """

    def __init__(
        self,
        secrets: Optional[Dict[str, str]] = None,
        tolerance_seconds: int = WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS,
    ):
        self._secrets = {kid: s.encode() for kid, s in (secrets or _load_webhook_secrets()).items()}
        self._tolerance = tolerance_seconds

    async def __call__(
        self,
        request: Request,
        x_truevow_key_id: Optional[str] = Header(None, alias="X-TrueVow-Key-Id"),
        x_truevow_timestamp: Optional[str] = Header(None, alias="X-TrueVow-Timestamp"),
        x_truevow_signature: Optional[str] = Header(None, alias="X-TrueVow-Signature"),
    ) -> Dict:
        if settings.SKIP_AUTH or not settings.ENABLE_SERVICE_AUTH:
            return {"authenticated": False, "bypass_mode": True}

        if not x_truevow_key_id or not x_truevow_timestamp or not x_truevow_signature:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signing headers: X-TrueVow-Key-Id, X-TrueVow-Timestamp, X-TrueVow-Signature",
            )

        secret = self._secrets.get(x_truevow_key_id)
        if secret is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Unknown key ID: {x_truevow_key_id}",
            )

        try:
            ts = int(x_truevow_timestamp)
        except (ValueError, TypeError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timestamp format")

        now = int(time_module.time())
        if abs(now - ts) > self._tolerance:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Webhook timestamp outside tolerance window",
            )

        raw_body = await request.body()
        path = request.url.path
        body_hash = hashlib.sha256(raw_body).hexdigest()
        signing_string = f"{x_truevow_timestamp}:{request.method.upper()}:{path}:{body_hash}"

        expected = hmac.new(secret, signing_string.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected, x_truevow_signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

        return {
            "authenticated": True,
            "key_id": x_truevow_key_id,
            "timestamp": ts,
        }


def get_settle_webhook_signer() -> WebhookSigner:
    """Returns a WebhookSigner configured from env vars (TRUEVOW_WEBHOOK_KEY_ID)."""
    secrets = _load_webhook_secrets()
    key_id = os.getenv("TRUEVOW_WEBHOOK_KEY_ID", "settle-service")
    return WebhookSigner(key_id=key_id, secret=secrets[key_id])


def get_webhook_verifier() -> WebhookVerifier:
    """Returns a WebhookVerifier with secrets from env vars."""
    return WebhookVerifier()


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
        if settings.use_mock_data:
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

