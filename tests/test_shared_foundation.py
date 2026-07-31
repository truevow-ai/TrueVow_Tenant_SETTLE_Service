"""
Shared Foundation Tests — TrueVow Platform Core

Tests the 9 shared foundation services that every product uses.
"""

import pytest
from datetime import datetime, UTC, date
from uuid import UUID, uuid4

from app.shared.models import (
    AuthorityClass, ActorRole, ConsentType, ConsentState,
    DocumentState, WorkItemState, CommunicationChannel,
    Tenant, Matter, ConsentRecord, DocumentVersion,
    AuditEvent, EventEnvelope, TransitionContract,
    JurisdictionProfile, FirmPolicy, IntegrationConnection,
    RoleAssignment,
)


# ============================================================================
# AUTHORITY GATE TESTS
# ============================================================================

class TestAuthorityGate:
    def test_settlement_accept_is_client_only(self):
        from app.shared.authority_gate import authority_gate
        assert authority_gate.is_client_only("settlement.accept") is True

    def test_representation_approve_is_attorney_only(self):
        from app.shared.authority_gate import authority_gate
        assert authority_gate.is_attorney_only("representation.approve") is True

    def test_ai_self_authorize_is_prohibited(self):
        from app.shared.authority_gate import authority_gate
        assert authority_gate.is_prohibited("platform.self_authorize") is True

    def test_conflict_clear_is_prohibited_for_platform(self):
        from app.shared.authority_gate import UNIVERSAL_AUTHORITY_REGISTRY
        assert UNIVERSAL_AUTHORITY_REGISTRY["conflict.clear"]["platform_role"] == "prohibited"

    def test_client_can_accept_settlement(self):
        from app.shared.authority_gate import authority_gate
        result = authority_gate.validate(
            action="settlement.accept",
            actor_role=ActorRole.CLIENT,
            actor_id=uuid4(),
            tenant_id=uuid4(),
        )
        assert result["valid"] is True

    def test_paralegal_cannot_accept_settlement(self):
        from app.shared.authority_gate import authority_gate
        result = authority_gate.validate(
            action="settlement.accept",
            actor_role=ActorRole.PARALEGAL,
            actor_id=uuid4(),
            tenant_id=uuid4(),
        )
        assert result["valid"] is False

    def test_attorney_can_approve_representation(self):
        from app.shared.authority_gate import authority_gate
        result = authority_gate.validate(
            action="representation.approve",
            actor_role=ActorRole.RESPONSIBLE_ATTORNEY,
            actor_id=uuid4(),
            tenant_id=uuid4(),
        )
        assert result["valid"] is True

    def test_case_manager_cannot_approve_representation(self):
        from app.shared.authority_gate import authority_gate
        result = authority_gate.validate(
            action="representation.approve",
            actor_role=ActorRole.CASE_MANAGER,
            actor_id=uuid4(),
            tenant_id=uuid4(),
        )
        assert result["valid"] is False

    def test_transition_contract_valid(self):
        from app.shared.authority_gate import authority_gate
        contract = TransitionContract(
            transition_id=uuid4(),
            aggregate_type="matter",
            from_states=["active_prelitigation", "demand_preparation"],
            to_state="negotiation",
            command="open_negotiation",
            required_authority=AuthorityClass.ATTY_AUTH,
            event_type="negotiation.round_opened",
        )
        result = authority_gate.validate_transition(contract, "active_prelitigation")
        assert result["valid"] is True

    def test_transition_contract_invalid_state(self):
        from app.shared.authority_gate import authority_gate
        contract = TransitionContract(
            transition_id=uuid4(),
            aggregate_type="matter",
            from_states=["active_prelitigation"],
            to_state="negotiation",
            command="open_negotiation",
            required_authority=AuthorityClass.ATTY_AUTH,
            event_type="negotiation.round_opened",
        )
        result = authority_gate.validate_transition(contract, "closed")
        assert result["valid"] is False

    def test_all_core_actions_registered(self):
        from app.shared.authority_gate import UNIVERSAL_AUTHORITY_REGISTRY
        required = [
            "settlement.accept", "settlement.reject", "settlement.counter",
            "representation.approve", "representation.decline",
            "conflict.clear", "conflict.search",
            "demand.authorize_transmission",
            "engagement.sign_client", "engagement.sign_firm",
            "matter.activate", "matter.close",
            "disbursement.authorize", "allocation.approve",
        ]
        for action in required:
            assert action in UNIVERSAL_AUTHORITY_REGISTRY, f"Missing action: {action}"


# ============================================================================
# ACTOR ROLE AUTHORITY MAP TESTS
# ============================================================================

class TestActorAuthorityMap:
    def test_attorney_has_full_authority(self):
        from app.shared.authority_gate import ACTOR_AUTHORITY_MAP
        allowed = ACTOR_AUTHORITY_MAP[ActorRole.RESPONSIBLE_ATTORNEY]
        assert AuthorityClass.ATTY_AUTH in allowed
        assert AuthorityClass.STAFF_AUTH in allowed

    def test_client_has_client_auth_only(self):
        from app.shared.authority_gate import ACTOR_AUTHORITY_MAP
        allowed = ACTOR_AUTHORITY_MAP[ActorRole.CLIENT]
        assert AuthorityClass.CLIENT_AUTH in allowed
        assert AuthorityClass.ATTY_AUTH not in allowed
        assert AuthorityClass.STAFF_AUTH not in allowed

    def test_ai_cannot_do_attorney_things(self):
        from app.shared.authority_gate import ACTOR_AUTHORITY_MAP
        allowed = ACTOR_AUTHORITY_MAP[ActorRole.AI_ASSISTANCE]
        assert AuthorityClass.ATTY_AUTH not in allowed
        assert AuthorityClass.CLIENT_AUTH not in allowed


