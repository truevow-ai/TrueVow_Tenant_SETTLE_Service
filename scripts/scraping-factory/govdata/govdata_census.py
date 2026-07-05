"""
govdata_census.py — Census ACS 5-year demographic data.

Fetches median income, median age, population, and education attainment
from the Census Bureau's American Community Survey (ACS) 5-year estimates.
"""

from __future__ import annotations

import json
from typing import Any

from govdata_common import (
    SettleRow,
    http_get,
    get_env,
    state_to_fips,
    fips_to_state,
    print_stderr,
)

CENSUS_BASE = "https://api.census.gov/data"
DEFAULT_ACS_YEAR = 2023

VAR_MEDIAN_INCOME = "B19013_001E"
VAR_MEDIAN_AGE = "B01002_001E"
VAR_TOTAL_POP = "B01003_001E"
VAR_EDU_BA = "B15003_022E"
VAR_EDU_MA = "B15003_023E"
VAR_EDU_PROF = "B15003_024E"
VAR_EDU_DOC = "B15003_025E"
VAR_EDU_TOTAL = "B15003_001E"

CORE_VARS = [
    VAR_MEDIAN_INCOME, VAR_MEDIAN_AGE, VAR_TOTAL_POP,
    VAR_EDU_BA, VAR_EDU_MA, VAR_EDU_PROF, VAR_EDU_DOC, VAR_EDU_TOTAL,
]


def _fetch_acs(year: int, vars_list: list[str], geography: str) -> dict[str, Any] | None:
    api_key = get_env("CENSUS_DATA_API_KEY") or ""
    var_str = ",".join(["NAME"] + vars_list)
    url = f"{CENSUS_BASE}/{year}/acs/acs5?get={var_str}&for={geography}"
    if api_key:
        url += f"&key={api_key}"
    raw = http_get(url)
    data = json.loads(raw)
    if not isinstance(data, list) or len(data) < 2:
        return None
    headers = data[0]
    values = data[1]
    return dict(zip(headers, values))


def _num(val: str | None) -> float:
    try:
        return float(val or "0")
    except (ValueError, TypeError):
        return 0.0


def _rows_from_record(record: dict[str, Any], geo: str) -> list[SettleRow]:
    rows: list[SettleRow] = []

    median_income = _num(record.get(VAR_MEDIAN_INCOME))
    median_age = _num(record.get(VAR_MEDIAN_AGE))
    total_pop = _num(record.get(VAR_TOTAL_POP))
    edu_total = _num(record.get(VAR_EDU_TOTAL))
    edu_ba = _num(record.get(VAR_EDU_BA))
    edu_ma = _num(record.get(VAR_EDU_MA))
    edu_prof = _num(record.get(VAR_EDU_PROF))
    edu_doc = _num(record.get(VAR_EDU_DOC))

    name = record.get("NAME", geo)
    year_str = record.get("year", "")

    metrics = [
        ("median_income", median_income),
        ("median_age", median_age),
        ("total_population", total_pop),
    ]
    if edu_total > 0:
        edu_pct = round(((edu_ba + edu_ma + edu_prof + edu_doc) / edu_total) * 100, 2)
        metrics.append(("education_pct_bachelors_plus", edu_pct))

    for kind, value in metrics:
        row = SettleRow(
            kind=kind,
            entity_id=geo,
            entity_name=name,
            jurisdiction=geo,
            value_text=json.dumps({"value": value}),
            observed_at=str(year_str),
            source_url=f"{CENSUS_BASE}/{year_str}/acs/acs5",
            source_dataset="census_acs5",
            source_sha256="",
            fetch_timestamp="",
            cache_status="live",
        )
        rows.append(row)

    return rows


def _matrix_to_records(headers: list[str], all_values: list[list[str]]) -> list[dict[str, Any]]:
    records = []
    for values in all_values:
        rec = dict(zip(headers, values))
        records.append(rec)
    return records


