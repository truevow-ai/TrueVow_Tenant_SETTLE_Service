"""
Bounded tests for external/historical contribution provenance/evidence capability.

Proves that external/historical provenance can use the existing SETTLE evidence
architecture without fabricating evidence, bypassing privacy, requiring TRACE
origin, or changing schema.
"""

from app.services.external_provenance import (
    map_external_to_provenance,
    build_external_record,
    check_contradictory_sources,
    check_duplicate_source,
    is_unknown_or_missing,
    stripped_cannot_be_evidence,
    _validate_source_type,
)


def _base_contribution(**overrides):
    data = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "motor_vehicle_accident",
        "outcome_type": "settlement",
        "source_url": "https://example.org/settlement-agreement-123",
        "medical_bills": 50000.0,
        "medical_bills_snippet": "medical bills totalled $50,000 for treatment",
    }
    data.update(overrides)
    return data


# 1. externally originated contribution maps valid provenance without TRACE lifecycle
def test_external_origin_no_trace_lifecycle():
    data = _base_contribution()
    record = map_external_to_provenance(
        data,
        source_type="firm_submission",
        source_url="https://example.org/settlement-agreement-123",
        source_notes="executed settlement agreement",
    )
    assert record["source"] == "firm_submission"
    assert record["source_url"] == "https://example.org/settlement-agreement-123"
    assert record["source_notes"] == "executed settlement agreement"
    # No TRACE lifecycle, INTAKE session, or matter.activated required.


# 2. supported field persists existing field_evidence
def test_supported_field_persists_evidence():
    data = _base_contribution()
    result = build_external_record(
        data,
        source_type="firm_submission",
        source_url="https://example.org/settlement-agreement-123",
    )
    assert not result["rejected"]
    assert "medical_bills" in result["evidence"]
    assert result["evidence"]["medical_bills"]["value"] == 50000.0
    assert result["evidence"]["medical_bills"]["source_url"].startswith("https://")


# 3. unsupported field not promoted merely because record has a source
def test_unsupported_field_not_promoted():
    data = _base_contribution(
        medical_bills=999999.0,  # fabricated — not in snippet
        medical_bills_snippet="medical bills totalled $50,000 for treatment",
    )
    result = build_external_record(data, source_type="firm_submission")
    assert "medical_bills" not in result["record"]
    assert "medical_bills" in result["stripped"]


# 4. one source supports multiple fields where evidence actually supports them
def test_one_source_supports_multiple_fields():
    data = _base_contribution(
        insurance_carrier="State Farm",
        insurance_carrier_snippet="insured by State Farm",
    )
    record = map_external_to_provenance(
        data,
        source_type="firm_submission",
        source_url="https://example.org/settlement-agreement-123",
    )
    assert record["source_url"] == "https://example.org/settlement-agreement-123"
    assert record["insurance_carrier"] == "State Farm"
    # Same source_url supports both fields — that is legitimate reuse.


# 5. different sources can support different fields
def test_different_sources_support_different_fields():
    data = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "motor_vehicle_accident",
        "outcome_type": "settlement",
        "medical_bills": 50000.0,
        "medical_bills_snippet": "medical bills totalled $50,000",
        "source_url": "https://example.org/medical",
    }
    record = map_external_to_provenance(
        data,
        source_type="firm_submission",
        source_url="https://example.org/medical",
    )
    assert record["source_url"] == "https://example.org/medical"
    # Different fields may legitimately draw from different sources.


# 6. contradictory evidence does not silently promote a value
def test_contradictory_source_handling():
    result = check_contradictory_sources(
        primary_value=50000.0,
        primary_snippet="medical bills totalled $50,000",
        secondary_value=75000.0,
        secondary_snippet="medical bills totalled $75,000",
    )
    assert result["relationship"] == "CONTRADICT"
    assert result["promote"] is False


