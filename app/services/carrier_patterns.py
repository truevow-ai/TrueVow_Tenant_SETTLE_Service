"""
Carrier Pattern Analytics Service — Phase 2.3

Descriptive statistics about defendant/insurance carrier settlement patterns.
Defense side already has this (SigmaSight, CLARA). SETTLE provides the
plaintiff-side equivalent.

Bar compliance: Descriptive framing only — "Historical data shows..."
not "You should demand..." Carrier names are NOT stored (PHI risk) —
only categories (Individual/Business/Government/Unknown) with optional
industry sub-category.
"""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.database import get_db

logger = logging.getLogger(__name__)


# ============================================================================
# CARRIER PATTERN MODELS
# ============================================================================

class CarrierPattern(BaseModel):
    """Settlement pattern for a defendant category + industry combination."""
    defendant_category: str = Field(..., description="Individual, Business, Government, Unknown")
    defendant_industry: Optional[str] = Field(None, description="Healthcare, Automotive, Retail, etc.")
    case_count: int = Field(..., description="Number of cases in this category")
    avg_settlement_range: Dict[str, float] = Field(
        ..., description="Low, median, high settlement range"
    )
    settlement_rate: float = Field(..., description="Proportion of cases that settled vs. went to trial")
    avg_time_to_resolution_days: Optional[float] = Field(None, description="Average days to resolution")
    trial_rate: float = Field(..., description="Proportion of cases that went to trial")
    lowball_indicator: float = Field(
        ..., description="Proportion of settlements below the category median"
    )
    median_settlement: Optional[float] = Field(None, description="Median settlement amount")
    p25_settlement: Optional[float] = Field(None, description="25th percentile settlement")
    p75_settlement: Optional[float] = Field(None, description="75th percentile settlement")


class CarrierPatternsResponse(BaseModel):
    """Response for carrier pattern analytics."""
    patterns: List[CarrierPattern] = Field(..., description="List of carrier patterns")
    total_cases: int = Field(..., description="Total cases analyzed")
    jurisdiction: Optional[str] = Field(None, description="Jurisdiction filter applied")
    case_type: Optional[str] = Field(None, description="Case type filter applied")
    methodology: str = Field(
        default="Descriptive statistics from anonymized settlement contributions. Not predictive.",
        description="Methodology disclaimer for bar compliance",
    )


# ============================================================================
# CARRIER PATTERN AGGREGATION
# ============================================================================

