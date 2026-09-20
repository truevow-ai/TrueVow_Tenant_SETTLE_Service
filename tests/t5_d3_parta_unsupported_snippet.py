"""
T5-D3-REPAIR-001 PART A — RED

Adversarial evidence-semantics test at the approved Seam A.

The upstream verdict carries a field_evidence entry with a truthy source_url
and a truthy snippet, BUT the snippet does NOT actually support the
authoritative amount according to the repository's existing verdict evidence
contract (app/services/verdict_guard.py _value_backed: the value must appear
verbatim in the snippet — digits for amounts).

Expected: settlement_amount != VERIFIED.

A convenient JSON shape (source_url + snippet present) must not grant field
authority. Only value-backed evidence does.
"""

import json

import pytest

from app.services.analytics_authority import (
    AuthorityContext,
    authenticate_projection,
)

AUTHORITATIVE_AMOUNT = 100000.0
UPSTREAM_ID = "v-30000000-0000-0000-0000-000000000003"


def _upstream_verdict():
    """Real, verified, with an evidence entry that has the right SHAPE but
    a snippet that does NOT support the authoritative amount."""
    return {
        "id": UPSTREAM_ID,
        "review_status": "verified",
        "total_verdict": AUTHORITATIVE_AMOUNT,
        "settlement_amount": None,
        "field_evidence": {
            "total_verdict": {
                "value": "100000.00",
                # Truthy source_url and truthy snippet — the convenient JSON
                # shape Slice 1's _field_evidence_supports() currently accepts.
                # But the snippet does not mention the amount at all, so the
                # repository's real evidence contract rejects it.
                "snippet": "this record was reviewed and confirmed",
                "source_url": "https://example.invalid/verdicts/v-30000000",
            },
        },
    }


def _contribution():
    return {
        "id": "c-30000000-0000-0000-0000-000000000003",
        "source_type": "scraped_verdict",
        "exact_outcome_amount": AUTHORITATIVE_AMOUNT,
        "case_narrative": json.dumps(
            {
                "_upstream_verdict_id": UPSTREAM_ID,
                "_review_status": "verified",
                "field_evidence": {},
            },
            default=str,
        ),
    }


def test_unsupported_snippet_must_not_grant_amount_authority():
    """RED target.

    An evidence entry whose snippet does not verbatim support the
    authoritative amount must NOT grant settlement_amount VERIFIED authority,
    even though source_url and snippet are both truthy.
    """
    contribution = _contribution()
    upstream = _upstream_verdict()

    context = authenticate_projection(contribution, upstream)

    assert isinstance(context, AuthorityContext)
    assert context.authenticated is False
    assert context.field_states.get("settlement_amount") != "verified"