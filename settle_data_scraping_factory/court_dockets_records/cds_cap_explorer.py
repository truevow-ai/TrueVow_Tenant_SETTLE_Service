"""
cds_cap_explorer.py — Map the Caselaw Access Project (static.case.law) bulk corpus
to the exact reporters we need for Florida & California.

Level 0 (no blockers): reads CAP's public metadata, selects the CA + FL reporters,
flags multi-state regional reporters (e.g., So.2d covers AL/FL/LA/MS — must be
filtered per-case to Florida downstream), and writes a target manifest with full
provenance for the next piece (the case fetcher).

Run:
    python cds_cap_explorer.py            # print summary + write manifest
    python cds_cap_explorer.py --selftest # run assertions, exit 0/1

Output: cap_targets_fl_ca.json (reporter slugs + year ranges + provenance)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make the shared _common package importable.
_FACTORY_ROOT = Path(__file__).resolve().parent.parent
if str(_FACTORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_FACTORY_ROOT))

from _common.fetcher import Fetcher  # noqa: E402

CAP_BASE = "https://static.case.law"
JURISDICTIONS_URL = f"{CAP_BASE}/JurisdictionsMetadata.json"
REPORTERS_URL = f"{CAP_BASE}/ReportersMetadata.json"

DEFAULT_TARGET_STATES = ["California", "Florida"]
OUT_PATH = Path(__file__).parent / "cap_targets_fl_ca.json"


def _real_states(jurisdiction_names: list[str]) -> list[str]:
    """Drop the 'Regional' pseudo-jurisdiction; return real state names."""
    return [n for n in jurisdiction_names if n and n != "Regional"]


def build_targets(fetcher: Fetcher, target_states: list[str]) -> dict:
    jur_res = fetcher.get_json(JURISDICTIONS_URL)
    rep_res = fetcher.get_json(REPORTERS_URL)
    jurisdictions = jur_res.json()
    reporters = rep_res.json()

    # reporter slug -> list of real state names it spans (to detect multi-state)
    reporter_states: dict[str, list[str]] = {}
    for r in reporters:
        slug = r.get("slug")
        if not slug:
            continue
        names = [j.get("name_long") for j in r.get("jurisdictions", [])]
        reporter_states[slug] = _real_states(names)

    targets: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for jur in jurisdictions:
        state = jur.get("name_long")
        if state not in target_states:
            continue
        for rep in jur.get("reporters", []):
            slug = rep.get("slug")
            if not slug:
                continue
            key = (state, slug)
            if key in seen:
                continue
            seen.add(key)
            spanned = reporter_states.get(slug, [state])
            other_states = [s for s in spanned if s != state]
            targets.append(
                {
                    "state": state,
                    "reporter_slug": slug,
                    "short_name": rep.get("short_name"),
                    "full_name": rep.get("full_name"),
                    "start_year": rep.get("start_year"),
                    "end_year": rep.get("end_year"),
                    "base_url": f"{CAP_BASE}/{slug}/",
                    "multi_state": len(spanned) > 1,
                    "other_states": other_states,
                }
            )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_states": target_states,
        "sources": [jur_res.provenance(), rep_res.provenance()],
        "target_count": len(targets),
        "targets": sorted(targets, key=lambda t: (t["state"], t["reporter_slug"])),
    }


def print_summary(manifest: dict) -> None:
    print(f"CAP targets generated_at={manifest['generated_at']}")
    print(f"Target states: {', '.join(manifest['target_states'])}")
    print(f"Total target reporters: {manifest['target_count']}\n")
    cur_state = None
    for t in manifest["targets"]:
        if t["state"] != cur_state:
            cur_state = t["state"]
            print(f"== {cur_state} ==")
        flag = f"  [multi-state -> filter to {t['state']}; also: {', '.join(t['other_states'])}]" if t["multi_state"] else ""
        print(f"  {t['reporter_slug']:14s} {str(t['short_name']):16s} {t['start_year']}-{t['end_year']}{flag}")
    print()


def write_manifest(manifest: dict, out_path: Path = OUT_PATH) -> Path:
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out_path


def selftest() -> int:
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    with Fetcher(min_delay=0.3) as f:
        m = build_targets(f, DEFAULT_TARGET_STATES)

    slugs = {(t["state"], t["reporter_slug"]) for t in m["targets"]}
    check("found targets", m["target_count"] > 0)
    check("California reporters present", any(s == "California" for s, _ in slugs))
    check("Florida reporters present", any(s == "Florida" for s, _ in slugs))
    check("CA: cal-rptr-3d present", ("California", "cal-rptr-3d") in slugs)
    check("CA: cal-super-ct present", ("California", "cal-super-ct") in slugs)
    check("FL: so3d present", ("Florida", "so3d") in slugs)
    check("FL: so2d flagged multi-state",
          any(t["reporter_slug"] == "so2d" and t["state"] == "Florida" and t["multi_state"] for t in m["targets"]))
    check("provenance: 2 sources with sha256",
          len(m["sources"]) == 2 and all(s.get("sha256") for s in m["sources"]))

    if failures:
        print(f"\nRESULT: FAILED ({len(failures)}) -> {failures}")
        return 1
    print("\nRESULT: ALL CHECKS PASSED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="CAP reporter explorer for FL/CA")
    ap.add_argument("--states", nargs="+", default=DEFAULT_TARGET_STATES)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    with Fetcher(min_delay=0.3) as f:
        manifest = build_targets(f, args.states)
    print_summary(manifest)
    out = write_manifest(manifest)
    print(f"Wrote manifest -> {out} ({manifest['target_count']} reporters)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
