"""Phase 3a Parts 2-4 — Recover case_name, scrape TopVerdict for attorneys,
re-run CL disambiguation, re-enumerate, declare verdict.

Adapted from architect's original "list-page -> detail-page" plan after
probe revealed:
  (a) TopVerdict list pages ARE the detail pages (no second-tier nav)
  (b) case_citation already contains "Plaintiff v Defendant" for 100% of
      rows -- the scraper stored case_name in the wrong column
  (c) list pages expose attorneys + amount + type; NO court/docket/judge

Strategy:
  Part 2A: copy provenance.case_citation -> provenance.case_name when the
           citation matches "X v Y" / "X vs Y" pattern.
  Part 2B: scrape 126 unique TopVerdict source URLs; match list-rows to DB
           rows by case_name; update provenance.plaintiff_firm with the
           attorneys field.
  Part 3:  re-run CL disambiguation -- this time queries actually fire
           because case_name is now populated.
  Part 4:  re-enum (jurisdiction, case_type) -> count real-county pairs
           clearing n>=50, declare GREEN/YELLOW/RED.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

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


LOG = SERVICE_ROOT / "logs" / "phase3a_main.log"
LOG.parent.mkdir(parents=True, exist_ok=True)
_fh = LOG.open("w", encoding="utf-8")
sys.stdout = _Tee(sys.__stdout__, _fh)
sys.stderr = _Tee(sys.__stderr__, _fh)

from app.core.config import settings  # noqa: E402
from app.core.database import get_db, reset_client  # noqa: E402


PAGE = 1000

# ---------------------------------------------------------------------------
# Constants from prior phase 2 work (re-used)
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
CL_COURT_TO_COUNTY: dict[str, str] = {
    "flmd": "Orange", "flnd": "Leon", "flsd": "Miami-Dade",
    "flacir11": "Miami-Dade", "flacir13": "Hillsborough",
    "flacir15": "Palm Beach", "flacir16": "Monroe", "flacir17": "Broward",
}
CIRCUIT_ID_RE = re.compile(r"flacir(\d+)$|fla(\d+)cir$", re.I)

# Case-name validation: recognises "X v Y" / "X vs Y" / "X v. Y" / "X vs. Y"
CASE_NAME_RE = re.compile(r".+\s+v\.?s?\.?\s+.+", re.I)

# Florida law-firm city -> county hint map (best-effort; tertiary signal)
FIRM_CITY_TO_COUNTY: dict[str, str] = {
    "miami": "Miami-Dade", "miami beach": "Miami-Dade", "coral gables": "Miami-Dade",
    "doral": "Miami-Dade", "homestead": "Miami-Dade",
    "fort lauderdale": "Broward", "ft lauderdale": "Broward", "ft. lauderdale": "Broward",
    "hollywood": "Broward", "pembroke pines": "Broward", "plantation": "Broward",
    "west palm beach": "Palm Beach", "boca raton": "Palm Beach", "delray beach": "Palm Beach",
    "boynton beach": "Palm Beach", "jupiter": "Palm Beach",
    "tampa": "Hillsborough", "brandon": "Hillsborough",
    "orlando": "Orange", "winter park": "Orange",
    "kissimmee": "Osceola",
    "jacksonville": "Duval",
    "fort myers": "Lee", "ft myers": "Lee", "ft. myers": "Lee", "cape coral": "Lee",
    "naples": "Collier",
    "sarasota": "Sarasota",
    "st. petersburg": "Pinellas", "st petersburg": "Pinellas", "clearwater": "Pinellas",
    "tallahassee": "Leon",
    "gainesville": "Alachua",
    "pensacola": "Escambia",
    "ocala": "Marion",
    "daytona beach": "Volusia", "daytona": "Volusia",
    "melbourne": "Brevard",
    "lakeland": "Polk",
    "key west": "Monroe",
    "bradenton": "Manatee",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "DNT": "1", "Upgrade-Insecure-Requests": "1",
}


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
async def _boot():
    settings.USE_MOCK_DATA = False
    settings.SETTLE_USE_MOCK_DATA = False
    reset_client()
    return await get_db()


def _paginate(db, table, select, filters=None, max_rows=5000):
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


def _fetch_provenance(db, ids: list[str]) -> dict[str, dict]:
    out = {}
    CHUNK = 50
    for i in range(0, len(ids), CHUNK):
        chunk = ids[i:i + CHUNK]
        q = db.table("settle_case_provenance").select(
            "contribution_id,case_name,case_citation,docket_number,judge_name,"
            "source_url,news_provenance,plaintiff_firm,enrichment_status,match_confidence"
        ).in_("contribution_id", chunk).limit(PAGE)
        r = q.execute()
        for row in r.data or []:
            out[row["contribution_id"]] = row
    return out


# ---------------------------------------------------------------------------
# CourtListener client (re-used)
# ---------------------------------------------------------------------------
class CLClient:
    BASE = "https://www.courtlistener.com/api/rest/v4"

    def __init__(self, token: str | None):
        self.token = token
        h = dict(HEADERS)
        h["User-Agent"] = "TrueVow-SETTLE-DataScaling/1.0"
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
            r = self.client.get(f"{self.BASE}/dockets/", params={"docket_number": docket, "page_size": 10})
            if r.status_code == 429:
                self.throttles += 1; time.sleep(10); return []
            if r.status_code >= 400:
                self.errs += 1; return []
            return (r.json().get("results", []) or [])
        except Exception:
            self.errs += 1; return []

    def search_opinions(self, name: str) -> list[dict]:
        if not name: return []
        q = name.strip()[:120]
        self._pace(); self.calls += 1
        try:
            r = self.client.get(f"{self.BASE}/search/", params={"q": q, "type": "o", "page_size": 10})
            if r.status_code == 429:
                self.throttles += 1; time.sleep(10); return []
            if r.status_code >= 400:
                self.errs += 1; return []
            return (r.json().get("results", []) or [])
        except Exception:
            self.errs += 1; return []

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


def _county_from_firm(firm: str | None) -> str | None:
    if not firm: return None
    s = firm.lower()
    # Try longer phrases first to avoid e.g. "miami" matching inside "miami beach"
    for city in sorted(FIRM_CITY_TO_COUNTY.keys(), key=lambda x: -len(x)):
        if city in s:
            return FIRM_CITY_TO_COUNTY[city]
    return None


def _format_juris(county: str) -> str:
    return f"{county} County, FL"


# ---------------------------------------------------------------------------
# TopVerdict list-page parser
# ---------------------------------------------------------------------------
def _parse_topverdict_listpage(html: str) -> list[dict]:
    """Return [{'rank': str, 'amount': str, 'attorneys': str, 'case': str,
                'type': str}, ...] for each verdict row on the page.
    Uses the list-rank / list-row1 / list-row2 class scheme observed in probe."""
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    current: dict = {}
    # Walk the table body; rows alternate as: rank-tr, then field-trs
    for tr in soup.find_all("tr"):
        rank_td = tr.find("td", class_="list-rank")
        if rank_td:
            if current:
                rows.append(current)
            current = {"rank": rank_td.get_text(strip=True)}
            continue
        # Field rows: 2 tds, label then value
        tds = tr.find_all("td")
        if len(tds) == 2:
            label = tds[0].get_text(strip=True).rstrip(":").lower()
            value = tds[1].get_text(strip=True)
            if label in {"amount", "attorneys", "case", "type", "visit"}:
                current[label] = value
    if current:
        rows.append(current)
    return rows


def _normalise_case_name(s: str) -> str:
    if not s: return ""
    return re.sub(r"\s+", " ", s.strip().lower())


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main() -> int:
    print("=" * 72)
    print("Phase 3a — Recover case_name + scrape attorneys + re-disambiguate + verdict")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 72)

    db = asyncio.run(_boot())

    # Pre-flight
    print("\n[PRE-FLIGHT]")
    smoke = db.table("settle_contributions").select("id", count="exact").limit(1).execute().count
    print(f"  Supabase reachable, settle_contributions count={smoke}")

    # ------------------------------------------------------------------
    # PART 2A — Recover case_name from case_citation
    # ------------------------------------------------------------------
    print("\n[PART 2A] Recover case_name from case_citation")
    print("-" * 72)
    unknown_rows = _paginate(
        db, "settle_contributions", "id,jurisdiction,case_type,status",
        filters=[("eq", "jurisdiction", "FL (Unknown County)")],
    )
    print(f"  Unknown-County rows: {len(unknown_rows)}")
    ids = [r["id"] for r in unknown_rows if r.get("id")]
    prov_by_id = _fetch_provenance(db, ids)
    print(f"  Provenance loaded:    {len(prov_by_id)}")

    case_name_recovered = 0
    case_name_skipped_pattern = 0
    case_name_already_set = 0
    case_name_no_citation = 0
    case_name_fail = 0
    name_updates = []
    for cid, prov in prov_by_id.items():
        existing = (prov.get("case_name") or "").strip()
        if existing:
            case_name_already_set += 1
            continue
        cit = (prov.get("case_citation") or "").strip()
        if not cit:
            case_name_no_citation += 1
            continue
        if not CASE_NAME_RE.match(cit):
            case_name_skipped_pattern += 1
            continue
        name_updates.append((cid, cit))

    print(f"  Already set (case_name not null): {case_name_already_set}")
    print(f"  No case_citation: {case_name_no_citation}")
    print(f"  Citation present but not 'X v Y' pattern: {case_name_skipped_pattern}")
    print(f"  Will recover: {len(name_updates)}")

    # Apply in batches of 25 with 0.5s pause
    print("\n  Applying case_name updates (batches of 25, 0.5s pause)...")
    for i in range(0, len(name_updates), 25):
        batch = name_updates[i:i + 25]
        for cid, name in batch:
            try:
                r = db.table("settle_case_provenance").update({"case_name": name}).eq("contribution_id", cid).execute()
                if r.data:
                    case_name_recovered += 1
                else:
                    case_name_fail += 1
            except Exception as e:
                case_name_fail += 1
                print(f"    [ERR] case_name {cid}: {e}")
        time.sleep(0.5)
    print(f"  case_name recovered: ok={case_name_recovered} fail={case_name_fail}")

    # Reload provenance to get updated case_name values
    prov_by_id = _fetch_provenance(db, ids)
    populated_now = sum(1 for p in prov_by_id.values() if p.get("case_name"))
    print(f"  case_name populated now: {populated_now}/{len(prov_by_id)} ({100*populated_now/max(1,len(prov_by_id)):.1f}%)")

    # ------------------------------------------------------------------
    # PART 2B — Scrape TopVerdict list pages, enrich plaintiff_firm
    # ------------------------------------------------------------------
    print("\n[PART 2B] Scrape TopVerdict source URLs to enrich plaintiff_firm")
    print("-" * 72)

    # Group rows by source_url (only single-URL rows; skip pipe-delimited combos)
    url_to_provs: dict[str, list[dict]] = defaultdict(list)
    for p in prov_by_id.values():
        u = (p.get("source_url") or "").strip()
        if not u:
            continue
        # If pipe-delimited, take first as primary
        if "|" in u:
            u = u.split("|")[0].strip()
        if "topverdict.com" not in u:
            continue  # non-TopVerdict source
        url_to_provs[u].append(p)
    print(f"  Unique TopVerdict source URLs: {len(url_to_provs)}")
    print(f"  Provenance rows w/ TopVerdict source: {sum(len(v) for v in url_to_provs.values())}")

    # Scrape each unique URL once
    case_to_firm: dict[str, str] = {}  # normalised case_name -> attorneys
    pages_fetched = 0
    pages_failed = 0
    pages_403 = 0
    rows_parsed = 0
    scrape_start = time.time()

    with httpx.Client(timeout=30.0, headers=HEADERS, follow_redirects=True) as c:
        for url, provs in url_to_provs.items():
            if time.time() - scrape_start > 60 * 60:  # 1h scrape cap
                print("  [HALT] 1h scrape cap reached; stopping scrape loop")
                break
            try:
                r = c.get(url)
                if r.status_code == 403:
                    pages_403 += 1
                    pages_failed += 1
                    print(f"    [403] {url}")
                    time.sleep(2.0)
                    continue
                if r.status_code != 200:
                    pages_failed += 1
                    print(f"    [{r.status_code}] {url}")
                    time.sleep(2.0)
                    continue
                pages_fetched += 1
                listrows = _parse_topverdict_listpage(r.text)
                rows_parsed += len(listrows)
                for lr in listrows:
                    cn = lr.get("case", "")
                    if cn and lr.get("attorneys"):
                        case_to_firm[_normalise_case_name(cn)] = lr["attorneys"]
            except Exception as e:
                pages_failed += 1
                print(f"    [ERR] {url}: {e}")
            time.sleep(2.0)  # be polite

    print(f"\n  Pages fetched ok: {pages_fetched}/{len(url_to_provs)}")
    print(f"  Pages failed:     {pages_failed}  (403: {pages_403})")
    print(f"  List-rows parsed: {rows_parsed}")
    print(f"  Unique case-name -> attorneys mappings: {len(case_to_firm)}")

    # Surface-back: >10% 403s
    fail_403_rate = 100 * pages_403 / max(1, len(url_to_provs))
    if fail_403_rate > 10:
        print(f"  [SURFACE] 403 rate {fail_403_rate:.1f}% > 10% threshold -- partial scrape only")

    # Match each prov row's case_name to a list-row attorneys string, write to plaintiff_firm
    firm_ok = 0
    firm_fail = 0
    firm_unmatched = 0
    for cid, prov in prov_by_id.items():
        existing_firm = (prov.get("plaintiff_firm") or "").strip()
        if existing_firm:
            continue  # don't overwrite
        cn = (prov.get("case_name") or prov.get("case_citation") or "").strip()
        if not cn:
            firm_unmatched += 1
            continue
        firm = case_to_firm.get(_normalise_case_name(cn))
        if not firm:
            firm_unmatched += 1
            continue
        try:
            r = db.table("settle_case_provenance").update({"plaintiff_firm": firm[:500]}).eq("contribution_id", cid).execute()
            if r.data:
                firm_ok += 1
            else:
                firm_fail += 1
        except Exception as e:
            firm_fail += 1
            print(f"    [ERR] firm {cid}: {e}")
    print(f"\n  plaintiff_firm enriched: ok={firm_ok} fail={firm_fail} unmatched={firm_unmatched}")

    # Reload provenance once more
    prov_by_id = _fetch_provenance(db, ids)

    # ------------------------------------------------------------------
    # PART 3 — Re-run CL disambiguation
    # ------------------------------------------------------------------
    print("\n[PART 3] Re-run CourtListener disambiguation with populated case_name")
    print("-" * 72)
    # Load CL token from .env.local (cheap parser)
    cl_token = None
    env_path = SERVICE_ROOT / ".env.local"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, _, v = s.partition("=")
            if k.strip() == "COURTLISTENER_API_TOKEN":
                cl_token = v.strip()
                break
            if k.strip() == "COURTLISTENER_API_KEY" and not cl_token:
                cl_token = v.strip()
    print(f"  CL token: {'present (5000/hr)' if cl_token else 'absent (anonymous 600/hr)'}")

    cl = CLClient(cl_token)
    resolutions = []
    res_start = time.time()
    for i, row in enumerate(unknown_rows, 1):
        if time.time() - res_start > 60 * 30:
            print("  [HALT] 30min disambiguate cap reached; stopping")
            break
        cid = row.get("id")
        prov = prov_by_id.get(cid) or {}
        res = {
            "contribution_id": cid, "resolved_county": None,
            "resolved_jurisdiction": None, "confidence": "none",
            "method": "none", "cl_docket_id": None, "notes": "",
        }
        docket = prov.get("docket_number")
        case_name = prov.get("case_name") or prov.get("case_citation")
        firm = prov.get("plaintiff_firm")

        # 1) docket lookup
        if docket and not res["resolved_county"]:
            for h in cl.search_dockets(docket):
                court = h.get("court_id") or h.get("court")
                if isinstance(court, str) and court.startswith("http"):
                    court = court.rstrip("/").rsplit("/", 1)[-1]
                if not court or not court.lower().startswith(("fl", "fla")):
                    continue
                co = _county_from_cl(court)
                if co:
                    res.update(resolved_county=co, resolved_jurisdiction=_format_juris(co),
                               confidence="high", method="cl_docket",
                               cl_docket_id=str(h.get("id") or ""), notes=f"court_id={court}")
                    break

        # 2) case-name lookup
        if case_name and not res["resolved_county"]:
            for h in cl.search_opinions(case_name):
                court = h.get("court_id") or h.get("court")
                if isinstance(court, str) and court.startswith("http"):
                    court = court.rstrip("/").rsplit("/", 1)[-1]
                if not court or not court.lower().startswith(("fl", "fla")):
                    continue
                co = _county_from_cl(court)
                if co:
                    res.update(resolved_county=co, resolved_jurisdiction=_format_juris(co),
                               confidence="medium", method="cl_name",
                               cl_docket_id=str(h.get("docket_id") or h.get("id") or ""),
                               notes=f"court_id={court}")
                    break

        # 3) firm-city fallback (low confidence)
        if not res["resolved_county"]:
            co = _county_from_firm(firm)
            if co:
                res.update(resolved_county=co, resolved_jurisdiction=_format_juris(co),
                           confidence="low", method="firm_city",
                           notes=f"firm={(firm or '')[:80]}")

        resolutions.append(res)
        if i % 25 == 0 or i == len(unknown_rows):
            matched = sum(1 for x in resolutions if x["resolved_county"])
            print(f"    [{i}/{len(unknown_rows)}] matched={matched} cl_calls={cl.calls} errs={cl.errs} "
                  f"throttles={cl.throttles} elapsed={time.time()-res_start:.0f}s")
    cl.close()

    matched = [r for r in resolutions if r["resolved_county"]]
    by_method = Counter(r["method"] for r in matched)
    by_conf = Counter(r["confidence"] for r in matched)
    by_county = Counter(r["resolved_county"] for r in matched)
    match_rate = 100 * len(matched) / max(1, len(resolutions))
    cl_only_match = sum(1 for r in matched if r["method"] in ("cl_docket", "cl_name"))
    cl_only_rate = 100 * cl_only_match / max(1, len(resolutions))

    print(f"\n  Disambiguation results:")
    print(f"    Total queried:      {len(resolutions)}")
    print(f"    Matched (any):      {len(matched)} ({match_rate:.1f}%)")
    print(f"    CL-only matches:    {cl_only_match} ({cl_only_rate:.1f}%)")
    print(f"    By method:          {dict(by_method)}")
    print(f"    By confidence:      {dict(by_conf)}")
    print(f"    By county (top 15): {dict(by_county.most_common(15))}")
    print(f"    CL calls:           {cl.calls}")
    print(f"    CL errors:          {cl.errs}")
    print(f"    CL throttles:       {cl.throttles}")

    # Architect surface-back: halt if CL match rate (high+medium only) <30%
    if cl_only_rate < 30:
        print(f"\n  [SURFACE] CL-only match rate {cl_only_rate:.1f}% < 30% threshold")
        print(f"  Per architect directive (Part 3 step 4): halt updates and surface back.")
        print(f"  Will NOT apply jurisdiction updates.")
        apply_updates = False
    else:
        apply_updates = True
        print(f"  [OK] CL-only match rate {cl_only_rate:.1f}% >= 30%; proceeding with updates.")

    # Apply updates only for high/medium (CL-backed) confidence
    updates_ok = 0
    updates_fail = 0
    if apply_updates:
        print("\n  Applying jurisdiction updates (high/medium confidence only)...")
        applicable = [r for r in matched if r["confidence"] in ("high", "medium")]
        for i in range(0, len(applicable), 20):
            batch = applicable[i:i + 20]
            for res in batch:
                try:
                    r = db.table("settle_contributions").update(
                        {"jurisdiction": res["resolved_jurisdiction"]}
                    ).eq("id", res["contribution_id"]).execute()
                    if r.data:
                        updates_ok += 1
                    else:
                        updates_fail += 1
                except Exception as e:
                    updates_fail += 1
                    print(f"    [ERR] update {res['contribution_id']}: {e}")
            time.sleep(1.0)
        print(f"  jurisdiction updates: ok={updates_ok} fail={updates_fail}")

        # Provenance bump for CL-backed matches
        prov_ok = 0
        prov_fail = 0
        for res in applicable:
            patch = {"enrichment_status": "cl_enriched", "match_confidence": res["confidence"]}
            if res.get("cl_docket_id"):
                patch["cl_docket_id"] = res["cl_docket_id"]
            try:
                r = db.table("settle_case_provenance").update(patch).eq("contribution_id", res["contribution_id"]).execute()
                if r.data:
                    prov_ok += 1
                else:
                    prov_fail += 1
            except Exception as e:
                prov_fail += 1
                print(f"    [ERR] prov {res['contribution_id']}: {e}")
        print(f"  provenance bumps: ok={prov_ok} fail={prov_fail}")

    # ------------------------------------------------------------------
    # PART 4 — Re-enumerate + verdict
    # ------------------------------------------------------------------
    print("\n[PART 4] Re-run (jurisdiction, case_type) enumeration")
    print("-" * 72)
    approved = _paginate(db, "settle_contributions", "jurisdiction,case_type",
                         filters=[("eq", "status", "approved")])
    pair_counts = Counter()
    for r in approved:
        pair_counts[(r.get("jurisdiction"), r.get("case_type"))] += 1
    GATE = 50
    passing = [(p, n) for p, n in pair_counts.items() if n >= GATE]
    passing.sort(key=lambda x: -x[1])
    real_county = [(p, n) for p, n in passing if p[0] and "Unknown County" not in str(p[0])]
    sentinel = [(p, n) for p, n in passing if p[0] and "Unknown County" in str(p[0])]

    print(f"  Approved total: {len(approved)}")
    print(f"  Unique pairs:   {len(pair_counts)}")
    print(f"  Passing n>={GATE}:")
    print(f"    real-county: {len(real_county)}")
    print(f"    sentinel:    {len(sentinel)}")
    print(f"  Top 15 pairs:")
    for (j, ct), n in sorted(pair_counts.items(), key=lambda x: -x[1])[:15]:
        flag = ">>PASS" if n >= GATE else ""
        print(f"    {n:>5}  {j} | {ct}   {flag}")

    if len(real_county) >= 3:
        verdict = "GREEN"
        reason = f"{len(real_county)} real-county pairs clear n>={GATE}"
    elif 1 <= len(real_county) <= 2:
        verdict = "YELLOW"
        reason = f"{len(real_county)} real-county pair(s) clear n>={GATE}"
    else:
        verdict = "RED"
        reason = "0 real-county pairs clear the gate"
    print(f"\n  VERDICT: {verdict}  ({reason})")

    # Dump structured summary
    summary = {
        "started": datetime.now(timezone.utc).isoformat(),
        "case_name_recovered": case_name_recovered,
        "case_name_already_set": case_name_already_set,
        "case_name_pattern_skipped": case_name_skipped_pattern,
        "case_name_no_citation": case_name_no_citation,
        "topverdict_pages_fetched": pages_fetched,
        "topverdict_pages_failed": pages_failed,
        "topverdict_403s": pages_403,
        "topverdict_rows_parsed": rows_parsed,
        "case_to_firm_mappings": len(case_to_firm),
        "plaintiff_firm_enriched": firm_ok,
        "plaintiff_firm_unmatched": firm_unmatched,
        "disambiguate_resolutions": len(resolutions),
        "disambiguate_matched": len(matched),
        "disambiguate_match_rate_pct": round(match_rate, 2),
        "disambiguate_cl_only_rate_pct": round(cl_only_rate, 2),
        "disambiguate_by_method": dict(by_method),
        "disambiguate_by_confidence": dict(by_conf),
        "disambiguate_by_county": dict(by_county.most_common()),
        "cl_calls": cl.calls,
        "cl_errors": cl.errs,
        "cl_throttles": cl.throttles,
        "updates_applied": apply_updates,
        "updates_ok": updates_ok,
        "updates_fail": updates_fail,
        "approved_after": len(approved),
        "pairs_passing_n50": len(passing),
        "real_county_passing": [
            {"jurisdiction": p[0], "case_type": p[1], "n": n} for p, n in real_county
        ],
        "sentinel_passing": [
            {"jurisdiction": p[0], "case_type": p[1], "n": n} for p, n in sentinel
        ],
        "verdict": verdict,
        "verdict_reason": reason,
    }
    out = SERVICE_ROOT / "logs" / "phase3a_summary.json"
    out.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\n  Structured summary: {out}")

    print("\n" + "=" * 72)
    print(f"Finished: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
