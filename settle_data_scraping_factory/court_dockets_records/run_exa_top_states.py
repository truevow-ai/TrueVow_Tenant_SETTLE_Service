"""
run_exa_top_states.py — Scaled carrier+age Exa enrichment for the highest-volume
states. Carriers + ages ONLY (news amounts excluded by policy). Every field is
verbatim+source-url verified downstream by the no-fabrication gate.

Crash-safe & resumable: appends each enriched row to <file>_exa_enriched.jsonl
as it goes and records progress in <file>.exa_progress. Re-running resumes from
the last completed row (skips rows already written), so repeated interruptions
never lose work or re-spend API budget.

Heartbeat: prints a timestamped line every HEARTBEAT_EVERY rows so an observer
can confirm it is alive and not stuck.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

from dotenv import load_dotenv  # noqa: E402
for _envp in (_HERE.parent.parent / ".env.local", Path.cwd() / ".env.local"):
    if _envp.exists():
        load_dotenv(_envp)
        break

import cds_enrich_exa  # noqa: E402
cds_enrich_exa.EXA_API_KEY = os.getenv("EXA_API_KEY", cds_enrich_exa.EXA_API_KEY)
from cds_enrich_exa import search_news, enrich_exa, EXA_DELAY  # noqa: E402

OUT = _HERE / "out"
FIELDS = {"insurance_carrier", "plaintiff_age_range"}
HEARTBEAT_EVERY = 25

TARGETS = [
    "cap_crawl_california/cap_california_accepted_enriched.jsonl",
    "cl_crawl_florida/courtlistener_florida_accepted_enriched.jsonl",
    "cap_crawl_pennsylvania/cap_pennsylvania_accepted_enriched.jsonl",
    "cap_crawl_florida/cap_florida_accepted_enriched.jsonl",
    "cap_crawl_new_york/cap_new_york_accepted_enriched.jsonl",
    "cap_crawl_georgia/cap_georgia_accepted_enriched.jsonl",
    "cap_crawl_north_carolina/cap_north_carolina_accepted_enriched.jsonl",
    "cap_crawl_texas/cap_texas_accepted_enriched.jsonl",
]


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _read_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8-sig").splitlines() if x.strip()]


def process_file(rel: str) -> None:
    src = OUT / rel
    if not src.exists():
        print(f"SKIP (missing): {rel}", flush=True)
        return
    out_path = src.with_name(src.stem + "_exa_enriched.jsonl")
    prog_path = src.with_suffix(".exa_progress")

    rows = _read_jsonl(src)
    done = 0
    if prog_path.exists():
        try:
            done = int(prog_path.read_text().strip() or "0")
        except ValueError:
            done = 0
    mode = "a" if done else "w"

    print(f"=== {rel} | {len(rows)} rows | resuming at {done} ===", flush=True)
    enriched_ct = 0
    with out_path.open(mode, encoding="utf-8") as out_f:
        for i in range(done, len(rows)):
            c = rows[i]
            if not all(c.get(f) for f in FIELDS):
                pairs = search_news(c)
                if pairs:
                    nf = enrich_exa(c, pairs, fields=FIELDS)
                    if nf:
                        c.update(nf)
                        enriched_ct += 1
                    time.sleep(EXA_DELAY)
            out_f.write(json.dumps(c, default=str) + "\n")
            out_f.flush()
            prog_path.write_text(str(i + 1))
            if (i + 1) % HEARTBEAT_EVERY == 0:
                print(f"  [{_ts()}] {rel.split('/')[-1]}: {i+1}/{len(rows)} "
                      f"(+{enriched_ct} enriched this run)", flush=True)
    print(f"  [{_ts()}] DONE {rel.split('/')[-1]}: {len(rows)} rows, +{enriched_ct} enriched", flush=True)


def main() -> int:
    print(f"[{_ts()}] Exa top-states run start (fields={sorted(FIELDS)})", flush=True)
    for rel in TARGETS:
        try:
            process_file(rel)
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {rel}: {type(e).__name__}: {e}", flush=True)
    print(f"[{_ts()}] ALL DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
