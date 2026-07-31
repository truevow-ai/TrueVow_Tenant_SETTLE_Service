"""
Audit Event Store — Preserves legally and operationally significant evidence.

Implements the ontology Event Envelope contract:
  - append_only (immutable)
  - idempotent_by_event_id
  - tenant_scoped
  - schema_versioned
  - no_secrets_in_payload

INV-015: Business audit evidence is not derived solely from mutable diagnostic logs.
INV-021: Audit event is append-only and tenant-scoped.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, UTC
from uuid import UUID, uuid4

from app.core.database import get_db
from app.shared.models import (
    EventEnvelope, AuthorityClass, ActorRole,
)

logger = logging.getLogger(__name__)


class AuditEventStore:
    """Append-only, immutable audit event storage."""

    async def record_event(
        self,
        tenant_id: UUID,
        event_type: str,
        aggregate_type: str,
        aggregate_id: UUID,
        aggregate_version: int,
        actor_type: ActorRole,
        actor_id: UUID,
        authority_class: AuthorityClass,
        authority_record_id: UUID,
        policy_version_id: UUID,
        payload: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[UUID] = None,
        causation_id: Optional[UUID] = None,
        prior_state: Optional[str] = None,
        resulting_state: Optional[str] = None,
        sensitivity_class: str = "internal",
    ) -> Optional[UUID]:
        db = await get_db()
        if db is None:
            logger.warning(f"Audit event not recorded (no DB): {event_type}")
            return None

        now = datetime.now(UTC)
        event_id = uuid4()

        envelope = EventEnvelope(
            event_id=event_id,
            event_type=event_type,
            occurred_at=now,
            recorded_at=now,
            tenant_id=tenant_id,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            aggregate_version=aggregate_version,
            actor_type=actor_type,
            actor_id=actor_id,
            authority_class=authority_class,
            authority_record_id=authority_record_id,
            policy_version_id=policy_version_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
            payload=payload or {},
            sensitivity_class=sensitivity_class,
            schema_version="1.0.1",
        )

        record = {
            "id": str(envelope.event_id),
            "tenant_id": str(envelope.tenant_id),
            "event_type": envelope.event_type,
            "occurred_at": envelope.occurred_at.isoformat(),
            "recorded_at": envelope.recorded_at.isoformat(),
            "aggregate_type": envelope.aggregate_type,
            "aggregate_id": str(envelope.aggregate_id),
            "aggregate_version": envelope.aggregate_version,
            "actor_type": envelope.actor_type.value,
            "actor_id": str(envelope.actor_id),
            "authority_class": envelope.authority_class.value,
            "authority_record_id": str(envelope.authority_record_id),
            "policy_version_id": str(envelope.policy_version_id),
            "correlation_id": str(envelope.correlation_id) if envelope.correlation_id else None,
            "causation_id": str(envelope.causation_id) if envelope.causation_id else None,
            "prior_state": prior_state,
            "resulting_state": resulting_state,
            "payload": envelope.payload,
            "sensitivity_class": envelope.sensitivity_class,
            "schema_version": "1.0.1",
        }

        try:
            result = db.table("audit_events").insert(record).execute()
            if result.data:
                return event_id
            return None
        except Exception as e:
            logger.error(f"Failed to record audit event: {e}")
            return None

    async def get_events(
        self,
        tenant_id: UUID,
        aggregate_type: Optional[str] = None,
        aggregate_id: Optional[UUID] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list:
        db = await get_db()
        if db is None:
            return []
        query = db.table("audit_events").select("*").eq("tenant_id", str(tenant_id))
        if aggregate_type:
            query = query.eq("aggregate_type", aggregate_type)
        if aggregate_id:
            query = query.eq("aggregate_id", str(aggregate_id))
        if event_type:
            query = query.eq("event_type", event_type)
        query = query.order("occurred_at", desc=True).limit(limit).offset(offset)
        result = query.execute()
        if not result.data:
            return []
        return result.data

    async def get_timeline(self, tenant_id: UUID, aggregate_id: UUID) -> list:
        return await self.get_events(
            tenant_id=tenant_id,
            aggregate_id=aggregate_id,
            limit=500,
        )

    async def check_idempotent(self, event_id: UUID) -> bool:
        db = await get_db()
        if db is None:
            return False
        result = db.table("audit_events").select("id").eq("id", str(event_id)).limit(1).execute()
        return bool(result.data)


audit_event_store = AuditEventStore()
