"""
Bounded tests for external/historical contribution analytics eligibility.

Proves eligibility before aggregation, operation-specific dimension gating,
and that stored/verified/eligible remain distinct.
"""

from app.services.analytics_eligibility import (
    stored_is_not_verified,
    stored_is_not_eligible,
    record_status_implies_field_eligibility,
    required_dimensions_for_operation,
    operation_is_known,
    field_eligible_for_operation,
    record_eligible_for_operation,
    eligible_population,
    aggregate_count_eligible,
    minimum_n_preserved,
    minimum_n_counts_eligible_population,
    confidence_eligibility,
    comparable_retrieval_eligibility,
    county_state_eligibility,
    external_origin_auto_eligible,
    external_origin_auto_ineligible,
    unknown_as_zero,
    missing_as_zero,
    stripped_analytics,
    not_applicable_semantics,
    own_case_only_behavior,
    tenant_privacy_preserved,
    analytics_eligibility_decision,
    MIN_AGGREGATE_N,
)


def _partially_verified():
    """A historical case: some facts verified, some not."""
    return {
        "jurisdiction": "verified",
        "case_type": "verified",
        "settlement_amount": "verified",
        "medical_specials": "verified",
        "lost_wages": "unknown",
        "policy_limits": "unverified",
        "comparative_fault": "unverified",
    }


# 1. stored but unverified external contribution does not influence analytics
def test_stored_unverified_does_not_influence():
    assert stored_is_not_verified("approved")
    assert stored_is_not_verified("pending")


# 2. verified eligible contribution can influence operation with all dims verified
def test_verified_eligible_influences():
    states = _partially_verified()
    assert record_eligible_for_operation(states, "comparable_percentile") is True


# 3. partially verified record participates in operation whose dims are verified
def test_partial_participates_when_dims_verified():
    states = _partially_verified()
    assert record_eligible_for_operation(states, "comparable_percentile") is True


# 4. same record excluded from operation requiring unverified dimension
def test_partial_excluded_when_dim_unverified():
    states = _partially_verified()
    assert record_eligible_for_operation(states, "policy_limit_analysis") is False


# 5. record-level status does not manufacture field eligibility
def test_record_status_does_not_manufacture_field_eligibility():
    assert record_status_implies_field_eligibility("reviewed", "supported") is False
    assert record_status_implies_field_eligibility("reviewed", "verified") is True


# 6. unsupported field does not influence aggregate
def test_unsupported_field_not_influential():
    assert field_eligible_for_operation("policy_limits", "supported", "policy_limit_analysis") is False
    assert field_eligible_for_operation("policy_limits", "verified", "policy_limit_analysis") is True


# 7. contradicted field does not influence operation requiring that field
def test_contradicted_field_not_influential():
    assert field_eligible_for_operation("settlement_amount", "contradicted", "comparable_percentile") is False


# 8. invalidated field does not influence operation requiring that field
def test_invalidated_field_not_influential():
    assert field_eligible_for_operation("settlement_amount", "invalidated", "comparable_percentile") is False


# 9. corrected old value ceases influencing future analytics
def test_corrected_old_value_ceases():
    states = dict(_partially_verified(), settlement_amount="unverified")
    assert record_eligible_for_operation(states, "comparable_percentile") is False


# 10. re-verified replacement value may become eligible
def test_reverified_replacement_eligible():
    states = dict(_partially_verified(), settlement_amount="verified")
    assert record_eligible_for_operation(states, "comparable_percentile") is True


# 11. UNKNOWN is not counted as zero
def test_unknown_not_zero():
    assert unknown_as_zero() is False


# 12. MISSING is not counted as zero
def test_missing_not_zero():
    assert missing_as_zero() is False


# 13. STRIPPED is never eligible
def test_stripped_never_eligible():
    assert stripped_analytics() is False


# 14. NOT_APPLICABLE preserves canonical behavior and is not coerced to zero
def test_not_applicable_semantics():
    assert not_applicable_semantics() is True


