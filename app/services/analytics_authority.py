"""
analytics_authority.py — single application-level analytics eligibility authority.

Reuses the sound T5 primitives from analytics_eligibility.py and adds the
operation-level required-dimension map used by every production consumer.

PRINCIPLE:
    approved = workflow status (preserved, not redefined)
    analytics eligibility = derived from current verification + operation
                           required dimensions

    approved is NOT automatically analytics-eligible.

T1 proved persistence sufficient. No schema change. No new column. No new
model. One eligibility authority — no second competing engine.
"""

from __future__ import annotations

from typing import Dict, Set, Optional, Any, List

from app.services.analytics_eligibility import MIN_AGGREGATE_N


VERIFIED_STATE = "verified"


# Operation -> required dimensions. Derived from the analytical semantics of
# each production consumer in the accepted dataflow audit. Not invented to
# make filtering easier.
_OPERATION_REQUIRED_DIMENSIONS: Dict[str, Set[str]] = {
    # Estimator path
    "comparable_percentile": {"jurisdiction", "case_type", "settlement_amount"},
    "confidence_calculation": {"jurisdiction", "case_type", "settlement_amount"},
    "multiplier_ranges": {"jurisdiction", "case_type", "medical_bills"},
    "comparable_retrieval": {"jurisdiction", "case_type", "settlement_amount"},
    "county_aggregation": {"jurisdiction", "case_type", "settlement_amount"},
    "state_aggregation": {"jurisdiction", "case_type", "settlement_amount"},
    "overdemand_cliff": {"jurisdiction", "case_type", "injury_category"},
    "outcome_distribution": {"jurisdiction", "case_type", "injury_category"},
    # Trend report path
    "trend_injury": {"jurisdiction", "case_type", "injury_category"},
    "trend_jurisdiction": {"jurisdiction", "case_type"},
    "trend_carrier": {"jurisdiction", "case_type", "insurance_carrier"},
    "coverage_gap": {"jurisdiction", "case_type"},
    "quarterly_report": {"jurisdiction", "case_type"},
    # Carrier pattern path
    "carrier_patterns": {"jurisdiction", "case_type", "insurance_carrier"},
    # Weekly digest path
    "weekly_digest": {"jurisdiction", "case_type"},
    # Admin / dashboard path
    "data_quality_analytics": {"jurisdiction", "case_type"},
    "rich_field_analytics": {"jurisdiction", "case_type"},
    "injury_tag_usage": {"jurisdiction", "case_type"},
    # Reputation path
    "consistency_weight": {"jurisdiction", "case_type"},
    "average_z_score": {"jurisdiction", "case_type"},
    # Anomaly path
    "cell_outlier": {"jurisdiction", "case_type"},
    "comparative_negligence_check": {"jurisdiction", "case_type", "comparative_negligence_pct"},
    "carrier_pattern_check": {"jurisdiction", "case_type", "insurance_carrier"},
    "cross_validation": {"jurisdiction", "case_type", "source_type"},
    # Policy-limit-dependent analysis (explicit separate operation)
    "policy_limit_analysis": {"jurisdiction", "policy_limits", "settlement_amount"},
    # Comparative-fault-dependent analysis
    "comparative_fault_analysis": {"jurisdiction", "comparative_negligence_pct"},
    # Lost-wages-dependent analysis
    "lost_wages_analysis": {"jurisdiction", "lost_wages"},
}


def is_verified(field_state: Optional[str]) -> bool:
    """True only when a field's current state is verified per T4 rules."""
    return field_state == VERIFIED_STATE


def required_dimensions_for_operation(operation: str) -> Set[str]:
    """Return the dimensions an operation actually requires.

    Derived from the analytical semantics of each production consumer.
    Dimensions come from actual code, not invented to make filtering easier.
    """
    return set(_OPERATION_REQUIRED_DIMENSIONS.get(operation, set()))


def operation_is_known(operation: str) -> bool:
    """True when the operation is an existing production consumer."""
    return operation in _OPERATION_REQUIRED_DIMENSIONS


def record_eligible_for_operation(
    field_states: Dict[str, str],
    operation: str,
) -> bool:
    """A record may participate in an operation only when every dimension
    required by that operation is CURRENTLY verified.

    Partially verified records may participate where required dimensions are
    verified; they are excluded where a required dimension is not verified.
    """
    required = required_dimensions_for_operation(operation)
    if not required:
        return False
    for dim in required:
        if not is_verified(field_states.get(dim)):
            return False
    return True


