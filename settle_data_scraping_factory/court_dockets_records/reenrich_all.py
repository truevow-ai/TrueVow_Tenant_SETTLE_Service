"""
reenrich_all.py — Re-run the snippet-capturing enricher over every accepted /
needs_review base file, so every enriched field carries source evidence for the
no-fabrication gate. Reads opinion text from the shared _cache (no new network
calls for already-fetched opinions).

Usage:
    python reenrich_all.py --dry-run     # list files, no work
    python reenrich_all.py               # re-enrich all base files
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

from _common.fetcher import Fetcher  # noqa: E402
from cds_enrich_offline import enrich_file  # noqa: E402

OUT = _HERE / "out"


def targets() -> list[Path]:
    accepted_only = "--accepted-only" in sys.argv
    pats = ("*_accepted.jsonl",) if accepted_only else ("*_accepted.jsonl", "*_needs_review.jsonl")
    seen: set[Path] = set()
    for pat in pats:
        for f in OUT.rglob(pat):
            n = f.name
            if any(t in n for t in (".verdicts.", ".rejects.", ".enriched.", "_enriched.", "_exa")):
                continue
            if not f.stat().st_size:
                continue
            seen.add(f)
    return sorted(seen)


def main() -> int:
    dry = "--dry-run" in sys.argv
    files = targets()
    print(f"{'DRY-RUN: ' if dry else ''}{len(files)} base files to re-enrich")
    if dry:
        for f in files:
            print("  ", f.relative_to(OUT))
        return 0

    done = total_enriched = 0
    with Fetcher(min_delay=0.0) as ft:  # cache hits dominate; 0 delay
        for f in files:
            try:
                r = enrich_file(f, dry_run=False, fetcher=ft)
                done += 1
                total_enriched += r["enriched"]
                print(f"  [{done}/{len(files)}] {f.parent.name}/{f.name}: {r['enriched']}/{r['total_rows']}")
            except Exception as e:
                print(f"  ERROR {f.name}: {type(e).__name__}: {e}")
    print(f"\nDONE: {done} files, {total_enriched} rows enriched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
