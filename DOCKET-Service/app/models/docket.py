"""
DOCKET-Service Data Models
Pydantic models for court docket and litigation tracking.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID


# ============================================================================
# VALIDATION CONSTANTS
# ============================================================================

VALID_CASE_TYPES = [
    "Civil",
    "Criminal",
    "Bankruptcy",
    "Family",
    "Probate",
    "Personal Injury",
    "Contract Dispute",
    "Employment",
    "Real Estate",
    "Other",
]

VALID_CASE_STATUSES = [
    "active",
    "closed",
    "appealed",
    "dismissed",
    "settled",
    "pending",
]

VALID_SOURCES = [
    "pacer",
    "courtlistener",
    "scraped",
    "manual",
]


# ============================================================================
# DATABASE MODELS
# ============================================================================

class DocketCase(BaseModel):
    """Database model for docket cases."""

    model_config = {"from_attributes": True}

    id: UUID
    court_id: Optional[str] = None
    case_number: Optional[str] = None
    case_name: Optional[str] = None
    case_type: Optional[str] = None
    filing_date: Optional[date] = None
    status: Optional[str] = None
    judge_name: Optional[str] = None
    plaintiff_attorney: Optional[str] = None
    defense_attorney: Optional[str] = None
    plaintiff_firm: Optional[str] = None
    defense_firm: Optional[str] = None
    parties: Optional[Dict[str, Any]] = None
    claims: Optional[Dict[str, Any]] = None
    outcomes: Optional[Dict[str, Any]] = None
    damages_claimed: Optional[float] = None
    damages_awarded: Optional[float] = None
    settlement_amount: Optional[float] = None
    last_activity_date: Optional[date] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    scraped_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================

class DocketSearchFilter(BaseModel):
    """Search filters for docket cases."""

    court_id: Optional[str] = None
    case_number: Optional[str] = None
    case_name: Optional[str] = None
    case_type: Optional[str] = None
    status: Optional[str] = None
    judge_name: Optional[str] = None
    plaintiff_attorney: Optional[str] = None
    defense_attorney: Optional[str] = None
    plaintiff_firm: Optional[str] = None
    defense_firm: Optional[str] = None
    filing_date_from: Optional[date] = None
    filing_date_to: Optional[date] = None
    damages_min: Optional[float] = None
    damages_max: Optional[float] = None
    source: Optional[str] = None

    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)

    # Sort
    sort_by: str = Field(default="filing_date")
    sort_order: str = Field(default="desc")


class DocketSearchResult(BaseModel):
    """Single docket case in search results."""

    id: UUID
    court_id: Optional[str] = None
    case_number: Optional[str] = None
    case_name: Optional[str] = None
    case_type: Optional[str] = None
    filing_date: Optional[date] = None
    status: Optional[str] = None
    judge_name: Optional[str] = None
    plaintiff_attorney: Optional[str] = None
    defense_attorney: Optional[str] = None
    plaintiff_firm: Optional[str] = None
    defense_firm: Optional[str] = None
    damages_claimed: Optional[float] = None
    damages_awarded: Optional[float] = None
    settlement_amount: Optional[float] = None
    last_activity_date: Optional[date] = None
    source: Optional[str] = None
    created_at: datetime


class DocketSearchResponse(BaseModel):
    """Paginated docket search response."""

    results: List[DocketSearchResult]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool
    response_time_ms: Optional[int] = None


class DocketStatsResponse(BaseModel):
    """Aggregate docket statistics."""

    total_cases: int
    by_case_type: Dict[str, int]
    by_status: Dict[str, int]
    by_source: Dict[str, int]
    by_judge: Dict[str, int]
    avg_damages_awarded: Optional[float] = None
    avg_settlement_amount: Optional[float] = None
    date_range: Dict[str, Optional[str]]


class DocketCreateRequest(BaseModel):
    """Manual docket entry request."""

    court_id: Optional[str] = None
    case_number: Optional[str] = None
    case_name: Optional[str] = None
    case_type: Optional[str] = None
    filing_date: Optional[date] = None
    status: Optional[str] = None
    judge_name: Optional[str] = None
    plaintiff_attorney: Optional[str] = None
    defense_attorney: Optional[str] = None
    plaintiff_firm: Optional[str] = None
    defense_firm: Optional[str] = None
    parties: Optional[Dict[str, Any]] = None
    claims: Optional[Dict[str, Any]] = None
    outcomes: Optional[Dict[str, Any]] = None
    damages_claimed: Optional[float] = None
    damages_awarded: Optional[float] = None
    settlement_amount: Optional[float] = None
    last_activity_date: Optional[date] = None
    source_url: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v and v not in VALID_CASE_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(VALID_CASE_STATUSES)}")
        return v


class DocketUpdateRequest(BaseModel):
    """Partial docket update request."""

    case_name: Optional[str] = None
    status: Optional[str] = None
    judge_name: Optional[str] = None
    plaintiff_attorney: Optional[str] = None
    defense_attorney: Optional[str] = None
    plaintiff_firm: Optional[str] = None
    defense_firm: Optional[str] = None
    parties: Optional[Dict[str, Any]] = None
    claims: Optional[Dict[str, Any]] = None
    outcomes: Optional[Dict[str, Any]] = None
    damages_claimed: Optional[float] = None
    damages_awarded: Optional[float] = None
    settlement_amount: Optional[float] = None
    last_activity_date: Optional[date] = None
    source_url: Optional[str] = None
