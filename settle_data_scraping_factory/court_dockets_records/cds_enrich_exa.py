"""
cds_enrich_exa.py — Exa-based news enrichment for verdict candidates.

Uses Exa AI Search to find news articles and legal coverage about specific
verdicts/settlements, then regex-extracts fields that are rarely present in
appellate opinions: insurance carrier, medical expenses, lost wages,
plaintiff age (from news), expert witness details, and itemized damages.

Requires: EXA_API_KEY in .env.local (or env var)
Install:  pip install exa-py==2.14.0

Usage:
    python cds_enrich_exa.py --in out/cap_crawl_california/cap_california_accepted_enriched.jsonl --dry-run
    python cds_enrich_exa.py --in out/cap_crawl_california/cap_california_accepted_enriched.jsonl --max 50
    python cds_enrich_exa.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv(".env.local")

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from _common.enrich import (  # noqa: E402
    _INSURANCE_RE, _MEDICAL_BILLS_RE, _LOST_WAGES_RE,
    _PLAINTIFF_AGE_RE, _AGE_YEARS_OLD_RE, _AGE_OF_RE,
    _TRIAL_DURATION_RE, _EXPERT_RE,
    _EXPERT_PLAINTIFF_RE, _EXPERT_DEFENSE_RE, _ECONOMIC_RE,
    _NONECONOMIC_RE, _PUNITIVE_RE,
    _best_amount, extract_carrier,
)

EXA_API_KEY = os.getenv("EXA_API_KEY", "")
EXA_DELAY = 0.5
MAX_RESULTS = 5


def _get_exa():
    from exa_py import Exa
    return Exa(api_key=EXA_API_KEY)


def build_query(c: dict) -> str:
    """Build a targeted search query from case metadata."""
    parts = []
    name = c.get("case_name", "")
    if name:
        parts.append(name)
    state = c.get("state", "")
    if state:
        parts.append(f"{state}")
    injury = c.get("injury_category", [])
    if injury:
        parts.append(" ".join(injury))
    case_type = c.get("case_type", "")
    if case_type and case_type != "personal_injury_general":
        parts.append(case_type.replace("_", " "))
    amount = c.get("exact_outcome_amount")
    if amount:
        parts.append(f"${int(amount):,}")
    parts.extend(["jury verdict", "settlement", "personal injury lawsuit"])
    return " ".join(parts)


def search_news(c: dict, max_results: int = MAX_RESULTS) -> list[str]:
    """Search Exa for news about this case. Returns list of highlight strings."""
    if not EXA_API_KEY:
        return []
    query = build_query(c)
    try:
        exa = _get_exa()
        results = exa.search(
            query,
            type="auto",
            num_results=max_results,
            contents={"highlights": True},
        )
        highlights: list[str] = []
        for r in results.results:
            if r.highlights:
                highlights.extend(r.highlights)
            if r.text and len(highlights) < max_results * 3:
                highlights.append(r.text[:2000])
        return highlights
    except Exception:
        return []


def enrich_exa(c: dict, highlights: Optional[list[str]] = None) -> dict:
    """Enrich a candidate with Exa-sourced fields. Returns dict of new fields."""
    if highlights is None:
        highlights = search_news(c)
    if not highlights:
        return {}

    all_text = "\n".join(highlights)
    enriched = {}

    if not c.get("medical_bills"):
        med_val, med_snip = _best_amount(all_text, _MEDICAL_BILLS_RE)
        if med_val:
            enriched["medical_bills"] = med_val
            enriched["exa_medical_bills_snippet"] = med_snip[:200]

    if not c.get("lost_wages"):
        lw_val, lw_snip = _best_amount(all_text, _LOST_WAGES_RE)
        if lw_val:
            enriched["lost_wages"] = lw_val
            enriched["exa_lost_wages_snippet"] = lw_snip[:200]

    econ_val, econ_snip = _best_amount(all_text, _ECONOMIC_RE)
    if econ_val and not c.get("economic_damages"):
        enriched["economic_damages"] = econ_val
        enriched["exa_economic_snippet"] = econ_snip[:200]

    ne_val, ne_snip = _best_amount(all_text, _NONECONOMIC_RE)
    if ne_val and not c.get("non_economic_damages"):
        enriched["non_economic_damages"] = ne_val
        enriched["exa_noneconomic_snippet"] = ne_snip[:200]

    pun_val, pun_snip = _best_amount(all_text, _PUNITIVE_RE)
    if pun_val and not c.get("punitive_damages"):
        enriched["punitive_damages"] = pun_val
        enriched["exa_punitive_snippet"] = pun_snip[:200]

    if not c.get("insurance_carrier"):
        carrier = extract_carrier(all_text)
        if carrier:
            enriched["insurance_carrier"] = carrier
            ins_ctx = _INSURANCE_RE.search(all_text)
            if ins_ctx:
                enriched["exa_insurance_snippet"] = ins_ctx.group(0)[:200]

    if not c.get("plaintiff_age_range"):
        age_m = _PLAINTIFF_AGE_RE.search(all_text)
        if age_m is None:
            age_m = _AGE_YEARS_OLD_RE.search(all_text)
        if age_m is None:
            age_m = _AGE_OF_RE.search(all_text)
        if age_m:
            try:
                age = int(age_m.group(1))
                if 0 < age < 120:
                    if age < 18:
                        enriched["plaintiff_age_range"] = "0_17"
                    elif age < 30:
                        enriched["plaintiff_age_range"] = "18_29"
                    elif age < 45:
                        enriched["plaintiff_age_range"] = "30_44"
                    elif age < 60:
                        enriched["plaintiff_age_range"] = "45_59"
                    elif age < 75:
                        enriched["plaintiff_age_range"] = "60_74"
                    else:
                        enriched["plaintiff_age_range"] = "75_plus"
                    enriched["exa_age_snippet"] = age_m.group(0)[:200]
            except (ValueError, IndexError):
                pass

    if not c.get("trial_duration_days"):
        td_m = _TRIAL_DURATION_RE.search(all_text)
        if td_m:
            days = int(td_m.group(1))
            if 0 < days < 1000:
                enriched["trial_duration_days"] = days

    if not c.get("expert_witnesses_plaintiff") or not c.get("expert_witnesses_defense"):
        all_experts = len(_EXPERT_RE.findall(all_text))
        if all_experts > 0:
            pl = len(_EXPERT_PLAINTIFF_RE.findall(all_text))
            df = len(_EXPERT_DEFENSE_RE.findall(all_text))
            if pl > 0:
                enriched["expert_witnesses_plaintiff"] = pl
            if df > 0:
                enriched["expert_witnesses_defense"] = df
            if pl == 0 and df == 0:
                enriched["expert_witnesses_plaintiff"] = max(1, all_experts // 2)
                enriched["expert_witnesses_defense"] = max(1, all_experts - all_experts // 2)

    enriched["_exa_search_used"] = True
    return enriched


def enrich_file_exa(in_path: Path, max_cases: int = 0, dry_run: bool = False) -> dict:
    """Enrich candidates in a JSONL file using Exa news search."""
    if not EXA_API_KEY:
        return {"error": "EXA_API_KEY not set", "input_file": str(in_path)}

    rows = []
    for line in in_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

    if max_cases > 0:
        rows = rows[:max_cases]

    enriched_rows = []
    enriched_count = 0
    new_field_count = 0

    for i, c in enumerate(rows):
        highlights = search_news(c)
        if highlights:
            new_fields = enrich_exa(c, highlights)
            if new_fields:
                enriched_count += 1
                new_field_count += len([k for k in new_fields if not k.startswith("_") and not k.startswith("exa_")])
                c.update(new_fields)
        enriched_rows.append(c)
        if highlights:
            time.sleep(EXA_DELAY)
        if (i + 1) % 20 == 0:
            print(f"  ... {i+1}/{len(rows)} processed, {enriched_count} enriched so far")
            sys.stdout.flush()

    out_path = in_path.with_name(in_path.stem.replace("_enriched", "") + "_exa_enriched.jsonl" if "_enriched" in in_path.stem else in_path.stem + "_exa.jsonl")
    if dry_run:
        out_path = in_path.with_suffix(".exa_dry.jsonl")

    out_path.write_text("\n".join(json.dumps(r, default=str) for r in enriched_rows), encoding="utf-8")

    return {
        "input_file": str(in_path),
        "output_file": str(out_path),
        "total_rows": len(rows),
        "exa_enriched": enriched_count,
        "new_fields_added": new_field_count,
        "mode": "dry_run" if dry_run else "live",
    }


def selftest() -> int:
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    candidate = {
        "case_name": "Smith v. Jones Construction Co.",
        "state": "Florida",
        "case_type": "motor_vehicle_accident",
        "injury_category": ["neck", "back"],
        "exact_outcome_amount": 1250000.0,
    }

    print("Query builder:")
    q = build_query(candidate)
    check("query includes case name", "Smith v. Jones" in q)
    check("query includes state", "Florida" in q)
    check("query includes injury", "neck back" in q)
    check("query includes case type", "motor vehicle accident" in q)

    print("Enrich from mock highlights:")
    mock = [
        "The jury awarded $1,250,000 to the plaintiff, a 42-year-old construction worker. "
        "Medical bills totalled $320,000. Lost wages were $150,000. "
        "The defendant was insured by Progressive Insurance. "
        "After a 10-day trial, the jury found the defendant negligent.",
    ]
    ef = enrich_exa(candidate, highlights=mock)
    check("medical_bills from exa", ef.get("medical_bills") == 320000.0)
    check("lost_wages from exa", ef.get("lost_wages") == 150000.0)
    check("plaintiff_age from exa", ef.get("plaintiff_age_range") == "30_44")
    check("insurance_carrier from exa", ef.get("insurance_carrier") is not None and "Progressive" in str(ef.get("insurance_carrier")))
    check("trial_duration from exa", ef.get("trial_duration_days") == 10)
    check("exa flag set", ef.get("_exa_search_used") is True)

    print("No override of existing fields:")
    pre_filled = dict(candidate, medical_bills=999999.0, insurance_carrier="Geico")
    ef2 = enrich_exa(pre_filled, highlights=mock)
    check("existing medical_bills not overwritten", ef2.get("medical_bills") is None or ef2.get("medical_bills") == 999999.0)
    check("existing insurance not overwritten", ef2.get("insurance_carrier") is None or ef2.get("insurance_carrier") == "Geico")

    if failures:
        print(f"\nRESULT: FAILED ({len(failures)}) -> {failures}")
        return 1
    print("\nRESULT: ALL CHECKS PASSED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Exa news enrichment for verdict candidates")
    ap.add_argument("--in", dest="in_path", help="Input JSONL file (enriched candidates)")
    ap.add_argument("--max", type=int, default=0, help="Max cases to process")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if not args.in_path:
        ap.error("--in required (or --selftest)")

    res = enrich_file_exa(Path(args.in_path), max_cases=args.max, dry_run=args.dry_run)
    print(json.dumps(res, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
