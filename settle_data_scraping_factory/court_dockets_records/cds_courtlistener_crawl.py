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


def _get_json_riding_throttle(f, url, params, headers, log, sleep_s, deadline):
    """GET JSON, sleeping/retrying through throttles until it succeeds or the deadline."""
    while time.time() < deadline:
        try:
            return f.get_json(url, params=params, headers=headers).json()
        except Exception as e:
            log.warning("throttled/error: %s -- sleeping %.0fs for the rolling window", str(e)[:90], sleep_s)
            time.sleep(sleep_s)
    return None


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

    with Fetcher(min_delay=args.min_delay) as f:
        for court in courts:
            if time.time() >= deadline or (args.max_opinions and processed >= args.max_opinions):
                break
            url = f"{cl.CL_API}/search/"
            params = {"q": args.query, "type": "o", "court": court, "order_by": "dateFiled desc"}
            page = 0
            while url and time.time() < deadline:
                if args.max_opinions and processed >= args.max_opinions:
                    break
                data = _get_json_riding_throttle(f, url, params, headers, log, args.throttle_sleep, deadline)
                if not data:
                    break
                page += 1
                results = data.get("results", [])
                log.info("court=%s page=%d results=%d", court, page, len(results))
                for item in results:
                    if time.time() >= deadline or (args.max_opinions and processed >= args.max_opinions):
                        break
                    op_id = cl._opinion_id(item)
                    if not op_id or str(op_id) in seen:
                        continue
                    seen.add(str(op_id))
                    try:
                        rec = cl.fetch_opinion_record(f, item, court, headers)
                    except Exception as e:
                        log.warning("detail %s error: %s -- sleeping %.0fs", op_id, str(e)[:80], args.throttle_sleep)
                        time.sleep(args.throttle_sleep)
                        continue
                    if rec is None:
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
