"""
_common/fetcher.py — Shared Level-0 (plain-HTTP) fetcher for the SETTLE data factory.

Level 0 of the escalation ladder documented in
docs/01-main/SCRAPING_TOOLING_AND_HUMAN_EMULATION.md:

    L0 plain HTTP (this module) -> L1 curl_cffi -> L2 stealth browser -> L3 challenge solver

Use L0 for APIs and static/bulk endpoints that do not fight back (CourtListener
bulk, Caselaw Access Project static.case.law, FJC IDB, MoreLaw, etc.).

Design goals:
  * Polite by default: identifies itself, rate-limits, backs off.
  * Robust: retries transient errors (429 / 5xx / timeouts / transport errors).
  * Reproducible & cheap: on-disk cache so re-runs don't re-hit the network.
  * Provenance built in: every result carries url + sha256 + fetch timestamp,
    which the zero-fabrication data-integrity guardrail (LOW_BLOCKER_DATA_SOURCES
    section 6a) requires for every downstream row.

This module is intentionally dependency-light: stdlib + httpx only.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "TrueVow-SETTLE-DataFactory/1.0 "
    "(+https://truevow.law; legal-research; contact: data@truevow.law)"
)

# HTTP statuses worth retrying (transient).
_RETRY_STATUSES = {408, 425, 429, 500, 502, 503, 504}

_DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / "_cache"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _full_url(url: str, params: Optional[dict]) -> str:
    if not params:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{urlencode(params, doseq=True)}"


@dataclass
class FetchResult:
    """A single fetch + its provenance."""

    url: str
    status_code: int
    content: bytes
    sha256: str
    fetched_at: str
    from_cache: bool
    content_type: Optional[str] = None

    def text(self, encoding: str = "utf-8") -> str:
        return self.content.decode(encoding, errors="replace")

    def json(self) -> Any:
        return json.loads(self.content)

    def provenance(self) -> dict:
        """Provenance dict to attach to every downstream record."""
        return {
            "source_url": self.url,
            "sha256": self.sha256,
            "fetched_at": self.fetched_at,
            "status_code": self.status_code,
            "content_type": self.content_type,
        }


class Fetcher:
    """Polite, retrying, caching L0 HTTP client.

    Example:
        with Fetcher(min_delay=1.0) as f:
            res = f.get_json("https://static.case.law/JurisdictionsMetadata.json")
            print(res.provenance())
    """

    def __init__(
        self,
        min_delay: float = 1.0,
        max_retries: int = 4,
        timeout: float = 30.0,
        user_agent: str = DEFAULT_USER_AGENT,
        cache_dir: Optional[Path | str] = None,
        use_cache: bool = True,
        jitter: float = 0.4,
    ) -> None:
        self.min_delay = max(0.0, min_delay)
        self.max_retries = max(0, max_retries)
        self.jitter = max(0.0, jitter)
        self.use_cache = use_cache
        self.cache_dir = Path(cache_dir) if cache_dir else _DEFAULT_CACHE_DIR
        if self.use_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_ts = 0.0
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": user_agent,
                "Accept-Encoding": "gzip, deflate",
            },
        )

    # -- caching ---------------------------------------------------------------

    def _cache_paths(self, full_url: str) -> tuple[Path, Path]:
        key = hashlib.sha256(full_url.encode("utf-8")).hexdigest()
        shard = self.cache_dir / key[:2]
        return shard / f"{key}.bin", shard / f"{key}.meta.json"

    def _read_cache(self, full_url: str) -> Optional[FetchResult]:
        if not self.use_cache:
            return None
        bin_path, meta_path = self._cache_paths(full_url)
        if not (bin_path.exists() and meta_path.exists()):
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            content = bin_path.read_bytes()
            return FetchResult(
                url=full_url,
                status_code=meta["status_code"],
                content=content,
                sha256=meta["sha256"],
                fetched_at=meta["fetched_at"],
                from_cache=True,
                content_type=meta.get("content_type"),
            )
        except Exception as e:  # corrupt cache entry — ignore and refetch
            logger.warning("Cache read failed for %s: %s", full_url, e)
            return None

    def _write_cache(self, res: FetchResult) -> None:
        if not self.use_cache:
            return
        bin_path, meta_path = self._cache_paths(res.url)
        bin_path.parent.mkdir(parents=True, exist_ok=True)
        bin_path.write_bytes(res.content)
        meta_path.write_text(
            json.dumps(
                {
                    "url": res.url,
                    "status_code": res.status_code,
                    "sha256": res.sha256,
                    "fetched_at": res.fetched_at,
                    "content_type": res.content_type,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    # -- rate limiting ---------------------------------------------------------

    def _respect_rate_limit(self) -> None:
        if self.min_delay <= 0:
            return
        elapsed = time.monotonic() - self._last_request_ts
        wait = self.min_delay - elapsed
        if self.jitter:
            wait += random.uniform(0, self.jitter)
        if wait > 0:
            time.sleep(wait)

    # -- core fetch ------------------------------------------------------------

    def get(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> FetchResult:
        full_url = _full_url(url, params)

        cached = self._read_cache(full_url)
        if cached is not None:
            logger.info("CACHE HIT %s", full_url)
            return cached

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            self._respect_rate_limit()
            self._last_request_ts = time.monotonic()
            try:
                resp = self._client.get(full_url, headers=headers)
                if resp.status_code in _RETRY_STATUSES:
                    raise httpx.HTTPStatusError(
                        f"retryable status {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                resp.raise_for_status()
                content = resp.content
                res = FetchResult(
                    url=full_url,
                    status_code=resp.status_code,
                    content=content,
                    sha256=hashlib.sha256(content).hexdigest(),
                    fetched_at=_utc_now_iso(),
                    from_cache=False,
                    content_type=resp.headers.get("content-type"),
                )
                self._write_cache(res)
                logger.info("OK %s (%s bytes)", full_url, len(content))
                return res
            except (httpx.HTTPStatusError, httpx.TransportError, httpx.TimeoutException) as e:
                last_exc = e
                if attempt >= self.max_retries:
                    break
                backoff = (2 ** attempt) + random.uniform(0, self.jitter)
                logger.warning(
                    "Fetch failed (attempt %d/%d) for %s: %s — retrying in %.1fs",
                    attempt + 1, self.max_retries + 1, full_url, e, backoff,
                )
                time.sleep(backoff)

        raise RuntimeError(f"Fetch failed after {self.max_retries + 1} attempts: {full_url}") from last_exc

    # -- convenience -----------------------------------------------------------

    def get_json(self, url: str, params: Optional[dict] = None, headers: Optional[dict] = None) -> FetchResult:
        return self.get(url, params=params, headers=headers)

    def get_text(self, url: str, params: Optional[dict] = None, headers: Optional[dict] = None) -> FetchResult:
        return self.get(url, params=params, headers=headers)

    def download(self, url: str, dest: Path | str, params: Optional[dict] = None) -> FetchResult:
        res = self.get(url, params=params)
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(res.content)
        return res

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "Fetcher":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
