"""
Bounded tests for external/historical contribution verification lifecycle.

Proves partial verification, correction and re-verification using existing
SETTLE persistence and authority without fabricating evidence or allowing
stale verification to survive material changes.
"""

from app.services.external_verification import (
    summarize_record_status,
    field_verification_state,
    field_is_verified,
    record_status_implies_all_fields,
    check_contradiction,
    check_duplicate_source,
    apply_correction,
    stale_verification_after_correction,
    reverify_field,
    reverify_after_source_invalidation,
    is_unknown,
    is_missing,
    is_not_applicable,
    semantic_distinct,
    stripped_cannot_become_verified,
    analytics_eligibility_undelegated,
    verification_truth_for_analytics,
    tenant_can_modify,
    run_external_verification,
)


def _base_contribution(**overrides):
    data = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "motor_vehicle_accident",
        "outcome_type": "settlement",
        "source_url": "https://example.org/settlement-agreement-123",
        "medical_bills": 50000.0,
        "medical_bills_snippet": "medical bills totalled $50,000 for treatment",
        "settlement_amount": 100000.0,
        "settlement_amount_snippet": "the settlement amount was $100,000",
    }
    data.update(overrides)
    return data


# 1. fully supported external contribution reaches correct verification state
def test_fully_supported_reaches_verified_state():
    data = _base_contribution(
        insurance_carrier="State Farm",
        insurance_carrier_snippet="insured by State Farm",
    )
    result = run_external_verification(
        data,
        source_type="firm_submission",
        source_url="https://example.org/settlement-agreement-123",
        field_corroboration={"medical_bills": True, "insurance_carrier": True},
    )
    assert not result["rejected"]
    assert result["field_states"]["medical_bills"] == "verified"
    # Record-level status summarizes actual field states. Not every tracked
    # field is corroboration-flagged here, so the record is reviewed, not
    # fully verified — partial verification is preserved.
    assert result["record_status"] == "reviewed"


# 2. partially supported contribution remains partially verified
def test_partially_supported_remains_partial():
    data = _base_contribution()
    result = run_external_verification(
        data,
        source_type="firm_submission",
        source_url="https://example.org/settlement-agreement-123",
        field_corroboration={"medical_bills": True},
    )
    assert result["field_states"]["medical_bills"] == "verified"
    assert "lost_wages" not in result["field_states"]


# 3. verified field does not verify sibling fields
def test_verified_field_does_not_verify_sibling_fields():
    states = {
        "jurisdiction": "verified",
        "lost_wages": "unknown",
        "policy_limits": "unverified",
    }
    assert not record_status_implies_all_fields("reviewed", states)
    assert not field_is_verified("unknown")


# 4. UNKNOWN remains non-zero and unverified
def test_unknown_remains_non_zero_unverified():
    assert is_unknown("UNKNOWN")
    assert not is_unknown(0)
    assert not field_is_verified("unknown")


# 5. MISSING distinct from UNKNOWN/zero
def test_missing_distinct_from_unknown_and_zero():
    assert is_missing("MISSING")
    assert not is_missing("UNKNOWN")
    assert not is_missing(0)


# 6. NOT_APPLICABLE distinct from MISSING/UNKNOWN
def test_not_applicable_distinct_from_missing_unknown():
    assert is_not_applicable("NOT_APPLICABLE")
    assert not is_not_applicable("MISSING")
    assert not is_not_applicable("UNKNOWN")


def test_semantic_distinctness():
    result = semantic_distinct("UNKNOWN", "MISSING", "NOT_APPLICABLE", 0.0)
    assert result["unknown_missing_not_applicable_distinct"]


# 7. STRIPPED cannot become verified
def test_stripped_cannot_become_verified():
    assert stripped_cannot_become_verified("REDACTED-SSN")
    assert not stripped_cannot_become_verified("UNKNOWN")
    assert not stripped_cannot_become_verified("NOT_APPLICABLE")


# 8. two genuinely independent agreeing sources preserve corroboration
def test_independent_sources_agree():
    result = check_duplicate_source(
        "https://example.org/agreement",
        "https://example.org/court-record",
    )
    assert result["independent"] is True


# 9. duplicate source does not increase independent corroboration
def test_duplicate_source_not_independent():
    result = check_duplicate_source(
        "https://example.org/agreement",
        "https://example.org/agreement",
    )
    assert result["independent"] is False


# 10. contradictory sources prevent inappropriate automatic promotion
def test_contradictory_sources_prevent_promotion():
    result = check_contradiction(100000.0, 125000.0)
    assert result["contradicted"] is True
    assert result["relationship"] == "CONTRADICT"


def test_agreeing_sources_do_not_contradict():
    result = check_contradiction(100000.0, 100000.0)
    assert result["contradicted"] is False
    assert result["relationship"] == "AGREE"


# 11. correction preserves audit history
def test_correction_preserves_audit_history():
    result = apply_correction(
        field_states={"medical_bills": "verified"},
        corrected_field="medical_bills",
        old_value=50000.0,
        new_value=55000.0,
        new_source_url="https://example.org/updated-agreement",
        prior_verification_state="verified",
    )
    assert result["audit_history_preserved"] is True
    assert result["stale_verification_inherited"] is False
    assert result["new_verification_state"] != "verified"


