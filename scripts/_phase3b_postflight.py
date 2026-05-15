"""Phase 3 (B) - Post-flight verification (5 checks).

Self-tees to logs/phase3b_postflight.log. Prints PHASE3B: GREEN if all 5 pass,
PHASE3B: RED with specifics on first failure.

Checks:
1. Schema sample validates (5 random structured_field_inference rows -> InjuryClassification.model_validate)
2. Source count >= stats['reclassified']
3. No "Unspecified" sentinel remains in injury_category
4. Pending review queue count >= stats['queued_to_review']
5. Queued review rows are well-formed (3 random samples)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "phase3b_postflight.log"
STATS_PATH = LOG_DIR / "phase3b_reclassify_stats.json"

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
log = logging.getLogger("phase3b_postflight")

from app.core.database import get_db  # noqa: E402
from app.services.injury_classifier.schema import (  # noqa: E402
    InjuryClassification,
    ClassificationSource,
)


def load_stats() -> dict:
    if not STATS_PATH.exists():
        raise SystemExit(f"Stats file not found: {STATS_PATH}")
    with STATS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


async def check_1_schema_sample(db) -> tuple[bool, str]:
    resp = (
        db.table("settle_contributions")
        .select("id, injury_classification")
        .eq("injury_classification->>source", ClassificationSource.STRUCTURED_FIELD_INFERENCE.value)
        .limit(50)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return False, "No structured_field_inference rows found to sample"
    sample = random.sample(rows, min(5, len(rows)))
    for row in sample:
        try:
            payload = row["injury_classification"]
            if isinstance(payload, str):
                payload = json.loads(payload)
            InjuryClassification.model_validate(payload)
        except Exception as e:  # noqa: BLE001
            return False, f"Validation failed for row {row['id']}: {e}"
    return True, f"Validated {len(sample)} sample rows"


async def check_2_source_count(db, stats: dict) -> tuple[bool, str]:
    resp = (
        db.table("settle_contributions")
        .select("id", count="exact")
        .eq("injury_classification->>source", ClassificationSource.STRUCTURED_FIELD_INFERENCE.value)
        .execute()
    )
    actual = resp.count if resp.count is not None else len(resp.data or [])
    expected = stats.get("reclassified", 0)
    if actual < expected:
        return False, f"Source count mismatch: DB has {actual}, stats says {expected}"
    return True, f"Source count {actual} >= stats reclassified {expected}"


async def check_3_no_unspecified(db) -> tuple[bool, str]:
    resp = (
        db.table("settle_contributions")
        .select("id")
        .cs("injury_category", ["Unspecified"])
        .execute()
    )
    bad = resp.data or []
    if bad:
        return False, f"Found {len(bad)} rows still containing 'Unspecified' sentinel"
    return True, "No 'Unspecified' sentinel rows remain"


async def check_4_review_queue_count(db, stats: dict) -> tuple[bool, str]:
    resp = (
        db.table("injury_review_queue")
        .select("id", count="exact")
        .eq("status", "pending")
        .execute()
    )
    actual = resp.count if resp.count is not None else len(resp.data or [])
    expected = stats.get("queued_to_review", 0)
    if actual < expected:
        return False, f"Review queue mismatch: DB has {actual}, stats says {expected}"
    return True, f"Review queue pending count {actual} >= stats queued {expected}"


async def check_5_queued_well_formed(db) -> tuple[bool, str]:
    resp = (
        db.table("injury_review_queue")
        .select("id, contribution_id, classification_snapshot, triggers, status")
        .eq("status", "pending")
        .limit(50)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return False, "No pending review queue rows to sample"
    sample = random.sample(rows, min(3, len(rows)))
    for row in sample:
        snap = row.get("classification_snapshot")
        if isinstance(snap, str):
            try:
                snap = json.loads(snap)
            except Exception as e:  # noqa: BLE001
                return False, f"Queue row {row['id']} snapshot not parseable JSON: {e}"
        try:
            InjuryClassification.model_validate(snap)
        except Exception as e:  # noqa: BLE001
            return False, f"Queue row {row['id']} snapshot fails InjuryClassification validation: {e}"

        triggers = row.get("triggers")
        if isinstance(triggers, str):
            try:
                triggers = json.loads(triggers)
            except Exception:  # noqa: BLE001
                triggers = None
        if not isinstance(triggers, list) or len(triggers) == 0:
            return False, f"Queue row {row['id']} triggers is empty or not list"

        if row.get("status") != "pending":
            return False, f"Queue row {row['id']} status != 'pending'"
    return True, f"Validated {len(sample)} queued review rows"


async def main() -> int:
    db = await get_db()
    if db is None:
        log.error("get_db() returned None - cannot run postflight.")
        return 2

    stats = load_stats()
    log.info(f"Loaded stats: reclassified={stats.get('reclassified')} queued={stats.get('queued_to_review')}")

    results: list[tuple[str, bool, str]] = []

    name = "1. Schema sample validates"
    ok, msg = await check_1_schema_sample(db)
    log.info(f"[{name}] {'PASS' if ok else 'FAIL'} - {msg}")
    results.append((name, ok, msg))

    name = "2. Source count matches stats"
    ok, msg = await check_2_source_count(db, stats)
    log.info(f"[{name}] {'PASS' if ok else 'FAIL'} - {msg}")
    results.append((name, ok, msg))

    name = "3. No 'Unspecified' sentinel remains"
    ok, msg = await check_3_no_unspecified(db)
    log.info(f"[{name}] {'PASS' if ok else 'FAIL'} - {msg}")
    results.append((name, ok, msg))

    name = "4. Review queue count matches"
    ok, msg = await check_4_review_queue_count(db, stats)
    log.info(f"[{name}] {'PASS' if ok else 'FAIL'} - {msg}")
    results.append((name, ok, msg))

    name = "5. Queued review rows well-formed"
    ok, msg = await check_5_queued_well_formed(db)
    log.info(f"[{name}] {'PASS' if ok else 'FAIL'} - {msg}")
    results.append((name, ok, msg))

    all_pass = all(ok for _, ok, _ in results)
    if all_pass:
        log.info("PHASE3B: GREEN")
        return 0
    failed = [n for n, ok, _ in results if not ok]
    log.error(f"PHASE3B: RED - failed: {failed}")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
