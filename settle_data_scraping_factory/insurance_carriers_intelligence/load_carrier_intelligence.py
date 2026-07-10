"""
load_carrier_intelligence.py — Aggregate verified carrier facts into
settle_carrier_intelligence, keyed by the canonical carrier name used in
settle_verdicts.

Every fact is re-verified by cis_fabrication_gate before it is aggregated, so
nothing unverifiable is stored (no-fabrication directive). Rollups
(complaint_total, years, has_sec_filings) are derived ONLY from verified facts
and remain traceable to their source_url.

Usage:
    python load_carrier_intelligence.py --dry-run
    python load_carrier_intelligence.py
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import httpx
from dotenv import load_dotenv

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
load_dotenv(_HERE.parent.parent / ".env.local")

from cis_fabrication_gate import verify_carrier_fact  # noqa: E402
from cis_orchestrator import CARRIERS  # noqa: E402

OUT = _HERE / "out"
DB_URL = (os.getenv("SETTLE_DATABASE_URL") or "").rstrip("/")
DB_KEY = os.getenv("SETTLE_DATABASE_SERVICE_ROLE_KEY") or os.getenv("SETTLE_DATABASE_API_SECRET_KEY")
_TABLE = "settle_carrier_intelligence"

# NAIC -> canonical registry name (verdicts use the canonical name).
_NAIC_TO_NAME = {c.naic: c.name for c in CARRIERS if c.naic}


def _headers() -> dict:
    return {"apikey": DB_KEY, "Authorization": f"Bearer {DB_KEY}",
            "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}


def build_rows() -> list[dict]:
    # carrier_name -> aggregation
    agg: dict[str, dict] = defaultdict(lambda: {
        "facts": [], "legal_names": set(), "naic": None,
        "complaint_total": 0, "years": set(), "has_sec": False, "datasets": set(),
    })

    for f in glob.glob(str(OUT / "**" / "*_facts.jsonl"), recursive=True):
        for line in Path(f).read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line:
                continue
            fact = json.loads(line)
            # Re-verify EVERY fact at load time (gate runs on past + future).
            gate = verify_carrier_fact(fact)
            if not gate["ok"]:
                continue

            naic = str(fact.get("entity_id", "")).strip()
            name = _NAIC_TO_NAME.get(naic)
            if not name:
                # SEC facts may key by CIK; skip if we can't map to a canonical
                # carrier name (never guess the linkage).
                continue

            a = agg[name]
            a["naic"] = naic
            if fact.get("entity_name"):
                a["legal_names"].add(fact["entity_name"])
            if fact.get("source_dataset"):
                a["datasets"].add(fact["source_dataset"])
            a["facts"].append({
                "kind": fact.get("kind"),
                "value_text": fact.get("value_text"),
                "source_url": fact.get("source_url"),
                "source_sha256": fact.get("source_sha256"),
                "observed_at": fact.get("observed_at"),
            })
            if fact.get("kind") == "naic_complaint_index":
                try:
                    payload = json.loads(fact.get("value_text") or "{}")
                    a["complaint_total"] += int(payload.get("complaint_count", 0) or 0)
                    if payload.get("complaint_year"):
                        a["years"].add(str(payload["complaint_year"]))
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
            if fact.get("kind") == "sec_filing":
                a["has_sec"] = True

    rows = []
    for name, a in sorted(agg.items()):
        rows.append({
            "carrier_name": name,
            "naic_code": a["naic"],
            "legal_entity_names": sorted(a["legal_names"]),
            "fact_count": len(a["facts"]),
            "facts": a["facts"],
            "complaint_total": a["complaint_total"] or None,
            "complaint_years": sorted(a["years"]) or None,
            "has_sec_filings": a["has_sec"],
            "source_datasets": sorted(a["datasets"]) or None,
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Load carrier intelligence into DB")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = build_rows()
    print(f"Aggregated {len(rows)} carriers from verified facts:")
    for r in rows:
        print(f"  {r['carrier_name']:28s} naic={r['naic_code']:6s} facts={r['fact_count']:3d} "
              f"complaints={r['complaint_total']} sec={r['has_sec_filings']}")

    if args.dry_run:
        print("\nDRY-RUN: nothing written.")
        return 0
    if not (DB_URL and DB_KEY):
        print("ERROR: DB creds missing")
        return 1

    with httpx.Client() as client:
        r = client.post(f"{DB_URL}/rest/v1/{_TABLE}?on_conflict=carrier_name",
                        headers={**_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"},
                        content=json.dumps(rows, default=str), timeout=120)
        print(f"\nupsert HTTP {r.status_code}" + ("" if r.status_code < 300 else f": {r.text[:300]}"))
        return 0 if r.status_code < 300 else 1


if __name__ == "__main__":
    sys.exit(main())
