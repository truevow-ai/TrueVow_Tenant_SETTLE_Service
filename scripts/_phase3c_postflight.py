"""Phase 3 (C) — Post-flight verification.

Runs 8 checks against Supabase Postgres via psycopg2 (session pooler URL):

 1. settle_contributions.injury_classification exists, JSONB, NOT NULL, default '{}'::jsonb
 2. settle_contributions.case_narrative exists, TEXT, nullable
 3. injury_review_queue exists with all 14 columns + idx_review_queue_status + idx_review_queue_contribution
 4. Sample 5 lifted rows: InjuryClassification.model_validate round-trips
 5. COUNT(*) WHERE injury_classification->>'source' = 'legacy_single_tag' ~= stats['lifted']
 6. COUNT(*) WHERE injury_classification = '{}'::jsonb ~= stats['skipped_empty']
 7. case_narrative IS NULL for all rows
 8. SELECT COUNT(*) FROM injury_review_queue = 0

Emits PHASE3C: GREEN or PHASE3C: RED <check_id>: <reason>.

Writes:
- logs/phase3c_postflight.log  (full output)
"""
from __future__ import annotations

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
LOG_PATH = LOG_DIR / "phase3c_postflight.log"
STATS_PATH = LOG_DIR / "phase3c_legacy_lift_stats.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("phase3c_postflight")

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env.local")
    load_dotenv()
except ImportError:
    pass

import psycopg2  # noqa: E402
import psycopg2.extras  # noqa: E402

from app.services.injury_classifier import InjuryClassification  # noqa: E402


EXPECTED_REVIEW_QUEUE_COLUMNS = {
    "id", "contribution_id", "classification_snapshot", "triggers", "status",
    "claimed_by", "claimed_at", "reviewed_by", "reviewed_at", "review_action",
    "review_notes", "final_tags", "created_at", "updated_at",
}
EXPECTED_REVIEW_QUEUE_INDEXES = {
    "idx_review_queue_status", "idx_review_queue_contribution",
}


def get_conn():
    url = (
        os.getenv("SETTLE_DATABASE_SESSION_POOLER_URL")
        or os.getenv("SETTLE_DATABASE_POOLER_CONNECTION_URL")
        or os.getenv("DATABASE_URL")
    )
    if not url:
        raise RuntimeError("No DB URL in env (SETTLE_DATABASE_SESSION_POOLER_URL / DATABASE_URL)")
    return psycopg2.connect(url)


def check_1_injury_classification_column(cur) -> tuple[bool, str]:
    cur.execute(
        """
        SELECT data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'settle_contributions'
          AND column_name = 'injury_classification'
        """
    )
    row = cur.fetchone()
    if not row:
        return False, "column missing"
    data_type, is_nullable, default = row
    if data_type != "jsonb":
        return False, f"data_type={data_type} (expected jsonb)"
    if is_nullable != "NO":
        return False, f"is_nullable={is_nullable} (expected NO)"
    if default is None or "'{}'" not in default:
        return False, f"default={default!r} (expected '{{}}'::jsonb)"
    return True, f"JSONB NOT NULL DEFAULT {default}"


def check_2_case_narrative_column(cur) -> tuple[bool, str]:
    cur.execute(
        """
        SELECT data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'settle_contributions'
          AND column_name = 'case_narrative'
        """
    )
    row = cur.fetchone()
    if not row:
        return False, "column missing"
    data_type, is_nullable = row
    if data_type != "text":
        return False, f"data_type={data_type} (expected text)"
    if is_nullable != "YES":
        return False, f"is_nullable={is_nullable} (expected YES)"
    return True, "TEXT NULL"


