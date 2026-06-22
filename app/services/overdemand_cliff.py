"""
Overdemand Cliff Detection Service — Phase 3.2

Identifies the demand band above which settlement rate drops significantly.
Descriptive framing only — "Historical data shows..." not "You should demand..."

Algorithm:
1. Group historical cases by injury type + defendant category
2. Calculate settlement rate by outcome amount bucket
3. Identify the "cliff" — the bucket where settlement rate drops >20% from previous bucket
4. Return cliff threshold with estimate
"""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.database import get_db

logger = logging.getLogger(__name__)


# ============================================================================
# OVERDEMAND CLIFF MODELS
# ============================================================================

class OverdemandCliffResponse(BaseModel):
    """Overdemand cliff detection result."""
    threshold: Optional[float] = Field(None, description="Demand amount above which settlement rate drops significantly")
    settlement_rate_below: Optional[float] = Field(None, description="Settlement rate below the cliff threshold")
    settlement_rate_above: Optional[float] = Field(None, description="Settlement rate above the cliff threshold")
    warning: Optional[str] = Field(None, description="Human-readable warning message")
    has_cliff: bool = Field(default=False, description="Whether a significant cliff was detected")
    methodology: str = Field(
        default="Historical data analysis from anonymized settlement contributions. Not predictive.",
    )


# ============================================================================
# AMOUNT BUCKETS
# ============================================================================

AMOUNT_BUCKETS = [
    (0, 50000),
    (50000, 100000),
    (100000, 150000),
    (150000, 225000),
    (225000, 300000),
    (300000, 600000),
    (600000, 1000000),
    (1000000, float("inf")),
]


# ============================================================================
# OVERDEMAND CLIFF DETECTOR
# ============================================================================

class OverdemandCliffDetector:
    """Detects overdemand cliffs in historical settlement data."""

    async def detect_cliff(
        self,
        jurisdiction: Optional[str] = None,
        case_type: Optional[str] = None,
        injury_category: Optional[List[str]] = None,
        defendant_category: Optional[str] = None,
        min_cases_per_bucket: int = 5,
    ) -> OverdemandCliffResponse:
        """
        Detect overdemand cliff for a given case profile.

        Args:
            jurisdiction: Optional jurisdiction filter
            case_type: Optional case type filter
            injury_category: Optional injury category filter
            defendant_category: Optional defendant category filter
            min_cases_per_bucket: Minimum cases required per bucket for analysis

        Returns:
            OverdemandCliffResponse with cliff threshold and warning
        """
        db = await get_db()

        # Build query
        query = db.table("settle_contributions").select("*").eq("status", "approved")

        if jurisdiction:
            query = query.eq("jurisdiction", jurisdiction)
        if case_type:
            query = query.eq("case_type", case_type)
        if injury_category:
            query = query.cs("injury_category", injury_category)
        if defendant_category:
            query = query.eq("defendant_category", defendant_category)

        result = await query.execute()
        rows = result.data or []

        if len(rows) < min_cases_per_bucket * 2:
            return OverdemandCliffResponse(
                has_cliff=False,
                warning="Insufficient data to detect overdemand cliff.",
            )

        # Group cases by amount bucket
        bucket_data: Dict[int, Dict[str, int]] = {}
        for i, (low, high) in enumerate(AMOUNT_BUCKETS):
            bucket_data[i] = {"total": 0, "settled": 0}

        for row in rows:
            amount = row.get("exact_outcome_amount")
            if amount is None:
                # Estimate from bucket
                amount = _estimate_from_range(row.get("outcome_amount_range", ""))
            if amount is None:
                continue

            outcome = row.get("outcome_type", "")
            is_settlement = outcome == "Settlement"

            # Find bucket
            for i, (low, high) in enumerate(AMOUNT_BUCKETS):
                if low <= amount < high:
                    bucket_data[i]["total"] += 1
                    if is_settlement:
                        bucket_data[i]["settled"] += 1
                    break

        # Calculate settlement rates per bucket
        bucket_rates = []
        for i, (low, high) in enumerate(AMOUNT_BUCKETS):
            data = bucket_data[i]
            if data["total"] >= min_cases_per_bucket:
                rate = data["settled"] / data["total"]
                bucket_rates.append({
                    "bucket_index": i,
                    "low": low,
                    "high": high,
                    "total": data["total"],
                    "settled": data["settled"],
                    "rate": rate,
                })

        if len(bucket_rates) < 2:
            return OverdemandCliffResponse(
                has_cliff=False,
                warning="Insufficient bucket data to detect overdemand cliff.",
            )

        # Find the cliff — where rate drops >20% from previous bucket
        cliff_bucket = None
        for i in range(1, len(bucket_rates)):
            prev_rate = bucket_rates[i - 1]["rate"]
            curr_rate = bucket_rates[i]["rate"]
            drop = prev_rate - curr_rate
            if drop > 0.20:  # >20% drop
                cliff_bucket = bucket_rates[i]
                break

        if cliff_bucket is None:
            return OverdemandCliffResponse(
                has_cliff=False,
                warning="No significant overdemand cliff detected in historical data.",
            )

        threshold = cliff_bucket["low"]
        rate_below = bucket_rates[cliff_bucket["bucket_index"] - 1]["rate"]
        rate_above = cliff_bucket["rate"]
        drop_pct = (rate_below - rate_above) * 100

        return OverdemandCliffResponse(
            threshold=threshold,
            settlement_rate_below=round(rate_below, 3),
            settlement_rate_above=round(rate_above, 3),
            has_cliff=True,
            warning=f"Historical data shows demands above ${threshold:,.0f} in this category settle {drop_pct:.0f}% less often ({rate_below:.0%} vs {rate_above:.0%}).",
        )


def _estimate_from_range(range_str: str) -> Optional[float]:
    """Estimate amount from bucketed outcome range."""
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


# Singleton instance
overdemand_cliff_detector = OverdemandCliffDetector()
