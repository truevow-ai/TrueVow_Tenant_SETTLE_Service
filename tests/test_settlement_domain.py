"""
Settlement Domain Tests — SETTLE Resolution Workflow

Tests the settlement workflow model validation, authority gate,
state transitions, and invariants.
"""

import pytest
from datetime import datetime, UTC, date
from uuid import UUID, uuid4
from pydantic import ValidationError


# ============================================================================
# MODEL VALIDATION TESTS
# ============================================================================

class TestSettlementDecisionCreate:
    """Test ENT-096 SettlementDecisionCreate validation."""

    def test_accept_decision_valid(self):
        from app.models.settlement import SettlementDecisionCreate
        decision = SettlementDecisionCreate(
            matter_id=uuid4(),
            offer_id=uuid4(),
            decision="accept",
            decided_by=uuid4(),
            informed_consent_confirmed=True,
            attorney_advised_at=datetime.now(UTC),
        )
        assert decision.decision == "accept"
        assert decision.informed_consent_confirmed is True

    def test_counter_decision_requires_amount(self):
        from app.models.settlement import SettlementDecisionCreate
        with pytest.raises(ValidationError, match="Counteroffer amount is required"):
            SettlementDecisionCreate(
                matter_id=uuid4(),
                offer_id=uuid4(),
                decision="counter",
                decided_by=uuid4(),
                counter_amount=None,
            )

    def test_counter_decision_with_amount_valid(self):
        from app.models.settlement import SettlementDecisionCreate
        decision = SettlementDecisionCreate(
            matter_id=uuid4(),
            offer_id=uuid4(),
            decision="counter",
            decided_by=uuid4(),
            counter_amount=50000.0,
        )
        assert decision.decision == "counter"
        assert decision.counter_amount == 50000.0

    def test_reject_decision_valid(self):
        from app.models.settlement import SettlementDecisionCreate
        decision = SettlementDecisionCreate(
            matter_id=uuid4(),
            offer_id=uuid4(),
            decision="reject",
            decided_by=uuid4(),
            rationale="Amount too low",
        )
        assert decision.decision == "reject"

    def test_requires_decided_by(self):
        from app.models.settlement import SettlementDecisionCreate
        with pytest.raises(ValidationError):
            SettlementDecisionCreate(
                matter_id=uuid4(),
                offer_id=uuid4(),
                decision="accept",
                decided_by=None,
            )


class TestOfferCreate:
    """Test ENT-094 OfferCreate validation."""

    def test_valid_offer(self):
        from app.models.settlement import OfferCreate
        offer = OfferCreate(
            matter_id=uuid4(),
            negotiation_round_id=uuid4(),
            source="insurer",
            amount=250000.0,
            terms_summary="Full and final settlement",
        )
        assert offer.amount == 250000.0
        assert offer.source == "insurer"

    def test_negative_amount_rejected(self):
        from app.models.settlement import OfferCreate
        with pytest.raises(ValidationError):
            OfferCreate(
                matter_id=uuid4(),
                negotiation_round_id=uuid4(),
                source="insurer",
                amount=-1000.0,
            )


class TestAllocationCreate:
    """Test ENT-102 SettlementAllocationCreate validation."""

    def test_valid_allocation(self):
        from app.models.settlement import SettlementAllocationCreate
        alloc = SettlementAllocationCreate(
            matter_id=uuid4(),
            settlement_agreement_id=uuid4(),
            gross_proceeds=100000.0,
            attorney_fees=33333.0,
            costs_advanced=5000.0,
            lien_payments=10000.0,
        )
        assert alloc.gross_proceeds == 100000.0
        assert alloc.attorney_fees == 33333.0


class TestDemandAuthorization:
    """Test demand authorization request validation."""

    def test_valid_authorization(self):
        from app.models.settlement import DemandAuthorizationRequest
        auth = DemandAuthorizationRequest(
            package_id=uuid4(),
            document_hash="abc123def456",
            authorized_by=uuid4(),
        )
        assert auth.document_hash == "abc123def456"

    def test_empty_hash_rejected(self):
        from app.models.settlement import DemandAuthorizationRequest
        with pytest.raises(ValidationError):
            DemandAuthorizationRequest(
                package_id=uuid4(),
                document_hash="",
                authorized_by=uuid4(),
            )


class TestLienCreate:
    """Test ENT-100 LienCreate validation."""

    def test_valid_lien(self):
        from app.models.settlement import LienCreate
        lien = LienCreate(
            matter_id=uuid4(),
            claimant="Medicare",
            claimant_type="medicare",
            asserted_amount=25000.0,
        )
        assert lien.claimant == "Medicare"
        assert lien.claimant_type == "medicare"

    def test_invalid_claimant_type_rejected(self):
        from app.models.settlement import LienCreate
        with pytest.raises(ValidationError):
            LienCreate(
                matter_id=uuid4(),
                claimant="Unknown",
                claimant_type="invalid_type",
            )


# ============================================================================
# AUTHORITY GATE TESTS
# ============================================================================

