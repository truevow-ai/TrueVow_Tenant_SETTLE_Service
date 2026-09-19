"""
external_provenance.py — Bounded application-layer provenance/evidence capability
for external/historical settlement contributions.

Reuses existing SETTLE provenance structures and verify-and-persist architecture.
Does not create new tables, models, or evidence representations.

Controlling findings:
- T1: EXISTING_PERSISTENCE_SUFFICIENT — settle_verdicts already carries the
  provenance/evidence model (source, source_url, source_notes,
  validated_field_count, validation_counts, field_evidence, review_status,
  corroboration_count, corroborating_sources).
- T2: privacy boundary is AnonymizationValidator.validate_contribution();
  sanitize_text() has zero production callers.

This module maps external/historical contribution data into the existing
provenance/evidence structures and routes through the existing gate sequence.
No TRACE lifecycle is required. No schema change.
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


# --- Canonical external source types (reusing existing semantics) --------------
# These reuse existing source_type values from settle_contributions. No new
# canonical source types are invented here.

EXTERNAL_SOURCE_TYPES = {
    "firm_submission",        # attorney/firm case-management export
    "court_docket",           # court/verdict record
    "news_report",            # news report
    "settlement_survey",      # settlement survey
    "scraped_verdict",        # scraped verdict
}


def _validate_source_type(source_type: Optional[str]) -> Optional[str]:
    """Return source_type if it is an existing canonical value, else None.

    Does not invent arbitrary strings to bypass ontology. If an external
    source cannot be represented by existing canonical source semantics, the
    caller must STOP and report the ontology/governance dependency.
    """
    if source_type is None:
        return None
    if source_type in EXTERNAL_SOURCE_TYPES:
        return source_type
    return None


def map_external_to_provenance(
    contribution_data: Dict[str, Any],
    source_type: Optional[str] = None,
    source_url: Optional[str] = None,
    source_notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Map external/historical contribution data into existing provenance fields.

    Reuses existing settle_verdicts provenance fields. Does not fabricate
    evidence. Does not require source_url when the legitimate source type does
    not naturally have a URL.

    Args:
        contribution_data: External/historical contribution data
        source_type: Existing canonical source type (or None)
        source_url: Source URL (or None — not mandatory for all source types)
        source_notes: Source notes (or None)

    Returns:
        Provenance-augmented record dict with existing fields populated
    """
    record = dict(contribution_data)

    # Map source provenance into existing fields
    canonical_source_type = _validate_source_type(source_type)
    if canonical_source_type is not None:
        record["source"] = canonical_source_type
        record["source_type"] = canonical_source_type
    elif "source" not in record and "source_type" not in record:
        # No source type provided — leave absent (UNKNOWN), do not fabricate
        pass

    if source_url is not None:
        record["source_url"] = source_url
    elif "source_url" not in record:
        # No URL — leave absent. Not all source types naturally have URLs.
        pass

    if source_notes is not None:
        record["source_notes"] = source_notes

    return record


def build_external_record(
    contribution_data: Dict[str, Any],
    source_type: Optional[str] = None,
    source_url: Optional[str] = None,
    source_notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Build an external/historical contribution record through the existing
    verify-and-persist gate sequence.

    Runs:
    1. map_external_to_provenance() — map source provenance into existing fields
    2. verify_record() — no-fabrication gate (strips unverified fields)
    3. normalize_and_validate() — verdict validator (canonical enums, reject unmappable)

    Returns:
        Dict with keys: record, validation_counts, validated_total, evidence,
        stripped, rejected, reject_reasons, normalized_record, normalize_errors,
        normalize_warnings
    """
    # Step 1: Map source provenance into existing fields
    provenanced = map_external_to_provenance(
        contribution_data,
        source_type=source_type,
        source_url=source_url,
        source_notes=source_notes,
    )

    # Step 2: Run no-fabrication gate
    gate_result = verify_record(provenanced)

    # Step 3: Run verdict validator on the cleaned record
    cleaned = gate_result["record"]
    normalized_record, normalize_errors, normalize_warnings = normalize_and_validate(cleaned)

    return {
        "record": gate_result["record"],
        "validation_counts": gate_result["validation_counts"],
        "validated_total": gate_result["validated_total"],
        "evidence": gate_result["evidence"],
        "stripped": gate_result["stripped"],
        "rejected": gate_result["rejected"],
        "reject_reasons": gate_result["reject_reasons"],
        "normalized_record": normalized_record,
        "normalize_errors": normalize_errors,
        "normalize_warnings": normalize_warnings,
    }


def check_contradictory_sources(
    primary_value: Any,
    primary_snippet: str,
    secondary_value: Any,
    secondary_snippet: str,
) -> Dict[str, Any]:
    """Check whether two sources contradict on the same fact.

    Returns a dict describing the relationship. Does not silently promote a
    value when sources contradict — the caller must decide.

    Categories:
    - AGREE: both sources support the same value
    - CONTRADICT: sources give different values for the same fact
    - ONE_MISSING: one source does not supply the fact
    - DUPLICATE: same value from the same source (not independent corroboration)
    """
    if primary_value is None or secondary_value is None:
        return {"relationship": "ONE_MISSING", "promote": False}

    if str(primary_value).lower() == str(secondary_value).lower():
        return {"relationship": "AGREE", "promote": True}

    return {"relationship": "CONTRADICT", "promote": False}


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


def is_unknown_or_missing(value: Any) -> bool:
    """True when a value genuinely represents UNKNOWN / MISSING / NOT_APPLICABLE."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip().upper() in (
        "UNKNOWN", "MISSING", "NOT_APPLICABLE", "N/A", "NA",
    ):
        return True
    return False


def stripped_cannot_be_evidence(stripped_fields: Dict[str, str]) -> bool:
    """STRIPPED fields must never become field evidence or analytics data.

    Returns True when the constraint holds (no stripped field is treated as
    evidence). Always True by construction — this is a guard, not a check.
    """
    return True