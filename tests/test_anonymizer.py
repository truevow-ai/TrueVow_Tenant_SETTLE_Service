"""
Unit tests for Anonymization Validator Service
"""

import pytest

from app.services.anonymizer import AnonymizationValidator


def test_validate_contribution_valid():
    """Test that valid anonymous data passes validation"""
    
    validator = AnonymizationValidator()
    
    valid_data = {
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
        "consent_confirmed": True
    }
    
    is_valid, violations = validator.validate_contribution(valid_data)
    assert is_valid, f"Should be valid, got violations: {violations}"
    assert len(violations) == 0


def test_detect_ssn():
    """Test SSN detection"""
    
    validator = AnonymizationValidator()
    
    # SSN in jurisdiction (should be caught)
    data_with_ssn = {
        "jurisdiction": "Maricopa County, AZ 123-45-6789",  # SSN in field
        "case_type": "Motor Vehicle Accident",
        "injury_category": ["Spinal Injury"],
        "defendant_category": "Business",
        "outcome_type": "Settlement",
        "outcome_amount_range": "$300k-$600k",
        "consent_confirmed": True,
        "medical_bills": 50000.00
    }
    
    is_valid, violations = validator.validate_contribution(data_with_ssn)
    assert not is_valid
    assert any("ssn" in v.lower() for v in violations)


def test_detect_phone_number():
    """Test phone number detection"""
    
    validator = AnonymizationValidator()
    
    data_with_phone = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Motor Vehicle Accident",
        "injury_category": ["Spinal Injury"],
        "primary_diagnosis": "Call 555-123-4567",  # Phone in field
        "defendant_category": "Business",
        "outcome_type": "Settlement",
        "outcome_amount_range": "$300k-$600k",
        "consent_confirmed": True,
        "medical_bills": 50000.00
    }
    
    is_valid, violations = validator.validate_contribution(data_with_phone)
    assert not is_valid
    assert any("phone" in v.lower() for v in violations)


def test_detect_email():
    """Test email detection"""
    
    validator = AnonymizationValidator()
    
    data_with_email = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Motor Vehicle Accident",
        "injury_category": ["Spinal Injury"],
        "primary_diagnosis": "Contact john@example.com",  # Email in field
        "defendant_category": "Business",
        "outcome_type": "Settlement",
        "outcome_amount_range": "$300k-$600k",
        "consent_confirmed": True,
        "medical_bills": 50000.00
    }
    
    is_valid, violations = validator.validate_contribution(data_with_email)
    assert not is_valid
    assert any("email" in v.lower() for v in violations)


def test_detect_person_name():
    """Test person name detection"""
    
    validator = AnonymizationValidator()
    
    data_with_name = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Motor Vehicle Accident",
        "injury_category": ["John Smith fell"],  # Name in field
        "defendant_category": "Business",
        "outcome_type": "Settlement",
        "outcome_amount_range": "$300k-$600k",
        "consent_confirmed": True,
        "medical_bills": 50000.00
    }
    
    is_valid, violations = validator.validate_contribution(data_with_name)
    assert not is_valid
    assert any("name" in v.lower() for v in violations)


def test_detect_specific_business_identifier():
    """Test detection of specific business identifiers (e.g., store #123)"""
    
    validator = AnonymizationValidator()
    
    data_with_specific_business = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Premises Liability (Slip/Trip/Fall)",
        "injury_category": ["Spinal Injury"],
        "defendant_category": "Kroger #342",  # Specific store number
        "outcome_type": "Settlement",
        "outcome_amount_range": "$300k-$600k",
        "consent_confirmed": True,
        "medical_bills": 50000.00
    }
    
    is_valid, violations = validator.validate_contribution(data_with_specific_business)
    assert not is_valid
    assert any("business identifier" in v.lower() for v in violations)


def test_validate_drop_down_values():
    """Test validation of drop-down values"""
    
    validator = AnonymizationValidator()
    
    # Invalid case type (not from drop-down)
    invalid_case_type = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Custom Case Type Not In List",  # Invalid
        "injury_category": ["Spinal Injury"],
        "defendant_category": "Business",
        "outcome_type": "Settlement",
        "outcome_amount_range": "$300k-$600k",
        "consent_confirmed": True,
        "medical_bills": 50000.00
    }
    
    is_valid, violations = validator.validate_contribution(invalid_case_type)
    assert not is_valid
    assert any("case_type" in v.lower() for v in violations)


def test_check_for_liability_language():
    """Test detection of forbidden liability language"""
    
    validator = AnonymizationValidator()
    
    # Should detect liability language
    liability_text = "The defendant was negligent and at fault for the accident"
    forbidden_phrases = validator.check_for_liability_language(liability_text)
    assert len(forbidden_phrases) > 0
    assert "negligent" in forbidden_phrases or "at fault" in forbidden_phrases
    
    # Safe text (no liability language)
    safe_text = "Settlement for spinal injury case"
    forbidden_phrases = validator.check_for_liability_language(safe_text)
    assert len(forbidden_phrases) == 0


def test_sanitize_text():
    """Test text sanitization (for legacy data cleanup)"""
    
    validator = AnonymizationValidator()
    
    # Text with SSN
    text_with_ssn = "Medical bills 123-45-6789 total $50k"
    sanitized = validator.sanitize_text(text_with_ssn)
    assert "123-45-6789" not in sanitized
    assert "[REDACTED-SSN]" in sanitized
    
    # Text with phone
    text_with_phone = "Call 555-123-4567 for details"
    sanitized = validator.sanitize_text(text_with_phone)
    assert "555-123-4567" not in sanitized
    assert "[REDACTED-PHONE]" in sanitized

