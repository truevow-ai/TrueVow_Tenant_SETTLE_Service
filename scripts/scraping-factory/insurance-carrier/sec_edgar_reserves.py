"""
sec_edgar_reserves.py — Fetch SEC loss reserve data for insurance carriers.

Pulls P&C (Property and Casualty) loss reserve concepts from the SEC
XBRL taxonomy via data.sec.gov. Maps to CarrierFact output.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

import requests

from carrier_common import (
    CarrierFact,
    CARRIER_BOUNDS,
    cached_get_json,
    cached_http_get,
    assert_in_range,
    assert_finite,
    assert_valid_cik,
    InvariantError,
)

DATA_BASE = "https://data.sec.gov"
_CACHE_DAYS = 1

P_AND_C_RESERVE_CONCEPTS: list[str] = [
    "LossReserveEstimate",
    "PolicyLiabilitiesAndAccruals",
    "UnpaidLossesAndLossAdjustmentExpenses",
    "ClaimsReserve",
]


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "User-Agent": "SETTLE Carrier Skill (research) admin@truevow.law",
    }


def _pad_cik(cik: str) -> str:
    cik = assert_valid_cik(cik)
    return cik.zfill(10)


def get_concept(
    cik: str,
    concept: str,
    cache_days: int = _CACHE_DAYS,
) -> dict[str, Any]:
    padded = _pad_cik(cik)
    url = f"{DATA_BASE}/api/xbrl/companyconcept/CIK{padded}/us-gaap/{concept}.json"
    data = cached_get_json(url, headers=_headers(), cache_days=cache_days)
    return data if isinstance(data, dict) else {}


def get_frame(
    cik: str,
    concept: str,
    unit: str = "USD",
    cache_days: int = _CACHE_DAYS,
) -> list[dict[str, Any]]:
    concept_data = get_concept(cik, concept, cache_days=cache_days)
    units = concept_data.get("units", {})
    target_key = f"{unit}"
    frames = units.get(target_key, [])
    return frames if isinstance(frames, list) else []


def get_loss_reserves(
    cik: str,
    cache_days: int = _CACHE_DAYS,
) -> dict[str, Any]:
    result: dict[str, Any] = {"cik": cik, "concepts": {}}

    for concept in P_AND_C_RESERVE_CONCEPTS:
        try:
            frames = get_frame(cik, concept, cache_days=cache_days)
            if frames:
                latest = frames[-1] if frames else {}
                val = latest.get("val")
                if val is not None:
                    result["concepts"][concept] = {
                        "latest_value": val,
                        "filing_date": latest.get("end", ""),
                        "fy": latest.get("fy"),
                        "fp": latest.get("fp"),
                        "form": latest.get("form"),
                    }
        except Exception:
            continue

    return result


def reserves_to_carrier_facts(reserves_data: dict[str, Any]) -> list[dict[str, Any]]:
    from datetime import datetime, timezone
    import hashlib

    now = datetime.now(timezone.utc).isoformat()
    facts: list[dict[str, Any]] = []

    for concept, details in reserves_data.get("concepts", {}).items():
        value = details.get("latest_value")
        if value is None:
            continue

        try:
            assert_finite(f"loss_reserve_{concept}", float(value))
        except InvariantError:
            continue

        try:
            assert_in_range("loss_reserve", float(value), *CARRIER_BOUNDS["loss_reserve"])
        except InvariantError:
            pass

        fact = CarrierFact(
            kind="sec_loss_reserve",
            entity_id=str(reserves_data.get("cik", "")),
            entity_name="",
            value_text=json.dumps({
                "concept": concept,
                "latest_value": value,
                "filing_date": details.get("filing_date"),
                "fiscal_year": details.get("fy"),
                "fiscal_period": details.get("fp"),
                "form": details.get("form"),
            }),
            observed_at=now,
            source_url=f"{DATA_BASE}/api/xbrl/companyconcept/CIK{_pad_cik(str(reserves_data.get('cik','')))}/us-gaap/{concept}.json",
            source_dataset="sec_edgar_xbrl_reserves",
            source_sha256=hashlib.sha256(json.dumps(details, sort_keys=True, default=str).encode()).hexdigest(),
            fetch_timestamp=now,
            cache_status="live",
        )
        facts.append(fact.to_dict())

    return facts


def main() -> int:
    ap = argparse.ArgumentParser(description="SEC loss reserve scraper")
    ap.add_argument("--cik", required=True, help="CIK number (e.g. 0000080661)")
    ap.add_argument("--output", default=None, help="JSONL output path")
    args = ap.parse_args()

    reserves = get_loss_reserves(args.cik)
    facts = reserves_to_carrier_facts(reserves)

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
