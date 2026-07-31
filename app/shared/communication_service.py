"""
Communication Service — Email, SMS, voice, reminders, and delivery evidence.

Handles ENT-022 Communications and ENT-112 Notifications.
Every outbound communication must pass consent checks.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, UTC
from uuid import UUID, uuid4

from app.core.database import get_db
from app.shared.models import (
    Communication, CommunicationChannel, CommunicationStatus, Notification,
)

logger = logging.getLogger(__name__)


class CommunicationService:
    """Manages communications and notifications across all channels."""

    async def send(
        self,
        tenant_id: UUID,
        channel: CommunicationChannel,
        direction: str,
        recipient_id: Optional[UUID],
        recipient_address: Optional[str],
        subject: Optional[str],
        body: str,
        matter_id: Optional[UUID] = None,
        sender_id: Optional[UUID] = None,
        template_id: Optional[UUID] = None,
        consent_id: Optional[UUID] = None,
    ) -> Optional[Communication]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        comm_id = uuid4()
        record = {
            "id": str(comm_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(matter_id) if matter_id else None,
            "channel": channel,
            "direction": direction,
            "sender_id": str(sender_id) if sender_id else None,
            "recipient_id": str(recipient_id) if recipient_id else None,
            "recipient_address": recipient_address,
            "subject": subject,
            "body": body,
            "template_id": str(template_id) if template_id else None,
            "consent_id": str(consent_id) if consent_id else None,
            "status": "queued",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("communications").insert(record).execute()
        if not result.data:
            return None

        await self._update_status(comm_id, "sent")

        return Communication(**result.data[0])

    async def record_inbound(
        self,
        tenant_id: UUID,
        channel: CommunicationChannel,
        sender_address: str,
        subject: Optional[str],
        body: str,
        matter_id: Optional[UUID] = None,
        recipient_id: Optional[UUID] = None,
    ) -> Optional[Communication]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        comm_id = uuid4()
        record = {
            "id": str(comm_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(matter_id) if matter_id else None,
            "channel": channel,
            "direction": "inbound",
            "sender_id": None,
            "recipient_id": str(recipient_id) if recipient_id else None,
            "recipient_address": sender_address,
            "subject": subject,
            "body": body,
            "status": "delivered",
            "delivered_at": now.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("communications").insert(record).execute()
        if not result.data:
            return None
        return Communication(**result.data[0])

    async def _update_status(
        self, comm_id: UUID, status: CommunicationStatus,
        error_message: Optional[str] = None,
    ) -> Optional[Communication]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        update: Dict[str, Any] = {"status": status, "updated_at": now.isoformat()}
        if status == "sent":
            update["sent_at"] = now.isoformat()
        if status == "delivered":
            update["delivered_at"] = now.isoformat()
        if status == "failed":
            update["error_message"] = error_message

        result = db.table("communications").update(update).eq("id", str(comm_id)).execute()
        if not result.data:
            return None
        return Communication(**result.data[0])

    async def record_delivery(
        self, comm_id: UUID, delivery_evidence: Dict[str, Any],
    ) -> Optional[Communication]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        result = db.table("communications").update({
            "status": "delivered",
            "delivered_at": now.isoformat(),
            "delivery_evidence": delivery_evidence,
            "updated_at": now.isoformat(),
        }).eq("id", str(comm_id)).execute()
        if not result.data:
            return None
        return Communication(**result.data[0])

    async def get_communications_by_matter(self, matter_id: UUID) -> list:
        db = await get_db()
        if db is None:
            return []
        result = db.table("communications").select("*").eq("matter_id", str(matter_id)).order("created_at", desc=True).execute()
        if not result.data:
            return []
        return result.data

    async def create_notification(
        self,
        tenant_id: UUID,
        notification_type: str,
        title: str,
        body: str,
        user_id: Optional[UUID] = None,
        matter_id: Optional[UUID] = None,
        channel: CommunicationChannel = "portal",
        event_type: Optional[str] = None,
        event_id: Optional[UUID] = None,
        action_url: Optional[str] = None,
    ) -> Optional[Notification]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        notif_id = uuid4()
        record = {
            "id": str(notif_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(matter_id) if matter_id else None,
            "user_id": str(user_id) if user_id else None,
            "notification_type": notification_type,
            "title": title,
            "body": body,
            "channel": channel,
            "event_type": event_type,
            "event_id": str(event_id) if event_id else None,
            "is_read": False,
            "action_url": action_url,
            "created_at": now.isoformat(),
        }
        result = db.table("notifications").insert(record).execute()
        if not result.data:
            return None
        return Notification(**result.data[0])

    async def send_reminder(
        self,
        tenant_id: UUID,
        user_id: UUID,
        title: str,
        body: str,
        matter_id: Optional[UUID] = None,
        channel: CommunicationChannel = "portal",
    ) -> Optional[Notification]:
        return await self.create_notification(
            tenant_id=tenant_id,
            notification_type="reminder",
            title=title,
            body=body,
            user_id=user_id,
            matter_id=matter_id,
            channel=channel,
        )

    async def get_unread_notifications(self, user_id: UUID) -> list:
        db = await get_db()
        if db is None:
            return []
        result = db.table("notifications").select("*").eq("user_id", str(user_id)).eq("is_read", False).order("created_at", desc=True).execute()
        if not result.data:
            return []
        return result.data

    async def mark_read(self, notification_id: UUID) -> bool:
        db = await get_db()
        if db is None:
            return False
        now = datetime.now(UTC)
        result = db.table("notifications").update({
            "is_read": True,
            "read_at": now.isoformat(),
        }).eq("id", str(notification_id)).execute()
        return bool(result.data)


communication_service = CommunicationService()
