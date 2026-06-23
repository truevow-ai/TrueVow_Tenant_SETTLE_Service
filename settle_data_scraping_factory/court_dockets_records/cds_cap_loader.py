"""
cds_cap_loader.py — Load CAP pipeline rows into the SETTLE internal-verdicts
review queue (settle_verdicts, review_status='pending') via the admin bulk-insert API.

Pieces 1-5 produce validated/scored/deduped candidate rows (accepted / needs_review).
This piece maps them to the settle_verdicts schema and posts them so a human can
review them in the SETTLE admin dashboard. Nothing is auto-published to customers —
rows land as review_status='pending' / 'needs_review'.

Integrity (guardrail 6a): we map ONLY fields we actually have. We do NOT invent a
county (CAP appellate data is state-level) or a precise date (CAP dates are often
year-only) — those imprecisions are recorded truthfully in source_notes instead of
being faked. Provenance (source_url + sha256 + evidence snippet) is preserved.

Endpoints used:
    POST /api/v1/internal/verdicts/scrape/jobs         (job tracking; best-effort)
    POST /api/v1/internal/verdicts/scrape/bulk-insert  (records; server dedups)
    PATCH /api/v1/internal/verdicts/scrape/jobs/{id}    (job result; best-effort)

Run:
    python cds_cap_loader.py --in out/cap_so3d_florida_accepted.jsonl --dry-run
    python cds_cap_loader.py --in out/cap_so3d_florida_accepted.jsonl     # live POST
    python cds_cap_loader.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import httpx

SETTLE_API_URL = os.getenv("SETTLE_API_URL", "http://localhost:8002")
# Admin key must start with 'settle_' (auth format gate). In mock mode any such key works.
SETTLE_ADMIN_KEY = os.getenv("SETTLE_ADMIN_API_KEY", "settle_admin_dev_key")

_SETTLEMENT_KINDS = {"settlement"}


def map_candidate_to_verdict(c: dict) -> dict:
    """Map a pipeline candidate row -> settle_verdicts record. Faithful; no fabrication."""
    state = c.get("state")
    amount = c.get("exact_outcome_amount")
    outcome_type = c.get("outcome_type")

    # Route the amount to the correct field (settlement vs verdict/award/damages).
    total_verdict = None
    settlement_amount = None
    if amount is not None:
        if outcome_type in _SETTLEMENT_KINDS:
            settlement_amount = amount
        else:
            total_verdict = amount

    # jurisdiction: use a real county hint if the opinion text gave one, else the state.
    jurisdiction = c.get("county_hint") or state

    # case_type: keep specific type if found; else a general PI bucket (accepted rows
    # always have an injury or a case_type, so this is a category, not a fabrication).
    case_type = c.get("case_type") or ("personal_injury_general" if c.get("injury_category") else None)

    # Provenance + evidence + honest imprecision flags for the human reviewer.
    notes = {
        "pipeline_status": c.get("status"),
        "pipeline_reason": c.get("reason"),
        "official_citation": c.get("official_citation"),
        "decision_year": c.get("year"),
        "jurisdiction_granularity": "county" if c.get("county_hint") else "state",
        "date_precision": "year_only",
        "amount_snippet": c.get("amount_snippet"),
        "extraction_method": c.get("extraction_method"),
        "text_sha256": c.get("text_sha256"),
        "full_text_url": c.get("full_text_url"),
    }

    review_status = "needs_review" if c.get("status") == "needs_review" else "pending"

    record = {
        "case_name": c.get("case_name"),
        "jurisdiction": jurisdiction,
        "case_type": case_type,
        "injury_type": c.get("injury_category") or [],
        "outcome_type": outcome_type or "unknown",
        "total_verdict": total_verdict,
        "settlement_amount": settlement_amount,
        # verdict_date intentionally omitted: CAP is year-only; decision_year is in notes.
        "source": "caselaw_access_project",
        "source_url": c.get("full_text_url") or c.get("source_url"),
        "source_notes": json.dumps({k: v for k, v in notes.items() if v is not None}, default=str),
        "review_status": review_status,
        "confidence_score": c.get("confidence_score"),
    }
    # Drop null amount fields so we don't send explicit nulls.
    return {k: v for k, v in record.items() if v is not None}


def _read_rows(path: Path) -> list[dict]:
    rows = []
    # utf-8-sig tolerates a leading BOM (some editors/PowerShell add one).
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_file(in_path: Path, dry_run: bool, source_label: str = "caselaw_access_project") -> dict:
    rows = _read_rows(in_path)
    records = [map_candidate_to_verdict(r) for r in rows]

    if dry_run:
        out = in_path.with_suffix(".verdicts.jsonl")
        out.write_text("\n".join(json.dumps(r, default=str) for r in records), encoding="utf-8")
        return {"mode": "dry_run", "mapped": len(records), "payload_written": str(out)}

    headers = {"Authorization": f"Bearer {SETTLE_ADMIN_KEY}", "X-Admin-Key": SETTLE_ADMIN_KEY}

    # Best-effort job tracking in its OWN client/connection so a failure (e.g. no DB ->
    # 500 + connection close) cannot poison the bulk-insert connection.
    job_id = None
    try:
        with httpx.Client(timeout=60.0, headers=headers) as jc:
            jr = jc.post(
                f"{SETTLE_API_URL}/api/v1/internal/verdicts/scrape/jobs",
                json={"source": source_label, "source_config": {"in_file": in_path.name, "count": len(records)}},
            )
            if jr.status_code == 200:
                job_id = jr.json().get("id")
    except Exception:
        pass

    # Bulk-insert on a fresh connection, with a retry on transient disconnects.
    result = {"http_status": None}
    last_err = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=120.0, headers=headers) as bc:
                resp = bc.post(
                    f"{SETTLE_API_URL}/api/v1/internal/verdicts/scrape/bulk-insert",
                    json=records,
                )
            result = {"http_status": resp.status_code}
            try:
                result.update(resp.json())
            except Exception:
                result["body"] = resp.text[:300]
            break
        except (httpx.RemoteProtocolError, httpx.TransportError) as e:
            last_err = e
    else:
        result = {"http_status": None, "error": f"bulk-insert failed after retries: {last_err}"}

    if job_id:
        try:
            with httpx.Client(timeout=60.0, headers=headers) as pc:
                pc.patch(
                    f"{SETTLE_API_URL}/api/v1/internal/verdicts/scrape/jobs/{job_id}",
                    params={
                        "status": "completed",
                        "records_found": len(records),
                        "records_inserted": result.get("inserted", 0),
                        "records_skipped": result.get("skipped", 0),
                        "records_failed": result.get("failed", 0),
                    },
                )
        except Exception:
            pass

    result["mode"] = "live"
    result["mapped"] = len(records)
    return result


def selftest() -> int:
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    accepted = {
        "source": "caselaw_access_project", "state": "Florida", "county_hint": None,
        "case_type": "motor_vehicle_accident", "injury_category": ["neck", "back"],
        "outcome_type": "verdict", "exact_outcome_amount": 1_250_000, "outcome_amount_range": "1m_5m",
        "year": 2018, "is_verdict": True, "source_url": "https://static.case.law/so3d/1/CasesMetadata.json",
        "full_text_url": "https://static.case.law/so3d/1/cases/0001-01.json", "text_sha256": "a" * 64,
        "amount_snippet": "jury awarded $1,250,000 in damages for spinal injuries",
        "extraction_method": "deterministic_regex_keyword", "case_name": "Doe v. Roe",
        "official_citation": "1 So. 3d 1", "confidence_score": 0.85, "status": "accepted", "reason": "validated",
    }
    print("Accepted -> verdict record mapping:")
    v = map_candidate_to_verdict(accepted)
    check("case_name mapped", v["case_name"] == "Doe v. Roe")
    check("amount routed to total_verdict", v.get("total_verdict") == 1_250_000)
    check("no settlement_amount on verdict", "settlement_amount" not in v)
    check("injury_type list preserved", v["injury_type"] == ["neck", "back"])
    check("review_status pending", v["review_status"] == "pending")
    check("source_url is provenance", v["source_url"].endswith(".json"))
    check("NO fabricated verdict_date", "verdict_date" not in v)
    notes = json.loads(v["source_notes"])
    check("notes carry year + snippet + sha256", notes.get("decision_year") == 2018 and notes.get("amount_snippet") and notes.get("text_sha256"))
    check("notes flag state-level + year-only", notes.get("jurisdiction_granularity") == "state" and notes.get("date_precision") == "year_only")
    check("confidence preserved", v["confidence_score"] == 0.85)

    print("Settlement routing + needs_review status:")
    s = dict(accepted, outcome_type="settlement", status="needs_review", reason="below_confidence_threshold")
    vs = map_candidate_to_verdict(s)
    check("amount routed to settlement_amount", vs.get("settlement_amount") == 1_250_000)
    check("no total_verdict on settlement", "total_verdict" not in vs)
    check("needs_review status", vs["review_status"] == "needs_review")

    print("Dry-run file mapping (no network):")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "sample.jsonl"
        p.write_text(json.dumps(accepted) + "\n", encoding="utf-8")
        res = load_file(p, dry_run=True)
        check("dry-run mapped 1", res["mapped"] == 1)
        check("payload file written", Path(res["payload_written"]).exists())

    if failures:
        print(f"\nRESULT: FAILED ({len(failures)}) -> {failures}")
        return 1
    print("\nRESULT: ALL CHECKS PASSED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Load CAP pipeline rows into SETTLE review queue")
    ap.add_argument("--in", dest="in_path")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.in_path:
        ap.error("--in is required (or --selftest)")
    res = load_file(Path(args.in_path), dry_run=args.dry_run)
    print(json.dumps(res, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
