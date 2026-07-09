"""
cis_orchestrator.py — Insurance Carrier Intelligence orchestrator.

Runs the carrier-intelligence scraping skills (NAIC complaints, SEC EDGAR
filings + loss reserves, FL OIR, CourtListener bad-faith) for a registry of
top US auto / personal-injury carriers, aggregates the results into a unified
carrier profile, and writes CarrierSourceDoc JSONL into
insurance_carriers_intelligence/out/<slug>/.

Every source runs in isolation: a failure or throttle in one source never
aborts the others. Public mutuals with no SEC ticker skip SEC gracefully.

Usage:
    python cis_orchestrator.py --list
    python cis_orchestrator.py --carrier "State Farm" --dry-run
    python cis_orchestrator.py --top 10 --skip courtlistener   # skip throttled source
    python cis_orchestrator.py --all
    python cis_orchestrator.py --selftest
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

_THIS_DIR = Path(__file__).resolve().parent
_FACTORY_ROOT = _THIS_DIR.parent
_SKILL_DIR = (_FACTORY_ROOT.parent / "scripts" / "scraping-factory" / "insurance-carrier").resolve()

for _p in (str(_FACTORY_ROOT), str(_SKILL_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT_DIR = _THIS_DIR / "out"


@dataclass
class Carrier:
    name: str
    naic: Optional[str] = None      # NAIC company code (complaints)
    ticker: Optional[str] = None    # SEC ticker (public parents only)
    state_focus: Optional[str] = None


# Top US auto / personal-injury liability carriers. NAIC codes are the primary
# writing-company codes; tickers are set only for SEC-public parents (mutuals
# and foreign-owned carriers have none and skip SEC automatically).
CARRIERS: list[Carrier] = [
    Carrier("State Farm", naic="25178", ticker=None),
    Carrier("GEICO", naic="22063", ticker=None),
    Carrier("Progressive", naic="24260", ticker="PGR"),
    Carrier("Allstate", naic="19232", ticker="ALL"),
    Carrier("USAA", naic="25941", ticker=None),
    Carrier("Liberty Mutual", naic="23043", ticker=None),
    Carrier("Nationwide", naic="23787", ticker=None),
    Carrier("Farmers Insurance", naic="21652", ticker=None),
    Carrier("Travelers", naic="25658", ticker="TRV"),
    Carrier("American Family Insurance", naic="19275", ticker=None),
]


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_source(label: str, fn: Callable[[], list[dict]], results: dict) -> None:
    """Run one source in isolation; record facts or the error, never raise."""
    try:
        facts = fn() or []
        results["sources"][label] = {"status": "ok", "facts": len(facts)}
        results["facts"].extend(facts)
        print(f"    [{label}] ok: {len(facts)} facts")
    except Exception as e:  # noqa: BLE001 — deliberately tolerant
        results["sources"][label] = {"status": "error", "error": f"{type(e).__name__}: {e}"}
        print(f"    [{label}] ERROR: {type(e).__name__}: {e}")


def collect_carrier(carrier: Carrier, skip: set[str], cl_limit: int = 20) -> dict:
    """Collect facts for one carrier from all (non-skipped) sources."""
    print(f"  Carrier: {carrier.name} (NAIC={carrier.naic}, ticker={carrier.ticker})")
    results: dict[str, Any] = {
        "carrier": carrier.name,
        "naic": carrier.naic,
        "ticker": carrier.ticker,
        "collected_at": _now(),
        "sources": {},
        "facts": [],
    }

    if "naic" not in skip and carrier.naic:
        import naic_complaints as naic
        _run_source(
            "naic_complaints",
            lambda: naic.to_carrier_facts(naic.get_raw_complaints(naic_code=carrier.naic, limit=200)),
            results,
        )

    if "sec" not in skip and carrier.ticker:
        import sec_edgar_filings as sec
        import sec_edgar_reserves as sec_res

        def _sec_filings() -> list[dict]:
            cik = sec.resolve_cik(carrier.ticker)
            if not cik:
                raise RuntimeError(f"could not resolve CIK for ticker {carrier.ticker}")
            return sec.filings_to_carrier_facts(sec.list_filings(cik, form_type="10-K", limit=5))

        def _sec_reserves() -> list[dict]:
            cik = sec.resolve_cik(carrier.ticker)
            if not cik:
                raise RuntimeError(f"could not resolve CIK for ticker {carrier.ticker}")
            return sec_res.reserves_to_carrier_facts(sec_res.get_loss_reserves(cik))

        _run_source("sec_edgar_filings", _sec_filings, results)
        _run_source("sec_edgar_reserves", _sec_reserves, results)

    if "courtlistener" not in skip:
        import courtlistener_bad_faith as bf

        def _bad_faith() -> list[dict]:
            hits = bf.search_bad_faith(carrier.name, state=carrier.state_focus, limit=cl_limit)
            facts = [bf.search_result_to_carrier_fact(h, "bad_faith_opinion_count") for h in hits]
            return [f for f in facts if f]

        _run_source("courtlistener_bad_faith", _bad_faith, results)

    if "profile" not in skip:
        import carrier_profile as prof
        _run_source(
            "carrier_profile",
            lambda: prof.build_carrier_profile(carrier.name, naic_code=carrier.naic),
            results,
        )

    return results


def write_carrier_output(results: dict, dry_run: bool) -> Optional[Path]:
    slug = _slug(results["carrier"])
    carrier_dir = OUT_DIR / slug
    if dry_run:
        return None
    carrier_dir.mkdir(parents=True, exist_ok=True)
    out_path = carrier_dir / f"{slug}_facts.jsonl"
    # Facts are already canonical CarrierFact dicts; write them verbatim.
    # (cis_common.write_facts_jsonl would re-wrap dicts and nest each fact
    # inside value_text, so we serialise directly here.)
    with out_path.open("w", encoding="utf-8") as f:
        for fact in results["facts"]:
            f.write(json.dumps(fact, default=str) + "\n")
    manifest = {k: v for k, v in results.items() if k != "facts"}
    manifest["fact_count"] = len(results["facts"])
    (carrier_dir / f"{slug}_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8"
    )
    return out_path


def run(carriers: list[Carrier], skip: set[str], dry_run: bool, cl_limit: int = 20) -> dict:
    print(f"Orchestrating {len(carriers)} carriers "
          f"(skip={sorted(skip) or 'none'}, mode={'dry-run' if dry_run else 'live'})")
    summary: dict[str, Any] = {"carriers": [], "totals": {"facts": 0, "errors": 0}}
    for c in carriers:
        res = collect_carrier(c, skip=skip, cl_limit=cl_limit)
        out = write_carrier_output(res, dry_run=dry_run)
        errors = sum(1 for s in res["sources"].values() if s["status"] == "error")
        summary["carriers"].append({
            "carrier": c.name,
            "facts": len(res["facts"]),
            "sources": res["sources"],
            "output": str(out) if out else None,
        })
        summary["totals"]["facts"] += len(res["facts"])
        summary["totals"]["errors"] += errors
    return summary


def selftest() -> int:
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    check("registry has 10 carriers", len(CARRIERS) == 10)
    check("all carriers have NAIC", all(c.naic for c in CARRIERS))
    check("slug is filesystem-safe", _slug("State Farm & Co.") == "state_farm___co")
    check("skill dir exists", _SKILL_DIR.exists())

    # _run_source must swallow errors and record them.
    res = {"sources": {}, "facts": []}
    _run_source("boom", lambda: (_ for _ in ()).throw(RuntimeError("x")), res)
    check("failing source is isolated", res["sources"]["boom"]["status"] == "error")
    _run_source("good", lambda: [{"kind": "t"}], res)
    check("good source collects facts", len(res["facts"]) == 1)

    if failures:
        print(f"\nRESULT: FAILED ({len(failures)}) -> {failures}")
        return 1
    print("\nRESULT: ALL CHECKS PASSED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Insurance carrier intelligence orchestrator")
    ap.add_argument("--carrier", help="Run a single carrier by name")
    ap.add_argument("--top", type=int, help="Run the top N carriers from the registry")
    ap.add_argument("--all", action="store_true", help="Run every carrier in the registry")
    ap.add_argument("--skip", default="", help="Comma-separated sources to skip "
                    "(naic,sec,courtlistener,profile)")
    ap.add_argument("--cl-limit", type=int, default=20, help="CourtListener max results/carrier")
    ap.add_argument("--dry-run", action="store_true", help="Collect but do not write files")
    ap.add_argument("--list", action="store_true", help="List the carrier registry")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if args.list:
        for c in CARRIERS:
            print(f"  {c.name:28s} NAIC={c.naic or '-':7s} ticker={c.ticker or '-'}")
        return 0

    skip = {s.strip().lower() for s in args.skip.split(",") if s.strip()}

    if args.carrier:
        chosen = [c for c in CARRIERS if c.name.lower() == args.carrier.lower()]
        if not chosen:
            chosen = [Carrier(args.carrier)]
    elif args.top:
        chosen = CARRIERS[: args.top]
    elif args.all:
        chosen = CARRIERS
    else:
        ap.error("one of --carrier, --top, --all, --list, or --selftest is required")

    summary = run(chosen, skip=skip, dry_run=args.dry_run, cl_limit=args.cl_limit)
    print("\n" + json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
