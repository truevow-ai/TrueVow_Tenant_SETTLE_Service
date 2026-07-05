"""
govdata_bea.py — Bureau of Economic Analysis Regional Price Parities (RPP) data.

Fetches cost-of-living adjustments per state from BEA API and bulk ZIP.
RPP values represent price level relative to national average (100 = US avg).
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from typing import Any

from govdata_common import (
    SettleRow,
    http_get,
    get_env,
    state_to_fips,
    fips_to_state,
    STATE_FIPS,
    print_stderr,
)

BEA_API_BASE = "https://apps.bea.gov/api/data/"
SARPP_ZIP_URL = "https://apps.bea.gov/regional/zip/SARPP.zip"
DEFAULT_LINE_CODE = "all_items"
DEFAULT_LINE_DESC = ("goods", "services_rents", "services_other")


def _bea_api_call(
    method: str,
    dataset: str,
    geo_fips: str,
    year: str = "ALL",
    line_code: str = DEFAULT_LINE_CODE,
) -> dict[str, Any]:
    params = {
        "UserID": get_env("BEA_DATA_API_KEY") or "",
        "method": method,
        "datasetname": dataset,
        "GeoFips": geo_fips,
        "Year": year,
        "LineCode": line_code,
        "ResultFormat": "JSON",
    }
    url = BEA_API_BASE + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    data = http_get(url)
    return json.loads(data)


def get_rpp(state: str, year: int | None = None, line: str = DEFAULT_LINE_CODE) -> list[SettleRow]:
    fips = state_to_fips(state)
    if not fips:
        print_stderr(f"govdata_bea: unknown state {state!r}")
        return []

    geo = f"{fips}000"
    year_str = str(year) if year else "ALL"
    raw = _bea_api_call("GetData", "RegionalProduct", geo, year=year_str, line_code=line)

    rows: list[SettleRow] = []
    data_entries = raw.get("BEAAPI", {}).get("Results", {}).get("Data", [])
    for entry in data_entries:
        val = entry.get("DataValue", "")
        try:
            float_val = float(val.replace(",", ""))
        except (ValueError, AttributeError):
            continue

        row = SettleRow(
            kind="rpp",
            entity_id=entry.get("GeoFips", fips),
            entity_name=entry.get("GeoName", state),
            jurisdiction=fips_to_state(fips) or state,
            value_text=json.dumps({
                "rpp": float_val,
                "line_code": entry.get("LineCode"),
                "line_desc": entry.get("CL_UNIT", ""),
                "year": entry.get("TimePeriod"),
            }),
            observed_at=entry.get("TimePeriod", ""),
            source_url=SARPP_ZIP_URL,
            source_dataset="bea_rpp",
            source_sha256="",
            fetch_timestamp="",
            cache_status="live",
        )
        rows.append(row)

    return rows


def bulk_state_rpp() -> list[SettleRow]:
    rows: list[SettleRow] = []
    for fips, abbr in STATE_FIPS.items():
        rows.extend(get_rpp(abbr))
    return rows


def _bulk_zip_fallback() -> list[SettleRow]:
    content = http_get(SARPP_ZIP_URL)
    rows: list[SettleRow] = []

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for name in zf.namelist():
            if name.endswith(".csv"):
                with zf.open(name) as f:
                    reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))
                    for row_data in reader:
                        geo_fips = row_data.get("GeoFips", "")
                        if len(geo_fips) >= 2:
                            state_fips = geo_fips[:2]
                            rpp_val = row_data.get("RPP", "")
                            try:
                                float_val = float(rpp_val)
                            except (ValueError, AttributeError):
                                continue
                            row = SettleRow(
                                kind="rpp",
                                entity_id=geo_fips,
                                entity_name=row_data.get("GeoName", ""),
                                jurisdiction=fips_to_state(state_fips) or state_fips,
                                value_text=json.dumps({"rpp": float_val}),
                                observed_at="",
                                source_url=SARPP_ZIP_URL,
                                source_dataset="bea_rpp_bulk",
                                source_sha256="",
                                fetch_timestamp="",
                                cache_status="live",
                            )
                            rows.append(row)

    return rows


if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser(description="BEA Regional Price Parities client")
    sub = ap.add_subparsers(dest="cmd")

    p_state = sub.add_parser("state", help="Single-state RPP")
    p_state.add_argument("--state", required=True)
    p_state.add_argument("--year", type=int)
    p_state.add_argument("--line", default=DEFAULT_LINE_CODE)

    p_bulk = sub.add_parser("bulk", help="Bulk all states via API")

    p_zip = sub.add_parser("zip", help="Bulk from ZIP fallback")

    args = ap.parse_args()

    if args.cmd == "state":
        rows = get_rpp(args.state, year=args.year, line=args.line)
    elif args.cmd == "bulk":
        rows = bulk_state_rpp()
    elif args.cmd == "zip":
        rows = _bulk_zip_fallback()
    else:
        ap.print_help()
        rows = []

    for r in rows:
        print(json.dumps(r.to_dict()))
    print(f"Total: {len(rows)} rows", file=sys.stderr)
