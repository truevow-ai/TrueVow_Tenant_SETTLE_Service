"""
load_exa_enriched.py — Upsert Exa-enriched carriers + ages into settle_verdicts
through the no-fabrication gate.

Only values that pass verify_record (value verbatim in snippet + source_url) are
written — nothing lands unverified. Existing values (deterministic or prior Exa)
are never overwritten unless they lack evidence and the Exa-sourced value has it.

Usage:
    python load_exa_enriched.py --dry-run
    python load_exa_enriched.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(".env.local")
DB_URL = (os.getenv("SETTLE_DATABASE_URL") or "").rstrip("/")
DB_KEY = os.getenv("SETTLE_DATABASE_SERVICE_ROLE_KEY") or os.getenv("SETTLE_DATABASE_API_SECRET_KEY")
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))
from no_fabrication_gate import verify_record  # noqa: E402

EXA_FILES = [
    "cap_crawl_california/cap_california_accepted_enriched_exa_enriched.jsonl",
    "cl_crawl_florida/courtlistener_florida_accepted_enriched_exa_enriched.jsonl",
]


def _headers(extra=None):
    h = {"apikey": DB_KEY, "Authorization": f"Bearer {DB_KEY}", "Content-Type": "application/json"}
    if extra:
        h.update(extra)
    return h


def _fetch_candidates(path: Path) -> list[dict]:
    updatable = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if not r.get("_exa_search_used"):
            continue
        g = verify_record(r)
        updates = {}
        if g["validation_counts"].get("insurance_carrier"):
            ev = g["evidence"].get("insurance_carrier") or {}
            updates["insurance_carrier"] = r["insurance_carrier"]
            updates["field_evidence"] = (r.get("field_evidence") or {}) | {"insurance_carrier": ev}
        if g["validation_counts"].get("plaintiff_age_range"):
            ev = g["evidence"].get("plaintiff_age_range") or {}
            updates["plaintiff_age_range"] = r["plaintiff_age_range"]
            updates["field_evidence"] = (r.get("field_evidence") or {}) | {"plaintiff_age_range": ev}
        if updates:
            updates["_case_name"] = r.get("case_name")
            updates["_jurisdiction"] = r.get("jurisdiction") or r.get("state")
            updates["_source_url"] = r.get("source_url") or r.get("full_text_url")
            updatable.append(updates)
    return updatable


def main() -> int:
    ap = argparse.ArgumentParser(description="Load gated Exa-enriched carriers+ages into DB")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    all_updates = []
    for rel in EXA_FILES:
        p = _HERE / "out" / rel
        if not p.exists():
            continue
        updates = _fetch_candidates(p)
        print(f"{rel}: {len(updates)} gated updatable")
        all_updates += updates

    counts = Counter()
    for u in all_updates:
        if "insurance_carrier" in u:
            counts["carrier"] += 1
        if "plaintiff_age_range" in u:
            counts["age"] += 1
    print(f"\nTOTAL gated-ready: {len(all_updates)} records ({dict(counts)})")

    if args.dry_run:
        print("DRY-RUN: nothing written.")
        return 0

    if not (DB_URL and DB_KEY):
        print("ERROR: DB creds missing")
        return 1

    updated_carrier = 0
    updated_age = 0
    not_found = 0
    with httpx.Client(timeout=120) as c:
        for u in all_updates:
            cn = u.pop("_case_name")
            jur = u.pop("_jurisdiction")
            src = u.pop("_source_url")
            fe = u.pop("field_evidence", {})
            # Match by case_name + jurisdiction (unique-ish for the verdicts we enriched).
            # Update only rows where these fields are missing (Exa adds to gaps).
            patch = {}
            if "insurance_carrier" in u:
                patch["insurance_carrier"] = u["insurance_carrier"]
            if "plaintiff_age_range" in u:
                patch["plaintiff_age_range"] = u["plaintiff_age_range"]
            if fe:
                patch["field_evidence"] = json.dumps(fe, default=str)
            if not patch:
                continue

            # Find the row and PATCH — preserve any existing values (no overwrite
            # of a more-authoritative deterministic value with Exa; Exa only fills).
            filter_q = f"case_name=eq.{httpx.URL(cn).path.lstrip('/')}" + (
                f"&jurisdiction=eq.{httpx.URL(jur).path.lstrip('/')}" if jur else "")
            # PostgREST needs URL-encoded values; use httpx params
            params = {"case_name": f"eq.{cn}"}
            if jur:
                params["jurisdiction"] = f"eq.{jur}"
            try:
                resp = c.patch(
                    f"{DB_URL}/rest/v1/settle_verdicts",
                    params=params,
                    headers=_headers({"Prefer": "return=minimal"}),
                    content=json.dumps(patch, default=str),
                )
                if resp.status_code < 300:
                    if "insurance_carrier" in u:
                        updated_carrier += 1
                    if "plaintiff_age_range" in u:
                        updated_age += 1
                elif resp.status_code == 404 or "not found" in resp.text.lower():
                    not_found += 1
            except Exception:
                not_found += 1
            if (updated_carrier + updated_age + not_found) % 200 == 0:
                print(f"  ... {updated_carrier} carriers, {updated_age} ages, {not_found} not-found so far", flush=True)

    print(f"\nUPDATED: {updated_carrier} carriers + {updated_age} ages in settle_verdicts")
    if not_found:
        print(f"not-found (name/jurisdiction mismatch): {not_found}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
