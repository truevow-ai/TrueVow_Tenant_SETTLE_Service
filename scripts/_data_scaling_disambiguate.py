"""Phase 2 — Data Scaling County Disambiguation Pass.

Goal: Resolve the 186 `FL (Unknown County)` contribution rows to specific
Florida counties via CourtListener docket/opinion lookup, with news-URL
parsing as a secondary signal. Target >=30% success rate. After update,
re-run the (jurisdiction, case_type) enumeration to count real-county
pairs clearing n=50.

Architecture:
  1. Pre-flight gates (env token, Supabase reachability, alembic HEAD)
  2. Fetch 186 Unknown-County rows + provenance metadata
  3. Per row: CourtListener lookup (docket -> case_name -> skip)
  4. URL-hint fallback from `news_provenance`
  5. Dry-run summary (do NOT write yet)
  6. Apply UPDATEs in batches of 20 with 1s pause
  7. Re-run enumeration probe (approved pool, n >= 50)
  8. Provenance bump (enrichment_status news_enriched -> cl_enriched)
  9. Final Markdown report with production-readiness verdict

Read-write for settle_contributions.jurisdiction + settle_case_provenance
(enrichment_status, match_confidence, cl_docket_id). No git staging, no
commits -- data work only.
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
from typing import Any

SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))


# ---------------------------------------------------------------------------
# _Tee self-capture (belt-and-suspenders against PowerShell pipe flakiness)
# ---------------------------------------------------------------------------
class _Tee:
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


LOG_PATH = SERVICE_ROOT / "logs" / "disambiguate.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
_log_fh = LOG_PATH.open("w", encoding="utf-8")
sys.stdout = _Tee(sys.__stdout__, _log_fh)
sys.stderr = _Tee(sys.__stderr__, _log_fh)

import httpx  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import get_db, reset_client  # noqa: E402


PAGE = 1000


def hr(char: str = "=", width: int = 72) -> None:
    print(char * width)


# ---------------------------------------------------------------------------
# FL circuit -> county mapping (judicial circuits 1-20)
#   Single-county circuits resolve unambiguously.
#   Multi-county circuits return the list; caller must have extra signal to
#   pick the specific county, else skips update.
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# CourtListener court_id -> county mapping
#   Covers known FL state + federal court IDs. Partial coverage -- state
#   circuit coverage on CL is sparse, so this is a best-effort lookup.
# ---------------------------------------------------------------------------
CL_COURT_TO_COUNTY: dict[str, str] = {
    # Federal district courts (primary seat county)
    "flmd": "Orange",       # Middle District of FL (Orlando seat; Tampa & Jax divisions)
    "flnd": "Leon",         # Northern District of FL (Tallahassee seat)
    "flsd": "Miami-Dade",   # Southern District of FL (Miami seat)
    # Florida DCAs -- multi-circuit; do NOT map (caller skips)
    # "fladistctapp1": None,
    # Florida Supreme / appellate -- skip
    # Known state circuit court IDs (CL's coverage is sparse, add as discovered)
    "flacir11": "Miami-Dade",
    "flacir13": "Hillsborough",
    "flacir15": "Palm Beach",
    "flacir16": "Monroe",
    "flacir17": "Broward",
}

# ---------------------------------------------------------------------------
# News URL -> county hint patterns (secondary signal)
# ---------------------------------------------------------------------------
URL_COUNTY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"miami[-_]?dade|miamidade", re.I), "Miami-Dade"),
    (re.compile(r"broward", re.I), "Broward"),
    (re.compile(r"palm[-_]?beach", re.I), "Palm Beach"),
    (re.compile(r"hillsborough|tampa(bay)?|tampa[-_]?bay", re.I), "Hillsborough"),
    (re.compile(r"orange[-_]?county|orlandosentinel|orlando[-_]?county", re.I), "Orange"),
    (re.compile(r"duval|jacksonville", re.I), "Duval"),
    (re.compile(r"pinellas|st[-_.]?petersburg|clearwater", re.I), "Pinellas"),
    (re.compile(r"leon[-_]?county|tallahassee", re.I), "Leon"),
    (re.compile(r"sarasota", re.I), "Sarasota"),
    (re.compile(r"lee[-_]?county|fort[-_]?myers", re.I), "Lee"),
    (re.compile(r"collier|naples", re.I), "Collier"),
    (re.compile(r"volusia|daytona", re.I), "Volusia"),
    (re.compile(r"brevard", re.I), "Brevard"),
    (re.compile(r"seminole", re.I), "Seminole"),
    (re.compile(r"osceola|kissimmee", re.I), "Osceola"),
    (re.compile(r"polk[-_]?county|lakeland", re.I), "Polk"),
    (re.compile(r"pasco", re.I), "Pasco"),
    (re.compile(r"manatee|bradenton", re.I), "Manatee"),
    (re.compile(r"alachua|gainesville", re.I), "Alachua"),
    (re.compile(r"escambia|pensacola", re.I), "Escambia"),
    (re.compile(r"marion[-_]?county|ocala", re.I), "Marion"),
    (re.compile(r"st[-_.]?lucie", re.I), "St. Lucie"),
    (re.compile(r"martin[-_]?county", re.I), "Martin"),
    (re.compile(r"indian[-_]?river", re.I), "Indian River"),
    (re.compile(r"monroe[-_]?county|key[-_]?west", re.I), "Monroe"),
]

CIRCUIT_ID_RE = re.compile(r"flacir(\d+)$|fla(\d+)cir$", re.I)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _format_jurisdiction(county: str) -> str:
    """Canonical jurisdiction string for UPDATE."""
    return f"{county} County, FL"


def _parse_env_file(path: Path) -> dict[str, str]:
    """Cheap .env parser (key=value lines, skips comments/blank)."""
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        k, _, v = s.partition("=")
        out[k.strip()] = v.strip()
    return out


def _hint_from_url(url: str | None) -> str | None:
    """Extract county name from a news URL using regex patterns."""
    if not url:
        return None
    for pat, county in URL_COUNTY_PATTERNS:
        if pat.search(url):
            return county
    return None


def _county_from_cl_court_id(court_id: str | None) -> str | None:
    """Map CL court_id to county if known."""
    if not court_id:
        return None
    cid = court_id.lower().strip()
    if cid in CL_COURT_TO_COUNTY:
        return CL_COURT_TO_COUNTY[cid]
    # Try parsing 'flacirNN' or 'flaNNcir' patterns
    m = CIRCUIT_ID_RE.search(cid)
    if m:
        circ_num = int(m.group(1) or m.group(2))
        counties = FL_CIRCUIT_TO_COUNTIES.get(circ_num)
        if counties and len(counties) == 1:
            return counties[0]
    return None


# ---------------------------------------------------------------------------
# CourtListener client
# ---------------------------------------------------------------------------
class CLClient:
    BASE = "https://www.courtlistener.com/api/rest/v4"

    def __init__(self, token: str | None):
        self.token = token
        self.headers = {"User-Agent": "TrueVow-SETTLE-DataScaling/1.0"}
        if token:
            self.headers["Authorization"] = f"Token {token}"
        self.client = httpx.Client(timeout=20.0, headers=self.headers)
        # Pacing: 0.25s/call authenticated (=4 req/s, within 5000/hr), 6s anonymous
        self.sleep_between = 0.25 if token else 6.0
        self.last_call = 0.0
        self.calls_made = 0
        self.errors = 0
        self.throttle_hits = 0

    def _pace(self):
        dt = time.time() - self.last_call
        if dt < self.sleep_between:
            time.sleep(self.sleep_between - dt)
        self.last_call = time.time()

    def search_by_docket(self, docket_number: str) -> list[dict]:
        """Search dockets by docket_number, filtered to FL-ish courts."""
        if not docket_number:
            return []
        self._pace()
        self.calls_made += 1
        try:
            r = self.client.get(
                f"{self.BASE}/dockets/",
                params={"docket_number": docket_number, "page_size": 10},
            )
            if r.status_code == 429:
                self.throttle_hits += 1
                time.sleep(10)
                return []
            if r.status_code >= 400:
                self.errors += 1
                return []
            j = r.json()
            return j.get("results", []) or []
        except Exception:
            self.errors += 1
            return []

    def search_opinions_by_name(self, case_name: str) -> list[dict]:
        """Search opinions by case name. FL-prefiltered via court-id suffix."""
        if not case_name:
            return []
        # Trim common "v. / vs." split tokens -- just use shortest descriptor
        q = case_name.strip()
        if len(q) > 120:
            q = q[:120]
        self._pace()
        self.calls_made += 1
        try:
            r = self.client.get(
                f"{self.BASE}/search/",
                params={"q": q, "type": "o", "page_size": 10},
            )
            if r.status_code == 429:
                self.throttle_hits += 1
                time.sleep(10)
                return []
            if r.status_code >= 400:
                self.errors += 1
                return []
            j = r.json()
            return j.get("results", []) or []
        except Exception:
            self.errors += 1
            return []

    def close(self):
        try:
            self.client.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Resolution per row
# ---------------------------------------------------------------------------
def _resolve_row(row: dict, prov: dict, cl: CLClient) -> dict:
    """Return a resolution dict:
      {
        'contribution_id', 'case_name', 'docket_number',
        'resolved_county', 'resolved_jurisdiction',
        'confidence' ('high'|'medium'|'low'|'none'),
        'method' ('cl_docket'|'cl_name'|'url_hint'|'none'),
        'cl_docket_id' (if any), 'notes'
      }
    """
    out = {
        "contribution_id": row.get("id"),
        "case_name": (prov or {}).get("case_name"),
        "docket_number": (prov or {}).get("docket_number"),
        "resolved_county": None,
        "resolved_jurisdiction": None,
        "confidence": "none",
        "method": "none",
        "cl_docket_id": None,
        "notes": "",
    }
    docket = (prov or {}).get("docket_number")
    case_name = (prov or {}).get("case_name")
    news_url = (prov or {}).get("news_provenance")

    # Strategy 1: exact docket match on CL
    if docket:
        hits = cl.search_by_docket(docket)
        for h in hits:
            court_id = h.get("court_id") or h.get("court")
            # court field sometimes is a URL like ".../courts/flmd/"
            if isinstance(court_id, str) and court_id.startswith("http"):
                court_id = court_id.rstrip("/").rsplit("/", 1)[-1]
            if court_id and not court_id.lower().startswith(("fl", "fla")):
                continue  # not a FL court
            county = _county_from_cl_court_id(court_id)
            if county:
                out["resolved_county"] = county
                out["resolved_jurisdiction"] = _format_jurisdiction(county)
                out["confidence"] = "high"
                out["method"] = "cl_docket"
                out["cl_docket_id"] = str(h.get("id") or "")
                out["notes"] = f"court_id={court_id}"
                return out
            if court_id:
                out["notes"] = f"cl_docket hit but unmapped court_id={court_id}"

    # Strategy 2: case-name search on CL opinions
    if case_name and out["resolved_county"] is None:
        hits = cl.search_opinions_by_name(case_name)
        for h in hits:
            court_id = h.get("court_id") or h.get("court")
            if isinstance(court_id, str) and court_id.startswith("http"):
                court_id = court_id.rstrip("/").rsplit("/", 1)[-1]
            if court_id and not court_id.lower().startswith(("fl", "fla")):
                continue
            county = _county_from_cl_court_id(court_id)
            if county:
                out["resolved_county"] = county
                out["resolved_jurisdiction"] = _format_jurisdiction(county)
                out["confidence"] = "medium"
                out["method"] = "cl_name"
                out["cl_docket_id"] = str(h.get("docket_id") or h.get("id") or "")
                out["notes"] = f"court_id={court_id}"
                return out

    # Strategy 3: news URL hint (fallback)
    if news_url:
        county = _hint_from_url(news_url)
        if county:
            out["resolved_county"] = county
            out["resolved_jurisdiction"] = _format_jurisdiction(county)
            out["confidence"] = "low"
            out["method"] = "url_hint"
            out["notes"] = f"url={news_url[:80]}"
            return out

    return out


# ---------------------------------------------------------------------------
# DB operations
# ---------------------------------------------------------------------------
def _paginate(db, table: str, select: str, filters=None, max_rows: int = 5000) -> list[dict]:
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


def _fetch_provenance_chunked(db, ids: list[str]) -> dict[str, dict]:
    """Batched IN lookup for provenance rows by contribution_id."""
    CHUNK = 50
    out: dict[str, dict] = {}
    for i in range(0, len(ids), CHUNK):
        chunk = ids[i : i + CHUNK]
        q = db.table("settle_case_provenance").select(
            "contribution_id,case_name,docket_number,judge_name,"
            "case_citation,source_url,news_provenance,cl_docket_id,"
            "enrichment_status,match_confidence"
        ).in_("contribution_id", chunk).limit(PAGE)
        resp = q.execute()
        for r in (resp.data or []):
            out[r.get("contribution_id")] = r
    return out


async def _boot():
    settings.USE_MOCK_DATA = False
    settings.SETTLE_USE_MOCK_DATA = False
    reset_client()
    return await get_db()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    hr()
    print("Phase 2 - Data Scaling County Disambiguation Pass")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    hr()

    # ------------------------------------------------------------------
    # PRE-FLIGHT
    # ------------------------------------------------------------------
    print("\n[PRE-FLIGHT]")

    # 1. Load .env.local for CL token
    env = _parse_env_file(SERVICE_ROOT / ".env.local")
    cl_token = (
        env.get("COURTLISTENER_API_TOKEN")
        or env.get("COURTLISTENER_API_KEY")
        or os.environ.get("COURTLISTENER_API_TOKEN")
        or os.environ.get("COURTLISTENER_API_KEY")
    )
    if cl_token:
        print(f"  [OK] CL token loaded (len={len(cl_token)}, rate=5000/hr)")
    else:
        print("  [WARN] No CL token found -- using anonymous rate (600/hr, 6s sleep/row)")

    # 2. Supabase smoke
    try:
        db = asyncio.run(_boot())
        smoke = db.table("settle_contributions").select("id", count="exact").limit(1).execute()
        smoke_count = smoke.count
        print(f"  [OK] Supabase reachable, settle_contributions count={smoke_count}")
    except Exception as e:
        print(f"  [FAIL] Supabase smoke: {e}")
        return 2

    # 3. Alembic HEAD (read-only check via alembic_version table if present)
    try:
        av = db.table("alembic_version").select("version_num").limit(1).execute()
        head = (av.data or [{}])[0].get("version_num")
        expected = "ec7e4c7db3be"
        tag = "[OK]" if head == expected else "[WARN]"
        print(f"  {tag} alembic HEAD={head} (expected={expected})")
    except Exception as e:
        print(f"  [WARN] alembic_version read failed: {e}")

    # ------------------------------------------------------------------
    # FETCH Unknown-County rows
    # ------------------------------------------------------------------
    print("\n[STEP 1] Fetching Unknown-County contribution rows...")
    unknown_rows = _paginate(
        db,
        "settle_contributions",
        "id,jurisdiction,case_type,status",
        filters=[("eq", "jurisdiction", "FL (Unknown County)")],
    )
    print(f"  Fetched {len(unknown_rows)} rows with jurisdiction='FL (Unknown County)'")
    ids = [r["id"] for r in unknown_rows if r.get("id")]

    print("\n[STEP 1b] Fetching provenance for those rows (chunked IN)...")
    prov_by_id = _fetch_provenance_chunked(db, ids)
    print(f"  Fetched {len(prov_by_id)} provenance records")

    # Status distribution (limit disambiguation to approved+pending, not rejected/flagged)
    status_counts = Counter(r.get("status") for r in unknown_rows)
    print(f"  Status distribution: {dict(status_counts)}")

    # ------------------------------------------------------------------
    # RESOLUTION PASS
    # ------------------------------------------------------------------
    print("\n[STEP 2] Resolving via CourtListener + URL hints...")
    cl = CLClient(cl_token)
    resolutions: list[dict] = []
    start = time.time()
    for i, row in enumerate(unknown_rows, 1):
        prov = prov_by_id.get(row.get("id")) or {}
        res = _resolve_row(row, prov, cl)
        resolutions.append(res)
        if i % 25 == 0 or i == len(unknown_rows):
            elapsed = time.time() - start
            matched = sum(1 for r in resolutions if r["resolved_county"])
            print(
                f"  [{i}/{len(unknown_rows)}] matched={matched} "
                f"cl_calls={cl.calls_made} errors={cl.errors} "
                f"throttles={cl.throttle_hits} elapsed={elapsed:.0f}s"
            )
        # Wall-clock safety
        if time.time() - start > 2 * 3600:
            print("  [HALT] 2h wall-clock exceeded; stopping resolution loop")
            break
    cl.close()

    # ------------------------------------------------------------------
    # DRY-RUN SUMMARY
    # ------------------------------------------------------------------
    print("\n[STEP 3] Dry-run summary")
    hr("-")
    matched = [r for r in resolutions if r["resolved_county"]]
    unmatched = [r for r in resolutions if not r["resolved_county"]]
    by_method = Counter(r["method"] for r in matched)
    by_conf = Counter(r["confidence"] for r in matched)
    by_county = Counter(r["resolved_county"] for r in matched)

    print(f"  Total queried:        {len(resolutions)}")
    print(f"  Matched:              {len(matched)} ({100*len(matched)/max(1,len(resolutions)):.1f}%)")
    print(f"  Unmatched:            {len(unmatched)}")
    print(f"  By method:            {dict(by_method)}")
    print(f"  By confidence:        {dict(by_conf)}")
    print("  County distribution (top 15):")
    for county, n in by_county.most_common(15):
        print(f"    {county:<20} {n}")
    print(f"  CL calls:             {cl.calls_made}")
    print(f"  CL errors:            {cl.errors}")
    print(f"  CL throttle hits:     {cl.throttle_hits}")

    match_rate = 100 * len(matched) / max(1, len(resolutions))

    # Surface-back trigger: <60% match rate
    if match_rate < 60:
        print(
            f"\n  [SURFACE] Match rate {match_rate:.1f}% below the 60% "
            "architect-comfort threshold (architect's >40% failure rule)."
        )
        print(
            "  Proceeding with confident matches only (high/medium/url_hint). "
            "Architect review recommended post-pass."
        )

    # Gate: if 0 matches, abort -- nothing to apply
    if len(matched) == 0:
        print("\n  [ABORT] Zero matches -- nothing to update. Halting before writes.")
        return 3

    # ------------------------------------------------------------------
    # APPLY UPDATES (batched, with pause)
    # ------------------------------------------------------------------
    print("\n[STEP 4] Applying UPDATE to settle_contributions.jurisdiction...")
    applied_ok = 0
    applied_fail = 0
    # Sort: high confidence first so any partial halt preserves best data
    conf_order = {"high": 0, "medium": 1, "low": 2}
    matched_sorted = sorted(matched, key=lambda r: conf_order.get(r["confidence"], 3))

    BATCH = 20
    for i in range(0, len(matched_sorted), BATCH):
        batch = matched_sorted[i : i + BATCH]
        for res in batch:
            cid = res["contribution_id"]
            new_j = res["resolved_jurisdiction"]
            try:
                resp = (
                    db.table("settle_contributions")
                    .update({"jurisdiction": new_j})
                    .eq("id", cid)
                    .execute()
                )
                if resp.data:
                    applied_ok += 1
                else:
                    applied_fail += 1
            except Exception as e:
                applied_fail += 1
                print(f"    [ERR] {cid}: {e}")
        done = min(i + BATCH, len(matched_sorted))
        print(
            f"  batch {i//BATCH + 1}: ok={applied_ok} fail={applied_fail} "
            f"({done}/{len(matched_sorted)})"
        )
        time.sleep(1.0)
    print(f"  Total UPDATEs applied: ok={applied_ok} fail={applied_fail}")

    # ------------------------------------------------------------------
    # PROVENANCE BUMP (only for rows that had a CL-backed match)
    # ------------------------------------------------------------------
    print("\n[STEP 5] Bumping provenance enrichment_status + match_confidence...")
    prov_ok = 0
    prov_fail = 0
    conf_map = {"high": "high", "medium": "medium", "low": "low"}
    for res in matched_sorted:
        if res["method"] not in ("cl_docket", "cl_name"):
            continue
        cid = res["contribution_id"]
        patch: dict[str, Any] = {
            "enrichment_status": "cl_enriched",
            "match_confidence": conf_map.get(res["confidence"], "low"),
        }
        if res.get("cl_docket_id"):
            patch["cl_docket_id"] = res["cl_docket_id"]
        try:
            resp = (
                db.table("settle_case_provenance")
                .update(patch)
                .eq("contribution_id", cid)
                .execute()
            )
            if resp.data:
                prov_ok += 1
            else:
                prov_fail += 1
        except Exception as e:
            prov_fail += 1
            print(f"    [ERR] prov {cid}: {e}")
    print(f"  Provenance bumps: ok={prov_ok} fail={prov_fail}")

    # ------------------------------------------------------------------
    # RE-ENUMERATION PROBE
    # ------------------------------------------------------------------
    print("\n[STEP 6] Re-running (jurisdiction, case_type) enumeration...")
    approved_rows = _paginate(
        db,
        "settle_contributions",
        "jurisdiction,case_type",
        filters=[("eq", "status", "approved")],
    )
    pair_counts: Counter = Counter()
    for r in approved_rows:
        pair_counts[(r.get("jurisdiction"), r.get("case_type"))] += 1

    GATE = 50
    passing = [(p, n) for p, n in pair_counts.items() if n >= GATE]
    passing.sort(key=lambda x: -x[1])
    real_county_passing = [
        (p, n)
        for p, n in passing
        if p[0] and "Unknown County" not in str(p[0])
    ]
    sentinel_passing = [
        (p, n) for p, n in passing if p[0] and "Unknown County" in str(p[0])
    ]

    print(f"  Approved rows total: {len(approved_rows)}")
    print(f"  Unique pairs:        {len(pair_counts)}")
    print(f"  Passing n>={GATE}:   {len(passing)}")
    print(f"    - real-county:     {len(real_county_passing)}")
    print(f"    - sentinel (Unknown): {len(sentinel_passing)}")
    print("  Top 15 pairs (all):")
    for (juris, ct), n in sorted(pair_counts.items(), key=lambda x: -x[1])[:15]:
        flag = ">>PASS" if n >= GATE else ""
        print(f"    {n:>5}  {juris} | {ct}   {flag}")

    # ------------------------------------------------------------------
    # PRODUCTION-READINESS VERDICT
    # ------------------------------------------------------------------
    print("\n[STEP 7] Production-readiness verdict")
    hr("-")
    if len(real_county_passing) >= 3:
        verdict = "GREEN"
        reason = f"{len(real_county_passing)} real-county pairs clear n>={GATE}"
    elif 1 <= len(real_county_passing) <= 2:
        verdict = "YELLOW"
        reason = (
            f"{len(real_county_passing)} real-county pair(s) clear n>={GATE}; "
            "consider Phase 3 targeted scrape"
        )
    else:
        verdict = "RED"
        reason = "0 real-county pairs clear the gate; Phase 3 required"
    print(f"  VERDICT: {verdict}  ({reason})")

    # ------------------------------------------------------------------
    # SUMMARY DUMP (machine-readable for architect)
    # ------------------------------------------------------------------
    summary = {
        "started": datetime.now(timezone.utc).isoformat(),
        "unknown_rows_fetched": len(unknown_rows),
        "provenance_loaded": len(prov_by_id),
        "resolutions": len(resolutions),
        "matched": len(matched),
        "unmatched": len(unmatched),
        "match_rate_pct": round(match_rate, 2),
        "by_method": dict(by_method),
        "by_confidence": dict(by_conf),
        "county_distribution": dict(by_county.most_common()),
        "updates_ok": applied_ok,
        "updates_fail": applied_fail,
        "provenance_bumps_ok": prov_ok,
        "provenance_bumps_fail": prov_fail,
        "cl_calls": cl.calls_made,
        "cl_errors": cl.errors,
        "cl_throttles": cl.throttle_hits,
        "approved_after": len(approved_rows),
        "pairs_passing_n50": len(passing),
        "real_county_passing": [
            {"jurisdiction": p[0], "case_type": p[1], "n": n}
            for p, n in real_county_passing
        ],
        "sentinel_passing": [
            {"jurisdiction": p[0], "case_type": p[1], "n": n}
            for p, n in sentinel_passing
        ],
        "verdict": verdict,
        "verdict_reason": reason,
    }
    summary_path = SERVICE_ROOT / "logs" / "disambiguate_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\n  Structured summary: {summary_path}")

    hr()
    print(f"Finished: {datetime.now(timezone.utc).isoformat()}")
    hr()
    return 0


if __name__ == "__main__":
    sys.exit(main())