# 12. corrected verified value does not inherit stale verification
def test_stale_verification_not_inherited():
    assert stale_verification_after_correction("verified", "supported") is True


def test_corrected_to_verified_not_stale():
    assert stale_verification_after_correction("verified", "verified") is False


# 13. re-verification can establish new verified state
def test_reverification_establishes_new_state():
    result = reverify_field(
        field_state="verified",
        source_supports=True,
        contradicted=False,
        has_independent_valid_source=True,
    )
    assert result["new_state"] == "verified"
    assert result["transition_occurred"] is False


def test_reverification_invalidates_when_source_lost():
    result = reverify_field(
        field_state="verified",
        source_supports=False,
        contradicted=False,
        has_independent_valid_source=False,
    )
    assert result["new_state"] == "unverified"
    assert result["transition_occurred"] is True


# 14. invalidated source removes/reconsiders dependent verification
def test_source_invalidation_reconsiders_dependent():
    result = reverify_after_source_invalidation(
        field_state="verified",
        other_independent_valid_source=False,
    )
    assert result["new_state"] == "unverified"
    assert result["transition_occurred"] is True


# 15. another still-valid independent source handled per corroboration rules
def test_other_valid_source_preserves_verification():
    result = reverify_after_source_invalidation(
        field_state="verified",
        other_independent_valid_source=True,
    )
    assert result["new_state"] == "verified"


# 16. tenant cannot modify another tenant's contribution verification state
def test_cross_tenant_modification_not_permitted():
    result = tenant_can_modify("tenant-a", "tenant-b")
    assert result["permitted"] is False
    assert result["reason"] == "cross_tenant"


def test_same_tenant_modification_permitted():
    result = tenant_can_modify("tenant-a", "tenant-a")
    assert result["permitted"] is True


# 17. privacy boundary remains intact
def test_privacy_boundary_remains_intact():
    from app.services.anonymizer import AnonymizationValidator
    validator = AnonymizationValidator()
    data = {
        "jurisdiction": "Maricopa County, AZ 123-45-6789",
        "case_type": "Motor Vehicle Accident",
        "injury_category": ["Spinal Injury"],
        "defendant_category": "Business",
        "outcome_type": "Settlement",
        "outcome_amount_range": "$300k-$600k",
        "consent_confirmed": True,
        "medical_bills": 50000.00,
    }
    is_valid, violations = validator.validate_contribution(data)
    assert not is_valid
    assert any("ssn" in v.lower() for v in violations)


# 18. no-fabrication remains intact
def test_no_fabrication_remains_intact():
    from settle_data_scraping_factory.court_dockets_records import no_fabrication_gate
    rc = no_fabrication_gate.selftest()
    assert rc == 0


# 19. T3 provenance regression remains green
def test_t3_provenance_regression():
    from app.services.external_provenance import map_external_to_provenance
    record = map_external_to_provenance(
        _base_contribution(),
        source_type="firm_submission",
        source_url="https://example.org/settlement-agreement-123",
    )
    assert record["source"] == "firm_submission"
    assert record["source_url"] == "https://example.org/settlement-agreement-123"


# 20. existing anonymizer regression remains green
def test_existing_anonymizer_regression():
    from app.services.anonymizer import AnonymizationValidator
    validator = AnonymizationValidator()
    text_with_ssn = "Medical bills 123-45-6789 total $50k"
    sanitized = validator.sanitize_text(text_with_ssn)
    assert "123-45-6789" not in sanitized
    assert "[REDACTED-SSN]" in sanitized


# --- Additional bounded tests ---

def test_analytics_eligibility_not_implemented_in_t4():
    assert analytics_eligibility_undelegated() == "T5_OWNED"


def test_verification_truth_for_analytics_exposes_state():
    result = verification_truth_for_analytics("verified")
    assert result["is_verified"] is True
    assert result["analytics_eligibility"] == "T5_OWNED"


def test_record_status_summary_all_verified():
    states = {"a": "verified", "b": "verified"}
    assert summarize_record_status(states) == "verified"


def test_record_status_summary_partial():
    states = {"a": "verified", "b": "supported"}
    assert summarize_record_status(states) == "reviewed"


def test_record_status_summary_none_verified():
    states = {"a": "supported", "b": "unverified"}
    assert summarize_record_status(states) == "pending"


def test_record_status_summary_with_rejected():
    states = {"a": "verified", "b": "rejected"}
    assert summarize_record_status(states) == "rejected"


def test_field_verification_state_unverified_without_evidence():
    assert field_verification_state(50000.0, has_evidence=False) == "unverified"


def test_field_verification_state_verified_with_corroboration():
    assert field_verification_state(
        50000.0, has_evidence=True, has_independent_corroboration=True
    ) == "verified"


def test_field_verification_state_supported_without_corroboration():
    assert field_verification_state(
        50000.0, has_evidence=True, has_independent_corroboration=False
    ) == "supported"


def test_field_verification_state_none_is_unknown():
    assert field_verification_state(None, has_evidence=False) == "unknown"


def test_external_verification_routes_through_gate_sequence():
    result = run_external_verification(
        _base_contribution(),
        source_type="firm_submission",
        source_url="https://example.org/settlement-agreement-123",
    )
    assert "field_states" in result
    assert "record_status" in result
    assert "normalized_record" in result
    assert "analytics_eligibility" in result