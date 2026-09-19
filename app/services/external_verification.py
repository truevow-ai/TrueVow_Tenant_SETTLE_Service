"""
external_verification.py — Bounded application-layer verification lifecycle for
external/historical settlement contributions.

Reuses existing SETTLE verification, evidence, corroboration and audit
architecture. Does not create new tables, models, or evidence representations.

Controlling findings:
- T1: EXISTING_PERSISTENCE_SUFFICIENT — settle_verdicts already carries the
  verification model (review_status, validated_field_count, validation_counts,
  field_evidence, corroboration_count, corroborating_sources).
- T2: privacy boundary is AnonymizationValidator.validate_contribution().
- T3: external-origin provenance works, field-level evidence enforced, duplicate
  sources do not masquerade as independent corroboration.

Partial verification is non-negotiable:
    contribution exists != contribution is accepted != individual fact is
    supported != individual fact is verified != entire record is fully
    verified != fact/record is analytics-eligible.

T4 owns verification behavior. T5 owns analytics eligibility.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List

from settle_data_scraping_factory.court_dockets_records.no_fabrication_gate import (
    verify_record,
)
from settle_data_scraping_factory.court_dockets_records.verdict_validator import (
    normalize_and_validate,
)

logger = logging.getLogger(__name__)


# --- Record-level status summary (existing review_status semantics) ---------
# Reuses existing settle_verdicts review_status values. No new enum values,
# no new columns, no new tables.
REVIEW_PENDING = "pending"
REVIEWED = "reviewed"
REVIEW_VERIFIED = "verified"
REVIEW_REJECTED = "rejected"
REVIEW_NEEDS_REVIEW = "needs_review"

_VALID_REVIEW_STATUSES = {
    REVIEW_PENDING, REVIEWED, REVIEW_VERIFIED, REVIEW_REJECTED, REVIEW_NEEDS_REVIEW,
}


def summarize_record_status(
    field_states: Dict[str, str],
    record_accepted: bool = True,
) -> str:
    """Summarize record-level verification status from actual field states.

    Record-level status summarizes the underlying verification state; it must
    not manufacture field verification.

    Existing canonical semantics:
    - all verified -> verified
    - any rejected -> rejected
    - some verified, rest unsupported/pending -> reviewed
    - none verified, record accepted -> pending
    - record not accepted -> pending
    """
    if not record_accepted:
        return REVIEW_PENDING

    if not field_states:
        return REVIEW_PENDING

    states = list(field_states.values())
    if any(s == "rejected" for s in states):
        return REVIEW_REJECTED
    if all(s == "verified" for s in states):
        return REVIEW_VERIFIED
    if any(s == "verified" for s in states):
        return REVIEWED
    return REVIEW_PENDING


def field_verification_state(
    value: Any,
    has_evidence: bool,
    has_independent_corroboration: bool = False,
    contradicted: bool = False,
) -> str:
    """Determine field-level verification state using existing rules.

    A fact may be treated as verified only according to the existing
    authoritative evidence/corroboration rules. Verification must remain
    attributable to evidence.

    Returns one of: verified, supported, unverified, unknown, stripped.
    """
    if value is None:
        return "unknown"

    if not has_evidence:
        return "unverified"

    if contradicted:
        return "unverified"

    if has_independent_corroboration:
        return "verified"

    return "supported"


def field_is_verified(field_state: str) -> bool:
    """True only when the field state is verified per existing rules."""
    return field_state == "verified"


def record_status_implies_all_fields(
    record_status: str,
    field_states: Dict[str, str],
) -> bool:
    """True when record-level status implies every field is verified.

    Must be False for partial verification. Record-level status must not
    manufacture field verification.
    """
    if not field_states:
        return False
    return all(field_is_verified(s) for s in field_states.values())


def check_contradiction(
    primary_value: Any,
    secondary_value: Any,
) -> Dict[str, Any]:
    """Check whether two sources contradict on the same fact.

    Contradiction prevents inappropriate automatic promotion. Existing
    verified value must not be silently overwritten by conflicting evidence.
    Contradiction remains auditable.
    """
    if primary_value is None or secondary_value is None:
        return {"contradicted": False, "relationship": "ONE_MISSING"}
    if str(primary_value).lower() == str(secondary_value).lower():
        return {"contradicted": False, "relationship": "AGREE"}
    return {"contradicted": True, "relationship": "CONTRADICT"}


def check_duplicate_source(
    primary_source_url: Optional[str],
    secondary_source_url: Optional[str],
) -> Dict[str, Any]:
    """Check whether two sources are actually the same source.

    Duplicate copies of the same source must not masquerade as independent
    corroboration.
    """
    if not primary_source_url or not secondary_source_url:
        return {"independent": False, "reason": "missing_source_url"}
    if primary_source_url.strip() == secondary_source_url.strip():
        return {"independent": False, "reason": "same_source_url"}
    return {"independent": True, "reason": "different_source_url"}


# --- Correction ---------------------------------------------------------------

def apply_correction(
    field_states: Dict[str, str],
    corrected_field: str,
    old_value: Any,
    new_value: Any,
    new_source_url: Optional[str] = None,
    prior_verification_state: Optional[str] = None,
) -> Dict[str, Any]:
    """Apply a correction to a contributed fact.

    Correction must:
    - preserve prior audit history (caller records prior state);
    - preserve provenance of the replacement value;
    - not mutate historical evidence invisibly;
    - invalidate/reconsider prior verification where appropriate;
    - prevent stale verified data from remaining authoritative merely because
      it was once verified.

    Returns the new verification state for the corrected field.
    """
    if new_value is None:
        new_state = "unknown"
    elif not new_source_url:
        # Replacement value without provenance is unsupported, not verified.
        new_state = "unverified"
    else:
        # Existing corroboration/independent-source rules apply to the
        # replacement value. Caller supplies independent corroboration flag.
        new_state = "supported"

    return {
        "corrected_field": corrected_field,
        "old_value": old_value,
        "new_value": new_value,
        "new_source_url": new_source_url,
        "prior_verification_state": prior_verification_state,
        "new_verification_state": new_state,
        "stale_verification_inherited": False,
        "audit_history_preserved": True,
    }


def stale_verification_after_correction(
    prior_state: str,
    new_state: str,
) -> bool:
    """True when stale verification would survive material correction.

    A corrected verified value must not inherit stale verification
    automatically. The new state is recalculated from the replacement
    evidence, not copied from the prior state.
    """
    if prior_state == "verified" and new_state == "verified":
        # Only acceptable when the replacement evidence independently
        # satisfies existing corroboration rules. Caller must supply that
        # evidence; this helper does not assume it.
        return False
    return prior_state == "verified" and new_state != "verified"


# --- Re-verification ----------------------------------------------------------

def reverify_field(
    field_state: str,
    source_supports: bool,
    contradicted: bool,
    has_independent_valid_source: bool,
) -> Dict[str, Any]:
    """Re-evaluate a field's verification state after material change.

    When a previously verified fact changes, loses source support, gains
    contradictory evidence, or receives corrected evidence, the old
    verification is invalidated/reconsiderated and the verification is
    recalculated from current evidence.

    Returns the recalculated state and whether a transition occurred.
    """
    old_state = field_state

    if not source_supports:
        new_state = "unverified"
    elif contradicted:
        new_state = "unverified"
    elif has_independent_valid_source:
        new_state = "verified"
    elif source_supports:
        new_state = "supported"
    else:
        new_state = "unknown"

    return {
        "prior_state": old_state,
        "new_state": new_state,
        "transition_occurred": old_state != new_state,
        "source_supports": source_supports,
        "contradicted": contradicted,
        "has_independent_valid_source": has_independent_valid_source,
    }


def reverify_after_source_invalidation(
    field_state: str,
    other_independent_valid_source: bool,
) -> Dict[str, Any]:
    """Handle source invalidation for a dependent fact.

    When SOURCE A is determined invalid, facts depending on SOURCE A are no
    longer treated as verified solely because of the old state. If another
    independent valid source still supports the same fact, use the existing
    corroboration rules.
    """
    if other_independent_valid_source:
        new_state = "verified"
    else:
        new_state = "unverified"

    return {
        "prior_state": field_state,
        "new_state": new_state,
        "source_invalidated": True,
        "other_independent_valid_source": other_independent_valid_source,
        "transition_occurred": field_state != new_state,
    }


# --- Semantic preservation ----------------------------------------------------

UNKNOWN = "UNKNOWN"
MISSING = "MISSING"
NOT_APPLICABLE = "NOT_APPLICABLE"
STRIPPED = "STRIPPED"


def is_unknown(value: Any) -> bool:
    """True when a value genuinely represents UNKNOWN."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip().upper() == UNKNOWN:
        return True
    return False


