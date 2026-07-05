"""
cds_morelaw_crawl.py — Long-running MoreLaw PI crawler (one source, all target states).

MoreLaw is organized by NATIONAL subject pages (not by state), so this is a single
crawler (not one-per-state): running 11 would re-fetch the same pages and hammer the
site. Its one task: walk MoreLaw's personal-injury subjects, take cases from the target
states (state read from the /XX/ URL code), skip criminal write-ups, classify every case
through the shared zero-fabrication pipeline (cds_cap_pipeline.build_candidate), and APPEND
accepted+needs_review to out/morelaw_crawl/morelaw_<state>_<status>.jsonl. Resumable: it
checkpoints finished subjects + seen case ids. Polite: one connection, paced.

It does NO classification of its own — all PI/$ judgment is the shared deterministic
extractor's, so it cannot fabricate; every record carries full provenance.

Run:
    python cds_morelaw_crawl.py --hours 720 --min-delay 1.5
    python cds_morelaw_crawl.py --hours 0.05 --min-delay 0.5 --max-cases 3   # smoke test
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_FACTORY_ROOT = _HERE.parent
for _p in (_FACTORY_ROOT, _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from _common.fetcher import Fetcher  # noqa: E402
import cds_morelaw as ml  # noqa: E402
from cds_cap_pipeline import build_candidate  # noqa: E402

OUT_DIR = _HERE / "out" / "morelaw_crawl"

# Target states (all 50 US states + DC) -> MoreLaw 2-letter URL codes.
STATE_FROM_CODE = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

# Curated personal-injury subjects (validated as productive during the FL harvest, incl.
# the verdict/damages-procedure ones that surface quantified awards).
PI_SUBJECTS = [
    "personal_injury", "auto_negligence", "car_wreck", "motor_vehicle", "medical_malpractice",
    "premises_liability", "slip_and_fall", "wrongful_death", "product_liability",
    "products_liability", "truck_wrecks", "negligence", "dram_shop", "nursing",
    "semi-tractor_trailer", "uninsured_motorist", "mesothelioma", "toxic_tort", "plane_crash",
    "pharmacy", "strict_liability", "negligent_hiring", "imputed_negligence", "intentional_tort",
    "assault", "sexual_assault", "sexual_abuse", "child_abuse", "failure_to_warn",
    "loss_of_consortium", "railroad", "workers_compensation", "federal_tort_claims", "invokana",
    "standard_of_care", "res_ipsa_loquitur", "respondeat_superior", "last_clear_chance",
    "sudden_emergency", "invitee", "licensee", "proximate_cause", "reasonable_care",
    "excessive_force", "false_arrest", "false_imprisonment", "malicious_prosecution",
    "health_care", "daubert", "remittitur", "judgment_notwithstanding_verdict",
    "punitive_damages", "nuisance",
]


def _state_slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _load_ckpt(ckpt: Path) -> dict:
    if ckpt.exists():
        try:
            return json.loads(ckpt.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"done_subjects": [], "seen_ids": [], "counts": {"accepted": 0, "needs_review": 0, "rejected": 0},
            "started_at": None, "last_at": None}


def _save_ckpt(ckpt: Path, ck: dict) -> None:
    tmp = ckpt.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(ck, default=str), encoding="utf-8")
    tmp.replace(ckpt)


def main() -> int:
    ap = argparse.ArgumentParser(description="MoreLaw PI crawler (single source, target states)")
    ap.add_argument("--hours", type=float, default=720.0)
    ap.add_argument("--min-delay", type=float, default=1.5, help="Seconds between requests (politeness)")
    ap.add_argument("--max-pages", type=int, default=60, help="Listing pages to scan per subject")
    ap.add_argument("--max-cases", type=int, default=0, help="0 = unlimited (until --hours / corpus end)")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ckpt = OUT_DIR / "checkpoint.json"
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(OUT_DIR / "crawl.log", encoding="utf-8"), logging.StreamHandler()],
    )
    log = logging.getLogger("morelaw_crawl")

    ck = _load_ckpt(ckpt)
    done = set(ck.get("done_subjects", []))
    seen = set(ck.get("seen_ids", []))
    counts = ck.get("counts", {"accepted": 0, "needs_review": 0, "rejected": 0})
    ck["started_at"] = ck.get("started_at") or time.strftime("%Y-%m-%dT%H:%M:%S")
    deadline = time.time() + args.hours * 3600
    processed = 0

    def _append(state: str, status: str, row: dict) -> None:
        with (OUT_DIR / f"morelaw_{_state_slug(state)}_{status}.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")

    log.info("MoreLaw crawl start | subjects=%d states=%s min_delay=%ss hours=%s done_subjects=%d seen=%d",
             len(PI_SUBJECTS), ",".join(STATE_FROM_CODE), args.min_delay, args.hours, len(done), len(seen))

    with Fetcher(min_delay=args.min_delay, use_cache=False) as f:
        for subject in PI_SUBJECTS:
            if time.time() >= deadline or (args.max_cases and processed >= args.max_cases):
                break
            if subject in done:
                continue
            try:
                entries = ml.iter_listing(f, subject, max_pages=args.max_pages)
            except Exception as e:
                log.warning("listing %s failed: %s", subject, str(e)[:80])
                continue
            for entry in entries:
                if time.time() >= deadline or (args.max_cases and processed >= args.max_cases):
                    break
                state = STATE_FROM_CODE.get(entry.get("state"))
                cid = str(entry.get("id"))
                if state is None or cid in seen:
                    continue
                try:
                    name, text, res = ml.fetch_detail(f, entry["path"])
                except Exception as e:
                    log.warning("detail %s failed: %s", entry.get("path"), str(e)[:60])
                    continue
                seen.add(cid)
                if not text or ml._looks_criminal(name, text):
                    continue
                rec = {
                    "source": "morelaw",
                    "jurisdiction": state,
                    "name_abbreviation": name,
                    "year": entry.get("year"),
                    "official_citation": f"morelaw:{cid}",
                    "docket_subject": subject,
                    "full_text_url": ml.MORELAW_BASE + entry["path"],
                    "source_url": ml.MORELAW_BASE + entry["path"],
                    "text_sha256": res.sha256,
                    "fetched_at": res.fetched_at,
                    "opinion_text": text,
                }
                cand = build_candidate(rec)
                st = cand["status"]
                counts[st] = counts.get(st, 0) + 1
                processed += 1
                if st in ("accepted", "needs_review"):
                    _append(state, st, cand)
                ck.update(done_subjects=sorted(done), seen_ids=sorted(seen), counts=counts,
                          last_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
                _save_ckpt(ckpt, ck)
                log.info("[%d] %-12s %s (%s) acc=%d nr=%d rej=%d",
                         processed, st, rec["official_citation"], state,
                         counts.get("accepted", 0), counts.get("needs_review", 0), counts.get("rejected", 0))
            done.add(subject)
            ck.update(done_subjects=sorted(done), seen_ids=sorted(seen), counts=counts,
                      last_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
            _save_ckpt(ckpt, ck)
            log.info("subject done: %s | seen=%d acc=%d nr=%d rej=%d", subject, processed,
                     counts.get("accepted", 0), counts.get("needs_review", 0), counts.get("rejected", 0))

    completed = time.time() < deadline and not (args.max_cases and processed >= args.max_cases)
    if completed:
        (OUT_DIR / "COMPLETE").write_text(time.strftime("%Y-%m-%dT%H:%M:%S"), encoding="utf-8")
        log.info("MoreLaw crawl COMPLETE (all subjects exhausted)")
    log.info("MoreLaw crawl done | processed=%d counts=%s", processed, json.dumps(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
