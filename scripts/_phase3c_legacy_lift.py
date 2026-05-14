"""Phase 3 (C) — Legacy injury_category -> injury_classification lift.

Applies to ALL rows in settle_contributions regardless of approval status.
For each row whose legacy injury_category contains at least one tag that
maps to a valid InjuryTag enum value, populate injury_classification JSONB
with source=legacy_single_tag, classifier_version=legacy, confidence=1.0.

No rule engine invocation. No narrative analysis. Pure lift of existing
structured tags into the new provenance-tracked audit shape.

Writes:
- logs/phase3c_legacy_lift.log  (progress + warnings)
- logs/phase3c_legacy_lift_stats.json  (final stats dict)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root on path when invoked from any CWD.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Force UTF-8 for Windows PowerShell log redirects.
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "phase3c_legacy_lift.log"
STATS_PATH = LOG_DIR / "phase3c_legacy_lift_stats.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("phase3c_legacy_lift")

from app.core.database import get_db  # noqa: E402
from app.services.injury_classifier import (  # noqa: E402
    ClassificationSource,
    InjuryClassification,
    InjuryTag,
    LEGACY_CLASSIFIER_VERSION,
)


PAGE_SIZE = 500


async def fetch_all_rows(db) -> list[dict]:
    """Paginate through settle_contributions pulling id + injury_category + timestamps."""
    all_rows: list[dict] = []
    offset = 0
    while True:
        response = (
            db.table("settle_contributions")
            .select("id", "injury_category", "created_at", "updated_at")
            .order("created_at", desc=False)
            .limit(PAGE_SIZE)
            .offset(offset)
            .execute()
        )
        batch = response.data or []
        if not batch:
            break
        all_rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_rows


async def main() -> int:
    db = await get_db()
    if db is None:
        logger.error("get_db() returned None — cannot run lift in mock mode or with bad creds.")
        return 2

    logger.info("Fetching settle_contributions rows ...")
    rows = await fetch_all_rows(db)
    logger.info("Fetched %d rows", len(rows))

    stats: dict = {
        "total": len(rows),
        "lifted": 0,
        "skipped_empty": 0,
        "invalid_tags_logged": 0,
        "errors": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    valid_enum_values = {t.value for t in InjuryTag}

    for idx, row in enumerate(rows, 1):
        if idx % 50 == 0:
            logger.info(
                "Progress: %d/%d (lifted=%d skipped_empty=%d invalid=%d errors=%d)",
                idx, len(rows), stats["lifted"], stats["skipped_empty"],
                stats["invalid_tags_logged"], stats["errors"],
            )
        try:
            existing_tags = row.get("injury_category") or []
            # Defensive: some legacy rows may store a comma-joined string.
            if isinstance(existing_tags, str):
                existing_tags = [t.strip() for t in existing_tags.split(",") if t.strip()]
            if not existing_tags:
                stats["skipped_empty"] += 1
                continue

            valid_tags = [t for t in existing_tags if t in valid_enum_values]
            invalid_tags = [t for t in existing_tags if t not in valid_enum_values]

            if invalid_tags:
                logger.warning(
                    "Row %s: invalid legacy tags (not in InjuryTag taxonomy): %s",
                    row["id"], invalid_tags,
                )
                stats["invalid_tags_logged"] += 1

            if not valid_tags:
                stats["skipped_empty"] += 1
                continue

            classified_at_str = (
                row.get("updated_at")
                or row.get("created_at")
                or datetime.now(timezone.utc).isoformat()
            )

            classification = InjuryClassification(
                tags=[InjuryTag(t) for t in valid_tags],
                confidence={t: 1.0 for t in valid_tags},
                matched_spans={t: [] for t in valid_tags},
                source=ClassificationSource.LEGACY_SINGLE_TAG,
                classifier_version=LEGACY_CLASSIFIER_VERSION,
                classified_at=classified_at_str,
                review_triggers=[],
                human_review_required=False,
                reviewed=False,
            )

            payload = classification.model_dump(mode="json")

            update_resp = (
                db.table("settle_contributions")
                .update({"injury_classification": payload})
                .eq("id", row["id"])
                .execute()
            )
            if update_resp.data is None:
                logger.warning(
                    "Row %s: update returned None (REST error) — counting as error",
                    row["id"],
                )
                stats["errors"] += 1
                continue

            stats["lifted"] += 1
        except Exception as e:  # noqa: BLE001
            stats["errors"] += 1
            logger.warning(
                "Row %s failed: %s: %s",
                row.get("id"), type(e).__name__, e,
            )

    stats["finished_at"] = datetime.now(timezone.utc).isoformat()
    with STATS_PATH.open("w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, default=str)

    logger.info(
        "DONE. Lifted %d/%d (empty=%d invalid=%d errors=%d). Stats -> %s",
        stats["lifted"], stats["total"], stats["skipped_empty"],
        stats["invalid_tags_logged"], stats["errors"], STATS_PATH,
    )

    # Surface-back trigger 3: lift error rate > 5%
    error_rate = (stats["errors"] / stats["total"]) if stats["total"] else 0.0
    if error_rate > 0.05:
        logger.error("Error rate %.2f%% exceeds 5%% threshold", error_rate * 100)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
