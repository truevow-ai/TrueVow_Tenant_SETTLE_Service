"""Phase 3a Part 1 — Revert the 10 low-confidence url-hint updates from the
Phase 2 disambiguation pass.

Identification strategy (defense-in-depth):
  filter A: jurisdiction != 'FL (Unknown County)' AND jurisdiction starts
            with one of the 6 url_hint counties (Lee/Brevard/Hillsborough/
            Duval/Broward/Escambia) — those are the only counties any
            url_hint match could have produced.
  filter B: updated_at >= 2026-05-13T04:24:00Z (run start floor; diagnostic
            was read-only so no other writes are in this window).

Apply intersection. Expected count: exactly 10 rows. Halt if !=10.

Then UPDATE settle_contributions SET jurisdiction='FL (Unknown County)'
WHERE id IN (...) — batched with 1s pause. Verify with SELECT.
"""
from __future__ import annotations

import asyncio
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))


class _Tee:
    def __init__(self, *s): self._s = s
    def write(self, d):
        for x in self._s:
            try: x.write(d); x.flush()
            except Exception: pass
    def flush(self):
        for x in self._s:
            try: x.flush()
            except Exception: pass


LOG = SERVICE_ROOT / "logs" / "disambiguate_revert.log"
LOG.parent.mkdir(parents=True, exist_ok=True)
_fh = LOG.open("w", encoding="utf-8")
sys.stdout = _Tee(sys.__stdout__, _fh)
sys.stderr = _Tee(sys.__stderr__, _fh)

from app.core.config import settings  # noqa: E402
from app.core.database import get_db, reset_client  # noqa: E402


# Url-hint county set — exactly the 6 counties a url_hint match produced.
URL_HINT_COUNTIES = {
    "Lee County, FL", "Brevard County, FL", "Hillsborough County, FL",
    "Duval County, FL", "Broward County, FL", "Escambia County, FL",
}

# Run-time window floor: disambiguate started 2026-05-13T04:24:00Z. Use a
# 1-minute floor (well before run start) to avoid clock-skew misses.
WINDOW_FLOOR = "2026-05-13T04:23:00Z"


async def _boot():
    settings.USE_MOCK_DATA = False
    settings.SETTLE_USE_MOCK_DATA = False
    reset_client()
    return await get_db()


def main() -> int:
    print("=" * 72)
    print("Phase 3a — Part 1 — Revert url-hint updates")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 72)

    db = asyncio.run(_boot())

    # Pull all post-floor non-Unknown rows, narrow to the 6 url-hint counties
    print("\n[STEP 1] Identifying candidate rows...")
    candidates = []
    offset = 0
    while True:
        q = (
            db.table("settle_contributions")
            .select("id,jurisdiction,status,updated_at")
            .gte("updated_at", WINDOW_FLOOR)
            .limit(1000)
            .offset(offset)
        )
        r = q.execute()
        page = r.data or []
        candidates.extend(page)
        if len(page) < 1000:
            break
        offset += 1000
    print(f"  Rows with updated_at >= {WINDOW_FLOOR}: {len(candidates)}")

    targets = [
        r for r in candidates
        if (r.get("jurisdiction") in URL_HINT_COUNTIES)
    ]
    print(f"  Filtered to url-hint counties: {len(targets)}")
    by_county = Counter(r["jurisdiction"] for r in targets)
    print(f"  By county: {dict(by_county)}")

    # Expected distribution from disambiguate_summary.json:
    expected = {
        "Lee County, FL": 2,
        "Brevard County, FL": 2,
        "Hillsborough County, FL": 2,
        "Duval County, FL": 2,
        "Broward County, FL": 1,
        "Escambia County, FL": 1,
    }
    expected_total = sum(expected.values())
    print(f"  Expected total: {expected_total} (per disambiguate_summary.json)")

    if len(targets) != expected_total:
        print(
            f"  [HALT] target count {len(targets)} != expected {expected_total}. "
            "Aborting revert; manual review needed."
        )
        return 2

    if dict(by_county) != expected:
        print(
            f"  [HALT] target distribution {dict(by_county)} != expected {expected}. "
            "Aborting revert."
        )
        return 3

    print("  [OK] Distribution matches Phase 2 url-hint output exactly.")

    # Print the 10 IDs we're about to revert
    print("\n[STEP 2] Targets:")
    for r in targets:
        print(f"  {r['id']}  {r['jurisdiction']}  status={r['status']}  updated_at={r['updated_at']}")

    # Apply revert
    print("\n[STEP 3] Reverting jurisdiction -> 'FL (Unknown County)' (1s/row pause)...")
    ok = 0
    fail = 0
    for r in targets:
        cid = r["id"]
        try:
            resp = (
                db.table("settle_contributions")
                .update({"jurisdiction": "FL (Unknown County)"})
                .eq("id", cid)
                .execute()
            )
            if resp.data:
                ok += 1
                print(f"  [OK]   {cid}  {r['jurisdiction']} -> FL (Unknown County)")
            else:
                fail += 1
                print(f"  [FAIL] {cid}  no data returned")
        except Exception as e:
            fail += 1
            print(f"  [ERR]  {cid}: {e}")
        time.sleep(1.0)
    print(f"  Total: ok={ok} fail={fail}")

    # Verify
    print("\n[STEP 4] Verifying...")
    verify_ids = [r["id"] for r in targets]
    CHUNK = 50
    seen = []
    for i in range(0, len(verify_ids), CHUNK):
        chunk = verify_ids[i:i + CHUNK]
        q = db.table("settle_contributions").select("id,jurisdiction").in_("id", chunk).limit(1000)
        r = q.execute()
        seen.extend(r.data or [])
    by_juris = Counter(s.get("jurisdiction") for s in seen)
    print(f"  Verified jurisdictions: {dict(by_juris)}")
    if by_juris.get("FL (Unknown County)") == len(targets):
        print("  [PASS] All targets are now 'FL (Unknown County)'.")
    else:
        print("  [WARN] Some targets did NOT revert. Manual inspection required.")
        return 4

    # Final state check: total Unknown-County approved count
    print("\n[STEP 5] Post-revert Unknown-County approved count...")
    cnt = (
        db.table("settle_contributions").select("id", count="exact")
        .eq("jurisdiction", "FL (Unknown County)").eq("status", "approved")
        .limit(1).execute().count
    )
    print(f"  Approved 'FL (Unknown County)' rows: {cnt}")

    print("\n" + "=" * 72)
    print(f"Finished: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
