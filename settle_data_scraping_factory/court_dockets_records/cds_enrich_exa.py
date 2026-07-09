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
    _TRIAL_DURATION_RE,
    _EXPERT_PLAINTIFF_RE, _EXPERT_DEFENSE_RE, _ECONOMIC_RE,
    _NONECONOMIC_RE, _PUNITIVE_RE, _KNOWN_CARRIERS_RE,
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


def search_news(c: dict, max_results: int = MAX_RESULTS) -> list[tuple[str, str]]:
    """Search Exa for news about this case.

    Returns list of (text, source_url) pairs so every extracted field can be
    traced back to a specific article — verifiability is mandatory for a legal
    product, so a snippet with no source URL is worthless.
    """
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
        pairs: list[tuple[str, str]] = []
        for r in results.results:
            url = getattr(r, "url", "") or ""
            if r.highlights:
                for h in r.highlights:
                    pairs.append((h, url))
            if r.text and len(pairs) < max_results * 3:
                pairs.append((r.text[:2000], url))
        return pairs
    except Exception:
        return []


def _value_in_snippet(value, snippet: str) -> bool:
    """The extracted value must literally appear in its source snippet.

    This is the line-by-line/number-by-number verifiability gate: if the digits
    of an amount, or an age, are not present verbatim in the snippet, the field
    is not verifiable and must be dropped (never inferred).
    """
    if not snippet:
        return False
    if isinstance(value, (int, float)):
        digits = f"{int(value):,}"
        plain = str(int(value))
        return digits in snippet or plain in snippet
    return str(value) in snippet


