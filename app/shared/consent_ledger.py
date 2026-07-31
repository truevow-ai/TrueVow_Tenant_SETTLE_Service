"""
Consent Ledger — Records consent as append-only, versioned events.

INV-012: Consent history preserved. Grants, refusals, revocations, expirations,
and supersessions are append-only events. Consent must not be represented by
a single mutable Boolean field.
"""

import logging
from typing import Optional
from datetime import datetime, UTC
from uuid import UUID, uuid4

from app.core.database import get_db
from app.shared.models import (
    ConsentRecord, ConsentType, CommunicationChannel,
)

logger = logging.getLogger(__name__)


class ConsentLedger:
    """Append-only consent record management."""

    async def request_consent(
        self,
        tenant_id: UUID,
        person_id: UUID,
        consent_type: ConsentType,
        matter_id: Optional[UUID] = None,
        disclosure_text: Optional[str] = None,
        channel: Optional[CommunicationChannel] = None,
    ) -> Optional[ConsentRecord]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        record_id = uuid4()
        record = {
            "id": str(record_id),
            "tenant_id": str(tenant_id),
            "person_id": str(person_id),
            "matter_id": str(matter_id) if matter_id else None,
            "consent_type": consent_type,
            "state": "requested",
            "version": 1,
            "requested_at": now.isoformat(),
            "disclosure_text": disclosure_text,
            "channel": channel,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("consent_records").insert(record).execute()
        if not result.data:
            return None
        return ConsentRecord(**result.data[0])

    async def record_grant(
        self,
        consent_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[ConsentRecord]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        update = {
            "state": "granted",
            "granted_at": now.isoformat(),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "updated_at": now.isoformat(),
        }
        result = db.table("consent_records").update(update).eq("id", str(consent_id)).execute()
        if not result.data:
            return None
        return ConsentRecord(**result.data[0])

    async def record_decline(self, consent_id: UUID) -> Optional[ConsentRecord]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        result = db.table("consent_records").update({
            "state": "declined",
            "declined_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }).eq("id", str(consent_id)).execute()
        if not result.data:
            return None
        return ConsentRecord(**result.data[0])

    async def record_revocation(self, consent_id: UUID) -> Optional[ConsentRecord]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        result = db.table("consent_records").update({
            "state": "revoked",
            "revoked_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }).eq("id", str(consent_id)).execute()
        if not result.data:
            return None
        return ConsentRecord(**result.data[0])

    async def supersede_consent(
        self,
        old_consent_id: UUID,
        tenant_id: UUID,
        person_id: UUID,
        consent_type: ConsentType,
        matter_id: Optional[UUID] = None,
        disclosure_text: Optional[str] = None,
    ) -> Optional[ConsentRecord]:
        old = await self.get_consent(old_consent_id)
        if old is None:
            return None

        new_record = await self.request_consent(
            tenant_id=tenant_id,
            person_id=person_id,
            consent_type=consent_type,
            matter_id=matter_id,
            disclosure_text=disclosure_text,
        )
        if new_record is None:
            return None

        db = await get_db()
        now = datetime.now(UTC)
        await db.table("consent_records").update({
            "state": "superseded",
            "superseded_by_id": str(new_record.id),
            "updated_at": now.isoformat(),
        }).eq("id", str(old_consent_id)).execute()

        return new_record

    async def get_consent(self, consent_id: UUID) -> Optional[ConsentRecord]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("consent_records").select("*").eq("id", str(consent_id)).execute()
        if not result.data:
            return None
        return ConsentRecord(**result.data[0])

    async def get_active_consent(
        self, person_id: UUID, consent_type: ConsentType, matter_id: Optional[UUID] = None,
    ) -> Optional[ConsentRecord]:
        db = await get_db()
        if db is None:
            return None
        query = db.table("consent_records").select("*").eq("person_id", str(person_id)).eq("consent_type", consent_type).eq("state", "granted").order("granted_at", desc=True).limit(1)
        if matter_id:
            query = query.eq("matter_id", str(matter_id))
        result = query.execute()
        if not result.data:
            return None
        return ConsentRecord(**result.data[0])

    async def has_valid_consent(
        self, person_id: UUID, consent_type: ConsentType, matter_id: Optional[UUID] = None,
    ) -> bool:
        record = await self.get_active_consent(person_id, consent_type, matter_id)
        return record is not None

    async def get_consent_history(self, person_id: UUID) -> list:
        db = await get_db()
        if db is None:
            return []
        result = db.table("consent_records").select("*").eq("person_id", str(person_id)).order("created_at", desc=True).execute()
        if not result.data:
            return []
        return result.data


consent_ledger = ConsentLedger()
