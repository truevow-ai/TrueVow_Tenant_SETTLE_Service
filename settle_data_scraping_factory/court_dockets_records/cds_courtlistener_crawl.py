"""
cds_courtlistener_crawl.py — Long-running, rate-limit-respecting CourtListener FL crawler.

CourtListener's free authenticated tier allows only 5 req/min, 50 req/hr, and 125 req/day
(rolling windows; most-restrictive wins). This crawler paces EVERY request through the
shared Fetcher (default min_delay=700s ~= the 125/day ceiling) so it can run unattended for
~24h without ever tripping the throttle.

It cursor-paginates the Florida state courts (fla, fladistctapp), runs each opinion through
the shared zero-fabrication pipeline (cds_cap_pipeline.build_candidate), and APPENDS results
to out/cl_fl_crawl/courtlistener_florida_<status>.jsonl as it goes (durable on crash). It
checkpoints the seen opinion ids (resume-safe + dedup), pre-seeds `seen` from our existing FL
buckets so it doesn't waste precious quota re-fetching, and RIDES OUT throttling by sleeping
and retrying when the API returns 429 (instead of crashing).

Run unattended for 24h (this is what the launcher uses):
    python cds_courtlistener_crawl.py --hours 24 --min-delay 700

Quick smoke test (uses a little quota):
    python cds_courtlistener_crawl.py --hours 0.05 --min-delay 2 --max-opinions 2 --throttle-sleep 10
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_FACTORY_ROOT = _HERE.parent
for _p in (_FACTORY_ROOT, _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from _common.fetcher import Fetcher  # noqa: E402
import cds_courtlistener as cl  # noqa: E402
from cds_cap_pipeline import build_candidate  # noqa: E402

OUT_DIR = _HERE / "out" / "cl_fl_crawl"
CKPT = OUT_DIR / "checkpoint.json"
LOG_PATH = OUT_DIR / "crawl.log"


def _load_ckpt() -> dict:
    if CKPT.exists():
        try:
            return json.loads(CKPT.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"seen_ids": [], "counts": {"accepted": 0, "needs_review": 0, "rejected": 0},
            "started_at": None, "last_at": None}


def _save_ckpt(ck: dict) -> None:
    tmp = CKPT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ck, default=str), encoding="utf-8")
    tmp.replace(CKPT)


def _append(status: str, row: dict) -> None:
    with (OUT_DIR / f"courtlistener_florida_{status}.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def _preseed_seen() -> set:
    """Seed dedup from every existing FL CourtListener bucket so we don't re-spend quota."""
    seen: set = set()
    out_root = _HERE / "out"
    if not out_root.exists():
        return seen
    for f in out_root.rglob("courtlistener_florida**.jsonl"):
        try:
            for line in f.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line:
                    continue
                cite = (json.loads(line).get("official_citation") or "")
                m = re.match(r"courtlistener:(\d+)", cite)
                if m:
                    seen.add(m.group(1))
        except Exception:
            continue
    return seen


def _get_riding(f, url, params, headers, log, sleep_s, deadline):
    """GET a FetchResult, sleeping/retrying through throttles until success or the deadline.

    Returns None only when the deadline is reached while still throttled (so the caller can
    stop WITHOUT marking the in-flight opinion as seen). DRF does not count 429'd requests
    against the quota, so probing during a throttle window is safe and clears naturally.
    """
    while time.time() < deadline:
        try:
            return f.get(url, params=params, headers=headers)
        except Exception as e:
            log.warning("throttled/error: %s -- sleeping %.0fs for the rolling window", str(e)[:90], sleep_s)
            time.sleep(sleep_s)
    return None


