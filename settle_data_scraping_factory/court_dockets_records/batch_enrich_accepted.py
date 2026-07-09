"""Batch enrich all accepted JSONL files in out/ directory."""
import sys
import os
from pathlib import Path

RECORDS_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / ".." / "settle_data_scraping_factory" / "court_dockets_records"
RECORDS_DIR = RECORDS_DIR.resolve()
sys.path.insert(0, str(RECORDS_DIR))

from cds_enrich_offline import enrich_file  # noqa: E402

out_dir = RECORDS_DIR / "out"

accepted_files = sorted(
    p for p in out_dir.rglob("*_accepted.jsonl")
    if ".enriched." not in p.name
    and ".verdicts." not in p.name
    and p.stat().st_size > 0
)

print(f"Processing {len(accepted_files)} accepted files across all states...")
print()

grand_total = 0
grand_enriched = 0

for p in accepted_files:
    label = f"{p.parent.name}/{p.name}"
    try:
        r = enrich_file(p, dry_run=False)
        grand_total += r["total_rows"]
        grand_enriched += r["enriched"]
        print(f"  {label}: {r['enriched']:>6}/{r['total_rows']:>6} enriched  -> {r['output_file']}")
    except Exception as e:
        print(f"  {label}: ERROR - {e}")

print()
print(f"TOTAL: {grand_enriched}/{grand_total} cases enriched ({100*grand_enriched//max(1,grand_total)}%)")
