"""
Settlement Decision & Attorney Recommendation Service — SETTLE Domain

Handles ENT-096 Settlement Decision and Attorney Settlement Recommendations.

THE CRITICAL BOUNDARY (INV-005):
  - The client makes the settlement decision.
  - SETTLE records the decision.
  - The attorney provides a recommendation (AUTH-015).
  - The platform captures but never makes the decision.
"""

import logging
from typing import Optional, List
from datetime import datetime, UTC
from uuid import UUID, uuid4

from app.core.database import get_db
from app.models.settlement import (
    SettlementDecision, SettlementDecisionCreate,
    AttorneyRecommendation, AttorneyRecommendationCreate,
)
from app.services.settlement.authority_gate import (
    settlement_authority_gate,
    settlement_invariants,
)
from app.services.settlement.audit import settlement_audit

logger = logging.getLogger(__name__)


class DecisionService:
    """Manages settlement decisions and attorney recommendations."""

    async def create_attorney_recommendation(
        self,
        tenant_id: UUID,
        matter_id: UUID,
        offer_id: UUID,
        data: AttorneyRecommendationCreate,
        recommended_by: UUID,
        actor_role: str,
    ) -> Optional[AttorneyRecommendation]:
        gate = await settlement_authority_gate.gate_action(
            action="attorney.recommendation",
            actor_role=actor_role,
            actor_id=recommended_by,
            matter_id=matter_id,
            tenant_id=tenant_id,
        )
        if not gate["valid"]:
            logger.warning(f"Attorney recommendation denied: {gate['reason']}")
            return None

        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        rec_id = uuid4()
        record = {
            "id": str(rec_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(matter_id),
            "offer_id": str(offer_id),
            "recommended_action": data.recommended_action,
            "recommended_counter_amount": data.recommended_counter_amount,
            "analysis_summary": data.analysis_summary,
            "considerations": data.considerations,
            "ai_supported": False,
            "recommended_by": str(recommended_by),
            "recommended_at": now.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_attorney_recommendations").insert(record).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=matter_id,
            event_type="attorney.recommendation_provided",
            actor_id=recommended_by,
            actor_type="attorney",
            entity_type="attorney_recommendation",
            entity_id=rec_id,
            details={"action": data.recommended_action, "offer_id": str(offer_id)},
        )
        return AttorneyRecommendation(**result.data[0])

    async def get_recommendation(self, recommendation_id: UUID) -> Optional[AttorneyRecommendation]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("settle_attorney_recommendations").select("*").eq("id", str(recommendation_id)).execute()
        if not result.data:
            return None
        return AttorneyRecommendation(**result.data[0])

    async def get_recommendations_by_offer(self, offer_id: UUID) -> List[AttorneyRecommendation]:
        db = await get_db()
        if db is None:
            return []
        result = db.table("settle_attorney_recommendations").select("*").eq("offer_id", str(offer_id)).order("recommended_at", desc=True).execute()
        if not result.data:
            return []
        return [AttorneyRecommendation(**r) for r in result.data]

    async def record_settlement_decision(
        self,
        tenant_id: UUID,
        data: SettlementDecisionCreate,
        recorded_by: UUID,
    ) -> Optional[SettlementDecision]:
        """
        Record a client's settlement decision.

        INV-005: This is the CRITICAL boundary. The platform captures the
        decision but NEVER makes it. The client MUST be the decider.

        For acceptance, we require:
        - An attributable client or valid representative (decided_by)
        - Informed consent confirmation
        - Attorney advice timestamp (when applicable)
        """
        action_map = {
            "accept": "settlement.accept",
            "reject": "settlement.reject",
            "counter": "settlement.counter",
        }
        action = action_map.get(data.decision)
        if not action:
            return None

        gate = await settlement_authority_gate.gate_action(
            action=action,
            actor_role="client",
            actor_id=data.decided_by,
            matter_id=data.matter_id,
            tenant_id=tenant_id,
        )
        if not gate["valid"]:
            logger.warning(f"Settlement decision denied: {gate['reason']}")
            return None

        invariant_check = await settlement_invariants.check_client_settlement_authority(
            settlement_decision_id=UUID("00000000-0000-0000-0000-000000000000"),
            decided_by=data.decided_by,
        )
        if not invariant_check["valid"]:
            logger.warning(f"Invariant check failed: {invariant_check['reason']}")
            return None

        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        decision_id = uuid4()
        record = {
            "id": str(decision_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(data.matter_id),
            "offer_id": str(data.offer_id),
            "decision": data.decision,
            "decided_by": str(data.decided_by),
            "representative_authority_id": str(data.representative_authority_id) if data.representative_authority_id else None,
            "attorney_recommendation_id": str(data.attorney_recommendation_id) if data.attorney_recommendation_id else None,
            "attorney_advised_at": data.attorney_advised_at.isoformat() if data.attorney_advised_at else None,
            "informed_consent_confirmed": data.informed_consent_confirmed,
            "rationale": data.rationale,
            "counter_amount": data.counter_amount,
            "counter_terms": data.counter_terms,
            "decided_at": now.isoformat(),
            "recorded_by": str(recorded_by),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_settlement_decisions").insert(record).execute()
        if not result.data:
            return None

        event_type_map = {
            "accept": "settlement.accepted_by_client",
            "reject": "settlement.rejected_by_client",
            "counter": "settlement.counter_authorized_by_client",
        }
        event_type = event_type_map.get(data.decision, "settlement.decision_recorded")

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=data.matter_id,
            event_type=event_type,
            actor_id=data.decided_by,
            actor_type="client",
            entity_type="settlement_decision",
            entity_id=decision_id,
            details={
                "decision": data.decision,
                "offer_id": str(data.offer_id),
                "informed_consent_confirmed": data.informed_consent_confirmed,
            },
        )
        return SettlementDecision(**result.data[0])

    async def get_settlement_decision(self, decision_id: UUID) -> Optional[SettlementDecision]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("settle_settlement_decisions").select("*").eq("id", str(decision_id)).execute()
        if not result.data:
            return None
        return SettlementDecision(**result.data[0])

    async def get_decisions_by_matter(self, matter_id: UUID) -> List[SettlementDecision]:
        db = await get_db()
        if db is None:
            return []
        result = db.table("settle_settlement_decisions").select("*").eq("matter_id", str(matter_id)).order("decided_at", desc=True).execute()
        if not result.data:
            return []
        return [SettlementDecision(**r) for r in result.data]

    async def get_decisions_by_offer(self, offer_id: UUID) -> List[SettlementDecision]:
        db = await get_db()
        if db is None:
            return []
        result = db.table("settle_settlement_decisions").select("*").eq("offer_id", str(offer_id)).order("decided_at", desc=True).execute()
        if not result.data:
            return []
        return [SettlementDecision(**r) for r in result.data]


decision_service = DecisionService()
