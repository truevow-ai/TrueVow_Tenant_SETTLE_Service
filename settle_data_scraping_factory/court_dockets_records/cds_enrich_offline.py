"""
cds_enrich_offline.py — Re-fetch opinion text from full_text_url and run deep enrichment.

Enriches existing pipeline candidate JSONL files with fields extracted from the
original opinion text. Falls through to optional Exa news search for fields that
opinions rarely contain (insurance carrier, plaintiff age from news, etc.).

Usage:
    python cds_enrich_offline.py --in out/cap_crawl_florida/cap_florida_accepted.jsonl --dry-run
    python cds_enrich_offline.py --in out/cap_crawl_florida/cap_florida_accepted.jsonl
    python cds_enrich_offline.py --in-dir out/ --dry-run  # process all jsonl recursively
    python cds_enrich_offline.py --selftest
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from _common.fetcher import Fetcher  # noqa: E402
from _common.enrich import enrich  # noqa: E402

OUT_DIR = Path(__file__).parent / "out"

ENRICHABLE_FIELDS = [
    "judge_name", "medical_bills", "economic_damages", "non_economic_damages",
    "punitive_damages", "lost_wages", "plaintiff_age_range", "trial_duration_days",
    "expert_witnesses_plaintiff", "expert_witnesses_defense",
    "defendant_category", "defendant_industry", "insurance_carrier",
    "policy_limit_indicator", "verdict_date", "filing_date",
    "comparative_negligence_pct", "liability_tier",
]


def enrich_candidate(c: dict, f: Optional[Fetcher] = None) -> dict:
    """Enrich a single candidate. Re-fetches opinion text if needed."""
    text = c.get("_raw_opinion_text")

    if not text and f is not None:
        url = c.get("full_text_url")
        if not url:
            return c
        try:
            source = c.get("source", "")
            if source in ("caselaw_access_project", "courtlistener"):
                res = f.get_json(url)
                data = res.json()
                if source == "caselaw_access_project":
                    opinions = (data.get("casebody") or {}).get("opinions") or []
                    text = "\n\n".join(o.get("text", "") for o in opinions if isinstance(o, dict))
                else:
                    text = data.get("plain_text") or data.get("html_with_citations") or ""
                    if isinstance(text, str) and text.startswith("<"):
                        from bs4 import BeautifulSoup
                        text = BeautifulSoup(text, "lxml").get_text(" ", strip=True)
            else:
                res = f.get_text(url)
                text = res.text()
        except Exception:
            return c

    if not text:
        return c

    ef = enrich(text, case_type=c.get("case_type"))
    enriched = c.copy()
    enriched["_enrichment"] = ef.to_dict()

    for field_name in ENRICHABLE_FIELDS:
        val = getattr(ef, field_name, None)
        if val is not None:
            enriched[field_name] = val

    return enriched


def enrich_file(in_path: Path, dry_run: bool = False, fetcher: Optional[Fetcher] = None) -> dict:
    """Enrich all candidates in a JSONL file."""
    rows = []
    for line in in_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

    enriched_rows = []
    enriched_count = 0
    self_fetch = fetcher is None

    if self_fetch:
        fetcher = Fetcher(min_delay=0.3)

    try:
        for r in rows:
            er = enrich_candidate(r, f=fetcher)
            enriched_rows.append(er)
            if er.get("_enrichment"):
                enriched_count += 1
    finally:
        if self_fetch and fetcher:
            fetcher.close()

    if dry_run:
        out_path = in_path.with_suffix(".enriched.jsonl")
    else:
        out_path = in_path.with_name(in_path.stem + "_enriched.jsonl")

    out_path.write_text("\n".join(json.dumps(r, default=str) for r in enriched_rows), encoding="utf-8")

    return {
        "input_file": str(in_path),
        "output_file": str(out_path),
        "total_rows": len(rows),
        "enriched": enriched_count,
        "mode": "dry_run" if dry_run else "live",
    }


def enrich_dir(dir_path: Path, dry_run: bool = False) -> list[dict]:
    """Enrich all JSONL files in a directory tree."""
    results = []
    with Fetcher(min_delay=0.3) as ft:
        for p in sorted(dir_path.rglob("*.jsonl")):
            if ".enriched." in p.name or ".verdicts." in p.name:
                continue
            res = enrich_file(p, dry_run=dry_run, fetcher=ft)
            results.append(res)
            print(json.dumps(res, default=str))
    return results


def selftest() -> int:
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    candidate = {
        "source": "caselaw_access_project",
        "state": "Florida",
        "case_type": "motor_vehicle_accident",
        "injury_category": ["neck", "back"],
        "outcome_type": "verdict",
        "exact_outcome_amount": 1250000.0,
        "case_name": "Doe v. Roe",
        "full_text_url": "https://static.case.law/so3d/1/cases/0001-01.json",
        "confidence_score": 0.85,
        "status": "accepted",
        "reason": "validated",
        "_raw_opinion_text": (
            "SMITH, J.\n\n"
            "The plaintiff, aged 45 years, sustained lumbar spine injuries "
            "in a rear-end collision. The defendant was insured by Geico Insurance. "
            "After a 5-day trial, the jury returned a verdict for $750,000. "
            "Medical bills totalled $180,000. Lost wages were $45,000. "
            "The plaintiff was found 10 percent at fault."
        ),
    }

    print("Offline enrichment (text already in candidate):")
    enriched = enrich_candidate(candidate)
    check("judge_name enriched", enriched.get("judge_name") == "SMITH J.")
    check("medical_bills enriched", enriched.get("medical_bills") == 180000.0)
    check("lost_wages enriched", enriched.get("lost_wages") == 45000.0)
    check("plaintiff_age enriched", enriched.get("plaintiff_age_range") == "45_59")
    check("trial_duration enriched", enriched.get("trial_duration_days") == 5)
    check("insurance_carrier enriched", enriched.get("insurance_carrier") is not None and "GEICO" in enriched["insurance_carrier"].upper())
    check("comparative_negligence enriched", enriched.get("comparative_negligence_pct") == 10.0)
    check("liability_tier enriched", enriched.get("liability_tier") == "likely_liable")
    check("original fields preserved", enriched.get("case_name") == "Doe v. Roe")

    print("No text -> no enrichment, no crash:")
    empty = {"case_name": "Test"}
    e2 = enrich_candidate(empty)
    check("empty candidate unchanged", e2 == empty)

    print("Carrier extractor rejects sentence fragments (regression):")
    from _common.enrich import extract_carrier
    check("garbage phrase rejected",
          extract_carrier("insured by the appellee who appeals from a post-judgment order which") in (None, "appellee"))
    check("lowercase fragment not a carrier",
          extract_carrier("coverage through his employer to take your claim seriously") is None)
    check("known carrier normalised", extract_carrier("The vehicle was covered by state farm.") == "State Farm")
    check("contextual suffixed carrier", extract_carrier("The defendant was insured by Acme Casualty Company.") is not None)
    check("ambiguous word not a carrier without context",
          extract_carrier("The general rule is that travelers on the nationwide highway must yield.") is None)
    check("ambiguous word IS a carrier with context",
          extract_carrier("The plaintiff's uninsured motorist claim against Nationwide was denied.") == "Nationwide")

    if failures:
        print(f"\nRESULT: FAILED ({len(failures)}) -> {failures}")
        return 1
    print("\nRESULT: ALL CHECKS PASSED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Offline enrichment of pipeline candidates")
    ap.add_argument("--in", dest="in_path", help="Input JSONL file")
    ap.add_argument("--in-dir", dest="in_dir", help="Input directory (recursive JSONL)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if args.in_dir:
        results = enrich_dir(Path(args.in_dir), dry_run=args.dry_run)
        print(json.dumps({"total_files": len(results), "results": results}, indent=2, default=str))
    elif args.in_path:
        res = enrich_file(Path(args.in_path), dry_run=args.dry_run)
        print(json.dumps(res, indent=2, default=str))
    else:
        ap.error("--in or --in-dir required (or --selftest)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