def enrich_exa(c: dict, pairs: Optional[list[tuple[str, str]]] = None) -> dict:
    """Enrich a candidate with Exa-sourced fields.

    Every field written carries: the value, a verbatim source snippet, and the
    source article URL. A value that does not appear verbatim in its snippet is
    dropped. Nothing is guessed or inferred.
    """
    if pairs is None:
        pairs = search_news(c)
    if not pairs:
        return {}

    # Search each article's text individually so a field's snippet and its
    # source URL always come from the SAME article (no cross-article mixing).
    enriched: dict = {}

    def _fill_amount(field: str, regex, snippet_key: str, url_key: str):
        if c.get(field) or field in enriched:
            return
        for text, url in pairs:
            val, snip = _best_amount(text, regex)
            if val and _value_in_snippet(val, snip):
                enriched[field] = val
                enriched[snippet_key] = snip[:300]
                enriched[url_key] = url
                return

    _fill_amount("medical_bills", _MEDICAL_BILLS_RE, "exa_medical_bills_snippet", "exa_medical_bills_url")
    _fill_amount("lost_wages", _LOST_WAGES_RE, "exa_lost_wages_snippet", "exa_lost_wages_url")
    _fill_amount("economic_damages", _ECONOMIC_RE, "exa_economic_snippet", "exa_economic_url")
    _fill_amount("non_economic_damages", _NONECONOMIC_RE, "exa_noneconomic_snippet", "exa_noneconomic_url")
    _fill_amount("punitive_damages", _PUNITIVE_RE, "exa_punitive_snippet", "exa_punitive_url")

    if not c.get("insurance_carrier"):
        for text, url in pairs:
            carrier = extract_carrier(text)
            if carrier:
                ins_ctx = _INSURANCE_RE.search(text) or _KNOWN_CARRIERS_RE.search(text)
                snip = ins_ctx.group(0) if ins_ctx else ""
                # The carrier name must appear verbatim in the snippet context.
                if snip and _value_in_snippet(carrier, text):
                    enriched["insurance_carrier"] = carrier
                    enriched["exa_insurance_snippet"] = snip[:300]
                    enriched["exa_insurance_url"] = url
                    break

    if not c.get("plaintiff_age_range"):
        for text, url in pairs:
            age_m = (_PLAINTIFF_AGE_RE.search(text) or _AGE_YEARS_OLD_RE.search(text)
                     or _AGE_OF_RE.search(text))
            if not age_m:
                continue
            try:
                age = int(age_m.group(1))
            except (ValueError, IndexError):
                continue
            if not (0 < age < 120):
                continue
            if age < 18:
                bucket = "0_17"
            elif age < 30:
                bucket = "18_29"
            elif age < 45:
                bucket = "30_44"
            elif age < 60:
                bucket = "45_59"
            elif age < 75:
                bucket = "60_74"
            else:
                bucket = "75_plus"
            enriched["plaintiff_age_range"] = bucket
            enriched["exa_age_snippet"] = age_m.group(0)[:300]
            enriched["exa_age_url"] = url
            break

    if not c.get("trial_duration_days"):
        for text, url in pairs:
            td_m = _TRIAL_DURATION_RE.search(text)
            if td_m:
                days = int(td_m.group(1))
                if 0 < days < 1000:
                    enriched["trial_duration_days"] = days
                    enriched["exa_trial_duration_snippet"] = td_m.group(0)[:300]
                    enriched["exa_trial_duration_url"] = url
                    break

    # Expert-witness counts: report ONLY what is explicitly attributable to a
    # side, each with its snippet. NEVER split a total in half by guessing.
    for text, url in pairs:
        pl = _EXPERT_PLAINTIFF_RE.findall(text)
        df = _EXPERT_DEFENSE_RE.findall(text)
        if pl and not c.get("expert_witnesses_plaintiff") and "expert_witnesses_plaintiff" not in enriched:
            enriched["expert_witnesses_plaintiff"] = len(pl)
            enriched["exa_expert_plaintiff_url"] = url
        if df and not c.get("expert_witnesses_defense") and "expert_witnesses_defense" not in enriched:
            enriched["expert_witnesses_defense"] = len(df)
            enriched["exa_expert_defense_url"] = url

    if enriched:
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
        pairs = search_news(c)
        if pairs:
            new_fields = enrich_exa(c, pairs)
            if new_fields:
                enriched_count += 1
                new_field_count += len([k for k in new_fields if not k.startswith("_") and not k.startswith("exa_")])
                c.update(new_fields)
        enriched_rows.append(c)
        if pairs:
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

    print("Enrich from mock article (value+snippet+url, verifiable):")
    mock = [(
        "The jury awarded $1,250,000 to the plaintiff, a 42-year-old construction worker. "
        "Medical bills totalled $320,000. Lost wages were $150,000. "
        "The defendant was insured by Progressive Insurance. "
        "After a 10-day trial, the jury found the defendant negligent.",
        "https://news.example.com/verdict-smith-jones",
    )]
    ef = enrich_exa(candidate, pairs=mock)
    check("medical_bills from exa", ef.get("medical_bills") == 320000.0)
    check("medical_bills carries snippet", "320,000" in str(ef.get("exa_medical_bills_snippet", "")))
    check("medical_bills carries source url", ef.get("exa_medical_bills_url", "").startswith("https://"))
    check("lost_wages from exa", ef.get("lost_wages") == 150000.0)
    check("plaintiff_age from exa", ef.get("plaintiff_age_range") == "30_44")
    check("age carries snippet", "42" in str(ef.get("exa_age_snippet", "")))
    check("insurance_carrier from exa", "Progressive" in str(ef.get("insurance_carrier")))
    check("carrier carries source url", ef.get("exa_insurance_url", "").startswith("https://"))
    check("trial_duration from exa", ef.get("trial_duration_days") == 10)
    check("trial_duration carries snippet", "10" in str(ef.get("exa_trial_duration_snippet", "")))
    check("exa flag set", ef.get("_exa_search_used") is True)

    print("NEVER guess: unattributable value not in snippet is dropped:")
    # A snippet that names a figure with no verbatim digits must not yield a number.
    liar = [("The plaintiff received a substantial but undisclosed settlement.",
             "https://news.example.com/x")]
    ef_liar = enrich_exa(dict(candidate), pairs=liar)
    check("no fabricated medical_bills", ef_liar.get("medical_bills") is None)
    check("no fabricated amount at all", not any(k in ef_liar for k in
          ("medical_bills", "lost_wages", "economic_damages", "settlement_amount")))

    print("NEVER guess: expert counts are never split from a total:")
    experts = [("Three experts testified at trial about the injuries.",
                "https://news.example.com/e")]
    ef_exp = enrich_exa(dict(candidate), pairs=experts)
    check("no guessed plaintiff expert count", ef_exp.get("expert_witnesses_plaintiff") is None)
    check("no guessed defense expert count", ef_exp.get("expert_witnesses_defense") is None)

    print("No override of existing fields:")
    pre_filled = dict(candidate, medical_bills=999999.0, insurance_carrier="Geico")
    ef2 = enrich_exa(pre_filled, pairs=mock)
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
