"""
run_exa_top_states.py — Scaled carrier+age Exa enrichment for the highest-volume
states. Carriers + ages ONLY (news amounts excluded by policy). Every field is
verbatim+source-url verified downstream by the no-fabrication gate.

Idempotent: writes <file>_exa_enriched.jsonl per source; skip-complete inside
enrich_file_exa avoids API calls where both fields already exist.
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

# Load API keys from the repo-root .env.local regardless of CWD (a bare
# subprocess launch may not sit in the repo root).
from dotenv import load_dotenv  # noqa: E402
for _envp in (_HERE.parent.parent / ".env.local", Path.cwd() / ".env.local"):
    if _envp.exists():
        load_dotenv(_envp)
        break

import os  # noqa: E402
import cds_enrich_exa  # noqa: E402
# Ensure the module-level key reflects the loaded env.
cds_enrich_exa.EXA_API_KEY = os.getenv("EXA_API_KEY", cds_enrich_exa.EXA_API_KEY)
from cds_enrich_exa import enrich_file_exa  # noqa: E402

OUT = _HERE / "out"

# Highest-volume accepted-enriched files (top 8 by record count).
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

FIELDS = {"insurance_carrier", "plaintiff_age_range"}


def main() -> int:
    for rel in TARGETS:
        p = OUT / rel
        if not p.exists():
            print(f"SKIP (missing): {rel}", flush=True)
            continue
        # cl_crawl_florida has no _accepted_enriched yet in some layouts; guard.
        print(f"=== {rel} ===", flush=True)
        try:
            res = enrich_file_exa(p, dry_run=False, fields=FIELDS)
            print(f"  searched={res.get('exa_searched')} enriched={res.get('exa_enriched')} "
                  f"new_fields={res.get('new_fields_added')} skipped={res.get('skipped_complete')}",
                  flush=True)
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}", flush=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
