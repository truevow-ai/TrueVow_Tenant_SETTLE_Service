"""
filter_cap_min_year.py — Filter CAP pipeline JSONL output files to exclude rows
with year < MIN_YEAR (default 2015). This cleans pre-2015 appellate opinions from
the on-disk corpus so that only current (2015+) settlement data remains.

Operates in-place: overwrites each JSONL file with only the rows that pass the
year filter. Creates a .bak backup first.

Run:
    python filter_cap_min_year.py --min-year 2015
    python filter_cap_min_year.py --min-year 2015 --dry-run   # report only, no changes
    python filter_cap_min_year.py --min-year 2015 --dir out/cap_crawl_california  # single dir
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MIN_YEAR_DEFAULT = 2015
_SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = _SCRIPT_DIR / "out"


def _has_year_field(row: dict) -> bool:
    return "year" in row and row["year"] is not None


def filter_file(filepath: Path, min_year: int, dry_run: bool) -> tuple[int, int, int]:
    """Filter a single JSONL file. Returns (kept, removed, skipped_preserved)."""
    lines = filepath.read_text(encoding="utf-8-sig").splitlines()
    kept: list[str] = []
    removed = 0
    skipped = 0

    for line in lines:
        line_s = line.strip()
        if not line_s:
            continue
        try:
            row = json.loads(line_s)
        except json.JSONDecodeError:
            kept.append(line_s)
            skipped += 1
            continue

        yr = row.get("year")
        if yr is not None and isinstance(yr, (int, float)) and yr < min_year:
            removed += 1
            continue
        kept.append(line_s)

    if not dry_run and removed > 0:
        filepath.rename(filepath.with_suffix(filepath.suffix + ".bak"))
        filepath.write_text("\n".join(kept) + "\n", encoding="utf-8")

    return len(kept) - skipped, removed, skipped


def _is_cap_jsonl(filename: str) -> bool:
    """Match CAP pipeline outputs: cap_<slug>_<state>_<status>.jsonl"""
    return filename.startswith("cap_") and filename.endswith(".jsonl")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Filter CAP JSONL files to min-year threshold"
    )
    ap.add_argument(
        "--min-year", type=int, default=MIN_YEAR_DEFAULT,
        help=f"Minimum year to keep (default {MIN_YEAR_DEFAULT})",
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="Report what would be removed without making changes",
    )
    ap.add_argument(
        "--dir", type=Path, default=None,
        help="Target a single directory (default: all out/ dirs recursively)",
    )
    args = ap.parse_args()

    dirs = [args.dir] if args.dir else [OUT_DIR]
    total_files = 0
    total_kept = 0
    total_removed = 0

    for root_dir in dirs:
        if not root_dir.is_dir():
            print(f"ERROR: directory not found: {root_dir}")
            return 1

        for jsonl_path in sorted(root_dir.rglob("*.jsonl")):
            if not _is_cap_jsonl(jsonl_path.name):
                continue
            kept, removed, skipped = filter_file(jsonl_path, args.min_year, args.dry_run)
            if removed > 0 or args.dry_run:
                status = "[DRY-RUN] " if args.dry_run else ""
                print(
                    f"{status}{jsonl_path.relative_to(_SCRIPT_DIR.parent)}"
                    f"  kept={kept}  removed={removed}  skipped={skipped}"
                )
            total_files += 1
            total_kept += kept
            total_removed += removed

    print()
    print(
        f"Total: {total_files} files, {total_kept} rows kept, "
        f"{total_removed} rows would be removed"
        if args.dry_run
        else f"Total: {total_files} files, {total_kept} rows kept, {total_removed} rows removed"
    )
    print("Run with --dry-run first to preview.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
