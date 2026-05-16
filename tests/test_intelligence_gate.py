"""
Tests for app/services/intelligence_gate.py + estimator wiring.

Year-2 "Never Sell Empty Dashboards" guardrail. These tests verify the HARD
n<50 floor: aggregate ranges must never render when approved-row count
falls below the threshold, regardless of legacy multiplier fallbacks.
"""

from __future__ import annotations

import pytest
from typing import Optional
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
    `.execute().count` for eq-only chains (county-exact tier). State-tier
    ilike queries hit auto-generated MagicMocks whose execute().count is
    non-int — gate catches the TypeError and returns n_state=0. So tests
    using this stub see: n_county=count_value, n_state=0.

    Tests that care about state-tier counts should use _make_hierarchical_db_stub.
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


def _make_hierarchical_db_stub(n_county: int, n_state_suffix: int, n_state_sentinel: int):
    """
    Build a db stub whose `.execute().count` differs depending on whether
    the last filter was .eq('jurisdiction', ...) [county tier] or
    .ilike('jurisdiction', '%, STATE') [state suffix] or
    .ilike('jurisdiction', 'STATE (%') [state sentinel].

    Implementation: each jurisdiction-filter method returns a DIFFERENT
    terminal node whose execute() returns the tier-specific count. The
    status/case_type/carrier filters self-chain before the terminal.
    """
    def _mk_exec(count: int):
        r = MagicMock()
        r.count = count
        r.data = []
        ex = MagicMock()
        ex.execute.return_value = r
        return ex

    county_node = _mk_exec(n_county)
    suffix_node = _mk_exec(n_state_suffix)
    sentinel_node = _mk_exec(n_state_sentinel)

    # Pre-filter node chains status/case_type/carrier .eq() calls and
    # dispatches on the jurisdiction filter method.
    prefilter = MagicMock()
    prefilter.eq.return_value = prefilter  # status / case_type / carrier

    def _eq_dispatch(col, val):
        if col == "jurisdiction":
            return county_node
        return prefilter  # status, case_type, carrier

    def _ilike_dispatch(col, pattern):
        if col == "jurisdiction":
            # Sentinel patterns start with the state code, e.g. 'FL (%'.
            # Suffix patterns start with '%, '.
            if pattern.startswith("%,"):
                return suffix_node
            return sentinel_node
        return prefilter

    prefilter.eq.side_effect = _eq_dispatch
    prefilter.ilike.side_effect = _ilike_dispatch

    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value = prefilter
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
    assert result.aggregation_level == "none"
    assert result.n_county == 7
    # state-tier queries on a non-hierarchical stub return 0 via the
    # TypeError-caught path; gate reports max(n_county, n_state) as n.
    assert result.n_state == 0
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
    assert result.aggregation_level == "county"
    assert result.n == MIN_AGGREGATE_N
    assert result.n_county == MIN_AGGREGATE_N
    assert result.own_case_only is False
    assert result.suppressed_features == []


@pytest.mark.asyncio
async def test_gate_sufficient_well_above_threshold():
    db = _make_db_stub(count_value=250)
    gate = IntelligenceGate(db_connection=db)

    result = await gate.check(jurisdiction="Maricopa County, AZ", case_type="Premises")

    assert result.status == "sufficient"
    assert result.aggregation_level == "county"
    assert result.n == 250
    assert result.own_case_only is False


# ---------------------------------------------------------------------------
# Hierarchical fallback tests (Option D)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gate_falls_back_to_state_when_county_thin():
    """
    County has 13 rows (below floor), state-wide counties have 50, sentinel
    bucket has 107. Gate should fall back to state tier: n_state = 50+107 = 157.
    """
    db = _make_hierarchical_db_stub(
        n_county=13, n_state_suffix=50, n_state_sentinel=107,
    )
    gate = IntelligenceGate(db_connection=db)

    result = await gate.check(
        jurisdiction="Miami-Dade County, FL", case_type="Motor Vehicle Accident"
    )

    assert result.status == "sufficient"
    assert result.aggregation_level == "state"
    assert result.n_county == 13
    assert result.n_state == 157
    assert result.n == 157
    assert result.own_case_only is False
    assert result.suppressed_features == []


