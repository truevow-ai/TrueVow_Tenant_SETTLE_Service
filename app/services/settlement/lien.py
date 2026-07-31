"""
Lien Tracking Service — SETTLE Domain

Handles ENT-100 Lien/Reimbursement Claim and ENT-101 Lien Resolution.

Claims against proceeds must be:
  1. Asserted (recorded)
  2. Verified (documented)
  3. Resolved (negotiated, waived, adjudicated, or paid)

AUTH-017: Lien resolution may require ATTY-AUTH or CLIENT-AUTH per policy.
"""

import logging
from typing import Optional, List
from datetime import datetime, UTC
from uuid import UUID, uuid4

from app.core.database import get_db
from app.models.settlement import (
    Lien, LienCreate, LienVerify, LienResolve,
)
from app.services.settlement.authority_gate import (
    settlement_authority_gate,
    LIEN_TRANSITIONS,
)
from app.services.settlement.audit import settlement_audit

logger = logging.getLogger(__name__)


class LienService:
    """Manages liens and lien resolutions."""

    async def create_lien(
        self,
        tenant_id: UUID,
        data: LienCreate,
        created_by: UUID,
        actor_role: str,
    ) -> Optional[Lien]:
        gate = await settlement_authority_gate.gate_action(
            action="lien.create",
            actor_role=actor_role,
            actor_id=created_by,
            matter_id=data.matter_id,
            tenant_id=tenant_id,
        )
        if not gate["valid"]:
            return None

        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        lien_id = uuid4()
        record = {
            "id": str(lien_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(data.matter_id),
            "claimant": data.claimant,
            "claimant_type": data.claimant_type,
            "claim_basis": data.claim_basis,
            "asserted_amount": data.asserted_amount,
            "status": "asserted",
            "asserted_date": data.asserted_date.isoformat() if data.asserted_date else now.date().isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_liens").insert(record).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=data.matter_id,
            event_type="lien.asserted",
            actor_id=created_by,
            actor_type=actor_role,
            entity_type="lien",
            entity_id=lien_id,
            details={"claimant": data.claimant, "amount": data.asserted_amount},
        )
        return Lien(**result.data[0])

    async def get_lien(self, lien_id: UUID) -> Optional[Lien]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("settle_liens").select("*").eq("id", str(lien_id)).execute()
        if not result.data:
            return None
        return Lien(**result.data[0])

    async def get_liens_by_matter(self, matter_id: UUID) -> List[Lien]:
        db = await get_db()
        if db is None:
            return []
        result = db.table("settle_liens").select("*").eq("matter_id", str(matter_id)).order("created_at", desc=True).execute()
        if not result.data:
            return []
        return [Lien(**r) for r in result.data]

    async def request_lien_documents(
        self,
        lien_id: UUID,
        requested_by: UUID,
        tenant_id: UUID,
        matter_id: UUID,
    ) -> Optional[Lien]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        update = {
            "status": "documents_requested",
            "documents_requested_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_liens").update(update).eq("id", str(lien_id)).execute()
        if not result.data:
            return None
        return Lien(**result.data[0])

    async def verify_lien(
        self,
        tenant_id: UUID,
        matter_id: UUID,
        data: LienVerify,
        actor_role: str,
    ) -> Optional[Lien]:
        lien = await self.get_lien(data.lien_id)
        if lien is None:
            return None

        gate = await settlement_authority_gate.gate_action(
            action="lien.verify",
            actor_role=actor_role,
            actor_id=data.verified_by,
            matter_id=matter_id,
            tenant_id=tenant_id,
            current_state=lien.status,
            target_state="verified",
            transition_map=LIEN_TRANSITIONS,
        )
        if not gate["valid"]:
            logger.warning(f"Lien verification denied: {gate['reason']}")
            return None

        db = await get_db()
        now = datetime.now(UTC)
        update = {
            "status": "verified",
            "verified_amount": data.verified_amount,
            "verified_by": str(data.verified_by),
            "verified_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_liens").update(update).eq("id", str(data.lien_id)).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=matter_id,
            event_type="lien.verified",
            actor_id=data.verified_by,
            actor_type=actor_role,
            entity_type="lien",
            entity_id=data.lien_id,
            details={"verified_amount": data.verified_amount, "asserted_amount": lien.asserted_amount},
        )
        return Lien(**result.data[0])

    async def resolve_lien(
        self,
        tenant_id: UUID,
        matter_id: UUID,
        data: LienResolve,
        actor_role: str,
    ) -> Optional[Lien]:
        lien = await self.get_lien(data.lien_id)
        if lien is None:
            return None

        gate = await settlement_authority_gate.gate_action(
            action="lien.resolve",
            actor_role=actor_role,
            actor_id=data.resolved_by,
            matter_id=matter_id,
            tenant_id=tenant_id,
            current_state=lien.status,
            target_state="resolved",
            transition_map=LIEN_TRANSITIONS,
        )
        if not gate["valid"]:
            logger.warning(f"Lien resolution denied: {gate['reason']}")
            return None

        db = await get_db()
        now = datetime.now(UTC)
        update = {
            "status": "resolved",
            "negotiated_amount": data.final_amount,
            "resolution_date": now.date().isoformat(),
            "note": data.note,
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_liens").update(update).eq("id", str(data.lien_id)).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=matter_id,
            event_type="lien.resolved",
            actor_id=data.resolved_by,
            actor_type=actor_role,
            entity_type="lien",
            entity_id=data.lien_id,
            details={"final_amount": data.final_amount, "resolution_type": data.resolution_type},
        )
        return Lien(**result.data[0])

    async def get_lien_resolutions(self, matter_id: UUID) -> list:
        """Get all lien resolution records for a matter."""
        db = await get_db()
        if db is None:
            return []
        liens = await self.get_liens_by_matter(matter_id)
        resolved = [li for li in liens if li.status in ("resolved", "paid")]
        return [li.model_dump() for li in resolved]

    async def get_outstanding_liens(self, matter_id: UUID) -> List[Lien]:
        """Get liens that are not yet resolved or paid."""
        db = await get_db()
        if db is None:
            return []
        result = db.table("settle_liens").select("*").eq("matter_id", str(matter_id)).not_.in_("status", ["resolved", "paid"]).execute()
        if not result.data:
            return []
        return [Lien(**r) for r in result.data]


lien_service = LienService()
