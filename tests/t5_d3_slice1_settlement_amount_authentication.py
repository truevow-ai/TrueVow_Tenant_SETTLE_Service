"""
T5-D3-TDD-001 — TRACER BULLET 1 (RED)

Seam A — provenance resolution.

A contribution claiming an upstream verdict reference may authenticate its
settlement amount ONLY when the reference resolves to a CURRENT authoritative
upstream settle_verdicts row and the projection faithfully matches it.

This test exercises ONE capability: authenticated settlement amount.

It deliberately does NOT assert that other analytical fields become verified.
Blanket field verification is the defect this tracer bullet exists to remove.

Reference surface: case_narrative structured JSON, key "_upstream_verdict_id".
The reference is a CLAIM, never authority.
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

def _upstream_verdict(
    *,
    verdict_id="v-10000000-0000-0000-0000-000000000001",
    review_status="verified",
    total_verdict=250000.0,
    settlement_amount=None,
    field_evidence=None,
):
    """A CURRENT authoritative settle_verdicts row.

    Amount selection follows the existing bridge contract
    (bridge_verdicts_to_estimator.py:121): total_verdict OR settlement_amount.
    """
    if field_evidence is None:
        field_evidence = {
            "total_verdict": {
                "value": "250000.00",
                "snippet": "total verdict $250,000.00",
                "source_url": "https://example.invalid/verdicts/v-10000000",
            },
        }
    return {
        "id": verdict_id,
        "review_status": review_status,
        "total_verdict": total_verdict,
        "settlement_amount": settlement_amount,
        "field_evidence": field_evidence,
    }


def _contribution(
    *,
    upstream_verdict_id="v-10000000-0000-0000-0000-000000000001",
    exact_outcome_amount=250000.0,
    source_type="scraped_verdict",
):
    """A settle_contributions row carrying a CLAIMED upstream reference.

    The reference lives in case_narrative JSON. It is a claim, not authority.
    """
    return {
        "id": "c-10000000-0000-0000-0000-000000000001",
        "source_type": source_type,
        "exact_outcome_amount": exact_outcome_amount,
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Motor Vehicle Accident",
        "medical_bills": 40000.0,
        "insurance_carrier": "Acme Insurance",
        "comparative_negligence_pct": 10.0,
        "injury_category": ["traumatic_brain_injury"],
        "defendant_category": "Business",
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
# RED — the capability must not exist before implementation
# ---------------------------------------------------------------------------

def test_authenticates_settlement_amount_when_reference_resolves_and_matches():
    """RED target.

    A contribution whose claimed upstream verdict id resolves to a CURRENT
    verified verdict, whose authoritative amount matches the contribution's
    exact_outcome_amount, and whose field_evidence supports that amount, may
    authenticate settlement_amount.

    Critically: no other analytical field becomes VERIFIED merely because the
    row is authenticated.
    """
    contribution = _contribution()
    upstream = _upstream_verdict()

    context = authenticate_projection(contribution, upstream)

    assert isinstance(context, AuthorityContext)
    assert context.authenticated is True
    assert context.field_states["settlement_amount"] == "verified"

    # Blanket field verification must NOT occur.
    for field in (
        "jurisdiction",
        "case_type",
        "medical_bills",
        "insurance_carrier",
        "comparative_negligence_pct",
        "injury_category",
        "defendant_category",
    ):
        assert context.field_states.get(field) != "verified", (
            f"{field} must not be blanket-verified by Seam A authentication"
        )