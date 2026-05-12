"""
Tests for app/services/intelligence_gate.py + estimator wiring.

Year-2 "Never Sell Empty Dashboards" guardrail. These tests verify the HARD
n<50 floor: aggregate ranges must never render when approved-row count
falls below the threshold, regardless of legacy multiplier fallbacks.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock

from app.services.intelligence_gate import (
    IntelligenceGate,
    AggregateGateResult,
    SUPPRESSED_WHEN_INSUFFICIENT,
    MIN_AGGREGATE_N,
)
from app.services.estimator import SettlementEstimator
from app.models.case_bank import EstimateRequest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_stub(count_value: int):
    """
    Build a Supabase-shaped query builder that returns `count_value` from
    `.execute().count`. Matches the fluent chain used in IntelligenceGate.check.
    """
    exec_result = MagicMock()
    exec_result.count = count_value
    exec_result.data = []

    query = MagicMock()
    query.eq.return_value = query
    query.execute.return_value = exec_result

    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value = query
    return db


def _make_raising_db():
    """DB whose execute() raises — for fail-closed verification."""
    query = MagicMock()
    query.eq.return_value = query
    query.execute.side_effect = RuntimeError("connection dropped")

    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value = query
    return db


# ---------------------------------------------------------------------------
# IntelligenceGate.check()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gate_insufficient_when_n_below_50():
    db = _make_db_stub(count_value=7)
    gate = IntelligenceGate(db_connection=db)

    result = await gate.check(jurisdiction="Duval County, FL", case_type="MVA")

    assert isinstance(result, AggregateGateResult)
    assert result.status == "insufficient_data"
    assert result.n == 7
    assert result.threshold == MIN_AGGREGATE_N
    assert result.own_case_only is True
    assert result.suppressed_features == SUPPRESSED_WHEN_INSUFFICIENT
    assert result.jurisdiction == "Duval County, FL"
    assert result.case_type == "MVA"


@pytest.mark.asyncio
async def test_gate_sufficient_at_threshold():
    db = _make_db_stub(count_value=MIN_AGGREGATE_N)
    gate = IntelligenceGate(db_connection=db)

    result = await gate.check(jurisdiction="Duval County, FL")

    assert result.status == "sufficient"
    assert result.n == MIN_AGGREGATE_N
    assert result.own_case_only is False
    assert result.suppressed_features == []


@pytest.mark.asyncio
async def test_gate_sufficient_well_above_threshold():
    db = _make_db_stub(count_value=250)
    gate = IntelligenceGate(db_connection=db)

    result = await gate.check(jurisdiction="Maricopa County, AZ", case_type="Premises")

    assert result.status == "sufficient"
    assert result.n == 250
    assert result.own_case_only is False


@pytest.mark.asyncio
async def test_gate_fails_closed_when_db_none(monkeypatch):
    # Force get_db() to return None so the gate takes the "DB unavailable" branch.
    async def _none_db():
        return None
    monkeypatch.setattr("app.services.intelligence_gate.get_db", _none_db)

    gate = IntelligenceGate(db_connection=None)
    result = await gate.check(jurisdiction="Duval County, FL")

    assert result.status == "insufficient_data"
    assert result.n == 0
    assert result.own_case_only is True
    assert result.suppressed_features == SUPPRESSED_WHEN_INSUFFICIENT


@pytest.mark.asyncio
async def test_gate_fails_closed_on_query_exception():
    db = _make_raising_db()
    gate = IntelligenceGate(db_connection=db)

    result = await gate.check(jurisdiction="Duval County, FL")

    assert result.status == "insufficient_data"
    assert result.n == 0
    assert result.own_case_only is True


# ---------------------------------------------------------------------------
# SettlementEstimator integration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_estimator_short_circuits_on_insufficient_data():
    """
    When the gate says insufficient_data, the estimator MUST return an
    EstimateResponse with zero percentiles, own_case_only=True, and
    the full suppressed_features list. No multiplier fallback.
    """
    stub_gate = MagicMock()
    stub_gate.check = AsyncMock(return_value=AggregateGateResult(
        status="insufficient_data",
        n=7,
        threshold=MIN_AGGREGATE_N,
        own_case_only=True,
        suppressed_features=list(SUPPRESSED_WHEN_INSUFFICIENT),
        jurisdiction="Duval County, FL",
        case_type="Motor Vehicle Accident",
    ))

    estimator = SettlementEstimator(db_connection=None, gate=stub_gate)

    request = EstimateRequest(
        jurisdiction="Duval County, FL",
        case_type="Motor Vehicle Accident",
        injury_category=["Spinal Injury"],
        medical_bills=25000.0,
    )
    response = await estimator.estimate_settlement_range(request)

    assert response.confidence == "insufficient_data"
    assert response.own_case_only is True
    assert response.n_cases == 7
    assert response.percentile_25 == 0.0
    assert response.median == 0.0
    assert response.percentile_75 == 0.0
    assert response.percentile_95 == 0.0
    assert response.comparable_cases == []
    assert set(response.suppressed_features) == set(SUPPRESSED_WHEN_INSUFFICIENT)
    assert "suppressed" in (response.range_justification or "").lower()


@pytest.mark.asyncio
async def test_estimator_runs_full_pipeline_when_gate_passes():
    """
    When the gate returns sufficient, the estimator proceeds through the
    percentile branch. Mock data in _generate_mock_cases returns 25 rows,
    which is enough to exercise the percentile path.
    """
    stub_gate = MagicMock()
    stub_gate.check = AsyncMock(return_value=AggregateGateResult(
        status="sufficient",
        n=120,
        threshold=MIN_AGGREGATE_N,
        own_case_only=False,
        suppressed_features=[],
        jurisdiction="Duval County, FL",
        case_type="Motor Vehicle Accident",
    ))

    estimator = SettlementEstimator(db_connection=None, gate=stub_gate)

    request = EstimateRequest(
        jurisdiction="Duval County, FL",
        case_type="Motor Vehicle Accident",
        injury_category=["Spinal Injury"],
        medical_bills=25000.0,
    )
    response = await estimator.estimate_settlement_range(request)

    assert response.confidence in {"medium", "high"}
    assert response.own_case_only is False
    assert response.suppressed_features == []
    assert response.median > 0
