"""
cds_morelaw.py — MoreLaw.com verdict adapter (Level 0/1, free, FL/CA, real $ amounts).

MoreLaw publishes free verdict/case write-ups. Subject tagging is NOISY (the
"personal_injury" subject page contains mislabeled criminal cases), so EVERY case
is run through the shared PI extractor downstream, which abstains on non-PI
(zero-fabrication guardrail). State is taken reliably from the detail URL (/FL/, /CA/).

This adapter yields normalized records with the SAME keys the CAP pipeline consumes
(cds_cap_pipeline.build_candidate), so MoreLaw flows through the same
validate -> score -> dedup -> route -> loader path.

Run:
    python cds_morelaw.py --states Florida California --max 20 --out out/morelaw_fl_ca.jsonl
    python cds_morelaw.py --selftest
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterator, Optional

from bs4 import BeautifulSoup

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from _common.fetcher import Fetcher  # noqa: E402

MORELAW_BASE = "https://www.morelaw.com"
OUT_DIR = Path(__file__).parent / "out"

# PI-relevant subject slugs on MoreLaw (/cases/<slug>/). Noisy — extractor filters.
PI_SUBJECTS = [
    "personal_injury", "auto_negligence", "car_wreck", "motor_vehicle",
    "medical_malpractice", "premises_liability", "slip_and_fall", "wrongful_death",
    "product_liability", "products_liability", "truck_wrecks", "negligence",
    "dram_shop", "nursing", "semi-tractor_trailer", "uninsured_motorist",
]
STATE_NAME = {"FL": "Florida", "CA": "California"}
NAME_TO_CODE = {v: k for k, v in STATE_NAME.items()}

_LINK_RE = re.compile(r'/verdicts/[^"\']*?/([A-Z]{2})/(\d+)/')


def iter_listing(f: Fetcher, subject: str, max_pages: int = 3) -> list[dict]:
    """Parse a subject listing across pages -> entries {path, state, id, year, listing_amount}."""
    entries: list[dict] = []
    seen_ids: set[str] = set()
    for page in range(1, max_pages + 1):
        url = f"{MORELAW_BASE}/cases/{subject}/" + (f"?page={page}" if page > 1 else "")
        try:
            html = f.get_text(url).text()
        except Exception:
            break
        page_ids_before = len(seen_ids)
        for m in _LINK_RE.finditer(html):
            state, cid = m.group(1), m.group(2)
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            tail = html[m.end(): m.end() + 220]
            dm = re.search(r"\$(\d*)\s*\((\d{2})-(\d{2})-(\d{4})", tail)
            year = int(dm.group(4)) if dm else None
            listing_amount = (float(dm.group(1)) if dm and dm.group(1) else None)
            entries.append({
                "path": m.group(0),
                "state": state,
                "id": cid,
                "year": year,
                "listing_amount": listing_amount,
            })
        # stop if a page added nothing new
        if len(seen_ids) == page_ids_before:
            break
    return entries


def _focus_narrative(full: str) -> str:
    """Narrative after 'Description:' (drops nav/footer noise), guaranteeing the
    structured result field (Outcome/Verdict/Settlement/Judgment/Award) stays in view.

    MoreLaw states the result in a structured field, e.g.
    "Outcome: Plaintiff's verdict for $76 million." On long write-ups that field can
    fall past the 8000-char window — which would hide the clean, sourced dollar amount
    from the shared extractor and wrongly route the case to needs_review. The appended
    snippet is real page text, so this aids capture without fabricating anything.
    """
    idx = full.find("Description:")
    body = full[idx + len("Description:"):] if idx >= 0 else full
    text = body[:8000].strip()
    om = re.search(r"(?:Outcome|Verdict|Settlement|Judgment|Award)\s*:\s*.{0,400}", body, re.IGNORECASE)
    if om and om.group(0) not in text:
        text = f"{text} {om.group(0)}".strip()
    return text


def fetch_detail(f: Fetcher, path: str) -> tuple[Optional[str], str, object]:
    res = f.get_text(MORELAW_BASE + path)
    soup = BeautifulSoup(res.text(), "lxml")
    heading_el = soup.find(["h1", "h2"])
    name = heading_el.get_text(strip=True) if heading_el else None
    full = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    text = _focus_narrative(full)
    return name, text, res


def fetch_state_cases(
    f: Fetcher,
    states: list[str],
    subjects: Optional[list[str]] = None,
    max_cases: int = 25,
    max_pages: int = 3,
) -> Iterator[dict]:
    subjects = subjects or PI_SUBJECTS
    want_codes = {NAME_TO_CODE[s] for s in states if s in NAME_TO_CODE}
    count = 0
    seen: set[str] = set()
    for subject in subjects:
        if count >= max_cases:
            break
        for entry in iter_listing(f, subject, max_pages=max_pages):
            if count >= max_cases:
                break
            if entry["state"] not in want_codes or entry["id"] in seen:
                continue
            seen.add(entry["id"])
            name, text, res = fetch_detail(f, entry["path"])
            if not text:
                continue
            count += 1
            yield {
                "source": "morelaw",
                "jurisdiction": STATE_NAME[entry["state"]],
                "name_abbreviation": name,
                "year": entry["year"],
                "official_citation": f"morelaw:{entry['id']}",
                "docket_subject": subject,
                "full_text_url": MORELAW_BASE + entry["path"],
                "source_url": MORELAW_BASE + entry["path"],
                "text_sha256": res.sha256,
                "fetched_at": res.fetched_at,
                "opinion_text": text,
                "listing_amount": entry["listing_amount"],
            }


def selftest() -> int:
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    from _common.extract import extract
    from cds_cap_pipeline import build_candidate

    # Offline: the structured result field is recovered even when it falls past the
    # 8000-char narrative window (prevents false 'needs_review' on long write-ups).
    print("Outcome-field recovery (offline, long write-up):")
    long_full = ("Description: " + ("plaintiff negligence motor vehicle accident injury " * 250)
                 + " Outcome: Plaintiff's verdict for $2,500,000 in damages.")
    focused = _focus_narrative(long_full)
    naive = long_full[long_full.find("Description:") + len("Description:"):][:8000]
    check("naive 8000-slice would drop the Outcome amount", extract(naive).amount is None)
    check("focused narrative recovers the sourced Outcome amount", extract(focused).amount == 2_500_000)
    check("recovered amount carries a real snippet (no fabrication)",
          bool(extract(focused).amount_snippet) and "2,500,000" in extract(focused).amount_snippet)

    with Fetcher(min_delay=1.0) as f:
        recs = list(fetch_state_cases(f, ["Florida", "California"],
                                      subjects=["personal_injury", "auto_negligence", "wrongful_death"],
                                      max_cases=6, max_pages=2))
    print(f"  fetched {len(recs)} MoreLaw FL/CA records")
    check("got records", len(recs) >= 1)
    check("all FL/CA", all(r["jurisdiction"] in ("Florida", "California") for r in recs))
    check("provenance on every record", all(r.get("source_url") and len(r.get("text_sha256", "")) == 64 and r.get("fetched_at") for r in recs))
    check("opinion_text non-empty", all(len(r.get("opinion_text", "")) > 50 for r in recs))
    check("source tagged morelaw", all(r["source"] == "morelaw" for r in recs))
    check("dedup id present", all(r["official_citation"].startswith("morelaw:") for r in recs))

    # Integrity: extractor must not fabricate $ on non-PI MoreLaw cases.
    hallucinated = sum(1 for r in recs if (not extract(r["opinion_text"]).is_pi) and extract(r["opinion_text"]).amount is not None)
    check("no fabricated $ on non-PI cases", hallucinated == 0)

    # Integration: records flow through the shared pipeline candidate builder.
    statuses = []
    for r in recs:
        c = build_candidate(r)
        statuses.append(c["status"])
        if c["status"] == "accepted":
            check(f"accepted row has $ + snippet + provenance ({r['official_citation']})",
                  bool(c["exact_outcome_amount"]) and bool(c["amount_snippet"]) and bool(c["source_url"]))
    print(f"  pipeline statuses: {statuses}")
    check("pipeline processed all records", len(statuses) == len(recs))

    if failures:
        print(f"\nRESULT: FAILED ({len(failures)}) -> {failures}")
        return 1
    print("\nRESULT: ALL CHECKS PASSED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="MoreLaw FL/CA verdict adapter")
    ap.add_argument("--states", nargs="+", default=["Florida", "California"])
    ap.add_argument("--subjects", nargs="+", default=None)
    ap.add_argument("--max", type=int, default=25)
    ap.add_argument("--max-pages", type=int, default=3)
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else OUT_DIR / "morelaw_fl_ca.jsonl"
    n = 0
    with Fetcher(min_delay=1.0) as f, out_path.open("w", encoding="utf-8") as fh:
        for rec in fetch_state_cases(f, args.states, subjects=args.subjects, max_cases=args.max, max_pages=args.max_pages):
            fh.write(json.dumps(rec, default=str) + "\n")
            n += 1
    print(f"Wrote {n} MoreLaw records -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
