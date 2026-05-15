"""Phase 3.B remediation pass: scrub "Unspecified" sentinel from rows where
classification produced no inferred tags.

Target: rows where injury_category contains "Unspecified" AND
injury_classification IS NULL (i.e., the reclassification pass didn't write
any record because classifier_tags + existing_valid = empty set).

Action: replace injury_category with [] (empty array, drops Unspecified).
Does NOT write an injury_classification record - these rows have no inferred
classification. Future Phase 3.5 narrative-acquisition will overwrite both
columns when real prose is available.

Idempotent: re-runs are safe (no Unspecified-containing rows means no work).

Architect-logic-gap remediation: Step 3 reference code's
`if not merged_tags: continue` skipped the DB write for the empty-result case,
leaving ["Unspecified"] in place. This pass closes the gap without touching
the 47 successfully-classified records.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "phase3b_scrub_unspecified.log"
STATS_PATH = LOG_DIR / "phase3b_scrub_unspecified_stats.json"

# Self-tee
_handlers = [
    logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8"),
    logging.StreamHandler(sys.stdout),
]
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=_handlers,
)
log = logging.getLogger("phase3b_scrub_unspecified")

from app.core.database import get_db  # noqa: E402


async def main() -> int:
    db = await get_db()
    if db is None:
        log.error("get_db() returned None - cannot run scrub.")
        return 2

    log.info("Locating rows where injury_category contains 'Unspecified' ...")
    resp = (
        db.table("settle_contributions")
        .select("id, injury_category, injury_classification")
        .cs("injury_category", ["Unspecified"])
        .execute()
    )
    rows = resp.data or []
    log.info(f"Found {len(rows)} candidate rows")

    stats = {
        "total_offenders_found": len(rows),
        "scrubbed": 0,
        "skipped_has_classification": 0,
        "skipped_no_unspecified": 0,
        "errors": 0,
    }

    for row in rows:
        try:
            existing = row.get("injury_category") or []
            if "Unspecified" not in existing:
                stats["skipped_no_unspecified"] += 1
                continue

            # Defense-in-depth: don't scrub if there's an existing classification
            # (those rows were intentionally classified - separate from the bug case)
            ic = row.get("injury_classification")
            if ic and ic != {}:
                stats["skipped_has_classification"] += 1
                continue

            # Build new injury_category: drop "Unspecified", preserve everything else
            # (in practice for the target rows, this yields [])
            new_tags = [t for t in existing if t != "Unspecified"]

            db.table("settle_contributions").update({
                "injury_category": new_tags,
            }).eq("id", row["id"]).execute()

            stats["scrubbed"] += 1
        except Exception as e:  # noqa: BLE001
            stats["errors"] += 1
            log.warning(f"Row {row.get('id')} failed: {type(e).__name__}: {e}")

    with STATS_PATH.open("w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, default=str)

    log.info(
        f"DONE. Scrubbed {stats['scrubbed']}/{stats['total_offenders_found']} | "
        f"skipped_has_classification={stats['skipped_has_classification']} | "
        f"skipped_no_unspecified={stats['skipped_no_unspecified']} | "
        f"errors={stats['errors']}. Stats -> {STATS_PATH}"
    )
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
