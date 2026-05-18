"""Phase 3a Part 2 — Probe — fetch one TopVerdict list page and one ForThePeople
URL, dump structure to inform full scraper design.

Read-only against DB. Live HTTP fetch. Caps to 3 fetches total.
"""
from __future__ import annotations

import asyncio
import sys
import time
from collections import Counter
from pathlib import Path

import httpx

SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))


class _Tee:
    def __init__(self, *s): self._s = s
    def write(self, d):
        for x in self._s:
            try: x.write(d); x.flush()
            except Exception: pass
    def flush(self):
        for x in self._s:
            try: x.flush()
            except Exception: pass


LOG = SERVICE_ROOT / "logs" / "detailscrape_probe.log"
LOG.parent.mkdir(parents=True, exist_ok=True)
_fh = LOG.open("w", encoding="utf-8")
sys.stdout = _Tee(sys.__stdout__, _fh)
sys.stderr = _Tee(sys.__stderr__, _fh)

from bs4 import BeautifulSoup  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import get_db, reset_client  # noqa: E402


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",  # NO brotli (per architect note)
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
}


async def _boot():
    settings.USE_MOCK_DATA = False
    settings.SETTLE_USE_MOCK_DATA = False
    reset_client()
    return await get_db()


def _fetch(url: str) -> tuple[int, str]:
    print(f"\n[FETCH] {url}")
    try:
        with httpx.Client(timeout=30.0, headers=HEADERS, follow_redirects=True) as c:
            r = c.get(url)
            print(f"  status={r.status_code}, body_len={len(r.text)}")
            return r.status_code, r.text
    except Exception as e:
        print(f"  [ERR] {e}")
        return 0, ""


def main() -> int:
    db = asyncio.run(_boot())

    # Pull a handful of sample rows + provenance
    print("[STEP 1] Sampling 10 Unknown-County rows for source_url variety...")
    rows = []
    offset = 0
    while offset < 1000:
        q = (
            db.table("settle_contributions").select("id,jurisdiction,case_type,outcome_amount_range")
            .eq("jurisdiction", "FL (Unknown County)").eq("status", "approved")
            .limit(1000).offset(offset)
        )
        r = q.execute()
        page = r.data or []
        rows.extend(page)
        if len(page) < 1000: break
        offset += 1000
    print(f"  {len(rows)} approved Unknown-County rows")

    ids = [r["id"] for r in rows]
    prov = []
    CHUNK = 50
    for i in range(0, len(ids), CHUNK):
        chunk = ids[i:i + CHUNK]
        q = db.table("settle_case_provenance").select(
            "contribution_id,source_url,news_provenance,case_citation"
        ).in_("contribution_id", chunk).limit(1000)
        r = q.execute()
        prov.extend(r.data or [])
    print(f"  {len(prov)} provenance rows")

    # Distribution of source_url -- how many unique?
    src_counts = Counter(p.get("source_url") for p in prov if p.get("source_url"))
    print(f"\n[STEP 2] Unique source_url count: {len(src_counts)}")
    print("  Top 15 source_urls by row count:")
    for url, n in src_counts.most_common(15):
        print(f"    {n:>3}  {url}")

    # Sample case_citations
    print("\n[STEP 3] Sample case_citations (15 unique):")
    cits = list({p.get("case_citation") for p in prov if p.get("case_citation")})[:15]
    for c in cits:
        print(f"    {c}")

    # Sample news_provenance distribution
    news_counts = Counter()
    for p in prov:
        nu = p.get("news_provenance")
        if nu:
            # Take just the host
            from urllib.parse import urlparse
            try:
                host = urlparse(nu.split("|")[0].strip()).netloc
                news_counts[host] += 1
            except Exception:
                pass
    print("\n[STEP 4] news_provenance host distribution (top 15):")
    for host, n in news_counts.most_common(15):
        print(f"    {n:>3}  {host}")

    # Pick the most common source_url and fetch it
    if src_counts:
        top_url = src_counts.most_common(1)[0][0]
        print(f"\n[STEP 5] Probing top source_url: {top_url}")
        status, body = _fetch(top_url)
        if status == 200 and body:
            soup = BeautifulSoup(body, "html.parser")
            # Look for verdict cards / links
            print("\n  Page title:", (soup.title.string or "").strip()[:120] if soup.title else "(none)")
            # Find anchors with class/href hints
            anchors = soup.find_all("a", href=True)
            print(f"  Total anchors: {len(anchors)}")
            verdict_anchors = [a for a in anchors if "/verdict" in a.get("href", "").lower()
                               or "/case" in a.get("href", "").lower()]
            print(f"  Anchors w/ /verdict or /case: {len(verdict_anchors)}")
            print("  Sample (first 8):")
            for a in verdict_anchors[:8]:
                txt = (a.get_text(strip=True) or "")[:80]
                print(f"    href={a['href'][:100]}  text={txt!r}")
            # Look for h2/h3 headings (often verdict titles)
            h2s = soup.find_all(["h2", "h3", "h4"])[:15]
            print(f"\n  Headings (first 15):")
            for h in h2s:
                t = h.get_text(strip=True)[:120]
                print(f"    <{h.name}> {t!r}")
            # Look for class names that might indicate verdict cards
            classes = Counter()
            for tag in soup.find_all(class_=True):
                for cls in tag.get("class", []):
                    if "verdict" in cls.lower() or "case" in cls.lower() or "list" in cls.lower():
                        classes[cls] += 1
            print(f"\n  Verdict/case/list-related classes (top 15):")
            for cls, n in classes.most_common(15):
                print(f"    {n:>4}  {cls}")
            # Dump first 3000 chars of body for inspection
            dump_path = SERVICE_ROOT / "logs" / "detailscrape_probe_body.html"
            dump_path.write_text(body[:50000], encoding="utf-8")
            print(f"\n  First 50KB dumped to: {dump_path}")
        else:
            print("  [WARN] Fetch failed or empty body")
        time.sleep(2)

    # Probe the unique news_provenance host pattern (forthepeople.com had a clear case_name)
    fp_sample = next((p.get("news_provenance") for p in prov
                       if p.get("news_provenance") and "forthepeople.com" in p.get("news_provenance")),
                     None)
    if fp_sample:
        # Take first URL if pipe-delimited
        url = fp_sample.split("|")[0].strip()
        print(f"\n[STEP 6] Probing forthepeople.com sample: {url}")
        status, body = _fetch(url)
        if status == 200 and body:
            soup = BeautifulSoup(body, "html.parser")
            print("  Page title:", (soup.title.string or "").strip()[:120] if soup.title else "(none)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
