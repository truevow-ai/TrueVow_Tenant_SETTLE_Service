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
import sys
from datetime import datetime, timezone
from typing import Any


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
    # The Texas complaint-index dataset (pa9u-9s9w) keys carriers by `naic_id`
    # and `year`; complaint tallies live in col1/col2/col3. The raw complaint
    # records dataset carries no carrier identity, so all carrier-scoped
    # lookups go through this index.
    params: dict[str, Any] = {
        "$offset": offset,
        "$limit": limit,
        "$order": "company_name",
    }
    if naic_code:
        assert_valid_naic(naic_code)
        params["naic_id"] = naic_code
    if year:
        params["year"] = str(year)

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
    # Carrier-scoped complaint data is only available via the index dataset
    # (the raw-records dataset has no NAIC/company column). Delegate so callers
    # passing a naic_code get meaningful, carrier-attributed rows.
    if naic_code:
        return get_complaint_index(
            offset=offset, limit=limit, naic_code=naic_code,
            year=year, cache_days=cache_days,
        )

    params: dict[str, Any] = {
        "$offset": offset,
        "$limit": limit,
        "$order": ":id",
    }
    url = f"{TX_SOCRATA_BASE}/{COMPLAINT_RECORDS_DATASET}"
    data = cached_get_json(url, headers=_headers(), params=params, cache_days=cache_days)
    return data if isinstance(data, list) else [data]


def to_carrier_facts(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()

    for row in raw:
        # Index dataset (pa9u-9s9w) uses naic_id; tolerate the older `naic` key.
        naic = row.get("naic_id") or row.get("naic", "")
        try:
            assert_valid_naic(str(naic))
        except InvariantError:
            continue

        # Complaint tallies are split across col1/col2/col3 (confirmed/
        # questioned/total); sum whatever is numeric. Fall back to an explicit
        # complaint_count if a future schema provides one.
        def _int(v: Any) -> int:
            try:
                return int(float(v))
            except (TypeError, ValueError):
                return 0

        if "complaint_count" in row:
            complaint_count = _int(row.get("complaint_count"))
        else:
            complaint_count = _int(row.get("col1")) + _int(row.get("col2")) + _int(row.get("col3"))

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
                "complaint_year": row.get("year") or row.get("complaint_year"),
                "coverage_type": row.get("type_cd") or row.get("coverage_type"),
                "org_id": row.get("org_id"),
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