class TestSettlementAuthorityGate:
    """Test authority classification for SETTLE domain actions."""

    def test_settlement_accept_requires_client_auth(self):
        from app.services.settlement.authority_gate import (
            settlement_authority_gate,
            AuthorityClass,
        )
        authority = settlement_authority_gate.get_required_authority("settlement.accept")
        assert authority == AuthorityClass.CLIENT_AUTH

    def test_settlement_reject_requires_client_auth(self):
        from app.services.settlement.authority_gate import (
            settlement_authority_gate,
            AuthorityClass,
        )
        authority = settlement_authority_gate.get_required_authority("settlement.reject")
        assert authority == AuthorityClass.CLIENT_AUTH

    def test_demand_authorize_requires_attorney_auth(self):
        from app.services.settlement.authority_gate import (
            settlement_authority_gate,
            AuthorityClass,
        )
        authority = settlement_authority_gate.get_required_authority("demand.authorize")
        assert authority == AuthorityClass.ATTY_AUTH

    def test_attorney_recommendation_requires_attorney_auth(self):
        from app.services.settlement.authority_gate import (
            settlement_authority_gate,
            AuthorityClass,
        )
        authority = settlement_authority_gate.get_required_authority("attorney.recommendation")
        assert authority == AuthorityClass.ATTY_AUTH

    def test_client_can_accept_settlement(self):
        from app.services.settlement.authority_gate import settlement_authority_gate
        result = settlement_authority_gate.validate_authority(
            action="settlement.accept",
            actor_role="client",
            actor_id=uuid4(),
            matter_id=uuid4(),
            tenant_id=uuid4(),
        )
        assert result["valid"] is True

    def test_paralegal_cannot_accept_settlement(self):
        from app.services.settlement.authority_gate import settlement_authority_gate
        result = settlement_authority_gate.validate_authority(
            action="settlement.accept",
            actor_role="paralegal",
            actor_id=uuid4(),
            matter_id=uuid4(),
            tenant_id=uuid4(),
        )
        assert result["valid"] is False

    def test_attorney_can_authorize_demand(self):
        from app.services.settlement.authority_gate import settlement_authority_gate
        result = settlement_authority_gate.validate_authority(
            action="demand.authorize",
            actor_role="attorney",
            actor_id=uuid4(),
            matter_id=uuid4(),
            tenant_id=uuid4(),
        )
        assert result["valid"] is True

    def test_client_cannot_authorize_demand(self):
        from app.services.settlement.authority_gate import settlement_authority_gate
        result = settlement_authority_gate.validate_authority(
            action="demand.authorize",
            actor_role="client",
            actor_id=uuid4(),
            matter_id=uuid4(),
            tenant_id=uuid4(),
        )
        assert result["valid"] is False

    def test_is_client_auth_required(self):
        from app.services.settlement.authority_gate import settlement_authority_gate
        assert settlement_authority_gate.is_client_auth_required("settlement.accept") is True
        assert settlement_authority_gate.is_client_auth_required("settlement.reject") is True
        assert settlement_authority_gate.is_client_auth_required("settlement.counter") is True
        assert settlement_authority_gate.is_client_auth_required("demand.authorize") is False


class TestStateTransitions:
    """Test state machine transitions for SETTLE domain entities."""

    def test_demand_package_valid_transition(self):
        from app.services.settlement.authority_gate import (
            settlement_authority_gate,
            DEMAND_PACKAGE_TRANSITIONS,
        )
        result = settlement_authority_gate.validate_state_transition(
            current_state="drafting",
            target_state="attorney_review",
            transition_map=DEMAND_PACKAGE_TRANSITIONS,
        )
        assert result["valid"] is True

    def test_demand_package_invalid_transition(self):
        from app.services.settlement.authority_gate import (
            settlement_authority_gate,
            DEMAND_PACKAGE_TRANSITIONS,
        )
        result = settlement_authority_gate.validate_state_transition(
            current_state="assembling",
            target_state="authorized",
            transition_map=DEMAND_PACKAGE_TRANSITIONS,
        )
        assert result["valid"] is False

    def test_offer_valid_transition(self):
        from app.services.settlement.authority_gate import (
            settlement_authority_gate,
            OFFER_TRANSITIONS,
        )
        result = settlement_authority_gate.validate_state_transition(
            current_state="offer_received",
            target_state="under_review",
            transition_map=OFFER_TRANSITIONS,
        )
        assert result["valid"] is True

    def test_offer_invalid_transition(self):
        from app.services.settlement.authority_gate import (
            settlement_authority_gate,
            OFFER_TRANSITIONS,
        )
        result = settlement_authority_gate.validate_state_transition(
            current_state="accepted",
            target_state="offer_received",
            transition_map=OFFER_TRANSITIONS,
        )
        assert result["valid"] is False

    def test_lien_valid_transition(self):
        from app.services.settlement.authority_gate import (
            settlement_authority_gate,
            LIEN_TRANSITIONS,
        )
        result = settlement_authority_gate.validate_state_transition(
            current_state="asserted",
            target_state="under_review",
            transition_map=LIEN_TRANSITIONS,
        )
        assert result["valid"] is True

    def test_disbursement_valid_transition(self):
        from app.services.settlement.authority_gate import (
            settlement_authority_gate,
            DISBURSEMENT_TRANSITIONS,
        )
        result = settlement_authority_gate.validate_state_transition(
            current_state="pending",
            target_state="authorized",
            transition_map=DISBURSEMENT_TRANSITIONS,
        )
        assert result["valid"] is True


