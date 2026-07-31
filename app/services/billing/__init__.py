"""
Billing Usage Emitter — SETTLE Product Service

SETTLE emits operational facts to the Billing Usage Ledger.
SETTLE does NOT calculate prices, apply credits, or determine chargeability.
The Billing Service is the sole authority for pricing and entitlements.

Usage events emitted:
  settle.report.finalized — when a report enters FINALIZED state
"""

import logging
from typing import Optional
from datetime import datetime, UTC
from uuid import UUID, uuid4

from app.core.database import get_db
from app.models.billing import (
    BillingUsageEvent,
    BillingUsageEventCreate,
    SubscriptionGateResult,
    EntitlementGrant,
)

logger = logging.getLogger(__name__)


class BillingUsageEmitter:
    """Records operational billing facts. Does not calculate prices."""

    async def emit_usage(
        self,
        event: BillingUsageEventCreate,
    ) -> Optional[BillingUsageEvent]:
        db = await get_db()
        if db is None:
            logger.warning("Billing usage event not recorded (no DB)")
            return None

        now = datetime.now(UTC)
        event_id = uuid4()

        record = {
            "id": str(event_id),
            "tenant_id": str(event.tenant_id),
            "meter_code": event.meter_code,
            "event_type": event.event_type,
            "source_entity_type": event.source_entity_type,
            "source_entity_id": str(event.source_entity_id),
            "occurred_at": now.isoformat(),
            "payload": event.payload,
            "is_test": event.is_test,
            "is_duplicate": event.is_duplicate,
            "billing_qualification_hint": event.billing_qualification_hint,
            "created_at": now.isoformat(),
        }

        try:
            result = db.table("settle_billing_events").insert(record).execute()
            if result.data:
                logger.info(
                    "billing_event_emitted meter=%s tenant=%s event=%s",
                    event.meter_code, str(event.tenant_id), event.event_type,
                )
                return BillingUsageEvent(**result.data[0])
            return None
        except Exception as e:
            logger.error("Failed to emit billing usage event: %s", e)
            return None

    async def emit_report_finalized(
        self,
        tenant_id: UUID,
        report_id: UUID,
        query_id: Optional[UUID] = None,
        report_type: Optional[str] = None,
        is_test: bool = False,
    ) -> Optional[BillingUsageEvent]:
        return await self.emit_usage(
            BillingUsageEventCreate(
                tenant_id=tenant_id,
                meter_code="settle_finalized_report",
                event_type="settle.report.finalized",
                source_entity_type="settle_report",
                source_entity_id=report_id,
                payload={
                    "report_id": str(report_id),
                    "query_id": str(query_id) if query_id else None,
                    "report_type": report_type or "standard",
                },
                is_test=is_test,
                billing_qualification_hint="report_finalized",
            ),
        )

    async def get_usage_for_tenant(
        self, tenant_id: UUID, meter_code: Optional[str] = None,
    ) -> list:
        db = await get_db()
        if db is None:
            return []
        query = db.table("settle_billing_events").select("*").eq("tenant_id", str(tenant_id)).eq("is_test", False).eq("is_duplicate", False)
        if meter_code:
            query = query.eq("meter_code", meter_code)
        result = query.order("occurred_at", desc=True).execute()
        if not result.data:
            return []
        return result.data


class SubscriptionGate:
    """Enforces SETTLE backend capabilities based on Billing entitlements.

    The Billing Service is the authoritative source for entitlement data.
    This gate checks the cached/retrieved entitlement and enforces
    capability access at the backend level.

    Fail-closed: If entitlement cannot be resolved, new billable work is blocked
    but existing record access is preserved.
    """

    @staticmethod
    def has_capability(entitlement: EntitlementGrant, capability: str) -> bool:
        """Check if entitlement includes a specific capability."""
        return capability in entitlement.capabilities

    @staticmethod
    async def check_access(
        tenant_id: UUID,
        required_capability: str,
        entitlement: Optional[EntitlementGrant] = None,
    ) -> SubscriptionGateResult:
        if entitlement is None:
            return SubscriptionGateResult(
                allowed=False,
                reason="Entitlement not resolved. Billing Service unreachable or tenant not found.",
                tenant_id=tenant_id,
                required_capability=required_capability,
            )

        sus = entitlement.subscription_status
        blocked_states = {"SUSPENDED", "EXPIRED"}
        if sus in blocked_states:
            return SubscriptionGateResult(
                allowed=False,
                reason=f"Subscription is {sus}. New billable work blocked. Existing records preserved.",
                subscription_status=sus,
                tenant_id=tenant_id,
                required_capability=required_capability,
            )

        read_only_states = {"CANCELLED"}
        if sus in read_only_states and required_capability not in {
            "SETTLE_REPORT_VIEW", "SETTLE_ESTIMATE_QUERY",
        }:
            return SubscriptionGateResult(
                allowed=False,
                reason=f"Subscription is {sus}. Only read access preserved.",
                subscription_status=sus,
                tenant_id=tenant_id,
                required_capability=required_capability,
            )

        if not SubscriptionGate.has_capability(entitlement, required_capability):
            return SubscriptionGateResult(
                allowed=False,
                reason=f"Capability '{required_capability}' not included in plan '{entitlement.plan_code}'.",
                subscription_status=sus,
                tenant_id=tenant_id,
                required_capability=required_capability,
            )

        return SubscriptionGateResult(
            allowed=True,
            subscription_status=sus,
            tenant_id=tenant_id,
            required_capability=required_capability,
        )

    @staticmethod
    async def check_report_generation(
        tenant_id: UUID,
        entitlement: Optional[EntitlementGrant] = None,
    ) -> SubscriptionGateResult:
        return await SubscriptionGate.check_access(
            tenant_id=tenant_id,
            required_capability="SETTLE_REPORT_GENERATE",
            entitlement=entitlement,
        )

    @staticmethod
    async def check_advanced_features(
        tenant_id: UUID,
        entitlement: Optional[EntitlementGrant] = None,
    ) -> SubscriptionGateResult:
        return await SubscriptionGate.check_access(
            tenant_id=tenant_id,
            required_capability="SETTLE_ADVANCED_REPORTS",
            entitlement=entitlement,
        )


billing_emitter = BillingUsageEmitter()
subscription_gate = SubscriptionGate()
