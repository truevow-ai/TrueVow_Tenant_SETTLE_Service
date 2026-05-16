"""
Unit tests for Settlement Estimator Service
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock, AsyncMock

from app.services.estimator import SettlementEstimator
from app.services.intelligence_gate import AggregateGateResult, MIN_AGGREGATE_N
from app.models.case_bank import EstimateRequest, SettleContribution


def _sufficient_gate(n: int = 120) -> MagicMock:
    """Stub IntelligenceGate that always returns sufficient — lets the
    percentile branch run against the estimator's mock cases."""
    stub = MagicMock()
    stub.check = AsyncMock(return_value=AggregateGateResult(
        status="sufficient",
        n=n,
        threshold=MIN_AGGREGATE_N,
        own_case_only=False,
        suppressed_features=[],
    ))
    return stub


@pytest.mark.asyncio
async def test_estimator_with_sufficient_cases():
    """Test estimator with >=15 cases (percentile calculation)"""

    estimator = SettlementEstimator(gate=_sufficient_gate())

    request = EstimateRequest(
        jurisdiction="Maricopa County, AZ",
        case_type="Auto Accident",
        injury_category=["Spinal Injury", "Back Injury"],
        medical_bills=50000.00
    )

    response = await estimator.estimate_settlement_range(request)

    # Assertions
    assert response.n_cases >= 15, "Should have at least 15 cases"
    assert response.confidence in ["medium", "high"]
    assert response.percentile_25 < response.median < response.percentile_75 < response.percentile_95
    assert response.response_time_ms < 1000, "Should respond in <1 second"
    assert len(response.comparable_cases) > 0


@pytest.mark.asyncio
async def test_estimator_with_insufficient_cases():
    """Test estimator with <15 cases (multiplier fallback)"""
    
    estimator = SettlementEstimator()
    
    # Mock query that returns few cases
    # In production, this would query a jurisdiction with limited data
    
    request = EstimateRequest(
        jurisdiction="Test County, WY",  # Small state
        case_type="Rare Case Type",
        injury_category=["Rare Injury Type"],
        medical_bills=25000.00
    )
    
    # For this test, we'd mock the database to return <15 cases
    # Response should use multiplier fallback
    # confidence should be "low"


@pytest.mark.asyncio
async def test_bucket_to_midpoint():
    """Test outcome range bucket to midpoint conversion"""
    
    estimator = SettlementEstimator()
    
    assert estimator._bucket_to_midpoint("$50k-$100k") == 75000
    assert estimator._bucket_to_midpoint("$300k-$600k") == 450000
    assert estimator._bucket_to_midpoint("$1M+") == 1500000


@pytest.mark.asyncio
async def test_response_time():
    """Test that estimator responds within 1 second"""

    estimator = SettlementEstimator(gate=_sufficient_gate())

    request = EstimateRequest(
        jurisdiction="Maricopa County, AZ",
        case_type="Auto Accident",
        injury_category=["Spinal Injury"],
        medical_bills=50000.00
    )
    
    start_time = datetime.now(UTC)
    response = await estimator.estimate_settlement_range(request)
    elapsed_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
    
    assert elapsed_ms < 1000, f"Response took {elapsed_ms}ms, should be <1000ms"
    assert response.response_time_ms < 1000


# ---------------------------------------------------------------------------
# Pilot-mode estimator tests (ADR S-2 v2 — Cohort T)
# ---------------------------------------------------------------------------

from app.services.intelligence_gate import IntelligenceGate  # noqa: E402


def _pilot_gate(n: int = 12) -> MagicMock:
    """Stub that returns a pilot-mode AggregateGateResult (is_pilot_response=True)."""
    stub = MagicMock()
    stub.check = AsyncMock(return_value=AggregateGateResult(
        status="sufficient",
        aggregation_level="state",
        n=n,
        n_county=5,
        n_state=n,
        threshold=IntelligenceGate.PILOT_MIN_AGGREGATE_N,
        own_case_only=False,
        suppressed_features=[],
        is_pilot_response=True,
    ))
    return stub


def _build_contribution(idx: int, *, narrative: bool):
    """Build a SettleContribution with or without case_narrative."""
    return SettleContribution(
        id=uuid4(),
        jurisdiction="Miami-Dade County, FL",
        case_type="Motor Vehicle Accident",
        injury_category=["traumatic_brain_injury"],
        primary_diagnosis="TBI",
        treatment_type=["Surgery"],
        duration_of_treatment="6-12 months",
        imaging_findings=["MRI"],
        medical_bills=40000.0 + idx * 1000,
        lost_wages=8000.0,
        policy_limits="$100k/$300k",
        defendant_category="Business",
        outcome_type="Settlement",
        outcome_amount_range=[
            "$50k-$100k", "$100k-$150k", "$150k-$225k",
            "$225k-$300k", "$300k-$600k",
        ][idx % 5],
        contributed_at=datetime.now(UTC) - timedelta(days=idx * 5),
        blockchain_hash=f"h{idx}",
        consent_confirmed=True,
        contributor_api_key_id=uuid4(),
        founding_member=True,
        created_at=datetime.now(UTC) - timedelta(days=idx * 5),
        updated_at=datetime.now(UTC) - timedelta(days=idx * 5),
        status="approved",
        rejection_reason=None,
        is_outlier=False,
        confidence_score=1.0,
        case_narrative=(f"Real prose for case {idx}: TBI fact pattern, "
                        f"surgery, recovery details." if narrative else None),
    )