@pytest.mark.asyncio
async def test_gate_county_tier_preferred_over_state():
    """
    When county clears the floor, gate should NOT fall back to state — even
    if state-wide would give a bigger number. Higher precision wins.
    """
    db = _make_hierarchical_db_stub(
        n_county=75, n_state_suffix=200, n_state_sentinel=300,
    )
    gate = IntelligenceGate(db_connection=db)

    result = await gate.check(
        jurisdiction="Miami-Dade County, FL", case_type="Motor Vehicle Accident"
    )

    assert result.status == "sufficient"
    assert result.aggregation_level == "county"
    assert result.n == 75
    assert result.n_county == 75
    # State tier was not queried; n_state echoes county as lower bound.
    assert result.n_state == 75


@pytest.mark.asyncio
async def test_gate_insufficient_when_neither_tier_clears():
    """
    Both tiers below floor. Gate reports the max as n, returns insufficient.
    """
    db = _make_hierarchical_db_stub(
        n_county=13, n_state_suffix=20, n_state_sentinel=10,
    )
    gate = IntelligenceGate(db_connection=db)

    result = await gate.check(
        jurisdiction="Miami-Dade County, FL", case_type="Motor Vehicle Accident"
    )

    assert result.status == "insufficient_data"
    assert result.aggregation_level == "none"
    assert result.n_county == 13
    assert result.n_state == 30   # 20 + 10
    assert result.n == 30         # max(13, 30)
    assert result.own_case_only is True
    assert result.suppressed_features == SUPPRESSED_WHEN_INSUFFICIENT


@pytest.mark.asyncio
async def test_gate_state_tier_sums_suffix_plus_sentinel():
    """
    State tier clears via sentinel ALONE (counties below floor, sentinel above).
    Verifies the sentinel ("FL (Unknown County)") bucket participates in the
    state count — the whole point of Option D.
    """
    db = _make_hierarchical_db_stub(
        n_county=10, n_state_suffix=20, n_state_sentinel=107,
    )
    gate = IntelligenceGate(db_connection=db)

    result = await gate.check(
        jurisdiction="Broward County, FL", case_type="Motor Vehicle Accident"
    )

    assert result.status == "sufficient"
    assert result.aggregation_level == "state"
    assert result.n_state == 127  # 20 + 107
    assert result.n == 127


@pytest.mark.asyncio
async def test_gate_cannot_fallback_without_parseable_state():
    """
    Malformed jurisdiction (no comma) — state tier can't be attempted.
    Gate returns insufficient with aggregation_level='none'.
    """
    db = _make_hierarchical_db_stub(
        n_county=0, n_state_suffix=200, n_state_sentinel=200,
    )
    gate = IntelligenceGate(db_connection=db)

    # No comma in the jurisdiction — _parse_state returns None.
    result = await gate.check(jurisdiction="SomeMalformedJurisdiction")

    assert result.status == "insufficient_data"
    assert result.aggregation_level == "none"
    assert result.n_state == 0  # state tier never queried


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
        aggregation_level="county",
        n=120,
        n_county=120,
        n_state=120,
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
    # Option D: county-tier response carries tier signal.
    assert response.aggregation_level == "county"
    assert response.n_county == 120


@pytest.mark.asyncio
async def test_estimator_state_tier_response_contract():
    """
    Option D: when the gate falls back to state tier, the EstimateResponse
    MUST carry aggregation_level='state' and the justification MUST tell
    the attorney the numbers are statewide with county-specific precision
    pending.
    """
    stub_gate = MagicMock()
    stub_gate.check = AsyncMock(return_value=AggregateGateResult(
        status="sufficient",
        aggregation_level="state",
        n=157,
        n_county=13,
        n_state=157,
        threshold=MIN_AGGREGATE_N,
        own_case_only=False,
        suppressed_features=[],
        jurisdiction="Miami-Dade County, FL",
        case_type="Motor Vehicle Accident",
    ))

    estimator = SettlementEstimator(db_connection=None, gate=stub_gate)

    request = EstimateRequest(
        jurisdiction="Miami-Dade County, FL",
        case_type="Motor Vehicle Accident",
        injury_category=["Spinal Injury"],
        medical_bills=25000.0,
    )
    response = await estimator.estimate_settlement_range(request)

    # Response contract: tier signal propagated.
    assert response.aggregation_level == "state"
    assert response.n_county == 13
    assert response.n_state == 157
    assert response.own_case_only is False
    assert response.suppressed_features == []
    assert response.median > 0

    # Justification copy: must reference statewide aggregation AND the
    # county-specific precision-in-progress signal.
    justification = (response.range_justification or "").lower()
    assert "fl" in justification or "statewide" in justification or "florida" in justification
    assert "miami-dade" in justification
    assert "aggregated" in justification or "aggregation" in justification


