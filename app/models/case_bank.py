"""
Case Bank Data Models - Settlement Contributions and Queries
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime, UTC
from uuid import UUID


# ============================================================================
# DATABASE MODELS
# ============================================================================

class SettleContribution(BaseModel):
    """Database model for settlement contributions"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    
    # Step 1: Venue & Case Type
    jurisdiction: str = Field(..., description="e.g., 'Maricopa County, AZ'")
    case_type: str = Field(..., description="Drop-down case type")
    
    # Step 2: Injury & Treatment
    injury_category: List[str] = Field(..., description="Multi-select injury categories")
    primary_diagnosis: Optional[str] = Field(None, description="Drop-down diagnosis")
    treatment_type: List[str] = Field(default_factory=list, description="Multi-select treatments")
    duration_of_treatment: Optional[str] = Field(None, description="Drop-down duration")
    imaging_findings: List[str] = Field(default_factory=list, description="Multi-select imaging")
    
    # Step 3: Financial
    medical_bills: float = Field(..., ge=0, description="Medical bills amount")
    lost_wages: Optional[float] = Field(None, ge=0, description="Lost wages amount")
    policy_limits: Optional[str] = Field(None, description="Drop-down policy limits")
    
    # Step 4: Liability Context
    defendant_category: str = Field(..., description="Drop-down defendant category")
    
    # Step 5: Outcome
    outcome_type: str = Field(..., description="Drop-down outcome type")
    outcome_amount_range: str = Field(..., description="Bucketed outcome range")
    
    # Compliance & Audit
    contributed_at: datetime
    blockchain_hash: Optional[str] = None
    consent_confirmed: bool = True
    
    # Contributor Tracking
    contributor_api_key_id: Optional[UUID] = None
    founding_member: bool = False
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    status: str = Field(default="pending", description="pending, approved, rejected, flagged")
    rejection_reason: Optional[str] = None
    
    # Data Quality
    is_outlier: bool = False
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================

class EstimateRequest(BaseModel):
    """Request model for settlement range estimation"""
    
    jurisdiction: str = Field(..., min_length=5, description="County and state (e.g., 'Maricopa County, AZ')")
    case_type: str = Field(..., description="Case type")
    injury_category: List[str] = Field(..., min_length=1, description="Injury categories (multi-select)")
    medical_bills: float = Field(..., ge=0, description="Medical bills amount")
    
    # Optional filters
    primary_diagnosis: Optional[str] = Field(None, description="Primary diagnosis")
    treatment_type: Optional[List[str]] = Field(None, description="Treatment types")
    duration_of_treatment: Optional[str] = Field(None, description="Duration of treatment")
    imaging_findings: Optional[List[str]] = Field(None, description="Imaging findings")
    lost_wages: Optional[float] = Field(None, ge=0, description="Lost wages amount")
    policy_limits: Optional[str] = Field(None, description="Policy limits")
    defendant_category: Optional[str] = Field(None, description="Defendant category")
    
    @field_validator('jurisdiction')
    @classmethod
    def validate_jurisdiction(cls, v):
        """Validate jurisdiction format"""
        if ',' not in v:
            raise ValueError("Jurisdiction must be in format 'County Name, STATE' (e.g., 'Maricopa County, AZ')")
        return v.strip()


class ComparableCase(BaseModel):
    """Comparable case data (anonymized)"""
    
    model_config = ConfigDict(from_attributes=True)
    
    jurisdiction: str
    case_type: str
    injury_category: List[str]
    primary_diagnosis: Optional[str]
    medical_bills: float
    outcome_range: str
    outcome_type: str
    contributed_at: datetime


class EstimateResponse(BaseModel):
    """Response model for settlement range estimation"""
    
    # Statistical ranges
    percentile_25: float = Field(..., description="25th percentile")
    median: float = Field(..., description="50th percentile (median)")
    percentile_75: float = Field(..., description="75th percentile")
    percentile_95: float = Field(..., description="95th percentile")
    
    # Metadata
    n_cases: int = Field(..., description="Number of comparable cases")
    confidence: str = Field(..., description="low, medium, high")
    
    # Comparable cases (for report)
    comparable_cases: List[ComparableCase] = Field(
        default_factory=list,
        description="Sample of comparable cases"
    )
    
    # Justification (for report)
    range_justification: Optional[str] = Field(
        None,
        description="Explanation of how range was calculated"
    )
    
    # Query metadata
    query_id: Optional[UUID] = Field(None, description="Query ID for report generation")
    queried_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")


