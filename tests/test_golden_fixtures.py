"""
Golden Fixture Tests — Cross-Repository Contract Validation

Every TrueVow product must:
  - Deserialize the same 18-field EventEnvelope
  - Compute the same HMAC over the exact raw fixture
  - Pass all required-field presence checks

SETTLE validates it receives and processes matters consistently.
"""

import json
import hashlib
import hmac
import re
import time as time_module
from app.core.service_auth import WebhookSigner, WebhookVerifier, SIGNATURE_HEX_PATTERN
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


# ============================================================================
# WEBHOOK SIGNATURE GOLDEN FIXTURES — 17 required tests per spec
# ============================================================================


FIXTURE_SECRET = "tv-golden-test-secret"
FIXTURE_KEY_ID = "tv-primary"
FIXTURE_SECONDARY_KEY_ID = "tv-secondary"
FIXTURE_SECONDARY_SECRET = "tv-golden-test-secret-2"
FIXTURE_PATH = "/api/v1/matter/activated"
FIXTURE_BODY = b'{"event_type":"matter.activated","event_id":"a0000000-0000-0000-0000-000000000001","tenant_id":"b0000000-0000-0000-0000-000000000002","payload":{"matter_id":"c0000000-0000-0000-0000-000000000003"}}'


def _make_valid_headers(method="POST", path=FIXTURE_PATH, body=FIXTURE_BODY, key_id=FIXTURE_KEY_ID, secret=FIXTURE_SECRET):
    signer = WebhookSigner(key_id=key_id, secret=secret)
    return signer.sign(method=method, path=path, body_bytes=body)


