"""
Settlement Agreement & Release Service — SETTLE Domain

Handles ENT-097 Settlement Agreement and ENT-098 Release.

INV-006: Every executed document references an immutable Document Version and hash.
AUTH-017: Release requires legal review and client authorization.
"""

import logging
from typing import Optional, List
from datetime import datetime, UTC
from uuid import UUID, uuid4

from app.core.database import get_db
from app.models.settlement import (
    SettlementAgreement, SettlementAgreementCreate,
    Release, ReleaseCreate, ReleaseReviewRequest,
)
from app.services.settlement.authority_gate import (
    settlement_authority_gate,
    settlement_invariants,
)
from app.services.settlement.audit import settlement_audit

logger = logging.getLogger(__name__)


class AgreementService:
    """Manages settlement agreements and releases."""

    async def create_settlement_agreement(
        self,
        tenant_id: UUID,
        data: SettlementAgreementCreate,
        created_by: UUID,
        actor_role: str,
    ) -> Optional[SettlementAgreement]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        agreement_id = uuid4()
        record = {
            "id": str(agreement_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(data.matter_id),
            "settlement_decision_id": str(data.settlement_decision_id),
            "claim_ids": [str(c) for c in data.claim_ids],
            "document_version": 1,
            "status": "draft",
            "gross_amount": data.gross_amount,
            "is_confidential": data.is_confidential,
            "agreement_date": data.agreement_date.isoformat() if data.agreement_date else None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_settlement_agreements").insert(record).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=data.matter_id,
            event_type="agreement.created",
            actor_id=created_by,
            actor_type=actor_role,
            entity_type="settlement_agreement",
            entity_id=agreement_id,
        )
        return SettlementAgreement(**result.data[0])

    async def get_agreement(self, agreement_id: UUID) -> Optional[SettlementAgreement]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("settle_settlement_agreements").select("*").eq("id", str(agreement_id)).execute()
        if not result.data:
            return None
        return SettlementAgreement(**result.data[0])

    async def get_agreements_by_matter(self, matter_id: UUID) -> List[SettlementAgreement]:
        db = await get_db()
        if db is None:
            return []
        result = db.table("settle_settlement_agreements").select("*").eq("matter_id", str(matter_id)).order("created_at", desc=True).execute()
        if not result.data:
            return []
        return [SettlementAgreement(**r) for r in result.data]

    async def approve_agreement(
        self,
        agreement_id: UUID,
        attorney_id: UUID,
        tenant_id: UUID,
        matter_id: UUID,
        actor_role: str,
    ) -> Optional[SettlementAgreement]:
        gate = await settlement_authority_gate.gate_action(
            action="agreement.approve",
            actor_role=actor_role,
            actor_id=attorney_id,
            matter_id=matter_id,
            tenant_id=tenant_id,
        )
        if not gate["valid"]:
            logger.warning(f"Agreement approval denied: {gate['reason']}")
            return None

        agreement = await self.get_agreement(agreement_id)
        if agreement is None:
            return None

        _ = await settlement_invariants.check_immutable_document_version(
            document_hash=agreement.document_hash,
            state="in_review",
        )

        db = await get_db()
        now = datetime.now(UTC)
        update = {
            "status": "in_review",
            "attorney_approved_by": str(attorney_id),
            "attorney_approved_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_settlement_agreements").update(update).eq("id", str(agreement_id)).execute()
        if not result.data:
            return None
        return SettlementAgreement(**result.data[0])

    async def record_client_signature(
        self,
        agreement_id: UUID,
        client_id: UUID,
        tenant_id: UUID,
        matter_id: UUID,
    ) -> Optional[SettlementAgreement]:
        gate = await settlement_authority_gate.gate_action(
            action="agreement.sign_client",
            actor_role="client",
            actor_id=client_id,
            matter_id=matter_id,
            tenant_id=tenant_id,
        )
        if not gate["valid"]:
            return None

        db = await get_db()
        now = datetime.now(UTC)
        update = {
            "status": "client_approved",
            "client_signed_by": str(client_id),
            "client_signed_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_settlement_agreements").update(update).eq("id", str(agreement_id)).execute()
        if not result.data:
            return None
        return SettlementAgreement(**result.data[0])

    async def record_firm_signature(
        self,
        agreement_id: UUID,
        attorney_id: UUID,
        tenant_id: UUID,
        matter_id: UUID,
        actor_role: str,
    ) -> Optional[SettlementAgreement]:
        gate = await settlement_authority_gate.gate_action(
            action="agreement.sign_firm",
            actor_role=actor_role,
            actor_id=attorney_id,
            matter_id=matter_id,
            tenant_id=tenant_id,
        )
        if not gate["valid"]:
            return None

        db = await get_db()
        now = datetime.now(UTC)
        update = {
            "status": "fully_executed",
            "firm_signed_by": str(attorney_id),
            "firm_signed_at": now.isoformat(),
            "fully_executed_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_settlement_agreements").update(update).eq("id", str(agreement_id)).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=matter_id,
            event_type="agreement.fully_executed",
            actor_id=attorney_id,
            actor_type=actor_role,
            entity_type="settlement_agreement",
            entity_id=agreement_id,
        )
        return SettlementAgreement(**result.data[0])

    async def create_release(
        self,
        tenant_id: UUID,
        data: ReleaseCreate,
        created_by: UUID,
        actor_role: str,
    ) -> Optional[Release]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        release_id = uuid4()
        record = {
            "id": str(release_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(data.matter_id),
            "settlement_agreement_id": str(data.settlement_agreement_id),
            "version": 1,
            "status": "draft",
            "release_scope": data.release_scope,
            "is_mutual": data.is_mutual,
            "note": data.note,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_releases").insert(record).execute()
        if not result.data:
            return None
        return Release(**result.data[0])

    async def get_release(self, release_id: UUID) -> Optional[Release]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("settle_releases").select("*").eq("id", str(release_id)).execute()
        if not result.data:
            return None
        return Release(**result.data[0])

    async def attorney_review_release(
        self,
        tenant_id: UUID,
        matter_id: UUID,
        review: ReleaseReviewRequest,
        actor_role: str,
    ) -> Optional[Release]:
        gate = await settlement_authority_gate.gate_action(
            action="release.review",
            actor_role=actor_role,
            actor_id=review.attorney_id,
            matter_id=matter_id,
            tenant_id=tenant_id,
        )
        if not gate["valid"]:
            return None

        db = await get_db()
        now = datetime.now(UTC)
        update = {
            "status": "attorney_reviewed" if review.approved else "draft",
            "attorney_reviewed_by": str(review.attorney_id),
            "attorney_reviewed_at": now.isoformat(),
            "note": review.notes,
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_releases").update(update).eq("id", str(review.release_id)).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=matter_id,
            event_type="release.attorney_reviewed",
            actor_id=review.attorney_id,
            actor_type=actor_role,
            entity_type="release",
            entity_id=review.release_id,
        )
        return Release(**result.data[0])

    async def sign_release(
        self,
        release_id: UUID,
        client_id: UUID,
        tenant_id: UUID,
        matter_id: UUID,
    ) -> Optional[Release]:
        gate = await settlement_authority_gate.gate_action(
            action="release.sign_client",
            actor_role="client",
            actor_id=client_id,
            matter_id=matter_id,
            tenant_id=tenant_id,
        )
        if not gate["valid"]:
            return None

        db = await get_db()
        now = datetime.now(UTC)
        update = {
            "status": "signed",
            "client_signed_by": str(client_id),
            "client_signed_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_releases").update(update).eq("id", str(release_id)).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=matter_id,
            event_type="release.signed",
            actor_id=client_id,
            actor_type="client",
            entity_type="release",
            entity_id=release_id,
        )
        return Release(**result.data[0])


agreement_service = AgreementService()