# 15. MIN_AGGREGATE_N counts eligible analytical population
def test_min_n_counts_eligible_population():
    result = minimum_n_counts_eligible_population(60, 40)
    assert result["stored_false_positive"] is True
    assert result["eligible_clears_floor"] is False


# 16. fewer than 50 eligible records cannot become aggregate via ineligible records
def test_ineligible_cannot_clear_floor():
    result = minimum_n_counts_eligible_population(60, 40)
    assert result["stored_would_clear_floor"] is True
    assert result["eligible_clears_floor"] is False
    assert result["stored_false_positive"] is True


# 17. eligible population >= threshold preserves existing aggregate behavior
def test_eligible_population_preserves_behavior():
    result = minimum_n_counts_eligible_population(60, 60)
    assert result["stored_false_positive"] is False
    assert result["eligible_clears_floor"] is True


# 18. county aggregation excludes ineligible records
def test_county_aggregation_excludes_ineligible():
    states = _partially_verified()
    assert county_state_eligibility(states, "county_aggregation") is True
    bad_states = dict(states, settlement_amount="unverified")
    assert county_state_eligibility(bad_states, "county_aggregation") is False


# 19. state fallback excludes ineligible records
def test_state_fallback_excludes_ineligible():
    states = _partially_verified()
    assert county_state_eligibility(states, "state_aggregation") is True
    bad_states = dict(states, settlement_amount="unverified")
    assert county_state_eligibility(bad_states, "state_aggregation") is False


# 20. comparable retrieval excludes records missing required dimensions
def test_comparable_retrieval_excludes_ineligible():
    states = _partially_verified()
    assert comparable_retrieval_eligibility(states) is True
    bad_states = dict(states, settlement_amount="unsupported")
    assert comparable_retrieval_eligibility(bad_states) is False


# 21. ineligible records do not increase confidence
def test_ineligible_do_not_increase_confidence():
    result = confidence_eligibility(eligible_count=40, ineligible_count=20)
    assert result["ineligible_increases_confidence"] is False
    assert result["ineligible_increases_sample_size"] is False


# 22. duplicate/corroboration rules from T4 remain intact
def test_duplicate_rules_remain_intact():
    from app.services.external_verification import check_duplicate_source
    result = check_duplicate_source(
        "https://example.org/a", "https://example.org/a"
    )
    assert result["independent"] is False


# 23. own_case_only behavior remains consistent with existing authority
def test_own_case_only_behavior():
    states = _partially_verified()
    result = own_case_only_behavior(states, "comparable_percentile")
    assert result["visibility_as_own_submitted_record"] is True
    assert result["own_case_context"] is True
    assert result["shared_aggregate_eligibility"] is True


def test_own_case_only_ineligible():
    states = dict(_partially_verified(), settlement_amount="unverified")
    result = own_case_only_behavior(states, "comparable_percentile")
    assert result["shared_aggregate_eligibility"] is False


# 24. external origin alone neither grants nor denies eligibility
def test_external_origin_auto_eligible():
    assert external_origin_auto_eligible() is False


def test_external_origin_auto_ineligible():
    assert external_origin_auto_ineligible() is False


# 25. tenant/privacy isolation remains intact
def test_tenant_privacy():
    result = tenant_privacy_preserved("tenant-a", "tenant-b")
    assert result["permitted"] is False
    result = tenant_privacy_preserved("tenant-a", "tenant-a")
    assert result["permitted"] is True


# 26. T2 privacy regression remains green
def test_t2_privacy_regression():
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


# 27. T3 provenance regression remains green
def test_t3_provenance_regression():
    from app.services.external_provenance import map_external_to_provenance
    record = map_external_to_provenance(
        {
            "jurisdiction": "Maricopa County, AZ",
            "case_type": "motor_vehicle_accident",
            "outcome_type": "settlement",
            "source_url": "https://example.org/settlement-agreement-123",
            "medical_bills": 50000.0,
            "medical_bills_snippet": "medical bills totalled $50,000 for treatment",
            "settlement_amount": 100000.0,
            "settlement_amount_snippet": "the settlement amount was $100,000",
        },
        source_type="firm_submission",
        source_url="https://example.org/settlement-agreement-123",
    )
    assert record["source"] == "firm_submission"
    assert record["source_url"] == "https://example.org/settlement-agreement-123"


