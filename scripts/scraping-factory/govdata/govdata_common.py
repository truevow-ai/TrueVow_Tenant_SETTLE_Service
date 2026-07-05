"""
govdata_common.py — Shared infrastructure for the govdata scraping skill.

Provides:
  - SettleRow: canonical govdata record format
  - http_get / http_post_json: network primitives with fallback
  - cached_http_get: file-system caching for slow APIs
  - State FIPS/abbreviation/name mappings
  - Validation helpers (assert_in_range, assert_finite)
  - Staleness guard (requires_freshness, StaleDataError)
  - write_csv / write_jsonl: batch output helpers
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Iterable

try:
    import requests

    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False
    import urllib.request
    import urllib.parse
    import urllib.error

DEFAULT_UA = "SETTLE-govdata-skill/1.0 (carrier-skill@example.com)"


def http_get(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> bytes:
    if _HAS_REQUESTS:
        resp = requests.get(url, headers=headers or {}, timeout=timeout)
        resp.raise_for_status()
        return resp.content
    else:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()


def http_post_json(url: str, data: Any, headers: dict[str, str] | None = None, timeout: int = 30) -> Any:
    if _HAS_REQUESTS:
        resp = requests.post(url, json=data, headers=headers or {}, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    else:
        body = json.dumps(data).encode()
        h = (headers or {}).copy()
        h["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())


def _env_get(key: str) -> str | None:
    return os.environ.get(key)


CACHE_ROOT = os.path.join(os.path.expanduser("~"), ".cache", "govdata")
_CACHE_INDEX_PATH = os.path.join(CACHE_ROOT, "index.json")


@dataclass
class CachedResponse:
    url: str
    status_code: int
    content_type: str
    sha256: str
    fetched_at: str
    size_bytes: int
    cache_hit: bool = False


def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:24]


def _load_index() -> dict[str, Any]:
    if os.path.exists(_CACHE_INDEX_PATH):
        try:
            with open(_CACHE_INDEX_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_index(idx: dict[str, Any]) -> None:
    os.makedirs(CACHE_ROOT, exist_ok=True)
    with open(_CACHE_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=2)


def cached_http_get(
    url: str,
    headers: dict[str, str] | None = None,
    cache_days: int = 7,
    timeout: int = 30,
) -> tuple[bytes, CachedResponse]:
    os.makedirs(CACHE_ROOT, exist_ok=True)
    key = _cache_key(url)
    cache_path = os.path.join(CACHE_ROOT, key)
    idx = _load_index()

    if key in idx:
        entry = idx[key]
        age = time.time() - entry.get("fetched_at_unix", 0)
        if age < cache_days * 86400 and os.path.exists(cache_path):
            with open(cache_path, "rb") as f:
                content = f.read()
            cr = CachedResponse(**entry)
            cr.cache_hit = True
            return content, cr

    content = http_get(url, headers=headers, timeout=timeout)
    sha = hashlib.sha256(content).hexdigest()
    fetched_at = datetime.now(timezone.utc).isoformat()

    with open(cache_path, "wb") as f:
        f.write(content)

    entry = {
        "url": url,
        "status_code": 200,
        "content_type": "application/octet-stream",
        "sha256": sha,
        "fetched_at": fetched_at,
        "fetched_at_unix": time.time(),
        "size_bytes": len(content),
        "cache_hit": False,
    }
    idx[key] = entry
    _save_index(idx)

    return content, CachedResponse(**entry)


def cache_stats() -> dict[str, int]:
    idx = _load_index()
    hit = sum(1 for _v in idx.values() if _v.get("cache_hit", False))
    return {"total_entries": len(idx), "cache_hits": hit}


class InvariantError(ValueError):
    pass


CMS_BOUNDS: dict[str, tuple[float, float]] = {
    "allowed_amount": (0.0, 500_000.0),
    "rvu_work": (0.0, 1_000.0),
    "rvu_pe": (0.0, 2_000.0),
    "rvu_mp": (0.0, 1_000.0),
    "conversion_factor": (0.0, 100.0),
    "gpci_work": (0.5, 3.0),
    "gpci_pe": (0.5, 3.0),
    "gpci_mp": (0.5, 3.0),
    "life_expectancy": (0.0, 120.0),
    "median_income": (0.0, 500_000.0),
    "total_population": (0.0, 50_000_000.0),
}


def assert_in_range(label: str, value: float, lo: float, hi: float) -> None:
    if not (lo <= value <= hi):
        raise InvariantError(f"{label} {value} out of bounds [{lo}, {hi}]")


def assert_finite(label: str, value: float) -> None:
    import math
    if not math.isfinite(value):
        raise InvariantError(f"{label} is not finite: {value}")


class StaleDataError(RuntimeError):
    pass


def days_since(timestamp: str) -> float:
    from datetime import datetime, timezone, timedelta
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).total_seconds() / 86400
    except Exception:
        return float("inf")


def requires_freshness(max_age_days: int = 7) -> bool:
    return True


VALID_METRIC_TYPES: frozenset[str] = frozenset({
    "allowed_amount", "rvu", "gpci", "life_expectancy",
    "median_income", "total_population", "rpp", "education_pct",
})
_VALID_CACHE_STATUSES: frozenset[str] = frozenset({"hit", "miss", "stale"})


def sha256_hex(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SettleRow:
    kind: str
    entity_id: str
    entity_name: str
    jurisdiction: str
    value_text: str
    observed_at: str
    source_url: str
    source_dataset: str
    source_sha256: str
    fetch_timestamp: str
    cache_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_csv(rows: Iterable[SettleRow], path: str) -> int:
    try:
        first = next(iter(rows))
    except StopIteration:
        return 0
    all_rows = [first] + list(rows)
    fieldnames = [f.name for f in SettleRow.__dataclass_fields__.values()]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in all_rows:
            w.writerow(r.to_dict())
    return len(all_rows)


def write_jsonl(rows: Iterable[SettleRow], path: str) -> int:
    count = 0
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r.to_dict(), default=str) + "\n")
            count += 1
    return count


STATE_FIPS: dict[str, str] = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
    "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
    "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
    "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
    "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
    "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY",
}

STATE_ABBR_TO_FIPS: dict[str, str] = {v.upper(): k for k, v in STATE_FIPS.items()}

STATE_NAME_TO_FIPS: dict[str, str] = {
    "alabama": "01", "alaska": "02", "arizona": "04", "arkansas": "05",
    "california": "06", "colorado": "08", "connecticut": "09",
    "delaware": "10", "district of columbia": "11", "florida": "12",
    "georgia": "13", "hawaii": "15", "idaho": "16", "illinois": "17",
    "indiana": "18", "iowa": "19", "kansas": "20", "kentucky": "21",
    "louisiana": "22", "maine": "23", "maryland": "24",
    "massachusetts": "25", "michigan": "26", "minnesota": "27",
    "mississippi": "28", "missouri": "29", "montana": "30",
    "nebraska": "31", "nevada": "32", "new hampshire": "33",
    "new jersey": "34", "new mexico": "35", "new york": "36",
    "north carolina": "37", "north dakota": "38", "ohio": "39",
    "oklahoma": "40", "oregon": "41", "pennsylvania": "42",
    "rhode island": "44", "south carolina": "45", "south dakota": "46",
    "tennessee": "47", "texas": "48", "utah": "49", "vermont": "50",
    "virginia": "51", "washington": "53", "west virginia": "54",
    "wisconsin": "55", "wyoming": "56",
}


def state_to_fips(identifier: str) -> str | None:
    if len(identifier) == 2 and identifier.isdigit():
        return identifier
    upper = identifier.upper()
    if len(upper) == 2:
        return STATE_ABBR_TO_FIPS.get(upper)
    return STATE_NAME_TO_FIPS.get(upper.lower())


def fips_to_state(fips: str) -> str | None:
    return STATE_FIPS.get(fips)


def get_env(name: str) -> str | None:
    return os.environ.get(name)


def require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise InvariantError(f"Required environment variable {name} is not set")
    return val


def print_stderr(*args: Any) -> None:
    print(*args, file=sys.stderr)