def _fetch_record_riding(f, item, queried_court, headers, log, sleep_s, deadline):
    """Fetch one opinion's detail (riding out throttles) and build a CAP-schema record.

    Returns (status, rec):
      ("ok", rec)        fetched + usable -> classify
      ("skip", None)     fetched but unusable (non-FL / no text / no url) -> mark seen, skip
      ("deadline", None) could NOT fetch before the deadline (throttled) -> do NOT mark seen
    """
    court_id = item.get("court_id") or queried_court
    jurisdiction = cl.STATE_FROM_COURT.get(court_id)
    op_id = cl._opinion_id(item)
    if jurisdiction is None or not op_id:
        return "skip", None
    res = _get_riding(f, f"{cl.CL_API}/opinions/{op_id}/", None, headers, log, sleep_s, deadline)
    if res is None:
        return "deadline", None
    try:
        detail = res.json()
    except Exception:
        return "skip", None
    text = cl._opinion_text_from_detail(detail)
    if len(text) < 50:
        return "skip", None
    source_url = cl._abs_url(detail.get("absolute_url")) or cl._abs_url(item.get("absolute_url"))
    if not source_url:
        return "skip", None
    rec = {
        "source": "courtlistener",
        "jurisdiction": jurisdiction,
        "name_abbreviation": item.get("caseName") or item.get("case_name") or detail.get("caseName"),
        "year": cl._year_from(item.get("dateFiled") or item.get("date_filed") or detail.get("date_created")),
        "official_citation": cl._first_citation(item) or f"courtlistener:{op_id}",
        "court_id": court_id,
        "full_text_url": f"{cl.CL_API}/opinions/{op_id}/",
        "source_url": source_url,
        "text_sha256": res.sha256,
        "fetched_at": res.fetched_at,
        "opinion_text": text,
    }
    return "ok", rec


def main() -> int:
    ap = argparse.ArgumentParser(description="Paced, unattended CourtListener FL crawler")
    ap.add_argument("--hours", type=float, default=24.0, help="How long to run")
    ap.add_argument("--min-delay", type=float, default=700.0,
                    help="Seconds between requests (~700 keeps under 125/day)")
    ap.add_argument("--query", default=cl.DEFAULT_QUERY)
    ap.add_argument("--max-opinions", type=int, default=0, help="0 = unlimited (until --hours)")
    ap.add_argument("--throttle-sleep", type=float, default=900.0,
                    help="Seconds to sleep when the API throttles")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()],
    )
    log = logging.getLogger("cl_fl_crawl")

    ck = _load_ckpt()
    seen = set(ck.get("seen_ids", [])) | _preseed_seen()
    counts = ck.get("counts", {"accepted": 0, "needs_review": 0, "rejected": 0})
    ck["started_at"] = ck.get("started_at") or time.strftime("%Y-%m-%dT%H:%M:%S")

    key = cl._load_api_key()
    headers = cl._auth_headers(key)
    courts = cl.STATE_TO_COURTS.get("Florida", [])
    deadline = time.time() + args.hours * 3600
    processed = 0

    log.info("FL crawl start | courts=%s query=%r min_delay=%ss hours=%s preseeded_seen=%d",
             courts, args.query, args.min_delay, args.hours, len(seen))

    with Fetcher(min_delay=args.min_delay, max_retries=1) as f:
        for court in courts:
            if time.time() >= deadline or (args.max_opinions and processed >= args.max_opinions):
                break
            url = f"{cl.CL_API}/search/"
            params = {"q": args.query, "type": "o", "court": court, "order_by": "dateFiled desc"}
            page = 0
            while url and time.time() < deadline:
                if args.max_opinions and processed >= args.max_opinions:
                    break
                res = _get_riding(f, url, params, headers, log, args.throttle_sleep, deadline)
                if res is None:
                    break
                data = res.json()
                page += 1
                results = data.get("results", [])
                log.info("court=%s page=%d results=%d", court, page, len(results))
                for item in results:
                    if time.time() >= deadline or (args.max_opinions and processed >= args.max_opinions):
                        break
                    op_id = cl._opinion_id(item)
                    if not op_id or str(op_id) in seen:
                        continue
                    status, rec = _fetch_record_riding(f, item, court, headers, log, args.throttle_sleep, deadline)
                    if status == "deadline":
                        break  # throttled past the deadline; DON'T mark seen -> retried next run
                    seen.add(str(op_id))  # we fetched it (usable or not) -> never re-spend quota on it
                    if status != "ok" or rec is None:
                        ck.update(seen_ids=sorted(seen), last_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
                        _save_ckpt(ck)
                        continue
                    cand = build_candidate(rec)
                    st = cand["status"]
                    _append(st, cand)
                    counts[st] = counts.get(st, 0) + 1
                    processed += 1
                    ck.update(seen_ids=sorted(seen), counts=counts, last_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
                    _save_ckpt(ck)
                    log.info("[%d] %-12s %s | acc=%d nr=%d rej=%d",
                             processed, st, rec.get("official_citation"),
                             counts.get("accepted", 0), counts.get("needs_review", 0), counts.get("rejected", 0))
                params = None
                url = data.get("next")

    log.info("FL crawl done | processed=%d counts=%s elapsed_h=%.2f",
             processed, json.dumps(counts), (args.hours * 3600 - max(0, deadline - time.time())) / 3600)
    return 0


if __name__ == "__main__":
    sys.exit(main())
