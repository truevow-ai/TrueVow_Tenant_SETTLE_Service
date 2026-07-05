"""
naic_complaints.py — Fetch NAIC complaint index data from Texas Socrata open data portal.

The Texas Department of Insurance publishes NAIC-compliant complaint records
via data.texas.gov. This scraper pulls the complaint index and raw complaint
records, then maps them to CarrierFact outputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

import requests

from carrier_common import (
    CarrierFact,
    CARRIER_BOUNDS,
    cached_get_json,
    assert_in_range,
    assert_valid_naic,
    InvariantError,
)

TX_SOCRATA_BASE = "https://data.texas.gov/resource"
COMPLAINT_INDEX_DATASET = "pa9u-9s9w"
COMPLAINT_RECORDS_DATASET = "jjc8-mxkg"
_CACHE_DAYS = 7


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "User-Agent": "SETTLE Carrier Skill (research)",
    }


def get_complaint_index(
    offset: int = 0,
    limit: int = 1000,
    naic_code: str | None = None,
    year: int | None = None,
    cache_days: int = _CACHE_DAYS,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "$offset": offset,
        "$limit": limit,
        "$order": "company_name",
    }
    if naic_code:
        assert_valid_naic(naic_code)
        params["naic"] = naic_code
    if year:
        params["complaint_year"] = str(year)

    url = f"{TX_SOCRATA_BASE}/{COMPLAINT_INDEX_DATASET}"
    data = cached_get_json(url, headers=_headers(), params=params, cache_days=cache_days)
    return data if isinstance(data, list) else [data]


def get_raw_complaints(
    offset: int = 0,
    limit: int = 1000,
    naic_code: str | None = None,
    year: int | None = None,
    cache_days: int = _CACHE_DAYS,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "$offset": offset,
        "$limit": limit,
        "$order": ":id",
    }
    if naic_code:
        assert_valid_naic(naic_code)
        params["naic"] = naic_code
    if year:
        params["complaint_year"] = str(year)

    url = f"{TX_SOCRATA_BASE}/{COMPLAINT_RECORDS_DATASET}"
    data = cached_get_json(url, headers=_headers(), params=params, cache_days=cache_days)
    return data if isinstance(data, list) else [data]


def to_carrier_facts(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()

    for row in raw:
        naic = row.get("naic", "")
        try:
            assert_valid_naic(str(naic))
        except InvariantError:
            continue

        complaint_count = int(row.get("complaint_count", 0) or 0)
        try:
            assert_in_range("complaint_count", complaint_count, *CARRIER_BOUNDS["complaint_count"])
        except InvariantError:
            continue

        fact = CarrierFact(
            kind="naic_complaint_index",
            entity_id=str(naic),
            entity_name=str(row.get("company_name", "")),
            value_text=json.dumps({
                "complaint_count": complaint_count,
                "complaint_year": row.get("complaint_year"),
                "coverage_type": row.get("coverage_type"),
                "complaint_type": row.get("complaint_type"),
            }),
            observed_at=now,
            source_url=f"{TX_SOCRATA_BASE}/{COMPLAINT_INDEX_DATASET}",
            source_dataset="texas_naic_complaints",
            source_sha256=hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest(),
            fetch_timestamp=now,
            cache_status="live",
        )
        facts.append(fact.to_dict())

    return facts


def main() -> int:
    ap = argparse.ArgumentParser(description="NAIC complaint index scraper")
    ap.add_argument("--naic", help="NAIC company code (e.g. 25178 for State Farm)")
    ap.add_argument("--year", type=int, help="Complaint year")
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--output", default=None, help="JSONL output path")
    args = ap.parse_args()

    raw = get_raw_complaints(
        naic_code=args.naic,
        year=args.year,
        limit=args.limit,
    )
    facts = to_carrier_facts(raw)

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
