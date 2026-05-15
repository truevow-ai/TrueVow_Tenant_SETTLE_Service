"""Phase 3 (B) - Pseudo-narrative reclassification from structured fields.

Applies to ALL rows in settle_contributions. For each row, synthesize a
pseudo-narrative from injury_category + primary_diagnosis + treatment_type +
imaging_findings + defendant_category + case_type, run the deterministic
classifier on that text, MERGE classifier-derived tags with valid existing
legacy tags (dropping "Unspecified" sentinels), and write back:

  - injury_category := merged tags (may add tags, drops Unspecified)
  - injury_classification := full audit-trail JSONB with
    source=structured_field_inference, classifier_version=CLASSIFIER_VERSION

Rows whose classification is human_review_required=True also get an INSERT
into injury_review_queue with status='pending'.

Writes:
  - logs/phase3b_reclassify.log         (progress + per-row warnings)
  - logs/phase3b_reclassify_stats.json  (final stats dict)

Surface-back triggers handled inside script:
  - error rate > 5%  -> exit code 3
  - review-required rate > 50%  -> exit code 4
  - zero cells flipped is *not* assessed here (deferred to Step 4 enumeration)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
from collections import Counter
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
LOG_PATH = LOG_DIR / "phase3b_reclassify.log"
STATS_PATH = LOG_DIR / "phase3b_reclassify_stats.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("phase3b_reclassify")

from app.core.database import get_db  # noqa: E402
from app.services.injury_classifier import (  # noqa: E402
    CLASSIFIER_VERSION,
    ClassificationSource,
    InjuryClassification,
    InjuryTag,
    classify,
    synthesize_pseudo_narrative,
)


PAGE_SIZE = 500
SELECT_COLUMNS = (
    "id, injury_category, primary_diagnosis, treatment_type, "
    "imaging_findings, defendant_category, case_type, outcome_amount_range"
)


def parse_verdict_amount(bucket: str | None) -> int | None:
    """Best-effort midpoint parse of bucket strings like '$1M+', '$100k-$250k'."""
    if not bucket:
        return None
    try:
        if "+" in bucket:
            m = re.search(r"\$(\d+\.?\d*)([KkMm])\+?", bucket)
            if m:
                base = float(m.group(1))
                mult = 1_000_000 if m.group(2).lower() == "m" else 1_000
                return int(base * mult * 1.5)
        m = re.match(r"\$(\d+\.?\d*)([KkMm])?-\$(\d+\.?\d*)([KkMm])?", bucket)
        if m:
            low = float(m.group(1)) * (1_000_000 if (m.group(2) or "").lower() == "m" else 1_000)
            high = float(m.group(3)) * (1_000_000 if (m.group(4) or "").lower() == "m" else 1_000)
            return int((low + high) / 2)
    except Exception:
        return None
    return None


async def fetch_all_rows(db) -> list[dict]:
    """Paginate through settle_contributions pulling structured-field columns."""
    all_rows: list[dict] = []
    offset = 0
    while True:
        response = (
            db.table("settle_contributions")
            .select(SELECT_COLUMNS)
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


def _normalize_existing_tags(raw) -> list[str]:
    """Defensive coercion: legacy rows may store comma-joined string."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(t) for t in raw if t]
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    return []