# ============================================================================
# INVARIANT TESTS
# ============================================================================

class TestSettlementInvariants:
    """Test non-negotiable invariants for SETTLE domain."""

    @pytest.mark.asyncio
    async def test_client_settlement_authority_invariant(self):
        from app.services.settlement.authority_gate import settlement_invariants
        result = await settlement_invariants.check_client_settlement_authority(
            settlement_decision_id=uuid4(),
            decided_by=uuid4(),
        )
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_client_settlement_authority_no_decider(self):
        from app.services.settlement.authority_gate import settlement_invariants
        result = await settlement_invariants.check_client_settlement_authority(
            settlement_decision_id=uuid4(),
            decided_by=None,
        )
        assert result["valid"] is False
        assert result["invariant"] == "INV-005"

    @pytest.mark.asyncio
    async def test_money_reconciliation_valid(self):
        from app.services.settlement.authority_gate import settlement_invariants
        result = await settlement_invariants.check_money_reconciliation(
            gross_proceeds=100000.0,
            total_deductions=40000.0,
            client_net=60000.0,
        )
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_money_reconciliation_fails(self):
        from app.services.settlement.authority_gate import settlement_invariants
        result = await settlement_invariants.check_money_reconciliation(
            gross_proceeds=100000.0,
            total_deductions=40000.0,
            client_net=50000.0,
        )
        assert result["valid"] is False
        assert result["invariant"] == "INV-013"

    @pytest.mark.asyncio
    async def test_immutable_document_version(self):
        from app.services.settlement.authority_gate import settlement_invariants
        result = await settlement_invariants.check_immutable_document_version(
            document_hash="abc123",
            state="authorized",
        )
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_immutable_document_missing_hash(self):
        from app.services.settlement.authority_gate import settlement_invariants
        result = await settlement_invariants.check_immutable_document_version(
            document_hash=None,
            state="authorized",
        )
        assert result["valid"] is False
        assert result["invariant"] == "INV-006"


# ============================================================================
# AUTHORITY REGISTRY COMPLETENESS TEST
# ============================================================================

class TestAuthorityRegistryCompleteness:
    """Verify all SETTLE actions are registered in the authority map."""

    REQUIRED_ACTIONS = [
        "demand.draft.create",
        "demand.draft.review",
        "demand.authorize",
        "demand.transmit",
        "offer.record",
        "offer.notify_client",
        "counteroffer.create",
        "counteroffer.authorize",
        "settlement.accept",
        "settlement.reject",
        "settlement.counter",
        "attorney.recommendation",
        "agreement.create",
        "agreement.approve",
        "agreement.sign_client",
        "agreement.sign_firm",
        "release.review",
        "release.sign_client",
        "payment.record",
        "payment.receive",
        "allocation.create",
        "allocation.approve",
        "closing_statement.create",
        "closing_statement.approve",
        "disbursement.create",
        "disbursement.authorize",
        "lien.create",
        "lien.verify",
        "lien.resolve",
        "matter.close",
        "matter.reopen",
    ]

    def test_all_actions_registered(self):
        from app.services.settlement.authority_gate import SETTLE_AUTHORITY_MAP
        for action in self.REQUIRED_ACTIONS:
            assert action in SETTLE_AUTHORITY_MAP, f"Missing authority mapping for: {action}"

    def test_no_prohibited_actions(self):
        from app.services.settlement.authority_gate import (
            SETTLE_AUTHORITY_MAP,
            AuthorityClass,
        )
        settlement_decision_actions = [
            "settlement.accept",
            "settlement.reject",
            "settlement.counter",
        ]
        for action in settlement_decision_actions:
            authority = SETTLE_AUTHORITY_MAP[action]
            assert authority == AuthorityClass.CLIENT_AUTH, (
                f"Action '{action}' must require CLIENT_AUTH, got {authority}"
            )

    def test_attorney_actions_not_client(self):
        from app.services.settlement.authority_gate import (
            SETTLE_AUTHORITY_MAP,
            AuthorityClass,
        )
        attorney_actions = [
            "demand.authorize",
            "demand.draft.review",
            "attorney.recommendation",
            "matter.close",
            "matter.reopen",
        ]
        for action in attorney_actions:
            authority = SETTLE_AUTHORITY_MAP[action]
            assert authority != AuthorityClass.CLIENT_AUTH, (
                f"Action '{action}' should not need CLIENT_AUTH"
            )
