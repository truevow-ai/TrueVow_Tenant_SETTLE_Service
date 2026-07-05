"""
govdata_cms_pfs.py — CMS Physician Fee Schedule lookups.

Returns Medicare-allowed amounts for CPT codes by locality (GPCI-adjusted).
Used for medical-cost reasonableness checks in settlement valuation.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from govdata_common import (
    SettleRow,
    print_stderr,
    write_csv,
    assert_in_range,
    assert_finite,
    sha256_hex,
    utc_now_iso,
    InvariantError,
    requires_freshness,
    StaleDataError,
)

CMS_PFS_URL = "https://www.cms.gov/medicare/physician-fee-schedule/search"
CMS_RVU_BULK_URL = "https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files"

CONVERSION_FACTOR_2025 = 32.3465
DEFAULT_YEAR = 2025
EMBEDDED_AS_OF = "2026-05-07"
EMBEDDED_MAX_AGE_DAYS = 30

GPCI_2025: dict[str, dict[str, Any]] = {
    "FL-03": {"work": 0.981, "pe": 1.172, "mp": 0.939, "locality_name": "Fort Lauderdale, FL"},
    "FL-99": {"work": 1.000, "pe": 1.000, "mp": 1.000, "locality_name": "Miami, FL"},
    "FL-Rest": {"work": 0.980, "pe": 0.959, "mp": 0.959, "locality_name": "Rest of Florida"},
    "CA-18": {"work": 1.067, "pe": 1.187, "mp": 1.055, "locality_name": "Los Angeles-Long Beach-Anaheim, CA"},
    "NY-01": {"work": 1.052, "pe": 1.178, "mp": 1.062, "locality_name": "Manhattan, NY"},
    "TX-18": {"work": 1.011, "pe": 1.043, "mp": 1.026, "locality_name": "Houston, TX"},
    "IL-16": {"work": 1.027, "pe": 1.061, "mp": 0.982, "locality_name": "Chicago, IL"},
    "National": {"work": 1.000, "pe": 1.000, "mp": 1.000, "locality_name": "National (GPCI=1)"},
}

RVU_2025: dict[str, dict[str, Any]] = {
    "22551": {
        "description": "Arthrodesis, anterior interbody, C2-C7, cervical",
        "work_rvu": 31.48,
        "pe_rvu_facility": 11.04,
        "mp_rvu_facility": 5.53,
    },
    "27447": {
        "description": "Total knee arthroplasty",
        "work_rvu": 20.72,
        "pe_rvu_facility": 8.25,
        "mp_rvu_facility": 3.16,
    },
}

RVU_2024: dict[str, dict[str, Any]] = {}
GPCI_2024: dict[str, dict[str, Any]] = {}
CONVERSION_FACTOR_2024 = 32.7442


def get_medicare_allowed(
    cpt_code: str,
    locality: str = "National",
    place_of_service: str = "facility",
    year: int = DEFAULT_YEAR,
) -> dict[str, Any] | None:
    if year == 2025:
        rvu_data = RVU_2025
        gpci_data = GPCI_2025
        cf = CONVERSION_FACTOR_2025
    elif year == 2024:
        rvu_data = RVU_2024
        gpci_data = GPCI_2024
        cf = CONVERSION_FACTOR_2024
    else:
        rvu_data = RVU_2025
        gpci_data = GPCI_2025
        cf = CONVERSION_FACTOR_2025

    rvu = rvu_data.get(cpt_code)
    gpci = gpci_data.get(locality)
    if not rvu or not gpci:
        return None

    if place_of_service == "facility":
        pe_rvu = rvu["pe_rvu_facility"]
    else:
        pe_rvu = rvu.get("pe_rvu_nonfacility", rvu["pe_rvu_facility"])

    wrvu = rvu["work_rvu"]
    mrvu = rvu.get("mp_rvu_facility", 0.0)

    wrvu_adj = wrvu * gpci["work"]
    pe_adj = pe_rvu * gpci["pe"]
    mp_adj = mrvu * gpci["mp"]

    total_rvu = wrvu_adj + pe_adj + mp_adj
    allowed = total_rvu * cf

    return {
        "cpt_code": cpt_code,
        "description": rvu["description"],
        "locality": locality,
        "locality_name": gpci.get("locality_name", ""),
        "place_of_service": place_of_service,
        "year": year,
        "work_rvu": wrvu,
        "work_gpci": gpci["work"],
        "work_rvu_adjusted": round(wrvu_adj, 4),
        "pe_rvu": pe_rvu,
        "pe_gpci": gpci["pe"],
        "pe_rvu_adjusted": round(pe_adj, 4),
        "mp_rvu": mrvu,
        "mp_gpci": gpci["mp"],
        "mp_rvu_adjusted": round(mp_adj, 4),
        "total_rvu": round(total_rvu, 4),
        "conversion_factor": cf,
        "allowed_amount": round(allowed, 2),
    }


def bulk_pfs_locality(
    locality: str = "National",
    place_of_service: str = "facility",
    year: int = DEFAULT_YEAR,
) -> list[SettleRow]:
    rows: list[SettleRow] = []
    rvu_data = RVU_2025 if year == 2025 else RVU_2024

    for cpt_code in rvu_data:
        result = get_medicare_allowed(cpt_code, locality, place_of_service, year)
        if result:
            row = SettleRow(
                kind="allowed_amount",
                entity_id=cpt_code,
                entity_name=result["description"],
                jurisdiction=locality,
                value_text=json.dumps(result),
                observed_at=f"{year}-01-01",
                source_url=CMS_PFS_URL,
                source_dataset="cms_pfs",
                source_sha256="",
                fetch_timestamp=utc_now_iso(),
                cache_status="embedded",
            )
            rows.append(row)

    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="CMS Physician Fee Schedule lookup")
    ap.add_argument("--cpt", default="22551", help="CPT code (e.g. 22551)")
    ap.add_argument("--locality", default="FL-03", help="GPCI locality (e.g. FL-03)")
    ap.add_argument("--place", default="facility", choices=["facility", "non-facility"])
    ap.add_argument("--year", type=int, default=DEFAULT_YEAR)
    ap.add_argument("--bulk", action="store_true", help="Output all CPTs for locality")
    ap.add_argument("--output", default=None, help="CSV output path")
    args = ap.parse_args()

    if args.bulk:
        rows = bulk_pfs_locality(args.locality, args.place, args.year)
    else:
        result = get_medicare_allowed(args.cpt, args.locality, args.place, args.year)
        if not result:
            print_stderr(f"No data for CPT {args.cpt} in locality {args.locality}")
            return 1
        rows = [
            SettleRow(
                kind="allowed_amount",
                entity_id=args.cpt,
                entity_name=result["description"],
                jurisdiction=args.locality,
                value_text=json.dumps(result),
                observed_at=f"{args.year}-01-01",
                source_url=CMS_PFS_URL,
                source_dataset="cms_pfs",
                source_sha256="",
                fetch_timestamp=utc_now_iso(),
                cache_status="embedded",
            )
        ]

    if args.output:
        write_csv(rows, args.output)
        print(f"Wrote {len(rows)} rows to {args.output}")
    else:
        for r in rows:
            print(json.dumps(r.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
