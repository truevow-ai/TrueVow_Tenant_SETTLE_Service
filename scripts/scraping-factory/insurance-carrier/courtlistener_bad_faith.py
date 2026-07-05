"""
courtlistener_bad_faith.py — Search CourtListener for bad-faith and punitive
damages opinions involving insurance carriers.

Uses the CourtListener REST API v4 to search for opinions tagged with
bad-faith / punitive damages keywords and maps them to CarrierFact output.
"""

from __future__ import annotations

import argparse
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
    assert_finite,
)

CL_BASE = "https://www.courtlistener.com/api/rest/v4"
_CACHE_DAYS = 1


def _headers() -> dict[str, str]:
    token = os.getenv("COURTLISTENER_API_KEY", "")
    h = {
        "Accept": "application/json",
        "User-Agent": "SETTLE Carrier Skill (research)",
    }
    if token:
        h["Authorization"] = f"Token {token}"
    return h


def search_bad_faith(
    carrier_name: str,
    state: str | None = None,
    limit: int = 50,
    cache_days: int = _CACHE_DAYS,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "q": f'"{carrier_name}" AND (bad faith OR bad-faith)',
        "type": "o",
        "order_by": "dateFiled desc",
        "page_size": min(limit, 100),
    }
    if state:
        params["court__jurisdiction__contains"] = state

    url = f"{CL_BASE}/search/"
    data = cached_get_json(url, headers=_headers(), params=params, cache_days=cache_days)
    if not isinstance(data, dict):
        return []
    return data.get("results", [])


def search_punitive(
    carrier_name: str,
    state: str | None = None,
    limit: int = 50,
    cache_days: int = _CACHE_DAYS,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "q": f'"{carrier_name}" AND (punitive damages OR exemplary damages)',
        "type": "o",
        "order_by": "dateFiled desc",
        "page_size": min(limit, 100),
    }
    if state:
        params["court__jurisdiction__contains"] = state

    url = f"{CL_BASE}/search/"
    data = cached_get_json(url, headers=_headers(), params=params, cache_days=cache_days)
    if not isinstance(data, dict):
        return []
    return data.get("results", [])


def get_opinion(opinion_id: int, cache_days: int = _CACHE_DAYS) -> dict[str, Any] | None:
    url = f"{CL_BASE}/opinions/{opinion_id}/"
    try:
        data = cached_get_json(url, headers=_headers(), cache_days=cache_days)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def search_result_to_carrier_fact(result: dict[str, Any], kind: str) -> dict[str, Any] | None:
    import hashlib

    now = datetime.now(timezone.utc).isoformat()
    opinion_id = result.get("id")
    if not opinion_id:
        return None

    opinion = get_opinion(int(opinion_id))
    if not opinion:
        return None

    opinion_text = opinion.get("plain_text", "") or opinion.get("html_with_citations", "")
    snippet = (opinion_text[:500] + "...") if len(opinion_text) > 500 else opinion_text

    fact = CarrierFact(
        kind=kind,
        entity_id="",
        entity_name=result.get("caseName", ""),
        value_text=json.dumps({
            "court": result.get("court", ""),
            "date_filed": result.get("dateFiled", ""),
            "docket_number": result.get("docketNumber", ""),
            "citation": result.get("citation", ""),
            "snippet": snippet,
            "opinion_id": opinion_id,
        }),
        observed_at=now,
        source_url=result.get("absolute_url", f"https://www.courtlistener.com{result.get('absolute_url','')}"),
        source_dataset="courtlistener_bad_faith_opinions",
        source_sha256=hashlib.sha256(json.dumps(result, sort_keys=True, default=str).encode()).hexdigest(),
        fetch_timestamp=now,
        cache_status="live",
    )
    return fact.to_dict()


def main() -> int:
    ap = argparse.ArgumentParser(description="CourtListener bad-faith opinion scraper")
    ap.add_argument("--carrier", required=True, help="Carrier name (e.g. 'State Farm')")
    ap.add_argument("--state", help="State abbreviation (e.g. FL, CA)")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--output", default=None, help="JSONL output path")
    args = ap.parse_args()

    bad_faith_results = search_bad_faith(args.carrier, args.state, limit=args.limit)
    punitive_results = search_punitive(args.carrier, args.state, limit=args.limit)

    facts: list[dict[str, Any]] = []
    for r in bad_faith_results:
        fact = search_result_to_carrier_fact(r, "bad_faith_opinion")
        if fact:
            facts.append(fact)
    for r in punitive_results:
        fact = search_result_to_carrier_fact(r, "punitive_damages_opinion")
        if fact:
            facts.append(fact)

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
