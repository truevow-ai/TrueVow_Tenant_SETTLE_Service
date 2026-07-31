"""
Settlement Authority Gate Service

Enforces the Decision Authority Registry (AUTH-014 through AUTH-020) and
non-negotiable invariants for the SETTLE domain.

Every material action must pass:
  1. Authority classification check
  2. State transition validation
  3. Invariant validation
  4. Audit event emission

Failure mode: fail-closed (TV-CMP-002).
"""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
from enum import Enum

logger = logging.getLogger(__name__)


class AuthorityClass(str, Enum):
    SYS_ADMIN = "SYS-ADMIN"
    FIRM_POLICY = "FIRM-POLICY"
    STAFF_AUTH = "STAFF-AUTH"
    ATTY_AUTH = "ATTY-AUTH"
    CLIENT_AUTH = "CLIENT-AUTH"
    PROHIBITED = "PROHIBITED"


# ============================================================================
# SETTLE DOMAIN AUTHORITY REGISTRY
# ============================================================================

SETTLE_AUTHORITY_MAP = {
    # Demand
    "demand.draft.create": AuthorityClass.FIRM_POLICY,
    "demand.draft.review": AuthorityClass.ATTY_AUTH,
    "demand.authorize": AuthorityClass.ATTY_AUTH,
    "demand.transmit": AuthorityClass.FIRM_POLICY,

    # Offers
    "offer.record": AuthorityClass.FIRM_POLICY,
    "offer.notify_client": AuthorityClass.SYS_ADMIN,
    "counteroffer.create": AuthorityClass.FIRM_POLICY,
    "counteroffer.authorize": AuthorityClass.CLIENT_AUTH,

    # Settlement decisions (CRITICAL BOUNDARY)
    "settlement.accept": AuthorityClass.CLIENT_AUTH,
    "settlement.reject": AuthorityClass.CLIENT_AUTH,
    "settlement.counter": AuthorityClass.CLIENT_AUTH,
    "attorney.recommendation": AuthorityClass.ATTY_AUTH,

    # Agreements & Releases
    "agreement.create": AuthorityClass.FIRM_POLICY,
    "agreement.approve": AuthorityClass.ATTY_AUTH,
    "agreement.sign_client": AuthorityClass.CLIENT_AUTH,
    "agreement.sign_firm": AuthorityClass.ATTY_AUTH,
    "release.review": AuthorityClass.ATTY_AUTH,
    "release.sign_client": AuthorityClass.CLIENT_AUTH,

    # Payments & Financial
    "payment.record": AuthorityClass.FIRM_POLICY,
    "payment.receive": AuthorityClass.FIRM_POLICY,
    "allocation.create": AuthorityClass.FIRM_POLICY,
    "allocation.approve": AuthorityClass.ATTY_AUTH,
    "closing_statement.create": AuthorityClass.FIRM_POLICY,
    "closing_statement.approve": AuthorityClass.ATTY_AUTH,
    "disbursement.create": AuthorityClass.FIRM_POLICY,
    "disbursement.authorize": AuthorityClass.STAFF_AUTH,

    # Liens
    "lien.create": AuthorityClass.FIRM_POLICY,
    "lien.verify": AuthorityClass.FIRM_POLICY,
    "lien.resolve": AuthorityClass.ATTY_AUTH,

    # Closure
    "matter.close": AuthorityClass.ATTY_AUTH,
    "matter.reopen": AuthorityClass.ATTY_AUTH,
}


# ============================================================================
# VALID STATE TRANSITIONS
# ============================================================================

DEMAND_PACKAGE_TRANSITIONS = {
    "assembling": ["drafting"],
    "drafting": ["attorney_review"],
    "attorney_review": ["revision_required", "authorized"],
    "revision_required": ["attorney_review"],
    "authorized": ["sent", "withdrawn"],
    "sent": ["superseded"],
    "superseded": [],
    "withdrawn": [],
}

OFFER_TRANSITIONS = {
    "offer_received": ["client_notice_pending", "under_review", "expired"],
    "client_notice_pending": ["under_review", "expired"],
    "under_review": ["counter_authorized", "accepted", "rejected", "expired"],
    "counter_authorized": ["under_review", "expired"],
    "accepted": ["documentation_pending"],
    "rejected": [],
    "expired": [],
    "documentation_pending": ["fully_documented"],
    "fully_documented": ["payment_pending"],
    "payment_pending": ["funded"],
    "funded": [],
}

