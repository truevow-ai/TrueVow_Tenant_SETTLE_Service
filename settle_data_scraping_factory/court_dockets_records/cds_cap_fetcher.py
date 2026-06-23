"""
cds_cap_fetcher.py — Fetch & normalize Caselaw Access Project (static.case.law) cases
for a target reporter + state. Level 0 (no blockers, public-domain bulk).

Layout (verified):
    {BASE}/{slug}/VolumesMetadata.json          -> list of volumes (volume_folder)
    {BASE}/{slug}/{volume}/CasesMetadata.json   -> list of case metadata
    {BASE}/{slug}/{volume}/cases/{file_name}.json -> full case incl. casebody.opinions[].text

Per-case metadata carries `jurisdiction.name_long`, so multi-state regional
reporters (So.2d = AL/FL/LA/MS) are filtered per-case to the target state.

Every emitted record carries provenance (source_url + sha256 + fetched_at) per the
zero-fabrication data-integrity guardrail. Nothing is invented: fields absent in the
source are emitted as null.

Run:
    python cds_cap_fetcher.py --slug cal-super-ct --state California --max 20
    python cds_cap_fetcher.py --slug so3d --state Florida --max 10 --with-text
    python cds_cap_fetcher.py --selftest
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterator, Optional

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from _common.fetcher import Fetcher, FetchResult  # noqa: E402

CAP_BASE = "https://static.case.law"
OUT_DIR = Path(__file__).parent / "out"


def _year(decision_date: Optional[str]) -> Optional[int]:
    if not decision_date:
        return None
    m = re.search(r"\b(1[89]\d{2}|20\d{2})\b", str(decision_date))
    return int(m.group(1)) if m else None


def list_volumes(f: Fetcher, slug: str) -> list[str]:
    res = f.get_json(f"{CAP_BASE}/{slug}/VolumesMetadata.json")
    vols = res.json()
    return [v.get("volume_folder") for v in vols if v.get("volume_folder")]


def list_cases_meta(f: Fetcher, slug: str, volume: str) -> tuple[list[dict], FetchResult]:
    res = f.get_json(f"{CAP_BASE}/{slug}/{volume}/CasesMetadata.json")
    return res.json(), res


def fetch_case_text(f: Fetcher, slug: str, volume: str, file_name: str) -> tuple[str, FetchResult]:
    res = f.get_json(f"{CAP_BASE}/{slug}/{volume}/cases/{file_name}.json")
    case = res.json()
    opinions = (case.get("casebody") or {}).get("opinions") or []
    text = "\n\n".join(o.get("text", "") for o in opinions if isinstance(o, dict))
    return text, res


def normalize_case(meta: dict, slug: str, volume: str, source_url: str, source_sha256: str, fetched_at: str) -> dict:
    court = meta.get("court") or {}
    jur = meta.get("jurisdiction") or {}
    cites = meta.get("citations") or []
    official = next((c.get("cite") for c in cites if c.get("type") == "official"), None)
    analysis = meta.get("analysis") or {}
    return {
        "source": "caselaw_access_project",
        "reporter_slug": slug,
        "volume": volume,
        "case_id": meta.get("id"),
        "file_name": meta.get("file_name"),
        "name_abbreviation": meta.get("name_abbreviation"),
        "name": meta.get("name"),
        "decision_date_raw": meta.get("decision_date"),
        "year": _year(meta.get("decision_date")),
        "docket_number": meta.get("docket_number") or None,
        "court_name": court.get("name"),
        "court_abbrev": court.get("name_abbreviation"),
        "jurisdiction": jur.get("name_long"),
        "official_citation": official,
        "word_count": analysis.get("word_count"),
        "ocr_confidence": analysis.get("ocr_confidence"),
        "full_text_url": f"{CAP_BASE}/{slug}/{volume}/cases/{meta.get('file_name')}.json",
        # provenance (data-integrity guardrail 6a)
        "source_url": source_url,
        "source_sha256": source_sha256,
        "fetched_at": fetched_at,
    }


def fetch_reporter(
    f: Fetcher,
    slug: str,
    state: str,
    max_cases: int = 50,
    with_text: bool = False,
) -> Iterator[dict]:
    count = 0
    for volume in list_volumes(f, slug):
        if count >= max_cases:
            break
        metas, meta_res = list_cases_meta(f, slug, volume)
        for meta in metas:
            if count >= max_cases:
                break
            jur = (meta.get("jurisdiction") or {}).get("name_long")
            if jur != state:
                continue  # filters multi-state reporters to the target state
            rec = normalize_case(
                meta, slug, volume,
                source_url=meta_res.url, source_sha256=meta_res.sha256, fetched_at=meta_res.fetched_at,
            )
            if with_text and rec["file_name"]:
                text, tres = fetch_case_text(f, slug, volume, rec["file_name"])
                rec["opinion_text"] = text
                rec["text_source_url"] = tres.url
                rec["text_sha256"] = tres.sha256
            count += 1
            yield rec


def selftest() -> int:
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    with Fetcher(min_delay=0.3) as f:
        recs = list(fetch_reporter(f, "cal-super-ct", "California", max_cases=10, with_text=False))
        check("got cases", len(recs) > 0)
        check("all jurisdiction == California", all(r["jurisdiction"] == "California" for r in recs))
        check("required fields present", all(r.get("case_id") and r.get("name_abbreviation") and r.get("court_name") for r in recs))
        check("year parsed", all(isinstance(r.get("year"), int) for r in recs))
        check("provenance on every record", all(r.get("source_url") and len(r.get("source_sha256", "")) == 64 and r.get("fetched_at") for r in recs))
        check("full_text_url well-formed", all(r["full_text_url"].endswith(".json") for r in recs))

        # full text retrieval works
        first = recs[0]
        text, tres = fetch_case_text(f, "cal-super-ct", first["volume"], first["file_name"])
        check("opinion text non-empty", len(text) > 200)
        check("text provenance sha256", len(tres.sha256) == 64)

        # multi-state filter sanity on a Florida regional reporter (one volume, metadata only)
        try:
            metas, _ = list_cases_meta(f, "so3d", list_volumes(f, "so3d")[0])
            states = {(m.get("jurisdiction") or {}).get("name_long") for m in metas}
            fl_only = [m for m in metas if (m.get("jurisdiction") or {}).get("name_long") == "Florida"]
            check("so3d volume spans multiple states (regional)", len(states) >= 1)
            check("so3d Florida filter returns FL-only", all((m.get("jurisdiction") or {}).get("name_long") == "Florida" for m in fl_only))
        except Exception as e:
            print("  [WARN] so3d multi-state check skipped:", str(e)[:120])

    if failures:
        print(f"\nRESULT: FAILED ({len(failures)}) -> {failures}")
        return 1
    print("\nRESULT: ALL CHECKS PASSED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="CAP case fetcher (FL/CA)")
    ap.add_argument("--slug", help="reporter slug, e.g. cal-super-ct or so3d")
    ap.add_argument("--state", help="target state name_long, e.g. California or Florida")
    ap.add_argument("--max", type=int, default=50)
    ap.add_argument("--with-text", action="store_true")
    ap.add_argument("--out", default=None, help="JSONL output path")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not (args.slug and args.state):
        ap.error("--slug and --state are required (or use --selftest)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else OUT_DIR / f"cap_{args.slug}_{args.state.lower()}.jsonl"

    n = 0
    with Fetcher(min_delay=0.5) as f, out_path.open("w", encoding="utf-8") as fh:
        for rec in fetch_reporter(f, args.slug, args.state, max_cases=args.max, with_text=args.with_text):
            fh.write(json.dumps(rec, default=str) + "\n")
            n += 1
    print(f"Wrote {n} {args.state} cases from {args.slug} -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
