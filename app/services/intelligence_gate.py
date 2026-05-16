"""
Intelligence Gate — the "Never Sell Empty Dashboards" guardrail with
hierarchical jurisdiction fallback (Option D, 2026-05-07).

Year-2 rule: if fewer than MIN_AGGREGATE_N approved settlement contributions
match the caller's filters, the service MUST refuse to emit aggregate
statistics. This is a HARD gate at EACH tier, not a soft confidence downgrade.

Hierarchical tiers (checked in order):
  1. county tier — exact jurisdiction match (e.g. "Miami-Dade County, FL").
     Pass if n_county >= MIN_AGGREGATE_N. Highest precision.
  2. state tier — all counties in the state PLUS the "<STATE> (Unknown County)"
     sentinel bucket. Pass if n_state >= MIN_AGGREGATE_N. Honest aggregation
     level is labeled "state" on the response so the UI can surface it.
  3. none — neither tier has n>=50. Suppress all aggregate widgets.

Rationale: county-exact data is thin for most TopVerdict-sourced rows
(trial verdicts without high-fidelity county resolution) but state-wide
aggregates clear 50 comfortably. Industry-standard fallback — Westlaw,
Jury Verdicts, etc. all show statewide patterns when county data is thin.
Credibility floor (n>=50) is PRESERVED at each tier; we're only adding
an honest precision signal, never lowering the bar.
"""

from __future__ import annotations

import logging
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