async def main() -> int:
    db = await get_db()
    if db is None:
        logger.error("get_db() returned None - cannot run reclassify in mock mode or with bad creds.")
        return 2

    logger.info("Fetching settle_contributions rows ...")
    rows = await fetch_all_rows(db)
    logger.info("Fetched %d rows", len(rows))

    stats: dict = {
        "total": len(rows),
        "empty_narrative_skipped": 0,
        "zero_tags_after_classify": 0,
        "reclassified": 0,
        "tags_added_vs_existing": 0,
        "tags_removed_unspecified": 0,
        "review_required": 0,
        "queued_to_review": 0,
        "source_distribution": Counter(),
        "tag_distribution": Counter(),
        "errors": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    valid_enum_values = {t.value for t in InjuryTag}

    for idx, row in enumerate(rows, 1):
        if idx % 50 == 0:
            logger.info(
                "Progress: %d/%d (reclassified=%d empty=%d zero=%d review=%d errors=%d)",
                idx, len(rows), stats["reclassified"], stats["empty_narrative_skipped"],
                stats["zero_tags_after_classify"], stats["queued_to_review"], stats["errors"],
            )
        try:
            pseudo_narrative = synthesize_pseudo_narrative(row)
            if not pseudo_narrative:
                stats["empty_narrative_skipped"] += 1
                continue

            verdict_amount = parse_verdict_amount(row.get("outcome_amount_range"))
            classification = classify(narrative=pseudo_narrative, verdict_amount=verdict_amount)

            classifier_tags = {
                t.value if hasattr(t, "value") else str(t)
                for t in classification.tags
            }
            # Drop the special UNCLASSIFIED tag from the merge set - it shouldn't
            # propagate to injury_category alongside real tags.
            classifier_tags.discard(InjuryTag.UNCLASSIFIED.value)

            existing_tags = _normalize_existing_tags(row.get("injury_category"))
            existing_valid = {t for t in existing_tags if t in valid_enum_values}
            had_unspecified = "Unspecified" in existing_tags

            merged_tags = sorted(existing_valid | classifier_tags)
            if not merged_tags:
                stats["zero_tags_after_classify"] += 1
                continue

            tags_added = len(merged_tags) - len(existing_valid)

            final = InjuryClassification(
                tags=[InjuryTag(t) for t in merged_tags],
                confidence={
                    t: classification.confidence.get(t, 1.0) if t in classifier_tags else 1.0
                    for t in merged_tags
                },
                matched_spans={
                    t: classification.matched_spans.get(t, []) if t in classifier_tags else []
                    for t in merged_tags
                },
                source=ClassificationSource.STRUCTURED_FIELD_INFERENCE,
                classifier_version=CLASSIFIER_VERSION,
                classified_at=datetime.now(timezone.utc),
                review_triggers=classification.review_triggers,
                human_review_required=classification.human_review_required,
                reviewed=False,
            )

            payload = final.model_dump(mode="json")

            update_resp = (
                db.table("settle_contributions")
                .update({
                    "injury_category": merged_tags,
                    "injury_classification": payload,
                })
                .eq("id", row["id"])
                .execute()
            )
            if update_resp.data is None:
                logger.warning(
                    "Row %s: update returned None (REST error) - counting as error",
                    row["id"],
                )
                stats["errors"] += 1
                continue

            stats["reclassified"] += 1
            stats["tags_added_vs_existing"] += tags_added
            if had_unspecified:
                stats["tags_removed_unspecified"] += 1
            stats["source_distribution"][str(final.source)] += 1
            for tag in merged_tags:
                stats["tag_distribution"][tag] += 1

            if final.human_review_required:
                stats["review_required"] += 1
                triggers_payload = [
                    t.value if hasattr(t, "value") else str(t)
                    for t in final.review_triggers
                ]
                queue_resp = (
                    db.table("injury_review_queue")
                    .insert({
                        "contribution_id": row["id"],
                        "classification_snapshot": payload,
                        "triggers": triggers_payload,
                        "status": "pending",
                    })
                    .execute()
                )
                if queue_resp.data is None:
                    logger.warning(
                        "Row %s: review_queue insert returned None - flagging error",
                        row["id"],
                    )
                    stats["errors"] += 1
                else:
                    stats["queued_to_review"] += 1
        except Exception as e:  # noqa: BLE001
            stats["errors"] += 1
            logger.warning(
                "Row %s failed: %s: %s",
                row.get("id"), type(e).__name__, e,
            )

    stats["finished_at"] = datetime.now(timezone.utc).isoformat()
    # Convert Counters to plain dicts for JSON
    stats["source_distribution"] = dict(stats["source_distribution"])
    stats["tag_distribution"] = dict(stats["tag_distribution"])

    with STATS_PATH.open("w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, default=str)

    logger.info(
        "DONE. Reclassified %d/%d | tags_added=%d | unspec_dropped=%d | "
        "review_required=%d | queued=%d | errors=%d. Stats -> %s",
        stats["reclassified"], stats["total"], stats["tags_added_vs_existing"],
        stats["tags_removed_unspecified"], stats["review_required"],
        stats["queued_to_review"], stats["errors"], STATS_PATH,
    )

    # Surface-back triggers
    error_rate = (stats["errors"] / stats["total"]) if stats["total"] else 0.0
    if error_rate > 0.05:
        logger.error("Error rate %.2f%% exceeds 5%% threshold", error_rate * 100)
        return 3

    if stats["total"]:
        review_rate = stats["review_required"] / stats["total"]
        if review_rate > 0.50:
            logger.error("Review-required rate %.2f%% exceeds 50%% threshold", review_rate * 100)
            return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
