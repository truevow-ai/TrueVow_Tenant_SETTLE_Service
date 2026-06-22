"""
Internal Verdict Data Models — Phase 1
Used for internal verdict research engine (ALM VerdictSearch competitor).
NOT customer-facing. Contains case names, judge names, carrier names.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID


# ============================================================================
# VALIDATION CONSTANTS
# ============================================================================

VALID_VERDICT_OUTCOME_TYPES = [
    "verdict_plaintiff",
    "verdict_defense",
    "settlement",
    "dismissed",
]

VALID_VERDICT_LIABILITY_TIERS = [
    "clear",
    "contested",
    "shared",
    "unknown",
]

VALID_VERDICT_PLAINTIFF_AGE_RANGES = [
    "under_18",
    "18_30",
    "31_45",
    "46_60",
    "61_75",
    "75_plus",
]

VALID_VERDICT_POLICY_LIMIT_INDICATORS = [
    "below_limits",
    "at_limits",
    "above_limits",
    "unknown",
]

VALID_VERDICT_SOURCES = [
    "scraped",
    "manual_entry",
    "partner_data",
]

VALID_VERDICT_REVIEW_STATUSES = [
    "pending",
    "reviewed",
    "verified",
    "rejected",
]

VALID_DEFENDANT_INDUSTRIES = [
    "Healthcare",
    "Automotive",
    "Retail",
    "Construction",
    "Insurance",
    "Manufacturing",
    "Technology",
    "Transportation",
    "Hospitality",
    "Education",
    "Government",
    "Other",
]


# ============================================================================
# DATABASE MODELS
# ============================================================================

class VerdictRecord(BaseModel):
    """Database model for internal verdict records"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    # Case Identification (Internal only)
    case_name: Optional[str] = None
    case_number: Optional[str] = None
    jurisdiction: str
    court: Optional[str] = None
    judge_name: Optional[str] = None

    # Case Classification
    case_type: str
    injury_type: List[str] = Field(default_factory=list)
    plaintiff_age_range: Optional[str] = None
    liability_tier: Optional[str] = None
    comparative_negligence_pct: Optional[float] = None

    # Financial Data (Internal — exact amounts)
    medical_bills: Optional[float] = None
    economic_damages: Optional[float] = None
    non_economic_damages: Optional[float] = None
    punitive_damages: Optional[float] = None
    total_verdict: Optional[float] = None
    settlement_amount: Optional[float] = None
    policy_limit_indicator: Optional[str] = None

    # Outcome
    outcome_type: str
    defendant_category: Optional[str] = None
    defendant_industry: Optional[str] = None
    insurance_carrier: Optional[str] = None

    # Trial Data
    expert_witnesses_plaintiff: Optional[int] = None
    expert_witnesses_defense: Optional[int] = None
    trial_duration_days: Optional[int] = None

    # Timing
    verdict_date: Optional[date] = None
    filing_date: Optional[date] = None
    resolution_date: Optional[date] = None

    # Source & Provenance
    source: str
    source_url: Optional[str] = None
    source_notes: Optional[str] = None

    # Data Quality
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    completeness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    review_status: str = Field(default="pending")
    reviewer_notes: Optional[str] = None

    # Metadata
    scraped_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================

