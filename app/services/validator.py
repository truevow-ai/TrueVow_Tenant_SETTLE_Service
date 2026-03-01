"""
Data Validator Service

Validates all incoming data for correctness, completeness, and compliance.
Works in tandem with AnonymizationValidator to ensure data quality.
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from app.models.case_bank import (
    ContributionRequest,
    VALID_CASE_TYPES,
    VALID_OUTCOME_RANGES,
    VALID_OUTCOME_TYPES,
    VALID_DEFENDANT_CATEGORIES,
    VALID_POLICY_LIMITS,
    VALID_DURATION_OF_TREATMENT
)

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Data validator for settlement contributions and queries.
    
    Validates:
    - Data types and formats
    - Required fields
    - Value ranges
    - Drop-down selections
    - Business logic constraints
    """
    
    # US States (2-letter codes)
    VALID_STATES = [
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
        "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
        "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
        "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
        "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
    ]
    
    # Financial limits
    MIN_MEDICAL_BILLS = 1
    MAX_MEDICAL_BILLS = 10_000_000
    MIN_LOST_WAGES = 0
    MAX_LOST_WAGES = 5_000_000
    
    def validate_contribution(
        self,
        request: ContributionRequest
    ) -> Tuple[bool, List[str]]:
        """
        Validate a settlement contribution request.
        
        Args:
            request: ContributionRequest object
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate jurisdiction
        errors.extend(self._validate_jurisdiction(request.jurisdiction))
        
        # Validate case type
        if request.case_type not in VALID_CASE_TYPES:
            errors.append(
                f"Invalid case_type: '{request.case_type}'. "
                f"Must be one of: {', '.join(VALID_CASE_TYPES)}"
            )
        
        # Validate injury category (at least one required)
        if not request.injury_category or len(request.injury_category) == 0:
            errors.append("At least one injury_category is required")
        
        # Validate financial amounts
        errors.extend(self._validate_financial_amounts(
            request.medical_bills,
            request.lost_wages
        ))
        
        # Validate policy limits
        if request.policy_limits and request.policy_limits not in VALID_POLICY_LIMITS:
            errors.append(
                f"Invalid policy_limits: '{request.policy_limits}'. "
                f"Must be one of: {', '.join(VALID_POLICY_LIMITS)}"
            )
        
        # Validate duration of treatment
        if request.duration_of_treatment and request.duration_of_treatment not in VALID_DURATION_OF_TREATMENT:
            errors.append(
                f"Invalid duration_of_treatment: '{request.duration_of_treatment}'. "
                f"Must be one of: {', '.join(VALID_DURATION_OF_TREATMENT)}"
            )
        
        # Validate defendant category
        if request.defendant_category not in VALID_DEFENDANT_CATEGORIES:
            errors.append(
                f"Invalid defendant_category: '{request.defendant_category}'. "
                f"Must be one of: {', '.join(VALID_DEFENDANT_CATEGORIES)}"
            )
        
        # Validate outcome type
        if request.outcome_type not in VALID_OUTCOME_TYPES:
            errors.append(
                f"Invalid outcome_type: '{request.outcome_type}'. "
                f"Must be one of: {', '.join(VALID_OUTCOME_TYPES)}"
            )
        
        # Validate outcome amount range
        if request.outcome_amount_range not in VALID_OUTCOME_RANGES:
            errors.append(
                f"Invalid outcome_amount_range: '{request.outcome_amount_range}'. "
                f"Must be one of: {', '.join(VALID_OUTCOME_RANGES)}"
            )
        
        # Validate consent is confirmed
        if not request.consent_confirmed:
            errors.append("Consent must be confirmed to submit contribution")
        
        # Check for outliers (flag for manual review)
        outlier_warnings = self._check_for_outliers(request)
        if outlier_warnings:
            logger.warning(f"Outlier warnings: {outlier_warnings}")
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.warning(f"Validation failed: {errors}")
        else:
            logger.info("Validation passed")
        
        return is_valid, errors
    
    def _validate_jurisdiction(self, jurisdiction: str) -> List[str]:
        """
        Validate jurisdiction format and state code.
        
        Args:
            jurisdiction: Jurisdiction string (e.g., "Maricopa County, AZ")
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check format
        if ',' not in jurisdiction:
            errors.append(
                "Jurisdiction must be in format 'County, ST' (e.g., 'Maricopa County, AZ')"
            )
            return errors
        
        parts = jurisdiction.split(',')
        if len(parts) != 2:
            errors.append(
                "Jurisdiction must have exactly one comma separating county and state"
            )
            return errors
        
        county, state = parts[0].strip(), parts[1].strip()
        
        # Validate county
        if len(county) < 2:
            errors.append("County name must be at least 2 characters")
        
        if not county[0].isupper():
            errors.append("County name must be capitalized")
        
        # Validate state
        if len(state) != 2 or not state.isalpha():
            errors.append("State must be 2-letter code (e.g., 'AZ', 'CA')")
        elif state.upper() not in self.VALID_STATES:
            errors.append(f"Invalid state code: '{state}'. Must be valid US state.")
        
        return errors
    
    def _validate_financial_amounts(
        self,
        medical_bills: float,
        lost_wages: Optional[float]
    ) -> List[str]:
        """
        Validate financial amounts are reasonable.
        
        Args:
            medical_bills: Medical bills amount
            lost_wages: Lost wages amount (optional)
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Validate medical bills
        if medical_bills < self.MIN_MEDICAL_BILLS:
            errors.append(
                f"medical_bills must be at least ${self.MIN_MEDICAL_BILLS:,.2f}"
            )
        
        if medical_bills > self.MAX_MEDICAL_BILLS:
            errors.append(
                f"medical_bills exceeds maximum of ${self.MAX_MEDICAL_BILLS:,.2f}. "
                f"Please contact support for high-value cases."
            )
        
        # Validate lost wages
        if lost_wages is not None:
            if lost_wages < self.MIN_LOST_WAGES:
                errors.append(
                    f"lost_wages cannot be negative. Got: ${lost_wages:,.2f}"
                )
            
            if lost_wages > self.MAX_LOST_WAGES:
                errors.append(
                    f"lost_wages exceeds maximum of ${self.MAX_LOST_WAGES:,.2f}"
                )
        
        return errors
    
    def _check_for_outliers(self, request: ContributionRequest) -> List[str]:
        """
        Check for statistical outliers that should be flagged for manual review.
        
        Args:
            request: ContributionRequest object
            
        Returns:
            List of outlier warnings
        """
        warnings = []
        
        # Check if medical bills are unusually high
        if request.medical_bills > 1_000_000:
            warnings.append(
                f"Unusually high medical bills: ${request.medical_bills:,.2f}"
            )
        
        # Check if outcome range seems inconsistent with medical bills
        outcome_midpoint = self._get_outcome_midpoint(request.outcome_amount_range)
        if outcome_midpoint:
            # Typical multiplier range: 1.5x - 8x
            multiplier = outcome_midpoint / request.medical_bills
            
            if multiplier < 0.5:
                warnings.append(
                    f"Outcome (${outcome_midpoint:,.0f}) is unusually low compared to "
                    f"medical bills (${request.medical_bills:,.2f}, multiplier: {multiplier:.2f})"
                )
            
            if multiplier > 15:
                warnings.append(
                    f"Outcome (${outcome_midpoint:,.0f}) is unusually high compared to "
                    f"medical bills (${request.medical_bills:,.2f}, multiplier: {multiplier:.2f})"
                )
        
        return warnings
    
    def _get_outcome_midpoint(self, outcome_range: str) -> Optional[float]:
        """
        Get midpoint of outcome range bucket.
        
        Args:
            outcome_range: Outcome range bucket
            
        Returns:
            Midpoint value in dollars
        """
        midpoints = {
            "$0-$50k": 25000,
            "$50k-$100k": 75000,
            "$100k-$150k": 125000,
            "$150k-$225k": 187500,
            "$225k-$300k": 262500,
            "$300k-$600k": 450000,
            "$600k-$1M": 800000,
            "$1M+": 1500000
        }
        return midpoints.get(outcome_range)
    
    def validate_query_request(self, request: dict) -> Tuple[bool, List[str]]:
        """
        Validate a settlement range query request.
        
        Args:
            request: Query request dictionary
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Required fields (updated to match new EstimateRequest model)
        required_fields = ["jurisdiction", "case_type", "injury_category", "medical_bills"]
        for field in required_fields:
            if field not in request or not request[field]:
                errors.append(f"Required field missing: {field}")
        
        # Validate jurisdiction format
        if "jurisdiction" in request:
            errors.extend(self._validate_jurisdiction(request["jurisdiction"]))
        
        # Validate medical bills
        if "medical_bills" in request:
            try:
                medical_bills = float(request["medical_bills"])
                if medical_bills < self.MIN_MEDICAL_BILLS or medical_bills > self.MAX_MEDICAL_BILLS:
                    errors.append(
                        f"medical_bills must be between ${self.MIN_MEDICAL_BILLS:,.2f} "
                        f"and ${self.MAX_MEDICAL_BILLS:,.2f}"
                    )
            except (ValueError, TypeError):
                errors.append("medical_bills must be a valid number")
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.warning(f"Query validation failed: {errors}")
        
        return is_valid, errors

