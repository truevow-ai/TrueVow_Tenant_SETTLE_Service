"""
Stage 2.3b.1 probe — verify SettleContribution(**row) works against a real
ingested `settle_contributions` row.

Decision-tree outputs:
  - DIRECT: PASS            -> inline conversion in _query_comparable_cases
  - DIRECT: FAIL + FILTERED: PASS -> add _row_to_sc() helper (strip extras)
  - BOTH FAIL               -> add ConfigDict(extra='ignore') to SettleContribution
  - zero rows / db is None  -> investigate upstream (mock override, status filter)

Run from SETTLE service root:
    python scripts/_phase2x_b1_probe.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import traceback
from pathlib import Path

# -- path bootstrap --------------------------------------------------------
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _truncate(s: str, n: int = 500) -> str:
    return s if len(s) <= n else s[:n] + f"... [+{len(s) - n} more chars truncated]"


async def _amain() -> None:
    # -- imports happen AFTER sys.path setup -------------------------------
    from app.core.config import settings
    from app.core.database import get_db
    from app.models.case_bank import SettleContribution

    # -- force mock mode OFF for the probe ---------------------------------
    orig_use_mock = settings.USE_MOCK_DATA
    orig_settle_use_mock = settings.SETTLE_USE_MOCK_DATA
    print("=" * 72)
    print("STAGE 2.3b.1 PROBE — SettleContribution(**row) viability check")
    print("=" * 72)
    print(f"[boot] sys.path[0] = {sys.path[0]}")
    print(f"[boot] original USE_MOCK_DATA        = {orig_use_mock!r}")
    print(f"[boot] original SETTLE_USE_MOCK_DATA = {orig_settle_use_mock!r}")

    try:
        # Pydantic v2 Settings: direct attribute override works on the live instance.
        settings.USE_MOCK_DATA = False
        settings.SETTLE_USE_MOCK_DATA = False
        print(f"[boot] forced  USE_MOCK_DATA        = {settings.USE_MOCK_DATA!r}")
        print(f"[boot] forced  SETTLE_USE_MOCK_DATA = {settings.SETTLE_USE_MOCK_DATA!r}")
        print(f"[boot] settings.use_mock_data property = {settings.use_mock_data!r}")
        print()

        # -- get_db() and assert real client -------------------------------
        db = await get_db()
        print(f"[db]  type(db) = {type(db).__name__ if db is not None else 'NoneType'}")
        if db is None:
            print("[db]  FATAL: get_db() returned None. Check Supabase URL/service key in .env.local.")
            return
        print()

        # -- query 1 approved row ------------------------------------------
        print("[query] db.table('settle_contributions').select('*').eq('status','approved').limit(1).execute()")
        resp = (
            db.table("settle_contributions")
            .select("*")
            .eq("status", "approved")
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        print(f"[query] rows returned = {len(rows)}")

        if not rows:
            # Secondary diag: try with no status filter so we know whether rows exist at all.
            print("[diag]  no approved rows — re-running without status filter")
            resp2 = db.table("settle_contributions").select("*").limit(1).execute()
            rows2 = resp2.data or []
            print(f"[diag]  unfiltered rows returned = {len(rows2)}")
            if rows2:
                print(f"[diag]  sample row status value = {rows2[0].get('status')!r}")
                print(f"[diag]  sample row column count = {len(rows2[0])}")
            print("STOP: zero approved rows. Investigate status values / RLS / mock override.")
            return

        row = rows[0]
        print()
        print("-" * 72)
        print("COLUMN LIST (from DB row)")
        print("-" * 72)
        col_list = sorted(row.keys())
        print(f"count = {len(col_list)}")
        for c in col_list:
            v = row[c]
            vtype = type(v).__name__
            vrepr = _truncate(repr(v), 80)
            print(f"  {c:40s} :: {vtype:10s} = {vrepr}")

        # -- SettleContribution model fields -------------------------------
        model_fields = set(SettleContribution.model_fields.keys())
        print()
        print("-" * 72)
        print("SettleContribution.model_fields.keys()")
        print("-" * 72)
        for f in sorted(model_fields):
            print(f"  {f}")
        print(f"count = {len(model_fields)}")

        # -- diff sets ------------------------------------------------------
        row_keys = set(row.keys())
        extras = row_keys - model_fields
        missing = model_fields - row_keys
        print()
        print("-" * 72)
        print("DIFF (row vs model)")
        print("-" * 72)
        print(f"extras  (in row, NOT in model) count={len(extras)}: {sorted(extras)}")
        print(f"missing (in model, NOT in row) count={len(missing)}: {sorted(missing)}")

        # -- Attempt 1: direct --------------------------------------------
        print()
        print("-" * 72)
        print("ATTEMPT 1 — direct SettleContribution(**row)")
        print("-" * 72)
        direct_pass = False
        try:
            sc_direct = SettleContribution(**row)
            direct_pass = True
            print("DIRECT: PASS")
            dump = sc_direct.model_dump_json(indent=2)
            print(_truncate(dump, 500))
        except Exception as e:
            print(f"DIRECT: FAIL -- {type(e).__name__}: {e}")
            tb = traceback.format_exc()
            print("--- traceback (trimmed) ---")
            print(_truncate(tb, 1200))

        # -- Attempt 2: filtered (only if direct failed) -------------------
        if not direct_pass:
            print()
            print("-" * 72)
            print("ATTEMPT 2 — filtered SettleContribution(**{k:v for k,v in row.items() if k in model_fields})")
            print("-" * 72)
            filtered = {k: v for k, v in row.items() if k in model_fields}
            print(f"[filtered] kept {len(filtered)} of {len(row)} row keys")
            try:
                sc_filt = SettleContribution(**filtered)
                print("FILTERED: PASS")
                dump = sc_filt.model_dump_json(indent=2)
                print(_truncate(dump, 500))
            except Exception as e:
                print(f"FILTERED: FAIL -- {type(e).__name__}: {e}")
                tb = traceback.format_exc()
                print("--- traceback (trimmed) ---")
                print(_truncate(tb, 1200))
        else:
            print()
            print("[skip] ATTEMPT 2 not needed (direct passed)")

        print()
        print("=" * 72)
        print("PROBE COMPLETE")
        print("=" * 72)

    finally:
        # always restore mock-mode flags
        settings.USE_MOCK_DATA = orig_use_mock
        settings.SETTLE_USE_MOCK_DATA = orig_settle_use_mock
        print(f"[teardown] restored USE_MOCK_DATA        = {settings.USE_MOCK_DATA!r}")
        print(f"[teardown] restored SETTLE_USE_MOCK_DATA = {settings.SETTLE_USE_MOCK_DATA!r}")


if __name__ == "__main__":
    asyncio.run(_amain())
