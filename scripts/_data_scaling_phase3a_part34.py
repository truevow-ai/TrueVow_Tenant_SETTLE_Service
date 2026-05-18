"""Phase 3a — Part 3 (CL disambiguation re-run) + Part 4 (enumeration + verdict).

Runs against the now-populated case_name field from Part 2A (which DB confirmed
successful, 202/204 case_names recovered). The original combined script crashed
silently after Part 2B; this is a focused completion script.

Strategy:
  - For each of the ~204 Unknown-County rows, query CourtListener:
    (1) by docket_number (high confidence)
    (2) by case_name (medium confidence)
  - Map CL court_id -> Florida county via FL_CIRCUIT_TO_COUNTIES + CL_COURT_TO_COUNTY.
  - Halt updates if (high+medium) match rate < 30% per architect directive.
  - Apply jurisdiction updates only on high/medium confidence.
  - Re-run enumeration: real-county (jurisdiction, case_type) pairs at n>=50.
  - Verdict: GREEN (>=3) / YELLOW (1-2) / RED (0).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx

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


LOG = SERVICE_ROOT / "logs" / "phase3a_part34.log"
LOG.parent.mkdir(parents=True, exist_ok=True)
_fh = LOG.open("w", encoding="utf-8")
sys.stdout = _Tee(sys.__stdout__, _fh)
sys.stderr = _Tee(sys.__stderr__, _fh)

from app.core.config import settings  # noqa: E402
from app.core.database import get_db, reset_client  # noqa: E402


PAGE = 1000

FL_CIRCUIT_TO_COUNTIES: dict[int, list[str]] = {
    1: ["Escambia", "Santa Rosa", "Okaloosa", "Walton"],
    2: ["Franklin", "Gadsden", "Jefferson", "Leon", "Liberty", "Wakulla"],
    3: ["Columbia", "Dixie", "Hamilton", "Lafayette", "Madison", "Suwannee", "Taylor"],
    4: ["Clay", "Duval", "Nassau"],
    5: ["Citrus", "Hernando", "Lake", "Marion", "Sumter"],
    6: ["Pasco", "Pinellas"],
    7: ["Flagler", "Putnam", "St. Johns", "Volusia"],
    8: ["Alachua", "Baker", "Bradford", "Gilchrist", "Levy", "Union"],
    9: ["Orange", "Osceola"],
    10: ["Hardee", "Highlands", "Polk"],
    11: ["Miami-Dade"],
    12: ["DeSoto", "Manatee", "Sarasota"],
    13: ["Hillsborough"],
    14: ["Bay", "Calhoun", "Gulf", "Holmes", "Jackson", "Washington"],
    15: ["Palm Beach"],
    16: ["Monroe"],
    17: ["Broward"],
    18: ["Brevard", "Seminole"],
    19: ["Indian River", "Martin", "Okeechobee", "St. Lucie"],
    20: ["Charlotte", "Collier", "Glades", "Hendry", "Lee"],
}
CL_COURT_TO_COUNTY: dict[str, str] = {
    "flmd": "Orange", "flnd": "Leon", "flsd": "Miami-Dade",
    "flacir11": "Miami-Dade", "flacir13": "Hillsborough",
    "flacir15": "Palm Beach", "flacir16": "Monroe", "flacir17": "Broward",
}
CIRCUIT_ID_RE = re.compile(r"flacir(\d+)$|fla(\d+)cir$", re.I)

HEADERS = {"User-Agent": "TrueVow-SETTLE-DataScaling/1.0"}


async def _boot():
    settings.USE_MOCK_DATA = False
    settings.SETTLE_USE_MOCK_DATA = False
    reset_client()
    return await get_db()


def _paginate(db, table, select, filters=None, max_rows=10000):
    rows, offset = [], 0
    while offset < max_rows:
        q = db.table(table).select(*select.split(","))
        if filters:
            for m, c, v in filters:
                q = getattr(q, m)(c, v)
        q = q.limit(PAGE).offset(offset)
        r = q.execute()
        page = r.data or []
        rows.extend(page)
        if len(page) < PAGE:
            break
        offset += PAGE
    return rows


def _fetch_prov(db, ids: list[str]) -> dict[str, dict]:
    out = {}
    CHUNK = 50
    for i in range(0, len(ids), CHUNK):
        chunk = ids[i:i + CHUNK]
        q = db.table("settle_case_provenance").select(
            "contribution_id,case_name,case_citation,docket_number"
        ).in_("contribution_id", chunk).limit(PAGE)
        r = q.execute()
        for row in r.data or []:
            out[row["contribution_id"]] = row
    return out


class CLClient:
    BASE = "https://www.courtlistener.com/api/rest/v4"

    def __init__(self, token: str | None):
        h = dict(HEADERS)
        if token:
            h["Authorization"] = f"Token {token}"
        self.client = httpx.Client(timeout=20.0, headers=h)
        self.sleep = 0.25 if token else 6.0
        self.last = 0.0
        self.calls = 0
        self.errs = 0
        self.throttles = 0

    def _pace(self):
        dt = time.time() - self.last
        if dt < self.sleep:
            time.sleep(self.sleep - dt)
        self.last = time.time()

    def search_dockets(self, docket: str) -> list[dict]:
        if not docket: return []
        self._pace(); self.calls += 1
        try:
            r = self.client.get(f"{self.BASE}/dockets/", params={"docket_number": docket, "page_size": 5})
            if r.status_code == 429:
                self.throttles += 1; time.sleep(10); return []
            if r.status_code >= 400:
                self.errs += 1; return []
            return (r.json().get("results", []) or [])
        except Exception as e:
            self.errs += 1; print(f"      [CL ERR docket] {e}"); return []

    def search_opinions(self, name: str) -> list[dict]:
        if not name: return []
        q = name.strip()[:120]
        self._pace(); self.calls += 1
        try:
            r = self.client.get(f"{self.BASE}/search/", params={"q": q, "type": "o", "page_size": 5})
            if r.status_code == 429:
                self.throttles += 1; time.sleep(10); return []
            if r.status_code >= 400:
                self.errs += 1; return []
            return (r.json().get("results", []) or [])
        except Exception as e:
            self.errs += 1; print(f"      [CL ERR opinions] {e}"); return []

    def close(self):
        try: self.client.close()
        except Exception: pass


def _county_from_cl(court_id: str | None) -> str | None:
    if not court_id: return None
    cid = court_id.lower().strip()
    if cid in CL_COURT_TO_COUNTY:
        return CL_COURT_TO_COUNTY[cid]
    m = CIRCUIT_ID_RE.search(cid)
    if m:
        n = int(m.group(1) or m.group(2))
        cs = FL_CIRCUIT_TO_COUNTIES.get(n)
        if cs and len(cs) == 1:
            return cs[0]
    return None


def _format_juris(county: str) -> str:
    return f"{county} County, FL"


def _load_cl_token() -> str | None:
    env_path = SERVICE_ROOT / ".env.local"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        if k.strip() == "COURTLISTENER_API_TOKEN":
            return v.strip()
    return None


def main() -> int:
    print("=" * 72)
    print("Phase 3a — Part 3 (CL re-disambig) + Part 4 (enumeration verdict)")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 72)

    db = asyncio.run(_boot())

    # --- Pre-flight: confirm Part 2A state still in place
    print("\n[PRE-FLIGHT]")
    total_approved = db.table("settle_contributions").select("id", count="exact").eq("status", "approved").execute().count
    unknown_approved = db.table("settle_contributions").select("id", count="exact").eq("status", "approved").eq("jurisdiction", "FL (Unknown County)").execute().count
    case_name_count = db.table("settle_case_provenance").select("contribution_id", count="exact").not_.is_("case_name", "null").execute().count
    print(f"  approved total: {total_approved}")
    print(f"  approved Unknown-County: {unknown_approved}")
    print(f"  provenance with case_name: {case_name_count}")
    if case_name_count < 100:
        print(f"  [HALT] case_name population insufficient")
        return 2

    # --- PART 3: re-disambiguation
    print("\n[PART 3] Re-run CourtListener disambiguation")
    print("-" * 72)
    unknown_rows = _paginate(
        db, "settle_contributions", "id,jurisdiction,case_type",
        filters=[("eq", "jurisdiction", "FL (Unknown County)")],
    )
    print(f"  Unknown-County rows fetched: {len(unknown_rows)}")
    ids = [r["id"] for r in unknown_rows if r.get("id")]
    prov_by_id = _fetch_prov(db, ids)
    print(f"  Provenance rows loaded:      {len(prov_by_id)}")

    cl_token = _load_cl_token()
    print(f"  CL token: {'present (5000/hr)' if cl_token else 'absent'}")
    cl = CLClient(cl_token)

    resolutions: list[dict] = []
    res_start = time.time()
    SOFT_CAP_SEC = 60 * 25

    for i, row in enumerate(unknown_rows, 1):
        if time.time() - res_start > SOFT_CAP_SEC:
            print(f"  [HALT] {SOFT_CAP_SEC}s disambig cap reached at i={i}")
            break
        cid = row.get("id")
        prov = prov_by_id.get(cid) or {}
        res = {
            "contribution_id": cid, "resolved_county": None,
            "resolved_jurisdiction": None, "confidence": "none",
            "method": "none", "cl_docket_id": None, "notes": "",
        }
        docket = (prov.get("docket_number") or "").strip()
        case_name = (prov.get("case_name") or prov.get("case_citation") or "").strip()

        # Strategy 1: docket lookup
        if docket:
            for h in cl.search_dockets(docket):
                court = h.get("court_id") or h.get("court")
                if isinstance(court, str) and court.startswith("http"):
                    court = court.rstrip("/").rsplit("/", 1)[-1]
                if not court or not str(court).lower().startswith(("fl", "fla")):
                    continue
                co = _county_from_cl(court)
                if co:
                    res.update(resolved_county=co, resolved_jurisdiction=_format_juris(co),
                               confidence="high", method="cl_docket",
                               cl_docket_id=str(h.get("id") or ""),
                               notes=f"court_id={court}")
                    break

        # Strategy 2: case-name lookup
        if case_name and not res["resolved_county"]:
            for h in cl.search_opinions(case_name):
                court = h.get("court_id") or h.get("court")
                if isinstance(court, str) and court.startswith("http"):
                    court = court.rstrip("/").rsplit("/", 1)[-1]
                if not court or not str(court).lower().startswith(("fl", "fla")):
                    continue
                co = _county_from_cl(court)
                if co:
                    res.update(resolved_county=co, resolved_jurisdiction=_format_juris(co),
                               confidence="medium", method="cl_name",
                               cl_docket_id=str(h.get("docket_id") or h.get("id") or ""),
                               notes=f"court_id={court}")
                    break

        resolutions.append(res)
        if i % 25 == 0 or i == len(unknown_rows):
            matched = sum(1 for x in resolutions if x["resolved_county"])
            print(f"    [{i}/{len(unknown_rows)}] matched={matched} cl_calls={cl.calls} "
                  f"errs={cl.errs} throttles={cl.throttles} "
                  f"elapsed={time.time()-res_start:.0f}s")
    cl.close()

    matched = [r for r in resolutions if r["resolved_county"]]
    by_method = Counter(r["method"] for r in matched)
    by_conf = Counter(r["confidence"] for r in matched)
    by_county = Counter(r["resolved_county"] for r in matched)
    match_rate = 100 * len(matched) / max(1, len(resolutions))
    cl_only = sum(1 for r in matched if r["method"] in ("cl_docket", "cl_name"))
    cl_only_rate = 100 * cl_only / max(1, len(resolutions))

    print(f"\n  Disambiguation results:")
    print(f"    Total queried:      {len(resolutions)}")
    print(f"    Matched (any):      {len(matched)} ({match_rate:.1f}%)")
    print(f"    CL-only matches:    {cl_only} ({cl_only_rate:.1f}%)")
    print(f"    By method:          {dict(by_method)}")
    print(f"    By confidence:      {dict(by_conf)}")
    print(f"    By county (top 15): {dict(by_county.most_common(15))}")
    print(f"    CL calls:           {cl.calls}")
    print(f"    CL errors:          {cl.errs}")
    print(f"    CL throttles:       {cl.throttles}")

    # Architect surface-back: <30% halt updates
    apply_updates = cl_only_rate >= 30
    if not apply_updates:
        print(f"\n  [SURFACE] CL-only match rate {cl_only_rate:.1f}% < 30% threshold")
        print(f"  Per architect directive: halt updates and surface back.")
    else:
        print(f"  [OK] CL-only match rate {cl_only_rate:.1f}% >= 30%; applying updates")

    updates_ok = updates_fail = 0
    if apply_updates:
        applicable = [r for r in matched if r["confidence"] in ("high", "medium")]
        print(f"\n  Applying jurisdiction updates ({len(applicable)} rows)...")
        for i, res in enumerate(applicable, 1):
            try:
                rr = db.table("settle_contributions").update(
                    {"jurisdiction": res["resolved_jurisdiction"]}
                ).eq("id", res["contribution_id"]).execute()
                if rr.data:
                    updates_ok += 1
                else:
                    updates_fail += 1
            except Exception as e:
                updates_fail += 1
                print(f"    [ERR] update {res['contribution_id']}: {e}")
            if i % 20 == 0:
                time.sleep(1.0)
        print(f"  jurisdiction updates: ok={updates_ok} fail={updates_fail}")

        # Provenance bump
        prov_ok = prov_fail = 0
        for res in applicable:
            patch = {"enrichment_status": "cl_enriched", "match_confidence": res["confidence"]}
            if res.get("cl_docket_id"):
                patch["cl_docket_id"] = res["cl_docket_id"]
            try:
                rr = db.table("settle_case_provenance").update(patch).eq("contribution_id", res["contribution_id"]).execute()
                if rr.data:
                    prov_ok += 1
                else:
                    prov_fail += 1
            except Exception as e:
                prov_fail += 1
        print(f"  provenance bumps: ok={prov_ok} fail={prov_fail}")

    # ------------------------------------------------------------------
    # PART 4 — Enumeration + verdict
    # ------------------------------------------------------------------
    print("\n[PART 4] Enumeration probe + verdict")
    print("-" * 72)
    approved = _paginate(
        db, "settle_contributions", "id,jurisdiction,case_type",
        filters=[("eq", "status", "approved")],
    )
    pair_counts = Counter()
    for r in approved:
        j = (r.get("jurisdiction") or "").strip()
        ct = (r.get("case_type") or "").strip()
        if not j or not ct:
            continue
        pair_counts[(j, ct)] += 1

    real_county_pairs = [
        (k, n) for k, n in pair_counts.items()
        if k[0] != "FL (Unknown County)" and "County" in k[0] and n >= 50
    ]
    real_county_pairs.sort(key=lambda x: -x[1])
    sentinel_pairs = [(k, n) for k, n in pair_counts.items() if k[0] == "FL (Unknown County)" and n >= 50]

    top_pairs = pair_counts.most_common(10)
    print(f"  Total approved rows scanned: {len(approved)}")
    print(f"  Total (jurisdiction, case_type) pairs: {len(pair_counts)}")
    print(f"  Top 10 pairs by count:")
    for (j, ct), n in top_pairs:
        marker = " [SENTINEL]" if j == "FL (Unknown County)" else " [REAL]" if "County" in j else ""
        print(f"    n={n:4d}  ({j}, {ct}){marker}")

    print(f"\n  Real-county pairs at n>=50: {len(real_county_pairs)}")
    for (j, ct), n in real_county_pairs:
        print(f"    n={n:4d}  ({j}, {ct})")
    print(f"  Sentinel pairs at n>=50: {len(sentinel_pairs)}")
    for (j, ct), n in sentinel_pairs:
        print(f"    n={n:4d}  ({j}, {ct})")

    if len(real_county_pairs) >= 3:
        verdict = "GREEN"
    elif len(real_county_pairs) >= 1:
        verdict = "YELLOW"
    else:
        verdict = "RED"

    print(f"\n========================================================================")
    print(f"  VERDICT: {verdict}")
    print(f"  real-county pairs n>=50: {len(real_county_pairs)}  sentinel n>=50: {len(sentinel_pairs)}")
    print(f"========================================================================")

    # Summary file
    summary = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "part3": {
            "queried": len(resolutions),
            "matched_total": len(matched),
            "matched_cl_only": cl_only,
            "match_rate_pct": round(match_rate, 1),
            "cl_only_rate_pct": round(cl_only_rate, 1),
            "by_method": dict(by_method),
            "by_confidence": dict(by_conf),
            "by_county": dict(by_county.most_common(20)),
            "cl_calls": cl.calls,
            "cl_errors": cl.errs,
            "cl_throttles": cl.throttles,
            "applied_updates": apply_updates,
            "jurisdiction_updates_ok": updates_ok,
            "jurisdiction_updates_fail": updates_fail,
        },
        "part4": {
            "total_approved": len(approved),
            "total_pairs": len(pair_counts),
            "real_county_pairs_n_gte_50": len(real_county_pairs),
            "sentinel_pairs_n_gte_50": len(sentinel_pairs),
            "top_10_pairs": [{"jurisdiction": j, "case_type": ct, "n": n} for (j, ct), n in top_pairs],
            "real_county_pairs": [{"jurisdiction": j, "case_type": ct, "n": n} for (j, ct), n in real_county_pairs],
        },
    }
    out = SERVICE_ROOT / "logs" / "phase3a_summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n  Summary written: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
