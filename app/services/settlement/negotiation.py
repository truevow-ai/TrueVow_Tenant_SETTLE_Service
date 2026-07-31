"""
Negotiation & Offer Service — SETTLE Domain

Handles ENT-093 Negotiation Round, ENT-094 Offer, ENT-095 Counteroffer.

Critical boundary: The client makes the settlement decision.
SETTLE records and supports the decision.
"""

import logging
from typing import Optional, List
from datetime import datetime, UTC
from uuid import UUID, uuid4

from app.core.database import get_db
from app.models.settlement import (
    NegotiationRound, NegotiationRoundCreate,
    Offer, OfferCreate,
    Counteroffer, CounterofferCreate, CounterofferAuthorize,
)
from app.services.settlement.authority_gate import (
    settlement_authority_gate,
    OFFER_TRANSITIONS,
)
from app.services.settlement.audit import settlement_audit

logger = logging.getLogger(__name__)


class NegotiationService:
    """Manages negotiation rounds, offers, and counteroffers."""

    async def create_negotiation_round(
        self,
        tenant_id: UUID,
        data: NegotiationRoundCreate,
        created_by: UUID,
    ) -> Optional[NegotiationRound]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)

        existing = db.table("settle_negotiation_rounds").select("round_number").eq("matter_id", str(data.matter_id)).order("round_number", desc=True).limit(1).execute()
        next_round = 1
        if existing.data:
            next_round = existing.data[0].get("round_number", 0) + 1

        round_id = uuid4()
        record = {
            "id": str(round_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(data.matter_id),
            "claim_ids": [str(c) for c in data.claim_ids],
            "round_number": next_round,
            "opened_at": now.isoformat(),
            "status": "open",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_negotiation_rounds").insert(record).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=data.matter_id,
            event_type="negotiation.round_opened",
            actor_id=created_by,
            actor_type="attorney",
            entity_type="negotiation_round",
            entity_id=round_id,
        )
        return NegotiationRound(**result.data[0])

    async def get_negotiation_round(self, round_id: UUID) -> Optional[NegotiationRound]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("settle_negotiation_rounds").select("*").eq("id", str(round_id)).execute()
        if not result.data:
            return None
        return NegotiationRound(**result.data[0])

    async def get_negotiation_rounds_by_matter(self, matter_id: UUID) -> List[NegotiationRound]:
        db = await get_db()
        if db is None:
            return []
        result = db.table("settle_negotiation_rounds").select("*").eq("matter_id", str(matter_id)).order("round_number", desc=False).execute()
        if not result.data:
            return []
        return [NegotiationRound(**r) for r in result.data]

    async def record_offer(
        self,
        tenant_id: UUID,
        data: OfferCreate,
        recorded_by: UUID,
        actor_role: str,
    ) -> Optional[Offer]:
        gate = await settlement_authority_gate.gate_action(
            action="offer.record",
            actor_role=actor_role,
            actor_id=recorded_by,
            matter_id=data.matter_id,
            tenant_id=tenant_id,
        )
        if not gate["valid"]:
            logger.warning(f"Offer recording denied: {gate['reason']}")
            return None

        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        offer_id = uuid4()

        record = {
            "id": str(offer_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(data.matter_id),
            "negotiation_round_id": str(data.negotiation_round_id),
            "claim_ids": [str(c) for c in data.claim_ids],
            "source": data.source,
            "source_contact_id": str(data.source_contact_id) if data.source_contact_id else None,
            "amount": data.amount,
            "is_global": data.is_global,
            "terms_summary": data.terms_summary,
            "expiration_date": data.expiration_date.isoformat() if data.expiration_date else None,
            "status": "offer_received",
            "received_at": data.received_at.isoformat() if data.received_at else now.isoformat(),
            "note": data.note,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_offers").insert(record).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=data.matter_id,
            event_type="offer.received",
            actor_id=recorded_by,
            actor_type=actor_role,
            entity_type="offer",
            entity_id=offer_id,
            details={"amount": data.amount, "source": data.source},
        )
        return Offer(**result.data[0])

    async def get_offer(self, offer_id: UUID) -> Optional[Offer]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("settle_offers").select("*").eq("id", str(offer_id)).execute()
        if not result.data:
            return None
        return Offer(**result.data[0])

    async def get_offers_by_matter(self, matter_id: UUID) -> List[Offer]:
        db = await get_db()
        if db is None:
            return []
        result = db.table("settle_offers").select("*").eq("matter_id", str(matter_id)).order("received_at", desc=True).execute()
        if not result.data:
            return []
        return [Offer(**r) for r in result.data]

    async def get_offers_by_round(self, negotiation_round_id: UUID) -> List[Offer]:
        db = await get_db()
        if db is None:
            return []
        result = db.table("settle_offers").select("*").eq("negotiation_round_id", str(negotiation_round_id)).order("received_at", desc=True).execute()
        if not result.data:
            return []
        return [Offer(**r) for r in result.data]

    async def update_offer_status(
        self,
        offer_id: UUID,
        new_status: str,
        actor_id: UUID,
        actor_role: str,
        tenant_id: UUID,
        matter_id: UUID,
    ) -> Optional[Offer]:
        offer = await self.get_offer(offer_id)
        if offer is None:
            return None

        gate = await settlement_authority_gate.gate_action(
            action="offer.notify_client" if new_status == "client_notice_pending" else "offer.record",
            actor_role=actor_role,
            actor_id=actor_id,
            matter_id=matter_id,
            tenant_id=tenant_id,
            current_state=offer.status,
            target_state=new_status,
            transition_map=OFFER_TRANSITIONS,
        )
        if not gate["valid"]:
            logger.warning(f"Offer status update denied: {gate['reason']}")
            return None

        db = await get_db()
        if db is None:
            return None

        update_data = {
            "status": new_status,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if new_status == "client_notice_pending":
            update_data["client_notified_at"] = datetime.now(UTC).isoformat()

        result = db.table("settle_offers").update(update_data).eq("id", str(offer_id)).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=matter_id,
            event_type=f"offer.{new_status}",
            actor_id=actor_id,
            actor_type=actor_role,
            entity_type="offer",
            entity_id=offer_id,
            prior_state=offer.status,
            resulting_state=new_status,
        )
        return Offer(**result.data[0])

    async def create_counteroffer(
        self,
        tenant_id: UUID,
        data: CounterofferCreate,
        created_by: UUID,
    ) -> Optional[Counteroffer]:
        offer = await self.get_offer(data.responds_to_offer_id)
        if offer is None:
            return None

        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        counter_id = uuid4()

        record = {
            "id": str(counter_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(data.matter_id),
            "negotiation_round_id": str(data.negotiation_round_id),
            "responds_to_offer_id": str(data.responds_to_offer_id),
            "claim_ids": [str(c) for c in data.claim_ids],
            "amount": data.amount,
            "is_global": data.is_global,
            "terms_summary": data.terms_summary,
            "expiration_date": data.expiration_date.isoformat() if data.expiration_date else None,
            "authorized_by_client": False,
            "status": "draft",
            "note": data.note,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_counteroffers").insert(record).execute()
        if not result.data:
            return None
        return Counteroffer(**result.data[0])

    async def authorize_counteroffer(
        self,
        tenant_id: UUID,
        matter_id: UUID,
        data: CounterofferAuthorize,
        actor_role: str,
    ) -> Optional[Counteroffer]:
        gate = await settlement_authority_gate.gate_action(
            action="counteroffer.authorize",
            actor_role=actor_role,
            actor_id=data.client_decision_id,
            matter_id=matter_id,
            tenant_id=tenant_id,
        )
        if not gate["valid"]:
            logger.warning(f"Counteroffer authorization denied: {gate['reason']}")
            return None

        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)

        update = {
            "status": "authorized",
            "authorized_by_client": True,
            "client_authorization_id": str(data.client_decision_id),
            "authorized_by_attorney": str(data.attorney_id),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_counteroffers").update(update).eq("id", str(data.counteroffer_id)).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=matter_id,
            event_type="counteroffer.authorized",
            actor_id=data.attorney_id,
            actor_type=actor_role,
            entity_type="counteroffer",
            entity_id=data.counteroffer_id,
            details={"client_decision_id": str(data.client_decision_id)},
        )
        return Counteroffer(**result.data[0])

    async def get_counteroffers_by_matter(self, matter_id: UUID) -> List[Counteroffer]:
        db = await get_db()
        if db is None:
            return []
        result = db.table("settle_counteroffers").select("*").eq("matter_id", str(matter_id)).order("created_at", desc=True).execute()
        if not result.data:
            return []
        return [Counteroffer(**r) for r in result.data]

    async def close_negotiation_round(
        self,
        round_id: UUID,
        actor_id: UUID,
        tenant_id: UUID,
        matter_id: UUID,
    ) -> Optional[NegotiationRound]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        result = db.table("settle_negotiation_rounds").update({
            "status": "closed",
            "closed_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }).eq("id", str(round_id)).execute()
        if not result.data:
            return None
        return NegotiationRound(**result.data[0])


negotiation_service = NegotiationService()
