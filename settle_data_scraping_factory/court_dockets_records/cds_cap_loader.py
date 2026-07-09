"""
cds_cap_loader.py — Load CAP pipeline rows into the SETTLE internal-verdicts
review queue (settle_verdicts, review_status='pending') via the admin bulk-insert API.

Pieces 1-5 produce validated/scored/deduped candidate rows (accepted / needs_review).
This piece maps them to the settle_verdicts schema and posts them so a human can
review them in the SETTLE admin dashboard. Nothing is auto-published to customers —
rows land as review_status='pending' / 'needs_review'.

Integrity (guardrail 6a): we map ONLY fields we actually have. We do NOT invent a
county (CAP appellate data is state-level) or a precise date (CAP dates are often
year-only) — those imprecisions are recorded truthfully in source_notes instead of
being faked. Provenance (source_url + sha256 + evidence snippet) is preserved.

Endpoints used:
    POST /api/v1/internal/verdicts/scrape/jobs         (job tracking; best-effort)
    POST /api/v1/internal/verdicts/scrape/bulk-insert  (records; server dedups)
    PATCH /api/v1/internal/verdicts/scrape/jobs/{id}    (job result; best-effort)

Run:
    python cds_cap_loader.py --in out/cap_so3d_florida_accepted.jsonl --dry-run
    python cds_cap_loader.py --in out/cap_so3d_florida_accepted.jsonl     # live POST
    python cds_cap_loader.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import httpx

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from verdict_validator import normalize_and_validate  # noqa: E402

SETTLE_API_URL = os.getenv("SETTLE_API_URL", "http://localhost:8002")
# Admin key must start with 'settle_' (auth format gate). In mock mode any such key works.
SETTLE_ADMIN_KEY = os.getenv("SETTLE_ADMIN_API_KEY", "settle_admin_dev_key")

_SETTLEMENT_KINDS = {"settlement"}


def map_candidate_to_verdict(c: dict) -> dict:
    """Map a pipeline candidate row -> settle_verdicts record. Faithful; no fabrication."""
    state = c.get("state")
    amount = c.get("exact_outcome_amount")
    outcome_type = c.get("outcome_type")

    # Route the amount to the correct field (settlement vs verdict/award/damages).
    total_verdict = None
    settlement_amount = None
    if amount is not None:
        if outcome_type in _SETTLEMENT_KINDS:
            settlement_amount = amount
        else:
            total_verdict = amount

    # jurisdiction: use a real county hint if the opinion text gave one, else the state.
    jurisdiction = c.get("county_hint") or state

    # case_type: keep specific type if found; else a general PI bucket (accepted rows
    # always have an injury or a case_type, so this is a category, not a fabrication).
    case_type = c.get("case_type") or ("personal_injury_general" if c.get("injury_category") else None)

    # Provenance + evidence + honest imprecision flags for the human reviewer.
    notes = {
        "pipeline_status": c.get("status"),
        "pipeline_reason": c.get("reason"),
        "official_citation": c.get("official_citation"),
        "decision_year": c.get("year"),
        "jurisdiction_granularity": "county" if c.get("county_hint") else "state",
        "date_precision": "year_only",
        "amount_snippet": c.get("amount_snippet"),
        "extraction_method": c.get("extraction_method"),
        "text_sha256": c.get("text_sha256"),
        "full_text_url": c.get("full_text_url"),
    }

    review_status = "needs_review" if c.get("status") == "needs_review" else "pending"

    # Completeness score: fraction of meaningful optional fields that are populated.
    optional_fields = [
        bool(c.get("case_name")),
        bool(c.get("docket_number")),
        bool(c.get("court_name")),
        bool(c.get("judge_name")),
        bool(c.get("case_type")),
        bool(c.get("injury_category")),
        bool(c.get("outcome_type")),
        bool(amount),
        bool(c.get("medical_bills")),
        bool(c.get("economic_damages")),
        bool(c.get("non_economic_damages")),
        bool(c.get("punitive_damages")),
        bool(c.get("plaintiff_age_range")),
        bool(c.get("liability_tier")),
        bool(c.get("comparative_negligence_pct")),
        bool(c.get("defendant_category")),
        bool(c.get("insurance_carrier")),
        bool(c.get("trial_duration_days")),
        bool(c.get("verdict_date")),
        bool(c.get("source_url") or c.get("full_text_url")),
        bool(c.get("year")),
    ]
    completeness_score = round(sum(1 for f in optional_fields if f) / len(optional_fields), 2)

    record = {
        "case_name": c.get("case_name"),
        "case_number": c.get("docket_number"),
        "jurisdiction": jurisdiction,
        "court": c.get("court_name"),
        "judge_name": c.get("judge_name"),
        "case_type": case_type,
        "injury_type": c.get("injury_category") or [],
        "plaintiff_age_range": c.get("plaintiff_age_range"),
        "liability_tier": c.get("liability_tier"),
        "comparative_negligence_pct": c.get("comparative_negligence_pct"),
        "medical_bills": c.get("medical_bills"),
        "economic_damages": c.get("economic_damages"),
        "non_economic_damages": c.get("non_economic_damages"),
        "punitive_damages": c.get("punitive_damages"),
        "total_verdict": total_verdict,
        "settlement_amount": settlement_amount,
        "policy_limit_indicator": c.get("policy_limit_indicator"),
        "outcome_type": outcome_type or "unknown",
        "defendant_category": c.get("defendant_category"),
        "defendant_industry": c.get("defendant_industry"),
        "insurance_carrier": c.get("insurance_carrier"),
        "expert_witnesses_plaintiff": c.get("expert_witnesses_plaintiff"),
        "expert_witnesses_defense": c.get("expert_witnesses_defense"),
        "trial_duration_days": c.get("trial_duration_days"),
        "verdict_date": c.get("verdict_date"),
        "filing_date": c.get("filing_date"),
        # source read from the candidate (courtlistener / morelaw / caselaw_access_project), never hardcoded.
        "source": c.get("source") or "caselaw_access_project",
        "source_url": c.get("full_text_url") or c.get("source_url"),
        "source_notes": json.dumps({k: v for k, v in notes.items() if v is not None}, default=str),
        "review_status": review_status,
        "confidence_score": c.get("confidence_score"),
        "completeness_score": completeness_score,
        "scraped_at": c.get("fetched_at"),
    }
    # Drop null amount fields so we don't send explicit nulls.
    return {k: v for k, v in record.items() if v is not None}


def _read_rows(path: Path) -> list[dict]:
    rows = []
    # utf-8-sig tolerates a leading BOM (some editors/PowerShell add one).
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def load_file(in_path: Path, dry_run: bool, source_label: Optional[str] = None) -> dict:
    rows = _read_rows(in_path)
    mapped = [map_candidate_to_verdict(r) for r in rows]

    # DB-boundary validation gate: EVERY record must pass before it can be
    # posted. Rejects are quarantined to a sidecar file (never inserted);
    # warnings (fields coerced/dropped) are tallied for the reviewer.
    records: list[dict] = []
    rejects: list[dict] = []
    warn_count = 0
    for original, m in zip(rows, mapped):
        clean, errors, warnings = normalize_and_validate(m)
        warn_count += len(warnings)
        if clean is None:
            rejects.append({
                "case_name": original.get("case_name"),
                "official_citation": original.get("official_citation"),
                "source_url": m.get("source_url"),
                "errors": errors,
                "record": m,
            })
        else:
            records.append(clean)

    if rejects:
        qpath = in_path.with_suffix(".rejects.jsonl")
        qpath.write_text("\n".join(json.dumps(r, default=str) for r in rejects), encoding="utf-8")

    # Job-tracking source label: honor an explicit override, else infer it from the rows
    # so courtlistener/morelaw/CAP batches are tracked truthfully (never hardcoded).
    if source_label is None:
        sources = {r.get("source") for r in rows if r.get("source")}
        source_label = sources.pop() if len(sources) == 1 else ("mixed" if sources else "caselaw_access_project")

    validation = {
        "input_rows": len(rows),
        "valid": len(records),
        "rejected": len(rejects),
        "warnings": warn_count,
        "rejects_file": str(in_path.with_suffix(".rejects.jsonl")) if rejects else None,
    }

    if dry_run:
        out = in_path.with_suffix(".verdicts.jsonl")
        out.write_text("\n".join(json.dumps(r, default=str) for r in records), encoding="utf-8")
        return {"mode": "dry_run", "mapped": len(records), "source_label": source_label,
                "payload_written": str(out), "validation": validation}

    if not records:
        return {"mode": "live", "mapped": 0, "http_status": None,
                "note": "all records rejected by validation", "validation": validation}

    headers = {"Authorization": f"Bearer {SETTLE_ADMIN_KEY}", "X-Admin-Key": SETTLE_ADMIN_KEY}

    # Best-effort job tracking in its OWN client/connection so a failure (e.g. no DB ->
    # 500 + connection close) cannot poison the bulk-insert connection.
    job_id = None
    try:
        with httpx.Client(timeout=60.0, headers=headers) as jc:
            jr = jc.post(
                f"{SETTLE_API_URL}/api/v1/internal/verdicts/scrape/jobs",
                json={"source": source_label, "source_config": {"in_file": in_path.name, "count": len(records)}},
            )
            if jr.status_code == 200:
                job_id = jr.json().get("id")
    except Exception:
        pass

    # Bulk-insert on a fresh connection, with a retry on transient disconnects.
    result = {"http_status": None}
    last_err = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=120.0, headers=headers) as bc:
                resp = bc.post(
                    f"{SETTLE_API_URL}/api/v1/internal/verdicts/scrape/bulk-insert",
                    json=records,
                )
            result = {"http_status": resp.status_code}
            try:
                result.update(resp.json())
            except Exception:
                result["body"] = resp.text[:300]
            break
        except (httpx.RemoteProtocolError, httpx.TransportError) as e:
            last_err = e
    else:
        result = {"http_status": None, "error": f"bulk-insert failed after retries: {last_err}"}

    if job_id:
        try:
            with httpx.Client(timeout=60.0, headers=headers) as pc:
                pc.patch(
                    f"{SETTLE_API_URL}/api/v1/internal/verdicts/scrape/jobs/{job_id}",
                    params={
                        "status": "completed",
                        "records_found": len(records),
                        "records_inserted": result.get("inserted", 0),
                        "records_skipped": result.get("skipped", 0),
                        "records_failed": result.get("failed", 0),
                    },
                )
        except Exception:
            pass

    result["mode"] = "live"
    result["mapped"] = len(records)
    result["validation"] = validation
    return result


def selftest() -> int:
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    accepted = {
        "source": "caselaw_access_project", "state": "Florida", "county_hint": None,
        "case_type": "motor_vehicle_accident", "injury_category": ["neck", "back"],
        "outcome_type": "verdict", "exact_outcome_amount": 1_250_000, "outcome_amount_range": "1m_5m",
        "year": 2018, "is_verdict": True, "source_url": "https://static.case.law/so3d/1/CasesMetadata.json",
        "full_text_url": "https://static.case.law/so3d/1/cases/0001-01.json", "text_sha256": "a" * 64,
        "amount_snippet": "jury awarded $1,250,000 in damages for spinal injuries",
        "extraction_method": "deterministic_regex_keyword", "case_name": "Doe v. Roe",
        "official_citation": "1 So. 3d 1", "confidence_score": 0.85, "status": "accepted", "reason": "validated",
        "court_name": "Florida Supreme Court", "court_abbrev": "Fla.",
        "docket_number": "SC18-1234", "fetched_at": "2026-06-30T17:41:24.753689+00:00",
        "judge_name": "WERDEGAR J.",
        "medical_bills": 245000.0,
        "economic_damages": 350000.0,
        "non_economic_damages": 900000.0,
        "punitive_damages": 500000.0,
        "plaintiff_age_range": "30_44",
        "liability_tier": "likely_liable",
        "comparative_negligence_pct": 15.0,
        "defendant_category": "healthcare",
        "defendant_industry": "healthcare",
        "insurance_carrier": "State Farm",
        "trial_duration_days": 7,
        "expert_witnesses_plaintiff": 2,
        "expert_witnesses_defense": 1,
        "verdict_date": "March 3, 2022",
        "filing_date": "June 15, 2019",
        "policy_limit_indicator": "mentioned: policy limit of $500,000",
    }
    print("Accepted -> verdict record mapping:")
    v = map_candidate_to_verdict(accepted)
    check("case_name mapped", v["case_name"] == "Doe v. Roe")
    check("amount routed to total_verdict", v.get("total_verdict") == 1_250_000)
    check("no settlement_amount on verdict", "settlement_amount" not in v)
    check("injury_type list preserved", v["injury_type"] == ["neck", "back"])
    check("review_status pending", v["review_status"] == "pending")
    check("source_url is provenance", v["source_url"].endswith(".json"))
    check("verdict_date mappable from enrichment", v.get("verdict_date") == "March 3, 2022")
    notes = json.loads(v["source_notes"])
    check("notes carry year + snippet + sha256", notes.get("decision_year") == 2018 and notes.get("amount_snippet") and notes.get("text_sha256"))
    check("notes flag state-level + year-only", notes.get("jurisdiction_granularity") == "state" and notes.get("date_precision") == "year_only")
    check("confidence preserved", v["confidence_score"] == 0.85)
    check("source read from candidate (not hardcoded)", v["source"] == "caselaw_access_project")
    check("court mapped from court_name", v.get("court") == "Florida Supreme Court")
    check("case_number mapped from docket_number", v.get("case_number") == "SC18-1234")
    check("judge_name mapped", v.get("judge_name") == "WERDEGAR J.")
    check("medical_bills mapped", v.get("medical_bills") == 245000.0)
    check("economic_damages mapped", v.get("economic_damages") == 350000.0)
    check("non_economic_damages mapped", v.get("non_economic_damages") == 900000.0)
    check("punitive_damages mapped", v.get("punitive_damages") == 500000.0)
    check("plaintiff_age_range mapped", v.get("plaintiff_age_range") == "30_44")
    check("liability_tier mapped", v.get("liability_tier") == "likely_liable")
    check("comparative_negligence_pct mapped", v.get("comparative_negligence_pct") == 15.0)
    check("defendant_category mapped", v.get("defendant_category") == "healthcare")
    check("insurance_carrier mapped", v.get("insurance_carrier") == "State Farm")
    check("trial_duration_days mapped", v.get("trial_duration_days") == 7)
    check("expert_witnesses_plaintiff mapped", v.get("expert_witnesses_plaintiff") == 2)
    check("expert_witnesses_defense mapped", v.get("expert_witnesses_defense") == 1)
    check("filing_date mapped", v.get("filing_date") == "June 15, 2019")
    check("policy_limit_indicator mapped", v.get("policy_limit_indicator") == "mentioned: policy limit of $500,000")
    check("completeness_score computed", isinstance(v.get("completeness_score"), float) and v["completeness_score"] > 0.3)
    check("scraped_at mapped from fetched_at", v.get("scraped_at") == "2026-06-30T17:41:24.753689+00:00")

    print("Source is read per-candidate (courtlistener):")
    cl = dict(accepted, source="courtlistener", official_citation="courtlistener:1")
    vcl = map_candidate_to_verdict(cl)
    check("courtlistener source preserved", vcl["source"] == "courtlistener")

    print("Settlement routing + needs_review status:")
    s = dict(accepted, outcome_type="settlement", status="needs_review", reason="below_confidence_threshold")
    vs = map_candidate_to_verdict(s)
    check("amount routed to settlement_amount", vs.get("settlement_amount") == 1_250_000)
    check("no total_verdict on settlement", "total_verdict" not in vs)
    check("needs_review status", vs["review_status"] == "needs_review")

    print("Dry-run file mapping (no network):")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "sample.jsonl"
        p.write_text(json.dumps(accepted) + "\n", encoding="utf-8")
        res = load_file(p, dry_run=True)
        check("dry-run mapped 1", res["mapped"] == 1)
        check("payload file written", Path(res["payload_written"]).exists())
        check("inferred source_label = caselaw_access_project", res["source_label"] == "caselaw_access_project")

        pcl = Path(tmp) / "cl.jsonl"
        pcl.write_text(json.dumps(dict(accepted, source="courtlistener")) + "\n", encoding="utf-8")
        rescl = load_file(pcl, dry_run=True)
        check("inferred source_label = courtlistener", rescl["source_label"] == "courtlistener")

    if failures:
        print(f"\nRESULT: FAILED ({len(failures)}) -> {failures}")
        return 1
    print("\nRESULT: ALL CHECKS PASSED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Load CAP pipeline rows into SETTLE review queue")
    ap.add_argument("--in", dest="in_path")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.in_path:
        ap.error("--in is required (or --selftest)")
    res = load_file(Path(args.in_path), dry_run=args.dry_run)
    print(json.dumps(res, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
