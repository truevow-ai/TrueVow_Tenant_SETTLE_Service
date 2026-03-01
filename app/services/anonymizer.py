"""
Anonymization Validator Service

Ensures that NO PHI (Protected Health Information) or PII is collected.
Validates that all contributions are bar-compliant and anonymous.

Reference: Part 7, Section 7.3 (Anonymization Logic) and 7.6 (Legal & Compliance)
"""

import re
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class AnonymizationValidator:
    """
    Anonymization validator for settlement contributions.
    
    CRITICAL COMPLIANCE RULES:
    ❌ NEVER allow: names, SSNs, DOBs, medical record numbers, case numbers
    ❌ NEVER allow: free-text narratives (injury descriptions, fault assessments)
    ❌ NEVER allow: specific business names ("Kroger #342")
    ❌ NEVER allow: addresses, phone numbers, emails
    ❌ NEVER allow: CPT/ICD diagnostic codes
    
    ✅ ONLY allow: drop-down values, generic categories, bucketed amounts
    """
    
    # Forbidden patterns (PHI/PII indicators)
    FORBIDDEN_PATTERNS = {
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b",  # SSN format
        "dob": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",  # Date format
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # Phone number
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
        "case_number": r"\bcase\s*#?\s*\d+\b",  # Case number
        "mrn": r"\bMRN\s*:?\s*\d+\b",  # Medical record number
        "address": r"\b\d+\s+[A-Z][a-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd)\b",  # Street address
    }
    
    # Forbidden name indicators (common first/last names)
    COMMON_NAMES = [
        "John", "Jane", "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
        "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
        # Add more as needed
    ]
    
    # Allowed drop-down values (pre-approved lists)
    ALLOWED_CASE_TYPES = [
        "Motor Vehicle Accident",
        "Motorcycle Accident",
        "Truck Accident",
        "Pedestrian Accident",
        "Bicycle Accident",
        "Premises Liability (Slip/Trip/Fall)",
        "Dog Bite",
        "Medical Malpractice",
        "Nursing Home Abuse",
        "Product Liability",
        "Workers Compensation",
        "Wrongful Death",
        "Other"
    ]
    
    ALLOWED_DEFENDANT_CATEGORIES = [
        "Individual",
        "Business",
        "Government Entity",
        "Unknown"
    ]
    
    ALLOWED_OUTCOME_TYPES = [
        "Settlement",
        "Jury Verdict",
        "Arbitration Award",
        "Mediation",
        "Judge's Decision"
    ]
    
    ALLOWED_OUTCOME_RANGES = [
        "$0-$50k",
        "$50k-$100k",
        "$100k-$150k",
        "$150k-$225k",
        "$225k-$300k",
        "$300k-$600k",
        "$600k-$1M",
        "$1M+"
    ]
    
    def validate_contribution(self, data: dict) -> Tuple[bool, List[str]]:
        """
        Validate that a contribution is fully anonymized and compliant.
        
        Args:
            data: Contribution data dictionary
            
        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        violations = []
        
        # Check 1: Validate all text fields for PHI/PII patterns
        text_fields = [
            "jurisdiction",
            "case_type",
            "primary_diagnosis",
            "duration_of_treatment",
            "policy_limits",
            "defendant_category",
            "outcome_type",
            "outcome_amount_range"
        ]
        
        for field in text_fields:
            if field in data and data[field]:
                field_violations = self._check_field_for_phi(field, data[field])
                violations.extend(field_violations)
        
        # Check 2: Validate array fields (injury_category, treatment_type, imaging_findings)
        array_fields = ["injury_category", "treatment_type", "imaging_findings"]
        for field in array_fields:
            if field in data and data[field]:
                for item in data[field]:
                    field_violations = self._check_field_for_phi(field, item)
                    violations.extend(field_violations)
        
        # Check 3: Validate drop-down fields are from allowed lists
        if "case_type" in data:
            if data["case_type"] not in self.ALLOWED_CASE_TYPES:
                violations.append(
                    f"case_type must be from pre-approved list. Got: '{data['case_type']}'"
                )
        
        if "defendant_category" in data:
            if data["defendant_category"] not in self.ALLOWED_DEFENDANT_CATEGORIES:
                violations.append(
                    f"defendant_category must be from pre-approved list. Got: '{data['defendant_category']}'"
                )
        
        if "outcome_type" in data:
            if data["outcome_type"] not in self.ALLOWED_OUTCOME_TYPES:
                violations.append(
                    f"outcome_type must be from pre-approved list. Got: '{data['outcome_type']}'"
                )
        
        if "outcome_amount_range" in data:
            if data["outcome_amount_range"] not in self.ALLOWED_OUTCOME_RANGES:
                violations.append(
                    f"outcome_amount_range must be bucketed. Got: '{data['outcome_amount_range']}'"
                )
        
        # Check 4: Validate jurisdiction format (must be "County, ST" format)
        if "jurisdiction" in data:
            if not self._validate_jurisdiction_format(data["jurisdiction"]):
                violations.append(
                    f"jurisdiction must be in format 'County, ST'. Got: '{data['jurisdiction']}'"
                )
        
        # Check 5: Ensure consent is confirmed
        if "consent_confirmed" in data:
            if not data["consent_confirmed"]:
                violations.append("consent_confirmed must be True")
        
        # Check 6: Validate financial data is reasonable
        if "medical_bills" in data:
            if not self._validate_financial_amount(data["medical_bills"]):
                violations.append(
                    f"medical_bills amount seems unrealistic: ${data['medical_bills']:,.2f}"
                )
        
        is_valid = len(violations) == 0
        
        if not is_valid:
            logger.warning(f"Anonymization validation failed: {violations}")
        else:
            logger.info("Anonymization validation passed")
        
        return is_valid, violations
    
    def _check_field_for_phi(self, field_name: str, value: str) -> List[str]:
        """
        Check a single field for PHI/PII patterns.
        
        Args:
            field_name: Name of the field
            value: Field value (string)
            
        Returns:
            List of violations found
        """
        violations = []
        
        # Check for forbidden patterns
        for pattern_name, pattern in self.FORBIDDEN_PATTERNS.items():
            if re.search(pattern, value, re.IGNORECASE):
                violations.append(
                    f"{field_name} contains potential {pattern_name.upper()}: '{value}'"
                )
        
        # Check for common names
        for name in self.COMMON_NAMES:
            if re.search(r'\b' + name + r'\b', value, re.IGNORECASE):
                violations.append(
                    f"{field_name} contains potential person name: '{name}' in '{value}'"
                )
        
        # Check for specific business names with store numbers
        if re.search(r'#\d+', value):
            violations.append(
                f"{field_name} contains specific business identifier: '{value}'. Use generic category instead."
            )
        
        return violations
    
    def _validate_jurisdiction_format(self, jurisdiction: str) -> bool:
        """
        Validate jurisdiction is in "County, ST" format.
        
        Args:
            jurisdiction: Jurisdiction string
            
        Returns:
            True if valid format
        """
        # Must have comma
        if ',' not in jurisdiction:
            return False
        
        parts = jurisdiction.split(',')
        if len(parts) != 2:
            return False
        
        county, state = parts[0].strip(), parts[1].strip()
        
        # County must be at least 2 characters
        if len(county) < 2:
            return False
        
        # State must be 2-letter code
        if len(state) != 2 or not state.isalpha():
            return False
        
        return True
    
    def _validate_financial_amount(self, amount: float) -> bool:
        """
        Validate financial amount is reasonable.
        
        Args:
            amount: Financial amount
            
        Returns:
            True if reasonable
        """
        # Medical bills should be between $1 and $10M
        if amount < 1 or amount > 10_000_000:
            return False
        
        return True
    
    def sanitize_text(self, text: str) -> str:
        """
        Sanitize text by removing potential PHI/PII.
        
        Note: In production, this should REJECT the submission, not sanitize.
        Sanitization is only for legacy data cleanup.
        
        Args:
            text: Input text
            
        Returns:
            Sanitized text
        """
        sanitized = text
        
        # Replace SSNs with [REDACTED]
        sanitized = re.sub(
            self.FORBIDDEN_PATTERNS["ssn"],
            "[REDACTED-SSN]",
            sanitized
        )
        
        # Replace phone numbers
        sanitized = re.sub(
            self.FORBIDDEN_PATTERNS["phone"],
            "[REDACTED-PHONE]",
            sanitized
        )
        
        # Replace emails
        sanitized = re.sub(
            self.FORBIDDEN_PATTERNS["email"],
            "[REDACTED-EMAIL]",
            sanitized
        )
        
        logger.warning(f"Sanitized text: '{text}' -> '{sanitized}'")
        
        return sanitized
    
    def check_for_liability_language(self, text: str) -> List[str]:
        """
        Check for forbidden liability/fault language.
        
        Examples of forbidden language:
        - "at fault", "negligent", "reckless"
        - "liable", "responsible for"
        - "violated", "failed to"
        
        Args:
            text: Text to check
            
        Returns:
            List of forbidden phrases found
        """
        forbidden_phrases = [
            "at fault",
            "negligent",
            "negligence",
            "reckless",
            "liable",
            "liability",
            "responsible for",
            "violated",
            "failed to",
            "breached",
            "causation",
            "proximately caused"
        ]
        
        found_phrases = []
        for phrase in forbidden_phrases:
            if phrase.lower() in text.lower():
                found_phrases.append(phrase)
        
        return found_phrases

