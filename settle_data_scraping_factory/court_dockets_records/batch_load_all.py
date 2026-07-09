"""
batch_load_all.py — Load all completed crawl JSONL outputs into the SETTLE review queue.

Scans out/ recursively for *_accepted.jsonl and *_needs_review.jsonl files,
deduplicates paths, and calls cds_cap_loader.load_file() on each.

Run:
    python batch_load_all.py --dry-run
    python batch_load_all.py              # live POST to SETTLE API
    python batch_load_all.py --sources cap --dry-run   # only CAP sources
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_FACTORY_ROOT = _HERE.parent
for _p in (_FACTORY_ROOT, _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from cds_cap_loader import load_file  # noqa: E402

OUT = _HERE / "out"


def find_payloads(out_root: Path, sources: list[str] | None = None) -> list[Path]:
    # Prefer the ENRICHED version of every accepted/needs_review file. The
    # enriched files carry carriers, damages, ages, ISO-mappable dates — loading
    # the bare *_accepted.jsonl would silently discard all enrichment work.
    # Derived/intermediate files are never payloads.
    _DERIVED = (".verdicts.", ".rejects.", ".exa_dry.", ".enriched.")

    def _excluded(f: Path) -> bool:
        return any(tag in f.name for tag in _DERIVED) or ".verdicts." in f.name

    def _src_ok(f: Path) -> bool:
        if f.parent.name == "morelaw_crawl" or f.name.startswith("morelaw"):
            return not sources or "morelaw" in sources
        if "courtlistener" in f.name.lower() or f.parent.name.startswith("cl_"):
            return not sources or "courtlistener" in sources
        return not sources or "cap" in sources

    payloads: set[Path] = set()
    for base_pat in ("*_accepted.jsonl", "*_needs_review.jsonl"):
        for f in out_root.rglob(base_pat):
            if _excluded(f) or not f.stat().st_size or not _src_ok(f):
                continue
            # Skip a base file when its *_enriched.jsonl sibling exists — the
            # enriched sibling is picked up by the *_enriched glob below.
            enriched = f.with_name(f.stem + "_enriched.jsonl")
            if enriched.exists():
                continue
            payloads.add(f)

    for enr_pat in ("*_accepted_enriched.jsonl", "*_needs_review_enriched.jsonl"):
        for f in out_root.rglob(enr_pat):
            if _excluded(f) or not f.stat().st_size or not _src_ok(f):
                continue
            payloads.add(f)

    return sorted(payloads)


def main() -> int:
    ap = argparse.ArgumentParser(description="Batch-load all crawl outputs into SETTLE")
    ap.add_argument("--dry-run", action="store_true", help="Map records but do not POST")
    ap.add_argument("--sources", help="Comma-separated filter: cap,courtlistener,morelaw")
    ap.add_argument("--limit", type=int, default=0, help="Max files to load (0=all)")
    ap.add_argument("--max-records", type=int, default=5000,
                    help="Max records per bulk-insert call")
    args = ap.parse_args()

    src_filter = [s.strip().lower() for s in args.sources.split(",")] if args.sources else None
    payloads = find_payloads(OUT, src_filter)

    print(f"Found {len(payloads)} payload files across {len({p.parent.name for p in payloads})} directories")
    if args.limit:
        payloads = payloads[: args.limit]
        print(f"Limited to first {len(payloads)} files")

    stats = {"files_ok": 0, "files_failed": 0, "total_records": 0}
    for p in payloads:
        try:
            result = load_file(p, dry_run=args.dry_run)
            status = "DRY" if result.get("mode") == "dry_run" else result.get("http_status", "??")
            records = result.get("mapped", 0)
            inserted = result.get("inserted", 0)
            skipped = result.get("skipped", 0)
            failed = result.get("failed", 0)
            print(f"  [{status}] {p.relative_to(OUT)} records={records}"
                  + (f" inserted={inserted} skipped={skipped} failed={failed}" if not args.dry_run else ""))
            if result.get("http_status") in (200, 201, None):
                stats["files_ok"] += 1
                stats["total_records"] += records
            else:
                stats["files_failed"] += 1
        except Exception as e:
            print(f"  [ERR] {p.relative_to(OUT)}: {e!s:.120}")
            stats["files_failed"] += 1

    print(f"\nDone: {stats['files_ok']} loaded, {stats['files_failed']} failed, {stats['total_records']} total records")
    return 1 if stats["files_failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