def check_3_review_queue_table(cur) -> tuple[bool, str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'injury_review_queue'
        """
    )
    cols = {r[0] for r in cur.fetchall()}
    missing = EXPECTED_REVIEW_QUEUE_COLUMNS - cols
    extra = cols - EXPECTED_REVIEW_QUEUE_COLUMNS
    if missing:
        return False, f"missing columns: {sorted(missing)}"
    if extra:
        return False, f"unexpected columns: {sorted(extra)}"

    cur.execute(
        """
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'injury_review_queue'
        """
    )
    idxs = {r[0] for r in cur.fetchall()}
    missing_idx = EXPECTED_REVIEW_QUEUE_INDEXES - idxs
    if missing_idx:
        return False, f"missing indexes: {sorted(missing_idx)}"
    return True, f"14 cols + {len(EXPECTED_REVIEW_QUEUE_INDEXES)} indexes present"


def check_4_sample_roundtrip(cur) -> tuple[bool, str]:
    cur.execute(
        """
        SELECT id, injury_classification
        FROM settle_contributions
        WHERE injury_classification->>'source' = 'legacy_single_tag'
        ORDER BY random()
        LIMIT 5
        """
    )
    rows = cur.fetchall()
    if not rows:
        return False, "no legacy_single_tag rows found to sample"
    parsed_ok = 0
    for row_id, payload in rows:
        try:
            InjuryClassification.model_validate(payload)
            parsed_ok += 1
        except Exception as e:  # noqa: BLE001
            return False, f"row {row_id} failed validate: {type(e).__name__}: {e}"
    return True, f"{parsed_ok}/{len(rows)} samples round-trip through Pydantic"


def check_5_legacy_count(cur, expected_lifted: int) -> tuple[bool, str]:
    cur.execute(
        """
        SELECT COUNT(*)
        FROM settle_contributions
        WHERE injury_classification->>'source' = 'legacy_single_tag'
        """
    )
    count = cur.fetchone()[0]
    if count != expected_lifted:
        return False, f"DB count {count} != stats.lifted {expected_lifted}"
    return True, f"DB legacy_single_tag count = {count} (matches stats)"


def check_6_empty_classification_count(cur, expected_skipped: int) -> tuple[bool, str]:
    cur.execute(
        """
        SELECT COUNT(*)
        FROM settle_contributions
        WHERE injury_classification = '{}'::jsonb
        """
    )
    count = cur.fetchone()[0]
    if count != expected_skipped:
        return False, f"DB count {count} != stats.skipped_empty {expected_skipped}"
    return True, f"DB empty-JSONB count = {count} (matches stats)"


def check_7_case_narrative_all_null(cur) -> tuple[bool, str]:
    cur.execute(
        "SELECT COUNT(*) FROM settle_contributions WHERE case_narrative IS NOT NULL"
    )
    count = cur.fetchone()[0]
    if count != 0:
        return False, f"{count} rows have non-NULL case_narrative (expected 0)"
    return True, "all rows case_narrative IS NULL"


def check_8_review_queue_empty(cur) -> tuple[bool, str]:
    cur.execute("SELECT COUNT(*) FROM injury_review_queue")
    count = cur.fetchone()[0]
    if count != 0:
        return False, f"{count} rows in injury_review_queue (expected 0)"
    return True, "injury_review_queue is empty"


def main() -> int:
    with STATS_PATH.open("r", encoding="utf-8") as f:
        stats = json.load(f)
    logger.info("Loaded lift stats: %s", stats)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            checks = [
                ("1 injury_classification column", lambda: check_1_injury_classification_column(cur)),
                ("2 case_narrative column", lambda: check_2_case_narrative_column(cur)),
                ("3 injury_review_queue table", lambda: check_3_review_queue_table(cur)),
                ("4 sample roundtrip", lambda: check_4_sample_roundtrip(cur)),
                ("5 legacy_single_tag count", lambda: check_5_legacy_count(cur, stats["lifted"])),
                ("6 empty JSONB count", lambda: check_6_empty_classification_count(cur, stats["skipped_empty"])),
                ("7 case_narrative all NULL", lambda: check_7_case_narrative_all_null(cur)),
                ("8 injury_review_queue empty", lambda: check_8_review_queue_empty(cur)),
            ]
            failures: list[tuple[str, str]] = []
            for name, fn in checks:
                ok, detail = fn()
                status = "PASS" if ok else "FAIL"
                logger.info("CHECK %s: %s  --  %s", name, status, detail)
                if not ok:
                    failures.append((name, detail))
    finally:
        conn.close()

    if failures:
        logger.error("PHASE3C: RED")
        for name, detail in failures:
            logger.error("  %s: %s", name, detail)
        return 1

    logger.info("PHASE3C: GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
