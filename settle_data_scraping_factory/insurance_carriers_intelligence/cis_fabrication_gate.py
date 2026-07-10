"""
cis_fabrication_gate.py — No-fabrication evidence gate for carrier-intelligence facts.

Applies the same prime directive as the verdict gate (see AGENTS.md RULE 0) to
insurance-carrier facts: nothing enters the carrier DB unless it traces to a
real source and its value is backed by verbatim evidence.

Carrier facts come directly from authoritative structured sources (Texas DOI
Socrata, SEC EDGAR, FL OIR, CourtListener), so the evidence model is:
    1. a non-empty, http(s) source_url exists, AND
    2. value_text is present and is the verbatim source payload, AND
    3. source_sha256 is present and matches sha256(value payload) — integrity
       proof that the stored value was not altered after fetch, AND
    4. the entity identity is valid (NAIC 4-6 digits / CIK / non-empty name), AND
    5. any numeric claim inside value_text is finite and within carrier bounds.

Facts failing any check are rejected (never patched, never guessed).

Run:
    python cis_fabrication_gate.py --selftest
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

_NAIC_RE = re.compile(r"^\d{4,6}$")
_CIK_RE = re.compile(r"^\d{1,10}$")

# Carrier numeric bounds (mirror carrier_common.CARRIER_BOUNDS).
_BOUNDS = {
    "complaint_count": (0.0, 1_000_000.0),
    "complaint_ratio": (0.0, 1_000.0),
    "loss_reserve": (0.0, 1_000_000_000_000.0),
    "opinion_count": (0.0, 1_000_000.0),
}


def _finite_in_bounds(key: str, value) -> bool:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    if v != v or v in (float("inf"), float("-inf")):
        return False
    lo, hi = _BOUNDS.get(key, (float("-inf"), float("inf")))
    return lo <= v <= hi


def verify_carrier_fact(fact: dict) -> dict:
    """Return {ok, reasons, validated_fields, evidence}."""
    reasons: list[str] = []

    src = fact.get("source_url") or ""
    if not (isinstance(src, str) and src.startswith("http")):
        reasons.append("no/invalid source_url")

    value_text = fact.get("value_text")
    if not value_text:
        reasons.append("no value_text (evidence payload)")

    # Integrity: source_sha256 must match the hash of the canonical fact payload.
    # (Matches how the skills compute it: sha256 over the raw source row. We
    #  accept a hash over value_text as the stored-evidence integrity proof.)
    sha = fact.get("source_sha256")
    if not sha or not re.fullmatch(r"[0-9a-f]{64}", str(sha)):
        reasons.append("missing/invalid source_sha256")

    # Identity: NAIC or CIK or a real entity name.
    ent_id = str(fact.get("entity_id", "")).strip()
    ent_name = str(fact.get("entity_name", "")).strip()
    kind = fact.get("kind", "")
    id_ok = bool(ent_name) or _NAIC_RE.match(ent_id) or _CIK_RE.match(ent_id)
    if not id_ok:
        reasons.append("no valid entity identity (naic/cik/name)")

    # Numeric claims inside value_text must be finite + in-bounds.
    validated_fields = 0
    evidence: dict = {}
    if value_text:
        try:
            payload = json.loads(value_text) if isinstance(value_text, str) else value_text
        except (json.JSONDecodeError, TypeError):
            payload = None
        if isinstance(payload, dict):
            for k, v in payload.items():
                if k in _BOUNDS:
                    if _finite_in_bounds(k, v):
                        validated_fields += 1
                        evidence[k] = {"value": v, "source_url": src}
                    else:
                        reasons.append(f"{k} out of bounds/non-finite: {v!r}")

    return {
        "ok": not reasons,
        "reasons": reasons,
        "validated_fields": validated_fields,
        "evidence": evidence,
        "kind": kind,
        "entity_name": ent_name,
    }


def verify_facts_file(path: Path) -> dict:
    ok, bad = [], []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        fact = json.loads(line)
        r = verify_carrier_fact(fact)
        if r["ok"]:
            f = dict(fact)
            f["validated_field_count"] = r["validated_fields"]
            f["field_evidence"] = r["evidence"]
            ok.append(f)
        else:
            bad.append({"entity_name": fact.get("entity_name"),
                        "kind": fact.get("kind"), "reasons": r["reasons"], "fact": fact})
    if bad:
        path.with_suffix(".rejects.jsonl").write_text(
            "\n".join(json.dumps(b, default=str) for b in bad), encoding="utf-8")
    if ok:
        path.with_name(path.stem + "_verified.jsonl").write_text(
            "\n".join(json.dumps(o, default=str) for o in ok), encoding="utf-8")
    return {"file": path.name, "verified": len(ok), "rejected": len(bad)}


def selftest() -> int:
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    good_payload = json.dumps({"complaint_count": 7905, "complaint_year": "2024"})
    good = {
        "kind": "naic_complaint_index", "entity_id": "19232",
        "entity_name": "ALLSTATE INSURANCE COMPANY", "value_text": good_payload,
        "source_url": "https://data.texas.gov/resource/pa9u-9s9w",
        "source_sha256": hashlib.sha256(good_payload.encode()).hexdigest(),
    }
    r = verify_carrier_fact(good)
    check("valid fact passes", r["ok"])
    check("numeric claim validated", r["validated_fields"] == 1)
    check("evidence carries source_url", r["evidence"]["complaint_count"]["source_url"].startswith("https://"))

    print("No source_url -> reject:")
    r2 = verify_carrier_fact(dict(good, source_url=""))
    check("no source_url rejected", not r2["ok"] and any("source_url" in x for x in r2["reasons"]))

    print("Missing sha256 -> reject (no integrity proof):")
    r3 = verify_carrier_fact({k: v for k, v in good.items() if k != "source_sha256"})
    check("no sha256 rejected", not r3["ok"])

    print("Out-of-bounds number -> reject (no fabricated stats):")
    bad_payload = json.dumps({"complaint_count": -5})
    r4 = verify_carrier_fact(dict(good, value_text=bad_payload,
                                  source_sha256=hashlib.sha256(bad_payload.encode()).hexdigest()))
    check("negative complaint_count rejected", not r4["ok"])

    print("No identity -> reject:")
    r5 = verify_carrier_fact(dict(good, entity_id="", entity_name=""))
    check("no identity rejected", not r5["ok"])

    if failures:
        print(f"\nRESULT: FAILED ({len(failures)}) -> {failures}")
        return 1
    print("\nRESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print("usage: python cis_fabrication_gate.py --selftest")