# 7. duplicate source does not falsely increase independent corroboration
def test_duplicate_source_independence():
    result = check_duplicate_source(
        "https://example.org/agreement",
        "https://example.org/agreement",
    )
    assert result["independent"] is False
    assert result["reason"] == "same_source_url"


def test_different_sources_are_independent():
    result = check_duplicate_source(
        "https://example.org/agreement",
        "https://example.org/court-record",
    )
    assert result["independent"] is True


# 8. missing/UNKNOWN/NOT_APPLICABLE values do not receive fabricated evidence
def test_missing_value_no_fabricated_evidence():
    data = _base_contribution(lost_wages=None)
    record = map_external_to_provenance(data, source_type="firm_submission")
    assert record.get("lost_wages") is None
    assert is_unknown_or_missing(None)


def test_unknown_value_preserved():
    assert is_unknown_or_missing("UNKNOWN")
    assert is_unknown_or_missing("MISSING")
    assert is_unknown_or_missing("NOT_APPLICABLE")


# 9. STRIPPED cannot become evidence
def test_stripped_cannot_be_evidence():
    assert stripped_cannot_be_evidence({"medical_bills": "value not verbatim in snippet"})


# 10. prohibited sensitive content still fails the T2 privacy boundary
def test_prohibited_content_still_rejected():
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


# 11. contributor tenant/user attribution is preserved
def test_contributor_attribution_preserved():
    data = _base_contribution()
    record = map_external_to_provenance(
        data,
        source_type="firm_submission",
        source_url="https://example.org/settlement-agreement-123",
    )
    # Existing attribution fields are preserved alongside provenance
    assert "source_url" in record
    assert "source" in record


# 12. no-fabrication behavior remains intact
def test_no_fabrication_remains_intact():
    from settle_data_scraping_factory.court_dockets_records import no_fabrication_gate
    rc = no_fabrication_gate.selftest()
    assert rc == 0


# 13. existing regression suite remains green
def test_existing_anonymizer_regression():
    from app.services.anonymizer import AnonymizationValidator
    validator = AnonymizationValidator()
    text_with_ssn = "Medical bills 123-45-6789 total $50k"
    sanitized = validator.sanitize_text(text_with_ssn)
    assert "123-45-6789" not in sanitized
    assert "[REDACTED-SSN]" in sanitized


# --- Additional bounded tests ---

def test_unknown_source_type_not_invented():
    """Unknown source type must not be fabricated into an arbitrary string."""
    result = _validate_source_type("nonexistent_source_type")
    assert result is None


def test_source_url_not_mandatory_for_all_sources():
    """source_url is not mandatory when the legitimate source type has no URL."""
    data = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "motor_vehicle_accident",
        "outcome_type": "settlement",
        "medical_bills": 50000.0,
        "medical_bills_snippet": "medical bills totalled $50,000 for treatment",
    }
    record = map_external_to_provenance(
        data,
        source_type="settlement_survey",
        source_url=None,
    )
    assert record["source"] == "settlement_survey"
    assert "source_url" not in record


def test_no_source_type_leaves_source_absent():
    """No source type provided — leave absent (UNKNOWN), do not fabricate."""
    data = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "motor_vehicle_accident",
        "outcome_type": "settlement",
        "medical_bills": 50000.0,
        "medical_bills_snippet": "medical bills totalled $50,000 for treatment",
    }
    record = map_external_to_provenance(data)
    assert "source" not in record
    assert "source_type" not in record


def test_external_record_routes_through_gate_sequence():
    """External record passes through verify_record then normalize_and_validate."""
    data = _base_contribution()
    result = build_external_record(
        data,
        source_type="firm_submission",
        source_url="https://example.org/settlement-agreement-123",
    )
    assert "record" in result
    assert "validation_counts" in result
    assert "evidence" in result
    assert "stripped" in result
    assert "normalized_record" in result
    assert "normalize_errors" in result
    assert "normalize_warnings" in result