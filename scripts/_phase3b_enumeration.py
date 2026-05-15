"""Phase 3 (B) - AFTER-state enumeration probe with BEFORE/AFTER diff.

Run AFTER _phase3b_reclassify.py. Captures the (jurisdiction, case_type, injury)
triple counts on approved rows post-Phase-3-(B), then compares to the BEFORE
snapshot at logs/phase3b_enumeration_before.json.

Writes:
  - logs/phase3b_enumeration_after.json   : AFTER state full snapshot
  - logs/phase3b_enumeration_diff.json    : BEFORE -> AFTER diff (cells flipped, etc.)
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
BEFORE_PATH = LOG_DIR / "phase3b_enumeration_before.json"
AFTER_PATH = LOG_DIR / "phase3b_enumeration_after.json"
DIFF_PATH = LOG_DIR / "phase3b_enumeration_diff.json"

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


def load_before() -> dict | None:
    if not BEFORE_PATH.exists():
        return None
    with BEFORE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


async def main() -> int:
    db = await get_db()
    if db is None:
        print("get_db() returned None - cannot run AFTER enumeration.")
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

    all_triples = [
        {"jurisdiction": j, "case_type": c, "injury": i, "n": n}
        for (j, c, i), n in triple_counts.items()
    ]

    after_state = {
        "total_approved": len(rows),
        "unique_triples": len(triple_counts),
        "pairs_at_or_above_50": pairs_at_or_above_50,
        "top_25_pairs": top_25,
        "orange_county_fl_premises_soft_tissue_n": orange_county_premises_soft_tissue,
        "all_triples": all_triples,
    }

    with AFTER_PATH.open("w", encoding="utf-8") as f:
        json.dump(after_state, f, indent=2, default=str)

    # Compute BEFORE -> AFTER diff
    before = load_before()
    diff = None
    if before is not None:
        before_triples = {
            (t["jurisdiction"], t["case_type"], t["injury"]): t["n"]
            for t in before.get("all_triples", [])
        }
        after_triples = {
            (t["jurisdiction"], t["case_type"], t["injury"]): t["n"]
            for t in after_state["all_triples"]
        }
        all_keys = set(before_triples.keys()) | set(after_triples.keys())

        # Newly populated cells: BEFORE n=0 -> AFTER n>=1
        new_cells = []
        # Removed cells: BEFORE n>=1 -> AFTER n=0
        removed_cells = []
        # Increased cells: BEFORE n>=1 AND AFTER > BEFORE
        increased_cells = []
        # Decreased cells: BEFORE n>=1 AND 1<=AFTER<BEFORE
        decreased_cells = []

        for k in all_keys:
            b = before_triples.get(k, 0)
            a = after_triples.get(k, 0)
            j, c, i = k
            entry = {"jurisdiction": j, "case_type": c, "injury": i, "before": b, "after": a}
            if b == 0 and a >= 1:
                new_cells.append(entry)
            elif b >= 1 and a == 0:
                removed_cells.append(entry)
            elif a > b > 0:
                increased_cells.append(entry)
            elif 0 < a < b:
                decreased_cells.append(entry)

        new_cells.sort(key=lambda x: -x["after"])
        removed_cells.sort(key=lambda x: -x["before"])
        increased_cells.sort(key=lambda x: -(x["after"] - x["before"]))
        decreased_cells.sort(key=lambda x: -(x["before"] - x["after"]))

        before_at_50 = before.get("pairs_at_or_above_50", [])
        after_at_50_keys = {(p["jurisdiction"], p["case_type"], p["injury"]) for p in pairs_at_or_above_50}
        before_at_50_keys = {(p["jurisdiction"], p["case_type"], p["injury"]) for p in before_at_50}

        new_pairs_at_50 = [p for p in pairs_at_or_above_50 if (p["jurisdiction"], p["case_type"], p["injury"]) not in before_at_50_keys]
        lost_pairs_at_50 = [p for p in before_at_50 if (p["jurisdiction"], p["case_type"], p["injury"]) not in after_at_50_keys]

        diff = {
            "before_total_approved": before.get("total_approved"),
            "after_total_approved": len(rows),
            "before_unique_triples": before.get("unique_triples"),
            "after_unique_triples": len(triple_counts),
            "newly_populated_cells_count": len(new_cells),
            "removed_cells_count": len(removed_cells),
            "increased_cells_count": len(increased_cells),
            "decreased_cells_count": len(decreased_cells),
            "before_pairs_at_n_geq_50": len(before_at_50),
            "after_pairs_at_n_geq_50": len(pairs_at_or_above_50),
            "new_pairs_at_n_geq_50": new_pairs_at_50,
            "lost_pairs_at_n_geq_50": lost_pairs_at_50,
            "newly_populated_cells_top_25": new_cells[:25],
            "increased_cells_top_25": increased_cells[:25],
            "removed_cells_top_25": removed_cells[:25],
            "decreased_cells_top_25": decreased_cells[:25],
            "orange_county_fl_premises_soft_tissue_before": before.get("orange_county_fl_premises_soft_tissue_n", 0),
            "orange_county_fl_premises_soft_tissue_after": orange_county_premises_soft_tissue,
        }
        with DIFF_PATH.open("w", encoding="utf-8") as f:
            json.dump(diff, f, indent=2, default=str)

    real_county_at_50 = len([
        p for p in pairs_at_or_above_50 if "Unknown" not in p["jurisdiction"]
    ])
    print(f"AFTER: total_approved={len(rows)} unique_triples={len(triple_counts)}")
    print(f"AFTER: pairs at n>=50 (all): {len(pairs_at_or_above_50)}")
    print(f"AFTER: real-county pairs at n>=50: {real_county_at_50}")
    print(f"AFTER: Orange County FL Premises Liability soft_tissue n={orange_county_premises_soft_tissue}")
    print(f"AFTER: Top 5:")
    for p in top_25[:5]:
        print(f"  n={p['n']:>4}  {p['jurisdiction']} | {p['case_type']} | {p['injury']}")

    if diff is not None:
        print()
        print(f"DIFF: newly_populated_cells={diff['newly_populated_cells_count']}")
        print(f"DIFF: removed_cells={diff['removed_cells_count']}")
        print(f"DIFF: increased_cells={diff['increased_cells_count']}")
        print(f"DIFF: decreased_cells={diff['decreased_cells_count']}")
        print(f"DIFF: pairs_at_n>=50 BEFORE={diff['before_pairs_at_n_geq_50']} AFTER={diff['after_pairs_at_n_geq_50']}")
        print(f"DIFF: new_pairs_at_n>=50={len(diff['new_pairs_at_n_geq_50'])}")
        print(f"DIFF: Orange County FL Premises Liability soft_tissue BEFORE={diff['orange_county_fl_premises_soft_tissue_before']} -> AFTER={diff['orange_county_fl_premises_soft_tissue_after']}")
        if diff["newly_populated_cells_top_25"]:
            print(f"DIFF: Top newly-populated cells:")
            for p in diff["newly_populated_cells_top_25"][:5]:
                print(f"  n={p['after']:>4}  {p['jurisdiction']} | {p['case_type']} | {p['injury']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
