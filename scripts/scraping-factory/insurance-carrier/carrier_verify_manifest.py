"""
carrier_verify_manifest.py — Verifiable carrier truth assertions.

A set of testable facts about insurance carriers that can be validated
independently against public data. These assertions serve as a smoke-test
manifest to confirm the carrier intelligence pipeline is working correctly.

Each entry is a verifiable claim with a verifier function path and expected value.
"""

from __future__ import annotations

from typing import Any

MANIFEST: list[dict[str, Any]] = [
    # --- Progressive (CIK: 0000080661) ---
    {
        "id": "sec_pgr_cik_resolve",
        "verifier": "sec_resolve_cik",
        "ticker": "PGR",
        "expected": "equals",
        "value": "0000080661",
        "source_url": "https://www.sec.gov/files/company_tickers.json",
    },
    {
        "id": "sec_all_cik_resolve",
        "verifier": "sec_resolve_cik",
        "ticker": "ALL",
        "expected": "equals",
        "value": "0000899051",
        "source_url": "https://www.sec.gov/files/company_tickers.json",
    },
    {
        "id": "sec_pgr_sic_insurance",
        "verifier": "sec_company_sic",
        "cik": "0000080661",
        "expected": "in_range",
        "source_url": "https://data.sec.gov/submissions/CIK0000080661.json",
    },
    {
        "id": "sec_pgr_name_contains_progressive",
        "verifier": "sec_company_name",
        "cik": "0000080661",
        "expected": "contains_ci",
        "value": "progressive",
        "source_url": "https://data.sec.gov/submissions/CIK0000080661.json",
    },
    {
        "id": "sec_pgr_10k_filings_exist",
        "verifier": "sec_filings_count",
        "cik": "0000080661",
        "form_type": "10-K",
        "expected": "gte",
        "value": 1,
        "source_url": "sec_edgar_filings.py",
    },
    {
        "id": "sec_pgr_reserves_positive",
        "verifier": "sec_latest_reserves",
        "cik": "0000080661",
        "expected": "gte",
        "value": 0,
        "source_url": "sec_edgar_reserves.py",
    },
    # --- State Farm (NAIC: 25178) ---
    {
        "id": "naic_state_farm_25178_resolves",
        "verifier": "naic_rows_count",
        "naic": "25178",
        "expected": "gte",
        "value": 1,
        "source_url": "https://data.texas.gov/resource/pa9u-9s9w.json",
    },
    {
        "id": "naic_state_farm_name_has_state_farm",
        "verifier": "naic_top_name",
        "naic": "25178",
        "expected": "contains_ci",
        "value": "state farm",
        "source_url": "https://data.texas.gov/resource/pa9u-9s9w.json",
    },
    # --- Cross-check ---
    {
        "id": "crosscheck_state_farm_25178_high",
        "verifier": "crosscheck_confidence",
        "entity_a_name": "State Farm",
        "entity_b_name": "State Farm Mutual",
        "expected": "gte",
        "value": "high",
        "source_url": "carrier_crosscheck.py",
    },
    {
        "id": "crosscheck_pgr_high",
        "verifier": "crosscheck_confidence",
        "entity_a_name": "Progressive",
        "entity_b_name": "The Progressive Corporation",
        "expected": "gte",
        "value": "high",
        "source_url": "carrier_crosscheck.py",
    },
    # --- Profile ---
    {
        "id": "profile_pgr_fact_count_nonzero",
        "verifier": "profile_fact_count",
        "entity_name": "Progressive",
        "expected": "gte",
        "value": 1,
        "source_url": "carrier_profile.py",
    },
]


def __repr__() -> str:
    return f"carrier_verify_manifest: {len(MANIFEST)} assertions"
