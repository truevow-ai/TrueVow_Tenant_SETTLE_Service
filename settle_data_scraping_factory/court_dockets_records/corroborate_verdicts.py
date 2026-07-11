"""
corroborate_verdicts.py — Multi-source corroboration cross-check.

Machine substitute for human verification (there is no qualified human verifier
yet). A verdict is promoted review_status pending -> verified ONLY when the same
real case appears in >=2 INDEPENDENT sources that AGREE on the outcome amount.
Nothing is guessed; promotion requires genuine cross-source agreement, and the
corroborating evidence (which sources, which URLs) is recorded so every
'verified' row is auditable.

Independent sources are distinguished by source_url host:
    static.case.law (Caselaw Access Project) | courtlistener.com | morelaw.com

Match keys (conservative, to avoid false merges):
  1. Exact official_citation (a reporter cite like "273 So. 3d 63") shared by
     two different hosts — strongest signal.
  2. Normalized case name + state + same amount bucket — secondary, used when a
     source (e.g. MoreLaw) has no reporter citation.

Amounts must agree within 1% (rounding/format tolerance) to count as agreement.

Usage:
    python corroborate_verdicts.py --dry-run
    python corroborate_verdicts.py            # promote agreeing verdicts
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv

load_dotenv(".env.local")
DB_URL = (os.getenv("SETTLE_DATABASE_URL") or "").rstrip("/")
DB_KEY = os.getenv("SETTLE_DATABASE_SERVICE_ROLE_KEY") or os.getenv("SETTLE_DATABASE_API_SECRET_KEY")

_HOST_TO_SOURCE = {
    "static.case.law": "caselaw_access_project",
    "www.courtlistener.com": "courtlistener",
    "courtlistener.com": "courtlistener",
    "www.morelaw.com": "morelaw",
    "morelaw.com": "morelaw",
}

_CITATION_NOISE = re.compile(r"[^a-z0-9]+")


def _headers(extra=None):
    h = {"apikey": DB_KEY, "Authorization": f"Bearer {DB_KEY}", "Content-Type": "application/json"}
    if extra:
        h.update(extra)
    return h


def _source_of(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return None
    return _HOST_TO_SOURCE.get(host)


def _norm_name(name: str | None) -> str:
    if not name:
        return ""
    n = name.lower()
    n = re.sub(r"\b(et\.? al\.?|inc\.?|llc|co\.?|corp\.?|ltd\.?|the)\b", " ", n)
    n = re.sub(r"[^a-z0-9]+", " ", n).strip()
    return n


def _norm_citation(cit: str | None) -> str | None:
    if not cit:
        return None
    c = cit.strip().lower()
    if c.startswith("morelaw:") or c.startswith("courtlistener:"):
        return None  # internal ids are not cross-source citations
    c = _CITATION_NOISE.sub(" ", c).strip()
    # Must look like a reporter cite: contains a volume number + reporter + page.
    return c if re.search(r"\d+\s+[a-z].*\d+", c) else None


def _state_of(juris: str | None) -> str:
    if not juris:
        return ""
    return juris.rsplit(",", 1)[-1].strip().lower()


def _amount(v: dict) -> float | None:
    return v.get("total_verdict") or v.get("settlement_amount")


def _amounts_agree(a: float, b: float) -> bool:
    if a is None or b is None:
        return False
    hi = max(a, b)
    return hi > 0 and abs(a - b) / hi <= 0.01


def fetch_all(client: httpx.Client) -> list[dict]:
    rows, off = [], 0
    # official_citation is NOT a top-level column — it lives in source_notes
    # JSON, which _citation() parses. Select only real columns.
    cols = ("id,case_name,jurisdiction,source_url,total_verdict,"
            "settlement_amount,outcome_type,review_status,source_notes")
    while True:
        d = client.get(f"{DB_URL}/rest/v1/settle_verdicts?select={cols}&limit=1000&offset={off}",
                       headers=_headers(), timeout=60).json()
        if not isinstance(d, list):
            raise RuntimeError(f"fetch error: {d}")
        if not d:
            break
        rows += d
        if len(d) < 1000:
            break
        off += 1000
    return rows


def _citation(v: dict) -> str | None:
    # official_citation lives in source_notes JSON.
    if v.get("source_notes"):
        try:
            return json.loads(v["source_notes"]).get("official_citation")
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def find_corroborated(rows: list[dict]) -> dict[str, dict]:
    """Return {verdict_id: {count, sources[]}} for verdicts corroborated by
    >=2 independent sources agreeing on amount."""
    # Build groups by citation and by name+state.
    by_cit: dict[str, list[dict]] = defaultdict(list)
    by_name: dict[tuple, list[dict]] = defaultdict(list)
    for v in rows:
        v["_source"] = _source_of(v.get("source_url"))
        v["_amount"] = _amount(v)
        cit = _norm_citation(_citation(v))
        if cit:
            by_cit[cit].append(v)
        nm = _norm_name(v.get("case_name"))
        if nm:
            by_name[(nm, _state_of(v.get("jurisdiction")))].append(v)

    result: dict[str, dict] = {}

    def _corroborate(group: list[dict], key_kind: str):
        # Need >=2 DISTINCT sources that agree on amount.
        for v in group:
            if v["_amount"] is None or v["_source"] is None:
                continue
            agreeing = {}
            for w in group:
                if w["_source"] is None or w["_amount"] is None:
                    continue
                if _amounts_agree(v["_amount"], w["_amount"]):
                    agreeing.setdefault(w["_source"], w)
            if len(agreeing) >= 2:
                info = result.get(v["id"])
                srcs = sorted(agreeing.keys())
                if not info or len(srcs) > info["count"]:
                    result[v["id"]] = {
                        "count": len(srcs),
                        "sources": srcs,
                        "match_key": key_kind,
                        "evidence": [{"source": s, "url": w.get("source_url"),
                                      "amount": w["_amount"]} for s, w in agreeing.items()],
                    }

    for cit, group in by_cit.items():
        if len({v["_source"] for v in group if v["_source"]}) >= 2:
            _corroborate(group, "official_citation")
    for key, group in by_name.items():
        if len({v["_source"] for v in group if v["_source"]}) >= 2:
            _corroborate(group, "name_state_amount")

    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Multi-source verdict corroboration")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not (DB_URL and DB_KEY):
        print("ERROR: DB creds missing")
        return 1

    with httpx.Client(timeout=120) as c:
        rows = fetch_all(c)
        print(f"scanned {len(rows)} verdicts")
        corr = find_corroborated(rows)
        by_count = defaultdict(int)
        for info in corr.values():
            by_count[info["count"]] += 1
        print(f"corroborated by >=2 independent sources: {len(corr)}")
        print(f"  by source count: {dict(by_count)}")
        by_key = defaultdict(int)
        for info in corr.values():
            by_key[info["match_key"]] += 1
        print(f"  by match key: {dict(by_key)}")

        # sample
        for vid, info in list(corr.items())[:5]:
            print(f"  {vid[:8]}  x{info['count']} {info['sources']} via {info['match_key']}")

        if args.dry_run:
            print("\nDRY-RUN: no promotions written.")
            return 0

        promoted = 0
        for vid, info in corr.items():
            payload = json.dumps({
                "review_status": "verified",
                "corroboration_count": info["count"],
                "corroborating_sources": info["evidence"],
            }, default=str)
            r = c.patch(f"{DB_URL}/rest/v1/settle_verdicts?id=eq.{vid}",
                        headers=_headers({"Prefer": "return=minimal"}), content=payload)
            if r.status_code < 300:
                promoted += 1
            else:
                print(f"  promote {vid[:8]} HTTP {r.status_code}: {r.text[:120]}")
        print(f"\nPROMOTED {promoted} verdicts to review_status='verified' (multi-source corroborated).")
        return 0


if __name__ == "__main__":
    sys.exit(main())