def get_state_acs(state: str, year: int = DEFAULT_ACS_YEAR) -> list[SettleRow]:
    fips = state_to_fips(state)
    if not fips:
        print_stderr(f"govdata_census: unknown state {state!r}")
        return []

    record = _fetch_acs(year, CORE_VARS, f"state:{fips}")
    if not record:
        return []
    record["year"] = year
    return _rows_from_record(record, f"state:{fips}")


def get_county_acs(state: str, county: str | None = None, year: int = DEFAULT_ACS_YEAR) -> list[SettleRow]:
    fips = state_to_fips(state)
    if not fips:
        return []

    if county:
        raw = http_get(
            f"{CENSUS_BASE}/{year}/acs/acs5?get={','.join(['NAME'] + CORE_VARS)}"
            f"&for=county:{county}&in=state:{fips}"
            + (f"&key={get_env('CENSUS_DATA_API_KEY') or ''}" if get_env("CENSUS_DATA_API_KEY") else "")
        )
        data = json.loads(raw)
        if not isinstance(data, list) or len(data) < 2:
            return []
        headers = data[0]
        values = data[1]
        record = dict(zip(headers, values))
        record["year"] = year
        return _rows_from_record(record, f"county:{county}, state:{fips}")

    records = []
    raw = http_get(
        f"{CENSUS_BASE}/{year}/acs/acs5?get={','.join(['NAME'] + CORE_VARS)}"
        f"&for=county:*&in=state:{fips}"
        + (f"&key={get_env('CENSUS_DATA_API_KEY') or ''}" if get_env("CENSUS_DATA_API_KEY") else "")
    )
    data = json.loads(raw)
    if not isinstance(data, list) or len(data) < 2:
        return []
    headers = data[0]
    all_values = data[1:]
    records = _matrix_to_records(headers, all_values)
    for rec in records:
        rec["year"] = year
    rows: list[SettleRow] = []
    for rec in records:
        rows.extend(_rows_from_record(rec, f"county:{rec.get('county','')}, state:{fips}"))
    return rows


def bulk_states_acs(year: int = DEFAULT_ACS_YEAR) -> list[SettleRow]:
    rows: list[SettleRow] = []
    from govdata_common import STATE_ABBR_TO_FIPS
    for abbr in STATE_ABBR_TO_FIPS:
        rows.extend(get_state_acs(abbr, year=year))
    return rows


def bulk_counties_acs(year: int = DEFAULT_ACS_YEAR) -> list[SettleRow]:
    rows: list[SettleRow] = []
    from govdata_common import STATE_ABBR_TO_FIPS
    for abbr in STATE_ABBR_TO_FIPS:
        rows.extend(get_county_acs(abbr, year=year))
    return rows


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Census ACS 5-year client")
    sub = ap.add_subparsers(dest="cmd")

    p_state = sub.add_parser("state", help="Single-state ACS snapshot")
    p_state.add_argument("--state", required=True)
    p_state.add_argument("--year", type=int, default=DEFAULT_ACS_YEAR)

    p_county = sub.add_parser("county", help="County-level ACS snapshot")
    p_county.add_argument("--state", required=True)
    p_county.add_argument("--year", type=int, default=DEFAULT_ACS_YEAR)

    p_bulk_s = sub.add_parser("bulk-states")
    p_bulk_s.add_argument("--year", type=int, default=DEFAULT_ACS_YEAR)

    p_bulk_c = sub.add_parser("bulk-counties")
    p_bulk_c.add_argument("--year", type=int, default=DEFAULT_ACS_YEAR)

    args = ap.parse_args()

    if args.cmd == "state":
        rows = get_state_acs(args.state, year=args.year)
    elif args.cmd == "county":
        rows = get_county_acs(args.state, year=args.year)
    elif args.cmd == "bulk-states":
        rows = bulk_states_acs(year=args.year)
    elif args.cmd == "bulk-counties":
        rows = bulk_counties_acs(year=args.year)
    else:
        ap.print_help()
        rows = []

    for r in rows:
        print(json.dumps(r.to_dict()))
    print(f"Total: {len(rows)} rows", file=sys.stderr)