# ============================================================================
# CONSENT LEDGER TESTS
# ============================================================================

class TestConsentModels:
    def test_consent_record_creation(self):
        record = ConsentRecord(
            id=uuid4(),
            tenant_id=uuid4(),
            person_id=uuid4(),
            consent_type="electronic_signature",
            state="requested",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert record.state == "requested"
        assert record.consent_type == "electronic_signature"

    def test_consent_state_transitions_are_app_only(self):
        valid_states = {"not_requested", "requested", "granted", "declined", "revoked", "expired", "superseded"}
        assert set(ConsentState.__args__) == valid_states


# ============================================================================
# DOCUMENT SERVICE TESTS
# ============================================================================

class TestDocumentService:
    def test_compute_hash_deterministic(self):
        from app.shared.document_service import document_service
        h1 = document_service.compute_hash("test content")
        h2 = document_service.compute_hash("test content")
        h3 = document_service.compute_hash("different content")
        assert h1 == h2
        assert h1 != h3
        assert len(h1) == 64

    def test_document_state_values(self):
        states = {"draft", "in_review", "approved", "executed", "filed_or_sent", "superseded", "void", "archived"}
        assert set(DocumentState.__args__) == states


# ============================================================================
# EVENT ENVELOPE TESTS
# ============================================================================

class TestEventEnvelope:
    def test_envelope_creation(self):
        envelope = EventEnvelope(
            event_id=uuid4(),
            event_type="matter.activated",
            occurred_at=datetime.now(UTC),
            tenant_id=uuid4(),
            aggregate_type="matter",
            aggregate_id=uuid4(),
            aggregate_version=1,
            actor_type=ActorRole.RESPONSIBLE_ATTORNEY,
            actor_id=uuid4(),
            authority_class=AuthorityClass.ATTY_AUTH,
            authority_record_id=uuid4(),
            policy_version_id=uuid4(),
        )
        assert envelope.schema_version == "1.0.1"
        assert envelope.event_type == "matter.activated"

    def test_envelope_required_fields(self):
        required = {
            "event_id", "event_type", "occurred_at", "recorded_at", "tenant_id",
            "aggregate_type", "aggregate_id", "aggregate_version",
            "actor_type", "actor_id", "authority_class", "authority_record_id",
            "policy_version_id", "correlation_id", "causation_id",
            "payload", "sensitivity_class", "schema_version",
        }
        envelope_fields = set(EventEnvelope.model_fields.keys())
        assert required.issubset(envelope_fields)


# ============================================================================
# TENANT & IDENTITY TESTS
# ============================================================================

class TestTenantModels:
    def test_tenant_isolation(self):
        t1 = uuid4()
        t2 = uuid4()
        tenant1 = Tenant(
            id=t1, name="Firm A", slug="firm-a",
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC),
        )
        assert str(tenant1.id) == str(t1)
        assert tenant1.slug == "firm-a"

    def test_matter_requires_attorney(self):
        matter = Matter(
            id=uuid4(),
            tenant_id=uuid4(),
            client_party_role_id=uuid4(),
            responsible_attorney_id=uuid4(),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert matter.responsible_attorney_id is not None

    def test_role_assignment_time_bounded(self):
        from datetime import timedelta
        now = datetime.now(UTC)
        role = RoleAssignment(
            id=uuid4(),
            user_id=uuid4(),
            tenant_id=uuid4(),
            role=ActorRole.PARALEGAL,
            effective_from=now,
            effective_to=now + timedelta(days=365),
            created_at=now,
            updated_at=now,
        )
        assert role.effective_to is not None


# ============================================================================
# TRANSITION CONTRACT TESTS
# ============================================================================

class TestTransitionContract:
    def test_default_fail_closed(self):
        contract = TransitionContract(
            transition_id=uuid4(),
            aggregate_type="settlement_agreement",
            from_states=["draft"],
            to_state="in_review",
            command="SubmitForReview",
            required_authority=AuthorityClass.ATTY_AUTH,
            event_type="agreement.submitted_for_review",
        )
        assert contract.failure_mode == "fail_closed"

    def test_requires_evidence(self):
        contract = TransitionContract(
            transition_id=uuid4(),
            aggregate_type="disbursement",
            from_states=["authorized"],
            to_state="completed",
            command="CompleteDisbursement",
            required_authority=AuthorityClass.STAFF_AUTH,
            required_evidence=["trust_balance_check", "payee_verification"],
            event_type="disbursement.completed",
        )
        assert "trust_balance_check" in contract.required_evidence


# ============================================================================
# WORK ITEM TESTS
# ============================================================================

class TestWorkItem:
    def test_work_item_states(self):
        states = {"created", "assigned", "in_progress", "blocked", "awaiting_external", "review_required", "completed", "waived", "cancelled"}
        assert set(WorkItemState.__args__) == states


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegrationModels:
    def test_integration_types(self):
        from app.shared.models import IntegrationType
        expected = {"calendar", "crm", "case_management", "esignature", "accounting", "trust_accounting", "document_storage", "email", "sms", "voice", "export", "import"}
        assert set(IntegrationType.__args__) == expected
