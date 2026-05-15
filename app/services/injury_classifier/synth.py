"""Pseudo-narrative synthesis from structured fields.

Used when raw narrative text is unavailable (pre-Phase-3.5 state). Concatenates
dropdown enum values into a comma-separated string that the deterministic regex
engine can scan. Lower recall than real-prose classification (no contextual
language) but recovers strong-pattern matches on clinical terms in the
structured fields.

Output is NOT stored in case_narrative — that column is reserved for real prose
from Phase 3.5 narrative acquisition. Pseudo-narratives are runtime-only.
"""
from __future__ import annotations
from typing import Any

# Skip values that are scraper sentinels rather than real classifications
SENTINEL_VALUES = frozenset({
    "Unspecified", "unspecified", "UNSPECIFIED",
    "N/A", "n/a", "Unknown", "unknown",
})


def _stringify_list(val: Any) -> str | None:
    """Convert list-or-string to a comma-joined string, dropping sentinels and empties."""
    if val is None:
        return None
    if isinstance(val, list):
        cleaned = [str(x).strip() for x in val if x and str(x).strip() not in SENTINEL_VALUES]
        return ", ".join(cleaned) if cleaned else None
    s = str(val).strip()
    if not s or s in SENTINEL_VALUES:
        return None
    return s


def synthesize_pseudo_narrative(row: dict) -> str:
    """Construct a pseudo-narrative from a settle_contributions row's structured fields.

    Args:
        row: dict-like with structured-field keys. Missing keys are skipped silently.

    Returns:
        A period-separated phrase string. Empty string if no structured signals available.
    """
    parts: list[str] = []

    # Prefix words ("Injury", "Diagnosis", etc.) are deliberately
    # non-pattern-matching so they don't false-positive any regex rules.

    ic = _stringify_list(row.get("injury_category"))
    if ic:
        parts.append(f"Injury types: {ic}")

    pd = _stringify_list(row.get("primary_diagnosis"))
    if pd:
        parts.append(f"Primary diagnosis: {pd}")

    tt = _stringify_list(row.get("treatment_type"))
    if tt:
        parts.append(f"Treatment: {tt}")

    imf = _stringify_list(row.get("imaging_findings"))
    if imf:
        parts.append(f"Imaging findings: {imf}")

    dc = _stringify_list(row.get("defendant_category"))
    if dc:
        parts.append(f"Defendant category: {dc}")

    ct = _stringify_list(row.get("case_type"))
    if ct:
        parts.append(f"Case type: {ct}")

    if not parts:
        return ""
    return ". ".join(parts) + "."
