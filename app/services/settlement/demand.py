"""
Demand Package & Transmission Service — SETTLE Domain

Handles ENT-081 Demand Package, ENT-082 Demand Draft, ENT-092 Demand Transmission.
Following ontology: Authorized demand/claim -> controlled resolution.
AUTH-014: Demand transmission requires ATTY-AUTH.
"""

import logging
from typing import Optional, List
from datetime import datetime, UTC
from uuid import UUID, uuid4

from app.core.database import get_db
from app.models.settlement import (
    DemandPackage, DemandPackageCreate, DemandAuthorizationRequest, DemandTransmitRequest,
    DemandDraft, DemandDraftCreate, DemandDraftReview,
    DemandTransmission,
)
from app.services.settlement.authority_gate import (
    settlement_authority_gate,
    DEMAND_PACKAGE_TRANSITIONS,
)
from app.services.settlement.audit import settlement_audit

logger = logging.getLogger(__name__)


class DemandService:
    """Manages demand packages, drafts, and transmissions."""

    async def create_demand_package(
        self,
        tenant_id: UUID,
        data: DemandPackageCreate,
        created_by: UUID,
    ) -> Optional[DemandPackage]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        package_id = uuid4()
        record = {
            "id": str(package_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(data.matter_id),
            "claim_ids": [str(c) for c in data.claim_ids],
            "version": 1,
            "state": "assembling",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_demand_packages").insert(record).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=data.matter_id,
            event_type="demand.package_created",
            actor_id=created_by,
            actor_type="attorney",
            entity_type="demand_package",
            entity_id=package_id,
        )
        return DemandPackage(**result.data[0])

    async def get_demand_package(self, package_id: UUID) -> Optional[DemandPackage]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("settle_demand_packages").select("*").eq("id", str(package_id)).execute()
        if not result.data:
            return None
        return DemandPackage(**result.data[0])

    async def get_demand_packages_by_matter(self, matter_id: UUID) -> List[DemandPackage]:
        db = await get_db()
        if db is None:
            return []
        result = db.table("settle_demand_packages").select("*").eq("matter_id", str(matter_id)).order("version", desc=True).execute()
        if not result.data:
            return []
        return [DemandPackage(**r) for r in result.data]

    async def update_demand_package_state(
        self,
        package_id: UUID,
        new_state: str,
        actor_id: UUID,
        actor_role: str,
        tenant_id: UUID,
        matter_id: UUID,
    ) -> Optional[DemandPackage]:
        package = await self.get_demand_package(package_id)
        if package is None:
            return None

        gate = await settlement_authority_gate.gate_action(
            action=f"demand.{'authorize' if new_state == 'authorized' else 'draft.create'}",
            actor_role=actor_role,
            actor_id=actor_id,
            matter_id=matter_id,
            tenant_id=tenant_id,
            current_state=package.state,
            target_state=new_state,
            transition_map=DEMAND_PACKAGE_TRANSITIONS,
        )
        if not gate["valid"]:
            logger.warning(f"Authority gate denied: {gate['reason']}")
            return None

        db = await get_db()
        if db is None:
            return None

        update = {
            "state": new_state,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if new_state == "authorized":
            update["authorized_by"] = str(actor_id)
            update["authorized_at"] = datetime.now(UTC).isoformat()

        result = db.table("settle_demand_packages").update(update).eq("id", str(package_id)).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=matter_id,
            event_type=f"demand.{new_state}",
            actor_id=actor_id,
            actor_type=actor_role,
            entity_type="demand_package",
            entity_id=package_id,
            prior_state=package.state,
            resulting_state=new_state,
        )
        return DemandPackage(**result.data[0])

    async def authorize_demand(
        self,
        tenant_id: UUID,
        matter_id: UUID,
        request: DemandAuthorizationRequest,
        actor_role: str,
    ) -> Optional[DemandPackage]:
        gate = await settlement_authority_gate.gate_action(
            action="demand.authorize",
            actor_role=actor_role,
            actor_id=request.authorized_by,
            matter_id=matter_id,
            tenant_id=tenant_id,
        )
        if not gate["valid"]:
            logger.warning(f"Demand authorization denied: {gate['reason']}")
            return None

        package = await self.get_demand_package(request.package_id)
        if package is None:
            return None
        if package.state != "attorney_review":
            logger.warning(f"Cannot authorize package in state '{package.state}'")
            return None

        return await self.update_demand_package_state(
            package_id=request.package_id,
            new_state="authorized",
            actor_id=request.authorized_by,
            actor_role=actor_role,
            tenant_id=tenant_id,
            matter_id=matter_id,
        )

    async def create_demand_transmission(
        self,
        tenant_id: UUID,
        matter_id: UUID,
        request: DemandTransmitRequest,
        transmitted_by: UUID,
        actor_role: str,
    ) -> Optional[DemandTransmission]:
        package = await self.get_demand_package(request.package_id)
        if package is None:
            return None
        if package.state != "authorized":
            logger.warning(f"Package must be authorized to transmit. Current: {package.state}")
            return None

        db = await get_db()
        if db is None:
            return None

        now = datetime.now(UTC)
        transmission_id = uuid4()
        record = {
            "id": str(transmission_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(matter_id),
            "package_id": str(request.package_id),
            "package_version": package.version,
            "recipient": request.recipient,
            "recipient_contact_id": str(request.recipient_contact_id) if request.recipient_contact_id else None,
            "method": request.method,
            "status": "transmitted",
            "transmission_notes": request.transmission_notes,
            "transmitted_by": str(transmitted_by),
            "transmitted_at": now.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_demand_transmissions").insert(record).execute()
        if not result.data:
            return None

        await self.update_demand_package_state(
            package_id=request.package_id,
            new_state="sent",
            actor_id=transmitted_by,
            actor_role=actor_role,
            tenant_id=tenant_id,
            matter_id=matter_id,
        )

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=matter_id,
            event_type="demand.transmitted",
            actor_id=transmitted_by,
            actor_type=actor_role,
            entity_type="demand_transmission",
            entity_id=transmission_id,
        )
        return DemandTransmission(**result.data[0])

    async def get_demand_transmissions(self, matter_id: UUID) -> List[DemandTransmission]:
        db = await get_db()
        if db is None:
            return []
        result = db.table("settle_demand_transmissions").select("*").eq("matter_id", str(matter_id)).order("transmitted_at", desc=True).execute()
        if not result.data:
            return []
        return [DemandTransmission(**r) for r in result.data]

    async def create_demand_draft(
        self,
        tenant_id: UUID,
        data: DemandDraftCreate,
        created_by: UUID,
    ) -> Optional[DemandDraft]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        draft_id = uuid4()
        record = {
            "id": str(draft_id),
            "matter_id": str(data.matter_id),
            "package_id": str(data.package_id) if data.package_id else None,
            "version": 1,
            "title": data.title,
            "generated_by": data.generated_by,
            "is_ai_generated": data.is_ai_generated,
            "state": "drafting",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_demand_drafts").insert(record).execute()
        if not result.data:
            return None
        return DemandDraft(**result.data[0])

    async def review_demand_draft(
        self,
        tenant_id: UUID,
        matter_id: UUID,
        review: DemandDraftReview,
    ) -> Optional[DemandDraft]:
        db = await get_db()
        if db is None:
            return None

        if review.action == "approve":
            new_state = "authorized"
        else:
            new_state = "revision_required"

        update = {
            "state": new_state,
            "attorney_reviewer_id": str(review.reviewer_id),
            "attorney_notes": review.notes,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if review.action == "approve":
            update["authorized_at"] = datetime.now(UTC).isoformat()

        result = db.table("settle_demand_drafts").update(update).eq("id", str(review.draft_id)).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=matter_id,
            event_type="demand.attorney_review_requested",
            actor_id=review.reviewer_id,
            actor_type="attorney",
            entity_type="demand_draft",
            entity_id=review.draft_id,
            resulting_state=new_state,
        )
        return DemandDraft(**result.data[0])


demand_service = DemandService()
