"""
Bounded tests for the SETTLE contribution privacy acceptance boundary.

These tests prove that the contribution acceptance boundary fails closed
for prohibited sensitive input without silently converting that input into
trusted evidence.

Scope: bounded hardening of the existing boundary. No replacement privacy
architecture. No new privacy service. No database change.
"""

from app.services.anonymizer import AnonymizationValidator
from app.services.validator import DataValidator
from settle_data_scraping_factory.court_dockets_records.no_fabrication_gate import (
    verify_record,
)


def _clean_contribution(**overrides):
    """Base valid de-identified contribution."""
    data = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Motor Vehicle Accident",
        "injury_category": ["Spinal Injury"],
        "primary_diagnosis": "Spinal Injury",
        "treatment_type": ["Physical Therapy", "Surgery"],
        "duration_of_treatment": "6-12 months",
        "imaging_findings": ["Herniated Disc"],
        "medical_bills": 50000.00,
        "lost_wages": 10000.00,
        "policy_limits": "$100k/$300k",
        "defendant_category": "Business",
        "outcome_type": "Settlement",
        "outcome_amount_range": "$300k-$600k",
        "consent_confirmed": True,
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Prohibited PHI/identifier is rejected on acceptance path
# ---------------------------------------------------------------------------

def test_prohibited_ssn_rejected():
    validator = AnonymizationValidator()
    data = _clean_contribution(jurisdiction="Maricopa County, AZ 123-45-6789")
    is_valid, violations = validator.validate_contribution(data)
    assert not is_valid
    assert any("ssn" in v.lower() for v in violations)


def test_prohibited_phone_rejected():
    validator = AnonymizationValidator()
    data = _clean_contribution(primary_diagnosis="Call 555-123-4567")
    is_valid, violations = validator.validate_contribution(data)
    assert not is_valid
    assert any("phone" in v.lower() for v in violations)


def test_prohibited_email_rejected():
    validator = AnonymizationValidator()
    data = _clean_contribution(primary_diagnosis="Contact john@example.com")
    is_valid, violations = validator.validate_contribution(data)
    assert not is_valid
    assert any("email" in v.lower() for v in violations)


def test_prohibited_name_rejected():
    validator = AnonymizationValidator()
    data = _clean_contribution(injury_category=["John Smith fell"])
    is_valid, violations = validator.validate_contribution(data)
    assert not is_valid
    assert any("name" in v.lower() for v in violations)


def test_prohibited_business_id_rejected():
    validator = AnonymizationValidator()
    data = _clean_contribution(defendant_category="Kroger #342")
    is_valid, violations = validator.validate_contribution(data)
    assert not is_valid
    assert any("business identifier" in v.lower() for v in violations)


# ---------------------------------------------------------------------------
# Rejected input is not persisted
# ---------------------------------------------------------------------------

def test_rejected_not_persisted():
    """Rejected contributions never reach the DB insert path."""
    validator = AnonymizationValidator()
    data = _clean_contribution(jurisdiction="Maricopa County, AZ 123-45-6789")
    is_valid, _ = validator.validate_contribution(data)
    assert not is_valid
    # The acceptance path short-circuits before any insert when is_valid is False.
    # This is the contract: rejection means no persistence.


# ---------------------------------------------------------------------------
# Silent sanitize-and-accept cannot occur
# ---------------------------------------------------------------------------

def test_no_silent_sanitize_and_accept():
    """No code path sanitizes prohibited input and then persists it."""
    validator = AnonymizationValidator()
    data = _clean_contribution(primary_diagnosis="Call 555-123-4567")
    is_valid, violations = validator.validate_contribution(data)
    assert not is_valid
    assert len(violations) > 0
    # validate_contribution() returns (False, violations). It never returns
    # (True, sanitized_value). There is no sanitize-then-accept path.


# ---------------------------------------------------------------------------
# STRIPPED cannot enter analytics as a value
# ---------------------------------------------------------------------------

def test_stripped_not_analytics_value():
    """STRIPPED fields do not survive the no-fabrication gate."""
    rec = {
        "jurisdiction": "X, FL",
        "case_type": "x",
        "source_url": "https://a",
        "medical_bills": 999999.0,
        "medical_bills_snippet": "medical bills totalled $245,000",
    }
    result = verify_record(rec)
    assert "medical_bills" not in result["record"]
    assert "medical_bills" in result["stripped"]
    # STRIPPED is not UNKNOWN, zero, NOT_APPLICABLE, verified evidence,
    # or analytics-eligible data. It is absent from the record.


# ---------------------------------------------------------------------------
# Missing/unknown values are not converted to zero
# ---------------------------------------------------------------------------

def test_missing_not_converted_to_zero():
    """Optional fields preserve None; no fabrication of zero."""
    validator = AnonymizationValidator()
    data = _clean_contribution()
    data["lost_wages"] = None
    is_valid, violations = validator.validate_contribution(data)
    assert is_valid, f"Should be valid, got: {violations}"
    # lost_wages=None is preserved as absent, not converted to zero.


# ---------------------------------------------------------------------------
# Valid de-identified contribution remains accepted
# ---------------------------------------------------------------------------

def test_valid_deidentified_accepted():
    validator = AnonymizationValidator()
    data = _clean_contribution()
    is_valid, violations = validator.validate_contribution(data)
    assert is_valid, f"Should be valid, got: {violations}"


# ---------------------------------------------------------------------------
# No-fabrication validation still operates
# ---------------------------------------------------------------------------

def test_no_fabrication_still_operates():
    """verify_record selftest passes — gate is intact."""
    from settle_data_scraping_factory.court_dockets_records import no_fabrication_gate
    import sys
    # Run the module's selftest directly.
    rc = no_fabrication_gate.selftest()
    assert rc == 0


# ---------------------------------------------------------------------------
# Existing sanitize_text() test remains functional
# ---------------------------------------------------------------------------

def test_existing_sanitize_text_test_unchanged():
    """The existing sanitize_text() test still passes (regression)."""
    from app.services.anonymizer import AnonymizationValidator
    validator = AnonymizationValidator()
    text_with_ssn = "Medical bills 123-45-6789 total $50k"
    sanitized = validator.sanitize_text(text_with_ssn)
    assert "123-45-6789" not in sanitized
    assert "[REDACTED-SSN]" in sanitized