"""
govdata_cms_pfs_crosscheck.py — Cross-validate embedded CMS PFS RVU/GPCI
values against live CMS bulk data files (RVU25A.zip).

Downloads the official CMS RVU and GPCI CSV files and compares a small
set of known-good values to flag any mapping errors or stale embedded data.
"""

from __future__ import annotations

import csv
import io
import os
import sys
import zipfile
from dataclasses import dataclass, asdict
from typing import Any
from pathlib import Path

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from govdata_common import cached_http_get, sha256_hex, InvariantError, assert_in_range
from govdata_cms_pfs import RVU_2025, GPCI_2025, CONVERSION_FACTOR_2025

CMS_RVU25A_ZIP = "https://www.cms.gov/files/zip/rvu25a.zip"
DEFAULT_TOLERANCE = 0.02


@dataclass
class CrossCheckResult:
    cpt_code: str
    locality: str
    field: str
    embedded_value: float
    live_value: float
    pct_diff: float
    passed: bool


def _parse_pprrvu_row_for(row: dict[str, str], cpt: str, pos: str = "facility") -> dict[str, float] | None:
    hcpcs = row.get("HCPCS", "").strip()
    if hcpcs != cpt:
        return None
    try:
        work = float(row.get("WORK RVU", "0") or "0")
        pe = float(row.get("PE RVU" if pos == "non-facility" else "FAC PE RVU", "0") or "0")
        mp = float(row.get("MP RVU", "0") or "0")
        return {"work_rvu": work, "pe_rvu": pe, "mp_rvu": mp}
    except (ValueError, KeyError):
        return None


def _parse_gpci_row_for(row: dict[str, str], locality: str) -> dict[str, float] | None:
    loc = row.get("LOCALITY", "").strip()
    if loc != locality:
        return None
    try:
        work = float(row.get("WORK GPCI", "0") or "0")
        pe = float(row.get("PE GPCI", "0") or "0")
        mp = float(row.get("MP GPCI", "0") or "0")
        return {"work": work, "pe": pe, "mp": mp}
    except (ValueError, KeyError):
        return None


def fetch_live_rvu_gpci_cf() -> dict[str, Any]:
    content, _resp = cached_http_get(CMS_RVU25A_ZIP)
    result: dict[str, Any] = {"rvu": {}, "gpci": {}, "conversion_factor": None}

    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for name in zf.namelist():
            lower = name.lower()
            if "pprrvu" in lower and name.endswith(".csv"):
                with zf.open(name) as f:
                    reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"))
                    for row in reader:
                        hcpcs = row.get("HCPCS", "").strip()
                        if hcpcs in RVU_2025:
                            result["rvu"][hcpcs] = _parse_pprrvu_row_for(row, hcpcs) or {}

            elif "gpci" in lower and name.endswith(".csv"):
                with zf.open(name) as f:
                    reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"))
                    for row in reader:
                        loc = row.get("LOCALITY", "").strip()
                        if loc in GPCI_2025:
                            result["gpci"][loc] = _parse_gpci_row_for(row, loc) or {}

    return result


def cross_check(
    tolerance: float = DEFAULT_TOLERANCE,
) -> list[CrossCheckResult]:
    results: list[CrossCheckResult] = []
    live = fetch_live_rvu_gpci_cf()

    for cpt, embedded in RVU_2025.items():
        live_rvu = live["rvu"].get(cpt, {})
        for field in ["work_rvu", "pe_rvu_facility", "mp_rvu_facility"]:
            emb_val = embedded.get(field)
            live_field = field.replace("_facility", "")
            live_val = live_rvu.get(live_field) if live_rvu else None
            if emb_val is not None and live_val is not None:
                pct = abs(emb_val - live_val) / max(abs(live_val), 0.01)
                results.append(CrossCheckResult(
                    cpt_code=cpt,
                    locality="",
                    field=field,
                    embedded_value=emb_val,
                    live_value=live_val,
                    pct_diff=round(pct, 4),
                    passed=pct <= tolerance,
                ))

    for loc, embedded in GPCI_2025.items():
        live_gpci = live["gpci"].get(loc, {})
        for field in ["work", "pe", "mp"]:
            emb_val = embedded.get(field)
            live_val = live_gpci.get(field) if live_gpci else None
            if emb_val is not None and live_val is not None:
                pct = abs(emb_val - live_val) / max(abs(live_val), 0.01)
                results.append(CrossCheckResult(
                    cpt_code="",
                    locality=loc,
                    field=field,
                    embedded_value=emb_val,
                    live_value=live_val,
                    pct_diff=round(pct, 4),
                    passed=pct <= tolerance,
                ))

    return results


def main() -> int:
    import json

    results = cross_check()
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {r.cpt_code or r.locality:8s} {r.field:20s} emb={r.embedded_value:10.4f} live={r.live_value:10.4f} diff={r.pct_diff:.4f}")

    print(f"\n{passed}/{len(results)} checks passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