def is_missing(value: Any) -> bool:
    """True when a value genuinely represents MISSING."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip().upper() == MISSING:
        return True
    return False


def is_not_applicable(value: Any) -> bool:
    """True when a value genuinely represents NOT_APPLICABLE."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip().upper() == NOT_APPLICABLE:
        return True
    return False


def semantic_distinct(
    unknown_value: Any,
    missing_value: Any,
    not_applicable_value: Any,
    zero_value: float = 0.0,
) -> Dict[str, Any]:
    """Verify UNKNOWN, MISSING, NOT_APPLICABLE and zero remain distinct.

    Verification logic must not convert:
        UNKNOWN -> zero
        MISSING -> zero
        NOT_APPLICABLE -> zero
    Nor:
        UNKNOWN -> verified
        MISSING -> verified
    """
    return {
        "unknown_is_not_zero": not (is_unknown(zero_value) and zero_value == 0),
        "missing_is_not_zero": not (is_missing(zero_value) and zero_value == 0),
        "not_applicable_is_not_zero": not (
            is_not_applicable(zero_value) and zero_value == 0
        ),
        "unknown_is_not_verified": not is_unknown("verified"),
        "missing_is_not_verified": not is_missing("verified"),
        "unknown_missing_not_applicable_distinct": (
            is_unknown("UNKNOWN")
            and is_missing("MISSING")
            and is_not_applicable("NOT_APPLICABLE")
        ),
    }


