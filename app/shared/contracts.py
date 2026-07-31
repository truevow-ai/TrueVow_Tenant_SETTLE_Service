"""
Frozen Shared Contracts — SETTLE Service v1.0.1

These contracts are frozen. Future incompatible changes require a new version.
Existing fields must not be renamed in place.

Contract                  Version    Status
──────────────────────    ───────    ──────
EventEnvelope             v1.0.1     FROZEN
MatterActivatedPayload    v1.0       FROZEN
ActivationEvidenceManifest v1.0      FROZEN
WebhookSignature          v1.0       FROZEN
AuthorityClass Registry   v1.0       FROZEN
Ontology Registry         v1.0       FROZEN
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from uuid import UUID

from app.shared.models import (
    EventEnvelope,
    AuthorityClass,
    ActorRole,
)


CONTRACT_VERSIONS = {
    "EventEnvelope": "1.0.1",
    "MatterActivatedPayload": "1.0",
    "ActivationEvidenceManifest": "1.0",
    "WebhookSignature": "1.0",
    "AuthorityClassRegistry": "1.0",
    "OntologyRegistry": "1.0",
}

ENVELOPE_REQUIRED_FIELDS = {
    "event_id", "event_type", "occurred_at", "recorded_at", "tenant_id",
    "aggregate_type", "aggregate_id", "aggregate_version",
    "actor_type", "actor_id", "authority_class", "authority_record_id",
    "policy_version_id", "correlation_id", "causation_id",
    "payload", "sensitivity_class", "schema_version",
}

MANIFEST_REQUIRED_FIELDS = {
    "manifest_id", "activation_id",
    "representation_decision_id", "conflict_clearance_authority_id",
    "engagement_workflow_id", "executed_package_id",
    "signature_evidence_ids", "completed_copy_delivery_id",
    "responsible_attorney_assignment_id",
    "jurisdiction_profile_version_id", "activation_policy_version_id",
    "generated_at", "schema_version",
}


def make_golden_envelope() -> EventEnvelope:
    """Produces the deterministic golden fixture for cross-repository testing.

    Every product (INTAKE, RETAINER, TRACE, SETTLE, COMMAND) must:
      - Deserialize this exact event
      - Produce the same 18-field envelope structure
      - Calculate the same HMAC over the raw fixture
    """
    return EventEnvelope(
        event_id=UUID("a0000000-0000-0000-0000-000000000001"),
        event_type="matter.activated",
        occurred_at=datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc),
        recorded_at=datetime(2026, 7, 29, 12, 0, 1, tzinfo=timezone.utc),
        tenant_id=UUID("b0000000-0000-0000-0000-000000000002"),
        aggregate_type="matter",
        aggregate_id=UUID("c0000000-0000-0000-0000-000000000003"),
        aggregate_version=1,
        actor_type=ActorRole.RESPONSIBLE_ATTORNEY,
        actor_id=UUID("d0000000-0000-0000-0000-000000000004"),
        authority_class=AuthorityClass.ATTY_AUTH,
        authority_record_id=UUID("e0000000-0000-0000-0000-000000000005"),
        policy_version_id=UUID("f0000000-0000-0000-0000-000000000006"),
        correlation_id=UUID("a0000000-0000-0000-0000-000000000001"),
        causation_id=None,
        payload={
            "matter_id": "c0000000-0000-0000-0000-000000000003",
            "activation_id": "10000000-0000-0000-0000-000000000010",
        },
        sensitivity_class="internal",
        schema_version="1.0.1",
    )


def make_golden_fixture_json() -> str:
    """Serialized golden fixture for HMAC verification."""
    envelope = make_golden_envelope()
    return json.dumps(envelope.model_dump(mode="json"), sort_keys=True)


def compute_golden_hmac(secret: str, method: str = "POST", path: str = "/api/v1/matter/activated") -> str:
    """Compute HMAC matching SaaS Admin TypeScript: timestamp:method:path:body_hash."""
    body = make_golden_fixture_json()
    body_bytes = body.encode()
    timestamp = "1753790400"
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    signing_string = f"{timestamp}:{method.upper()}:{path}:{body_hash}"
    return hmac.new(secret.encode(), signing_string.encode(), hashlib.sha256).hexdigest()
