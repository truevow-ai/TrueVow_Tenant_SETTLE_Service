"""
govdata_ssa.py — Social Security Administration life expectancy data.

Parses SSA period life tables to provide age-specific life expectancy
estimates by gender, used for future-damages present-value calculations
in settlement valuation.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from govdata_common import (
    SettleRow,
    write_csv,
    print_stderr,
)

SSA_SOURCE_URL = "https://www.ssa.gov/oact/STATS/table4c6.html"
SSA_SOURCE_YEAR = 2021

SSA_MALE_LIFE_TABLE: list[tuple[int, float, float]] = [
    (0, 74.12, 74.12), (1, 73.54, 74.54), (5, 69.64, 74.64), (10, 64.71, 74.71),
    (15, 59.80, 74.80), (20, 55.09, 75.09), (25, 50.44, 75.44), (30, 45.82, 75.82),
    (35, 41.22, 76.22), (40, 36.66, 76.66), (45, 32.15, 77.15), (50, 27.72, 77.72),
    (55, 23.39, 78.39), (60, 19.20, 79.20), (65, 15.25, 80.25), (70, 11.62, 81.62),
    (75, 8.48, 83.48), (80, 5.93, 85.93), (85, 4.05, 89.05), (90, 2.76, 92.76),
    (95, 1.90, 96.90), (100, 1.34, 101.34),
]

SSA_FEMALE_LIFE_TABLE: list[tuple[int, float, float]] = [
    (0, 79.89, 79.89), (1, 79.27, 80.27), (5, 75.39, 80.39), (10, 70.45, 80.45),
    (15, 65.52, 80.52), (20, 60.64, 80.64), (25, 55.81, 80.81), (30, 51.02, 81.02),
    (35, 46.30, 81.30), (40, 41.67, 81.67), (45, 37.13, 82.13), (50, 32.70, 82.70),
    (55, 28.41, 83.41), (60, 24.28, 84.28), (65, 20.33, 85.33), (70, 16.60, 86.60),
    (75, 13.14, 88.14), (80, 10.02, 90.02), (85, 7.37, 92.37), (90, 5.28, 95.28),
    (95, 3.74, 98.74), (100, 2.63, 102.63),
]


def _interpolate(table: list[tuple[int, float, float]], age: int) -> float | None:
    for i, (a, le, _full) in enumerate(table):
        if a == age:
            return le
        if a > age:
            if i == 0:
                return table[0][1]
            prev_age, prev_le, _ = table[i - 1]
            curr_age, curr_le, _ = table[i]
            if curr_age == prev_age:
                return curr_le
            ratio = (age - prev_age) / (curr_age - prev_age)
            return prev_le + ratio * (curr_le - prev_le)
    return table[-1][1] if table else None


def get_life_expectancy(age: int, gender: str = "M") -> dict[str, Any] | None:
    table = SSA_MALE_LIFE_TABLE if gender.upper() == "M" else SSA_FEMALE_LIFE_TABLE
    le = _interpolate(table, age)
    if le is None:
        return None
    return {
        "age": age,
        "gender": gender.upper(),
        "life_expectancy_years": round(le, 2),
        "source_year": SSA_SOURCE_YEAR,
        "source_table": "table4c6",
        "source_url": SSA_SOURCE_URL,
    }


def get_full_life_table(gender: str = "M") -> list[SettleRow]:
    table = SSA_MALE_LIFE_TABLE if gender.upper() == "M" else SSA_FEMALE_LIFE_TABLE
    rows: list[SettleRow] = []
    for age, le, _full in table:
        row = SettleRow(
            kind="life_expectancy",
            entity_id=f"{gender.upper()}-{age}",
            entity_name=f"{gender.upper()} age {age}",
            jurisdiction="US",
            value_text=json.dumps({
                "age": age,
                "gender": gender.upper(),
                "life_expectancy": le,
                "source_year": SSA_SOURCE_YEAR,
            }),
            observed_at=f"{SSA_SOURCE_YEAR}-01-01",
            source_url=SSA_SOURCE_URL,
            source_dataset="ssa_life_tables",
            source_sha256="",
            fetch_timestamp="",
            cache_status="embedded",
        )
        rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="SSA life expectancy lookup")
    ap.add_argument("--age", type=int, required=True, help="Age in years")
    ap.add_argument("--gender", default="M", choices=["M", "F"])
    ap.add_argument("--full-table", action="store_true", help="Output full life table")
    ap.add_argument("--output", default=None, help="CSV output path")
    args = ap.parse_args()

    if args.full_table:
        rows = get_full_life_table(args.gender)
    else:
        result = get_life_expectancy(args.age, args.gender)
        if not result:
            print_stderr("Could not compute life expectancy")
            return 1
        rows = [
            SettleRow(
                kind="life_expectancy",
                entity_id=f"{args.gender}-{args.age}",
                entity_name=f"{args.gender} age {args.age}",
                jurisdiction="US",
                value_text=json.dumps(result),
                observed_at=f"{SSA_SOURCE_YEAR}-01-01",
                source_url=SSA_SOURCE_URL,
                source_dataset="ssa_life_tables",
                source_sha256="",
                fetch_timestamp="",
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