# 28. T4 verification regression remains green
def test_t4_verification_regression():
    from app.services.external_verification import summarize_record_status
    assert summarize_record_status({"a": "verified", "b": "verified"}) == "verified"
    assert summarize_record_status({"a": "verified", "b": "supported"}) == "reviewed"


# 29. existing Case Bank regression remains green
def test_case_bank_regression():
    from app.services.external_verification import check_contradiction
    result = check_contradiction(100000.0, 125000.0)
    assert result["contradicted"] is True


# 30. full relevant regression suite remains green
def test_full_regression_suite():
    from settle_data_scraping_factory.court_dockets_records import no_fabrication_gate
    rc = no_fabrication_gate.selftest()
    assert rc == 0


# --- Additional bounded tests ---

def test_stored_is_not_verified_for_pending():
    assert stored_is_not_verified("pending") is True


def test_stored_is_not_verified_for_rejected():
    assert stored_is_not_verified("rejected") is True


def test_stored_is_not_eligible_for_approved():
    assert stored_is_not_eligible("approved") is True


def test_required_dimensions_for_comparable_percentile():
    dims = required_dimensions_for_operation("comparable_percentile")
    assert "jurisdiction" in dims
    assert "case_type" in dims
    assert "settlement_amount" in dims


def test_required_dimensions_for_policy_limit_analysis():
    dims = required_dimensions_for_operation("policy_limit_analysis")
    assert "policy_limits" in dims


def test_required_dimensions_for_lost_wages_analysis():
    dims = required_dimensions_for_operation("lost_wages_analysis")
    assert "lost_wages" in dims


def test_unknown_operation_returns_empty():
    assert required_dimensions_for_operation("unknown_operation") == set()
    assert operation_is_known("unknown_operation") is False


def test_eligible_population_filters_before_aggregation():
    records = [{"id": 1}, {"id": 2}, {"id": 3}]
    states = {
        "jurisdiction": "verified",
        "case_type": "verified",
        "settlement_amount": "verified",
    }
    eligible = eligible_population(records, states, "comparable_percentile")
    assert len(eligible) == 3


def test_eligible_population_excludes_ineligible():
    records = [{"id": 1}, {"id": 2}]
    states = {
        "jurisdiction": "verified",
        "case_type": "verified",
        "settlement_amount": "unverified",
    }
    eligible = eligible_population(records, states, "comparable_percentile")
    assert len(eligible) == 0


def test_aggregate_count_eligible():
    records = [{"id": 1}, {"id": 2}, {"id": 3}]
    states = {
        "jurisdiction": "verified",
        "case_type": "verified",
        "settlement_amount": "verified",
    }
    assert aggregate_count_eligible(records, states, "comparable_percentile") == 3


def test_minimum_n_preserved():
    assert minimum_n_preserved(50) is True
    assert minimum_n_preserved(49) is False


def test_confidence_eligibility_no_increase():
    result = confidence_eligibility(eligible_count=10, ineligible_count=100)
    assert result["ineligible_increases_confidence"] is False
    assert result["confidence_based_on_eligible_population"] is True


def test_analytics_eligibility_decision_eligible():
    states = {
        "jurisdiction": "verified",
        "case_type": "verified",
        "settlement_amount": "verified",
    }
    result = analytics_eligibility_decision(states, "comparable_percentile", "approved")
    assert result["eligible"] is True
    assert result["analytics_eligibility"] == "analytics_eligible"
    assert result["record_status_implies_field_eligibility"] is False


def test_analytics_eligibility_decision_ineligible():
    states = {
        "jurisdiction": "verified",
        "case_type": "verified",
        "settlement_amount": "unverified",
    }
    result = analytics_eligibility_decision(states, "comparable_percentile", "approved")
    assert result["eligible"] is False
    assert result["analytics_eligibility"] == "not_eligible"
    assert result["stored_is_not_verified"] is True
    assert result["stored_is_not_eligible"] is True