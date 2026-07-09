"""
cds_courtlistener_crawl.py — Long-running, rate-limit-respecting CourtListener crawler.

CourtListener's free authenticated tier allows only 5 req/min, 50 req/hr, and 125 req/day
(rolling windows; most-restrictive wins). This crawler paces EVERY request through the
shared Fetcher (default min_delay=700s ~= the 125/day ceiling) so it can run unattended for
~24h without ever tripping the throttle.

It processes states sequentially from a comma-separated list, cursor-paginating each state's
courts, running each opinion through the shared zero-fabrication pipeline
(cds_cap_pipeline.build_candidate), and APPENDING results to
out/cl_crawl_<state>/courtlistener_<state>_<status>.jsonl (durable on crash). It checkpoints
per-state seen opinion ids (resume-safe + dedup), pre-seeds `seen` from existing buckets,
and RIDES OUT throttling by sleeping and retrying when the API returns 429.

Run unattended:
    python cds_courtlistener_crawl.py --states florida,california,texas --hours 720 --min-delay 700

Quick smoke test:
    python cds_courtlistener_crawl.py --states florida --hours 0.05 --min-delay 2 --max-opinions 2
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


def _state_slug(state: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", state.lower()).strip("_")


def _parse_states(raw: str) -> list[str]:
    states = []
    for tok in raw.split(","):
        tok = tok.strip().replace("_", " ")
        if not tok:
            continue
        if tok == tok.lower():
            tok = tok.title()
        states.append(tok)
    return states


def _load_ckpt(ckpt_path: Path) -> dict:
    if ckpt_path.exists():
        try:
            return json.loads(ckpt_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"seen_ids": [], "counts": {"accepted": 0, "needs_review": 0, "rejected": 0},
            "started_at": None, "last_at": None}


def _save_ckpt(ckpt_path: Path, ck: dict) -> None:
    tmp = ckpt_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ck, default=str), encoding="utf-8")
    tmp.replace(ckpt_path)


def _preseed_seen(slug: str) -> set:
    seed: set = set()
    out_root = _HERE / "out"
    if not out_root.exists():
        return seed
    for f in out_root.rglob(f"courtlistener_{slug}*.jsonl"):
        try:
            for line in f.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line:
                    continue
                cite = (json.loads(line).get("official_citation") or "")
                m = re.match(r"courtlistener:(\d+)", cite)
                if m:
                    seed.add(m.group(1))
        except Exception:
            continue
    return seed


def _get_riding(f, url, params, headers, log, sleep_s, deadline, max_fails_per_url=3):
    fails = 0
    while time.time() < deadline and fails < max_fails_per_url:
        try:
            return f.get(url, params=params, headers=headers)
        except Exception as e:
            fails += 1
            log.warning("throttled/error (%d/%d): %s -- sleeping %.0fs",
                        fails, max_fails_per_url, str(e)[:90], sleep_s)
            time.sleep(sleep_s)
    return None


def _fetch_record_riding(f, item, queried_court, headers, log, sleep_s, deadline):
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


def _crawl_state(state: str, args, key, headers, log, global_deadline: float) -> int:
    slug = _state_slug(state)
    out_dir = _HERE / "out" / f"cl_crawl_{slug}"
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = out_dir / "checkpoint.json"

    ck = _load_ckpt(ckpt_path)
    seen = set(ck.get("seen_ids", [])) | _preseed_seen(slug)
    counts = ck.get("counts", {"accepted": 0, "needs_review": 0, "rejected": 0})
    ck["started_at"] = ck.get("started_at") or time.strftime("%Y-%m-%dT%H:%M:%S")

    courts = cl.STATE_TO_COURTS.get(state, [])
    if not courts:
        log.warning("No CourtListener courts found for state=%s", state)
        return 0

    deadline = global_deadline
    processed = 0

    def _append(status: str, row: dict) -> None:
        with (out_dir / f"courtlistener_{slug}_{status}.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")

    log.info("%s crawl start | courts=%s query=%r min_delay=%ss hours=%s preseeded_seen=%d",
             state, courts, args.query, args.min_delay, args.hours, len(seen))

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
                        break
                    seen.add(str(op_id))
                    if status != "ok" or rec is None:
                        ck.update(seen_ids=sorted(seen), last_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
                        _save_ckpt(ckpt_path, ck)
                        continue
                    cand = build_candidate(rec)
                    st = cand["status"]
                    _append(st, cand)
                    counts[st] = counts.get(st, 0) + 1
                    processed += 1
                    ck.update(seen_ids=sorted(seen), counts=counts, last_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
                    _save_ckpt(ckpt_path, ck)
                    log.info("[%d] %-12s %s | acc=%d nr=%d rej=%d",
                             processed, st, rec.get("official_citation"),
                             counts.get("accepted", 0), counts.get("needs_review", 0), counts.get("rejected", 0))
                params = None
                url = data.get("next")

    log.info("%s crawl done | processed=%d counts=%s elapsed_h=%.2f",
             state, processed, json.dumps(counts),
             (args.hours * 3600 - max(0, deadline - time.time())) / 3600)
    return processed


def main() -> int:
    ap = argparse.ArgumentParser(description="Paced, unattended CourtListener multi-state crawler")
    ap.add_argument("--states", required=True,
                    help="Comma-separated state names or slugs, e.g. 'florida,california,texas'")
    ap.add_argument("--hours", type=float, default=24.0, help="How long to run")
    ap.add_argument("--min-delay", type=float, default=700.0,
                    help="Seconds between requests (~700 keeps under 125/day)")
    ap.add_argument("--query", default=cl.DEFAULT_QUERY)
    ap.add_argument("--max-opinions", type=int, default=0, help="0 = unlimited (until --hours)")
    ap.add_argument("--throttle-sleep", type=float, default=900.0,
                    help="Seconds to sleep when the API throttles")
    args = ap.parse_args()

    states = _parse_states(args.states)
    if not states:
        print("Error: no valid states provided", file=sys.stderr)
        return 1

    log = logging.getLogger("cl_multi_crawl")
    log.setLevel(logging.INFO)

    key = cl._load_api_key()
    headers = cl._auth_headers(key)
    global_deadline = time.time() + args.hours * 3600

    total = 0
    for state in states:
        if time.time() >= global_deadline:
            break
        slug = _state_slug(state)
        st_log_path = _HERE / "out" / f"cl_crawl_{slug}" / "crawl.log"
        st_log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(st_log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(fh)
        if not any(isinstance(h, logging.StreamHandler) for h in log.handlers):
            ch = logging.StreamHandler()
            ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            log.addHandler(ch)

        n = _crawl_state(state, args, key, headers, log, global_deadline)
        total += n
        log.removeHandler(fh)

    log.info("multi-state crawl done | total_processed=%d states=%s", total, states)
    return 0


if __name__ == "__main__":
    sys.exit(main())
