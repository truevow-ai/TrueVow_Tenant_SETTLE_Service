"""
Override Tracking Service — Phase 3.3

Tracks when actual settlements differ from estimates.
Used for learning from overrides and improving estimates over time.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC
from uuid import UUID
from pydantic import BaseModel, Field

from app.core.database import get_db

logger = logging.getLogger(__name__)


# ============================================================================
# OVERRIDE MODELS
# ============================================================================

class OverrideRecord(BaseModel):
    """Single override record."""
    id: UUID
    query_id: Optional[UUID] = None
    contribution_id: Optional[UUID] = None
    estimate_median: Optional[float] = None
    actual_outcome: Optional[float] = None
    delta_pct: Optional[float] = None
    delta_direction: Optional[str] = None
    jurisdiction: Optional[str] = None
    case_type: Optional[str] = None
    injury_category: List[str] = Field(default_factory=list)
    medical_bills: Optional[float] = None
    created_at: datetime


class OverrideAnalytics(BaseModel):
    """Aggregate override analytics."""
    total_overrides: int
    avg_delta_pct: Optional[float] = None
    above_estimate_pct: Optional[float] = None
    below_estimate_pct: Optional[float] = None
    by_jurisdiction: List[Dict[str, Any]] = Field(default_factory=list)
    by_case_type: List[Dict[str, Any]] = Field(default_factory=list)


# ============================================================================
# OVERRIDE TRACKING SERVICE
# ============================================================================

class OverrideTrackingService:
    """Tracks and analyzes estimate overrides."""

    async def record_override(
        self,
        query_id: Optional[UUID],
        contribution_id: Optional[UUID],
        estimate_median: float,
        actual_outcome: float,
        jurisdiction: str,
        case_type: str,
        injury_category: List[str],
        medical_bills: float,
        created_by: Optional[UUID] = None,
    ) -> OverrideRecord:
        """
        Record an override (estimate vs actual delta).

        Args:
            query_id: Original query ID
            contribution_id: Contribution ID with actual outcome
            estimate_median: Median estimate at time of query
            actual_outcome: Actual settlement amount
            jurisdiction: Case jurisdiction
            case_type: Case type
            injury_category: Injury categories
            medical_bills: Medical bills amount
            created_by: User who submitted

        Returns:
            OverrideRecord
        """
        db = await get_db()

        delta = actual_outcome - estimate_median
        delta_pct = (delta / estimate_median * 100) if estimate_median > 0 else 0
        delta_direction = "above" if delta > 0 else "below"

        insert_data = {
            "query_id": str(query_id) if query_id else None,
            "contribution_id": str(contribution_id) if contribution_id else None,
            "estimate_median": estimate_median,
            "actual_outcome": actual_outcome,
            "delta_pct": round(delta_pct, 2),
            "delta_direction": delta_direction,
            "jurisdiction": jurisdiction,
            "case_type": case_type,
            "injury_category": injury_category,
            "medical_bills": medical_bills,
        }
        if created_by:
            insert_data["created_by"] = str(created_by)

        result = db.table("settle_estimate_overrides").insert(insert_data).execute()
        return OverrideRecord(**result.data[0])

    async def get_analytics(
        self,
        jurisdiction: Optional[str] = None,
        case_type: Optional[str] = None,
    ) -> OverrideAnalytics:
        """
        Get aggregate override analytics.

        Args:
            jurisdiction: Optional jurisdiction filter
            case_type: Optional case type filter

        Returns:
            OverrideAnalytics
        """
        db = await get_db()

        query = db.table("settle_estimate_overrides").select("*")
        if jurisdiction:
            query = query.eq("jurisdiction", jurisdiction)
        if case_type:
            query = query.eq("case_type", case_type)

        result = query.execute()
        rows = result.data or []

        if not rows:
            return OverrideAnalytics(total_overrides=0)

        total = len(rows)
        deltas = [r.get("delta_pct") for r in rows if r.get("delta_pct") is not None]
        avg_delta = sum(deltas) / len(deltas) if deltas else None

        above_count = sum(1 for r in rows if r.get("delta_direction") == "above")
        below_count = sum(1 for r in rows if r.get("delta_direction") == "below")
        above_pct = (above_count / total * 100) if total > 0 else None
        below_pct = (below_count / total * 100) if total > 0 else None

        # By jurisdiction
        jur_counts: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            j = r.get("jurisdiction", "Unknown")
            if j not in jur_counts:
                jur_counts[j] = {"jurisdiction": j, "count": 0, "avg_delta": 0, "deltas": []}
            jur_counts[j]["count"] += 1
            if r.get("delta_pct") is not None:
                jur_counts[j]["deltas"].append(r["delta_pct"])

        by_jurisdiction = []
        for j, data in jur_counts.items():
            avg = sum(data["deltas"]) / len(data["deltas"]) if data["deltas"] else None
            by_jurisdiction.append({
                "jurisdiction": data["jurisdiction"],
                "count": data["count"],
                "avg_delta_pct": round(avg, 2) if avg else None,
            })
        by_jurisdiction.sort(key=lambda x: x["count"], reverse=True)

        # By case type
        ct_counts: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            ct = r.get("case_type", "Unknown")
            if ct not in ct_counts:
                ct_counts[ct] = {"case_type": ct, "count": 0, "avg_delta": 0, "deltas": []}
            ct_counts[ct]["count"] += 1
            if r.get("delta_pct") is not None:
                ct_counts[ct]["deltas"].append(r["delta_pct"])

        by_case_type = []
        for ct, data in ct_counts.items():
            avg = sum(data["deltas"]) / len(data["deltas"]) if data["deltas"] else None
            by_case_type.append({
                "case_type": data["case_type"],
                "count": data["count"],
                "avg_delta_pct": round(avg, 2) if avg else None,
            })
        by_case_type.sort(key=lambda x: x["count"], reverse=True)

        return OverrideAnalytics(
            total_overrides=total,
            avg_delta_pct=round(avg_delta, 2) if avg_delta else None,
            above_estimate_pct=round(above_pct, 1) if above_pct else None,
            below_estimate_pct=round(below_pct, 1) if below_pct else None,
            by_jurisdiction=by_jurisdiction[:10],
            by_case_type=by_case_type[:10],
        )


# Singleton instance
override_tracking_service = OverrideTrackingService()
