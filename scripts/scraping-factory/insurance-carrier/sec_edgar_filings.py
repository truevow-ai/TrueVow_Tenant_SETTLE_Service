"""
sec_edgar_filings.py — Fetch SEC EDGAR filings for insurance carriers.

Pulls company submissions, filing lists, and full-text search results from
data.sec.gov and efts.sec.gov. Maps 10-K / 8-K filings to CarrierFact output.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from typing import Any

import requests

from carrier_common import (
    CarrierFact,
    cached_get_json,
    assert_valid_cik,
    assert_valid_accession,
    InvariantError,
)

DATA_BASE = "https://data.sec.gov"
EDGAR_BASE = "https://www.sec.gov"
EFTS_BASE = "https://efts.sec.gov/LATEST/search-index"

_TICKER_CACHE_DAYS = 30
_SUBMISSION_CACHE_DAYS = 1
_FTS_CACHE_DAYS = 1


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "User-Agent": "SETTLE Carrier Skill (research) admin@truevow.law",
    }


def _pad_cik(cik: str) -> str:
    cik = assert_valid_cik(cik)
    return cik.zfill(10)


def resolve_cik(ticker: str, cache_days: int = _TICKER_CACHE_DAYS) -> str | None:
    url = f"{EDGAR_BASE}/files/company_tickers.json"
    data = cached_get_json(url, headers=_headers(), cache_days=cache_days)
    if not isinstance(data, dict):
        return None
    target = ticker.upper()
    for _k, v in data.items():
        if isinstance(v, dict) and v.get("ticker", "").upper() == target:
            return str(v.get("cik_str", ""))
    return None


def get_company_submissions(cik: str, cache_days: int = _SUBMISSION_CACHE_DAYS) -> dict[str, Any]:
    cik = assert_valid_cik(cik)
    padded = _pad_cik(cik)
    url = f"{DATA_BASE}/submissions/CIK{padded}.json"
    data = cached_get_json(url, headers=_headers(), cache_days=cache_days)
    return data if isinstance(data, dict) else {}


def list_filings(
    cik: str,
    form_type: str = "10-K",
    limit: int = 20,
    cache_days: int = _SUBMISSION_CACHE_DAYS,
) -> list[dict[str, Any]]:
    subs = get_company_submissions(cik, cache_days=cache_days)
    filings = subs.get("filings", {}).get("recent", {})
    if not filings:
        return []

    results: list[dict[str, Any]] = []
    forms = filings.get("form", [])
    dates = filings.get("filingDate", [])
    accessions = filings.get("accessionNumber", [])
    primary_docs = filings.get("primaryDocument", [])

    for i, form in enumerate(forms):
        if form.upper() == form_type.upper():
            accession = accessions[i] if i < len(accessions) else ""
            cleaned = accession.replace("-", "")
            doc = primary_docs[i] if i < len(primary_docs) else ""
            results.append({
                "cik": cik,
                "form_type": form,
                "filing_date": dates[i] if i < len(dates) else "",
                "accession_number": accession,
                "primary_document": doc,
                "url": f"{EDGAR_BASE}/Archives/edgar/data/{int(cik)}/{cleaned}/{doc}" if doc else "",
            })
            if len(results) >= limit:
                break

    return results


def full_text_search(
    query: str,
    form_types: list[str] | None = None,
    limit: int = 20,
    cache_days: int = _FTS_CACHE_DAYS,
) -> list[dict[str, Any]]:
    if form_types is None:
        form_types = ["10-K", "8-K"]

    params: dict[str, Any] = {
        "q": query,
        "from": 0,
        "size": limit,
    }
    data = cached_get_json(EFTS_BASE, headers=_headers(), params=params, cache_days=cache_days)
    if not isinstance(data, dict):
        return []
    hits = data.get("hits", {}).get("hits", [])
    return [h.get("_source", {}) for h in hits]


def download_filing_index(
    cik: str,
    accession: str,
    cache_days: int = _SUBMISSION_CACHE_DAYS,
) -> dict[str, Any]:
    padded = _pad_cik(cik)
    cleaned = assert_valid_accession(accession).replace("-", "")
    url = f"{EDGAR_BASE}/Archives/edgar/data/{int(cik)}/{cleaned}/index.json"
    data = cached_get_json(url, headers=_headers(), cache_days=cache_days)
    return data if isinstance(data, dict) else {}


def filings_to_carrier_facts(filings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from datetime import datetime, timezone
    import hashlib

    now = datetime.now(timezone.utc).isoformat()
    facts: list[dict[str, Any]] = []

    for filing in filings:
        fact = CarrierFact(
            kind="sec_filing",
            entity_id=str(filing.get("cik", "")),
            entity_name="",
            value_text=json.dumps({
                "form_type": filing.get("form_type"),
                "filing_date": filing.get("filing_date"),
                "accession_number": filing.get("accession_number"),
                "primary_document": filing.get("primary_document"),
                "url": filing.get("url"),
            }),
            observed_at=now,
            source_url=filing.get("url", EDGAR_BASE),
            source_dataset="sec_edgar",
            source_sha256=hashlib.sha256(json.dumps(filing, sort_keys=True, default=str).encode()).hexdigest(),
            fetch_timestamp=now,
            cache_status="live",
        )
        facts.append(fact.to_dict())

    return facts


def main() -> int:
    ap = argparse.ArgumentParser(description="SEC EDGAR filings scraper")
    ap.add_argument("--cik", help="CIK number (e.g. 0000080661 for Progressive)")
    ap.add_argument("--ticker", help="Stock ticker (e.g. PGR)")
    ap.add_argument("--form", default="10-K", help="Form type (default: 10-K)")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--output", default=None, help="JSONL output path")
    args = ap.parse_args()

    cik = args.cik
    if not cik and args.ticker:
        cik = resolve_cik(args.ticker)
        if not cik:
            print(f"Could not resolve ticker: {args.ticker}")
            return 1

    if not cik:
        ap.error("--cik or --ticker is required")

    filings = list_filings(cik, form_type=args.form, limit=args.limit)
    facts = filings_to_carrier_facts(filings)

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