@pytest.mark.asyncio
async def test_estimator_insufficient_carries_tier_fields():
    """
    When both tiers fail, the suppressed response carries n_county/n_state
    so the UI can tell the attorney exactly how close each tier is.
    """
    stub_gate = MagicMock()
    stub_gate.check = AsyncMock(return_value=AggregateGateResult(
        status="insufficient_data",
        aggregation_level="none",
        n=30,
        n_county=13,
        n_state=30,
        threshold=MIN_AGGREGATE_N,
        own_case_only=True,
        suppressed_features=list(SUPPRESSED_WHEN_INSUFFICIENT),
        jurisdiction="Miami-Dade County, FL",
        case_type="Motor Vehicle Accident",
    ))

    estimator = SettlementEstimator(db_connection=None, gate=stub_gate)

    request = EstimateRequest(
        jurisdiction="Miami-Dade County, FL",
        case_type="Motor Vehicle Accident",
        injury_category=["Spinal Injury"],
        medical_bills=25000.0,
    )
    response = await estimator.estimate_settlement_range(request)

    assert response.confidence == "insufficient_data"
    assert response.own_case_only is True
    assert response.aggregation_level == "none"
    assert response.n_county == 13
    assert response.n_state == 30
    assert response.percentile_25 == 0.0
    assert response.median == 0.0


@pytest.mark.asyncio
async def test_estimator_handles_empty_pool_after_state_tier_pass():
    """
    Cohort R (2026-05-13): regression guard for the empty-pool 500.

    The gate can clear the state tier on (jurisdiction + case_type) yet the
    estimator's injury_category filter can narrow the pool to zero rows. The
    estimator MUST short-circuit to a graceful insufficient_data response
    instead of letting numpy.percentile([]) raise IndexError. The gate's
    tier counts (n_county / n_state) are preserved so the UI can explain to
    the attorney that the jurisdiction has data but no verdicts match the
    requested injury filter.
    """
    stub_gate = MagicMock()
    stub_gate.check = AsyncMock(return_value=AggregateGateResult(
        status="sufficient",
        aggregation_level="state",
        n=193,
        n_county=4,
        n_state=193,
        threshold=MIN_AGGREGATE_N,
        own_case_only=False,
        suppressed_features=[],
        jurisdiction="Orange County, FL",
        case_type="Premises Liability",
    ))

    estimator = SettlementEstimator(db_connection=None, gate=stub_gate)
    # Force the post-gate pool to be empty regardless of mock data.
    estimator._query_comparable_cases = AsyncMock(return_value=[])

    request = EstimateRequest(
        jurisdiction="Orange County, FL",
        case_type="Premises Liability",
        injury_category=["soft_tissue"],
        medical_bills=30000.0,
    )

    # MUST NOT raise.
    response = await estimator.estimate_settlement_range(request)

    # Graceful insufficient_data shape.
    assert response.confidence == "insufficient_data"
    assert response.own_case_only is True
    assert response.aggregation_level == "none"
    assert response.n_cases == 0
    assert response.percentile_25 == 0.0
    assert response.median == 0.0
    assert response.percentile_75 == 0.0
    assert response.percentile_95 == 0.0
    assert response.comparable_cases == []
    # Gate tier counts preserved for UI messaging.
    assert response.n_county == 4
    assert response.n_state == 193
    # Suppression list mirrors the gate-fail branch.
    assert set(response.suppressed_features) == set(SUPPRESSED_WHEN_INSUFFICIENT)
    # Justification names the jurisdiction, the n=193 statewide pool, and
    # the injury filter that wiped the pool out.
    j = (response.range_justification or "").lower()
    assert "orange county" in j
    assert "193" in j
    assert "soft_tissue" in j or "injury" in j


# ---------------------------------------------------------------------------
# Pilot-mode gate tests (ADR S-2 v2 — Cohort T)
# ---------------------------------------------------------------------------

from app.core.config import settings as _settle_settings  # noqa: E402


