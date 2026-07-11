"""
test_no_fabrication_gate.py — CI guard for the no-fabrication prime directive
(AGENTS.md RULE 0).

Two layers of protection, both run by truth-check:
  1. Behavioural: the gate strips fabricated/unverifiable fields and rejects
     records without provenance; it recognises verbatim-backed values.
  2. Structural: every DB insert path routes through BOTH gates
     (no_fabrication_gate.verify_record + verdict_validator.normalize_and_validate).
     If someone adds an insert that bypasses them, this test fails the build.

Keeping this green is mandatory. If it fails, do NOT relax the assertions —
fix the code so the gate is enforced.
"""

import sys
from pathlib import Path

_FACTORY = Path(__file__).resolve().parent.parent / "settle_data_scraping_factory"
_RECORDS = _FACTORY / "court_dockets_records"
for _p in (str(_FACTORY), str(_RECORDS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from no_fabrication_gate import verify_record  # noqa: E402


# ---- Layer 1: behavioural guarantees --------------------------------------

def _base():
    return {
        "jurisdiction": "Miami-Dade, FL",
        "case_type": "motor_vehicle_accident",
        "source_url": "https://static.case.law/so3d/1/cases/0001.json",
    }


def test_verbatim_field_survives_with_evidence():
    rec = dict(_base(),
               medical_bills=245000.0,
               medical_bills_snippet="medical bills totalled $245,000 for surgery")
    r = verify_record(rec)
    assert not r["rejected"]
    assert r["validation_counts"].get("medical_bills") == 1
    assert r["evidence"]["medical_bills"]["source_url"].startswith("https://")


def test_fabricated_value_is_stripped_never_kept():
    # Snippet says 245,000 but value claims 999,999 -> not verbatim -> stripped.
    rec = dict(_base(),
               medical_bills=999999.0,
               medical_bills_snippet="medical bills totalled $245,000 for surgery")
    r = verify_record(rec)
    assert "medical_bills" not in r["record"]
    assert "medical_bills" in r["stripped"]


def test_field_without_snippet_is_stripped():
    rec = dict(_base(), insurance_carrier="GEICO")  # no snippet
    r = verify_record(rec)
    assert "insurance_carrier" not in r["record"]


def test_record_without_provenance_is_rejected():
    r = verify_record({"case_type": "x", "outcome_type": "settlement"})  # no jurisdiction/source
    assert r["rejected"]


def test_age_bucket_must_match_snippet_age():
    rec = dict(_base(),
               plaintiff_age_range="0_17",
               plaintiff_age_range_snippet="the plaintiff, aged 52, was injured")
    r = verify_record(rec)
    assert "plaintiff_age_range" not in r["record"]  # 52 does not justify 0_17


def test_injuries_only_survive_with_extraction_evidence():
    rec = dict(_base(), injury_type=["back", "brain"],
               _extraction={"injuries": ["back"]})
    r = verify_record(rec)
    assert r["record"].get("injury_type") == ["back"]


def test_gate_selftest_passes():
    import no_fabrication_gate as g
    assert g.selftest() == 0


def test_verdict_validator_selftest_passes():
    import verdict_validator as v
    assert v.selftest() == 0


# ---- Layer 2: structural guard — no insert bypasses the gates -------------

def test_loaders_route_through_both_gates():
    """Every loader that inserts verdicts must import and call BOTH gates."""
    loaders = [
        _RECORDS / "cds_cap_loader.py",
        _RECORDS / "load_direct_supabase.py",
    ]
    for loader in loaders:
        src = loader.read_text(encoding="utf-8")
        assert "verify_record" in src, f"{loader.name} must call no_fabrication_gate.verify_record"
        assert "normalize_and_validate" in src, f"{loader.name} must call verdict_validator.normalize_and_validate"


def test_no_fabricated_case_type_fallback():
    """The 'personal_injury_general' fabricated fallback must never return."""
    src = (_RECORDS / "cds_cap_loader.py").read_text(encoding="utf-8")
    # It may appear only in a comment explaining its removal, never as an
    # assignment fallback ( ... or "personal_injury_general" ).
    assert 'or ("personal_injury_general"' not in src
    assert 'or "personal_injury_general"' not in src


def test_no_expert_witness_guessing():
    """The split-a-total-in-half expert guess must not exist in the enricher."""
    src = (_FACTORY / "_common" / "enrich.py").read_text(encoding="utf-8")
    assert "all_experts // 2" not in src


# ---- Layer 3: API service insert paths must also be gated -----------------

_APP = Path(__file__).resolve().parent.parent / "app"


def test_api_verdict_inserts_route_through_guard():
    """Every settle_verdicts insert in the API service must be preceded by the
    server-side no-fabrication guard. This closes the gap where the scraping
    bulk-insert endpoint / manual create could bypass the file-loader gates."""
    src = (_APP / "services" / "verdict_search.py").read_text(encoding="utf-8")
    assert "guard_verdict_record" in src, "verdict_search must import the guard"
    # Both insert call sites must exist alongside a guard call.
    assert src.count("guard_verdict_record(") >= 2, (
        "both bulk_insert_verdicts and create_verdict must call guard_verdict_record"
    )


def test_verdict_guard_behaviour():
    """The app-native guard enforces the same invariants as the factory gate."""
    import sys
    if str(_APP.parent) not in sys.path:
        sys.path.insert(0, str(_APP.parent))
    from app.services.verdict_guard import guard_verdict_record

    base = {"jurisdiction": "Miami-Dade, FL", "case_type": "motor_vehicle_accident",
            "outcome_type": "settlement", "source_url": "https://static.case.law/x"}

    # No provenance -> rejected.
    r, e = guard_verdict_record({k: v for k, v in base.items() if k != "source_url"})
    assert r is None and any("provenance" in x for x in e)

    # Amount with no evidence -> stripped, record survives.
    r2, _ = guard_verdict_record(dict(base, settlement_amount=250000.0))
    assert r2 is not None and "settlement_amount" not in r2

    # Amount with verbatim evidence -> kept.
    r3, _ = guard_verdict_record(dict(
        base, settlement_amount=250000.0,
        field_evidence={"settlement_amount": {"snippet": "settled for $250,000",
                                              "source_url": "https://static.case.law/x"}}))
    assert r3 is not None and r3.get("settlement_amount") == 250000.0

    # Out-of-bounds amount -> rejected.
    r4, e4 = guard_verdict_record(dict(base, settlement_amount=5_000_000_000.0))
    assert r4 is None

    # Invalid outcome enum -> rejected.
    r5, e5 = guard_verdict_record(dict(base, outcome_type="something_made_up"))
    assert r5 is None
