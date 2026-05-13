"""
SETTLE → Billing Service Client

SETTLE is a pure settlement engine -- it generates reports ONLY.
It has ZERO knowledge of usage tables, billing records, or pricing.

Architecture (corrected):
  SETTLE calls POST /api/v1/billing/consume-report (Billing Service)
  Billing Service handles BOTH authorization AND usage record creation.
  SaaS Admin is the usage orchestrator between services.

Integration Rules:
  [OK] DO: Call POST /api/v1/billing/consume-report
  [OK] DO: Include X-API-Key header
  [OK] DO: Use idempotency_key to prevent duplicates
  [NO] DON'T: Write to billing tables
  [NO] DON'T: Know pricing configuration

Flow:
  1. SETTLE → POST /api/v1/billing/consume-report?tenant_id={id}
  2. Billing Service checks entitlements, logs usage, returns result
  3. SETTLE receives { authorized, source, price_cents, ... }
  4. If authorized, SETTLE generates the report (its only job)
  5. SETTLE makes NO second billing call -- usage already logged

See: docs/SETTLE_BILLING_INTEGRATION_GUIDE.md
"""

import logging
from typing import Dict, Optional
from uuid import uuid4

from app.core.service_auth import get_platform_service_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class PlatformServiceClient:
    """
    Client for Billing Service consume-report endpoint.

    SETTLE calls Billing Service for:
    - consume_report: authorize + log usage in ONE call

    SETTLE NEVER:
    - Writes to settle_report_usage or any billing table
    - Knows about pricing tiers, rollover banks, or billing models
    - Makes separate auth-then-log calls
    """

    def __init__(self):
        self.client = get_platform_service_client()

    # ── Consume report (single call = auth + usage logging) ─────────

    async def consume_report(
        self,
        tenant_id: str,
        case_id: str,
        report_id: Optional[str] = None,
    ) -> Dict:
        """
        Authorize AND log a report consumption in ONE call.

        Billing Service handles:
        1. Feature access check (tier, entitlements, pricing)
        2. Usage record creation (writes to settle_report_usage)
        3. Idempotency (same key → same result, no double-charge)

        SETTLE has ZERO knowledge of how/where usage is stored.

        Endpoint: POST /api/v1/billing/consume-report?tenant_id={id}
        Auth: X-API-Key header (internal service API key)

        Args:
            tenant_id: Tenant requesting the report
            case_id: Case UUID (required)
            report_id: Optional report UUID, used as idempotency key

        Returns (per SETTLE_BILLING_INTEGRATION_GUIDE.md):
            {
                "authorized": bool,
                "case_id": str,
                "source": str,       # founding|complimentary|pro_included|...
                "price_cents": int,
                "reports_used": int,
                "reports_included": int,
                "remaining": int,
                "message": str,
            }
        """
        idempotency_key = report_id or str(uuid4())

        try:
            response = await self.client.post(
                f"/api/v1/billing/consume-report?tenant_id={tenant_id}",
                json={
                    "case_id": case_id,
                    "report_id": report_id,
                    "idempotency_key": idempotency_key,
                },
                headers={
                    "X-API-Key": settings.platform_service_api_key or "",
                }
            )

            logger.debug(
                f"Consume report: tenant={tenant_id}, case={case_id}, "
                f"authorized={response.get('authorized')}, "
                f"source={response.get('source')}, "
                f"price={response.get('price_cents')}c"
            )

            return response

        except Exception as e:
            logger.error(f"Consume report failed: {str(e)}")
            # Fail open -- allow report generation, bill at standalone rate
            return {
                "authorized": True,
                "case_id": case_id,
                "source": "standalone_invoice",
                "price_cents": 3900,
                "reports_used": 0,
                "reports_included": 0,
                "remaining": -1,
                "message": "Billing Service unavailable -- fail-open mode",
                "fallback": True,
            }

    # ── Tenant info ─────────────────────────────────────────────────

    async def get_tenant_info(self, tenant_id: str) -> Optional[Dict]:
        """Get tenant information from SaaS Admin (read-only)."""
        try:
            response = await self.client.get(f"/api/v1/tenants/{tenant_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to get tenant info: {str(e)}")
            return None

    async def close(self):
        await self.client.close()
