"""
Contract Registry — Golden Fixtures — WebhookSignature v1.0

Authoritative test vectors for cross-repository webhook signature validation.
Every backend service must pass these identical tests.

DO NOT re-serialize JSON bodies in verifiers — hash the exact raw request bytes.
"""

import json

FIXTURE_SECRET = "tv-golden-test-secret"
FIXTURE_KEY_ID = "tv-primary"
FIXTURE_SECONDARY_KEY_ID = "tv-secondary"
FIXTURE_SECONDARY_SECRET = "tv-golden-test-secret-2"
FIXTURE_PATH = "/api/v1/matter/activated"
FIXTURE_TIMESTAMP = "1753790400"

FIXTURE_VALID_BODY = json.dumps({
    "event_type": "matter.activated",
    "event_id": "a0000000-0000-0000-0000-000000000001",
    "tenant_id": "b0000000-0000-0000-0000-000000000002",
    "payload": {
        "matter_id": "c0000000-0000-0000-0000-000000000003",
        "activation_id": "10000000-0000-0000-0000-000000000010",
    }
}, sort_keys=True).encode()

FIXTURE_MODIFIED_BODY = json.dumps({
    "event_type": "matter.activated",
    "event_id": "a0000000-0000-0000-0000-000000000001",
    "tenant_id": "b0000000-0000-0000-0000-000000000002",
    "payload": {
        "matter_id": "c0000000-0000-0000-0000-000000000003",
        "activation_id": "20000000-0000-0000-0000-000000000020",
    }
}, sort_keys=True).encode()

FIXTURE_WRONG_PATH = "/api/v1/matter/wrong-endpoint"
FIXTURE_TRAILING_SLASH_PATH = "/api/v1/matter/activated/"
FIXTURE_QUERY_PATH = "/api/v1/matter/activated?foo=bar"

# Canonical signing string format: timestamp:method:path:body_hash
# Product extensions at root: PROHIBITED
# Extend only through payload object
