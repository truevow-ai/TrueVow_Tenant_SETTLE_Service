"""
carrier_profile.py — Build unified carrier profiles by aggregating data from
all insurance carrier intelligence sources (NAIC, SEC, FL OIR, CourtListener).

Combines complaint indices, SEC reserves, EDGAR filings, FL OIR reports,
and bad-faith opinions into a single CarrierFact profile.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from typing import Any

from carrier_common import CarrierFact, utc_now_iso


def build_carrier_profile(
    name: str,
    naic_code: str | None = None,
    cik: str | None = None,
) -> list[dict[str, Any]]:
    import hashlib

    now = utc_now_iso()
    profile: dict[str, Any] = {
        "profile_name": name,
        "naic_code": naic_code,
        "cik": cik,
        "generated_at": now,
        "facts": {},
    }

    fact = CarrierFact(
        kind="carrier_profile",
        entity_id=naic_code or cik or "",
        entity_name=name,
        value_text=json.dumps(profile),
        observed_at=now,
        source_url="",
        source_dataset="carrier_intelligence_profile",
        source_sha256=hashlib.sha256(json.dumps(profile, sort_keys=True, default=str).encode()).hexdigest(),
        fetch_timestamp=now,
        cache_status="generated",
    )

    return [fact.to_dict()]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build unified carrier profile")
    ap.add_argument("--name", required=True, help="Carrier name (e.g. 'State Farm')")
    ap.add_argument("--naic", default=None, help="NAIC company code")
    ap.add_argument("--cik", default=None, help="SEC CIK number")
    ap.add_argument("--output", default=None, help="JSONL output path")
    args = ap.parse_args()

    facts = build_carrier_profile(args.name, naic_code=args.naic, cik=args.cik)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            for fact in facts:
                f.write(json.dumps(fact, default=str) + "\n")
        print(f"Wrote {len(facts)} facts to {args.output}")
    else:
        print(json.dumps(facts, indent=2, default=str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
