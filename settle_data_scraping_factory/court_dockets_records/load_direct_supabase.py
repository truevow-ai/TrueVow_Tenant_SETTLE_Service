"""
load_direct_supabase.py — Load validated accepted-tier verdicts straight into
settle_verdicts via Supabase REST (bypasses the local :8002 API, which is down).

Every record goes through the SAME gate as the API path:
    map_candidate_to_verdict  ->  normalize_and_validate  ->  insert

Rejects are quarantined per-file (*.rejects.jsonl); only records that pass are
inserted. Dedup is by (case_name, jurisdiction, verdict_date) to match the
service's duplicate rule. Idempotent: re-running skips existing rows.

Usage:
    python load_direct_supabase.py --dry-run          # validate + report, no writes
    python load_direct_supabase.py --tier accepted    # load accepted tier (default)
    python load_direct_supabase.py --tier accepted --limit-files 3
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(".env.local")

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from cds_cap_loader import map_candidate_to_verdict, _read_rows  # noqa: E402
from verdict_validator import normalize_and_validate  # noqa: E402
from no_fabrication_gate import verify_record  # noqa: E402
from batch_load_all import find_payloads  # noqa: E402

OUT = _HERE / "out"
DB_URL = (os.getenv("SETTLE_DATABASE_URL") or "").rstrip("/")
DB_KEY = os.getenv("SETTLE_DATABASE_SERVICE_ROLE_KEY") or os.getenv("SETTLE_DATABASE_API_SECRET_KEY")

_TABLE = "settle_verdicts"
_BATCH = 500

# Columns that exist on settle_verdicts (drop anything the mapper emits that the
# table doesn't have, e.g. transient fields).
_COLUMNS = {
    "case_name", "case_number", "jurisdiction", "court", "judge_name",
    "case_type", "injury_type", "plaintiff_age_range", "liability_tier",
    "comparative_negligence_pct", "medical_bills", "economic_damages",
    "non_economic_damages", "punitive_damages", "total_verdict",
    "settlement_amount", "policy_limit_indicator", "outcome_type",
    "defendant_category", "defendant_industry", "insurance_carrier",
    "expert_witnesses_plaintiff", "expert_witnesses_defense",
    "trial_duration_days", "verdict_date", "filing_date", "resolution_date",
    "source", "source_url", "source_notes", "confidence_score",
    "completeness_score", "review_status", "reviewer_notes", "scraped_at",
    "validation_counts", "validated_field_count", "field_evidence",
}


def _headers() -> dict:
    return {
        "apikey": DB_KEY,
        "Authorization": f"Bearer {DB_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def _project(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if k in _COLUMNS}


def _exists(client: httpx.Client, rec: dict) -> bool:
    """Dedup by case_name + jurisdiction (+ verdict_date if present)."""
    if not (rec.get("case_name") and rec.get("jurisdiction")):
        return False
    params = {
        "select": "id",
        "case_name": f"eq.{rec['case_name']}",
        "jurisdiction": f"eq.{rec['jurisdiction']}",
        "limit": "1",
    }
    if rec.get("verdict_date"):
        params["verdict_date"] = f"eq.{rec['verdict_date']}"
    r = client.get(f"{DB_URL}/rest/v1/{_TABLE}", params=params, headers=_headers(), timeout=30)
    return r.status_code == 200 and bool(r.json())


def _existing_keys(client: httpx.Client, path_rows: list[dict]) -> set:
    """Fetch existing (case_name, jurisdiction, verdict_date) tuples for this
    file's jurisdictions in bulk, so dedup is a handful of GETs, not one per row."""
    jurisdictions = {r["jurisdiction"] for r in path_rows if r.get("jurisdiction")}
    existing: set = set()
    for juris in jurisdictions:
        offset = 0
        while True:
            params = {
                "select": "case_name,jurisdiction,verdict_date",
                "jurisdiction": f"eq.{juris}",
                "limit": "1000", "offset": str(offset),
            }
            r = client.get(f"{DB_URL}/rest/v1/{_TABLE}", params=params,
                           headers=_headers(), timeout=60)
            if r.status_code != 200 or not r.json():
                break
            for row in r.json():
                existing.add((row.get("case_name"), row.get("jurisdiction"), row.get("verdict_date")))
            if len(r.json()) < 1000:
                break
            offset += 1000
    return existing


