"""
Golden Fixture Tests — Cross-Repository Contract Validation

Every TrueVow product must:
  - Deserialize the same 18-field EventEnvelope
  - Compute the same HMAC over the exact raw fixture
  - Pass all required-field presence checks

SETTLE validates it receives and processes matters consistently.
"""

import json
import pytest
from app.shared.contracts import (
    make_golden_envelope,
    make_golden_fixture_json,
    compute_golden_hmac,
    CONTRACT_VERSIONS,
    ENVELOPE_REQUIRED_FIELDS,
    MANIFEST_REQUIRED_FIELDS,
)
from app.shared.models import EventEnvelope
from app.models.activation import (
    MatterActivationPayload,
    MatterActivationEvidenceManifest,
)


class TestGoldenFixture:
    """Cross-repository golden fixture — SETTLE validation."""

    def test_envelope_serializes_to_18_fields(self):
        envelope = make_golden_envelope()
        data = envelope.model_dump(mode="json")
        actual = set(data.keys())
        assert actual == ENVELOPE_REQUIRED_FIELDS, (
            f"Missing fields: {ENVELOPE_REQUIRED_FIELDS - actual}, "
            f"Extra fields: {actual - ENVELOPE_REQUIRED_FIELDS}"
        )

    def test_envelope_schema_version_is_1_0_1(self):
        envelope = make_golden_envelope()
        assert envelope.schema_version == "1.0.1"

    def test_envelope_deserializes_roundtrip(self):
        envelope = make_golden_envelope()
        json_str = make_golden_fixture_json()
        reloaded = EventEnvelope.model_validate(json.loads(json_str))
        assert reloaded.event_id == envelope.event_id
        assert reloaded.event_type == envelope.event_type
        assert reloaded.aggregate_type == envelope.aggregate_type
        assert reloaded.actor_type == envelope.actor_type
        assert reloaded.authority_class == envelope.authority_class
        assert reloaded.schema_version == "1.0.1"

    def test_hmac_is_deterministic(self):
        secret = "golden-fixture-secret"
        h1 = compute_golden_hmac(secret)
        h2 = compute_golden_hmac(secret)
        assert h1 == h2
        assert len(h1) == 64

    def test_hmac_changes_with_different_secret(self):
        h1 = compute_golden_hmac("secret-a")
        h2 = compute_golden_hmac("secret-b")
        assert h1 != h2

    def test_hmac_changes_with_different_body(self):
        h1 = compute_golden_hmac("secret", method="POST")
        h2 = compute_golden_hmac("secret", method="GET")
        assert h1 != h2


class TestFrozenContracts:
    """All contracts are frozen at the declared versions."""

    def test_event_envelope_version(self):
        assert CONTRACT_VERSIONS["EventEnvelope"] == "1.0.1"

    def test_matter_activated_payload_version(self):
        assert CONTRACT_VERSIONS["MatterActivatedPayload"] == "1.0"

    def test_evidence_manifest_version(self):
        assert CONTRACT_VERSIONS["ActivationEvidenceManifest"] == "1.0"

    def test_webhook_signature_version(self):
        assert CONTRACT_VERSIONS["WebhookSignature"] == "1.0"

    def test_authority_registry_version(self):
        assert CONTRACT_VERSIONS["AuthorityClassRegistry"] == "1.0"

    def test_ontology_registry_version(self):
        assert CONTRACT_VERSIONS["OntologyRegistry"] == "1.0"


class TestEvidenceManifest:
    """All 9 activation evidence references are present and mandatory."""

    def test_manifest_has_nine_required_fields(self):
        actual = set(MatterActivationEvidenceManifest.model_fields.keys())
        assert MANIFEST_REQUIRED_FIELDS.issubset(actual), (
            f"Missing: {MANIFEST_REQUIRED_FIELDS - actual}"
        )

    def test_manifest_can_be_constructed_with_all_nine(self):
        from uuid import uuid4
        from datetime import datetime, timezone

        manifest = MatterActivationEvidenceManifest(
            manifest_id=uuid4(),
            activation_id=uuid4(),
            representation_decision_id=uuid4(),
            conflict_clearance_authority_id=uuid4(),
            engagement_workflow_id=uuid4(),
            executed_package_id=uuid4(),
            signature_evidence_ids=[uuid4(), uuid4()],
            completed_copy_delivery_id=uuid4(),
            responsible_attorney_assignment_id=uuid4(),
            jurisdiction_profile_version_id=uuid4(),
            activation_policy_version_id=uuid4(),
            generated_at=datetime.now(timezone.utc),
        )
        assert manifest.representation_decision_id is not None
        assert manifest.conflict_clearance_authority_id is not None
        assert len(manifest.signature_evidence_ids) >= 1


class TestMatterActivationPayload:
    """SETTLE receives the payload, builds resolution context."""

    def test_payload_has_eleven_fields(self):
        fields = set(MatterActivationPayload.model_fields.keys())
        expected = {
            "matter_id", "activation_id", "evidence_manifest_id",
            "source_matter_candidate_id", "client_party_role_id",
            "responsible_attorney_assignment_id", "jurisdiction_profile_version_id",
            "activation_policy_version_id", "engagement_workflow_id",
            "occurred_at", "schema_version",
        }
        assert fields == expected

    def test_payload_can_be_constructed(self):
        from uuid import uuid4
        from datetime import datetime, timezone

        payload = MatterActivationPayload(
            matter_id=uuid4(),
            activation_id=uuid4(),
            evidence_manifest_id=uuid4(),
            source_matter_candidate_id=uuid4(),
            client_party_role_id=uuid4(),
            responsible_attorney_assignment_id=uuid4(),
            jurisdiction_profile_version_id=uuid4(),
            activation_policy_version_id=uuid4(),
            engagement_workflow_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
        )
        assert payload.schema_version == "1.0.1"


class TestJurisdictionSeparation:
    """Global JurisdictionProfile vs TenantJurisdictionActivation."""

    def test_global_profile_has_no_tenant_id(self):
        from app.shared.models import JurisdictionProfile
        fields = JurisdictionProfile.model_fields
        assert "tenant_id" not in fields, "Global JurisdictionProfile must not carry tenant_id"

    def test_tenant_activation_has_tenant_id(self):
        from app.shared.models import TenantJurisdictionActivation
        fields = TenantJurisdictionActivation.model_fields
        assert "tenant_id" in fields, "TenantJurisdictionActivation must carry tenant_id"

    def test_tenant_activation_references_profile(self):
        from app.shared.models import TenantJurisdictionActivation
        fields = TenantJurisdictionActivation.model_fields
        assert "jurisdiction_profile_version_id" in fields, "Must reference the global profile version"
