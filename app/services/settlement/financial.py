"""
Financial Services — SETTLE Domain

Handles ENT-099 Settlement Payment, ENT-102 Settlement Allocation,
ENT-103 Trust Ledger Entry, ENT-104 Closing Statement, ENT-105 Disbursement.

INV-013: Settlement allocations and disbursements must reconcile to
cleared funds and immutable ledger entries.

AUTH-018: Allocation approval requires ATTY-AUTH + CLIENT acknowledgment.
AUTH-019: Disbursement requires authorized firm user.
"""

import logging
from typing import Optional, List
from datetime import datetime, UTC, date as DateType
from uuid import UUID, uuid4

from app.core.database import get_db
from app.models.settlement import (
    SettlementPayment, SettlementPaymentCreate, PaymentReceiveRequest,
    SettlementAllocation, SettlementAllocationCreate, AllocationApproveRequest,
    TrustLedgerEntry, TrustLedgerEntryCreate,
    ClosingStatement, ClosingStatementCreate,
    Disbursement, DisbursementCreate, DisbursementAuthorize,
)
from app.services.settlement.authority_gate import (
    settlement_authority_gate,
    settlement_invariants,
    ALLOCATION_TRANSITIONS,
)
from app.services.settlement.audit import settlement_audit

logger = logging.getLogger(__name__)