# Year-2 "Credible Aggregation" floor. Do not lower without a written
# credibility rationale in docs/architecture/. Applies to BOTH tiers:
# county-exact and state-with-sentinel must each clear 50 independently.
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

    Hierarchical signal: `aggregation_level` tells the caller which tier
    cleared the floor. UI / justification copy MUST reflect this tier.
    """

    status: Literal["sufficient", "insufficient_data"] = Field(
        ..., description="Whether aggregate intelligence may be rendered."
    )
    aggregation_level: Literal["county", "state", "none"] = Field(
        default="none",
        description=(
            "Tier that cleared the floor. 'county' = exact county match, "
            "'state' = state-wide + sentinel bucket fallback, 'none' = neither tier cleared."
        ),
    )
    n: int = Field(..., ge=0, description="Effective approved-row count at the tier used.")
    n_county: int = Field(
        default=0, ge=0,
        description="Approved rows at exact county match (tier 1).",
    )
    n_state: int = Field(
        default=0, ge=0,
        description="Approved rows at state-wide + sentinel (tier 2).",
    )
    threshold: int = Field(default=MIN_AGGREGATE_N, description="Minimum N required per tier.")
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
    is_pilot_response: bool = Field(
        default=False,
        description=(
            "True when this result was produced via the pilot-mode gate path "
            "(ADR S-2 v2). UI MUST render pilot-phase disclosure when True. "
            "Always False for production county/state-tier responses."
        ),
    )


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
    # Pilot-mode floors (ADR S-2 v2). Production gate is UNCHANGED for
    # non-pilot users — these only apply when SETTLE_PILOT_MODE is on AND
    # the caller is a flagged pilot user AND production gate already failed.
    PILOT_MIN_AGGREGATE_N: int = 10
    PILOT_NARRATIVE_FLOOR: int = 5

    # Legacy / sentinel injury tags that do NOT count toward pilot-mode
    # eligibility. These are NOT in the closed-set InjuryTag taxonomy — they
    # represent unclassified data, scraper fallbacks, or case-type leakage
    # erroneously stored in the injury_category column. Pilot mode demands
    # at least one real InjuryTag value per row before the row counts.
    INJURY_PILOT_INELIGIBLE: frozenset = frozenset({
        "general_personal_injury",   # scraper fallback when no specific injury extractable
        "motor_vehicle_accident",    # case-type leakage as injury value
        "Unspecified",               # Phase 3.B scrub target, defense-in-depth
        "unspecified",
        "UNSPECIFIED",
        "Unknown",
        "unknown",
        "N/A",
        "n/a",
    })

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
        is_pilot_user: bool = False,
    ) -> AggregateGateResult:
        """
        Hierarchical gate check. Counts approved rows at two tiers and
        returns the first that clears MIN_AGGREGATE_N.

        Args:
            jurisdiction: e.g. "Miami-Dade County, FL". Required for hierarchical
                          fallback (state is parsed from the suffix). If None,
                          gate runs the global count (health-check mode) and
                          skips the tier logic.
            carrier: optional carrier filter (soft-fails if column absent).
            case_type: optional case-type filter (e.g. "Motor Vehicle Accident").

        Returns:
            AggregateGateResult with status, aggregation_level, n_county, n_state.
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
                aggregation_level="none",
                n=0,
                n_county=0,
                n_state=0,
                own_case_only=True,
                suppressed_features=list(SUPPRESSED_WHEN_INSUFFICIENT),
                jurisdiction=jurisdiction,
                carrier=carrier,
                case_type=case_type,
            )

        # ---- Tier 1: county-exact ----
        n_county = self._count_approved(
            db, case_type=case_type, carrier=carrier,
            filter_kind="county_exact", filter_value=jurisdiction,
        )
        if n_county >= self.MIN_AGGREGATE_N:
            return AggregateGateResult(
                status="sufficient",
                aggregation_level="county",
                n=n_county,
                n_county=n_county,
                n_state=n_county,  # state tier not queried; echo county as lower bound
                threshold=self.MIN_AGGREGATE_N,
                own_case_only=False,
                suppressed_features=[],
                jurisdiction=jurisdiction,
                carrier=carrier,
                case_type=case_type,
            )

        # ---- Tier 2: state-wide + sentinel ----
        state = _parse_state(jurisdiction)
        if state is None:
            # Can't do state fallback without a parseable state suffix.
            return AggregateGateResult(
                status="insufficient_data",
                aggregation_level="none",
                n=n_county,
                n_county=n_county,
                n_state=0,
                threshold=self.MIN_AGGREGATE_N,
                own_case_only=True,
                suppressed_features=list(SUPPRESSED_WHEN_INSUFFICIENT),
                jurisdiction=jurisdiction,
                carrier=carrier,
                case_type=case_type,
            )

        n_state_counties = self._count_approved(
            db, case_type=case_type, carrier=carrier,
            filter_kind="state_suffix", filter_value=state,
        )
        n_state_sentinel = self._count_approved(
            db, case_type=case_type, carrier=carrier,
            filter_kind="state_sentinel", filter_value=state,
        )
        n_state = n_state_counties + n_state_sentinel

        if n_state >= self.MIN_AGGREGATE_N:
            return AggregateGateResult(
                status="sufficient",
                aggregation_level="state",
                n=n_state,
                n_county=n_county,
                n_state=n_state,
                threshold=self.MIN_AGGREGATE_N,
                own_case_only=False,
                suppressed_features=[],
                jurisdiction=jurisdiction,
                carrier=carrier,
                case_type=case_type,
            )

        # ---- Pilot-mode state-tier path (ADR S-2 v2) ----
        # Only fires when production state-tier failed AND the caller is a
        # flagged pilot user AND the feature flag is on. Counts ONLY rows
        # with at least one real InjuryTag enum value in injury_category
        # (sentinel-tag rows are excluded). Returns is_pilot_response=True
        # so the estimator can apply the displayable-cases secondary gate
        # and inject pilot disclosure copy.
        if settings.SETTLE_PILOT_MODE and is_pilot_user:
            pilot_n = self._count_pilot_eligible_state(
                db, state=state, case_type=case_type, carrier=carrier,
            )
            if pilot_n >= self.PILOT_MIN_AGGREGATE_N:
                logger.info(
                    "IntelligenceGate: pilot-mode state-tier sufficient "
                    "(pilot_n=%d, prod_n_state=%d, jurisdiction=%r, case_type=%r)",
                    pilot_n, n_state, jurisdiction, case_type,
                )
                return AggregateGateResult(
                    status="sufficient",
                    aggregation_level="state",
                    n=pilot_n,
                    n_county=n_county,
                    n_state=pilot_n,
                    threshold=self.PILOT_MIN_AGGREGATE_N,
                    own_case_only=False,
                    suppressed_features=[],
                    jurisdiction=jurisdiction,
                    carrier=carrier,
                    case_type=case_type,
                    is_pilot_response=True,
                )

        # Neither tier cleared.
        return AggregateGateResult(
            status="insufficient_data",
            aggregation_level="none",
            n=max(n_county, n_state),
            n_county=n_county,
            n_state=n_state,
            threshold=self.MIN_AGGREGATE_N,
            own_case_only=True,
            suppressed_features=list(SUPPRESSED_WHEN_INSUFFICIENT),
            jurisdiction=jurisdiction,
            carrier=carrier,
            case_type=case_type,
        )

    def _count_approved(
        self,
        db,
        *,
        case_type: Optional[str],
        carrier: Optional[str],
        filter_kind: str,
        filter_value: Optional[str],
    ) -> int:
        """
        Count approved rows with one jurisdiction-shaped filter. Centralises
        the fail-closed boilerplate so the tier logic stays readable.

        filter_kind in:
          - "county_exact":    jurisdiction = filter_value
          - "state_suffix":    jurisdiction ILIKE '%, {state}'   (all counties in state)
          - "state_sentinel":  jurisdiction ILIKE '{state} (%'    (Unknown-County bucket)
          - None / missing filter_value returns 0 (no filter = no tier).
        """
        if not filter_value:
            return 0
        try:
            query = db.table("settle_contributions").select("id", count="exact").eq(
                "status", "approved"
            )
            if case_type:
                query = query.eq("case_type", case_type)
            if carrier:
                try:
                    query = query.eq("carrier_id", carrier)
                except Exception:
                    logger.debug("carrier filter skipped (column absent).")
            if filter_kind == "county_exact":
                query = query.eq("jurisdiction", filter_value)
            elif filter_kind == "state_suffix":
                query = query.ilike("jurisdiction", f"%, {filter_value}")
            elif filter_kind == "state_sentinel":
                query = query.ilike("jurisdiction", f"{filter_value} (%")
            else:
                logger.warning("IntelligenceGate: unknown filter_kind %r", filter_kind)
                return 0
            result = query.execute()
            raw = getattr(result, "count", None)
            # Strict type check: PostgREST returns count as int in JSON. Anything
            # else (None, MagicMock, stray object) is treated as 0 — prevents
            # MagicMock.__int__ (which returns 1) from silently corrupting counts
            # under tests that don't fully configure the filter chain.
            if isinstance(raw, bool):
                return 0
            if isinstance(raw, int):
                return raw if raw >= 0 else 0
            return 0
        except Exception as exc:
            logger.warning(
                "IntelligenceGate: count query failed (kind=%s, value=%r): %s; failing closed.",
                filter_kind, filter_value, exc,
            )
            return 0

    def _count_pilot_eligible_state(
        self,
        db,
        *,
        state: str,
        case_type: Optional[str],
        carrier: Optional[str],
    ) -> int:
        """Count approved state-tier rows whose `injury_category` contains at
        least one value from the closed-set InjuryTag enum (i.e., NOT only
        sentinel/legacy tags). Used for pilot-mode gate eligibility per
        ADR S-2 v2 sentinel exclusion.

        Implementation: pulls injury_category for state-tier rows (suffix +
        sentinel-bucket) via two PostgREST queries (matching the existing
        state-tier query split in estimator._query_state_tier), then applies
        a Python-side filter against the InjuryTag enum. Avoids relying on
        wrapper-specific array-overlap operators — see Cohort T surface-back
        trigger #2.

        Returns 0 fail-closed on any exception.
        """
        try:
            from app.services.injury_classifier import InjuryTag
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "IntelligenceGate: InjuryTag import failed (%s); pilot count = 0.",
                exc,
            )
            return 0

        valid_tags: frozenset = frozenset(
            t.value for t in InjuryTag
            if t.value not in self.INJURY_PILOT_INELIGIBLE
        )

        def _pull(filter_kind: str, filter_value: str) -> List[dict]:
            try:
                query = db.table("settle_contributions").select(
                    "id, injury_category"
                ).eq("status", "approved")
                if case_type:
                    query = query.eq("case_type", case_type)
                if carrier:
                    try:
                        query = query.eq("carrier_id", carrier)
                    except Exception:
                        logger.debug("carrier filter skipped (column absent).")
                if filter_kind == "state_suffix":
                    query = query.ilike("jurisdiction", f"%, {filter_value}")
                elif filter_kind == "state_sentinel":
                    query = query.ilike("jurisdiction", f"{filter_value} (%")
                else:
                    return []
                rows = query.execute().data or []
                # Tolerate MagicMock surfaces in tests — only accept lists.
                return rows if isinstance(rows, list) else []
            except Exception as exc:
                logger.warning(
                    "IntelligenceGate: pilot pull failed (kind=%s, state=%r): %s; "
                    "failing closed for this slice.",
                    filter_kind, filter_value, exc,
                )
                return []

        rows_a = _pull("state_suffix", state)
        rows_b = _pull("state_sentinel", state)

        # Dedupe by id; count only rows with at least one valid InjuryTag.
        seen: set = set()
        eligible = 0
        for row in rows_a + rows_b:
            if not isinstance(row, dict):
                continue
            rid = row.get("id")
            if rid in seen:
                continue
            seen.add(rid)
            tags = row.get("injury_category") or []
            if not isinstance(tags, list):
                continue
            if any(t in valid_tags for t in tags):
                eligible += 1
        return eligible


def _parse_state(jurisdiction: Optional[str]) -> Optional[str]:
    """Extract 2-letter state code from 'County, ST' format. Returns None
    if the input is missing or malformed (no comma, empty suffix)."""
    if not jurisdiction:
        return None
    parts = jurisdiction.rsplit(",", 1)
    if len(parts) != 2:
        return None
    state = parts[1].strip()
    return state or None


# ============================================================================
# MODULE-LEVEL CONVENIENCE
# ============================================================================

async def check_aggregate_availability(
    jurisdiction: Optional[str] = None,
    carrier: Optional[str] = None,
    case_type: Optional[str] = None,
    is_pilot_user: bool = False,
) -> AggregateGateResult:
    """
    One-shot convenience wrapper for callers that do not want to instantiate
    IntelligenceGate themselves. Resolves the DB connection on every call;
    for hot paths, construct an IntelligenceGate(db) and reuse it.
    """
    return await IntelligenceGate().check(
        jurisdiction=jurisdiction, carrier=carrier, case_type=case_type,
        is_pilot_user=is_pilot_user,
    )