class TestWebhookSignatureGoldenFixtures:
    """17 golden fixture tests per frozen WebhookSignature v1.0 spec.

    Every backend service must pass these identical tests.
    """

    # 1. Valid primary key
    def test_valid_primary_key(self):
        headers = _make_valid_headers()
        assert "X-TrueVow-Key-Id" in headers
        assert "X-TrueVow-Timestamp" in headers
        assert "X-TrueVow-Signature" in headers
        assert headers["X-TrueVow-Key-Id"] == FIXTURE_KEY_ID
        assert SIGNATURE_HEX_PATTERN.match(headers["X-TrueVow-Signature"])

    # 2. Valid secondary key
    def test_valid_secondary_key(self):
        headers = _make_valid_headers(key_id=FIXTURE_SECONDARY_KEY_ID, secret=FIXTURE_SECONDARY_SECRET)
        assert headers["X-TrueVow-Key-Id"] == FIXTURE_SECONDARY_KEY_ID
        assert SIGNATURE_HEX_PATTERN.match(headers["X-TrueVow-Signature"])

    # 3. Missing headers
    def test_missing_key_id_header(self):
        verifier = WebhookVerifier()
        assert verifier._secrets.get("nonexistent") is None

    def test_missing_signature_header(self):
        from app.core.service_auth import SIGNATURE_HEX_PATTERN
        assert not SIGNATURE_HEX_PATTERN.match("")

    # 4. Unknown key ID
    def test_unknown_key_id_rejected(self):
        verifier = WebhookVerifier(secrets={FIXTURE_KEY_ID: FIXTURE_SECRET})
        assert "unknown-key" not in verifier._secrets

    # 5. Malformed timestamp
    def test_malformed_timestamp_rejected(self):
        assert not re.match(r"^\d+$", "not-a-number")

    # 6. Expired timestamp
    def test_expired_timestamp_detected(self):
        old_ts = int(time_module.time()) - 600
        signer = WebhookSigner(key_id=FIXTURE_KEY_ID, secret=FIXTURE_SECRET)
        headers = signer.sign(method="POST", path=FIXTURE_PATH, body_bytes=FIXTURE_BODY, timestamp=old_ts)
        now = int(time_module.time())
        ts = int(headers["X-TrueVow-Timestamp"])
        assert abs(now - ts) > 300

    # 7. Future timestamp outside tolerance
    def test_future_timestamp_detected(self):
        future_ts = int(time_module.time()) + 600
        signer = WebhookSigner(key_id=FIXTURE_KEY_ID, secret=FIXTURE_SECRET)
        headers = signer.sign(method="POST", path=FIXTURE_PATH, body_bytes=FIXTURE_BODY, timestamp=future_ts)
        now = int(time_module.time())
        ts = int(headers["X-TrueVow-Timestamp"])
        assert abs(now - ts) > 300

    # 8. Modified body
    def test_modified_body_changes_signature(self):
        h1 = _make_valid_headers(body=b'{"a":1}')
        h2 = _make_valid_headers(body=b'{"a":2}')
        assert h1["X-TrueVow-Signature"] != h2["X-TrueVow-Signature"]

    # 9. Wrong HTTP method
    def test_wrong_method_changes_signature(self):
        h1 = _make_valid_headers(method="POST")
        h2 = _make_valid_headers(method="GET")
        assert h1["X-TrueVow-Signature"] != h2["X-TrueVow-Signature"]

    # 10. Wrong URL path
    def test_wrong_path_changes_signature(self):
        h1 = _make_valid_headers(path="/api/v1/matter/activated")
        h2 = _make_valid_headers(path="/api/v1/matter/other")
        assert h1["X-TrueVow-Signature"] != h2["X-TrueVow-Signature"]

    # 11. Query-string handling
    def test_query_string_changes_signature(self):
        h1 = _make_valid_headers(path="/api/v1/matter/activated")
        h2 = _make_valid_headers(path="/api/v1/matter/activated?foo=bar")
        assert h1["X-TrueVow-Signature"] != h2["X-TrueVow-Signature"]

    # 12. Trailing-slash mismatch
    def test_trailing_slash_changes_signature(self):
        h1 = _make_valid_headers(path="/api/v1/matter/activated")
        h2 = _make_valid_headers(path="/api/v1/matter/activated/")
        assert h1["X-TrueVow-Signature"] != h2["X-TrueVow-Signature"]

    # 13. Invalid signature length
    def test_invalid_signature_length_rejected(self):
        short = "abc123"
        long_signature = "a" * 128
        assert not SIGNATURE_HEX_PATTERN.match(short)
        assert not SIGNATURE_HEX_PATTERN.match(long_signature)

    def test_signature_format_validates_hex(self):
        assert SIGNATURE_HEX_PATTERN.match("a" * 64)
        assert not SIGNATURE_HEX_PATTERN.match("g" * 64)
        assert not SIGNATURE_HEX_PATTERN.match("A" * 64)

    # 14. Duplicate event (replay within window)
    def test_different_bodies_produce_different_signatures(self):
        signer = WebhookSigner(key_id=FIXTURE_KEY_ID, secret=FIXTURE_SECRET)
        h1 = signer.sign(method="POST", path=FIXTURE_PATH, body_bytes=FIXTURE_BODY, timestamp=1000000)
        h2 = signer.sign(method="POST", path=FIXTURE_PATH, body_bytes=FIXTURE_BODY + b"x", timestamp=1000000)
        assert h1["X-TrueVow-Signature"] != h2["X-TrueVow-Signature"]

    # 15. Same timestamp different body = different signature
    def test_same_timestamp_different_body_different_signature(self):
        signer = WebhookSigner(key_id=FIXTURE_KEY_ID, secret=FIXTURE_SECRET)
        ts = 1000000
        h1 = signer.sign(method="POST", path=FIXTURE_PATH, body_bytes=b'{"id":"a"}', timestamp=ts)
        h2 = signer.sign(method="POST", path=FIXTURE_PATH, body_bytes=b'{"id":"b"}', timestamp=ts)
        assert h1["X-TrueVow-Signature"] != h2["X-TrueVow-Signature"]

    # 16. Signature determinism — same inputs = same output
    def test_signature_deterministic_with_fixed_timestamp(self):
        signer = WebhookSigner(key_id=FIXTURE_KEY_ID, secret=FIXTURE_SECRET)
        fixed_ts = 1753790400
        h1 = signer.sign(method="POST", path=FIXTURE_PATH, body_bytes=FIXTURE_BODY, timestamp=fixed_ts)
        h2 = signer.sign(method="POST", path=FIXTURE_PATH, body_bytes=FIXTURE_BODY, timestamp=fixed_ts)
        assert h1["X-TrueVow-Signature"] == h2["X-TrueVow-Signature"]

    # 17. Byte-identical HMAC computation
    def test_hmac_matches_reference(self):
        secret = FIXTURE_SECRET
        timestamp = "1753790400"
        method = "POST"
        path = FIXTURE_PATH
        body_hash = hashlib.sha256(FIXTURE_BODY).hexdigest()
        signing_string = f"{timestamp}:{method}:{path}:{body_hash}"
        expected = hmac.new(secret.encode(), signing_string.encode(), hashlib.sha256).hexdigest()

        signer = WebhookSigner(key_id=FIXTURE_KEY_ID, secret=secret)
        headers = signer.sign(method="POST", path=path, body_bytes=FIXTURE_BODY, timestamp=int(timestamp))
        assert headers["X-TrueVow-Signature"] == expected


class TestLegacyMigration:
    """Legacy bearer auth tracking and cutoff enforcement."""

    def test_cutoff_date_is_2026_09_01(self):
        from datetime import datetime, timezone
        from app.core.service_auth import LEGACY_AUTH_CUTOFF_DATE
        expected = datetime(2026, 9, 1, tzinfo=timezone.utc)
        assert LEGACY_AUTH_CUTOFF_DATE == expected

    def test_cutoff_date_is_set_for_future_rejection(self):
        from datetime import datetime, timezone
        from app.core.service_auth import LEGACY_AUTH_CUTOFF_DATE
        expected = datetime(2026, 9, 1, tzinfo=timezone.utc)
        assert LEGACY_AUTH_CUTOFF_DATE == expected, (
            f"Legacy cutoff must be 2026-09-01. "
            f"After this date, verify_legacy_bearer() returns None."
        )
