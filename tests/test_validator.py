"""
Unit tests for Data Validator Service
"""

import pytest

from app.services.validator import DataValidator
from app.models.case_bank import ContributionRequest


# Year-2 mandatory v2 fields — every ContributionRequest test fixture must
# supply these, else Pydantic rejects the payload before the validator runs.
_V2_FIELDS = {
    "intake_version_id": "v2",
    "economic_strength_at_intake": "moderate",
    "final_treatment_escalation": "injections",
    "settlement_band": "150k_500k",
    "policy_limit_known": True,
    "time_to_resolution": "12_24_months",
    "litigation_filed": False,
}


def test_validate_jurisdiction():
    """Test jurisdiction format validation"""
    
    validator = DataValidator()
    
    # Valid formats
    errors = validator._validate_jurisdiction("Maricopa County, AZ")
    assert len(errors) == 0
    
    errors = validator._validate_jurisdiction("Los Angeles County, CA")
    assert len(errors) == 0
    
    # Invalid formats
    errors = validator._validate_jurisdiction("MaricopaAZ")  # Missing comma
    assert len(errors) > 0
    
    errors = validator._validate_jurisdiction("Maricopa, Arizona")  # Full state name
    assert len(errors) > 0
    
    errors = validator._validate_jurisdiction("M, AZ")  # County too short
    assert len(errors) > 0


def test_validate_financial_amounts():
    """Test financial amount validation"""
    
    validator = DataValidator()
    
    # Valid amounts
    errors = validator._validate_financial_amounts(50000.00, 10000.00)
    assert len(errors) == 0
    
    # Invalid: negative medical bills
    errors = validator._validate_financial_amounts(-1000.00, None)
    assert len(errors) > 0
    
    # Invalid: medical bills too high
    errors = validator._validate_financial_amounts(20_000_000.00, None)
    assert len(errors) > 0
    
    # Invalid: negative lost wages
    errors = validator._validate_financial_amounts(50000.00, -500.00)
    assert len(errors) > 0


def test_validate_contribution():
    """Test full contribution validation"""
    
    validator = DataValidator()
    
    # Valid contribution
    valid_request = ContributionRequest(
        jurisdiction="Maricopa County, AZ",
        case_type="Motor Vehicle Accident",
        injury_category=["Spinal Injury"],
        treatment_type=["Physical Therapy"],
        duration_of_treatment="6-12 months",
        imaging_findings=["Herniated Disc"],
        medical_bills=50000.00,
        defendant_category="Business",
        outcome_type="Settlement",
        outcome_amount_range="$300k-$600k",
        consent_confirmed=True,
        **_V2_FIELDS,
    )
    
    is_valid, errors = validator.validate_contribution(valid_request)
    assert is_valid, f"Should be valid, got errors: {errors}"
    assert len(errors) == 0
    
    # Invalid: missing consent
    invalid_request = ContributionRequest(
        jurisdiction="Maricopa County, AZ",
        case_type="Motor Vehicle Accident",
        injury_category=["Spinal Injury"],
        treatment_type=[],
        duration_of_treatment="6-12 months",
        imaging_findings=[],
        medical_bills=50000.00,
        defendant_category="Business",
        outcome_type="Settlement",
        outcome_amount_range="$300k-$600k",
        consent_confirmed=False,  # Invalid
        **_V2_FIELDS,
    )
    
    is_valid, errors = validator.validate_contribution(invalid_request)
    assert not is_valid
    assert any("consent" in error.lower() for error in errors)


def test_check_for_outliers():
    """Test outlier detection"""
    
    validator = DataValidator()
    
    # Normal case
    normal_request = ContributionRequest(
        jurisdiction="Maricopa County, AZ",
        case_type="Motor Vehicle Accident",
        injury_category=["Spinal Injury"],
        treatment_type=["Physical Therapy"],
        duration_of_treatment="6-12 months",
        imaging_findings=["Herniated Disc"],
        medical_bills=50000.00,
        defendant_category="Business",
        outcome_type="Settlement",
        outcome_amount_range="$150k-$225k",  # ~3x multiplier (normal)
        consent_confirmed=True,
        **_V2_FIELDS,
    )
    
    warnings = validator._check_for_outliers(normal_request)
    assert len(warnings) == 0
    
    # Outlier: unusually high multiplier
    outlier_request = ContributionRequest(
        jurisdiction="Maricopa County, AZ",
        case_type="Motor Vehicle Accident",
        injury_category=["Spinal Injury"],
        treatment_type=["Physical Therapy"],
        duration_of_treatment="6-12 months",
        imaging_findings=["Herniated Disc"],
        medical_bills=10000.00,
        defendant_category="Business",
        outcome_type="Settlement",
        outcome_amount_range="$1M+",  # >100x multiplier (outlier)
        consent_confirmed=True,
        **_V2_FIELDS,
    )
    
    warnings = validator._check_for_outliers(outlier_request)
    assert len(warnings) > 0