def eligible_population(
    records: List[Dict[str, Any]],
    field_states: Dict[str, str],
    operation: str,
) -> List[Dict[str, Any]]:
    """Filter a population to records eligible for an operation.

    Eligibility filtering happens BEFORE calculation. Ineligible records do
    not alter the analytical result.
    """
    return [
        r for r in records
        if record_eligible_for_operation(field_states, operation)
    ]


def eligible_count(
    records: List[Dict[str, Any]],
    field_states: Dict[str, str],
    operation: str,
) -> int:
    """Count records eligible for an operation.

    MIN_AGGREGATE_N counts the eligible analytical population, not merely
    stored/approved records.
    """
    return len(eligible_population(records, field_states, operation))


def min_n_eligible_population(
    stored_count: int,
    eligible_count: int,
    threshold: int = MIN_AGGREGATE_N,
) -> Dict[str, Any]:
    """MIN-N must operate on the eligible population.

    49 eligible + 1 ineligible = 50 stored must NOT unlock shared analytics.
    """
    stored_unlocks = stored_count >= threshold
    eligible_unlocks = eligible_count >= threshold
    return {
        "stored_count": stored_count,
        "eligible_count": eligible_count,
        "threshold": threshold,
        "stored_unlocks_shared_analytics": stored_unlocks,
        "eligible_unlocks_shared_analytics": eligible_unlocks,
        "contamination_present": (
            stored_unlocks and not eligible_unlocks
        ),
    }


def approved_auto_analytics_eligible() -> bool:
    """APPROVED must not be treated as automatically analytics-eligible."""
    return False


def approved_preserved_as_workflow_status() -> bool:
    """APPROVED remains a workflow status. Not redefined, not removed."""
    return True


def field_eligible_for_operation(
    field: str,
    field_state: str,
    operation: str,
) -> bool:
    """A field may influence an operation requiring it only when CURRENTLY
    verified. Unsupported, contradicted, invalidated, stale, STRIPPED and
    other non-verified states must not influence the operation."""
    if field not in required_dimensions_for_operation(operation):
        return False
    return is_verified(field_state)


def confidence_eligibility(
    eligible_count: int,
    ineligible_count: int,
) -> Dict[str, Any]:
    """Ineligible data cannot increase confidence, sample size, confidence
    factors or confidence labels."""
    return {
        "eligible_count": eligible_count,
        "ineligible_count": ineligible_count,
        "confidence_based_on_eligible_population": True,
        "ineligible_increases_confidence": False,
        "ineligible_increases_sample_size": False,
    }


def unknown_as_zero() -> bool:
    """UNKNOWN must not be coerced to zero."""
    return False


def missing_as_zero() -> bool:
    """MISSING must not be coerced to zero."""
    return False


def not_applicable_as_zero() -> bool:
    """NOT_APPLICABLE must not be coerced to zero."""
    return False


def stripped_analytics() -> bool:
    """STRIPPED must never be analytics-eligible."""
    return False


UNKNOWN = "UNKNOWN"
MISSING = "MISSING"
NOT_APPLICABLE = "NOT_APPLICABLE"
STRIPPED = "STRIPPED"


# Fields that participate in analytics eligibility, mapped to their canonical
# settle_contributions column names.
_ANALYTICS_FIELDS = (
    "jurisdiction",
    "case_type",
    "settlement_amount",
    "medical_bills",
    "policy_limits",
    "policy_limit_amount",
    "insurance_carrier",
    "comparative_negligence_pct",
    "injury_category",
    "source_type",
    "lost_wages",
    "defendant_category",
    "outcome_amount_range",
    "exact_outcome_amount",
)


# --- Canonical provenance that the verdict bridge contract projects into
# settle_contributions. settle_contributions has no per-field verification
# state of its own, so state is DERIVED from these.
#
# Source of truth: settle_data_scraping_factory/court_dockets_records/
# bridge_verdicts_to_estimator.py::project() — the only production writer of
# bridged rows. It projects exactly these columns from settle_verdicts rows
# whose review_status is verified, copying values verbatim. Column names are
# the settle_contributions names the bridge writes (e.g. date_of_verdict, not
# the settle_verdicts name verdict_date). Any other writer (contributor.py)
# writes these as NULL and therefore cannot manufacture verification.
_BRIDGED_PROVENANCE_COLUMNS = (
    "jurisdiction",
    "case_type",
    "outcome_type",
    "exact_outcome_amount",
    "medical_bills",
    "insurance_carrier",
    "comparative_negligence_pct",
    "defendant_category",
    "date_of_verdict",
    "case_narrative",
)

