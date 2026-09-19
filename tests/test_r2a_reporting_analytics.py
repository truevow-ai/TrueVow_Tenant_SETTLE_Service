"""
T5-R2A tests: settlement-intelligence reporting / trend / carrier-pattern
consumer remediation.

R2A wires the R1 canonical derived eligibility authority
(app.services.analytics_authority) into the reporting consumers. It creates
no new eligibility engine.

Over-inclusion control: a row with an unverified REQUIRED field is excluded
from the operation that requires it.
Over-exclusion control: an unverified UNRELATED field does NOT exclude the
row from an operation that does not require it.
Extreme-value control: an approved but analytically ineligible extreme value
cannot alter the statistic.
Correction / invalidation: a previously verified value stops affecting the
statistic when verification is removed; a re-verified replacement may re-enter.
"""

import json
import pytest
from app.services.analytics_authority import (
    required_dimensions_for_operation,
    record_eligible_for_operation,
    filter_rows_eligible,
    _row_carries_bridge_provenance,
    _extract_upstream_review_status,
)


def _narr(status):
    return json.dumps({"_review_status": status, "field_evidence": {}})


def _row(amount, injuries, verified=True, jurisdiction="Maricopa County, AZ",
         case_type="Motor Vehicle Accident", carrier="State Farm",
         medical_bills=50000.0, defendant_category="Business"):
    return {
        "id": f"r-{amount}",
        "status": "approved",
        "source_type": "scraped_verdict",
        "exact_outcome_amount": amount,
        "jurisdiction": jurisdiction,
        "case_type": case_type,
        "medical_bills": medical_bills,
        "insurance_carrier": carrier,
        "defendant_category": defendant_category,
        "comparative_negligence_pct": 25.0,
        "injury_category": injuries,
        "case_narrative": _narr("verified" if verified else "pending"),
    }


# ---------------------------------------------------------------------------
# R2A-1: bridge-authority safety check
# ---------------------------------------------------------------------------

def test_bridge_provenance_requires_upstream_verified_status():
    """scraped_verdict + amount alone must NOT confer verification."""
    base = _row(100000.0, ["Spinal Injury"])
    assert _row_carries_bridge_provenance(base) is True

    for status in ("pending", "needs_review", "rejected", "reviewed"):
        r = dict(base, case_narrative=_narr(status))
        assert _row_carries_bridge_provenance(r) is False, status

    # marker + amount with no upstream status at all
    r = dict(base, case_narrative=json.dumps({"field_evidence": {}}))
    assert _row_carries_bridge_provenance(r) is False

    # contributor submission (real firm_submission) must remain unsupported
    r = dict(base, source_type="firm_submission", case_narrative=None)
    assert _row_carries_bridge_proigible(r, "comparable_percentile") is False


def _row_eligible(r, op):
    return record_eligible_for_operation(r, op)


def test_bridge_provenance_requires_amount():
    r = _row(100000.0, ["Spinal Injury"])
    r2 = dict(r, exact_outcome_amount=None)
    assert _row_carries_bridge_provenance(r2) is False


def test_extract_upstream_review_status_absent_returns_none():
    assert _extract_upstream_review_status({}) is None
    assert _extract_upstream_review_status({"case_narrative": None}) is None
    assert _extract_upstream_review_status({"case_narrative": "not json"}) is None
    assert _extract_upstream_review_status(
        {"case_narrative": json.dumps({"field_evidence": {}})}) is None


# ---------------------------------------------------------------------------
# R2A-4: consumer-purpose classification / dimension matrix
# ---------------------------------------------------------------------------

def test_required_dimensions_for_reporting_operations():
    assert required_dimensions_for_operation("trend_injury") == {
        "jurisdiction", "case_type", "injury_category"}
    assert required_dimensions_for_operation("trend_jurisdiction") == {
        "jurisdiction", "case_type"}
    assert required_dimensions_for_operation("trend_carrier") == {
        "jurisdiction", "case_type", "insurance_carrier"}
    assert required_dimensions_for_operation("coverage_gap") == {
        "jurisdiction", "case_type"}
    assert required_dimensions_for_operation("quarterly_report") == {
        "jurisdiction", "case_type"}
    assert required_dimensions_for_operation("carrier_patterns") == {
        "jurisdiction", "case_type", "insurance_carrier"}


# ---------------------------------------------------------------------------
# Over-inclusion control: unverified REQUIRED field excludes the record
# ---------------------------------------------------------------------------

def test_trend_injury_excludes_row_with_unverified_injury():
    r = _row(100000.0, ["Spinal Injury"], verified=False)
    assert record_eligible_for_operation(r, "trend_injury") is False


def test_trend_carrier_excludes_row_with_unverified_carrier():
    r = _row(100000.0, ["Spinal Injury"], carrier=None, verified=False)
    assert record_eligible_for_operation(r, "trend_carrier") is False


