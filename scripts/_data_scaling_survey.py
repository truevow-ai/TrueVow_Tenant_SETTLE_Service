"""Phase 1 — Data Scaling Survey (read-only intelligence gathering).

Maps the gap between today's state and production target. Identifies
cheapest wins before spending enrichment budget. Eight surveys:

  Q1: Total approved row count
  Q2: Total pending count + enrichment_status breakdown (via provenance)
  Q3: Pending pool top-20 (jurisdiction, case_type) pairs
  Q4: Approved pool top-20 (jurisdiction, case_type) pairs
  Q5: Cheap-win pairs — approved 30-49 rows + matching pending
  Q6: Row count by data source (provenance.created_by scrape tag)
  Q7: Average days-in-pending (stuck-pending detection)
  Q8: Cross-state spot check — non-FL jurisdictions

Read-only. No writes. No commits. Uses SupabaseRESTClient from
app.core.database. Self-tees stdout+stderr to logs/data_scaling_survey.log.
"""
from __future__ import annotations

import asyncio
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))


class _Tee:
    """Duplicate stdout/stderr to a log file (belt-and-suspenders against
    flaky PowerShell pipe/redirection capture)."""

    def __init__(self, *streams):
        self._streams = streams

    def write(self, data):
        for s in self._streams:
            try:
                s.write(data)
                s.flush()
            except Exception:
                pass

    def flush(self):
        for s in self._streams:
            try:
                s.flush()
            except Exception:
                pass


LOG_PATH = SERVICE_ROOT / "logs" / "data_scaling_survey.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
_log_fh = LOG_PATH.open("w", encoding="utf-8")
sys.stdout = _Tee(sys.__stdout__, _log_fh)
sys.stderr = _Tee(sys.__stderr__, _log_fh)

from app.core.config import settings  # noqa: E402
from app.core.database import get_db, reset_client  # noqa: E402


PAGE = 1000  # PostgREST default max per page


def hr(char="=", width=72):
    print(char * width)


def _paginate(db, table: str, select: str, filters: list[tuple[str, str, str]] | None = None,
              max_rows: int = 5000) -> list[dict]:
    """Pull rows with range pagination. Returns all rows up to max_rows.

    filters: list of (method_name, column, value) tuples, e.g. [("eq","status","pending")].
    """
    rows: list[dict] = []
    offset = 0
    while offset < max_rows:
        q = db.table(table).select(*select.split(","))
        if filters:
            for method, col, val in filters:
                q = getattr(q, method)(col, val)
        q = q.limit(PAGE).offset(offset)
        resp = q.execute()
        page = resp.data or []
        rows.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE
    return rows


def _count_exact(db, table: str, filters: list[tuple[str, str, str]] | None = None) -> int | None:
    """Get exact row count using Prefer: count=exact header."""
    q = db.table(table).select("id", count="exact")
    if filters:
        for method, col, val in filters:
            q = getattr(q, method)(col, val)
    q = q.limit(1)
    resp = q.execute()
    return resp.count


async def _boot():
    # Force real-DB path (survey is useless in mock mode)
    settings.USE_MOCK_DATA = False
    settings.SETTLE_USE_MOCK_DATA = False
    reset_client()
    return await get_db()