class VerdictSearchFilter(BaseModel):
    """17-filter search request for internal verdict research"""

    # 1. Jurisdiction
    jurisdiction: Optional[str] = Field(None, description="County, ST or state abbreviation")
    # 2. Case Type
    case_type: Optional[List[str]] = Field(None, description="Multi-select case types")
    # 3. Injury Type
    injury_type: Optional[List[str]] = Field(None, description="Multi-select injury tags")
    # 4. Outcome Type
    outcome_type: Optional[List[str]] = Field(None, description="Multi-select outcome types")
    # 5. Verdict Amount Range
    verdict_amount_min: Optional[float] = Field(None, ge=0, description="Minimum verdict/settlement amount")
    verdict_amount_max: Optional[float] = Field(None, ge=0, description="Maximum verdict/settlement amount")
    # 6. Medical Bills Range
    medical_bills_min: Optional[float] = Field(None, ge=0, description="Minimum medical bills")
    medical_bills_max: Optional[float] = Field(None, ge=0, description="Maximum medical bills")
    # 7. Liability Tier
    liability_tier: Optional[List[str]] = Field(None, description="Multi-select liability tiers")
    # 8. Comparative Negligence
    comparative_negligence_min: Optional[float] = Field(None, ge=0, le=100, description="Min comparative negligence %")
    comparative_negligence_max: Optional[float] = Field(None, ge=0, le=100, description="Max comparative negligence %")
    # 9. Defendant Category
    defendant_category: Optional[List[str]] = Field(None, description="Multi-select defendant categories")
    # 10. Defendant Industry
    defendant_industry: Optional[List[str]] = Field(None, description="Multi-select defendant industries")
    # 11. Plaintiff Age Range
    plaintiff_age_range: Optional[List[str]] = Field(None, description="Multi-select age ranges")
    # 12. Date Range
    date_from: Optional[date] = Field(None, description="Verdict/settlement date from")
    date_to: Optional[date] = Field(None, description="Verdict/settlement date to")
    # 13. Insurance Carrier
    insurance_carrier: Optional[str] = Field(None, description="Carrier name search")
    # 14. Expert Witness Count
    expert_witness_min: Optional[int] = Field(None, ge=0, description="Min expert witnesses per side")
    expert_witness_max: Optional[int] = Field(None, ge=0, description="Max expert witnesses per side")
    # 15. Trial Duration
    trial_duration_min: Optional[int] = Field(None, ge=0, description="Min trial duration (days)")
    trial_duration_max: Optional[int] = Field(None, ge=0, description="Max trial duration (days)")
    # 16. Source Type
    source: Optional[List[str]] = Field(None, description="Multi-select source types")
    # 17. Confidence Score
    confidence_min: Optional[float] = Field(None, ge=0, le=1, description="Minimum confidence score")
    confidence_max: Optional[float] = Field(None, ge=0, le=1, description="Maximum confidence score")

    # Pagination
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=50, ge=1, le=500, description="Results per page")

    # Sort
    sort_by: str = Field(default="verdict_date", description="Field to sort by")
    sort_order: str = Field(default="desc", description="asc or desc")

    # Review status filter (internal)
    review_status: Optional[List[str]] = Field(None, description="Multi-select review statuses")


class VerdictSearchResult(BaseModel):
    """Single verdict record in search results"""

    id: UUID
    case_name: Optional[str] = None
    case_number: Optional[str] = None
    jurisdiction: str
    court: Optional[str] = None
    judge_name: Optional[str] = None
    case_type: str
    injury_type: List[str] = Field(default_factory=list)
    plaintiff_age_range: Optional[str] = None
    liability_tier: Optional[str] = None
    comparative_negligence_pct: Optional[float] = None
    medical_bills: Optional[float] = None
    economic_damages: Optional[float] = None
    non_economic_damages: Optional[float] = None
    punitive_damages: Optional[float] = None
    total_verdict: Optional[float] = None
    settlement_amount: Optional[float] = None
    policy_limit_indicator: Optional[str] = None
    outcome_type: str
    defendant_category: Optional[str] = None
    defendant_industry: Optional[str] = None
    insurance_carrier: Optional[str] = None
    expert_witnesses_plaintiff: Optional[int] = None
    expert_witnesses_defense: Optional[int] = None
    trial_duration_days: Optional[int] = None
    verdict_date: Optional[date] = None
    filing_date: Optional[date] = None
    resolution_date: Optional[date] = None
    source: str
    source_url: Optional[str] = None
    confidence_score: float
    completeness_score: float
    review_status: str
    created_at: datetime


class VerdictSearchResponse(BaseModel):
    """Paginated search response"""

    results: List[VerdictSearchResult]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    search_filters: Dict[str, Any] = Field(default_factory=dict)
    response_time_ms: Optional[int] = None