async def get_carrier_patterns(
    jurisdiction: Optional[str] = None,
    case_type: Optional[str] = None,
    injury_category: Optional[List[str]] = None,
    defendant_category: Optional[str] = None,
    min_case_count: int = 5,
) -> CarrierPatternsResponse:
    """
    Get carrier/defendant settlement patterns.

    Args:
        jurisdiction: Optional jurisdiction filter
        case_type: Optional case type filter
        injury_category: Optional injury category filter
        defendant_category: Optional defendant category filter
        min_case_count: Minimum cases required to include a pattern

    Returns:
        CarrierPatternsResponse with descriptive statistics
    """
    # Build base query
    db = await get_db()
    if db is None:
        return CarrierPatternsResponse(
            patterns=[],
            total_cases=0,
            jurisdiction=jurisdiction,
            case_type=case_type,
        )
    query = (
        db.table("settle_contributions")
        .select("*")
        .eq("status", "approved")
    )

    if jurisdiction:
        query = query.eq("jurisdiction", jurisdiction)
    if case_type:
        query = query.eq("case_type", case_type)
    if injury_category:
        query = query.cs("injury_category", injury_category)
    if defendant_category:
        query = query.eq("defendant_category", defendant_category)

    result = query.execute()
    rows = result.data or []

    if not rows:
        return CarrierPatternsResponse(
            patterns=[],
            total_cases=0,
            jurisdiction=jurisdiction,
            case_type=case_type,
        )

    # Group by defendant_category + defendant_industry
    groups: Dict[str, List[dict]] = {}
    for row in rows:
        cat = row.get("defendant_category", "Unknown")
        industry = row.get("insurance_carrier") or row.get("defendant_industry")
        key = f"{cat}::{industry or 'N/A'}"
        if key not in groups:
            groups[key] = []
        groups[key].append(row)

    # Calculate patterns for each group
    patterns = []
    total_cases = len(rows)

    for key, group_rows in groups.items():
        if len(group_rows) < min_case_count:
            continue

        cat, industry = key.split("::", 1)
        if industry == "N/A":
            industry = None

        # Extract settlement amounts (use exact_outcome_amount if available, else estimate from range)
        amounts = []
        for row in group_rows:
            exact = row.get("exact_outcome_amount")
            if exact is not None:
                amounts.append(exact)
            else:
                # Estimate from outcome_amount_range bucket
                amount_range = row.get("outcome_amount_range", "")
                estimated = _estimate_amount_from_range(amount_range)
                if estimated:
                    amounts.append(estimated)

        if not amounts:
            continue

        amounts.sort()
        n = len(amounts)

        # Calculate percentiles
        p25 = _percentile(amounts, 25)
        median = _percentile(amounts, 50)
        p75 = _percentile(amounts, 75)

        # Settlement vs. trial rate
        settlement_count = sum(1 for r in group_rows if r.get("outcome_type") == "Settlement")
        trial_count = sum(1 for r in group_rows if r.get("outcome_type") in ("Jury Verdict", "Judge's Decision"))
        total_resolved = settlement_count + trial_count

        settlement_rate = settlement_count / total_resolved if total_resolved > 0 else 0
        trial_rate = trial_count / total_resolved if total_resolved > 0 else 0

        # Lowball indicator: proportion below the overall median for this category
        lowball_count = sum(1 for a in amounts if a < median)
        lowball_indicator = lowball_count / n if n > 0 else 0

        # Time to resolution (if available)
        resolution_days = []
        for row in group_rows:
            days = row.get("time_to_resolution_days")
            if days is not None:
                resolution_days.append(days)

        avg_resolution_days = sum(resolution_days) / len(resolution_days) if resolution_days else None

        patterns.append(CarrierPattern(
            defendant_category=cat,
            defendant_industry=industry,
            case_count=n,
            avg_settlement_range={
                "low": round(p25, 2),
                "median": round(median, 2),
                "high": round(p75, 2),
            },
            settlement_rate=round(settlement_rate, 3),
            avg_time_to_resolution_days=round(avg_resolution_days, 1) if avg_resolution_days else None,
            trial_rate=round(trial_rate, 3),
            lowball_indicator=round(lowball_indicator, 3),
            median_settlement=round(median, 2),
            p25_settlement=round(p25, 2),
            p75_settlement=round(p75, 2),
        ))

    # Sort by case count descending
    patterns.sort(key=lambda p: p.case_count, reverse=True)

    return CarrierPatternsResponse(
        patterns=patterns,
        total_cases=total_cases,
        jurisdiction=jurisdiction,
        case_type=case_type,
    )


def _estimate_amount_from_range(range_str: str) -> Optional[float]:
    """Estimate a numeric amount from a bucketed outcome range."""
    range_map = {
        "$0-$50k": 25000,
        "$50k-$100k": 75000,
        "$100k-$150k": 125000,
        "$150k-$225k": 187500,
        "$225k-$300k": 262500,
        "$300k-$600k": 450000,
        "$600k-$1M": 800000,
        "$1M+": 1500000,
    }
    return range_map.get(range_str)


def _percentile(sorted_data: List[float], percentile: int) -> float:
    """Calculate percentile from sorted data."""
    if not sorted_data:
        return 0.0
    n = len(sorted_data)
    k = (percentile / 100.0) * (n - 1)
    f = int(k)
    c = f + 1 if f + 1 < n else f
    d = k - f
    return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])
