"""
Matter Closure Service — SETTLE Domain

Handles ENT-106 Matter Closure.

INV-019: Closed matters remain subject to retention, access, accounting,
and continuing-duty rules. Matter closure is not deletion.
"""

import logging
from typing import Optional
from datetime import datetime, UTC
from uuid import UUID, uuid4

from app.core.database import get_db
from app.models.settlement import (
    MatterClosure, MatterClosureRequest, MatterReopenRequest,
)
from app.services.settlement.authority_gate import (
    settlement_authority_gate,
)
from app.services.settlement.audit import settlement_audit
from app.services.settlement.lien import lien_service
from app.services.settlement.financial import payment_service, allocation_service

logger = logging.getLogger(__name__)


class ClosureService:
    """Manages matter closure and reopening."""

    async def get_closure_status(self, matter_id: UUID) -> Optional[MatterClosure]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("settle_matter_closures").select("*").eq("matter_id", str(matter_id)).order("created_at", desc=True).limit(1).execute()
        if not result.data:
            return None
        return MatterClosure(**result.data[0])

    async def _gather_unresolved_items(self, matter_id: UUID) -> list:
        """Check for unresolved items that should block or warn on closure."""
        unresolved = []

        outstanding_liens = await lien_service.get_outstanding_liens(matter_id)
        if outstanding_liens:
            unresolved.append({
                "type": "outstanding_liens",
                "count": len(outstanding_liens),
                "details": [{"claimant": li.claimant, "status": li.status, "amount": li.asserted_amount} for li in outstanding_liens],
            })

        payments = await payment_service.get_payments_by_matter(matter_id)
        pending_payments = [p for p in payments if p.status == "pending"]
        if pending_payments:
            unresolved.append({
                "type": "pending_payments",
                "count": len(pending_payments),
                "details": [{"payer": p.payer, "amount": p.amount} for p in pending_payments],
            })

        allocations = await allocation_service.get_allocations_by_matter(matter_id)
        unapproved = [a for a in allocations if a.status == "draft"]
        if unapproved:
            unresolved.append({
                "type": "unapproved_allocations",
                "count": len(unapproved),
            })

        trust_balance = await payment_service.get_trust_balance(matter_id)
        if trust_balance > 0:
            unresolved.append({
                "type": "trust_balance_remaining",
                "balance": trust_balance,
                "warning": "Trust account has remaining balance. Verify before closure.",
            })

        return unresolved

    async def close_matter(
        self,
        tenant_id: UUID,
        data: MatterClosureRequest,
        actor_role: str,
    ) -> Optional[MatterClosure]:
        gate = await settlement_authority_gate.gate_action(
            action="matter.close",
            actor_role=actor_role,
            actor_id=data.authorized_by,
            matter_id=data.matter_id,
            tenant_id=tenant_id,
        )
        if not gate["valid"]:
            logger.warning(f"Matter closure denied: {gate['reason']}")
            return None

        unresolved = await self._gather_unresolved_items(data.matter_id)

        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        closure_id = uuid4()
        record = {
            "id": str(closure_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(data.matter_id),
            "state": "closed",
            "closure_type": data.closure_type,
            "closed_at": now.isoformat(),
            "closed_by": str(data.authorized_by),
            "closure_authorized_by": str(data.authorized_by),
            "unresolved_items": unresolved,
            "note": data.note,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_matter_closures").insert(record).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=data.matter_id,
            event_type="matter.closed",
            actor_id=data.authorized_by,
            actor_type=actor_role,
            entity_type="matter_closure",
            entity_id=closure_id,
            details={
                "closure_type": data.closure_type,
                "unresolved_count": len(unresolved),
            },
        )
        return MatterClosure(**result.data[0])

    async def reopen_matter(
        self,
        tenant_id: UUID,
        data: MatterReopenRequest,
        actor_role: str,
    ) -> Optional[MatterClosure]:
        gate = await settlement_authority_gate.gate_action(
            action="matter.reopen",
            actor_role=actor_role,
            actor_id=data.authorized_by,
            matter_id=data.matter_id,
            tenant_id=tenant_id,
        )
        if not gate["valid"]:
            return None

        closure = await self.get_closure_status(data.matter_id)
        if closure is None or closure.state != "closed":
            logger.warning("Matter is not in closed state")
            return None

        db = await get_db()
        now = datetime.now(UTC)
        update = {
            "state": "reopened",
            "reopened_at": now.isoformat(),
            "reopened_by": str(data.authorized_by),
            "reopen_reason": data.reason,
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_matter_closures").update(update).eq("id", str(closure.id)).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=data.matter_id,
            event_type="matter.reopened",
            actor_id=data.authorized_by,
            actor_type=actor_role,
            entity_type="matter_closure",
            entity_id=closure.id,
            details={"reason": data.reason},
        )
        return MatterClosure(**result.data[0])


closure_service = ClosureService()