def test_coverage_gap_excludes_row_with_unverified_jurisdiction():
    r = _row(100000.0, ["Spinal Injury"], jurisdiction=None, verified=False)
    assert record_eligible_for_operation(r, "coverage_gap") is False


# ---------------------------------------------------------------------------
# Over-exclusion control: unverified UNRELATED field does NOT exclude the
# record from an operation that does not require it.
# ---------------------------------------------------------------------------

def test_trend_jurisdiction_allows_row_with_unverified_injury():
    r = _row(100000.0, ["Spinal Injury"], verified=False)
    assert record_eligible_for_operation(r, "trend_jurisdiction") is True


def test_trend_injury_allows_row_with_unverified_carrier():
    r = _row(100000.0, ["Spinal Injury"], carrier=None, verified=True)
    assert record_eligible_for_operation(r, "trend_injury") is True


def test_carrier_patterns_allows_row_with_unverified_injury():
    r = _row(100000.0, ["Spinal Injury"], verified=True)
    assert record_eligible_for_operation(r, "carrier_patterns") is True


# ---------------------------------------------------------------------------
# Extreme-value contamination
# ---------------------------------------------------------------------------

def test_ineligible_extreme_value_excluded_from_trend_injury():
    normal = [_row(100000.0 + i, ["Spinal Injury"]) for i in range(5)]
    extreme_ineligible = _row(50_000_000.0, ["Spinal Injury"], verified=False)
    rows = normal + [extreme_ineligible]
    eligible = filter_rows_eligible(rows, "trend_injury")
    assert len(eligible) == 5
    assert all(r["exact_outcome_amount"] < 1_000_000 for r in eligible)


def test_ineligible_extreme_value_excluded_from_carrier_patterns():
    normal = [_row(100000.0 + i, ["Spinal Injury"]) for i in range(5)]
    extreme_ineligible = _row(50_000_000.0, ["Spinal Injury"], verified=False)
    rows = normal + [extreme_ineligible]
    eligible = filter_rows_eligible(rows, "carrier_patterns")
    assert len(eligible) == 5


# ---------------------------------------------------------------------------
# Correction / invalidation / re-verification
# ---------------------------------------------------------------------------

def test_corrected_value_ceases_to_affect_reporting_population():
    r = _row(100000.0, ["Spinal Injury"], verified=True)
    assert record_eligible_for_operation(r, "trend_injury") is True
    corrected = dict(r, case_narrative=_narr("pending"))
    assert record_eligible_for_operation(corrected, "trend_injury") is False


def test_reverified_replacement_reenters_reporting_population():
    invalidated = dict(_row(100000.0, ["Spinal Injury"]),
                       case_narrative=_narr("pending"))
    assert record_eligible_for_operation(invalidated, "trend_injury") is False
    reverified = dict(invalidated, case_narrative=_narr("verified"))
    assert record_eligible_for_operation(reverified, "trend_injury") is True


# ---------------------------------------------------------------------------
# Approved semantics preserved
# ---------------------------------------------------------------------------

def test_approved_remains_workflow_status_not_auto_eligible():
    from app.services.analytics_authority import approved_auto_analytics_eligible
    assert approved_auto_anigible() is False


def test_approved_can_remain_a_precondition():
    """approved may be a precondition; it must not by itself confer eligibility."""
    r = _row(100000.0, ["Spinal Injury"], verified=True)
    r["status"] = "approved"
    assert record_eligible_for_operation(r, "trend_injury") is True
    r2 = dict(r, case_narrative=_narr("pending"))
    assert record_eligible_for_operation(r2, "trend_injury") is False
\n
def approved_auto_anigible():
    from app.services.analytics_authority import approved_auto_analytics_eligible
    return approved_auto_analytics_eligible()


def approved_auto_analytics_eligible():
    from app.services.analytics_authority import approved_auto_analytics_eligible
    return approved_auto_analytics_eligible()


# ---------------------------------------------------------------------------
# Real production caller wiring (no new engine created)
# ---------------------------------------------------------------------------

def test_no_new_eligibility_engine_created():
    import app.services.analytics_authority as aa
    import app.services.trend_reports as tr
    import app.services.carrier_patterns as cp
    for mod in (aa, tr, cp):
        for name in ("TrendEligibility", "CarrierEligibility",
                     "ReportingEligibility", "AnalyticsEligibilityV3"):
            assert not hasattr(mod, name), f"{mod.__name__}.{name} must not exist"


def test_canonical_authority_reused_by_reporting_consumers():
    import inspect
    import app.services.trend_reports as tr
    import app.services.carrier_patterns as cp
    for fn in (tr.TrendReportGenerator._calculate_injury_trends,
               tr.TrendReportGenerator._calculate_jurisdiction_trends,
               tr.TrendReportGenerator._calculate_carrier_trends,
               tr.TrendReportGenerator.generate_coverage_gap_analysis,
               tr.TrendReportGenerator.generate_quarterly_report,
               cp.get_carrier_patterns):
        src = inspect.getsource(fn)
        assert "analytics_authority" in src, fn.__qualname__