class PaymentService:
    """Manages settlement payments and trust ledger entries."""

    async def create_settlement_payment(
        self,
        tenant_id: UUID,
        data: SettlementPaymentCreate,
        created_by: UUID,
        actor_role: str,
    ) -> Optional[SettlementPayment]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        payment_id = uuid4()
        record = {
            "id": str(payment_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(data.matter_id),
            "settlement_agreement_id": str(data.settlement_agreement_id),
            "payer": data.payer,
            "payer_contact_id": str(data.payer_contact_id) if data.payer_contact_id else None,
            "amount": data.amount,
            "payment_method": data.payment_method,
            "reference_number": data.reference_number,
            "status": "pending",
            "expected_date": data.expected_date.isoformat() if data.expected_date else None,
            "note": data.note,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_settlement_payments").insert(record).execute()
        if not result.data:
            return None
        return SettlementPayment(**result.data[0])

    async def get_payment(self, payment_id: UUID) -> Optional[SettlementPayment]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("settle_settlement_payments").select("*").eq("id", str(payment_id)).execute()
        if not result.data:
            return None
        return SettlementPayment(**result.data[0])

    async def get_payments_by_matter(self, matter_id: UUID) -> List[SettlementPayment]:
        db = await get_db()
        if db is None:
            return []
        result = db.table("settle_settlement_payments").select("*").eq("matter_id", str(matter_id)).order("created_at", desc=True).execute()
        if not result.data:
            return []
        return [SettlementPayment(**r) for r in result.data]

    async def receive_payment(
        self,
        tenant_id: UUID,
        matter_id: UUID,
        data: PaymentReceiveRequest,
        received_by: UUID,
        actor_role: str,
    ) -> Optional[SettlementPayment]:
        payment = await self.get_payment(data.payment_id)
        if payment is None:
            return None

        db = await get_db()
        now = datetime.now(UTC)
        update = {
            "status": "received",
            "received_date": data.received_date.isoformat() if isinstance(data.received_date, DateType) else data.received_date,
            "deposited_to_trust": data.deposited_to_trust,
            "reference_number": data.reference_number or payment.reference_number,
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_settlement_payments").update(update).eq("id", str(data.payment_id)).execute()
        if not result.data:
            return None

        if data.deposited_to_trust:
            await self._create_trust_deposit_entry(
                tenant_id=tenant_id,
                matter_id=matter_id,
                payment_id=data.payment_id,
                amount=payment.amount,
                posted_by=received_by,
            )

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=matter_id,
            event_type="settlement.funded",
            actor_id=received_by,
            actor_type=actor_role,
            entity_type="settlement_payment",
            entity_id=data.payment_id,
            details={"amount": payment.amount, "deposited_to_trust": data.deposited_to_trust},
        )
        return SettlementPayment(**result.data[0])

    async def _create_trust_deposit_entry(
        self,
        tenant_id: UUID,
        matter_id: UUID,
        payment_id: UUID,
        amount: float,
        posted_by: UUID,
    ) -> Optional[TrustLedgerEntry]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        existing = db.table("settle_trust_ledger").select("running_balance").eq("matter_id", str(matter_id)).order("created_at", desc=True).limit(1).execute()
        current_balance = existing.data[0]["running_balance"] if existing.data else 0
        new_balance = current_balance + amount

        entry_id = uuid4()
        record = {
            "id": str(entry_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(matter_id),
            "settlement_payment_id": str(payment_id),
            "entry_type": "deposit",
            "amount": amount,
            "running_balance": new_balance,
            "description": "Settlement payment deposited to trust",
            "posted_by": str(posted_by),
            "posted_at": now.isoformat(),
            "created_at": now.isoformat(),
        }
        result = db.table("settle_trust_ledger").insert(record).execute()
        if not result.data:
            return None

        await db.table("settle_settlement_payments").update({
            "trust_ledger_entry_id": str(entry_id),
            "cleared_date": now.date().isoformat(),
            "status": "cleared",
        }).eq("id", str(payment_id)).execute()

        return TrustLedgerEntry(**result.data[0])

    async def create_trust_ledger_entry(
        self,
        tenant_id: UUID,
        data: TrustLedgerEntryCreate,
        posted_by: UUID,
    ) -> Optional[TrustLedgerEntry]:
        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        existing = db.table("settle_trust_ledger").select("running_balance").eq("matter_id", str(data.matter_id)).order("created_at", desc=True).limit(1).execute()
        current_balance = existing.data[0]["running_balance"] if existing.data else 0

        if data.entry_type in ("deposit", "reversal"):
            new_balance = current_balance + data.amount
        else:
            new_balance = current_balance - data.amount

        entry_id = uuid4()
        record = {
            "id": str(entry_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(data.matter_id),
            "settlement_payment_id": str(data.settlement_payment_id) if data.settlement_payment_id else None,
            "disbursement_id": str(data.disbursement_id) if data.disbursement_id else None,
            "entry_type": data.entry_type,
            "amount": data.amount,
            "running_balance": new_balance,
            "description": data.description,
            "reference_number": data.reference_number,
            "posted_by": str(posted_by),
            "posted_at": now.isoformat(),
            "created_at": now.isoformat(),
        }
        result = db.table("settle_trust_ledger").insert(record).execute()
        if not result.data:
            return None
        return TrustLedgerEntry(**result.data[0])

    async def get_trust_ledger(self, matter_id: UUID) -> list:
        db = await get_db()
        if db is None:
            return []
        result = db.table("settle_trust_ledger").select("*").eq("matter_id", str(matter_id)).order("created_at", desc=False).execute()
        if not result.data:
            return []
        return result.data

    async def get_trust_balance(self, matter_id: UUID) -> float:
        ledger = await self.get_trust_ledger(matter_id)
        if not ledger:
            return 0.0
        return ledger[-1].get("running_balance", 0)


class AllocationService:
    """Manages settlement allocations, closing statements, and disbursements."""

    async def create_allocation(
        self,
        tenant_id: UUID,
        data: SettlementAllocationCreate,
        created_by: UUID,
        actor_role: str,
    ) -> Optional[SettlementAllocation]:
        total_deductions = data.attorney_fees + data.costs_advanced + data.lien_payments + data.other_deductions
        client_net = data.gross_proceeds - total_deductions

        invariant_check = await settlement_invariants.check_money_reconciliation(
            gross_proceeds=data.gross_proceeds,
            total_deductions=total_deductions,
            client_net=client_net,
        )
        if not invariant_check["valid"]:
            logger.warning(f"Allocation reconciliation failed: {invariant_check['reason']}")
            return None

        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        alloc_id = uuid4()
        record = {
            "id": str(alloc_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(data.matter_id),
            "settlement_agreement_id": str(data.settlement_agreement_id),
            "version": 1,
            "gross_proceeds": data.gross_proceeds,
            "attorney_fees": data.attorney_fees,
            "attorney_fee_pct": data.attorney_fee_pct,
            "costs_advanced": data.costs_advanced,
            "lien_payments": data.lien_payments,
            "other_deductions": data.other_deductions,
            "client_net": client_net,
            "reconciliation_status": "balanced",
            "status": "draft",
            "note": data.note,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_settlement_allocations").insert(record).execute()
        if not result.data:
            return None
        return SettlementAllocation(**result.data[0])

    async def get_allocation(self, alloc_id: UUID) -> Optional[SettlementAllocation]:
        db = await get_db()
        if db is None:
            return None
        result = db.table("settle_settlement_allocations").select("*").eq("id", str(alloc_id)).execute()
        if not result.data:
            return None
        return SettlementAllocation(**result.data[0])

    async def get_allocations_by_matter(self, matter_id: UUID) -> List[SettlementAllocation]:
        db = await get_db()
        if db is None:
            return []
        result = db.table("settle_settlement_allocations").select("*").eq("matter_id", str(matter_id)).order("version", desc=True).execute()
        if not result.data:
            return []
        return [SettlementAllocation(**r) for r in result.data]

    async def approve_allocation(
        self,
        tenant_id: UUID,
        matter_id: UUID,
        data: AllocationApproveRequest,
        actor_role: str,
    ) -> Optional[SettlementAllocation]:
        allocation = await self.get_allocation(data.allocation_id)
        if allocation is None:
            return None

        gate = await settlement_authority_gate.gate_action(
            action="allocation.approve",
            actor_role=actor_role,
            actor_id=data.attorney_id,
            matter_id=matter_id,
            tenant_id=tenant_id,
            current_state=allocation.status,
            target_state="approved",
            transition_map=ALLOCATION_TRANSITIONS,
        )
        if not gate["valid"]:
            logger.warning(f"Allocation approval denied: {gate['reason']}")
            return None

        invariant_check = await settlement_invariants.check_money_reconciliation(
            gross_proceeds=allocation.gross_proceeds,
            total_deductions=allocation.attorney_fees + allocation.costs_advanced + allocation.lien_payments + allocation.other_deductions,
            client_net=allocation.client_net,
        )
        if not invariant_check["valid"]:
            logger.warning(f"Allocation reconciliation failed at approval: {invariant_check['reason']}")
            return None

        db = await get_db()
        now = datetime.now(UTC)
        update = {
            "status": "approved",
            "approved_by_attorney": str(data.attorney_id),
            "approved_at": now.isoformat(),
            "client_acknowledged": data.client_acknowledged,
            "client_acknowledged_at": now.isoformat() if data.client_acknowledged else None,
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_settlement_allocations").update(update).eq("id", str(data.allocation_id)).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=matter_id,
            event_type="allocation.approved",
            actor_id=data.attorney_id,
            actor_type=actor_role,
            entity_type="settlement_allocation",
            entity_id=data.allocation_id,
            details={
                "gross_proceeds": allocation.gross_proceeds,
                "client_net": allocation.client_net,
                "client_acknowledged": data.client_acknowledged,
            },
        )
        return SettlementAllocation(**result.data[0])

    async def create_closing_statement(
        self,
        tenant_id: UUID,
        data: ClosingStatementCreate,
        created_by: UUID,
        actor_role: str,
    ) -> Optional[ClosingStatement]:
        allocation = await self.get_allocation(data.allocation_id)
        if allocation is None:
            return None
        if allocation.status != "approved":
            logger.warning(f"Allocation must be approved to generate closing statement. Current: {allocation.status}")
            return None

        total_deductions = allocation.attorney_fees + allocation.costs_advanced + allocation.lien_payments + allocation.other_deductions
        line_items = [
            {"description": "Gross Settlement", "amount": allocation.gross_proceeds, "type": "credit"},
            {"description": "Attorney Fees", "amount": allocation.attorney_fees, "type": "debit"},
            {"description": "Costs Advanced", "amount": allocation.costs_advanced, "type": "debit"},
            {"description": "Lien Payments", "amount": allocation.lien_payments, "type": "debit"},
            {"description": "Other Deductions", "amount": allocation.other_deductions, "type": "debit"},
            {"description": "Net to Client", "amount": allocation.client_net, "type": "net"},
        ]

        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        stmt_id = uuid4()
        record = {
            "id": str(stmt_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(data.matter_id),
            "settlement_agreement_id": str(data.settlement_agreement_id),
            "allocation_id": str(data.allocation_id),
            "version": 1,
            "gross_recovery": allocation.gross_proceeds,
            "total_deductions": total_deductions,
            "net_to_client": allocation.client_net,
            "line_items": line_items,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_closing_statements").insert(record).execute()
        if not result.data:
            return None
        return ClosingStatement(**result.data[0])

    async def approve_closing_statement(
        self,
        statement_id: UUID,
        attorney_id: UUID,
        tenant_id: UUID,
        matter_id: UUID,
        actor_role: str,
    ) -> Optional[ClosingStatement]:
        gate = await settlement_authority_gate.gate_action(
            action="closing_statement.approve",
            actor_role=actor_role,
            actor_id=attorney_id,
            matter_id=matter_id,
            tenant_id=tenant_id,
        )
        if not gate["valid"]:
            return None

        db = await get_db()
        now = datetime.now(UTC)
        update = {
            "approved_by_attorney": str(attorney_id),
            "approved_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_closing_statements").update(update).eq("id", str(statement_id)).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=matter_id,
            event_type="closing_statement.approved",
            actor_id=attorney_id,
            actor_type=actor_role,
            entity_type="closing_statement",
            entity_id=statement_id,
        )
        return ClosingStatement(**result.data[0])

    async def create_disbursement(
        self,
        tenant_id: UUID,
        data: DisbursementCreate,
        created_by: UUID,
        actor_role: str,
    ) -> Optional[Disbursement]:
        allocation = await self.get_allocation(data.allocation_id)
        if allocation is None:
            return None
        if allocation.status != "approved":
            logger.warning(f"Allocation must be approved for disbursements. Current: {allocation.status}")
            return None

        trust_balance = await PaymentService().get_trust_balance(data.matter_id)
        if data.amount > trust_balance:
            logger.warning(f"Insufficient trust balance: needed={data.amount}, available={trust_balance}")
            return None

        db = await get_db()
        if db is None:
            return None
        now = datetime.now(UTC)
        disbursement_id = uuid4()
        record = {
            "id": str(disbursement_id),
            "tenant_id": str(tenant_id),
            "matter_id": str(data.matter_id),
            "allocation_id": str(data.allocation_id),
            "payee": data.payee,
            "payee_type": data.payee_type,
            "amount": data.amount,
            "status": "pending",
            "payment_method": data.payment_method,
            "reference_number": data.reference_number,
            "note": data.note,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_disbursements").insert(record).execute()
        if not result.data:
            return None
        return Disbursement(**result.data[0])

    async def authorize_disbursement(
        self,
        tenant_id: UUID,
        matter_id: UUID,
        data: DisbursementAuthorize,
        actor_role: str,
    ) -> Optional[Disbursement]:
        gate = await settlement_authority_gate.gate_action(
            action="disbursement.authorize",
            actor_role=actor_role,
            actor_id=data.authorized_by,
            matter_id=matter_id,
            tenant_id=tenant_id,
        )
        if not gate["valid"]:
            logger.warning(f"Disbursement authorization denied: {gate['reason']}")
            return None

        db = await get_db()
        now = datetime.now(UTC)
        disbursement = db.table("settle_disbursements").select("*").eq("id", str(data.disbursement_id)).execute()
        if not disbursement.data:
            return None
        current = disbursement.data[0]

        if current["status"] != "pending":
            logger.warning(f"Cannot authorize disbursement in status '{current['status']}'")
            return None

        trust_balance = await PaymentService().get_trust_balance(matter_id)
        if current["amount"] > trust_balance:
            logger.warning("Insufficient trust funds for disbursement")
            return None

        update = {
            "status": "authorized",
            "authorized_by": str(data.authorized_by),
            "authorized_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_disbursements").update(update).eq("id", str(data.disbursement_id)).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=matter_id,
            event_type="disbursement.authorized",
            actor_id=data.authorized_by,
            actor_type=actor_role,
            entity_type="disbursement",
            entity_id=data.disbursement_id,
            details={"amount": current["amount"], "payee": current["payee"]},
        )
        return Disbursement(**result.data[0])

    async def complete_disbursement(
        self,
        disbursement_id: UUID,
        completed_by: UUID,
        tenant_id: UUID,
        matter_id: UUID,
    ) -> Optional[Disbursement]:
        db = await get_db()
        now = datetime.now(UTC)
        disbursement = db.table("settle_disbursements").select("*").eq("id", str(disbursement_id)).execute()
        if not disbursement.data:
            return None
        current = disbursement.data[0]

        if current["status"] != "authorized":
            logger.warning(f"Cannot complete disbursement in status '{current['status']}'")
            return None

        update = {
            "status": "completed",
            "completed_by": str(completed_by),
            "completed_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        result = db.table("settle_disbursements").update(update).eq("id", str(disbursement_id)).execute()
        if not result.data:
            return None

        await settlement_audit.record(
            tenant_id=tenant_id,
            matter_id=matter_id,
            event_type="disbursement.completed",
            actor_id=completed_by,
            actor_type="trust_accounting",
            entity_type="disbursement",
            entity_id=disbursement_id,
            details={"amount": current["amount"], "payee": current["payee"]},
        )
        return Disbursement(**result.data[0])

    async def get_disbursements_by_matter(self, matter_id: UUID) -> List[Disbursement]:
        db = await get_db()
        if db is None:
            return []
        result = db.table("settle_disbursements").select("*").eq("matter_id", str(matter_id)).order("created_at", desc=True).execute()
        if not result.data:
            return []
        return [Disbursement(**r) for r in result.data]


payment_service = PaymentService()
allocation_service = AllocationService()
