"""
Intelligence Gate — the "Never Sell Empty Dashboards" guardrail.

Year-2 rule: if fewer than MIN_AGGREGATE_N approved settlement contributions
match the caller's filters, the service MUST refuse to emit aggregate
statistics (percentile ranges, carrier/defense-firm behavior, venue analytics,
etc.) and fall back to own-case-only rendering on the caller.

This is a HARD gate, not a soft confidence downgrade. It exists because
shipping a "median = $175k" chart that was computed from 7 cases is worse
than shipping no chart at all.

The gate is pure counting — no ML, no heuristics, no fallback. The caller
is responsible for suppressing any aggregate UI when `own_case_only=True`.
"""

from __future__ import annotations

import logging
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.core.database import get_db

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

# Year-2 "Credible Aggregation" floor. Do not lower without a written
# credibility rationale in docs/architecture/.
MIN_AGGREGATE_N: int = 50

# Features that MUST be suppressed when the gate returns insufficient_data.
# Callers should treat this list as authoritative — if you add a new
# aggregate-style dashboard widget, register it here.
SUPPRESSED_WHEN_INSUFFICIENT: List[str] = [
    "insurer_pattern_insights",          # "State Farm lowballs 37% below median"
    "defense_firm_behavior",             # defense firm settlement history
    "venue_analytics",                   # county-level outcome patterns
    "percentile_ranges",                 # p25/median/p75/p95 tables
    "time_to_resolution_trend",          # resolution-days histograms
    "policy_limit_distribution",         # policy-limit-known bucket charts
    "litigation_vs_settlement_roi",      # ROI modeling
]


# ============================================================================
# RESPONSE MODEL
# ============================================================================

class AggregateGateResult(BaseModel):
    """
    Result of an intelligence-gate check. Callers MUST respect
    `own_case_only=True` by suppressing every widget in
    `suppressed_features`.
    """

    status: Literal["sufficient", "insufficient_data"] = Field(
        ..., description="Whether aggregate intelligence may be rendered."
    )
    n: int = Field(..., ge=0, description="Approved contributions matching the filter set.")
    threshold: int = Field(default=MIN_AGGREGATE_N, description="Minimum N required.")
    own_case_only: bool = Field(
        ..., description="If True, caller must render only the user's own case — no aggregates."
    )
    suppressed_features: List[str] = Field(
        default_factory=list,
        description="Dashboard widgets the caller MUST hide. Empty when status=sufficient.",
    )
    jurisdiction: Optional[str] = Field(None, description="Filter echoed back for logging.")
    carrier: Optional[str] = Field(None, description="Filter echoed back for logging.")
    case_type: Optional[str] = Field(None, description="Filter echoed back for logging.")


# ============================================================================
# GATE SERVICE
# ============================================================================

class IntelligenceGate:
    """
    Counts approved rows in `settle_contributions` under caller-supplied
    filters and returns a gate decision. Pure data-plane; no caching here
    (let `query_cache_service` handle that upstream if hot paths emerge).
    """

    MIN_AGGREGATE_N: int = MIN_AGGREGATE_N

    def __init__(self, db_connection=None):
        """
        Args:
            db_connection: Optional pre-fetched DB client (SupabaseRESTClient).
                           If None, `check()` will resolve one via get_db().
        """
        self.db = db_connection

    async def check(
        self,
        jurisdiction: Optional[str] = None,
        carrier: Optional[str] = None,
        case_type: Optional[str] = None,
    ) -> AggregateGateResult:
        """
        Count approved contributions matching the filters and decide whether
        aggregate views may render.

        Args:
            jurisdiction: e.g. "Duval County, FL". At least one filter is expected
                          in practice, but all-None is allowed (returns the global
                          total — useful for health checks / admin dashboards).
            carrier: optional carrier name filter (will match the dedicated
                     `carrier_id` column once it lands; for now matches nothing
                     if the column doesn't exist — gate simply returns 0).
            case_type: optional case-type filter (e.g. "Premises Liability").

        Returns:
            AggregateGateResult with n, status, and suppressed_features.
        """
        db = self.db or await get_db()

        if db is None:
            # DB unreachable — fail CLOSED. Better to say "no data" than
            # to accidentally render a dashboard off stale cache.
            logger.warning(
                "IntelligenceGate: DB unavailable; failing closed (insufficient_data)."
            )
            return AggregateGateResult(
                status="insufficient_data",
                n=0,
                own_case_only=True,
                suppressed_features=list(SUPPRESSED_WHEN_INSUFFICIENT),
                jurisdiction=jurisdiction,
                carrier=carrier,
                case_type=case_type,
            )

        try:
            query = db.table("settle_contributions").select("id", count="exact").eq(
                "status", "approved"
            )

            if jurisdiction:
                query = query.eq("jurisdiction", jurisdiction)
            if case_type:
                query = query.eq("case_type", case_type)
            if carrier:
                # Column may not yet exist in all deployments; fail soft to 0.
                try:
                    query = query.eq("carrier_id", carrier)
                except Exception:
                    logger.debug("carrier filter skipped (column absent).")

            result = query.execute()
            n = int(getattr(result, "count", 0) or 0)
        except Exception as exc:
            logger.warning(
                "IntelligenceGate: count query failed (%s); failing closed.", exc
            )
            n = 0

        sufficient = n >= self.MIN_AGGREGATE_N
        return AggregateGateResult(
            status="sufficient" if sufficient else "insufficient_data",
            n=n,
            threshold=self.MIN_AGGREGATE_N,
            own_case_only=(not sufficient),
            suppressed_features=[] if sufficient else list(SUPPRESSED_WHEN_INSUFFICIENT),
            jurisdiction=jurisdiction,
            carrier=carrier,
            case_type=case_type,
        )


# ============================================================================
# MODULE-LEVEL CONVENIENCE
# ============================================================================

async def check_aggregate_availability(
    jurisdiction: Optional[str] = None,
    carrier: Optional[str] = None,
    case_type: Optional[str] = None,
) -> AggregateGateResult:
    """
    One-shot convenience wrapper for callers that do not want to instantiate
    IntelligenceGate themselves. Resolves the DB connection on every call;
    for hot paths, construct an IntelligenceGate(db) and reuse it.
    """
    return await IntelligenceGate().check(
        jurisdiction=jurisdiction, carrier=carrier, case_type=case_type
    )