def load_file(path: Path, client: httpx.Client | None, dry_run: bool) -> dict:
    rows = _read_rows(path)
    valid: list[dict] = []
    rejects: list[dict] = []
    warn = 0
    for original in rows:
        # Gate 1: no-fabrication — strip any field not verbatim-backed by
        # evidence + source_url; reject records lacking identity/provenance.
        gate = verify_record(original)
        if gate["rejected"]:
            rejects.append({"case_name": original.get("case_name"),
                            "errors": [f"no-fabrication: {r}" for r in gate["reject_reasons"]],
                            "record": original})
            continue
        verified = gate["record"]
        mapped = map_candidate_to_verdict(verified)
        mapped["validation_counts"] = gate["validation_counts"]
        mapped["validated_field_count"] = gate["validated_total"]
        mapped["field_evidence"] = gate["evidence"]
        # Gate 2: enum/format/bounds validation.
        clean, errors, warnings = normalize_and_validate(mapped)
        warn += len(warnings)
        if clean is None:
            rejects.append({"case_name": original.get("case_name"),
                            "errors": errors, "record": mapped})
        else:
            valid.append(_project(clean))

    if rejects:
        path.with_suffix(".rejects.jsonl").write_text(
            "\n".join(json.dumps(r, default=str) for r in rejects), encoding="utf-8")

    inserted = skipped = failed = 0
    if not dry_run and valid:
        existing = _existing_keys(client, valid)
        fresh = []
        for v in valid:
            key = (v.get("case_name"), v.get("jurisdiction"), v.get("verdict_date"))
            if v.get("case_name") and v.get("jurisdiction") and key in existing:
                skipped += 1
            else:
                fresh.append(v)
        for i in range(0, len(fresh), _BATCH):
            chunk = fresh[i:i + _BATCH]
            # PostgREST requires every object in a bulk insert to share the same
            # keys. Union all keys in the chunk and fill missing with None.
            keys: set[str] = set()
            for v in chunk:
                keys.update(v.keys())
            chunk = [{k: v.get(k) for k in keys} for v in chunk]
            try:
                r = client.post(f"{DB_URL}/rest/v1/{_TABLE}", headers=_headers(),
                                content=json.dumps(chunk, default=str), timeout=120)
                if r.status_code in (200, 201, 204):
                    inserted += len(chunk)
                else:
                    failed += len(chunk)
                    print(f"    insert HTTP {r.status_code}: {r.text[:200]}")
            except Exception as e:
                failed += len(chunk)
                print(f"    insert error: {type(e).__name__}: {e}")

    return {"file": str(path.relative_to(OUT)), "rows": len(rows),
            "valid": len(valid), "rejected": len(rejects), "warnings": warn,
            "inserted": inserted, "skipped": skipped, "failed": failed}


def main() -> int:
    ap = argparse.ArgumentParser(description="Direct Supabase load of validated verdicts")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--tier", choices=["accepted", "needs_review", "all"], default="accepted")
    ap.add_argument("--limit-files", type=int, default=0)
    args = ap.parse_args()

    if not (DB_URL and DB_KEY):
        print("ERROR: SETTLE_DATABASE_URL / service-role key not set")
        return 1

    payloads = find_payloads(OUT)
    if args.tier == "accepted":
        payloads = [p for p in payloads if "needs_review" not in p.name]
    elif args.tier == "needs_review":
        payloads = [p for p in payloads if "needs_review" in p.name]
    if args.limit_files:
        payloads = payloads[: args.limit_files]

    print(f"{'DRY-RUN' if args.dry_run else 'LOADING'} tier={args.tier}: {len(payloads)} files -> {_TABLE}")
    totals = {"rows": 0, "valid": 0, "rejected": 0, "inserted": 0, "skipped": 0, "failed": 0, "warnings": 0}

    client = None if args.dry_run else httpx.Client()
    try:
        for p in payloads:
            r = load_file(p, client, args.dry_run)
            for k in totals:
                totals[k] += r[k]
            flag = "" if not (r["inserted"] or r["failed"]) else f" ins={r['inserted']} skip={r['skipped']} fail={r['failed']}"
            print(f"  {r['file']}: valid={r['valid']} rejected={r['rejected']}{flag}")
    finally:
        if client:
            client.close()

    print(f"\nTOTAL: valid={totals['valid']} rejected={totals['rejected']} "
          f"warnings={totals['warnings']} inserted={totals['inserted']} "
          f"skipped={totals['skipped']} failed={totals['failed']}")
    return 1 if totals["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
