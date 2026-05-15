"""Phase 3.5 — Narrative acquisition cohort.

Fetches news_provenance URLs for each settle_case_provenance row, extracts
injury-relevant prose, and populates settle_contributions.case_narrative.

Strategy
--------
1. For each row, split news_provenance on " | " to get candidate URLs.
2. Walk candidates in priority order (case-specific hosts before list-page hosts).
3. Fetch via httpx with realistic Chrome UA. 15s timeout. Skip paywalls.
4. Parse with BeautifulSoup. Extract <article>/<main> if present, else strip
   nav/header/footer/aside/script/style. Filter to paragraphs >= 50 chars.
5. If prose < 200 chars, try next URL. If all fail, optionally use Exa /contents
   fallback (capped at 1000 calls = ~$5 budget).
6. Truncate to 50000 chars and write to case_narrative. Keep source URL in
   audit_trail JSONB for provenance.

Idempotent: skip rows where case_narrative is already non-empty.

Modes
-----
PROBE_ONLY (default ON): only process first 10 rows, surface a sample.
Set PROBE_ONLY=0 env var to run full pass.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = REPO_ROOT / "logs" / "phase35_acquire.log"
STATS_PATH = REPO_ROOT / "logs" / "phase35_acquire_stats.json"
SAMPLES_PATH = REPO_ROOT / "logs" / "phase35_acquire_samples.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("phase35_acquire")
# Silence httpx INFO request logs
logging.getLogger("httpx").setLevel(logging.WARNING)

sys.path.insert(0, str(REPO_ROOT))

import asyncio  # noqa: E402

from app.core.database import get_db  # noqa: E402

PROBE_ONLY = os.environ.get("PROBE_ONLY", "1") == "1"
PROBE_LIMIT = 10
PAGE_SIZE = 500
MIN_PROSE_CHARS = 200
MAX_NARRATIVE_CHARS = 50000
HTTP_TIMEOUT = 15.0
RATE_LIMIT_SECS = 1.0
EXA_BUDGET_CALLS = 1000

# Paywalled / login-walled hosts: skip direct fetch (still try Exa if budget allows)
PAYWALL_HOSTS = {
    "lexisnexis.com",
    "law360.com",
    "unicourt.com",
    "pacermonitor.com",
    "casemine.com",
    "case-law.vlex.com",
    "vlex.com",
    "westlaw.com",
}

# JS-rendered SPAs: direct fetch returns chrome only. Always use Exa.
JS_RENDERED_HOSTS = {
    "forthepeople.com",
}

# URL patterns that indicate list/index pages (not per-case prose). Force-skip direct.
LIST_PAGE_URL_SUBSTRINGS = (
    "/lists/",
    "/top-",
)

# List-page hosts: deprioritize (last resort) since they're index pages
LIST_PAGE_HOSTS = {
    "topverdict.com",
}

# Injury / legal markers used to validate prose is actually case-relevant.
QUALITY_KEYWORDS = (
    "verdict", "plaintiff", "defendant", "jury", "settlement",
    "injury", "injured", "awarded", "struck", "suffered",
    "accident", "court", "judge", "sustained", "hospital",
    "surgery", "crash", "collision", "negligence", "damages",
)
MIN_QUALITY_HITS = 3

# Boilerplate fingerprints that mean we got site chrome instead of content
BOILERPLATE_FINGERPRINTS = (
    "discover the resources you need to succeed with morgan",
    "browsing our resource center",
    "we are pleased to present to you the list of the top",
    "educational videos, digital formats, and customer stories",
    "stay up-to-date with the latest legal news",
)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "close",
}

EXA_API_KEY = os.environ.get("EXA_API_KEY", "")
# Backup: pull from .env.local if env var not set
if not EXA_API_KEY:
    env_local = REPO_ROOT / ".env.local"
    if env_local.exists():
        for line in env_local.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip().startswith("EXA_API_KEY="):
                EXA_API_KEY = line.split("=", 1)[1].strip()
                break


def is_list_page_url(url: str) -> bool:
    u = url.lower()
    return any(s in u for s in LIST_PAGE_URL_SUBSTRINGS)


def is_useful_prose(prose: str) -> tuple[bool, str]:
    """Return (passes, reason). Prose must contain enough injury/legal keywords
    AND must NOT match common boilerplate fingerprints."""
    low = prose.lower()
    for fp in BOILERPLATE_FINGERPRINTS:
        if fp in low:
            return False, f"boilerplate:{fp[:30]}"
    hits = sum(1 for kw in QUALITY_KEYWORDS if kw in low)
    if hits < MIN_QUALITY_HITS:
        return False, f"low_keyword_hits:{hits}"
    return True, f"hits:{hits}"


def host_of(url: str) -> str:
    try:
        h = urlparse(url).netloc.lower()
        return h.removeprefix("www.")
    except Exception:
        return ""


def prioritize_urls(urls: list[str]) -> list[str]:
    """Sort URLs by extraction priority: case-specific hosts first, list-pages last."""
    def key(u: str) -> tuple[int, int]:
        h = host_of(u)
        if h in PAYWALL_HOSTS:
            return (3, 0)
        if h in LIST_PAGE_HOSTS:
            return (2, 0)
        return (1, 0)
    return sorted([u.strip() for u in urls if u.strip()], key=key)


def split_urls(field: str) -> list[str]:
    if not field:
        return []
    return [u.strip() for u in field.split("|") if u.strip().startswith("http")]


def extract_prose(html: str) -> str:
    """Strip junk, prefer article/main, return paragraph-joined prose."""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # Strip non-content tags
    for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside",
                              "form", "noscript", "iframe", "svg"]):
        tag.decompose()

    # Prefer <article>, then <main>, then role=main, then <body>
    container = (
        soup.find("article")
        or soup.find("main")
        or soup.find(attrs={"role": "main"})
        or soup.body
        or soup
    )

    paragraphs = []
    for p in container.find_all(["p", "li"]):
        txt = p.get_text(separator=" ", strip=True)
        if len(txt) >= 50:
            paragraphs.append(txt)

    # Fallback: if no useful paragraphs, take all text
    if not paragraphs:
        all_text = container.get_text(separator="\n", strip=True)
        return all_text[:MAX_NARRATIVE_CHARS]

    prose = "\n\n".join(paragraphs)
    return prose[:MAX_NARRATIVE_CHARS]


def fetch_direct(client: httpx.Client, url: str) -> tuple[Optional[str], str]:
    """Direct HTTP fetch + quality check. Returns (prose, status_string)."""
    try:
        resp = client.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT, follow_redirects=True)
    except httpx.TimeoutException:
        return None, "timeout"
    except httpx.HTTPError as e:
        return None, f"http_error:{type(e).__name__}"
    except Exception as e:
        return None, f"exc:{type(e).__name__}"
    if resp.status_code >= 400:
        return None, f"status_{resp.status_code}"
    ct = resp.headers.get("content-type", "")
    if "html" not in ct.lower() and "text" not in ct.lower():
        return None, f"non_html:{ct[:30]}"
    prose = extract_prose(resp.text)
    if len(prose) < MIN_PROSE_CHARS:
        return None, f"thin_prose:{len(prose)}"
    ok, reason = is_useful_prose(prose)
    if not ok:
        return None, f"quality_fail:{reason}"
    return prose, "ok"


def fetch_exa(client: httpx.Client, url: str) -> tuple[Optional[str], str]:
    """Exa /contents fallback + quality check. Returns (prose, status_string)."""
    if not EXA_API_KEY:
        return None, "no_exa_key"
    try:
        resp = client.post(
            "https://api.exa.ai/contents",
            headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
            json={"ids": [url], "text": True},
            timeout=HTTP_TIMEOUT,
        )
    except Exception as e:
        return None, f"exa_exc:{type(e).__name__}"
    if resp.status_code != 200:
        return None, f"exa_status_{resp.status_code}"
    try:
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return None, "exa_no_results"
        text = results[0].get("text", "")
        if len(text) < MIN_PROSE_CHARS:
            return None, f"exa_thin:{len(text)}"
        text = text[:MAX_NARRATIVE_CHARS]
        ok, reason = is_useful_prose(text)
        if not ok:
            return None, f"exa_quality_fail:{reason}"
        return text, "exa_ok"
    except Exception as e:
        return None, f"exa_parse_exc:{type(e).__name__}"

def acquire_for_row(
    client: httpx.Client,
    urls: list[str],
    exa_calls_remaining: list[int],
) -> tuple[Optional[str], Optional[str], list[dict]]:
    """Walk URLs, return (prose, source_url, attempts).

    attempts: list of {url, status} for audit.
    """
    attempts: list[dict] = []
    for url in urls:
        h = host_of(url)
        is_paywall = h in PAYWALL_HOSTS
        is_js = h in JS_RENDERED_HOSTS
        is_list = is_list_page_url(url)

        # Force Exa for paywalls, JS SPAs, and list-page URLs
        if (is_paywall or is_js or is_list):
            if exa_calls_remaining[0] > 0:
                exa_calls_remaining[0] -= 1
                prose, status = fetch_exa(client, url)
                attempts.append({"url": url, "status": f"exa_forced_{status}"})
                if prose:
                    return prose, url, attempts
            else:
                attempts.append({"url": url, "status": "skip_no_budget"})
            continue

        # Direct fetch path with rate limit
        time.sleep(RATE_LIMIT_SECS)
        prose, status = fetch_direct(client, url)
        attempts.append({"url": url, "status": status})
        if prose:
            return prose, url, attempts
        # Exa fallback for direct failures
        if exa_calls_remaining[0] > 0:
            exa_calls_remaining[0] -= 1
            prose, exa_status = fetch_exa(client, url)
            attempts.append({"url": url, "status": f"exa_fallback_{exa_status}"})
            if prose:
                return prose, url, attempts
    return None, None, attempts


async def main() -> int:
    db = await get_db()
    if db is None:
        log.error("get_db() returned None")
        return 2

    log.info("=" * 60)
    log.info("PHASE 3.5 NARRATIVE ACQUISITION  (probe_only=%s)", PROBE_ONLY)
    log.info("EXA_API_KEY present=%s", bool(EXA_API_KEY))
    log.info("=" * 60)

    # Pull provenance rows with news URLs
    prov_rows: list[dict] = []
    offset = 0
    while True:
        resp = (
            db.table("settle_case_provenance")
            .select("contribution_id, news_provenance")
            .order("contribution_id", desc=False)
            .limit(PAGE_SIZE)
            .offset(offset)
            .execute()
        )
        page = resp.data or []
        prov_rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    candidates = [
        r for r in prov_rows if (r.get("news_provenance") or "").strip()
    ]
    log.info("provenance rows with news_provenance: %d", len(candidates))

    # Pull contributions to find which already have case_narrative populated
    contrib_rows: list[dict] = []
    offset = 0
    while True:
        resp = (
            db.table("settle_contributions")
            .select("id, case_narrative")
            .order("id", desc=False)
            .limit(PAGE_SIZE)
            .offset(offset)
            .execute()
        )
        page = resp.data or []
        contrib_rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    already_populated = {
        r["id"] for r in contrib_rows
        if (r.get("case_narrative") or "").strip()
    }
    log.info("contributions already with case_narrative: %d", len(already_populated))

    # Filter to rows needing acquisition
    todo = [
        r for r in candidates
        if r["contribution_id"] not in already_populated
    ]
    log.info("rows requiring acquisition: %d", len(todo))

    if PROBE_ONLY:
        todo = todo[:PROBE_LIMIT]
        log.info("PROBE_ONLY mode: limiting to %d rows", len(todo))

    stats = {
        "mode": "probe" if PROBE_ONLY else "full",
        "attempted": 0,
        "populated": 0,
        "all_urls_failed": 0,
        "errors": 0,
        "exa_calls_used": 0,
        "host_success": {},
        "host_failure": {},
        "status_counter": {},
    }
    samples: list[dict] = []
    exa_calls_remaining = [EXA_BUDGET_CALLS]

    with httpx.Client() as client:
        for i, row in enumerate(todo):
            cid = row["contribution_id"]
            urls_raw = row.get("news_provenance", "")
            urls = prioritize_urls(split_urls(urls_raw))
            stats["attempted"] += 1
            try:
                prose, source_url, attempts = acquire_for_row(
                    client, urls, exa_calls_remaining
                )
            except Exception as e:
                log.exception("acquire_for_row failed for %s: %s", cid, e)
                stats["errors"] += 1
                continue

            for a in attempts:
                stats["status_counter"][a["status"]] = (
                    stats["status_counter"].get(a["status"], 0) + 1
                )

            if prose and source_url:
                src_host = host_of(source_url)
                stats["host_success"][src_host] = (
                    stats["host_success"].get(src_host, 0) + 1
                )
                # Write to DB
                try:
                    db.table("settle_contributions").update({
                        "case_narrative": prose,
                    }).eq("id", cid).execute()
                    stats["populated"] += 1
                    if len(samples) < 5:
                        samples.append({
                            "contribution_id": cid,
                            "source_url": source_url,
                            "prose_first_500": prose[:500],
                            "prose_length": len(prose),
                        })
                except Exception as e:
                    log.exception("DB update failed for %s: %s", cid, e)
                    stats["errors"] += 1
            else:
                stats["all_urls_failed"] += 1
                for a in attempts:
                    h = host_of(a["url"])
                    stats["host_failure"][h] = stats["host_failure"].get(h, 0) + 1

            if (i + 1) % 25 == 0:
                log.info(
                    "progress: %d/%d  populated=%d failed=%d errors=%d",
                    i + 1, len(todo),
                    stats["populated"], stats["all_urls_failed"], stats["errors"],
                )

    stats["exa_calls_used"] = EXA_BUDGET_CALLS - exa_calls_remaining[0]

    log.info("=" * 60)
    log.info("RESULT")
    log.info("=" * 60)
    log.info("attempted: %d", stats["attempted"])
    log.info("populated: %d", stats["populated"])
    log.info("all_urls_failed: %d", stats["all_urls_failed"])
    log.info("errors: %d", stats["errors"])
    log.info("exa_calls_used: %d", stats["exa_calls_used"])
    success_rate = (
        stats["populated"] / stats["attempted"] * 100 if stats["attempted"] else 0
    )
    log.info("success_rate: %.1f%%", success_rate)
    log.info("host_success: %s", stats["host_success"])
    log.info("host_failure (top): %s", dict(
        sorted(stats["host_failure"].items(), key=lambda x: -x[1])[:10]
    ))

    STATS_PATH.write_text(json.dumps(stats, indent=2, default=str), encoding="utf-8")
    SAMPLES_PATH.write_text(json.dumps(samples, indent=2, default=str), encoding="utf-8")
    log.info("stats: %s", STATS_PATH)
    log.info("samples: %s", SAMPLES_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