def main() -> int:
    hr()
    print("Phase 1 — Data Scaling Survey")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    hr()

    # ------------------------------------------------------------------
    # PRE-FLIGHT
    # ------------------------------------------------------------------
    print("\n[pre-flight] Verifying environment + client instantiation...")
    try:
        supa_url = settings.supabase_url
        supa_key = settings.supabase_service_key
    except Exception as e:
        print(f"[pre-flight] FATAL: settings load failed — {e}")
        return 10
    if not supa_url or not supa_key:
        print("[pre-flight] FATAL: supabase_url or supabase_service_key not set")
        print(f"          url present: {bool(supa_url)}, key present: {bool(supa_key)}")
        return 11
    print(f"[pre-flight] supabase_url scheme OK ({supa_url.split('://')[0]}://...{supa_url[-20:]})")
    print(f"[pre-flight] service key present (len={len(supa_key)})")

    db = asyncio.run(_boot())
    if db is None:
        print("[pre-flight] FATAL: get_db() returned None")
        return 12
    print(f"[pre-flight] db type = {type(db).__name__}")

    # 1-row smoke probe
    smoke = db.table("settle_contributions").select("id").limit(1).execute()
    if smoke.data is None:
        print("[pre-flight] FATAL: 1-row smoke query returned None (HTTP error in REST client)")
        return 13
    print(f"[pre-flight] 1-row smoke OK (got {len(smoke.data)} row)")

    # Provenance smoke
    prov_smoke = db.table("settle_case_provenance").select("contribution_id").limit(1).execute()
    if prov_smoke.data is None:
        print("[pre-flight] WARN: provenance smoke returned None (RLS or missing table)")
    else:
        print(f"[pre-flight] provenance smoke OK (got {len(prov_smoke.data)} row)")
    hr()

    # ------------------------------------------------------------------
    # Q1 — Total approved
    # ------------------------------------------------------------------
    print("\n[Q1] Total approved row count")
    n_approved = _count_exact(db, "settle_contributions", [("eq", "status", "approved")])
    print(f"     approved  = {n_approved}")
    n_pending = _count_exact(db, "settle_contributions", [("eq", "status", "pending")])
    n_rejected = _count_exact(db, "settle_contributions", [("eq", "status", "rejected")])
    n_flagged = _count_exact(db, "settle_contributions", [("eq", "status", "flagged")])
    print(f"     pending   = {n_pending}")
    print(f"     rejected  = {n_rejected}")
    print(f"     flagged   = {n_flagged}")
    n_total = (n_approved or 0) + (n_pending or 0) + (n_rejected or 0) + (n_flagged or 0)
    print(f"     TOTAL     = {n_total}")

    # ------------------------------------------------------------------
    # Q2 — Pending + enrichment_status breakdown
    # ------------------------------------------------------------------
    print("\n[Q2] Pending pool enrichment_status breakdown (via provenance)")
    # Pull all pending contribution ids
    pending_rows = _paginate(
        db, "settle_contributions", "id,created_at",
        [("eq", "status", "pending")], max_rows=5000,
    )
    print(f"     pulled {len(pending_rows)} pending contribution rows")
    pending_ids = {r.get("id") for r in pending_rows if r.get("id")}

    # Pull provenance rows in chunks of 50 ids (safe URL length)
    prov_status_by_id: dict[str, str | None] = {}
    ids_list = list(pending_ids)
    CHUNK = 50
    for i in range(0, len(ids_list), CHUNK):
        chunk = ids_list[i:i + CHUNK]
        q = db.table("settle_case_provenance").select("contribution_id,enrichment_status").in_(
            "contribution_id", chunk
        ).limit(PAGE)
        resp = q.execute()
        for r in (resp.data or []):
            prov_status_by_id[r.get("contribution_id")] = r.get("enrichment_status")

    covered = len(prov_status_by_id)
    uncovered = len(pending_ids) - covered
    enrich_counter = Counter(
        (prov_status_by_id.get(pid) or "NO_PROVENANCE_ROW") for pid in pending_ids
    )
    print(f"     provenance-covered: {covered}/{len(pending_ids)} "
          f"({uncovered} pending rows have NO provenance row)")
    print("     enrichment_status distribution on pending:")
    for status, n in enrich_counter.most_common():
        print(f"       {n:>5}  {status}")

    # ------------------------------------------------------------------
    # Q3 — Pending pool top-20 (jurisdiction, case_type)
    # ------------------------------------------------------------------
    print("\n[Q3] Pending pool top-20 (jurisdiction, case_type) pairs")
    pending_full = _paginate(
        db, "settle_contributions", "jurisdiction,case_type",
        [("eq", "status", "pending")], max_rows=5000,
    )
    pend_pairs = Counter(
        (r.get("jurisdiction"), r.get("case_type")) for r in pending_full
    )
    for (juris, ct), n in pend_pairs.most_common(20):
        print(f"     {n:>4}  {juris} | {ct}")
    print(f"     (unique pending pairs: {len(pend_pairs)})")

    # ------------------------------------------------------------------
    # Q4 — Approved pool top-20 (jurisdiction, case_type)
    # ------------------------------------------------------------------
    print("\n[Q4] Approved pool top-20 (jurisdiction, case_type) pairs")
    approved_full = _paginate(
        db, "settle_contributions", "jurisdiction,case_type",
        [("eq", "status", "approved")], max_rows=5000,
    )
    app_pairs = Counter(
        (r.get("jurisdiction"), r.get("case_type")) for r in approved_full
    )
    for (juris, ct), n in app_pairs.most_common(20):
        marker = "PASS" if n >= 50 else "fail"
        print(f"     [{marker}] {n:>4}  {juris} | {ct}")
    print(f"     (unique approved pairs: {len(app_pairs)})")
    pass_count = sum(1 for n in app_pairs.values() if n >= 50)
    print(f"     pairs that PASS the n>=50 gate: {pass_count}")

    # ------------------------------------------------------------------
    # Q5 — Cheap wins (approved 30-49 + pending supply)
    # ------------------------------------------------------------------
    print("\n[Q5] CHEAP WINS: approved pairs in range 30-49 + pending supply")
    close_pairs = [(pair, n) for pair, n in app_pairs.items() if 30 <= n <= 49]
    close_pairs.sort(key=lambda x: -x[1])
    if not close_pairs:
        print("     (no pairs in the 30-49 approved range)")
    else:
        print(f"     {'needed':>7}  {'appr':>4}  {'pend':>5}  pair")
        for pair, n in close_pairs[:15]:
            pend_avail = pend_pairs.get(pair, 0)
            need = 50 - n
            print(f"     {need:>7}  {n:>4}  {pend_avail:>5}  {pair[0]} | {pair[1]}")

    # Medium-effort: 20-29 approved
    print("\n[Q5b] MEDIUM EFFORT: approved pairs 20-29 + pending supply")
    med_pairs = [(pair, n) for pair, n in app_pairs.items() if 20 <= n <= 29]
    med_pairs.sort(key=lambda x: -x[1])
    if not med_pairs:
        print("     (no pairs in the 20-29 approved range)")
    else:
        for pair, n in med_pairs[:10]:
            pend_avail = pend_pairs.get(pair, 0)
            need = 50 - n
            print(f"     need={need:<3} appr={n:<3} pend={pend_avail:<3}  {pair[0]} | {pair[1]}")

    # Hard: 0-2 approved but top-pending
    print("\n[Q5c] HARD CASES: pairs with 0-2 approved but high pending")
    hard_candidates = [
        (pair, pend_pairs[pair])
        for pair in pend_pairs
        if app_pairs.get(pair, 0) <= 2 and pend_pairs[pair] >= 10
    ]
    hard_candidates.sort(key=lambda x: -x[1])
    if not hard_candidates:
        print("     (no high-pending/low-approved pairs found)")
    else:
        for pair, pend_n in hard_candidates[:10]:
            app_n = app_pairs.get(pair, 0)
            print(f"     appr={app_n:<2} pend={pend_n:<4}  {pair[0]} | {pair[1]}")

    # ------------------------------------------------------------------
    # Q6 — Row count by data source (provenance.created_by)
    # ------------------------------------------------------------------
    print("\n[Q6] Row count by data source (provenance.created_by scrape tag)")
    prov_all = _paginate(
        db, "settle_case_provenance", "created_by,enrichment_status",
        None, max_rows=10000,
    )
    print(f"     pulled {len(prov_all)} provenance rows total")
    src_counter = Counter(r.get("created_by") or "(null)" for r in prov_all)
    print("     top-15 scrape sources:")
    for src, n in src_counter.most_common(15):
        print(f"       {n:>5}  {src}")
    print(f"     (unique scrape tags: {len(src_counter)})")

    # Enrichment status across ALL provenance rows
    print("\n     enrichment_status across ALL provenance rows:")
    all_enrich = Counter(r.get("enrichment_status") or "(null)" for r in prov_all)
    for status, n in all_enrich.most_common():
        print(f"       {n:>5}  {status}")

    # ------------------------------------------------------------------
    # Q7 — Average days in pending
    # ------------------------------------------------------------------
    print("\n[Q7] Average days-in-pending (stuck-pending detection)")
    now = datetime.now(timezone.utc)
    ages_days: list[float] = []
    for r in pending_rows:
        ts = r.get("created_at")
        if not ts:
            continue
        try:
            # Supabase returns ISO-8601 with 'Z' or '+00:00'
            ts_clean = ts.replace("Z", "+00:00") if ts.endswith("Z") else ts
            dt = datetime.fromisoformat(ts_clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_d = (now - dt).total_seconds() / 86400.0
            ages_days.append(age_d)
        except Exception:
            continue
    if ages_days:
        ages_days.sort()
        avg = sum(ages_days) / len(ages_days)
        median = ages_days[len(ages_days) // 2]
        p90 = ages_days[int(len(ages_days) * 0.9)] if len(ages_days) > 10 else ages_days[-1]
        oldest = ages_days[-1]
        over_30 = sum(1 for a in ages_days if a > 30)
        over_60 = sum(1 for a in ages_days if a > 60)
        print(f"     n={len(ages_days)}  avg={avg:.1f}d  median={median:.1f}d  "
              f"p90={p90:.1f}d  oldest={oldest:.1f}d")
        print(f"     pending > 30 days: {over_30}    pending > 60 days: {over_60}")
    else:
        print("     (no parseable created_at on pending rows)")

    # ------------------------------------------------------------------
    # Q8 — Cross-state spot check
    # ------------------------------------------------------------------
    print("\n[Q8] Cross-state spot check (approved + pending)")
    all_juris_approved = Counter(r.get("jurisdiction") for r in approved_full)
    all_juris_pending = Counter(r.get("jurisdiction") for r in pending_full)
    all_jurises = set(all_juris_approved) | set(all_juris_pending)
    print(f"     unique jurisdictions seen: {len(all_jurises)}")
    print(f"     {'juris':<20} {'appr':>5} {'pend':>5}")
    union = sorted(
        all_jurises,
        key=lambda j: -(all_juris_approved.get(j, 0) + all_juris_pending.get(j, 0)),
    )
    for j in union[:20]:
        a = all_juris_approved.get(j, 0)
        p = all_juris_pending.get(j, 0)
        print(f"     {str(j):<20} {a:>5} {p:>5}")
    non_fl = [j for j in all_jurises if j and "FL" not in str(j).upper()
              and "FLORIDA" not in str(j).upper()]
    print(f"     non-FL-looking jurisdictions: {len(non_fl)}")
    if non_fl:
        print(f"     sample: {non_fl[:10]}")

    # ------------------------------------------------------------------
    # FINAL VERDICT BLOCK
    # ------------------------------------------------------------------
    hr()
    print("SURVEY COMPLETE")
    print(f"Finished: {datetime.now(timezone.utc).isoformat()}")
    print(f"Log: {LOG_PATH}")
    hr()
    return 0


if __name__ == "__main__":
    sys.exit(main())
