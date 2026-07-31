"""
Tenant & Identity Core Service

Knows which firm, user, attorney, client, and matter owns every action.
Implements tenant isolation (INV-001), role-does-not-create-licensure (INV-018).
"""

import logging
from typing import Optional, List
from datetime import datetime, UTC, date
from uuid import UUID, uuid4

from app.core.database import get_db
from app.shared.models import (
    Tenant, UserAccount, RoleAssignment, ActorRole,
    Person, PartyRole, ContactPoint, Matter,
)

logger = logging.getLogger(__name__)


class TenantCore:
    """Central identity and tenancy management."""

    async def get_tenant(self, tenant_id: UUID) -> Optional[Tenant]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("tenants").select("*").eq("id", str(tenant_id)).execute()
        if not result.data:
            return None
        return Tenant(**result.data[0])

    async def get_user(self, user_id: UUID) -> Optional[UserAccount]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("user_accounts").select("*").eq("id", str(user_id)).execute()
        if not result.data:
            return None
        return UserAccount(**result.data[0])

    async def get_user_roles(
        self, user_id: UUID, tenant_id: UUID, matter_id: Optional[UUID] = None,
    ) -> List[RoleAssignment]:
        db = await get_db()
        if db is None:
            return []
        query = db.table("role_assignments").select("*").eq("user_id", str(user_id)).eq("tenant_id", str(tenant_id)).eq("is_active", True)
        if matter_id:
            query = query.eq("matter_id", str(matter_id))
        result = query.execute()
        if not result.data:
            return []
        return [RoleAssignment(**r) for r in result.data]

    async def has_role(
        self, user_id: UUID, tenant_id: UUID, role: ActorRole, matter_id: Optional[UUID] = None,
    ) -> bool:
        roles = await self.get_user_roles(user_id, tenant_id, matter_id)
        return any(r.role == role for r in roles)

    async def is_attorney(
        self, user_id: UUID, tenant_id: UUID, matter_id: Optional[UUID] = None,
    ) -> bool:
        attorney_roles = {
            ActorRole.RESPONSIBLE_ATTORNEY,
            ActorRole.SUPERVISING_ATTORNEY,
            ActorRole.MANAGING_ATTORNEY,
            ActorRole.LITIGATION_ATTORNEY,
        }
        roles = await self.get_user_roles(user_id, tenant_id, matter_id)
        return any(r.role in attorney_roles for r in roles)

    async def get_matter(self, matter_id: UUID) -> Optional[Matter]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("matters").select("*").eq("id", str(matter_id)).execute()
        if not result.data:
            return None
        return Matter(**result.data[0])

    async def get_responsible_attorney(self, matter_id: UUID) -> Optional[UUID]:
        matter = await self.get_matter(matter_id)
        if matter is None:
            return None
        return matter.responsible_attorney_id

    async def create_person(
        self, tenant_id: UUID, first_name: str, last_name: str, **kwargs,
    ) -> Optional[Person]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        person_id = uuid4()
        record = {
            "id": str(person_id),
            "tenant_id": str(tenant_id),
            "first_name": first_name,
            "last_name": last_name,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            **{k: v.isoformat() if isinstance(v, (datetime, date)) else v for k, v in kwargs.items()},
        }
        result = db.table("persons").insert(record).execute()
        if not result.data:
            return None
        return Person(**result.data[0])

    async def create_party_role(
        self, tenant_id: UUID, person_id: UUID, role: ActorRole, matter_id: Optional[UUID] = None,
    ) -> Optional[PartyRole]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        role_id = uuid4()
        record = {
            "id": str(role_id),
            "tenant_id": str(tenant_id),
            "person_id": str(person_id),
            "role": role.value,
            "matter_id": str(matter_id) if matter_id else None,
            "effective_from": now.isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("party_roles").insert(record).execute()
        if not result.data:
            return None
        return PartyRole(**result.data[0])

    async def get_contact_points(self, person_id: UUID) -> List[ContactPoint]:
        db = await get_db()
        if db is None:
            return []
        result = db.table("contact_points").select("*").eq("person_id", str(person_id)).execute()
        if not result.data:
            return []
        return [ContactPoint(**r) for r in result.data]

    async def validate_tenant_access(self, user_id: UUID, tenant_id: UUID) -> bool:
        user = await self.get_user(user_id)
        if user is None:
            return False
        return str(user.tenant_id) == str(tenant_id)


tenant_core = TenantCore()
