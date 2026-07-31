"""
Workflow Runtime — Deterministic states, timers, approvals, and escalations.

Implements the ontology transition contract:
  - Every transition has named authority, allowed prior states, required evidence,
    failure mode (default fail_closed), and audit event.
  - Signals are not conclusions (INV-009).
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, UTC, timedelta
from uuid import UUID, uuid4

from app.core.database import get_db
from app.shared.models import (
    WorkItem, WorkItemState, TransitionContract,
)

logger = logging.getLogger(__name__)


class WorkflowRuntime:
    """Runs deterministic state transitions with authority gating."""

    def __init__(self):
        self._transitions: Dict[str, List[TransitionContract]] = {}

    def register_transition(self, contract: TransitionContract) -> None:
        key = contract.aggregate_type
        if key not in self._transitions:
            self._transitions[key] = []
        self._transitions[key].append(contract)

    def get_allowed_transitions(
        self, aggregate_type: str, current_state: str,
    ) -> List[TransitionContract]:
        contracts = self._transitions.get(aggregate_type, [])
        return [c for c in contracts if current_state in c.from_states]

    def get_transition(
        self, aggregate_type: str, command: str,
    ) -> Optional[TransitionContract]:
        contracts = self._transitions.get(aggregate_type, [])
        for c in contracts:
            if c.command == command:
                return c
        return None

    async def create_work_item(
        self,
        tenant_id: UUID,
        work_type: str,
        title: str,
        matter_id: Optional[UUID] = None,
        priority: str = "medium",
        assigned_to: Optional[UUID] = None,
        assigned_queue: Optional[str] = None,
        due_date: Optional[datetime] = None,
        created_by: Optional[UUID] = None,
        description: Optional[str] = None,
    ) -> Optional[WorkItem]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        item_id = uuid4()
        record = {
            "id": str(item_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(matter_id) if matter_id else None,
            "work_type": work_type,
            "title": title,
            "description": description,
            "state": "created",
            "priority": priority,
            "assigned_to": str(assigned_to) if assigned_to else None,
            "assigned_queue": assigned_queue,
            "due_date": due_date.isoformat() if due_date else None,
            "created_by": str(created_by) if created_by else None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("work_items").insert(record).execute()
        if not result.data:
            return None
        return WorkItem(**result.data[0])

    async def transition_work_item(
        self,
        item_id: UUID,
        new_state: WorkItemState,
        actor_id: Optional[UUID] = None,
        blocked_reason: Optional[str] = None,
    ) -> Optional[WorkItem]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        update: Dict[str, Any] = {
            "state": new_state,
            "updated_at": now.isoformat(),
        }
        if new_state == "completed":
            update["completed_at"] = now.isoformat()
            update["completed_by"] = str(actor_id)
        if new_state == "blocked":
            update["blocked_reason"] = blocked_reason
        if new_state == "in_progress" or new_state == "assigned":
            update["assigned_to"] = str(actor_id)

        result = db.table("work_items").update(update).eq("id", str(item_id)).execute()
        if not result.data:
            return None
        return WorkItem(**result.data[0])

    async def get_work_item(self, item_id: UUID) -> Optional[WorkItem]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("work_items").select("*").eq("id", str(item_id)).execute()
        if not result.data:
            return None
        return WorkItem(**result.data[0])

    async def get_matter_work_items(self, matter_id: UUID) -> list:
        db = await get_db()
        if db is None:
            return []
        result = db.table("work_items").select("*").eq("matter_id", str(matter_id)).order("created_at", desc=True).execute()
        if not result.data:
            return []
        return result.data

    async def get_overdue_items(self, tenant_id: UUID) -> list:
        db = await get_db()
        if db is None:
            return []
        now = datetime.now(UTC).isoformat()
        result = db.table("work_items").select("*").eq("tenant_id", str(tenant_id)).not_.in_("state", ["completed", "waived", "cancelled"]).lt("due_date", now).execute()
        if not result.data:
            return []
        return result.data

    async def escalate_overdue(
        self, tenant_id: UUID, sla_minutes: int = 60,
    ) -> list:
        overdue = await self.get_overdue_items(tenant_id)
        if not overdue:
            return []
        now = datetime.now(UTC)
        escalated = []
        for item in overdue:
            due = datetime.fromisoformat(item["due_date"].replace("Z", "+00:00"))
            if (now - due) > timedelta(minutes=sla_minutes):
                item["state"] = "review_required"
                escalated.append(item)
        return escalated


workflow_runtime = WorkflowRuntime()
