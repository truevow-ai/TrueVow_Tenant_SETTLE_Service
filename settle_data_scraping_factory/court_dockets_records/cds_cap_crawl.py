"""
cds_cap_crawl.py — Long-running per-state Caselaw Access Project (CAP) crawler.

CAP (static.case.law) is a static, public, bulk corpus with NO API rate limit, so one
of these can run per state, fully in parallel, at full (polite) speed. For a target
state it derives the state's reporters from CAP metadata (cds_cap_explorer.build_targets),
walks each reporter's volumes, filters cases to the state, runs each opinion through the
shared zero-fabrication pipeline (cds_cap_pipeline.build_candidate), and APPENDS the
useful rows (accepted + needs_review only — rejected are counted but not persisted, to
keep the corpus manageable) to out/cap_crawl_<state>/cap_<state>_<status>.jsonl.

Resumable: it checkpoints completed reporter/volume keys, so a restart skips finished
volumes (a crash mid-volume re-does that volume; duplicate rows are deduped server-side
at load). Provenance (source_url + sha256 + fetched_at) is preserved on every record.

Run:
    python cds_cap_crawl.py --state Texas --hours 720 --min-delay 1.0 --min-year 1960
    python cds_cap_crawl.py --state "New York" --hours 0.02 --max-cases 3   # smoke test
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
import cds_cap_explorer as explorer  # noqa: E402
import cds_cap_fetcher as capf  # noqa: E402
from cds_cap_pipeline import build_candidate  # noqa: E402


def _state_slug(state: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", state.lower()).strip("_")


def _load_ckpt(ckpt: Path) -> dict:
    if ckpt.exists():
        try:
            return json.loads(ckpt.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"done_volumes": [], "counts": {"accepted": 0, "needs_review": 0, "rejected": 0},
            "started_at": None, "last_at": None}


def _save_ckpt(ckpt: Path, ck: dict) -> None:
    tmp = ckpt.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ck, default=str), encoding="utf-8")
    tmp.replace(ckpt)


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-state CAP crawler (unlimited static.case.law)")
    ap.add_argument("--state", required=True, help="Full state name_long, e.g. Texas / 'New York'")
    ap.add_argument("--hours", type=float, default=720.0)
    ap.add_argument("--min-delay", type=float, default=1.0, help="Seconds between requests (politeness)")
    ap.add_argument("--min-year", type=int, default=1960, help="Skip reporters ending before this year")
    ap.add_argument("--max-cases", type=int, default=0, help="0 = unlimited (until --hours / corpus end)")
    args = ap.parse_args()
    # Accept either a full name ("New York") or a no-space slug ("new_york"). The slug form
    # lets the supervisor launch multi-word states without any shell/quoting pitfalls.
    args.state = args.state.replace("_", " ").strip()
    if args.state == args.state.lower():
        args.state = args.state.title()

    out_dir = _HERE / "out" / f"cap_crawl_{_state_slug(args.state)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt = out_dir / "checkpoint.json"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(out_dir / "crawl.log", encoding="utf-8"), logging.StreamHandler()],
    )
    log = logging.getLogger(f"cap_crawl_{_state_slug(args.state)}")

    ck = _load_ckpt(ckpt)
    done = set(ck.get("done_volumes", []))
    counts = ck.get("counts", {"accepted": 0, "needs_review": 0, "rejected": 0})
    ck["started_at"] = ck.get("started_at") or time.strftime("%Y-%m-%dT%H:%M:%S")
    deadline = time.time() + args.hours * 3600
    processed = 0

    def _append(status: str, row: dict) -> None:
        with (out_dir / f"cap_{_state_slug(args.state)}_{status}.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")

    # use_cache=False: at multi-state scale the on-disk cache would bloat to many GB, and the
    # done-volume checkpoint already provides resume (finished volumes are skipped, not refetched).
    with Fetcher(min_delay=args.min_delay, use_cache=False) as f:
        try:
            manifest = explorer.build_targets(f, [args.state])
        except Exception as e:
            log.error("could not build reporter manifest for %s: %s", args.state, e)
            return 1
        reporters = []
        for t in manifest["targets"]:
            ey = t.get("end_year")
            if ey is None or ey >= args.min_year:
                reporters.append(t["reporter_slug"])
        log.info("CAP crawl start | state=%s reporters=%d (min_year=%s) min_delay=%ss hours=%s done_vols=%d",
                 args.state, len(reporters), args.min_year, args.min_delay, args.hours, len(done))

        for slug in reporters:
            if time.time() >= deadline or (args.max_cases and processed >= args.max_cases):
                break
            try:
                volumes = capf.list_volumes(f, slug)
            except Exception as e:
                log.warning("list_volumes %s failed: %s", slug, str(e)[:80])
                continue
            for volume in volumes:
                if time.time() >= deadline or (args.max_cases and processed >= args.max_cases):
                    break
                vkey = f"{slug}/{volume}"
                if vkey in done:
                    continue
                try:
                    metas, meta_res = capf.list_cases_meta(f, slug, volume)
                except Exception as e:
                    log.warning("cases_meta %s failed: %s", vkey, str(e)[:80])
                    continue
                for meta in metas:
                    if time.time() >= deadline or (args.max_cases and processed >= args.max_cases):
                        break
                    if (meta.get("jurisdiction") or {}).get("name_long") != args.state:
                        continue
                    file_name = meta.get("file_name")
                    if not file_name:
                        continue
                    rec = capf.normalize_case(meta, slug, volume, meta_res.url, meta_res.sha256, meta_res.fetched_at)
                    try:
                        text, tres = capf.fetch_case_text(f, slug, volume, file_name)
                    except Exception as e:
                        log.warning("case_text %s/%s failed: %s", vkey, file_name, str(e)[:60])
                        continue
                    rec["opinion_text"] = text
                    rec["text_sha256"] = tres.sha256
                    cand = build_candidate(rec)
                    st = cand["status"]
                    counts[st] = counts.get(st, 0) + 1
                    processed += 1
                    if st in ("accepted", "needs_review"):
                        _append(st, cand)
                # volume finished -> checkpoint (mid-volume crash re-does this volume; dedup at load)
                done.add(vkey)
                ck.update(done_volumes=sorted(done), counts=counts, last_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
                _save_ckpt(ckpt, ck)
                log.info("done %s | seen=%d acc=%d nr=%d rej=%d",
                         vkey, processed, counts.get("accepted", 0), counts.get("needs_review", 0), counts.get("rejected", 0))

    completed = time.time() < deadline and not (args.max_cases and processed >= args.max_cases)
    if completed:
        (out_dir / "COMPLETE").write_text(time.strftime("%Y-%m-%dT%H:%M:%S"), encoding="utf-8")
        log.info("CAP crawl COMPLETE (corpus exhausted) | state=%s", args.state)
    log.info("CAP crawl done | state=%s processed=%d counts=%s", args.state, processed, json.dumps(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
