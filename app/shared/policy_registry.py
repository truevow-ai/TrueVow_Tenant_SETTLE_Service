"""
Policy Registry — Stores firm-approved rules and jurisdiction configuration.

Each tenant's governing policies, jurisdiction profiles, and configuration
versions are immutable snapshots (INV-010: Policy-at-execution).
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, UTC, date
from uuid import UUID, uuid4

from app.core.database import get_db
from app.shared.models import (
    JurisdictionProfile, FirmPolicy, ConfigurationVersion,
)

logger = logging.getLogger(__name__)


class PolicyRegistry:
    """Manages tenant firm policies, jurisdiction profiles, and config versions."""

    async def get_jurisdiction_profile(self, jurisdiction: str) -> Optional[JurisdictionProfile]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("jurisdiction_profiles").select("*").eq("jurisdiction", jurisdiction).eq("is_active", True).order("version", desc=True).limit(1).execute()
        if not result.data:
            return None
        return JurisdictionProfile(**result.data[0])

    async def get_active_profile(self, jurisdiction: str) -> Optional[JurisdictionProfile]:
        return await self.get_jurisdiction_profile(jurisdiction)

    async def is_jurisdiction_supported(self, jurisdiction: str) -> bool:
        profile = await self.get_active_profile(jurisdiction)
        return profile is not None and profile.counsel_approval_status == "approved"

    async def get_firm_policy(
        self, tenant_id: UUID, policy_type: str,
    ) -> Optional[FirmPolicy]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("firm_policies").select("*").eq("tenant_id", str(tenant_id)).eq("policy_type", policy_type).eq("is_active", True).order("version", desc=True).limit(1).execute()
        if not result.data:
            return None
        return FirmPolicy(**result.data[0])

    async def create_policy(
        self, tenant_id: UUID, policy_name: str, policy_type: str, config: Dict[str, Any],
        approved_by: UUID, effective_date: Optional[date] = None,
    ) -> Optional[FirmPolicy]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        policy_id = uuid4()
        record = {
            "id": str(policy_id),
            "tenant_id": str(tenant_id),
            "policy_name": policy_name,
            "policy_type": policy_type,
            "version": 1,
            "effective_date": (effective_date or now.date()).isoformat(),
            "config": config,
            "approved_by": str(approved_by),
            "approved_at": now.isoformat(),
            "is_active": True,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("firm_policies").insert(record).execute()
        if not result.data:
            return None
        return FirmPolicy(**result.data[0])

    async def supersede_policy(
        self, policy_id: UUID, new_config: Dict[str, Any], approved_by: UUID,
    ) -> Optional[FirmPolicy]:
        existing = await self._get_policy_by_id(policy_id)
        if existing is None:
            return None
        new_policy = await self.create_policy(
            tenant_id=existing.tenant_id,
            policy_name=existing.policy_name,
            policy_type=existing.policy_type,
            config=new_config,
            approved_by=approved_by,
        )
        if new_policy is None:
            return None
        db = await get_db()
        now = datetime.now(UTC)
        await db.table("firm_policies").update({
            "is_active": False,
            "superseded_by": str(new_policy.id),
            "updated_at": now.isoformat(),
        }).eq("id", str(policy_id)).execute()
        return new_policy

    async def _get_policy_by_id(self, policy_id: UUID) -> Optional[FirmPolicy]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("firm_policies").select("*").eq("id", str(policy_id)).execute()
        if not result.data:
            return None
        return FirmPolicy(**result.data[0])

    async def create_configuration_snapshot(
        self, tenant_id: UUID, config_type: str, config_data: Dict[str, Any],
    ) -> Optional[ConfigurationVersion]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        import hashlib
        import json
        content_hash = hashlib.sha256(json.dumps(config_data, sort_keys=True).encode()).hexdigest()

        existing = db.table("configuration_versions").select("version").eq("tenant_id", str(tenant_id)).eq("config_type", config_type).order("version", desc=True).limit(1).execute()
        next_version = (existing.data[0].get("version", 0) + 1) if existing.data else 1

        snapshot_id = uuid4()
        record = {
            "id": str(snapshot_id),
            "tenant_id": str(tenant_id),
            "config_type": config_type,
            "version": next_version,
            "content_hash": content_hash,
            "config_data": config_data,
            "captured_at": now.isoformat(),
            "created_at": now.isoformat(),
        }
        result = db.table("configuration_versions").insert(record).execute()
        if not result.data:
            return None
        return ConfigurationVersion(**result.data[0])


policy_registry = PolicyRegistry()
