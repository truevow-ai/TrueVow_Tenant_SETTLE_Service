"""
recover_rejects.py — Re-verify rejected / quarantined verdict records against
their original sources and recover any that now legitimately pass the gates.

Recovery NEVER lowers the bar. A rejected record is recovered ONLY if, after
re-fetching its source and re-enriching, it passes BOTH gates:
    1. no_fabrication_gate.verify_record  (verbatim evidence + provenance)
    2. verdict_validator.normalize_and_validate  (enums/format/bounds)

This is the counterpart to the prime directive: the gate strips fabricated data,
but honest data that was rejected due to a stale/missing snippet (e.g. before
snippet-capture existed) can be legitimately recovered once real evidence is
re-fetched. Nothing is guessed.

Reads every *.rejects.jsonl under out/, attempts recovery, and writes:
    out/<file>.recovered.jsonl   — records that now pass (ready to load)
    out/recovery_report.json     — counts + per-reason breakdown

Usage:
    python recover_rejects.py --dry-run          # report only, no re-fetch
    python recover_rejects.py                     # re-fetch + re-verify
    python recover_rejects.py --limit 500         # cap re-fetches (API budget)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for _p in (str(_HERE), str(_HERE.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _common.fetcher import Fetcher  # noqa: E402
from cds_enrich_offline import enrich_candidate  # noqa: E402
from no_fabrication_gate import verify_record  # noqa: E402
from verdict_validator import normalize_and_validate  # noqa: E402
from cds_cap_loader import map_candidate_to_verdict  # noqa: E402

OUT = _HERE / "out"


def _reject_files() -> list[Path]:
    return sorted(
        p for p in OUT.rglob("*.rejects.jsonl")
        if ".recovered." not in p.name and p.stat().st_size > 0
    )


def _original_record(entry: dict) -> dict:
    """A rejects entry stores the (possibly mapped) record under 'record'."""
    return entry.get("record") or entry


def _passes_both_gates(candidate: dict) -> tuple[bool, dict | None]:
    gate = verify_record(candidate)
    if gate["rejected"]:
        return False, None
    m = map_candidate_to_verdict(gate["record"])
    m["validation_counts"] = gate["validation_counts"]
    m["validated_field_count"] = gate["validated_total"]
    m["field_evidence"] = gate["evidence"]
    clean, errors, _ = normalize_and_validate(m)
    return (clean is not None), clean


def recover(dry_run: bool, limit: int) -> dict:
    files = _reject_files()
    report: dict = {
        "reject_files": len(files),
        "examined": 0,
        "recovered_without_refetch": 0,
        "recovered_after_refetch": 0,
        "still_unrecoverable": 0,
        "reasons_remaining": Counter(),
    }
    refetched = 0

    fetcher = None if dry_run else Fetcher(min_delay=0.3)
    try:
        for f in files:
            recovered_rows = []
            for line in f.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line:
                    continue
                report["examined"] += 1
                entry = json.loads(line)
                rec = _original_record(entry)

                # 1. Does it pass now, as-is? (e.g. gate/enricher improved.)
                ok, clean = _passes_both_gates(rec)
                if ok:
                    report["recovered_without_refetch"] += 1
                    recovered_rows.append(clean)
                    continue

                # 2. Re-fetch source + re-enrich, then re-check.
                if not dry_run and rec.get("full_text_url") or rec.get("source_url"):
                    if limit and refetched >= limit:
                        report["still_unrecoverable"] += 1
                        for r in entry.get("errors", []):
                            report["reasons_remaining"][r] += 1
                        continue
                    try:
                        enriched = enrich_candidate(dict(rec), f=fetcher)
                        refetched += 1
                        ok2, clean2 = _passes_both_gates(enriched)
                        if ok2:
                            report["recovered_after_refetch"] += 1
                            recovered_rows.append(clean2)
                            continue
                    except Exception:
                        pass

                report["still_unrecoverable"] += 1
                for r in entry.get("errors", []):
                    report["reasons_remaining"][r] += 1

            if recovered_rows and not dry_run:
                out_path = f.with_suffix(".recovered.jsonl")
                out_path.write_text(
                    "\n".join(json.dumps(r, default=str) for r in recovered_rows), encoding="utf-8")
    finally:
        if fetcher:
            fetcher.close()

    report["reasons_remaining"] = dict(report["reasons_remaining"].most_common(15))
    report["total_recovered"] = (report["recovered_without_refetch"]
                                 + report["recovered_after_refetch"])
    if not dry_run:
        (OUT / "recovery_report.json").write_text(
            json.dumps(report, indent=2, default=str), encoding="utf-8")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Recover rejected records that now pass the gates")
    ap.add_argument("--dry-run", action="store_true",
                    help="Only re-check as-is (no source re-fetch)")
    ap.add_argument("--limit", type=int, default=0, help="Max source re-fetches (0=unlimited)")
    args = ap.parse_args()
    report = recover(dry_run=args.dry_run, limit=args.limit)
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
