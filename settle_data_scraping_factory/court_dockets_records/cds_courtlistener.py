"""
cds_courtlistener.py — CourtListener (Free Law Project) opinion adapter (Level 0 API).

CourtListener publishes a large, free corpus of court opinions via a REST API.
This adapter is the "volume engine" for FL/CA: it pulls published opinions from
Florida and California state courts and yields normalized records with the SAME
keys the shared CAP pipeline consumes (cds_cap_pipeline.build_candidate), so
CourtListener flows through the same validate -> score -> dedup -> route -> loader
path as CAP and MoreLaw.

INTEGRITY (LOW_BLOCKER_DATA_SOURCES section 6a — zero fabrication):
  * This adapter does NO classification or $-amount parsing of its own. The shared
    deterministic extractor (_common.extract) is the single source of truth for PI
    relevance, injuries, case type, and outcome amount (it abstains on non-PI).
  * Jurisdiction is taken reliably from the court id (FL/CA appellate court ids),
    never guessed from free text. Non-FL/CA results are dropped.
  * Every record carries provenance: source_url (web), full_text_url (API), the
    sha256 of the exact fetched payload, and a fetch timestamp.
  * CourtListener opinions are appellate / state-level and frequently year-only;
    the loader records that imprecision truthfully (it never invents a county/date).

Nothing is auto-published. Records route to accepted / needs_review / rejected and
only accepted + needs_review reach the human review queue (via cds_cap_loader).

Run:
    python cds_courtlistener.py --states Florida California --max 40
    python cds_courtlistener.py --states Florida --query "medical malpractice negligence" --max 25
    python cds_courtlistener.py --selftest

Env (loaded from .env.local / .env):
    COURTLISTENER_API_KEY  — free token (https://www.courtlistener.com/help/api/rest/);
                             raises the rate limit. Works (slower) without one.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterator, Optional

from bs4 import BeautifulSoup

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from _common.fetcher import Fetcher  # noqa: E402

CL_BASE = "https://www.courtlistener.com"
CL_API = f"{CL_BASE}/api/rest/v4"
OUT_DIR = Path(__file__).parent / "out"

# FL/CA *state* appellate court ids in CourtListener. Jurisdiction is derived from
# this map (a structured field), never from parsing free text.
STATE_FROM_COURT = {
    # Florida
    "fla": "Florida",            # Supreme Court of Florida
    "fladistctapp": "Florida",   # FL District Court of Appeal
    # California
    "cal": "California",          # Supreme Court of California
    "calctapp": "California",     # CA Court of Appeal
    "calappdeptsuper": "California",  # CA Appellate Division of the Superior Court
}
STATE_TO_COURTS = {
    "Florida": [c for c, s in STATE_FROM_COURT.items() if s == "Florida"],
    "California": [c for c, s in STATE_FROM_COURT.items() if s == "California"],
}

DEFAULT_QUERY = "personal injury negligence damages"


def _load_api_key() -> str:
    """Read COURTLISTENER_API_KEY from the environment, loading .env files if needed."""
    key = os.getenv("COURTLISTENER_API_KEY", "")
    if key:
        return key
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(_FACTORY_ROOT.parent / ".env.local")
        load_dotenv(_FACTORY_ROOT.parent / ".env")
        key = os.getenv("COURTLISTENER_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    # Dependency-light fallback: parse the key out of a local .env file ourselves.
    for env_name in (".env.local", ".env"):
        env_path = _FACTORY_ROOT.parent / env_name
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("COURTLISTENER_API_KEY") and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _auth_headers(key: str) -> Optional[dict]:
    return {"Authorization": f"Token {key}"} if key else None


def _abs_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    if url.startswith("http"):
        return url
    return CL_BASE + url if url.startswith("/") else url


def _year_from(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    m = re.search(r"(\d{4})", str(date_str))
    return int(m.group(1)) if m else None


def _opinion_id(item: dict) -> Optional[int]:
    """v4 search results nest opinion ids under `opinions`; fall back defensively."""
    ops = item.get("opinions") or []
    for o in ops:
        if isinstance(o, dict) and o.get("id"):
            return o["id"]
    for k in ("id", "opinion_id"):
        if item.get(k):
            return item[k]
    return None


def _first_citation(item: dict) -> Optional[str]:
    cites = item.get("citation")
    if isinstance(cites, list) and cites:
        return str(cites[0])
    if isinstance(cites, str) and cites:
        return cites
    return None


def _opinion_text_from_detail(detail: dict) -> str:
    """Plain text preferred; otherwise strip the cited-HTML body. No fabrication."""
    plain = (detail.get("plain_text") or "").strip()
    if plain:
        return plain[:60000]
    html = detail.get("html_with_citations") or detail.get("html") or detail.get("html_lawbox") or ""
    if not html:
        return ""
    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text)[:60000]


def iter_search(
    f: Fetcher,
    court: str,
    query: str,
    headers: Optional[dict],
    max_items: int,
    filed_after: Optional[str] = None,
    filed_before: Optional[str] = None,
) -> Iterator[dict]:
    """Yield opinion search-result items for one court id, paginating politely."""
    params = {"q": query, "type": "o", "court": court, "order_by": "dateFiled desc"}
    if filed_after:
        params["filed_after"] = filed_after
    if filed_before:
        params["filed_before"] = filed_before

    url: Optional[str] = f"{CL_API}/search/"
    use_params: Optional[dict] = params
    seen = 0
    while url and seen < max_items:
        try:
            res = f.get_json(url, params=use_params, headers=headers)
            data = res.json()
        except Exception:
            break
        for item in data.get("results", []):
            if seen >= max_items:
                break
            seen += 1
            yield item
        # `next` is an absolute URL already carrying query params.
        url = data.get("next")
        use_params = None


def fetch_opinion_record(
    f: Fetcher,
    item: dict,
    queried_court: str,
    headers: Optional[dict],
) -> Optional[dict]:
    """Build one normalized CAP-schema record from a search item + its opinion detail."""
    # Jurisdiction: trust the item's real court id when present, else the queried id.
    court_id = item.get("court_id") or queried_court
    jurisdiction = STATE_FROM_COURT.get(court_id)
    if jurisdiction is None:
        return None  # not an FL/CA court we recognize -> drop (no guessing)

    op_id = _opinion_id(item)
    if not op_id:
        return None

    full_text_url = f"{CL_API}/opinions/{op_id}/"
    try:
        res = f.get_json(full_text_url, headers=headers)
        detail = res.json()
    except Exception:
        return None

    text = _opinion_text_from_detail(detail)
    if len(text) < 50:
        return None

    source_url = _abs_url(detail.get("absolute_url")) or _abs_url(item.get("absolute_url"))
    if not source_url:
        return None  # provenance pair must be complete; never accept without it

    case_name = item.get("caseName") or item.get("case_name") or detail.get("caseName")
    citation = _first_citation(item) or f"courtlistener:{op_id}"
    year = _year_from(item.get("dateFiled") or item.get("date_filed") or detail.get("date_created"))

    return {
        "source": "courtlistener",
        "jurisdiction": jurisdiction,
        "name_abbreviation": case_name,
        "year": year,
        "official_citation": citation,
        "court_id": court_id,
        "full_text_url": full_text_url,
        "source_url": source_url,
        "text_sha256": res.sha256,
        "fetched_at": res.fetched_at,
        "opinion_text": text,
    }


def fetch_state_cases(
    f: Fetcher,
    states: list[str],
    query: str = DEFAULT_QUERY,
    max_cases: int = 40,
    filed_after: Optional[str] = None,
    filed_before: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Iterator[dict]:
    """Top-level adapter generator: FL/CA opinions -> normalized CAP-schema records."""
    headers = _auth_headers(api_key if api_key is not None else _load_api_key())
    courts: list[tuple[str, str]] = []
    for state in states:
        for court in STATE_TO_COURTS.get(state, []):
            courts.append((state, court))
    if not courts:
        return

    per_court = max(1, max_cases // len(courts) + 1)
    count = 0
    seen_ids: set = set()
    for _state, court in courts:
        if count >= max_cases:
            break
        for item in iter_search(f, court, query, headers, per_court, filed_after, filed_before):
            if count >= max_cases:
                break
            op_id = _opinion_id(item)
            if op_id in seen_ids:
                continue
            rec = fetch_opinion_record(f, item, court, headers)
            if rec is None:
                continue
            seen_ids.add(op_id)
            count += 1
            yield rec


def run(
    states: list[str],
    query: str = DEFAULT_QUERY,
    max_cases: int = 40,
    filed_after: Optional[str] = None,
    filed_before: Optional[str] = None,
    out_dir: Optional[Path] = None,
) -> dict:
    """Fetch -> route every record through the shared pipeline -> write buckets.

    Output files mirror the CAP pipeline naming so cds_cap_loader consumes them
    unchanged:  out/courtlistener_<state>_<bucket>.jsonl
    """
    from cds_cap_pipeline import build_candidate

    out_dir = out_dir or OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    buckets = {"accepted": [], "needs_review": [], "rejected": []}
    seen_keys: set[str] = set()
    duplicates = 0

    with Fetcher(min_delay=0.5) as f:
        for rec in fetch_state_cases(f, states, query=query, max_cases=max_cases,
                                     filed_after=filed_after, filed_before=filed_before):
            cand = build_candidate(rec)
            if cand["status"] == "accepted":
                if cand["dedup_key"] in seen_keys:
                    duplicates += 1
                    continue
                seen_keys.add(cand["dedup_key"])
            buckets[cand["status"]].append(cand)

    label = "_".join(s.lower() for s in states) or "all"
    for name, rows in buckets.items():
        path = out_dir / f"courtlistener_{label}_{name}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, default=str) + "\n")

    return {
        "source": "courtlistener",
        "states": states,
        "candidates_seen": sum(len(v) for v in buckets.values()) + duplicates,
        "accepted_usable": len(buckets["accepted"]),
        "needs_review": len(buckets["needs_review"]),
        "rejected": len(buckets["rejected"]),
        "duplicates_dropped": duplicates,
    }


def selftest() -> int:
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    from _common.extract import extract
    from cds_cap_pipeline import build_candidate

    # --- Offline integration check (always runs; proves the wiring + guardrails) ---
    print("Offline integration (synthetic FL opinion):")
    synthetic = {
        "source": "courtlistener",
        "jurisdiction": "Florida",
        "name_abbreviation": "Doe v. Roe",
        "year": 2019,
        "official_citation": "courtlistener:999999",
        "full_text_url": f"{CL_API}/opinions/999999/",
        "source_url": f"{CL_BASE}/opinion/999999/doe-v-roe/",
        "text_sha256": "a" * 64,
        "fetched_at": "2026-06-24T00:00:00+00:00",
        "opinion_text": ("The jury returned a verdict awarding the plaintiff $850,000 in damages "
                         "for cervical spine injuries sustained in the motor vehicle accident caused "
                         "by the defendant's negligence."),
    }
    c = build_candidate(synthetic)
    check("synthetic routes accepted", c["status"] == "accepted")
    check("amount captured (no fabrication path)", c["exact_outcome_amount"] == 850_000)
    check("snippet provenance present", bool(c["amount_snippet"]) and "850,000" in c["amount_snippet"])
    check("provenance carried (source_url + sha256)", bool(c["source_url"]) and len(c["text_sha256"]) == 64)

    non_pi = dict(synthetic, official_citation="courtlistener:888888",
                  opinion_text="Appeal from an order denying a motion to vacate under the rule of criminal procedure.")
    cn = build_candidate(non_pi)
    check("non-PI rejected, no fabricated $", cn["status"] == "rejected" and cn["exact_outcome_amount"] is None)

    # --- Live check (skips gracefully if the API/key is unavailable) ---
    print("Live CourtListener FL/CA fetch:")
    key = _load_api_key()
    if not key:
        print("  [SKIP] no COURTLISTENER_API_KEY in env — live fetch skipped (offline checks stand)")
    else:
        recs = []
        try:
            with Fetcher(min_delay=0.5) as f:
                recs = list(fetch_state_cases(f, ["Florida", "California"],
                                              query="personal injury negligence",
                                              max_cases=6, api_key=key))
        except Exception as e:
            print(f"  [SKIP] live fetch error ({str(e)[:80]}) — offline checks stand")
            recs = None

        if recs is not None:
            print(f"  fetched {len(recs)} CourtListener FL/CA records")
            check("got live records", len(recs) >= 1)
            if recs:
                check("all FL/CA", all(r["jurisdiction"] in ("Florida", "California") for r in recs))
                check("provenance on every record",
                      all(r.get("source_url") and r.get("full_text_url")
                          and len(r.get("text_sha256", "")) == 64 and r.get("fetched_at") for r in recs))
                check("opinion_text non-empty", all(len(r.get("opinion_text", "")) > 50 for r in recs))
                check("source tagged courtlistener", all(r["source"] == "courtlistener" for r in recs))
                # Zero fabrication: extractor must not invent $ on non-PI opinions.
                hallucinated = sum(1 for r in recs
                                   if (not extract(r["opinion_text"]).is_pi)
                                   and extract(r["opinion_text"]).amount is not None)
                check("no fabricated $ on non-PI opinions", hallucinated == 0)
                # Integration: every record flows through the shared pipeline.
                statuses = [build_candidate(r)["status"] for r in recs]
                print(f"  pipeline statuses: {statuses}")
                check("pipeline processed all records", len(statuses) == len(recs))
                check("accepted rows (if any) carry $ + snippet + provenance",
                      all(bool(build_candidate(r)["exact_outcome_amount"]) and bool(build_candidate(r)["amount_snippet"])
                          for r in recs if build_candidate(r)["status"] == "accepted"))

    if failures:
        print(f"\nRESULT: FAILED ({len(failures)}) -> {failures}")
        return 1
    print("\nRESULT: ALL CHECKS PASSED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="CourtListener FL/CA opinion adapter (pipeline-routed)")
    ap.add_argument("--states", nargs="+", default=["Florida", "California"])
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--max", type=int, default=40)
    ap.add_argument("--start-date", dest="filed_after", default=None, help="filed_after YYYY-MM-DD")
    ap.add_argument("--end-date", dest="filed_before", default=None, help="filed_before YYYY-MM-DD")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    summary = run(
        args.states,
        query=args.query,
        max_cases=args.max,
        filed_after=args.filed_after,
        filed_before=args.filed_before,
        out_dir=Path(args.out_dir) if args.out_dir else None,
    )
    print(json.dumps(summary, indent=2))
    print("\nNext: load accepted/needs_review into the review queue, e.g.")
    label = "_".join(s.lower() for s in args.states) or "all"
    print(f"  python cds_cap_loader.py --in out/courtlistener_{label}_accepted.jsonl --dry-run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
