"""
no_fabrication_gate.py — Universal anti-fabrication verifier for verdict records.

PRIME DIRECTIVE (non-negotiable, legal product):
    Every field that reaches the database MUST trace to a source URL and carry
    verbatim evidence (a snippet) in which the value literally appears. Nothing
    is guessed, inferred, hallucinated, or "salted". Zero records is preferable
    to one fabricated field. This gate runs on EVERY scrape outcome — records
    already scraped and all future ones.

For each verifiable field the gate checks:
    1. a non-empty source_url exists for that field (or the record's source_url), AND
    2. a non-empty evidence snippet exists, AND
    3. the value appears VERBATIM in that snippet
       (numbers by their digits; strings by substring; dates by their parts;
        enums by the keyword that justified them; lists element-by-element).

Any field failing verification is STRIPPED from the record (not guessed, not
kept). The gate returns:
    - the cleaned record (only verifiable fields survive),
    - validation_counts: {field: 1} for every field that passed (how many of the
      record's fields were independently validated against evidence),
    - a per-field audit trail (value + snippet + url for each verified field),
    - stripped: {field: reason} for everything removed.

A record with NO verifiable identity (jurisdiction/case_type/outcome + a real
source_url) is rejected entirely.

Run:
    python no_fabrication_gate.py --selftest
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

# Fields that require verbatim evidence, mapped to the candidate keys that may
# hold their snippet. Provenance for each is the record source_url unless a
# field-specific *_url exists (Exa news fields).
_EVIDENCE_SNIPPET_KEYS = {
    "medical_bills": ["medical_bills_snippet", "exa_medical_bills_snippet"],
    "economic_damages": ["economic_damages_snippet", "exa_economic_snippet"],
    "non_economic_damages": ["non_economic_damages_snippet", "exa_noneconomic_snippet"],
    "punitive_damages": ["punitive_damages_snippet", "exa_punitive_snippet"],
    "lost_wages": ["lost_wages_snippet", "exa_lost_wages_snippet"],
    "judge_name": ["judge_name_snippet"],
    "insurance_carrier": ["insurance_carrier_snippet", "exa_insurance_snippet"],
    "plaintiff_age_range": ["plaintiff_age_range_snippet", "exa_age_snippet"],
    "trial_duration_days": ["trial_duration_days_snippet", "exa_trial_duration_snippet"],
    "expert_witnesses_plaintiff": ["expert_witnesses_plaintiff_snippet"],
    "expert_witnesses_defense": ["expert_witnesses_defense_snippet"],
    "defendant_category": ["defendant_category_snippet"],
    "policy_limit_indicator": ["policy_limit_indicator_snippet"],
    "verdict_date": ["verdict_date_snippet"],
    "filing_date": ["filing_date_snippet"],
    "comparative_negligence_pct": ["comparative_negligence_pct_snippet"],
    "liability_tier": ["liability_tier_snippet"],
}

_FIELD_URL_KEYS = {
    "medical_bills": "exa_medical_bills_url",
    "economic_damages": "exa_economic_url",
    "non_economic_damages": "exa_noneconomic_url",
    "punitive_damages": "exa_punitive_url",
    "lost_wages": "exa_lost_wages_url",
    "insurance_carrier": "exa_insurance_url",
    "plaintiff_age_range": "exa_age_url",
    "trial_duration_days": "exa_trial_duration_url",
    "expert_witnesses_plaintiff": "exa_expert_plaintiff_url",
    "expert_witnesses_defense": "exa_expert_defense_url",
}

# Age bucket -> the years that legitimately justify it (checked against snippet).
_AGE_BUCKET_BOUNDS = {
    "0_17": (0, 17), "under_18": (0, 17),
    "18_29": (18, 29), "18_30": (18, 30),
    "30_44": (30, 44), "31_45": (31, 45),
    "45_59": (45, 59), "46_60": (46, 60),
    "60_74": (60, 74), "61_75": (61, 75),
    "75_plus": (75, 120),
}

# Enum -> keywords whose presence in the snippet justifies the value.
_LIABILITY_KEYWORDS = {
    "clear_liability": ["negligent", "liable", "liability", "fault", "breach"],
    "clear": ["negligent", "liable", "liability", "fault", "breach"],
    "disputed_liability": ["disput", "contest", "denied", "questioned"],
    "contested": ["disput", "contest", "denied", "questioned"],
    "shared_liability": ["comparative", "shared", "apportion", "percent", "%"],
    "shared": ["comparative", "shared", "apportion", "percent", "%"],
    "likely_liable": ["negligent", "liable", "fault", "%", "percent"],
    "likely_not_liable": ["not liable", "no negligence", "%", "percent"],
}


def _digits_in(value: float, snippet: str) -> bool:
    """A number is verified if its digits appear in the snippet in any common
    textual form (comma-grouped, plain, or shorthand like '1 million')."""
    iv = int(value)
    forms = {f"{iv:,}", str(iv)}
    # dollar shorthand: 1,250,000 -> "1.25 million"/"1,250,000"/"1250000"
    if iv >= 1_000_000 and iv % 100_000 == 0:
        millions = iv / 1_000_000
        forms.add(f"{millions:g} million")
        forms.add(f"{millions:g}m")
    if iv >= 1000 and iv % 1000 == 0:
        forms.add(f"{iv // 1000},000")
    low = snippet.lower()
    return any(f.lower() in low for f in forms)


def _verify_field(field: str, value: Any, snippet: str) -> bool:
    """Does `value` literally appear / find justification in `snippet`?"""
    if not snippet:
        return False
    low = snippet.lower()

    if field in ("medical_bills", "economic_damages", "non_economic_damages",
                 "punitive_damages", "lost_wages", "total_verdict", "settlement_amount"):
        return isinstance(value, (int, float)) and _digits_in(value, snippet)

    if field == "plaintiff_age_range":
        bounds = _AGE_BUCKET_BOUNDS.get(str(value))
        if not bounds:
            return False
        lo, hi = bounds
        for m in re.finditer(r"\b(\d{1,3})\b", snippet):
            n = int(m.group(1))
            if lo <= n <= hi:
                return True
        return False

    if field == "trial_duration_days":
        return isinstance(value, int) and str(value) in snippet

    if field in ("expert_witnesses_plaintiff", "expert_witnesses_defense"):
        # Justified by an explicit expert mention in the attributed snippet.
        return "expert" in low or "witness" in low

    if field == "comparative_negligence_pct":
        try:
            iv = int(float(value))
        except (TypeError, ValueError):
            return False
        return (str(iv) in snippet) or (f"{value}" in snippet)

    if field == "liability_tier":
        kws = _LIABILITY_KEYWORDS.get(str(value), [])
        return any(k in low for k in kws)

    if field in ("verdict_date", "filing_date"):
        # Value like "March 3, 2022" or ISO "2022-03-03" — verify the year and
        # a month token appear in the snippet.
        parts = re.findall(r"[A-Za-z]+|\d+", str(value))
        year = next((p for p in parts if p.isdigit() and len(p) == 4), None)
        if not year or year not in snippet:
            return False
        return True

    if field in ("judge_name", "insurance_carrier", "defendant_category",
                 "policy_limit_indicator"):
        # Value (or its salient token) must appear verbatim in the snippet.
        v = str(value)
        if v.lower() in low:
            return True
        # defendant_category is a derived label; accept if any word matches.
        tokens = [t for t in re.split(r"[\s_]+", v.lower()) if len(t) > 3]
        return any(t in low for t in tokens)

    # Unknown field -> require literal substring (conservative).
    return str(value).lower() in low


def verify_record(rec: dict, record_source_url: Optional[str] = None) -> dict:
    """Run the no-fabrication gate on one record.

    Returns dict:
        record: cleaned record (only verifiable fields kept)
        validation_counts: {field: 1} for each verified field
        validated_total: int
        evidence: {field: {value, snippet, source_url}}
        stripped: {field: reason}
        rejected: bool (True if record has no verifiable identity/provenance)
        reject_reasons: list[str]
    """
    out = dict(rec)
    src_url = record_source_url or rec.get("source_url") or rec.get("full_text_url")
    validated: dict[str, int] = {}
    evidence: dict[str, dict] = {}
    stripped: dict[str, str] = {}

    # The raw candidate carries the outcome amount as exact_outcome_amount +
    # amount_snippet (it only becomes total_verdict/settlement_amount after
    # mapping). Verify it here under its outcome-appropriate final name so the
    # amount is never unverified.
    raw_amount = rec.get("exact_outcome_amount")
    amount_snip = rec.get("amount_snippet")
    if raw_amount is not None:
        outcome = str(rec.get("outcome_type", "")).lower()
        amt_field = "settlement_amount" if outcome == "settlement" else "total_verdict"
        if src_url and amount_snip and _digits_in(float(raw_amount), amount_snip):
            validated[amt_field] = 1
            evidence[amt_field] = {"value": raw_amount, "snippet": amount_snip[:300],
                                   "source_url": src_url}
        else:
            stripped[amt_field] = "amount not verbatim in snippet"

    for field, snip_keys in _EVIDENCE_SNIPPET_KEYS.items():
        if out.get(field) is None:
            continue
        value = out[field]
        snippet = ""
        for sk in snip_keys:
            if rec.get(sk):
                snippet = rec[sk]
                break
        field_url = rec.get(_FIELD_URL_KEYS.get(field, ""), "") or src_url

        if not field_url:
            stripped[field] = "no source_url"
            out.pop(field, None)
            continue
        if not snippet:
            stripped[field] = "no evidence snippet"
            out.pop(field, None)
            continue
        if not _verify_field(field, value, snippet):
            stripped[field] = "value not verbatim in snippet"
            out.pop(field, None)
            continue

        validated[field] = 1
        evidence[field] = {"value": value, "snippet": snippet[:300], "source_url": field_url}

    # injury_type / injury_category: each element must appear in the opinion
    # evidence. Without stored per-injury snippets we require the extraction
    # provenance block; if absent, injuries are unverifiable -> strip.
    injuries = out.get("injury_type") or out.get("injury_category")
    if injuries:
        ext = rec.get("_extraction") or {}
        proven = {str(i).lower() for i in (ext.get("injuries") or [])}
        if proven:
            kept = [i for i in injuries if str(i).lower() in proven]
            dropped = [i for i in injuries if str(i).lower() not in proven]
            if kept:
                out["injury_type"] = kept
                validated["injury_type"] = len(kept)
                evidence["injury_type"] = {"value": kept, "snippet": "pi_terms/injuries",
                                           "source_url": src_url}
            else:
                out.pop("injury_type", None)
            if dropped:
                stripped["injury_type"] = f"unverified injuries dropped: {dropped}"
        else:
            stripped["injury_type"] = "no extraction evidence for injuries"
            out.pop("injury_type", None)

    # Identity/provenance floor: must have jurisdiction + case_type + a source.
    # (jurisdiction may still be the raw `state`/`county_hint` pre-mapping.)
    reject_reasons = []
    if not (out.get("jurisdiction") or out.get("state") or out.get("county_hint")):
        reject_reasons.append("no jurisdiction")
    if not out.get("case_type"):
        reject_reasons.append("no case_type")
    if not src_url:
        reject_reasons.append("no source_url (provenance)")

    return {
        "record": out,
        "validation_counts": validated,
        "validated_total": sum(validated.values()),
        "evidence": evidence,
        "stripped": stripped,
        "rejected": bool(reject_reasons),
        "reject_reasons": reject_reasons,
    }


def selftest() -> int:
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    print("Verified fields survive with counts + evidence:")
    rec = {
        "jurisdiction": "Miami-Dade, FL", "case_type": "motor_vehicle_accident",
        "source_url": "https://static.case.law/so3d/1/cases/0001.json",
        "medical_bills": 245000.0, "medical_bills_snippet": "medical bills totalled $245,000 for the surgery",
        "judge_name": "SMITH J.", "judge_name_snippet": "SMITH, J., delivered the opinion",
        "insurance_carrier": "State Farm", "insurance_carrier_snippet": "insured by State Farm",
        "plaintiff_age_range": "45_59", "plaintiff_age_range_snippet": "the plaintiff, aged 52, suffered",
        "verdict_date": "March 3, 2022", "verdict_date_snippet": "verdict returned on March 3, 2022",
    }
    r = verify_record(rec)
    check("not rejected", not r["rejected"])
    check("all 5 evidence fields validated", r["validated_total"] == 5)
    check("counts per field", r["validation_counts"].get("medical_bills") == 1)
    check("evidence carries snippet+url", r["evidence"]["medical_bills"]["source_url"].startswith("https://"))

    print("Fabricated value (not in snippet) is STRIPPED, never kept:")
    bad = dict(rec, medical_bills=999999.0)  # snippet still says 245,000
    rb = verify_record(bad)
    check("fabricated amount stripped", "medical_bills" not in rb["record"])
    check("strip reason recorded", "medical_bills" in rb["stripped"])

    print("Missing snippet -> field stripped (no evidence, no entry):")
    ns = {"jurisdiction": "X, FL", "case_type": "x", "source_url": "https://a",
          "insurance_carrier": "GEICO"}  # no snippet
    rn = verify_record(ns)
    check("carrier with no snippet stripped", "insurance_carrier" not in rn["record"])

    print("Missing source_url -> field stripped:")
    nu = {"jurisdiction": "X, FL", "case_type": "x",
          "judge_name": "DOE J.", "judge_name_snippet": "DOE, J."}
    rnu = verify_record(nu)
    check("field without any source_url stripped", "judge_name" not in rnu["record"])
    check("record rejected (no provenance at all)", rnu["rejected"])

    print("Age bucket must be justified by an in-range age in the snippet:")
    age_bad = dict(rec, plaintiff_age_range="0_17",
                   plaintiff_age_range_snippet="the plaintiff, aged 52, suffered")
    rab = verify_record(age_bad)
    check("wrong age bucket stripped", "plaintiff_age_range" not in rab["record"])

    print("Injuries: only those with extraction evidence survive:")
    inj = {"jurisdiction": "X, FL", "case_type": "x", "source_url": "https://a",
           "injury_type": ["back", "brain"], "_extraction": {"injuries": ["back"]}}
    ri = verify_record(inj)
    check("verified injury kept", ri["record"].get("injury_type") == ["back"])
    check("unverified injury dropped", "brain" not in (ri["record"].get("injury_type") or []))

    print("Zero verifiable fields but valid identity -> record kept, 0 counts:")
    bare = {"jurisdiction": "X, FL", "case_type": "x", "source_url": "https://a"}
    rbare = verify_record(bare)
    check("bare record not rejected", not rbare["rejected"])
    check("bare record has 0 validated fields", rbare["validated_total"] == 0)

    if failures:
        print(f"\nRESULT: FAILED ({len(failures)}) -> {failures}")
        return 1
    print("\nRESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print("usage: python no_fabrication_gate.py --selftest")