class VerdictStatsResponse(BaseModel):
    """Aggregate statistics for internal dashboard"""

    total_verdicts: int
    by_outcome_type: Dict[str, int]
    by_case_type: Dict[str, int]
    by_jurisdiction: Dict[str, int]
    by_review_status: Dict[str, int]
    by_source: Dict[str, int]
    avg_confidence_score: float
    avg_completeness_score: float
    avg_total_verdict: Optional[float] = None
    avg_settlement_amount: Optional[float] = None
    avg_medical_bills: Optional[float] = None
    avg_trial_duration_days: Optional[float] = None
    date_range: Dict[str, Optional[str]]


class VerdictDetailResponse(VerdictRecord):
    """Full verdict record detail (internal only)"""

    pass


class VerdictCreateRequest(BaseModel):
    """Manual verdict entry request (internal)"""

    case_name: Optional[str] = None
    case_number: Optional[str] = None
    jurisdiction: str
    court: Optional[str] = None
    judge_name: Optional[str] = None
    case_type: str
    injury_type: List[str] = Field(default_factory=list)
    plaintiff_age_range: Optional[str] = None
    liability_tier: Optional[str] = None
    comparative_negligence_pct: Optional[float] = None
    medical_bills: Optional[float] = None
    economic_damages: Optional[float] = None
    non_economic_damages: Optional[float] = None
    punitive_damages: Optional[float] = None
    total_verdict: Optional[float] = None
    settlement_amount: Optional[float] = None
    policy_limit_indicator: Optional[str] = None
    outcome_type: str
    defendant_category: Optional[str] = None
    defendant_industry: Optional[str] = None
    insurance_carrier: Optional[str] = None
    expert_witnesses_plaintiff: Optional[int] = None
    expert_witnesses_defense: Optional[int] = None
    trial_duration_days: Optional[int] = None
    verdict_date: Optional[date] = None
    filing_date: Optional[date] = None
    resolution_date: Optional[date] = None
    source_url: Optional[str] = None
    source_notes: Optional[str] = None

    @field_validator('jurisdiction')
    @classmethod
    def validate_jurisdiction(cls, v):
        if ',' not in v:
            raise ValueError("Jurisdiction must be in format 'County Name, STATE'")
        return v.strip()


class VerdictUpdateRequest(BaseModel):
    """Partial verdict update request (internal)"""

    case_name: Optional[str] = None
    case_number: Optional[str] = None
    court: Optional[str] = None
    judge_name: Optional[str] = None
    injury_type: Optional[List[str]] = None
    plaintiff_age_range: Optional[str] = None
    liability_tier: Optional[str] = None
    comparative_negligence_pct: Optional[float] = None
    medical_bills: Optional[float] = None
    economic_damages: Optional[float] = None
    non_economic_damages: Optional[float] = None
    punitive_damages: Optional[float] = None
    total_verdict: Optional[float] = None
    settlement_amount: Optional[float] = None
    policy_limit_indicator: Optional[str] = None
    outcome_type: Optional[str] = None
    defendant_category: Optional[str] = None
    defendant_industry: Optional[str] = None
    insurance_carrier: Optional[str] = None
    expert_witnesses_plaintiff: Optional[int] = None
    expert_witnesses_defense: Optional[int] = None
    trial_duration_days: Optional[int] = None
    verdict_date: Optional[date] = None
    filing_date: Optional[date] = None
    resolution_date: Optional[date] = None
    source_url: Optional[str] = None
    source_notes: Optional[str] = None
    confidence_score: Optional[float] = None
    completeness_score: Optional[float] = None
    review_status: Optional[str] = None
    reviewer_notes: Optional[str] = None


class VerdictScrapeJobResponse(BaseModel):
    """Scraping job status"""

    id: UUID
    source: str
    status: str
    records_found: int
    records_inserted: int
    records_skipped: int
    records_failed: int
    error_log: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


# ============================================================================
# SCRAPE JOB MODELS
# ============================================================================

class ScrapeJobCreateRequest(BaseModel):
    """Request to start a new scraping job"""

    source: str
    source_config: Dict[str, Any] = Field(default_factory=dict, description="Source-specific configuration")


class ScrapeJobListResponse(BaseModel):
    """List of scraping jobs"""

    jobs: List[VerdictScrapeJobResponse]
    total: int