def _make_pilot_db_stub(
    n_county: int,
    n_state_suffix: int,
    n_state_sentinel: int,
    pilot_suffix_rows: Optional[list] = None,
    pilot_sentinel_rows: Optional[list] = None,
):
    """Pilot-aware db stub. Two select shapes coexist:

      1) `.select("id", count="exact")` — production count path. `.execute().count`
         returns the configured tier count (n_county / n_state_suffix /
         n_state_sentinel) based on the jurisdiction filter chosen.
      2) `.select("id, injury_category")` — pilot eligibility path. `.execute().data`
         returns the pre-configured row list (pilot_suffix_rows /
         pilot_sentinel_rows) based on the jurisdiction filter chosen.
    """
    pilot_suffix_rows = pilot_suffix_rows or []
    pilot_sentinel_rows = pilot_sentinel_rows or []

    def _terminal(*, count: int = 0, data: Optional[list] = None):
        r = MagicMock()
        r.count = count
        r.data = data if data is not None else []
        ex = MagicMock()
        ex.execute.return_value = r
        return ex

    # Build per-(select-shape, jurisdiction-filter) terminals.
    count_county = _terminal(count=n_county)
    count_suffix = _terminal(count=n_state_suffix)
    count_sentinel = _terminal(count=n_state_sentinel)
    pilot_suffix = _terminal(data=pilot_suffix_rows)
    pilot_sentinel = _terminal(data=pilot_sentinel_rows)

    def _make_prefilter(*, is_pilot_select: bool):
        """Each select-shape gets its own prefilter chain so the dispatch
        knows which terminal family to route to."""
        prefilter = MagicMock()
        prefilter.eq.return_value = prefilter

        def _eq_dispatch(col, val):
            if col == "jurisdiction":
                # Pilot helper never uses .eq for jurisdiction (it always
                # uses .ilike), but production county tier does.
                return count_county
            return prefilter

        def _ilike_dispatch(col, pattern):
            if col != "jurisdiction":
                return prefilter
            if pattern.startswith("%,"):
                return pilot_suffix if is_pilot_select else count_suffix
            return pilot_sentinel if is_pilot_select else count_sentinel

        prefilter.eq.side_effect = _eq_dispatch
        prefilter.ilike.side_effect = _ilike_dispatch
        return prefilter

    count_prefilter = _make_prefilter(is_pilot_select=False)
    pilot_prefilter = _make_prefilter(is_pilot_select=True)

    select_mock = MagicMock()

    def _select_dispatch(*args, **kwargs):
        # Production count path: .select("id", count="exact")
        if kwargs.get("count") == "exact" or (len(args) >= 2 and args[1] == "exact"):
            terminal = MagicMock()
            terminal.eq.return_value = count_prefilter
            return terminal
        # Pilot path: .select("id, injury_category")
        if args and isinstance(args[0], str) and "injury_category" in args[0]:
            terminal = MagicMock()
            terminal.eq.return_value = pilot_prefilter
            return terminal
        # Default — fall back to count terminal
        terminal = MagicMock()
        terminal.eq.return_value = count_prefilter
        return terminal

    select_mock.side_effect = _select_dispatch

    table_mock = MagicMock()
    table_mock.select = select_mock

    db = MagicMock()
    db.table.return_value = table_mock
    return db


