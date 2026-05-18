"""Diagnostic: what provenance fields are actually populated for the
Unknown-County pool? Explains why CL had nothing to query with."""
from __future__ import annotations

import asyncio
import sys
from collections import Counter
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


LOG = SERVICE_ROOT / "logs" / "disambiguate_diag.log"
LOG.parent.mkdir(parents=True, exist_ok=True)
_fh = LOG.open("w", encoding="utf-8")
sys.stdout = _Tee(sys.__stdout__, _fh)
sys.stderr = _Tee(sys.__stderr__, _fh)

from app.core.config import settings  # noqa: E402
from app.core.database import get_db, reset_client  # noqa: E402


async def _boot():
    settings.USE_MOCK_DATA = False
    settings.SETTLE_USE_MOCK_DATA = False
    reset_client()
    return await get_db()


def main():
    db = asyncio.run(_boot())

    # Pull Unknown-County contributions (pending + approved, post-update state)
    unknown = []
    offset = 0
    while True:
        q = (
            db.table("settle_contributions")
            .select("id,jurisdiction,status")
            .eq("jurisdiction", "FL (Unknown County)")
            .limit(1000)
            .offset(offset)
        )
        r = q.execute()
        page = r.data or []
        unknown.extend(page)
        if len(page) < 1000:
            break
        offset += 1000
    print(f"Unknown-County rows (current, post-update): {len(unknown)}")

    ids = [r["id"] for r in unknown]
    prov_rows = []
    CHUNK = 50
    for i in range(0, len(ids), CHUNK):
        chunk = ids[i:i + CHUNK]
        q = db.table("settle_case_provenance").select(
            "contribution_id,case_name,case_citation,docket_number,"
            "judge_name,source_url,news_provenance,cl_docket_id,"
            "enrichment_status,match_confidence"
        ).in_("contribution_id", chunk).limit(1000)
        r = q.execute()
        prov_rows.extend(r.data or [])

    print(f"Provenance rows fetched: {len(prov_rows)}")
    print()

    fields = [
        "case_name", "case_citation", "docket_number",
        "judge_name", "source_url", "news_provenance", "cl_docket_id",
    ]
    for f in fields:
        non_null = sum(1 for p in prov_rows if p.get(f))
        non_empty = sum(1 for p in prov_rows if p.get(f) and str(p.get(f)).strip())
        print(f"  {f:<20} non_null={non_null:>4}  non_empty={non_empty:>4}  "
              f"({100*non_empty/max(1,len(prov_rows)):.1f}%)")

    # What's in news_provenance that DOES have a value? Sample 10 URLs.
    print("\nSample news_provenance URLs (first 10 non-empty):")
    n = 0
    for p in prov_rows:
        url = p.get("news_provenance")
        if url and n < 10:
            print(f"  {url[:140]}")
            n += 1

    print("\nSample source_url (first 10 non-empty):")
    n = 0
    for p in prov_rows:
        url = p.get("source_url")
        if url and n < 10:
            print(f"  {url[:140]}")
            n += 1

    print("\nSample case_name (first 10 non-empty):")
    n = 0
    for p in prov_rows:
        name = p.get("case_name")
        if name and n < 10:
            print(f"  {name[:140]}")
            n += 1

    print("\nSample docket_number (first 10 non-empty):")
    n = 0
    for p in prov_rows:
        d = p.get("docket_number")
        if d and n < 10:
            print(f"  {d}")
            n += 1

    # Status of recently-updated rows (Lee, Brevard, Hillsborough, Duval...)
    print("\nPost-update jurisdiction distribution (all settle_contributions):")
    offset = 0
    all_rows = []
    while True:
        q = db.table("settle_contributions").select("jurisdiction,status").limit(1000).offset(offset)
        r = q.execute()
        page = r.data or []
        all_rows.extend(page)
        if len(page) < 1000:
            break
        offset += 1000
    juris_approved = Counter(r.get("jurisdiction") for r in all_rows if r.get("status") == "approved")
    for j, n in juris_approved.most_common(20):
        print(f"  {n:>4}  {j}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
