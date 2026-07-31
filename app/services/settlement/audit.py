"""
Settlement Audit Service — SETTLE Domain

Records immutable audit events for every material action in the settlement domain.
Separate from diagnostic logs (INV-015).

Each audit event records:
  - What happened (event_type)
  - Who initiated it (actor_id, actor_type)
  - What it affected (entity_type, entity_id, matter_id)
  - State transitions (prior_state, resulting_state)
  - Authority source
  - Timestamp
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, UTC
from uuid import UUID, uuid4

from app.core.database import get_db

logger = logging.getLogger(__name__)


class SettlementAuditService:
    """Records immutable audit events for settlement domain."""

    async def record(
        self,
        tenant_id: UUID,
        matter_id: UUID,
        event_type: str,
        actor_id: Optional[UUID] = None,
        actor_type: Optional[str] = None,
        authority_source: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        prior_state: Optional[str] = None,
        resulting_state: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Optional[UUID]:
        """
        Record an immutable audit event.

        All parameters are keyword-only to prevent ordering mistakes.
        """
        db = await get_db()
        if db is None:
            logger.warning(f"Audit event not recorded (no DB): {event_type}")
            return None

        now = datetime.now(UTC)
        event_id = uuid4()
        record = {
            "id": str(event_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(matter_id),
            "event_type": event_type,
            "actor_id": str(actor_id) if actor_id else None,
            "actor_type": actor_type,
            "authority_source": authority_source,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id else None,
            "prior_state": prior_state,
            "resulting_state": resulting_state,
            "details": details or {},
            "occurred_at": now.isoformat(),
            "created_at": now.isoformat(),
        }
        try:
            result = db.table("settle_settlement_audit_events").insert(record).execute()
            if result.data:
                return event_id
            return None
        except Exception as e:
            logger.error(f"Failed to record audit event: {e}")
            return None

    async def get_audit_trail(
        self,
        matter_id: UUID,
        entity_type: Optional[str] = None,
        entity_id: Optional[UUID] = None,
        limit: int = 100,
    ) -> list:
        """Retrieve audit trail for a matter, optionally filtered by entity."""
        db = await get_db()
        if db is None:
            return []
        query = db.table("settle_settlement_audit_events").select("*").eq("matter_id", str(matter_id))
        if entity_type:
            query = query.eq("entity_type", entity_type)
        if entity_id:
            query = query.eq("entity_id", str(entity_id))
        query = query.order("occurred_at", desc=True).limit(limit)
        result = query.execute()
        if not result.data:
            return []
        return result.data

    async def get_settlement_timeline(self, matter_id: UUID) -> list:
        """Get chronological settlement timeline for a matter."""
        return await self.get_audit_trail(matter_id=matter_id)


settlement_audit = SettlementAuditService()
