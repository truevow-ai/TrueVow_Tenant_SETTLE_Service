"""Phase 3.5 — Survey news_provenance URLs prior to acquisition pass.

Read-only. Counts URLs, distributes by host, samples 5 for inspection.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = REPO_ROOT / "logs" / "phase35_survey.log"
STATS_PATH = REPO_ROOT / "logs" / "phase35_survey_stats.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("phase35_survey")

sys.path.insert(0, str(REPO_ROOT))

import asyncio  # noqa: E402

from app.core.database import get_db  # noqa: E402

PAGE_SIZE = 1000


async def main() -> int:
    db = await get_db()
    if db is None:
        log.error("get_db() returned None - cannot run survey.")
        return 2

    # Pull every settle_case_provenance row's contribution_id + news_provenance.
    all_rows: list[dict] = []
    offset = 0
    while True:
        resp = (
            db.table("settle_case_provenance")
            .select("contribution_id, news_provenance, source_url")
            .order("contribution_id", desc=False)
            .limit(PAGE_SIZE)
            .offset(offset)
            .execute()
        )
        page = resp.data or []
        all_rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    total_prov = len(all_rows)
    with_news = [r for r in all_rows if (r.get("news_provenance") or "").strip()]
    with_source = [r for r in all_rows if (r.get("source_url") or "").strip()]
    pct_news = (len(with_news) / total_prov * 100) if total_prov else 0.0

    # Host distribution
    host_counter: Counter[str] = Counter()
    for r in with_news:
        url = r["news_provenance"]
        try:
            host = urlparse(url).netloc.lower()
            host = host.removeprefix("www.")
        except Exception:
            host = "<unparseable>"
        host_counter[host] += 1

    # Total contributions for reference
    total_contrib_resp = (
        db.table("settle_contributions").select("id").limit(1).execute()
    )
    # PostgREST count not always returned by wrapper; do a full-page sweep instead
    total_contributions_rows: list[dict] = []
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
        total_contributions_rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    total_contributions = len(total_contributions_rows)
    populated_narratives = sum(
        1 for r in total_contributions_rows
        if (r.get("case_narrative") or "").strip()
    )

    stats = {
        "total_provenance_rows": total_prov,
        "rows_with_news_provenance": len(with_news),
        "rows_with_source_url": len(with_source),
        "pct_with_news_provenance": round(pct_news, 2),
        "total_contributions": total_contributions,
        "currently_populated_case_narrative": populated_narratives,
        "top_15_hosts": host_counter.most_common(15),
        "sample_urls": [
            {
                "contribution_id": r["contribution_id"],
                "news_provenance": r["news_provenance"],
            }
            for r in with_news[:5]
        ],
    }

    STATS_PATH.write_text(json.dumps(stats, indent=2, default=str), encoding="utf-8")
    log.info("=" * 60)
    log.info("PHASE 3.5 SURVEY")
    log.info("=" * 60)
    log.info("total_provenance_rows: %d", total_prov)
    log.info("rows_with_news_provenance: %d (%.1f%%)", len(with_news), pct_news)
    log.info("rows_with_source_url: %d", len(with_source))
    log.info("total_contributions: %s", total_contributions)
    log.info("currently_populated_case_narrative: %d", populated_narratives)
    log.info("top_15_hosts:")
    for host, n in host_counter.most_common(15):
        log.info("  %4d  %s", n, host)
    log.info("sample_urls (first 5):")
    for r in with_news[:5]:
        log.info("  %s -> %s", r["contribution_id"], r["news_provenance"])
    log.info("stats written to %s", STATS_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
