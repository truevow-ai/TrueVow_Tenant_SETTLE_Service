"""
fl_oir_filings.py — Fetch Florida Office of Insurance Regulation (OIR) filings.

Pulls public records from the Florida IRFS search portal and industry reports
from floir.com. Maps to CarrierFact output.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any

import requests

from carrier_common import (
    CarrierFact,
    cached_get_text,
    requires_freshness,
)

IRFS_BASE = "https://irfssearch.floir.gov"
INDUSTRY_REPORTS_URL = "https://www.floir.com/resources-and-reports/industry-reports"
USER_AGENT = "SETTLE Carrier Skill (research)"
_CACHE_DAYS = 7
EMBEDDED_AS_OF = "2026-05-07"


def _headers() -> dict[str, str]:
    return {
        "Accept": "text/html,application/xhtml+xml",
        "User-Agent": USER_AGENT,
    }


def irfs_quick_search(
    query: str,
    naic_code: str | None = None,
    cache_days: int = _CACHE_DAYS,
) -> str:
    params: dict[str, str] = {"query": query}
    if naic_code:
        params["naic"] = naic_code

    url = f"{IRFS_BASE}/search"
    text = cached_get_text(url, headers=_headers(), cache_days=cache_days)
    return text


def list_industry_reports(cache_days: int = 30) -> str:
    text = cached_get_text(INDUSTRY_REPORTS_URL, headers=_headers(), cache_days=cache_days)
    return text


def get_public_records_categories(
    category: str = "property-casualty",
    cache_days: int = _CACHE_DAYS,
) -> list[dict[str, Any]]:
    text = irfs_quick_search(category, cache_days=cache_days)

    records: list[dict[str, Any]] = []
    href_pattern = re.findall(r'href="([^"]+)"', text)
    name_pattern = re.findall(r'>([^<]{5,200})<', text)

    for i, href in enumerate(href_pattern):
        if "record" in href.lower() or "document" in href.lower() or "filing" in href.lower():
            name = name_pattern[i] if i < len(name_pattern) else ""
            full_url = href if href.startswith("http") else f"{IRFS_BASE}{href}"
            records.append({
                "url": full_url,
                "name": name.strip(),
                "category": category,
            })

    return records


def to_carrier_facts(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import hashlib

    now = datetime.now(timezone.utc).isoformat()
    facts: list[dict[str, Any]] = []

    for rec in records:
        fact = CarrierFact(
            kind="fl_oir_report",
            entity_id="",
            entity_name=rec.get("name", ""),
            value_text=json.dumps(rec),
            observed_at=now,
            source_url=rec.get("url", INDUSTRY_REPORTS_URL),
            source_dataset="fl_oir_public_records",
            source_sha256=hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode()).hexdigest(),
            fetch_timestamp=now,
            cache_status="live",
        )
        facts.append(fact.to_dict())

    return facts


def main() -> int:
    ap = argparse.ArgumentParser(description="Florida OIR filings scraper")
    ap.add_argument("--category", default="property-casualty", help="Record category")
    ap.add_argument("--output", default=None, help="JSONL output path")
    ap.add_argument("--list-reports", action="store_true", help="List industry reports HTML")
    args = ap.parse_args()

    if args.list_reports:
        html = list_industry_reports()
        print(html[:5000])
        return 0

    records = get_public_records_categories(args.category)
    facts = to_carrier_facts(records)

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