class TestPilotMode:
    """Pilot-mode gate threshold (ADR S-2 v2). Verifies sentinel exclusion,
    feature-flag gating, and county-tier non-relaxation."""

    @pytest.fixture(autouse=True)
    def _restore_pilot_mode(self, monkeypatch):
        # Default OFF for every test — each test opts in via monkeypatch.
        monkeypatch.setattr(_settle_settings, "SETTLE_PILOT_MODE", False)

    @pytest.mark.asyncio
    async def test_pilot_mode_off_uses_production_floor(self, monkeypatch):
        """Flag off → pilot path never fires even if user is flagged."""
        monkeypatch.setattr(_settle_settings, "SETTLE_PILOT_MODE", False)
        # Pilot rows present but irrelevant — flag is off.
        pilot_rows = [{"id": f"r{i}", "injury_category": ["traumatic_brain_injury"]} for i in range(15)]
        db = _make_pilot_db_stub(
            n_county=5, n_state_suffix=10, n_state_sentinel=5,
            pilot_suffix_rows=pilot_rows,
        )
        gate = IntelligenceGate(db_connection=db)

        result = await gate.check(
            jurisdiction="Miami-Dade County, FL",
            case_type="Motor Vehicle Accident",
            is_pilot_user=True,
        )

        assert result.status == "insufficient_data"
        assert result.is_pilot_response is False

    @pytest.mark.asyncio
    async def test_pilot_mode_on_pilot_user_passes_at_n_10(self, monkeypatch):
        """Flag on + pilot user + 12 real-tag rows → pilot state-tier sufficient."""
        monkeypatch.setattr(_settle_settings, "SETTLE_PILOT_MODE", True)
        pilot_rows = [
            {"id": f"r{i}", "injury_category": ["traumatic_brain_injury"]}
            for i in range(12)
        ]
        db = _make_pilot_db_stub(
            n_county=5, n_state_suffix=8, n_state_sentinel=4,
            pilot_suffix_rows=pilot_rows,
        )
        gate = IntelligenceGate(db_connection=db)

        result = await gate.check(
            jurisdiction="Miami-Dade County, FL",
            case_type="Motor Vehicle Accident",
            is_pilot_user=True,
        )

        assert result.status == "sufficient"
        assert result.aggregation_level == "state"
        assert result.is_pilot_response is True
        assert result.threshold == IntelligenceGate.PILOT_MIN_AGGREGATE_N
        assert result.n == 12
        assert result.n_state == 12
        assert result.suppressed_features == []

    @pytest.mark.asyncio
    async def test_pilot_mode_sentinel_only_rows_excluded(self, monkeypatch):
        """30 rows with ONLY sentinel tags → pilot_eligible=0 → insufficient."""
        monkeypatch.setattr(_settle_settings, "SETTLE_PILOT_MODE", True)
        sentinel_rows = [
            {"id": f"s{i}", "injury_category": ["general_personal_injury"]}
            for i in range(30)
        ]
        db = _make_pilot_db_stub(
            n_county=5, n_state_suffix=20, n_state_sentinel=10,
            pilot_suffix_rows=sentinel_rows[:20],
            pilot_sentinel_rows=sentinel_rows[20:],
        )
        gate = IntelligenceGate(db_connection=db)

        result = await gate.check(
            jurisdiction="Miami-Dade County, FL",
            case_type="Motor Vehicle Accident",
            is_pilot_user=True,
        )

        assert result.status == "insufficient_data"
        assert result.is_pilot_response is False

    @pytest.mark.asyncio
    async def test_pilot_mode_mixed_tags_partially_counts(self, monkeypatch):
        """Rows with at least one real InjuryTag count, even alongside sentinels."""
        monkeypatch.setattr(_settle_settings, "SETTLE_PILOT_MODE", True)
        mixed_rows = [
            {
                "id": f"m{i}",
                "injury_category": ["general_personal_injury", "traumatic_brain_injury"],
            }
            for i in range(15)
        ]
        db = _make_pilot_db_stub(
            n_county=5, n_state_suffix=10, n_state_sentinel=5,
            pilot_suffix_rows=mixed_rows,
        )
        gate = IntelligenceGate(db_connection=db)

        result = await gate.check(
            jurisdiction="Miami-Dade County, FL",
            case_type="Motor Vehicle Accident",
            is_pilot_user=True,
        )

        assert result.status == "sufficient"
        assert result.is_pilot_response is True
        assert result.n == 15

    @pytest.mark.asyncio
    async def test_pilot_mode_non_pilot_user_uses_production_floor(self, monkeypatch):
        """Flag on but is_pilot_user=False → pilot path skipped."""
        monkeypatch.setattr(_settle_settings, "SETTLE_PILOT_MODE", True)
        pilot_rows = [
            {"id": f"r{i}", "injury_category": ["traumatic_brain_injury"]}
            for i in range(15)
        ]
        db = _make_pilot_db_stub(
            n_county=5, n_state_suffix=10, n_state_sentinel=5,
            pilot_suffix_rows=pilot_rows,
        )
        gate = IntelligenceGate(db_connection=db)

        result = await gate.check(
            jurisdiction="Miami-Dade County, FL",
            case_type="Motor Vehicle Accident",
            is_pilot_user=False,
        )

        assert result.status == "insufficient_data"
        assert result.is_pilot_response is False

    @pytest.mark.asyncio
    async def test_pilot_mode_county_tier_still_requires_production_floor(self, monkeypatch):
        """County=30 (below 50) + state pilot-eligible=12 → pilot state-tier,
        NOT a county-tier relaxation. Pilot mode never bypasses county floor."""
        monkeypatch.setattr(_settle_settings, "SETTLE_PILOT_MODE", True)
        pilot_rows = [
            {"id": f"r{i}", "injury_category": ["traumatic_brain_injury"]}
            for i in range(12)
        ]
        db = _make_pilot_db_stub(
            n_county=30, n_state_suffix=8, n_state_sentinel=4,
            pilot_suffix_rows=pilot_rows,
        )
        gate = IntelligenceGate(db_connection=db)

        result = await gate.check(
            jurisdiction="Miami-Dade County, FL",
            case_type="Motor Vehicle Accident",
            is_pilot_user=True,
        )

        assert result.status == "sufficient"
        assert result.aggregation_level == "state"
        assert result.is_pilot_response is True
        assert result.n_county == 30  # production county count surfaced for transparency
        assert result.n == 12

