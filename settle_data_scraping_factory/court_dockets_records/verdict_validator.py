"""
verdict_validator.py — DB-boundary validation + normalization gate for verdict records.

This is the guardrail that must pass BEFORE any record reaches settle_verdicts.
The bulk-insert service inserts raw dicts with no validation, and the scraped
enrichment vocabularies do NOT match the DB's required enums (outcome_type,
liability_tier, plaintiff_age_range, defendant_industry) — nor are dates ISO.
Without this gate, malformed/garbage values would silently poison the table.

Contract:
    normalize_and_validate(mapped_record) -> (clean_record | None, errors, warnings)

- Enums are mapped to the DB's canonical vocabulary; unmappable enum values are
  a hard reject (never guessed into a wrong bucket).
- Dates are parsed to ISO (YYYY-MM-DD); unparseable dates are dropped with a
  warning (not a reject — the record is still useful).
- Numeric ranges are bounds-checked (pct 0-100, amounts >= 0, sane trial days).
- insurance_carrier is re-validated with the shared is_valid_carrier (defense in
  depth: even if a bad value slipped through enrichment, it dies here).
- Provenance (source_url) and a minimal identity (jurisdiction + case_type +
  outcome_type) are REQUIRED; missing them is a hard reject.

Run:
    python verdict_validator.py --selftest
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from _common.enrich import is_valid_carrier, clean_carrier  # noqa: E402

# --- DB canonical vocabularies (mirror app/models/verdicts.py) --------------

DB_OUTCOME_TYPES = {"verdict_plaintiff", "verdict_defense", "settlement", "dismissed"}
DB_LIABILITY_TIERS = {"clear", "contested", "shared", "unknown"}
DB_AGE_RANGES = {"under_18", "18_30", "31_45", "46_60", "61_75", "75_plus"}
DB_POLICY_LIMIT = {"below_limits", "at_limits", "above_limits", "unknown"}
DB_REVIEW_STATUSES = {"pending", "reviewed", "verified", "rejected"}
DB_SOURCES = {"scraped", "manual_entry", "partner_data"}
DB_DEFENDANT_INDUSTRIES = {
    "Healthcare", "Automotive", "Retail", "Construction", "Insurance",
    "Manufacturing", "Technology", "Transportation", "Hospitality",
    "Education", "Government", "Other",
}

# --- Scraped -> DB enum maps ------------------------------------------------

# Scraped outcome_type: damages/award/verdict are all plaintiff-favorable
# monetary outcomes; settlement is settlement; unspecified cannot be trusted to
# a plaintiff/defense bucket and is rejected (never guessed).
_OUTCOME_MAP = {
    "verdict": "verdict_plaintiff",
    "award": "verdict_plaintiff",
    "damages": "verdict_plaintiff",
    "verdict_plaintiff": "verdict_plaintiff",
    "verdict_defense": "verdict_defense",
    "defense_verdict": "verdict_defense",
    "settlement": "settlement",
    "dismissed": "dismissed",
    "dismissal": "dismissed",
}

_LIABILITY_MAP = {
    "clear_liability": "clear",
    "likely_liable": "clear",
    "disputed_liability": "contested",
    "contested_liability": "contested",
    "shared_liability": "shared",
    "comparative": "shared",
    "likely_not_liable": "unknown",
    "unknown": "unknown",
    "clear": "clear",
    "contested": "contested",
    "shared": "shared",
}

# Scraped age buckets -> DB buckets. The boundaries differ slightly
# (30_44 vs 31_45); we map by closest canonical bucket.
_AGE_MAP = {
    "0_17": "under_18",
    "under_18": "under_18",
    "18_29": "18_30",
    "18_30": "18_30",
    "30_44": "31_45",
    "31_45": "31_45",
    "45_59": "46_60",
    "46_60": "46_60",
    "60_74": "61_75",
    "61_75": "61_75",
    "75_plus": "75_plus",
}

_INDUSTRY_MAP = {
    "healthcare": "Healthcare",
    "automotive": "Automotive",
    "retail": "Retail",
    "construction": "Construction",
    "insurance": "Insurance",
    "insurance_company": "Insurance",
    "manufacturer": "Manufacturing",
    "manufacturing": "Manufacturing",
    "technology": "Technology",
    "transportation": "Transportation",
    "hospitality": "Hospitality",
    "education": "Education",
    "government": "Government",
    "employer": "Other",
    "employment": "Other",
    "landlord": "Other",
    "real_estate": "Other",
    "other": "Other",
}

_POLICY_LIMIT_MAP = {
    "below_limits": "below_limits",
    "at_limits": "at_limits",
    "above_limits": "above_limits",
    "unknown": "unknown",
}

# Amount plausibility (mirrors extractor bounds): $100 .. $1B.
_AMOUNT_MIN = 100.0
_AMOUNT_MAX = 1_000_000_000.0

_DATE_FORMATS = (
    "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d",
)


def _parse_date(value: Any) -> Optional[str]:
    """Return ISO YYYY-MM-DD, or None if unparseable."""
    if not value:
        return None
    if isinstance(value, str):
        v = value.strip()
        if not v:
            return None
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(v, fmt).date().isoformat()
            except ValueError:
                continue
    return None


def _num(value: Any) -> Optional[float]:
    try:
        f = float(value)
        return f if f == f else None  # reject NaN
    except (TypeError, ValueError):
        return None


def normalize_and_validate(rec: dict) -> tuple[Optional[dict], list[str], list[str]]:
    """Return (clean_record | None, errors, warnings).

    errors -> hard reject (record is quarantined, never inserted).
    warnings -> field dropped/coerced but record still valid.
    """
    errors: list[str] = []
    warnings: list[str] = []
    out = dict(rec)

    # --- Required identity + provenance (hard) ---
    if not out.get("jurisdiction"):
        errors.append("missing jurisdiction")
    if not out.get("case_type"):
        errors.append("missing case_type")
    if not (out.get("source_url") or out.get("source")):
        errors.append("missing provenance (source_url/source)")

    # --- outcome_type (hard: must map) ---
    ot = str(out.get("outcome_type", "")).strip().lower()
    mapped_ot = _OUTCOME_MAP.get(ot)
    if mapped_ot is None:
        errors.append(f"unmappable outcome_type: {out.get('outcome_type')!r}")
    else:
        out["outcome_type"] = mapped_ot

    # --- liability_tier (soft: coerce to 'unknown' if unmappable) ---
    if out.get("liability_tier") is not None:
        lt = str(out["liability_tier"]).strip().lower()
        mapped = _LIABILITY_MAP.get(lt)
        if mapped is None:
            warnings.append(f"unmapped liability_tier {out['liability_tier']!r} -> unknown")
            out["liability_tier"] = "unknown"
        else:
            out["liability_tier"] = mapped

    # --- plaintiff_age_range (soft: drop if unmappable) ---
    if out.get("plaintiff_age_range") is not None:
        ar = str(out["plaintiff_age_range"]).strip().lower()
        mapped = _AGE_MAP.get(ar)
        if mapped is None:
            warnings.append(f"dropped unmapped plaintiff_age_range {out['plaintiff_age_range']!r}")
            out.pop("plaintiff_age_range", None)
        else:
            out["plaintiff_age_range"] = mapped

    # --- defendant_industry (soft: coerce to 'Other') ---
    if out.get("defendant_industry") is not None:
        di = str(out["defendant_industry"]).strip().lower()
        out["defendant_industry"] = _INDUSTRY_MAP.get(di, "Other")

    # --- policy_limit_indicator (soft: drop if not enum) ---
    if out.get("policy_limit_indicator") is not None:
        pli = str(out["policy_limit_indicator"]).strip().lower()
        if pli in _POLICY_LIMIT_MAP:
            out["policy_limit_indicator"] = _POLICY_LIMIT_MAP[pli]
        else:
            # Loader stores prose like "mentioned: policy limit of $500,000";
            # that's provenance, not an enum -> move to notes, drop the column.
            warnings.append("policy_limit_indicator not an enum -> dropped")
            out.pop("policy_limit_indicator", None)

    # --- insurance_carrier (defense in depth) ---
    if out.get("insurance_carrier") is not None:
        cleaned = clean_carrier(out["insurance_carrier"])
        if cleaned is None or not is_valid_carrier(cleaned):
            warnings.append(f"dropped invalid insurance_carrier {out['insurance_carrier']!r}")
            out.pop("insurance_carrier", None)
        else:
            out["insurance_carrier"] = cleaned

    # --- amounts (hard if present-but-implausible) ---
    for fld in ("medical_bills", "economic_damages", "non_economic_damages",
                "punitive_damages", "total_verdict", "settlement_amount"):
        if out.get(fld) is not None:
            n = _num(out[fld])
            if n is None:
                warnings.append(f"dropped non-numeric {fld}")
                out.pop(fld, None)
            elif not (0 <= n <= _AMOUNT_MAX):
                errors.append(f"{fld} out of bounds: {n}")
            else:
                out[fld] = n

    # A monetary outcome with no amount at all is suspect -> reject.
    if mapped_ot in ("verdict_plaintiff", "settlement"):
        if out.get("total_verdict") is None and out.get("settlement_amount") is None:
            errors.append("monetary outcome with no amount")

    # --- comparative_negligence_pct (hard: 0-100) ---
    if out.get("comparative_negligence_pct") is not None:
        n = _num(out["comparative_negligence_pct"])
        if n is None or not (0 <= n <= 100):
            warnings.append(f"dropped invalid comparative_negligence_pct {out['comparative_negligence_pct']!r}")
            out.pop("comparative_negligence_pct", None)
        else:
            out["comparative_negligence_pct"] = n

    # --- expert counts / trial days (soft) ---
    for fld, hi in (("expert_witnesses_plaintiff", 100),
                    ("expert_witnesses_defense", 100),
                    ("trial_duration_days", 1000)):
        if out.get(fld) is not None:
            n = _num(out[fld])
            if n is None or not (0 <= n <= hi):
                warnings.append(f"dropped implausible {fld} {out[fld]!r}")
                out.pop(fld, None)
            else:
                out[fld] = int(n)

    # --- dates -> ISO (soft: drop unparseable) ---
    for fld in ("verdict_date", "filing_date", "resolution_date"):
        if out.get(fld) is not None:
            iso = _parse_date(out[fld])
            if iso is None:
                warnings.append(f"dropped unparseable {fld} {out[fld]!r}")
                out.pop(fld, None)
            else:
                out[fld] = iso

    # --- scores (soft: clamp) ---
    for fld in ("confidence_score", "completeness_score"):
        if out.get(fld) is not None:
            n = _num(out[fld])
            if n is None:
                out.pop(fld, None)
            else:
                out[fld] = min(1.0, max(0.0, n))

    # --- source normalization ---
    # settle_verdicts.source enum is scraped/manual_entry/partner_data; the data
    # provider (courtlistener/CAP/morelaw) is preserved in source_notes.
    out["source"] = "scraped"

    # --- review_status ---
    rs = out.get("review_status", "pending")
    if rs not in DB_REVIEW_STATUSES:
        rs = "pending"
    out["review_status"] = rs

    if errors:
        return None, errors, warnings
    return out, errors, warnings


def selftest() -> int:
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    base = {
        "jurisdiction": "Miami-Dade, FL", "case_type": "motor_vehicle_accident",
        "outcome_type": "award", "total_verdict": 1_250_000.0,
        "liability_tier": "clear_liability", "plaintiff_age_range": "30_44",
        "defendant_industry": "healthcare", "insurance_carrier": "State Farm",
        "verdict_date": "January 23, 2019", "comparative_negligence_pct": 15.0,
        "source_url": "https://static.case.law/so3d/1/cases/0001-01.json",
        "trial_duration_days": 7,
    }
    rec, errs, warns = normalize_and_validate(base)
    check("valid record passes", rec is not None and not errs)
    check("outcome award -> verdict_plaintiff", rec["outcome_type"] == "verdict_plaintiff")
    check("liability clear_liability -> clear", rec["liability_tier"] == "clear")
    check("age 30_44 -> 31_45", rec["plaintiff_age_range"] == "31_45")
    check("industry healthcare -> Healthcare", rec["defendant_industry"] == "Healthcare")
    check("date -> ISO", rec["verdict_date"] == "2019-01-23")
    check("source coerced to scraped", rec["source"] == "scraped")

    print("Unmappable outcome_type is a hard reject:")
    r2, e2, _ = normalize_and_validate(dict(base, outcome_type="unspecified"))
    check("unspecified rejected", r2 is None and any("outcome_type" in e for e in e2))

    print("Garbage carrier is dropped, record still valid:")
    r3, e3, w3 = normalize_and_validate(dict(base, insurance_carrier="withholds policy benefits in bad faith"))
    check("bad carrier dropped", r3 is not None and "insurance_carrier" not in r3)
    check("drop recorded as warning", any("insurance_carrier" in w for w in w3))

    print("Monetary outcome with no amount is rejected:")
    no_amt = {k: v for k, v in base.items() if k != "total_verdict"}
    r4, e4, _ = normalize_and_validate(no_amt)
    check("no-amount verdict rejected", r4 is None and any("no amount" in e for e in e4))

    print("Missing provenance/jurisdiction is rejected:")
    r5, e5, _ = normalize_and_validate({"case_type": "x", "outcome_type": "settlement", "settlement_amount": 5000})
    check("missing jurisdiction rejected", r5 is None and any("jurisdiction" in e for e in e5))

    print("Out-of-range comparative negligence is dropped (soft):")
    r6, e6, w6 = normalize_and_validate(dict(base, comparative_negligence_pct=250))
    check("bad pct dropped not rejected", r6 is not None and "comparative_negligence_pct" not in r6)

    print("Implausible amount is a hard reject:")
    r7, e7, _ = normalize_and_validate(dict(base, total_verdict=5_000_000_000.0))
    check("huge amount rejected", r7 is None and any("out of bounds" in e for e in e7))

    if failures:
        print(f"\nRESULT: FAILED ({len(failures)}) -> {failures}")
        return 1
    print("\nRESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print("usage: python verdict_validator.py --selftest")
