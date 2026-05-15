"""Clear case_narrative for rows where it's set — used to retry probe with new quality logic."""
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.core.database import get_db


async def main() -> int:
    db = await get_db()
    if db is None:
        print("get_db() returned None")
        return 2
    # Pull all contributions and find populated case_narrative rows
    rows: list[dict] = []
    offset = 0
    while True:
        resp = (
            db.table("settle_contributions")
            .select("id, case_narrative")
            .order("id", desc=False)
            .limit(500)
            .offset(offset)
            .execute()
        )
        page = resp.data or []
        rows.extend(page)
        if len(page) < 500:
            break
        offset += 500
    populated = [r for r in rows if (r.get("case_narrative") or "").strip()]
    print(f"pre-clear populated: {len(populated)}")
    cleared = 0
    for r in populated:
        try:
            db.table("settle_contributions").update(
                {"case_narrative": None}
            ).eq("id", r["id"]).execute()
            cleared += 1
        except Exception as e:
            print(f"failed {r['id']}: {e}")
    print(f"cleared {cleared} rows")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