class ContributionRequest(BaseModel):
    """Request model for settlement contribution"""
    
    # Step 1: Venue & Case Type
    jurisdiction: str = Field(..., min_length=5, description="County and state (e.g., 'Maricopa County, AZ')")
    case_type: str = Field(..., description="Case type from drop-down")
    
    # Step 2: Injury & Treatment
    injury_category: List[str] = Field(..., min_length=1, description="At least one injury category")
    primary_diagnosis: Optional[str] = Field(None, description="Primary diagnosis (optional)")
    treatment_type: List[str] = Field(default_factory=list, description="Treatment types")
    duration_of_treatment: Optional[str] = Field(None, description="Duration of treatment")
    imaging_findings: List[str] = Field(default_factory=list, description="Imaging findings")
    
    # Step 3: Financial
    medical_bills: float = Field(..., ge=0, description="Medical bills amount")
    lost_wages: Optional[float] = Field(None, ge=0, description="Lost wages (optional)")
    policy_limits: Optional[str] = Field(None, description="Policy limits (optional)")
    
    # Step 4: Liability
    defendant_category: str = Field(..., description="Defendant category")
    
    # Step 5: Outcome
    outcome_type: str = Field(..., description="Outcome type (Settlement, Verdict, etc.)")
    outcome_amount_range: str = Field(..., description="Bucketed outcome range")
    
    # Compliance
    consent_confirmed: bool = Field(True, description="Attorney confirms ethical compliance")
    
    @field_validator('outcome_amount_range')
    @classmethod
    def validate_outcome_range(cls, v):
        """Validate outcome range is one of the allowed buckets"""
        valid_ranges = [
            '$0-$50k', '$50k-$100k', '$100k-$150k', '$150k-$225k',
            '$225k-$300k', '$300k-$600k', '$600k-$1M', '$1M+'
        ]
        if v not in valid_ranges:
            raise ValueError(f"Outcome range must be one of: {', '.join(valid_ranges)}")
        return v
    
    @field_validator('jurisdiction')
    @classmethod
    def validate_jurisdiction(cls, v):
        """Validate jurisdiction format (must contain county and state)"""
        if ',' not in v:
            raise ValueError("Jurisdiction must be in format: 'County, ST' (e.g., 'Maricopa County, AZ')")
        return v.strip()


class ContributionResponse(BaseModel):
    """Response model for settlement contribution"""
    
    contribution_id: UUID = Field(..., description="Unique contribution ID")
    blockchain_hash: str = Field(..., description="OpenTimestamps blockchain hash")
    message: str = Field(..., description="Confirmation message")
    founding_member_status: Optional[dict] = Field(
        None,
        description="Founding member stats if applicable"
    )
    status: str = Field(default="pending", description="Contribution status")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ============================================================================
# VALIDATION CONSTANTS (Drop-down options)
# ============================================================================

VALID_CASE_TYPES = [
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

VALID_OUTCOME_RANGES = [
    '$0-$50k',
    '$50k-$100k',
    '$100k-$150k',
    '$150k-$225k',
    '$225k-$300k',
    '$300k-$600k',
    '$600k-$1M',
    '$1M+'
]

VALID_OUTCOME_TYPES = [
    "Settlement",
    "Jury Verdict",
    "Arbitration Award",
    "Mediation",
    "Judge's Decision"
]

VALID_DEFENDANT_CATEGORIES = [
    "Individual",
    "Business",
    "Government Entity",
    "Unknown"
]

VALID_POLICY_LIMITS = [
    "$15k/$30k",
    "$25k/$50k",
    "$50k/$100k",
    "$100k/$300k",
    "$250k/$500k",
    "$1M/$2M",
    "$1M+",
    "Unknown"
]

VALID_DURATION_OF_TREATMENT = [
    "<3 months",
    "3-6 months",
    "6-12 months",
    "1-2 years",
    "2+ years"
]