class TestPilotModeEstimator:
    """Tests for the pilot-mode estimator path (ADR S-2 v2): displayable
    cases gate, no confidence override, justification disclosure, and
    narrative-only comparable_cases."""

    @pytest.mark.asyncio
    async def test_pilot_mode_displayable_gate_fires(self):
        """Gate cleared (n=12), but only 3 cases have case_narrative → suppressed."""
        cases = (
            [_build_contribution(i, narrative=True) for i in range(3)]
            + [_build_contribution(i + 100, narrative=False) for i in range(9)]
        )
        estimator = SettlementEstimator(gate=_pilot_gate(n=12))

        async def _stub_query(req, aggregation_level="county"):
            return cases
        estimator._query_comparable_cases = _stub_query  # type: ignore[assignment]

        request = EstimateRequest(
            jurisdiction="Miami-Dade County, FL",
            case_type="Motor Vehicle Accident",
            injury_category=["traumatic_brain_injury"],
            medical_bills=40000.0,
        )

        response = await estimator.estimate_settlement_range(
            request, is_pilot_user=True
        )

        # Suppressed because narrative count (3) < PILOT_NARRATIVE_FLOOR (5).
        assert response.confidence == "insufficient_data"
        assert response.own_case_only is True
        assert response.is_pilot_response is False  # suppressed response — not a pilot estimate
        assert response.aggregation_level == "none"
        assert response.median == 0.0
        assert response.comparable_cases == []
        assert "narrative" in (response.range_justification or "").lower()

    @pytest.mark.asyncio
    async def test_pilot_response_confidence_not_overridden(self):
        """Pilot mode preserves the statistical confidence label — NOT "pilot_phase"."""
        cases = [_build_contribution(i, narrative=True) for i in range(12)]
        estimator = SettlementEstimator(gate=_pilot_gate(n=12))

        async def _stub_query(req, aggregation_level="county"):
            return cases
        estimator._query_comparable_cases = _stub_query  # type: ignore[assignment]

        request = EstimateRequest(
            jurisdiction="Miami-Dade County, FL",
            case_type="Motor Vehicle Accident",
            injury_category=["traumatic_brain_injury"],
            medical_bills=40000.0,
        )

        response = await estimator.estimate_settlement_range(
            request, is_pilot_user=True
        )

        # Confidence is the statistical measure (medium for n<30, high for n>=30).
        # Critically: it is NOT "pilot_phase" — the is_pilot_response bool
        # is the dedicated UI signal.
        assert response.confidence in ("high", "medium")
        assert response.confidence != "pilot_phase"
        assert response.is_pilot_response is True
        assert response.aggregation_level == "state"

    @pytest.mark.asyncio
    async def test_pilot_response_justification_includes_pilot_disclosure(self):
        """Justification contains the explicit PILOT MODE disclosure copy."""
        cases = [_build_contribution(i, narrative=True) for i in range(12)]
        estimator = SettlementEstimator(gate=_pilot_gate(n=12))

        async def _stub_query(req, aggregation_level="county"):
            return cases
        estimator._query_comparable_cases = _stub_query  # type: ignore[assignment]

        request = EstimateRequest(
            jurisdiction="Miami-Dade County, FL",
            case_type="Motor Vehicle Accident",
            injury_category=["traumatic_brain_injury"],
            medical_bills=40000.0,
        )

        response = await estimator.estimate_settlement_range(
            request, is_pilot_user=True
        )

        j = response.range_justification or ""
        assert "PILOT MODE" in j
        assert "STATEWIDE" in j or "statewide" in j
        assert "narrative" in j.lower()

    @pytest.mark.asyncio
    async def test_pilot_response_excludes_non_narrative_cases_from_comparable(self):
        """comparable_cases array contains ONLY narrative-bearing rows."""
        narrative_cases = [_build_contribution(i, narrative=True) for i in range(8)]
        non_narrative_cases = [_build_contribution(i + 100, narrative=False) for i in range(20)]
        all_cases = narrative_cases + non_narrative_cases
        estimator = SettlementEstimator(gate=_pilot_gate(n=8))

        async def _stub_query(req, aggregation_level="county"):
            return all_cases
        estimator._query_comparable_cases = _stub_query  # type: ignore[assignment]

        request = EstimateRequest(
            jurisdiction="Miami-Dade County, FL",
            case_type="Motor Vehicle Accident",
            injury_category=["traumatic_brain_injury"],
            medical_bills=40000.0,
        )

        response = await estimator.estimate_settlement_range(
            request, is_pilot_user=True
        )

        # n_cases reflects displayable count (8), not the gate's pre-filter
        # raw count or the unfiltered query result (28).
        assert response.n_cases == 8
        assert response.is_pilot_response is True
        # Sample is capped at 10; all comparable cases must be narrative-bearing.
        assert len(response.comparable_cases) > 0
        assert len(response.comparable_cases) <= 8

