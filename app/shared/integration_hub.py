"""
Integration Hub — Connects calendars, CRM/case systems, signatures, accounting, and exports.

Manages ENT-009 Integration Connections. Each integration is tenant-scoped,
versioned, and synchronized through adapters. External sync status never silently
changes the authoritative business state (INV-016).
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
from uuid import UUID, uuid4

from app.core.database import get_db
from app.shared.models import IntegrationConnection, IntegrationType

logger = logging.getLogger(__name__)


class IntegrationHub:
    """Manages external system integrations for tenants."""

    async def connect(
        self,
        tenant_id: UUID,
        name: str,
        integration_type: IntegrationType,
        provider: str,
        config: Dict[str, Any],
    ) -> Optional[IntegrationConnection]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        conn_id = uuid4()
        record = {
            "id": str(conn_id),
            "tenant_id": str(tenant_id),
            "name": name,
            "integration_type": integration_type,
            "provider": provider,
            "config": config,
            "is_active": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("integration_connections").insert(record).execute()
        if not result.data:
            return None
        return IntegrationConnection(**result.data[0])

    async def get_connection(self, conn_id: UUID) -> Optional[IntegrationConnection]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("integration_connections").select("*").eq("id", str(conn_id)).execute()
        if not result.data:
            return None
        return IntegrationConnection(**result.data[0])

    async def get_tenant_connections(
        self, tenant_id: UUID, integration_type: Optional[IntegrationType] = None,
    ) -> List[IntegrationConnection]:
        db = await get_db()
        if db is None:
            return []
        query = db.table("integration_connections").select("*").eq("tenant_id", str(tenant_id)).eq("is_active", True)
        if integration_type:
            query = query.eq("integration_type", integration_type)
        result = query.execute()
        if not result.data:
            return []
        return [IntegrationConnection(**r) for r in result.data]

    async def update_connection(
        self, conn_id: UUID, config: Dict[str, Any],
    ) -> Optional[IntegrationConnection]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        result = db.table("integration_connections").update({
            "config": config,
            "updated_at": now.isoformat(),
        }).eq("id", str(conn_id)).execute()
        if not result.data:
            return None
        return IntegrationConnection(**result.data[0])

    async def record_sync(
        self, conn_id: UUID, status: str, error: Optional[str] = None,
    ) -> Optional[IntegrationConnection]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        result = db.table("integration_connections").update({
            "last_sync_at": now.isoformat(),
            "last_sync_status": status,
            "last_sync_error": error,
            "updated_at": now.isoformat(),
        }).eq("id", str(conn_id)).execute()
        if not result.data:
            return None
        return IntegrationConnection(**result.data[0])

    async def disconnect(self, conn_id: UUID) -> bool:
        db = await get_db()
        if db is None:
            return False
        now = datetime.now(UTC)
        result = db.table("integration_connections").update({
            "is_active": False,
            "updated_at": now.isoformat(),
        }).eq("id", str(conn_id)).execute()
        return bool(result.data)


integration_hub = IntegrationHub()