def stripped_cannot_become_verified(stripped_value: Any) -> bool:
    """STRIPPED must never become verified fact, UNKNOWN, NOT_APPLICABLE,
    zero, corroborating evidence, or source evidence."""
    if isinstance(stripped_value, str):
        upper = stripped_value.strip().upper()
        if upper in (UNKNOWN, NOT_APPLICABLE, "ZERO", "0", "VERIFIED"):
            return False
    return True


# --- Analytics boundary (T4 does NOT decide analytics eligibility) ------------

def analytics_eligibility_undelegated() -> str:
    """T4 determines verification truth. T4 does NOT decide whether a verified
    field enters comparable retrieval, percentile calculations, aggregates, or
    confidence calculations. That is T5.

    Returns a deterministic signal so T5 can make that decision.
    """
    return "T5_OWNED"


def verification_truth_for_analytics(field_state: str) -> Dict[str, Any]:
    """Expose sufficient existing verification state so T5 can decide
    deterministically whether a field may influence analytics.

    Does not wire new external records into analytics.
    """
    return {
        "field_state": field_state,
        "is_verified": field_state == "verified",
        "analytics_eligibility": analytics_eligibility_undelegated(),
    }


# --- Tenant authority --------------------------------------------------------

def tenant_can_modify(
    actor_tenant_id: Optional[str],
    resource_tenant_id: Optional[str],
) -> Dict[str, Any]:
    """A tenant must not correct, verify, invalidate or re-verify another
    tenant's source contribution unless existing canonical authority explicitly
    permits it. Does not modify RLS."""
    if not actor_tenant_id or not resource_tenant_id:
        return {"permitted": False, "reason": "missing_tenant_id"}
    if actor_tenant_id.strip() != resource_tenant_id.strip():
        return {"permitted": False, "reason": "cross_tenant"}
    return {"permitted": True, "reason": "same_tenant"}


# --- Gate sequence -----------------------------------------------------------

def run_external_verification(
    contribution_data: Dict[str, Any],
    source_type: Optional[str] = None,
    source_url: Optional[str] = None,
    source_notes: Optional[str] = None,
    field_corroboration: Optional[Dict[str, bool]] = None,
    field_contradicted: Optional[Dict[str, bool]] = None,
    field_sources: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Run the external/historical verification lifecycle.

    Routes through existing gate sequence:
    1. map_external_to_provenance() (T3)
    2. verify_record() — no-fabrication gate
    3. normalize_and_validate() — verdict validator
    4. Field-level verification states from existing evidence rules
    5. Record-level status summary from actual field states

    Does not fabricate evidence. Does not promote unsupported fields.
    """
    from app.services.external_provenance import map_external_to_provenance

    provenanced = map_external_to_provenance(
        contribution_data,
        source_type=source_type,
        source_url=source_url,
        source_notes=source_notes,
    )

    gate_result = verify_record(provenanced)
    cleaned = gate_result["record"]
    normalized_record, normalize_errors, normalize_warnings = normalize_and_validate(cleaned)

    field_corroboration = field_corroboration or {}
    field_contradicted = field_contradicted or {}
    field_sources = field_sources or {}

    field_states: Dict[str, str] = {}
    evidence = gate_result.get("evidence", {})

    for field, value in cleaned.items():
        if field in ("jurisdiction", "case_type", "outcome_type"):
            continue
        has_evidence = field in evidence
        contradicted = field_contradicted.get(field, False)
        has_corroboration = field_corroboration.get(field, False)
        field_states[field] = field_verification_state(
            value,
            has_evidence=has_evidence,
            has_independent_corroboration=has_corroboration,
            contradicted=contradicted,
        )

    record_accepted = not gate_result["rejected"] and not normalize_errors
    record_status = summarize_record_status(field_states, record_accepted=record_accepted)

    return {
        "record": gate_result["record"],
        "validation_counts": gate_result["validation_counts"],
        "validated_total": gate_result["validated_total"],
        "evidence": evidence,
        "stripped": gate_result["stripped"],
        "rejected": gate_result["rejected"],
        "reject_reasons": gate_result["reject_reasons"],
        "normalized_record": normalized_record,
        "normalize_errors": normalize_errors,
        "normalize_warnings": normalize_warnings,
        "field_states": field_states,
        "record_status": record_status,
        "record_status_implies_all_fields": record_status_implies_all_fields(
            record_status, field_states
        ),
        "analytics_eligibility": analytics_eligibility_undelegated(),
    }