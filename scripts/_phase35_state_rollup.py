"""Phase 3.5 - state-tier rollup probe.

Read-only. Aggregates approved rows to (case_type, injury) pairs ignoring
jurisdiction (state-tier pool, since all data is FL). Used to evaluate the
pilot-mode gate threshold (n>=10, n>=15, n>=20, n>=25, n>=50).
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
OUTPUT_PATH = LOG_DIR / "phase35_state_tier_rollup.json"

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
    rows = await fetch_approved(db)

    # state-tier: (case_type, injury) — pool across all FL jurisdictions
    state_pair: Counter = Counter()
    # case-type only
    ct_only: Counter = Counter()
    # injury only
    inj_only: Counter = Counter()
    for row in rows:
        ct = row.get("case_type") or "<unknown>"
        ct_only[ct] += 1
        for inj in (row.get("injury_category") or []):
            state_pair[(ct, inj)] += 1
            inj_only[inj] += 1

    def cnt_at(c, n):
        return sum(1 for v in c.values() if v >= n)

    summary = {
        "total_approved": len(rows),
        "state_tier_pairs_total": len(state_pair),
        "state_tier_at_n10": cnt_at(state_pair, 10),
        "state_tier_at_n15": cnt_at(state_pair, 15),
        "state_tier_at_n20": cnt_at(state_pair, 20),
        "state_tier_at_n25": cnt_at(state_pair, 25),
        "state_tier_at_n50": cnt_at(state_pair, 50),
        "case_type_at_n10": cnt_at(ct_only, 10),
        "case_type_at_n50": cnt_at(ct_only, 50),
        "injury_at_n10": cnt_at(inj_only, 10),
        "injury_at_n50": cnt_at(inj_only, 50),
        "top_state_pairs": [
            {"case_type": ct, "injury": inj, "n": n}
            for (ct, inj), n in state_pair.most_common(25)
        ],
        "top_case_types": [
            {"case_type": k, "n": v} for k, v in ct_only.most_common(15)
        ],
        "top_injuries": [
            {"injury": k, "n": v} for k, v in inj_only.most_common(15)
        ],
    }

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    print("=" * 60)
    print("STATE-TIER ROLLUP (FL pooled)")
    print("=" * 60)
    print(f"total_approved:            {len(rows)}")
    print(f"unique state-tier pairs:   {len(state_pair)}")
    print(f"  at n>=10:                {summary['state_tier_at_n10']}")
    print(f"  at n>=15:                {summary['state_tier_at_n15']}")
    print(f"  at n>=20:                {summary['state_tier_at_n20']}")
    print(f"  at n>=25:                {summary['state_tier_at_n25']}")
    print(f"  at n>=50:                {summary['state_tier_at_n50']}")
    print(f"case_type at n>=10:        {summary['case_type_at_n10']}")
    print(f"case_type at n>=50:        {summary['case_type_at_n50']}")
    print(f"injury at n>=10:           {summary['injury_at_n10']}")
    print(f"injury at n>=50:           {summary['injury_at_n50']}")
    print()
    print("Top 15 state-tier pairs:")
    for p in summary["top_state_pairs"][:15]:
        print(f"  n={p['n']:>3}  {p['case_type']} | {p['injury']}")
    print()
    print("Top case_types:")
    for p in summary["top_case_types"][:8]:
        print(f"  n={p['n']:>3}  {p['case_type']}")
    print()
    print("Top injuries:")
    for p in summary["top_injuries"][:8]:
        print(f"  n={p['n']:>3}  {p['injury']}")
    print()
    print(f"output: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
