"""
verdict_guard.py — Server-side no-fabrication gate for ALL writes to
settle_verdicts (AGENTS.md RULE 0).

This is the app-native twin of
settle_data_scraping_factory/.../no_fabrication_gate.py + verdict_validator.py.
It exists so that NO insert path into settle_verdicts — the scraping bulk-insert
endpoint, manual admin create, or any future path — can write a value that is
not (a) a valid enum, (b) within plausible bounds, and (c) for evidence-bearing
fields, backed by a verbatim source snippet + source_url.

A record that cannot satisfy the identity/provenance floor is REJECTED.
Individual fields that are not verbatim-backed are STRIPPED (never guessed).
Nothing is fabricated to make a record "look" complete.

Use:
    clean, errors = guard_verdict_record(record)   # clean is None if rejected
"""

from __future__ import annotations

import re
from typing import Any, Optional, Tuple

# --- DB canonical vocabularies (mirror app/models/verdicts.py) --------------
_OUTCOME_TYPES = {"verdict_plaintiff", "verdict_defense", "settlement", "dismissed",
                  "Settlement", "Jury Verdict", "Arbitration Award", "Mediation",
                  "Judge's Decision"}
_LIABILITY_TIERS = {"clear", "contested", "shared", "unknown"}
_AGE_RANGES = {"under_18", "18_30", "31_45", "46_60", "61_75", "75_plus"}
_REVIEW_STATUSES = {"pending", "reviewed", "verified", "rejected"}

_AMOUNT_MIN = 100.0
_AMOUNT_MAX = 1_000_000_000.0

# Evidence-bearing fields: if present, the value must appear verbatim in a
# stored snippet (field_evidence[field].snippet) AND carry a source_url.
_EVIDENCE_FIELDS = {
    "medical_bills", "economic_damages", "non_economic_damages", "punitive_damages",
    "total_verdict", "settlement_amount", "judge_name", "insurance_carrier",
    "plaintiff_age_range", "trial_duration_days", "verdict_date", "filing_date",
    "comparative_negligence_pct", "defendant_category", "liability_tier",
}

_AGE_BUCKET_BOUNDS = {
    "under_18": (0, 17), "18_30": (18, 30), "31_45": (31, 45),
    "46_60": (46, 60), "61_75": (61, 75), "75_plus": (75, 120),
}


def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _digits_in(value: float, snippet: str) -> bool:
    iv = int(value)
    forms = {f"{iv:,}", str(iv)}
    if iv >= 1_000_000 and iv % 100_000 == 0:
        forms.add(f"{iv/1_000_000:g} million")
    low = snippet.lower()
    return any(f.lower() in low for f in forms)


def _value_backed(field: str, value: Any, snippet: str) -> bool:
    """Is `value` justified verbatim by `snippet`?"""
    if not snippet:
        return False
    low = snippet.lower()
    if field in ("medical_bills", "economic_damages", "non_economic_damages",
                 "punitive_damages", "total_verdict", "settlement_amount"):
        n = _num(value)
        return n is not None and _digits_in(n, snippet)
    if field == "plaintiff_age_range":
        b = _AGE_BUCKET_BOUNDS.get(str(value))
        if not b:
            return False
        return any(b[0] <= int(m) <= b[1] for m in re.findall(r"\b(\d{1,3})\b", snippet))
    if field in ("verdict_date", "filing_date"):
        yr = next((p for p in re.findall(r"\d{4}", str(value))), None)
        return bool(yr and yr in snippet)
    if field == "comparative_negligence_pct":
        n = _num(value)
        return n is not None and (str(int(n)) in snippet or str(n) in snippet)
    if field == "trial_duration_days":
        return str(value) in snippet
    # strings: verbatim substring (or a salient token)
    v = str(value).lower()
    if v in low:
        return True
    return any(t in low for t in re.split(r"[\s_]+", v) if len(t) > 3)


def guard_verdict_record(record: dict) -> Tuple[Optional[dict], list[str]]:
    """Return (clean_record | None, errors).

    clean_record is None -> REJECTED (identity/provenance floor not met, or an
    out-of-bounds/invalid-enum HARD failure). Otherwise unverifiable fields are
    stripped and the surviving record is returned.
    """
    errors: list[str] = []
    out = dict(record)
    evidence = out.get("field_evidence") or {}
    src_url = out.get("source_url")

    # --- identity + provenance floor (hard reject) ---
    if not out.get("jurisdiction"):
        errors.append("missing jurisdiction")
    if not out.get("case_type"):
        errors.append("missing case_type")
    if not out.get("outcome_type"):
        errors.append("missing outcome_type")
    if not src_url:
        errors.append("missing source_url (provenance)")

    # --- enum hard gates ---
    if out.get("outcome_type") and out["outcome_type"] not in _OUTCOME_TYPES:
        errors.append(f"invalid outcome_type: {out['outcome_type']!r}")
    if out.get("review_status") and out["review_status"] not in _REVIEW_STATUSES:
        out["review_status"] = "pending"

    # --- amount bounds (hard) ---
    for fld in ("medical_bills", "economic_damages", "non_economic_damages",
                "punitive_damages", "total_verdict", "settlement_amount"):
        if out.get(fld) is not None:
            n = _num(out[fld])
            if n is None:
                out.pop(fld, None)
            elif not (0 <= n <= _AMOUNT_MAX):
                errors.append(f"{fld} out of bounds: {n}")
            else:
                out[fld] = n

    # --- comparative negligence 0-100 (strip if bad) ---
    if out.get("comparative_negligence_pct") is not None:
        n = _num(out["comparative_negligence_pct"])
        if n is None or not (0 <= n <= 100):
            out.pop("comparative_negligence_pct", None)

    if errors:
        return None, errors

    # --- evidence gate: strip any evidence-field not verbatim-backed ---
    validated = 0
    for fld in list(out.keys()):
        if fld not in _EVIDENCE_FIELDS:
            continue
        if out.get(fld) is None:
            continue
        ev = evidence.get(fld) if isinstance(evidence, dict) else None
        snippet = (ev or {}).get("snippet") if isinstance(ev, dict) else None
        field_url = (ev or {}).get("source_url") if isinstance(ev, dict) else None
        field_url = field_url or src_url
        if not snippet or not field_url or not _value_backed(fld, out[fld], snippet):
            # No verbatim evidence -> strip (never keep an unverifiable value).
            out.pop(fld, None)
        else:
            validated += 1

    out["validated_field_count"] = validated
    return out, []