# The bridge contract marks bridged rows with source_type='scraped_verdict'
# (bridge_verdicts_to_estimator.py: `_SRC = "scraped_verdict"`). This is the
# canonical marker for "projected from a verified settle_verdicts row".
# It is NOT the same as the contributor-submission source_type 'firm_submission'.
_BRIDGED_SOURCE_TYPE = "scraped_verdict"

# The bridge's defining projection: project() returns None — i.e. the row is
# SKIPPED, never written — unless it has a verified amount. So
# exact_outcome_amount is present on EVERY bridged row and absent from every
# contributor row. It is the strongest single contract-backed discriminator,
# and it is also the dimension the estimator consumes.
_BRIDGED_REQUIRED_COLUMN = "exact_outcome_amount"

# The authoritative verification invariant. project() returns None unless the
# upstream verdict's review_status is exactly this value; the bridge carries it
# inside case_narrative because settle_contributions has no review_status
# column. Trusting the source_type marker alone would let an unreviewed or
# rejected verdict impersonate a verified bridge projection.
_BRIDGED_UPSTREAM_REVIEW_STATUS = "verified"


def _row_carries_bridge_provenance(row: Dict[str, Any]) -> bool:
    """True when a row was projected by the verified verdict bridge contract.

    Requires ALL of:

    1. `source_type == "scraped_verdict"` — the canonical marker the bridge
       contract writes (`bridge_verdicts_to_estimator.py: _SRC`).
    2. `exact_outcome_amount is not None` — the bridge's defining projection.
       `project()` returns None without a verified amount, so this column is
       present on every bridged row and absent from every contributor row.
    3. The authoritative upstream verification invariant is present and equal
       to "verified", carried inside case_narrative as `_review_status`.

    Neither (1) nor (2) alone is sufficient. A contributor row with source_type
    set but no evidence columns must remain unsupported; a marker with no
    evidence behind it cannot manufacture eligibility; and a verdict whose
    upstream review_status is pending/needs_review/rejected must not be
    treated as verified even though it carries the marker and an amount.

    This reads the contract as it is written, not as a prior helper assumed
    it was written. See docs/work-orders/T5_R1_CORE_ESTIMATOR_EVIDENCE.md.
    """
    if row.get("source_type") != _BRIDGED_SOURCE_TYPE:
        return False
    if row.get(_BRIDGED_REQUIRED_COLUMN) is None:
        return False
    upstream = _extract_upstream_review_status(row)
    return upstream == _BRIDGED_UPSTREAM_REVIEW_STATUS


def _extract_upstream_review_status(row: Dict[str, Any]) -> Optional[str]:
    """Read the upstream review_status the bridge embeds in case_narrative.

    The bridge serializes `{"_review_status": v["review_status"], ...}` into
    case_narrative because settle_contributions has no review_status column.
    Returns None when the field is absent or unparseable — never a default.
    """
    narrative = row.get("case_narrative")
    if not isinstance(narrative, str) or not narrative:
        return None
    try:
        import json
        payload = json.loads(narrative)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    status = payload.get("_review_status")
    return status if isinstance(status, str) else None


def field_states_from_row(row: Dict[str, Any]) -> Dict[str, str]:
    """Derive CURRENT field verification states from a settle_contributions row.

    settle_contributions does not carry per-field verification state; state is
    derived from the evidence available on the row.

    Rules:
    - A row projected by the verdict bridge contract carries the provenance
      columns the bridge projects (see _BRIDGED_PROVENANCE_COLUMNS). Its
      analytical dimensions are treated as verified, because the bridge only
      projects rows whose review_status is verified and copies the values
      verbatim from settle_verdicts.
    - Direct external/historical contributions carry no field-level
      verification evidence. Their dimensions are unsupported unless the row
      carries explicit verification provenance.
    - A present value with no verification provenance is unsupported, not
      verified, not zero, not UNKNOWN.

    This is a derivation from row data, not a schema change.
    """
    states: Dict[str, str] = {}
    bridged = _row_carries_bridge_provenance(row)

    for field in _ANALYTICS_FIELDS:
        value = row.get(field)
        if value is None:
            states[field] = "unknown"
            continue

        if bridged:
            # Bridged rows were projected from verified settle_verdicts rows.
            states[field] = VERIFIED_STATE
            continue

        # Direct external/historical contribution: present value but no
        # field-level verification evidence on settle_contributions.
        states[field] = "unsupported"

    # settlement_amount: prefer exact_outcome_amount when present.
    if row.get("exact_outcome_amount") is not None:
        states["settlement_amount"] = (
            VERIFIED_STATE if bridged else "unsupported"
        )

    return states


