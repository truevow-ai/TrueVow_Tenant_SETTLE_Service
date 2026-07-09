"""Batch enrich CAP accepted files — process up to max_cases total."""
import sys
from pathlib import Path

RECORDS_DIR = Path("settle_data_scraping_factory/court_dockets_records")
sys.path.insert(0, str(RECORDS_DIR))
from cds_enrich_offline import enrich_file  # noqa: E402

out_dir = RECORDS_DIR / "out"
max_cases = int(sys.argv[1]) if len(sys.argv) > 1 else 500

files = sorted(
    p for p in out_dir.rglob("cap_*_accepted.jsonl")
    if ".enriched." not in p.name
    and ".verdicts." not in p.name
    and p.stat().st_size > 0
)

# Sort by size (smallest first) so we make visible progress
files.sort(key=lambda p: p.stat().st_size)

remaining = []
processed = 0
for p in files:
    ep = p.with_name(p.stem + "_enriched.jsonl")
    if ep.exists():
        continue
    lines = len(p.read_text(encoding="utf-8").splitlines())
    if processed + lines <= max_cases:
        remaining.append(p)
        processed += lines
    else:
        break

print(f"Processing {len(remaining)} files, {processed} cases (limit: {max_cases})")
print()

grand_total = 0
grand_enriched = 0

for i, p in enumerate(remaining):
    label = f"{p.parent.name}/{p.name}"
    try:
        r = enrich_file(p, dry_run=False)
        grand_total += r["total_rows"]
        grand_enriched += r["enriched"]
        print(f"[{i+1}/{len(remaining)}] {label}: {r['enriched']}/{r['total_rows']} enriched -> {r['output_file']}")
    except Exception as e:
        print(f"[{i+1}/{len(remaining)}] {label}: ERROR - {e}")

print()
print(f"BATCH DONE: {grand_enriched}/{grand_total} enriched ({100*grand_enriched//max(1,grand_total)}%)")
