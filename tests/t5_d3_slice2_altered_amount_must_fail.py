"""
T5-D3-TDD-002 — TRACER BULLET 2 (RED)

Seam A — adversarial authentication.

Proves the upstream verdict reference is treated as a CLAIM requiring content
authentication, not as a magic provenance token.

A contribution that points at a REAL verified upstream verdict but alters
exact_outcome_amount MUST NOT receive VERIFIED authority for settlement_amount.

This slice concerns settlement_amount authority only. It does NOT introduce
a rule that one mismatched field invalidates every field forever.
"""

import json

import pytest

from app.services.analytics_authority import (
    AuthorityContext,
    authenticate_projection,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

AUTHORITATIVE_AMOUNT = 100000.0
ALTERED_AMOUNT = 125000.0
UPSTREAM_ID = "v-20000000-0000-0000-0000-000000000002"


def _upstream_verdict():
    """A real, CURRENT, verified upstream verdict with authoritative amount."""
    return {
        "id": UPSTREAM_ID,
        "review_status": "verified",
        "total_verdict": AUTHORITATIVE_AMOUNT,
        "settlement_amount": None,
        "field_evidence": {
            "total_verdict": {
                "value": "100000.00",
                "snippet": "total verdict $100,000.00",
                "source_url": "https://example.invalid/verdicts/v-20000000",
            },
        },
    }


def _contribution(*, upstream_verdict_id=UPSTREAM_ID, exact_outcome_amount=AUTHORITATIVE_AMOUNT):
    """A settle_contributions row carrying a CLAIMED upstream reference."""
    return {
        "id": "c-20000000-0000-0000-0000-000000000002",
        "source_type": "scraped_verdict",
        "exact_outcome_amount": exact_outcome_amount,
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Motor Vehicle Accident",
        "case_narrative": json.dumps(
            {
                "_upstream_verdict_id": upstream_verdict_id,
                "_review_status": "verified",
                "field_evidence": {},
            },
            default=str,
        ),
    }


# ---------------------------------------------------------------------------
# RED — the adversarial property
# ---------------------------------------------------------------------------

def test_real_upstream_reference_with_altered_amount_must_not_authenticate():
    """RED target.

    A contribution pointing at a REAL verified upstream verdict but with an
    altered exact_outcome_amount must NOT receive VERIFIED authority for
    settlement_amount.

    This proves the upstream id is a CLAIM requiring content authentication,
    not a magic provenance token.
    """
    contribution = _contribution(exact_outcome_amount=ALTERED_AMOUNT)
    upstream = _upstream_verdict()

    context = authenticate_projection(contribution, upstream)

    assert isinstance(context, AuthorityContext)
    assert context.authenticated is False
    assert context.field_states.get("settlement_amount") != "verified"
    assert "amount_mismatch" in context.reason