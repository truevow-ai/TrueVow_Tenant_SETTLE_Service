"""Batch enrich CAP accepted files only."""
import sys
from pathlib import Path

RECORDS_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("settle_data_scraping_factory/court_dockets_records")
sys.path.insert(0, str(RECORDS_DIR))
from cds_enrich_offline import enrich_file  # noqa: E402

out_dir = RECORDS_DIR / "out"

# CAP files only (skip CourtListener, MoreLaw, files we already enriched)
files = sorted(
    p for p in out_dir.rglob("cap_*_accepted.jsonl")
    if ".enriched." not in p.name
    and ".verdicts." not in p.name
    and p.stat().st_size > 0
    and not p.parent.name.startswith(".")
)

# Skip files already processed (check if _enriched version exists)
remaining = []
for p in files:
    enriched_path = p.with_name(p.stem + "_enriched.jsonl")
    if not enriched_path.exists():
        remaining.append(p)

print(f"Remaining CAP accepted files: {len(remaining)}")
total_lines = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in remaining)
print(f"Total cases: {total_lines}")
print()

if not remaining:
    print("All files already enriched!")
    sys.exit(0)

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
print(f"TOTAL: {grand_enriched}/{grand_total} CAP cases enriched ({100*grand_enriched//max(1,grand_total)}%)")
