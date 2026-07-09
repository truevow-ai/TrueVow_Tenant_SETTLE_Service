"""
clean_carriers.py — Scrub invalid insurance_carrier values from existing JSONL.

The pre-2026-07-08 deterministic enricher used a greedy IGNORECASE regex that
captured sentence fragments (e.g. "withholds policy benefits in bad faith")
into the insurance_carrier field. This pass re-validates every existing
insurance_carrier value with _common.enrich.clean_carrier and drops/normalises
the bad ones — in place, no re-fetch, effectively free.

Usage:
    python clean_carriers.py --dry-run          # report only
    python clean_carriers.py                     # rewrite files in place
    python clean_carriers.py --selftest
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from _common.enrich import clean_carrier  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def clean_file(path: Path, dry_run: bool) -> dict:
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))

    total_with = 0
    kept = 0
    normalised = 0
    dropped = 0
    changed = False

    for r in rows:
        val = r.get("insurance_carrier")
        if not val:
            continue
        total_with += 1
        cleaned = clean_carrier(val)
        if cleaned is None:
            r.pop("insurance_carrier", None)
            dropped += 1
            changed = True
        elif cleaned != val:
            r["insurance_carrier"] = cleaned
            normalised += 1
            kept += 1
            changed = True
        else:
            kept += 1

    if changed and not dry_run:
        path.write_text(
            "\n".join(json.dumps(r, default=str) for r in rows), encoding="utf-8"
        )

    return {
        "file": str(path.relative_to(OUT)),
        "with_carrier": total_with,
        "kept": kept,
        "normalised": normalised,
        "dropped": dropped,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Scrub invalid insurance_carrier values")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        from _common.enrich import is_valid_carrier
        cases = [
            ("withholds policy benefits in bad faith", False),
            ("of Pittsburgh", False),
            ("had no such knowledge", False),
            ("GEICO", True),
            ("State Farm", True),
            ("Carolina Casualty Insurance Company", True),
            ("The Hartford", True),
        ]
        ok = True
        for text, expected in cases:
            got = is_valid_carrier(text)
            flag = "PASS" if got == expected else "FAIL"
            if got != expected:
                ok = False
            print(f"  [{flag}] is_valid_carrier({text!r}) -> {got} (want {expected})")
        print("\nRESULT:", "ALL CHECKS PASSED" if ok else "FAILED")
        return 0 if ok else 1

    files = sorted(
        p for p in OUT.rglob("*_enriched.jsonl")
        if ".enriched." not in p.name and p.stat().st_size > 0
    )
    files += sorted(p for p in OUT.rglob("*_exa*.jsonl") if p.stat().st_size > 0)

    totals = {"with_carrier": 0, "kept": 0, "normalised": 0, "dropped": 0}
    for p in files:
        r = clean_file(p, dry_run=args.dry_run)
        if r["dropped"] or r["normalised"]:
            print(f"  {r['file']}: with={r['with_carrier']} kept={r['kept']} "
                  f"normalised={r['normalised']} dropped={r['dropped']}")
        for k in totals:
            totals[k] += r[k]

    mode = "DRY-RUN" if args.dry_run else "APPLIED"
    print(f"\n[{mode}] {len(files)} files | with_carrier={totals['with_carrier']} "
          f"kept={totals['kept']} normalised={totals['normalised']} dropped={totals['dropped']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