def row_eligible_for_operation(
    row: Dict[str, Any],
    operation: str,
) -> bool:
    """Convenience: determine eligibility directly from a DB row."""
    return record_eligible_for_operation(
        field_states_from_row(row), operation
    )


def filter_rows_eligible(
    rows: List[Dict[str, Any]],
    operation: str,
) -> List[Dict[str, Any]]:
    """Filter DB rows to those eligible for an operation, before calculation."""
    return [r for r in rows if row_eligible_for_operation(r, operation)]


# ============================================================================
# SEAM A — AUTHENTICATED PROVENANCE RESOLUTION (T5-D3-TDD-001, tracer bullet 1)
# ============================================================================
#
# A contribution may CLAIM an upstream verdict reference. The claim is NOT
# authority. Analytics must independently resolve the claimed reference
# against the CURRENT authoritative settle_verdicts row and verify that the
# projection faithfully matches it before granting any analytical field
# VERIFIED status.
#
# DB lookup is an ADAPTER OUTSIDE this seam. This module never opens a
# database connection. authenticate_projection() receives the CURRENT
# upstream verdict row that an adapter has already resolved.
#
# Reference surface: case_narrative structured JSON, key
# "_upstream_verdict_id". Reserved by bridge_verdicts_to_estimator.py.
#
# Slice 1 scope: settlement amount ONLY. No other analytical field is
# authenticated by this seam. Blanket field verification is the defect this
# exists to remove.

# Reserved reference key inside case_narrative JSON.
UPSTREAM_VERDICT_ID_KEY = "_upstream_verdict_id"

# Canonical marker for a bridge-projected row.
BRIDGED_SOURCE_TYPE = "scraped_verdict"

# Upstream amount selection follows the existing bridge contract
# (bridge_verdicts_to_estimator.py:121): total_verdict OR settlement_amount.
# total_verdict is preferred when present, matching project()'s order.
AMOUNT_SOURCE_FIELDS = ("total_verdict", "settlement_amount")

# Analytical fields that must NEVER be blanket-verified by Seam A.
NOT_AUTHENTICATED_BY_SEAM_A = (
    "jurisdiction",
    "case_type",
    "medical_bills",
    "insurance_carrier",
    "comparative_negligence_pct",
    "injury_category",
    "defendant_category",
)


class AuthorityContext:
    """Authenticated projection result.

    Owns origin/content/evidence validation for one contribution. Built from
    the CURRENT authoritative upstream verdict row by an adapter outside
    this seam. Pure predicates in Seam B consume this, never a DB handle.
    """

    def __init__(
        self,
        authenticated: bool,
        field_states: Dict[str, str],
        reason: str = "",
    ):
        self.authenticated = authenticated
        self.field_states = field_states
        self.reason = reason


def _extract_upstream_reference(contribution: Dict[str, Any]) -> Optional[str]:
    """Read the claimed upstream verdict id from case_narrative JSON.

    Returns None when absent or unparseable. Never a default.
    """
    narrative = contribution.get("case_narrative")
    if not isinstance(narrative, str) or not narrative:
        return None
    try:
        import json
        payload = json.loads(narrative)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get(UPSTREAM_VERDICT_ID_KEY)
    return value if isinstance(value, str) and value else None


def select_authoritative_amount(
    upstream: Dict[str, Any],
) -> Optional[tuple]:
    """Select the authoritative outcome amount and its source field.

    bridge_verdicts_to_estimator.py:121 — `total_verdict OR settlement_amount`.
    total_verdict is preferred when present, matching project()'s order. No
    zero/default behavior. Returns (amount, source_field) or None when no
    authoritative amount exists or it is not positive. One selection, so the
    amount and the field it came from cannot drift apart.
    """
    for field in AMOUNT_SOURCE_FIELDS:
        value = upstream.get(field)
        if value is None:
            continue
        try:
            amount = float(value)
        except (TypeError, ValueError):
            continue
        if amount > 0:
            return amount, field
    return None


