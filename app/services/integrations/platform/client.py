"""
Platform Service Client

Client for communicating with the Platform Service for:
- Reporting usage events (for billing)
- Syncing API key status
- Tenant provisioning callbacks
"""

import logging
from typing import Dict, Optional
from datetime import datetime

from app.core.service_auth import get_platform_service_client

logger = logging.getLogger(__name__)


class PlatformServiceClient:
    """
    Client for Platform Service integration.
    
    The Platform Service handles:
    - Tenant management
    - Billing & subscriptions
    - Integration gateway
    - Monitoring & observability
    """
    
    def __init__(self):
        """Initialize Platform Service client"""
        self.client = get_platform_service_client()
    
    async def report_usage(
        self,
        tenant_id: str,
        usage_type: str,
        quantity: int = 1,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Report usage event to Platform Service for billing.
        
        Args:
            tenant_id: Tenant ID
            usage_type: Type of usage (e.g., "settle_query", "settle_contribution", "settle_report")
            quantity: Quantity of usage (default: 1)
            metadata: Additional metadata
            
        Returns:
            Response from Platform Service
            
        Example:
            await platform_client.report_usage(
                tenant_id="tenant_123",
                usage_type="settle_query",
                quantity=1,
                metadata={"query_id": "query_456", "confidence": "high"}
            )
        """
        try:
            response = await self.client.post(
                "/api/v1/usage/report",
                json={
                    "tenant_id": tenant_id,
                    "service": "settle",
                    "usage_type": usage_type,
                    "quantity": quantity,
                    "metadata": metadata or {},
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            )
            
            logger.info(
                f"Usage reported to Platform Service: tenant={tenant_id}, "
                f"type={usage_type}, quantity={quantity}"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to report usage to Platform Service: {str(e)}")
            # Don't raise - usage reporting is non-critical
            return {"success": False, "error": str(e)}
    
    async def sync_api_key_status(
        self,
        api_key_id: str,
        status: str,
        last_used_at: Optional[datetime] = None,
        requests_used: Optional[int] = None
    ) -> Dict:
        """
        Sync API key status with Platform Service.
        
        Args:
            api_key_id: API key ID
            status: Status (e.g., "active", "revoked", "expired")
            last_used_at: Last usage timestamp
            requests_used: Total requests used
            
        Returns:
            Response from Platform Service
        """
        try:
            response = await self.client.post(
                f"/api/v1/api-keys/{api_key_id}/sync",
                json={
                    "status": status,
                    "last_used_at": last_used_at.isoformat() + "Z" if last_used_at else None,
                    "requests_used": requests_used,
                    "service": "settle"
                }
            )
            
            logger.info(f"API key status synced: {api_key_id} -> {status}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to sync API key status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_tenant_info(self, tenant_id: str) -> Optional[Dict]:
        """
        Get tenant information from Platform Service.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Tenant information or None if not found
        """
        try:
            response = await self.client.get(f"/api/v1/tenants/{tenant_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to get tenant info: {str(e)}")
            return None
    
    async def close(self):
        """Close the client connection"""
        await self.client.close()

