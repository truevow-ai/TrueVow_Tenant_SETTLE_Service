"""
carrier_common.py — Shared utilities for the insurance-carrier scraping skill.

Provides CarrierFact type, CARRIER_BOUNDS validation, NAIC/CIK/accession
assertions, cached HTTP helpers, and govdata bridging.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any
from pathlib import Path

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_GOVDATA_DIR = os.path.normpath(os.path.join(_THIS_DIR, "..", "govdata"))
if _GOVDATA_DIR not in sys.path:
    sys.path.insert(0, _GOVDATA_DIR)

try:
    import govdata_common  # noqa: F401
except ImportError:
    govdata_common = None  # type: ignore[assignment]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


@dataclass
class CarrierFact:
    kind: str
    entity_id: str
    entity_name: str
    value_text: str
    observed_at: str
    source_url: str
    source_dataset: str
    source_sha256: str
    fetch_timestamp: str
    cache_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CARRIER_BOUNDS: dict[str, tuple[float, float]] = {
    "complaint_count": (0.0, 1_000_000.0),
    "complaint_ratio": (0.0, 1_000.0),
    "loss_reserve": (0.0, 1_000_000_000_000.0),
    "opinion_count": (0.0, 1_000_000.0),
    "confidence": (0.0, 1.0),
}

_NAIC_RE = re.compile(r"^\d{4,6}$")
_CIK_RE = re.compile(r"^\d{1,10}$")
_ACCESSION_RE = re.compile(r"^\d{10}-\d{2}-\d{6}$")


def assert_valid_naic(naic: str) -> str:
    if not _NAIC_RE.match(str(naic)):
        raise InvariantError(f"invalid NAIC code: {naic!r}")
    return str(naic)


def assert_valid_cik(cik: str) -> str:
    if not _CIK_RE.match(str(cik)):
        raise InvariantError(f"invalid CIK: {cik!r}")
    return str(cik)


def assert_valid_accession(accession: str) -> str:
    if not _ACCESSION_RE.match(str(accession)):
        raise InvariantError(f"invalid accession: {accession!r}")
    return str(accession)


def assert_in_range(label: str, value: float, lo: float, hi: float) -> None:
    if not (lo <= value <= hi):
        raise InvariantError(f"{label} {value} out of bounds [{lo}, {hi}]")


def assert_finite(label: str, value: float) -> None:
    import math
    if not math.isfinite(value):
        raise InvariantError(f"{label} is not finite: {value}")


class InvariantError(ValueError):
    pass


_CACHE_DIR = Path(_THIS_DIR) / ".cache"


def cached_get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    cache_days: int = 1,
    params: dict[str, str] | None = None,
    timeout: int = 30,
) -> list[dict[str, Any]] | dict[str, Any]:
    import requests
    import time

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()[:16]
    cache_path = _CACHE_DIR / f"{cache_key}.json"

    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < cache_days * 86400:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data

    resp = requests.get(url, headers=headers or {}, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    return data


def cached_get_text(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    cache_days: int = 1,
    timeout: int = 30,
) -> str:
    import requests
    import time

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(url.encode()).hexdigest()[:16]
    cache_path = _CACHE_DIR / f"{cache_key}.txt"

    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < cache_days * 86400:
            return cache_path.read_text(encoding="utf-8")

    resp = requests.get(url, headers=headers or {}, timeout=timeout)
    resp.raise_for_status()
    text = resp.text

    cache_path.write_text(text, encoding="utf-8")
    return text


def cached_http_get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    cache_days: int = 1,
    timeout: int = 30,
) -> bytes:
    import requests
    import time

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(url.encode()).hexdigest()[:16]
    cache_path = _CACHE_DIR / f"{cache_key}.bin"

    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < cache_days * 86400:
            return cache_path.read_bytes()

    resp = requests.get(url, headers=headers or {}, timeout=timeout)
    resp.raise_for_status()
    content = resp.content

    cache_path.write_bytes(content)
    return content


def requires_freshness(max_age_days: int = 7) -> bool:
    return True