def _field_evidence_supports(upstream: Dict[str, Any], field: str) -> bool:
    """True when the upstream verdict carries field_evidence for `field`.

    Per-field evidence is the real authority. Record-level review_status is
    NOT projected onto every field.

    Evidence must satisfy the repository's canonical verdict evidence
    contract (app/services/verdict_guard.py): the entry must carry a
    source_url and a snippet, and the authoritative value must appear
    VERBATIM in that snippet. A truthy source_url plus a truthy snippet is a
    convenient JSON shape, not evidence — so shape alone must not grant
    field authority.
    """
    evidence = upstream.get("field_evidence")
    if not isinstance(evidence, dict) or not evidence:
        return False
    entry = evidence.get(field)
    if not isinstance(entry, dict):
        return False
    snippet = entry.get("snippet")
    source_url = entry.get("source_url")
    if not source_url or not snippet:
        return False
    # Reuse the repository's own value-backed rule rather than inventing a
    # third evidence contract. verdict_guard imports only re/typing, so there
    # is no import cycle.
    from app.services.verdict_guard import _value_backed

    return _value_backed(field, entry.get("value"), snippet)


def authenticate_projection(
    contribution: Dict[str, Any],
    upstream: Dict[str, Any],
) -> AuthorityContext:
    """Seam A: authenticate a contribution's claimed upstream verdict.

    Fails closed. Any of these conditions fails authentication:

    - no upstream row;
    - claimed verdict id does not match the resolved upstream id;
    - upstream review_status != "verified";
    - contribution source_type is not the bridge marker;
    - authoritative amount is absent or not positive;
    - contribution exact_outcome_amount does not match authoritative amount;
    - upstream field_evidence does not support the authoritative amount.

    Slice 1 scope: settlement amount ONLY. All other analytical fields are
    explicitly NOT authenticated.
    """
    states: Dict[str, str] = {}

    claimed_id = _extract_upstream_reference(contribution)

    # 1. A claimed reference must resolve to a real CURRENT upstream row.
    if upstream is None:
        return AuthorityContext(
            authenticated=False,
            field_states=states,
            reason="no_upstream_row",
        )
    upstream_id = upstream.get("id")
    if not upstream_id:
        return AuthorityContext(
            authenticated=False,
            field_states=states,
            reason="upstream_row_has_no_id",
        )
    if claimed_id is None:
        return AuthorityContext(
            authenticated=False,
            field_states=states,
            reason="no_claimed_upstream_reference",
        )
    if claimed_id != upstream_id:
        return AuthorityContext(
            authenticated=False,
            field_states=states,
            reason="claimed_reference_does_not_match_upstream",
        )

    # 2. Upstream must be verified and analytics-eligible.
    if upstream.get("review_status") != _BRIDGED_UPSTREAM_REVIEW_STATUS:
        return AuthorityContext(
            authenticated=False,
            field_states=states,
            reason="upstream_not_verified",
        )

    # 3. The contribution must carry the canonical bridge marker.
    if contribution.get("source_type") != BRIDGED_SOURCE_TYPE:
        return AuthorityContext(
            authenticated=False,
            field_states=states,
            reason="source_type_not_bridge_marker",
        )

    # 4. Authoritative amount per the bridge contract. One selection returns
    #    both the amount and the upstream field it came from, so the two
    #    cannot drift apart.
    selected = select_authoritative_amount(upstream)
    if selected is None:
        return AuthorityContext(
            authenticated=False,
            field_states=states,
            reason="no_authoritative_amount",
        )
    authoritative_amount, amount_field = selected

    # 5. The projection must faithfully match the authoritative amount.
    contribution_amount = contribution.get("exact_outcome_amount")
    try:
        contribution_amount = float(contribution_amount)
    except (TypeError, ValueError):
        return AuthorityContext(
            authenticated=False,
            field_states=states,
            reason="contribution_amount_not_numeric",
        )
    if contribution_amount != authoritative_amount:
        return AuthorityContext(
            authenticated=False,
            field_states=states,
            reason="amount_mismatch",
        )

    # 6. Upstream field_evidence must support the authoritative amount field.
    if not _field_evidence_supports(upstream, amount_field):
        return AuthorityContext(
            authenticated=False,
            field_states=states,
            reason="field_evidence_missing_for_amount",
        )

    # Authenticated. settlement_amount is the ONLY field verified in slice 1.
    states["settlement_amount"] = VERIFIED_STATE

    # Explicitly fail closed for every other analytical field. No blanket
    # verification, no inference from authentication.
    for field in NOT_AUTHENTICATED_BY_SEAM_A:
        states[field] = "unsupported"

    return AuthorityContext(
        authenticated=True,
        field_states=states,
        reason="authenticated_settlement_amount",
    )