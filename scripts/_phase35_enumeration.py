"""Phase 3.5 - AFTER-state enumeration probe.

Read-only. Counts (jurisdiction, case_type, injury) triples on approved rows
post-Phase-3.5. Compares against the Phase 3.B AFTER snapshot
(logs/phase3b_enumeration_after.json) which is the BEFORE baseline for 3.5.

Writes:
  - logs/phase35_enumeration.json : full snapshot per architect-spec
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
BEFORE_PATH = LOG_DIR / "phase3b_enumeration_after.json"  # 3.B AFTER == 3.5 BEFORE
OUTPUT_PATH = LOG_DIR / "phase35_enumeration.json"

from app.core.database import get_db  # noqa: E402

PAGE_SIZE = 500

# Sentinel jurisdictions to exclude from "real-county" rollup.
SENTINEL_JURISDICTION_SUBSTRINGS = ("unknown", "<unknown>")


def is_real_county(jurisdiction: str) -> bool:
    if not jurisdiction:
        return False
    j = jurisdiction.strip().lower()
    if not j:
        return False
    for s in SENTINEL_JURISDICTION_SUBSTRINGS:
        if s in j:
            return False
    return True


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


def load_before() -> dict | None:
    if not BEFORE_PATH.exists():
        return None
    with BEFORE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


async def main() -> int:
    db = await get_db()
    if db is None:
        print("get_db() returned None - cannot run enumeration.")
        return 2

    rows = await fetch_approved(db)

    triple_counts: Counter = Counter()
    for row in rows:
        jur = row.get("jurisdiction") or "<unknown>"
        ct = row.get("case_type") or "<unknown>"
        for inj in (row.get("injury_category") or []):
            triple_counts[(jur, ct, inj)] += 1

    pairs_at_50 = [
        {"jurisdiction": j, "case_type": c, "injury": i, "n": n}
        for (j, c, i), n in triple_counts.items() if n >= 50
    ]
    pairs_at_50.sort(key=lambda x: -x["n"])

    real_county_pairs_at_50 = [p for p in pairs_at_50 if is_real_county(p["jurisdiction"])]

    top_25 = [
        {"jurisdiction": j, "case_type": c, "injury": i, "n": n}
        for (j, c, i), n in triple_counts.most_common(25)
    ]

    real_county_top_5 = []
    for (j, c, i), n in triple_counts.most_common():
        if is_real_county(j):
            real_county_top_5.append({"jurisdiction": j, "case_type": c, "injury": i, "n": n})
            if len(real_county_top_5) >= 5:
                break

    orange_premises_soft = triple_counts.get(
        ("Orange County, FL", "Premises Liability", "soft_tissue"), 0
    )

    all_triples = [
        {"jurisdiction": j, "case_type": c, "injury": i, "n": n}
        for (j, c, i), n in triple_counts.items()
    ]

    # Diff vs Phase 3.B AFTER snapshot.
    before = load_before()
    newly_populated: list[dict] = []
    increased: list[dict] = []
    before_pairs_at_50_count = 0
    before_real_county_pairs_at_50_count = 0
    before_orange = 0
    if before is not None:
        before_triples = {
            (t["jurisdiction"], t["case_type"], t["injury"]): t["n"]
            for t in before.get("all_triples", [])
        }
        after_triples = {
            (t["jurisdiction"], t["case_type"], t["injury"]): t["n"]
            for t in all_triples
        }
        all_keys = set(before_triples.keys()) | set(after_triples.keys())
        for k in all_keys:
            b = before_triples.get(k, 0)
            a = after_triples.get(k, 0)
            j, c, i = k
            entry = {"jurisdiction": j, "case_type": c, "injury": i, "before": b, "after": a}
            if b == 0 and a >= 1:
                newly_populated.append(entry)
            elif a > b > 0:
                increased.append(entry)
        newly_populated.sort(key=lambda x: -x["after"])
        increased.sort(key=lambda x: -(x["after"] - x["before"]))

        before_pairs_at_50_list = before.get("pairs_at_or_above_50", [])
        before_pairs_at_50_count = len(before_pairs_at_50_list)
        before_real_county_pairs_at_50_count = len([
            p for p in before_pairs_at_50_list if is_real_county(p["jurisdiction"])
        ])
        before_orange = before.get("orange_county_fl_premises_soft_tissue_n", 0)

    snapshot = {
        "total_approved": len(rows),
        "unique_triples": len(triple_counts),
        "pairs_at_or_above_50": pairs_at_50,
        "real_county_pairs_at_or_above_50": real_county_pairs_at_50,
        "orange_county_fl_premises_soft_tissue_n": orange_premises_soft,
        "top_25_pairs": top_25,
        "real_county_top_5_pairs": real_county_top_5,
        "newly_populated_vs_phase3b": newly_populated,
        "increased_cells_vs_phase3b": increased,
        "baseline_phase3b": {
            "pairs_at_or_above_50_count": before_pairs_at_50_count,
            "real_county_pairs_at_or_above_50_count": before_real_county_pairs_at_50_count,
            "orange_county_fl_premises_soft_tissue_n": before_orange,
            "total_approved": (before or {}).get("total_approved"),
            "unique_triples": (before or {}).get("unique_triples"),
        },
    }

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, default=str)

    # Stdout headlines.
    print("=" * 60)
    print("PHASE 3.5 ENUMERATION  (read-only)")
    print("=" * 60)
    print(f"total_approved:          {len(rows)}")
    print(f"unique_triples:          {len(triple_counts)}")
    print(f"pairs at n>=50 (all):    {len(pairs_at_50)}")
    print(f"real-county pairs n>=50: BEFORE={before_real_county_pairs_at_50_count}  AFTER={len(real_county_pairs_at_50)}")
    print(f"Orange County FL PL soft_tissue: BEFORE={before_orange}  AFTER={orange_premises_soft}")
    print(f"newly-populated cells (BEFORE 0 -> AFTER >=1): {len(newly_populated)}")
    print(f"increased cells (AFTER > BEFORE):              {len(increased)}")
    print()
    print("Top 5 real-county pairs:")
    if real_county_top_5:
        for p in real_county_top_5:
            print(f"  n={p['n']:>4}  {p['jurisdiction']} | {p['case_type']} | {p['injury']}")
    else:
        print("  (none)")
    print()
    print("Top 5 pairs (all jurisdictions including sentinels):")
    for p in top_25[:5]:
        print(f"  n={p['n']:>4}  {p['jurisdiction']} | {p['case_type']} | {p['injury']}")
    if newly_populated:
        print()
        print("Top 5 newly-populated cells:")
        for p in newly_populated[:5]:
            print(f"  n={p['after']:>4}  {p['jurisdiction']} | {p['case_type']} | {p['injury']}")
    print()
    print(f"output: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
