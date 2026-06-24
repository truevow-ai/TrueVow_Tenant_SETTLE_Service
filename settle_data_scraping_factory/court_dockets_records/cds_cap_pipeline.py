"""
cds_cap_pipeline.py — End-to-end Caselaw Access Project -> PI candidate rows.

Wires Piece 1-4 together and enforces the data-integrity guardrail
(LOW_BLOCKER_DATA_SOURCES section 6a): every row is VALIDATED, SCORED, and
DEDUPED, carries provenance, and is ROUTED to one of three buckets — never
auto-published:

    accepted     -> PI + plausible $ outcome + provenance + confidence >= threshold
    needs_review -> PI but missing/low-confidence $ (admin decides)  [NOT counted to targets]
    rejected     -> not PI / failed validation

Counting honesty: only `accepted` rows count toward "1,000+ FL / 2,000+ CA".

Run:
    python cds_cap_pipeline.py --slug so3d --state Florida --max 50
    python cds_cap_pipeline.py --selftest
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from _common.extract import extract  # noqa: E402
from cds_cap_fetcher import fetch_reporter  # noqa: E402
from _common.fetcher import Fetcher  # noqa: E402

TARGET_STATES = {"Florida", "California"}
ACCEPT_CONFIDENCE = 0.6
OUT_DIR = Path(__file__).parent / "out"

# Outcome buckets (align with SettleContribution.outcome_amount_range style).
_BUCKETS = [
    (50_000, "under_50k"),
    (150_000, "50k_150k"),
    (500_000, "150k_500k"),
    (1_000_000, "500k_1m"),
    (5_000_000, "1m_5m"),
    (float("inf"), "5m_plus"),
]


def bucket_for(amount: Optional[float]) -> Optional[str]:
    if amount is None:
        return None
    for hi, label in _BUCKETS:
        if amount < hi:
            return label
    return "5m_plus"


def _norm_name(s: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def dedup_key(rec: dict) -> str:
    cite = rec.get("official_citation")
    if cite:
        return f"cite:{_norm_name(cite)}"
    return f"name:{rec.get('jurisdiction')}|{_norm_name(rec.get('name_abbreviation'))}|{rec.get('year')}"


def build_candidate(rec: dict) -> dict:
    """rec = a normalized CAP case (from fetch_reporter with_text=True)."""
    text = rec.get("opinion_text") or ""
    ex = extract(text)

    # county is not present in appellate opinions; try a light text hint, else null.
    county = None
    m = re.search(r"County of ([A-Z][a-zA-Z]+)", text)
    if m:
        county = f"{m.group(1)} County, {('FL' if rec.get('jurisdiction')=='Florida' else 'CA')}"

    candidate = {
        "source": rec.get("source", "caselaw_access_project"),
        "state": rec.get("jurisdiction"),
        "county_hint": county,
        "case_type": ex.case_type,
        "injury_category": ex.injuries,
        "outcome_type": ex.outcome_type,
        "exact_outcome_amount": ex.amount,
        "outcome_amount_range": bucket_for(ex.amount),
        "year": rec.get("year"),
        "is_verdict": (ex.outcome_type == "verdict") if ex.outcome_type else None,
        # provenance (guardrail 6a)
        "source_url": rec.get("source_url"),
        "full_text_url": rec.get("full_text_url"),
        "text_sha256": rec.get("text_sha256"),
        "fetched_at": rec.get("fetched_at"),
        "amount_snippet": ex.amount_snippet,
        "extraction_method": "deterministic_regex_keyword",
        "case_name": rec.get("name_abbreviation"),
        "official_citation": rec.get("official_citation"),
        # scoring / routing (filled by validate_and_score)
        "dedup_key": None,
        "confidence_score": None,
        "status": None,
        "reason": None,
        "_extraction": ex.to_dict(),
    }
    candidate["dedup_key"] = dedup_key(rec)
    return validate_and_score(candidate, ex)


def validate_and_score(c: dict, ex) -> dict:
    # Hard validation -> reject
    if c["state"] not in TARGET_STATES:
        c["status"], c["reason"] = "rejected", "jurisdiction_not_target"
        c["confidence_score"] = 0.0
        return c
    if not (c.get("source_url") and c.get("full_text_url")):
        c["status"], c["reason"] = "rejected", "missing_provenance"
        c["confidence_score"] = 0.0
        return c
    if not ex.is_pi:
        c["status"], c["reason"] = "rejected", "not_personal_injury"
        c["confidence_score"] = round(ex.confidence, 2)
        return c

    # Composite confidence: extractor + completeness + source reliability (CAP=official).
    score = ex.confidence
    if c["injury_category"]:
        score += 0.05
    if c["case_type"]:
        score += 0.05
    score = min(1.0, round(score + 0.05, 2))  # +0.05 source reliability (official corpus)
    c["confidence_score"] = score

    # Need a plausible, sourced $ outcome to be "accepted".
    if c["exact_outcome_amount"] is None:
        c["status"], c["reason"] = "needs_review", "pi_but_no_outcome_amount"
        return c
    if not c["amount_snippet"]:
        c["status"], c["reason"] = "needs_review", "amount_without_snippet"  # never trust unsourced $
        return c
    if not (c["injury_category"] or c["case_type"]):
        # PI signal + a $ figure but no concrete injury/case-type -> likely a non-PI
        # money mention (e.g., contract damages). Send to human review, never auto-accept.
        c["status"], c["reason"] = "needs_review", "no_injury_or_case_type"
        return c
    if score < ACCEPT_CONFIDENCE:
        c["status"], c["reason"] = "needs_review", "below_confidence_threshold"
        return c

    c["status"], c["reason"] = "accepted", "validated"
    return c


def run_pipeline(slug: str, state: str, max_cases: int) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    buckets = {"accepted": [], "needs_review": [], "rejected": []}
    seen_keys: set[str] = set()
    duplicates = 0

    with Fetcher(min_delay=0.5) as f:
        for rec in fetch_reporter(f, slug, state, max_cases=max_cases, with_text=True):
            cand = build_candidate(rec)
            if cand["status"] == "accepted":
                if cand["dedup_key"] in seen_keys:
                    duplicates += 1
                    continue
                seen_keys.add(cand["dedup_key"])
            buckets[cand["status"]].append(cand)

    for name, rows in buckets.items():
        path = OUT_DIR / f"cap_{slug}_{state.lower()}_{name}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, default=str) + "\n")

    summary = {
        "slug": slug,
        "state": state,
        "candidates_seen": sum(len(v) for v in buckets.values()) + duplicates,
        "accepted_usable": len(buckets["accepted"]),
        "needs_review": len(buckets["needs_review"]),
        "rejected": len(buckets["rejected"]),
        "duplicates_dropped": duplicates,
    }
    return summary


def selftest() -> int:
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    base = {
        "jurisdiction": "Florida", "name_abbreviation": "Doe v. Roe", "year": 2018,
        "official_citation": "1 So. 3d 999", "source_url": "https://static.case.law/so3d/1/CasesMetadata.json",
        "full_text_url": "https://static.case.law/so3d/1/cases/0999-01.json", "text_sha256": "x" * 64,
        "fetched_at": "2026-06-23T00:00:00+00:00",
    }

    print("Accepted path (PI + sourced $):")
    pi = dict(base, opinion_text=("The jury awarded the plaintiff $1,250,000 in damages for cervical "
                                  "spine injuries from the motor vehicle accident due to negligence."))
    c = build_candidate(pi)
    check("status accepted", c["status"] == "accepted")
    check("amount captured", c["exact_outcome_amount"] == 1_250_000)
    check("bucket 1m_5m", c["outcome_amount_range"] == "1m_5m")
    check("has snippet provenance", bool(c["amount_snippet"]) and "1,250,000" in c["amount_snippet"])
    check("confidence >= threshold", c["confidence_score"] >= ACCEPT_CONFIDENCE)
    check("dedup_key set", bool(c["dedup_key"]))

    print("Rejected path (not PI):")
    c2 = build_candidate(dict(base, opinion_text="In re Amendments to Florida Rule of Criminal Procedure 3.851."))
    check("status rejected", c2["status"] == "rejected")
    check("reason not_personal_injury", c2["reason"] == "not_personal_injury")
    check("no fabricated amount", c2["exact_outcome_amount"] is None)

    print("Needs-review path (PI, no $):")
    c3 = build_candidate(dict(base, opinion_text=("Plaintiff alleged negligence and personal injury; the trial "
                                                  "court entered judgment. Pain and suffering were at issue.")))
    check("status needs_review", c3["status"] == "needs_review")
    check("reason pi_but_no_outcome_amount", c3["reason"] == "pi_but_no_outcome_amount")
    check("no fabricated amount", c3["exact_outcome_amount"] is None)

    print("Missing provenance -> rejected:")
    bad = dict(base, opinion_text=pi["opinion_text"]); bad["full_text_url"] = None
    c4 = build_candidate(bad)
    check("status rejected (missing provenance)", c4["status"] == "rejected" and c4["reason"] == "missing_provenance")

    print("Real data — small so3d Florida slice (honest counts, zero fabrication):")
    try:
        summary = run_pipeline("so3d", "Florida", max_cases=8)
        print("   summary:", json.dumps(summary))
        check("ran end-to-end", summary["candidates_seen"] >= 1)
        # Verify accepted rows (if any) all have amount + snippet + provenance.
        acc_path = OUT_DIR / "cap_so3d_florida_accepted.jsonl"
        ok = True
        if acc_path.exists():
            for line in acc_path.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                if not (r.get("exact_outcome_amount") and r.get("amount_snippet") and r.get("full_text_url")):
                    ok = False
        check("every accepted row has $ + snippet + provenance", ok)
    except Exception as ex:
        check(f"real-data pipeline (no exception) [{str(ex)[:60]}]", False)

    if failures:
        print(f"\nRESULT: FAILED ({len(failures)}) -> {failures}")
        return 1
    print("\nRESULT: ALL CHECKS PASSED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="CAP -> PI candidate pipeline")
    ap.add_argument("--slug")
    ap.add_argument("--state")
    ap.add_argument("--max", type=int, default=50)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not (args.slug and args.state):
        ap.error("--slug and --state required (or --selftest)")
    summary = run_pipeline(args.slug, args.state, args.max)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