LIEN_TRANSITIONS = {
    "asserted": ["documents_requested", "under_review"],
    "documents_requested": ["under_review"],
    "under_review": ["verified", "disputed"],
    "verified": ["negotiating", "resolved"],
    "disputed": ["negotiating", "resolved"],
    "negotiating": ["resolved"],
    "resolved": ["paid"],
    "paid": [],
}

ALLOCATION_TRANSITIONS = {
    "draft": ["approved", "applied"],
    "approved": ["applied"],
    "applied": [],
}

DISBURSEMENT_TRANSITIONS = {
    "pending": ["authorized", "failed"],
    "authorized": ["completed", "failed"],
    "completed": ["reversed"],
    "failed": ["pending"],
    "reversed": [],
}


class SettlementAuthorityGate:
    """Enforces authority rules and invariants for all SETTLE domain actions."""

    @staticmethod
    def get_required_authority(action: str) -> AuthorityClass:
        """Get the authority class required for a given action."""
        authority = SETTLE_AUTHORITY_MAP.get(action)
        if authority is None:
            logger.warning(f"No authority mapping found for action: {action}. Defaulting to ATTY_AUTH (fail-safe).")
            return AuthorityClass.ATTY_AUTH
        return authority

    @staticmethod
    def is_client_auth_required(action: str) -> bool:
        """Check if an action requires client authority (INV-005 boundary)."""
        return SETTLE_AUTHORITY_MAP.get(action) == AuthorityClass.CLIENT_AUTH

    @staticmethod
    def is_platform_prohibited(action: str) -> bool:
        """Check if an action is prohibited for the platform."""
        return SETTLE_AUTHORITY_MAP.get(action) == AuthorityClass.PROHIBITED

    @staticmethod
    def validate_authority(
        action: str,
        actor_role: str,
        actor_id: UUID,
        matter_id: UUID,
        tenant_id: UUID,
    ) -> Dict[str, Any]:
        """
        Validate that the actor has the required authority for the action.

        Returns:
            Dict with validation result: {valid: bool, required: str, reason: str, ...}
        """
        required = SettlementAuthorityGate.get_required_authority(action)

        if required == AuthorityClass.PROHIBITED:
            return {
                "valid": False,
                "required": required.value,
                "reason": f"Action '{action}' is prohibited for platform execution.",
                "actor_id": str(actor_id),
                "matter_id": str(matter_id),
            }

        role_authority_map = {
            "attorney": [AuthorityClass.ATTY_AUTH, AuthorityClass.STAFF_AUTH, AuthorityClass.FIRM_POLICY, AuthorityClass.SYS_ADMIN],
            "managing_attorney": [AuthorityClass.ATTY_AUTH, AuthorityClass.STAFF_AUTH, AuthorityClass.FIRM_POLICY, AuthorityClass.SYS_ADMIN],
            "paralegal": [AuthorityClass.STAFF_AUTH, AuthorityClass.FIRM_POLICY, AuthorityClass.SYS_ADMIN],
            "case_manager": [AuthorityClass.STAFF_AUTH, AuthorityClass.FIRM_POLICY, AuthorityClass.SYS_ADMIN],
            "legal_assistant": [AuthorityClass.STAFF_AUTH, AuthorityClass.FIRM_POLICY, AuthorityClass.SYS_ADMIN],
            "intake_coordinator": [AuthorityClass.FIRM_POLICY, AuthorityClass.SYS_ADMIN],
            "firm_administrator": [AuthorityClass.FIRM_POLICY, AuthorityClass.SYS_ADMIN],
            "trust_accounting": [AuthorityClass.STAFF_AUTH, AuthorityClass.FIRM_POLICY, AuthorityClass.SYS_ADMIN],
            "client": [AuthorityClass.CLIENT_AUTH],
            "platform": [AuthorityClass.SYS_ADMIN, AuthorityClass.FIRM_POLICY],
        }

        allowed = role_authority_map.get(actor_role, [])
        if required not in allowed:
            return {
                "valid": False,
                "required": required.value,
                "actor_role": actor_role,
                "reason": f"Actor with role '{actor_role}' does not have required authority '{required.value}' for action '{action}'.",
                "actor_id": str(actor_id),
                "matter_id": str(matter_id),
            }

        return {
            "valid": True,
            "required": required.value,
            "actor_role": actor_role,
            "actor_id": str(actor_id),
            "matter_id": str(matter_id),
        }

    @staticmethod
    def validate_state_transition(
        current_state: str,
        target_state: str,
        transition_map: Dict[str, List[str]],
    ) -> Dict[str, Any]:
        """Validate that a state transition is allowed."""
        allowed_transitions = transition_map.get(current_state, [])
        if target_state not in allowed_transitions:
            return {
                "valid": False,
                "current_state": current_state,
                "target_state": target_state,
                "allowed": allowed_transitions,
                "reason": f"Transition from '{current_state}' to '{target_state}' is not allowed.",
            }
        return {
            "valid": True,
            "current_state": current_state,
            "target_state": target_state,
        }

    @staticmethod
    async def gate_action(
        action: str,
        actor_role: str,
        actor_id: UUID,
        matter_id: UUID,
        tenant_id: UUID,
        current_state: Optional[str] = None,
        target_state: Optional[str] = None,
        transition_map: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        """
        Universal gate: validate authority + state transition before executing.

        Must pass all checks. Failure is fail-closed.
        """
        authority_result = SettlementAuthorityGate.validate_authority(
            action=action,
            actor_role=actor_role,
            actor_id=actor_id,
            matter_id=matter_id,
            tenant_id=tenant_id,
        )
        if not authority_result["valid"]:
            return authority_result

        if current_state is not None and target_state is not None and transition_map is not None:
            state_result = SettlementAuthorityGate.validate_state_transition(
                current_state=current_state,
                target_state=target_state,
                transition_map=transition_map,
            )
            if not state_result["valid"]:
                return {**authority_result, **state_result, "valid": False}

        return authority_result


# ============================================================================
# INVARIANT CHECKS
# ============================================================================

class SettlementInvariants:
    """Checks non-negotiable invariants for the SETTLE domain."""

    @staticmethod
    async def check_client_settlement_authority(
        settlement_decision_id: UUID,
        decided_by: UUID,
    ) -> Dict[str, Any]:
        """
        INV-005: No settlement acceptance occurs without an attributable
        client or valid representative decision.
        """
        if decided_by is None:
            return {
                "valid": False,
                "invariant": "INV-005",
                "reason": "Settlement decision must have an identified decider (client or authorized representative).",
            }
        return {"valid": True, "invariant": "INV-005"}

    @staticmethod
    async def check_immutable_document_version(
        document_hash: Optional[str],
        state: str,
    ) -> Dict[str, Any]:
        """
        INV-006: Every sent, filed, or executed document references an
        immutable Document Version and hash.
        """
        immutable_states = {"sent", "authorized", "executed", "filed_or_sent", "fully_executed"}
        if state in immutable_states and not document_hash:
            return {
                "valid": False,
                "invariant": "INV-006",
                "reason": f"Document in state '{state}' must have an immutable document hash.",
            }
        return {"valid": True, "invariant": "INV-006"}

    @staticmethod
    async def check_money_reconciliation(
        gross_proceeds: float,
        total_deductions: float,
        client_net: float,
    ) -> Dict[str, Any]:
        """
        INV-013: Settlement allocations and disbursements must reconcile
        to cleared funds and immutable ledger entries.
        """
        expected_net = gross_proceeds - total_deductions
        if abs(expected_net - client_net) > 0.01:
            return {
                "valid": False,
                "invariant": "INV-013",
                "reason": f"Reconciliation failed: gross={gross_proceeds}, deductions={total_deductions}, expected_net={expected_net}, actual_net={client_net}",
            }
        return {"valid": True, "invariant": "INV-013"}

    @staticmethod
    async def check_no_self_approval(
        actor_id: UUID,
        approving_action: str,
    ) -> Dict[str, Any]:
        """
        INV-011: A service or AI component cannot create the authority
        record needed to approve its own proposed action.
        """
        ai_actor_ids = {UUID("00000000-0000-0000-0000-000000000000")}
        if actor_id in ai_actor_ids:
            return {
                "valid": False,
                "invariant": "INV-011",
                "reason": f"AI or platform actor cannot authorize '{approving_action}'.",
            }
        return {"valid": True, "invariant": "INV-011"}


settlement_authority_gate = SettlementAuthorityGate()
settlement_invariants = SettlementInvariants()
