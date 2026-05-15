"""Phase 3 (B) - BEFORE-state enumeration snapshot.

Run BEFORE _phase3b_reclassify.py. Captures the (jurisdiction, case_type, injury)
triple counts on approved rows in their post-Phase-3-(C), pre-Phase-3-(B) state.
This baseline is used by the commit message to compute the diff to AFTER.

Writes: logs/phase3b_enumeration_before.json
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = LOG_DIR / "phase3b_enumeration_before.json"

from app.core.database import get_db  # noqa: E402


PAGE_SIZE = 500


async def fetch_approved(db) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        resp = (
            db.table("settle_contributions")
            .select("id, jurisdiction, case_type, injury_category")
            .eq("status", "approved")
            .order("created_at", desc=False)
            .limit(PAGE_SIZE)
            .offset(offset)
            .execute()
        )
        batch = resp.data or []
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


async def main() -> int:
    db = await get_db()
    if db is None:
        print("get_db() returned None - cannot run BEFORE enumeration.")
        return 2

    rows = await fetch_approved(db)

    triple_counts: Counter = Counter()
    for row in rows:
        jur = row.get("jurisdiction") or "<unknown>"
        ct = row.get("case_type") or "<unknown>"
        for inj in (row.get("injury_category") or []):
            triple_counts[(jur, ct, inj)] += 1

    pairs_at_or_above_50 = [
        {"jurisdiction": j, "case_type": c, "injury": i, "n": n}
        for (j, c, i), n in triple_counts.items() if n >= 50
    ]
    pairs_at_or_above_50.sort(key=lambda x: -x["n"])

    top_25 = [
        {"jurisdiction": j, "case_type": c, "injury": i, "n": n}
        for (j, c, i), n in triple_counts.most_common(25)
    ]

    orange_county_premises_soft_tissue = triple_counts.get(
        ("Orange County, FL", "Premises Liability", "soft_tissue"), 0
    )

    # Serialize the full triples dict for downstream diff computation
    all_triples = [
        {"jurisdiction": j, "case_type": c, "injury": i, "n": n}
        for (j, c, i), n in triple_counts.items()
    ]

    before_state = {
        "total_approved": len(rows),
        "unique_triples": len(triple_counts),
        "pairs_at_or_above_50": pairs_at_or_above_50,
        "top_25_pairs": top_25,
        "orange_county_fl_premises_soft_tissue_n": orange_county_premises_soft_tissue,
        "all_triples": all_triples,
    }

    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(before_state, f, indent=2, default=str)

    real_county_at_50 = len([
        p for p in pairs_at_or_above_50 if "Unknown" not in p["jurisdiction"]
    ])
    print(f"BEFORE: total_approved={len(rows)} unique_triples={len(triple_counts)}")
    print(f"BEFORE: pairs at n>=50 (all): {len(pairs_at_or_above_50)}")
    print(f"BEFORE: real-county pairs at n>=50: {real_county_at_50}")
    print(f"BEFORE: Orange County FL Premises Liability soft_tissue n={orange_county_premises_soft_tissue}")
    print(f"BEFORE: Top 5:")
    for p in top_25[:5]:
        print(f"  n={p['n']:>4}  {p['jurisdiction']} | {p['case_type']} | {p['injury']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
