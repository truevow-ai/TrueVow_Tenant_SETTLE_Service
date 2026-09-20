"""
T5-D3-REPAIR-001 PART B — RED

Safe authority-reference serialization.

The bridge emits case_narrative as json.dumps(payload)[:5000]. Slicing
serialized JSON can truncate mid-document and produce invalid JSON, which
destroys the _upstream_verdict_id reference that D3 relies on for provenance.

A large but legitimate evidence payload must produce VALID, parseable,
structured JSON AND preserve the upstream reference key.

This is a bridge-contract test, not a Seam A test.
"""

import json

import pytest

from settle_data_scraping_factory.court_dockets_records import (
    bridge_verdicts_to_estimator as bridge,
)

REFERENCE_KEY = "_upstream_verdict_id"


def _large_field_evidence(n=60, per_entry=200):
    return {
        "field_%d" % i: {
            "value": "x" * per_entry,
            "snippet": "y" * per_entry,
            "source_url": "z" * per_entry,
        }
        for i in range(n)
    }


def _projected_narrative(field_evidence):
    """Serialize through the bridge's real serializer (post-repair)."""
    return bridge._serialize_narrative(
        {
            "_review_status": "verified",
            REFERENCE_KEY: "v-40000000-0000-0000-0000-000000000004",
            "field_evidence": field_evidence,
        }
    )


def test_large_legitimate_evidence_payload_keeps_reference_parseable():
    """RED target.

    A large but legitimate evidence payload must serialize to VALID,
    parseable structured JSON that still carries the upstream reference key.
    """
    narrative = _projected_narrative(_large_field_evidence())

    parsed = json.loads(narrative)  # must not raise
    assert isinstance(parsed, dict)
    assert REFERENCE_KEY in parsed
    assert parsed[REFERENCE_KEY]


def test_bridge_project_emits_reference_key():
    """The bridge's project() must carry the reserved reference key."""
    verdict = {
        "id": "v-40000000-0000-0000-0000-000000000004",
        "case_type": "motor_vehicle_accident",
        "outcome_type": "verdict_plaintiff",
        "review_status": "verified",
        "total_verdict": 100000.0,
        "jurisdiction": "Maricopa County, AZ",
        "verdict_date": "2024-01-15",
        "field_evidence": {
            "total_verdict": {
                "value": "100000.00",
                "snippet": "total verdict 100000.00",
                "source_url": "https://example.invalid/x",
            }
        },
    }

    row = bridge.project(verdict)

    assert row is not None
    payload = json.loads(row["case_narrative"])
    assert REFERENCE_KEY in payload
    assert payload[REFERENCE_KEY] == verdict["id"]