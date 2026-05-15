"""Phase 3.5 — Real-narrative reclassification.

For every settle_contributions row where case_narrative is now populated
(post-Phase-3.5 acquisition), re-run the classifier on the REAL narrative.
This overrides Phase 3.B's STRUCTURED_FIELD_INFERENCE classification with
a higher-fidelity rule_engine_* result.

Merge semantic mirrors Phase 3.B:
  merged_tags = existing_valid | classifier_tags  (drop UNCLASSIFIED sentinel)
If merged is empty (classifier matched nothing AND no valid existing tags),
write an UNCLASSIFIED record with review_trigger=UNCLASSIFIED_NARRATIVE so
the row enters review queue.

Writes:
  - settle_contributions.injury_category := merged_tags
  - settle_contributions.injury_classification := JSONB audit record
  - injury_review_queue insert for human_review_required=True rows

Idempotent: re-runs are safe (re-classification of a real narrative is
deterministic).
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = REPO_ROOT / "logs" / "phase35_reclassify.log"
STATS_PATH = REPO_ROOT / "logs" / "phase35_reclassify_stats.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("phase35_reclassify")
logging.getLogger("httpx").setLevel(logging.WARNING)

sys.path.insert(0, str(REPO_ROOT))

import asyncio  # noqa: E402

from app.core.database import get_db  # noqa: E402
from app.services.injury_classifier import (  # noqa: E402
    CLASSIFIER_VERSION,
    ClassificationSource,
    InjuryClassification,
    InjuryTag,
    classify,
)

PAGE_SIZE = 500
VALID_ENUM_VALUES = {t.value for t in InjuryTag}


def _normalize_existing_tags(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str):
        # Tolerate string-serialized array
        s = value.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return [str(v) for v in parsed]
            except Exception:
                pass
        return [s]
    return []


def parse_verdict_amount(value) -> int | None:
    """Best-effort parse of outcome_amount_range (e.g., '$1M-$5M' -> 1_000_000)."""
    if not value:
        return None
    s = str(value)
    m = re.search(r"\$?([\d.]+)\s*([KMBkmb])?", s)
    if not m:
        return None
    try:
        num = float(m.group(1))
    except ValueError:
        return None
    suffix = (m.group(2) or "").upper()
    multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(suffix, 1)
    return int(num * multiplier)


async def main() -> int:
    db = await get_db()
    if db is None:
        log.error("get_db() returned None")
        return 2

    log.info("=" * 60)
    log.info("PHASE 3.5 RECLASSIFY (real narrative)")
    log.info("=" * 60)

    # Pull all contributions with case_narrative populated
    rows: list[dict] = []
    offset = 0
    while True:
        resp = (
            db.table("settle_contributions")
            .select(
                "id, case_narrative, injury_category, injury_classification, "
                "outcome_amount_range"
            )
            .order("id", desc=False)
            .limit(PAGE_SIZE)
            .offset(offset)
            .execute()
        )
        page = resp.data or []
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    eligible = [
        r for r in rows
        if (r.get("case_narrative") or "").strip()
    ]
    log.info("contributions with case_narrative: %d", len(eligible))

    stats = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "rows_with_case_narrative": len(eligible),
        "reclassified": 0,
        "tags_added_vs_existing": 0,
        "source_upgraded_from_structured": 0,
        "had_no_prior_classification": 0,
        "review_required": 0,
        "queued_to_review": 0,
        "errors": 0,
        "tag_distribution": Counter(),
        "source_distribution": Counter(),
    }

    for idx, row in enumerate(eligible, start=1):
        if idx % 25 == 0:
            log.info(
                "progress: %d/%d  reclassified=%d errors=%d queued=%d",
                idx, len(eligible),
                stats["reclassified"], stats["errors"], stats["queued_to_review"],
            )
        try:
            narrative = row["case_narrative"]
            verdict_amount = parse_verdict_amount(row.get("outcome_amount_range"))
            classification = classify(narrative=narrative, verdict_amount=verdict_amount)

            classifier_tags = {
                t.value if hasattr(t, "value") else str(t)
                for t in classification.tags
            }
            classifier_tags.discard(InjuryTag.UNCLASSIFIED.value)

            existing_tags = _normalize_existing_tags(row.get("injury_category"))
            existing_valid = {t for t in existing_tags if t in VALID_ENUM_VALUES}

            merged_tags = sorted(existing_valid | classifier_tags)

            # Detect source upgrade (Phase 3.B set this to STRUCTURED_FIELD_INFERENCE)
            prior_classification = row.get("injury_classification") or {}
            prior_source = prior_classification.get("source") if isinstance(
                prior_classification, dict
            ) else None
            if prior_source == ClassificationSource.STRUCTURED_FIELD_INFERENCE.value:
                stats["source_upgraded_from_structured"] += 1
            elif not prior_classification:
                stats["had_no_prior_classification"] += 1

            tags_added = len(merged_tags) - len(existing_valid)

            if not merged_tags:
                # Real-narrative produced zero classifier hits AND no existing valid tags.
                # Write an UNCLASSIFIED record with the narrative's actual classifier
                # output (which has its own UNCLASSIFIED tag + review trigger).
                final = classification.model_copy(update={
                    "tags": classification.tags,
                    "classifier_version": CLASSIFIER_VERSION,
                    "classified_at": datetime.now(timezone.utc),
                })
                payload = final.model_dump(mode="json")
                update_resp = (
                    db.table("settle_contributions")
                    .update({
                        "injury_category": [],
                        "injury_classification": payload,
                    })
                    .eq("id", row["id"])
                    .execute()
                )
                if update_resp.data is None:
                    stats["errors"] += 1
                    continue
                stats["reclassified"] += 1
                stats["source_distribution"][str(final.source)] += 1
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
                        stats["errors"] += 1
                    else:
                        stats["queued_to_review"] += 1
                continue

            # Standard merge path: classifier matched something OR existing was valid
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
                source=classification.source,  # Real-narrative source: rule_engine_*
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
                stats["errors"] += 1
                continue

            stats["reclassified"] += 1
            stats["tags_added_vs_existing"] += max(tags_added, 0)
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
                    stats["errors"] += 1
                else:
                    stats["queued_to_review"] += 1

        except Exception as e:  # noqa: BLE001
            stats["errors"] += 1
            log.warning("Row %s failed: %s: %s", row.get("id"), type(e).__name__, e)

    stats["finished_at"] = datetime.now(timezone.utc).isoformat()
    stats["tag_distribution"] = dict(stats["tag_distribution"])
    stats["source_distribution"] = dict(stats["source_distribution"])

    STATS_PATH.write_text(json.dumps(stats, indent=2, default=str), encoding="utf-8")
    log.info("=" * 60)
    log.info("DONE")
    log.info("=" * 60)
    log.info("rows_eligible: %d", stats["rows_with_case_narrative"])
    log.info("reclassified: %d", stats["reclassified"])
    log.info("source_upgraded_from_structured: %d", stats["source_upgraded_from_structured"])
    log.info("had_no_prior_classification: %d", stats["had_no_prior_classification"])
    log.info("tags_added_vs_existing: %d", stats["tags_added_vs_existing"])
    log.info("review_required: %d", stats["review_required"])
    log.info("queued_to_review: %d", stats["queued_to_review"])
    log.info("errors: %d", stats["errors"])
    log.info("source_distribution: %s", stats["source_distribution"])
    log.info("tag_distribution: %s", stats["tag_distribution"])
    log.info("stats: %s", STATS_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
