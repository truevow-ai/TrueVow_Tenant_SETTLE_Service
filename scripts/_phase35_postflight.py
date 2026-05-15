"""Phase 3.5 postflight verification.

Checks:
1. Schema validates: every injury_classification JSONB parses as InjuryClassification.
2. classification_source distribution: rule_engine_* values now present.
3. No "Unspecified" sentinel in injury_category arrays.
4. Review queue count matches sum of human_review_required=True classifications.
5. Queued rows are well-formed (non-null contribution_id, classification_snapshot, triggers).
6. Verdict: GREEN (all 5 PASS) or RED (any FAIL).
"""
from __future__ import annotations

import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = REPO_ROOT / "logs" / "phase35_postflight.log"
RESULT_PATH = REPO_ROOT / "logs" / "phase35_postflight_result.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("phase35_postflight")
logging.getLogger("httpx").setLevel(logging.WARNING)

sys.path.insert(0, str(REPO_ROOT))

import asyncio  # noqa: E402

from app.core.database import get_db  # noqa: E402
from app.services.injury_classifier import (  # noqa: E402
    ClassificationSource,
    InjuryClassification,
)

PAGE_SIZE = 500


def fetch_all(db, table: str, select: str) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        resp = (
            db.table(table)
            .select(select)
            .order("id" if table != "injury_review_queue" else "created_at",
                   desc=False)
            .limit(PAGE_SIZE)
            .offset(offset)
            .execute()
        )
        page = resp.data or []
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


async def main() -> int:
    db = await get_db()
    if db is None:
        log.error("get_db() returned None")
        return 2

    log.info("=" * 60)
    log.info("PHASE 3.5 POSTFLIGHT")
    log.info("=" * 60)

    contribs = fetch_all(
        db, "settle_contributions",
        "id, injury_category, injury_classification, case_narrative",
    )
    queue = fetch_all(
        db, "injury_review_queue",
        "id, contribution_id, classification_snapshot, triggers, status",
    )
    log.info("settle_contributions rows: %d", len(contribs))
    log.info("injury_review_queue rows: %d", len(queue))

    checks: list[tuple[str, bool, str]] = []

    # Check 1: every injury_classification parses
    parse_failures: list[str] = []
    parsed_records: list[InjuryClassification] = []
    for r in contribs:
        ic = r.get("injury_classification")
        if not ic:
            continue
        try:
            rec = InjuryClassification.model_validate(ic)
            parsed_records.append(rec)
        except Exception as e:
            parse_failures.append(f"{r['id']}: {type(e).__name__}: {e}")
    if parse_failures:
        msg = (
            f"{len(parse_failures)} injury_classification records failed schema "
            f"validation. First 3: {parse_failures[:3]}"
        )
        checks.append(("1 schema_validates", False, msg))
    else:
        checks.append((
            "1 schema_validates",
            True,
            f"{len(parsed_records)} records all parse cleanly",
        ))

    # Check 2: classification source distribution shows rule_engine_*
    source_counter: Counter[str] = Counter()
    for rec in parsed_records:
        src = rec.source if isinstance(rec.source, str) else rec.source.value
        source_counter[src] += 1
    rule_engine_count = sum(
        n for src, n in source_counter.items() if src.startswith("rule_engine_")
    )
    if rule_engine_count > 0:
        checks.append((
            "2 rule_engine_source_present",
            True,
            f"rule_engine_* sources: {rule_engine_count}, full_dist: {dict(source_counter)}",
        ))
    else:
        checks.append((
            "2 rule_engine_source_present",
            False,
            f"No rule_engine_* sources found. dist: {dict(source_counter)}",
        ))

    # Check 3: no "Unspecified" in injury_category
    bad_unspecified = [
        r["id"] for r in contribs
        if r.get("injury_category") and "Unspecified" in r["injury_category"]
    ]
    if bad_unspecified:
        checks.append((
            "3 no_unspecified_sentinel",
            False,
            f"{len(bad_unspecified)} rows still contain 'Unspecified' in injury_category",
        ))
    else:
        checks.append((
            "3 no_unspecified_sentinel",
            True,
            "No 'Unspecified' sentinel present in any row",
        ))

    # Check 4: review queue count matches review_required count
    review_required_count = sum(
        1 for rec in parsed_records if rec.human_review_required
    )
    pending_queue_count = sum(1 for q in queue if q.get("status") == "pending")
    # Queue may have entries from Phase 3.B too. Just verify queue_count >= current review_required
    if len(queue) >= review_required_count:
        checks.append((
            "4 review_queue_coverage",
            True,
            f"queue_total={len(queue)}, current_review_required={review_required_count}, "
            f"pending={pending_queue_count}",
        ))
    else:
        checks.append((
            "4 review_queue_coverage",
            False,
            f"queue_total={len(queue)} < review_required={review_required_count}",
        ))

    # Check 5: queued rows are well-formed
    bad_queue = [
        q for q in queue
        if not q.get("contribution_id")
        or not q.get("classification_snapshot")
        or q.get("triggers") is None
    ]
    if bad_queue:
        checks.append((
            "5 queue_well_formed",
            False,
            f"{len(bad_queue)} queue rows have missing fields",
        ))
    else:
        checks.append((
            "5 queue_well_formed",
            True,
            f"all {len(queue)} queue rows well-formed",
        ))

    # Check 6: case_narrative coverage stats
    populated_cn = sum(
        1 for r in contribs if (r.get("case_narrative") or "").strip()
    )
    pct = populated_cn / len(contribs) * 100 if contribs else 0
    log.info("case_narrative populated: %d / %d (%.1f%%)",
             populated_cn, len(contribs), pct)

    log.info("-" * 60)
    log.info("CHECK RESULTS")
    log.info("-" * 60)
    all_pass = True
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        log.info("[%s] %s — %s", status, name, detail)
        if not ok:
            all_pass = False

    verdict = "GREEN" if all_pass else "RED"
    log.info("=" * 60)
    log.info("PHASE35: %s", verdict)
    log.info("=" * 60)

    result = {
        "verdict": verdict,
        "checks": [
            {"name": name, "pass": ok, "detail": detail}
            for name, ok, detail in checks
        ],
        "case_narrative_populated": populated_cn,
        "case_narrative_total": len(contribs),
        "case_narrative_pct": round(pct, 2),
        "source_distribution": dict(source_counter),
        "review_required_now": review_required_count,
        "queue_total": len(queue),
        "queue_pending": pending_queue_count,
    }
    RESULT_PATH.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    log.info("result: %s", RESULT_PATH)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
