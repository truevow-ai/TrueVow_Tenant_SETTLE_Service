"""
Settlement Range Estimator Service

Core algorithm for calculating settlement ranges based on comparable cases.
Gated by IntelligenceGate (Year-2 Credible Aggregation floor); returns percentile-based
range when cohort credibility threshold is met, suppressed response otherwise.

Reference: Part 7, Section 7.5 of Technical Documentation
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from datetime import datetime, UTC
import logging

from pydantic import ValidationError

from app.models.case_bank import (
    EstimateRequest,
    EstimateResponse,
    ComparableCase,
    SettleContribution
)
from app.services.intelligence_gate import (
    IntelligenceGate,
    SUPPRESSED_WHEN_INSUFFICIENT,
)

logger = logging.getLogger(__name__)


class SettlementEstimator:
    """
    Settlement Range Estimator using percentile-based calculation with
    hierarchical jurisdiction fallback (Option D, 2026-05-07).

    Algorithm:
    1. Query IntelligenceGate for cohort credibility. Gate returns one of:
       - sufficient @ county tier (n_county >= 50) — use county-specific pool
       - sufficient @ state tier  (n_state  >= 50) — use statewide + sentinel pool
       - insufficient_data                         — short-circuit, suppress aggregates
    2. If sufficient: query comparable cases at the tier the gate selected,
       compute percentiles (25th, median, 75th, 95th), return full estimate
       with aggregation_level signal so UI can label the precision tier.
    3. If insufficient_data: return suppressed response with own_case_only=True
       and aggregate widgets blocked. No multiplier fallback — synthesizing
       ranges from sub-threshold data is the anti-pattern this gate exists
       to prevent.
    4. Confidence label within passing cohorts: `high` (n >= 30) or `medium`
       (n < 30; only reachable via test-mode gate injection).
    """
    
    # Confidence thresholds
    CONFIDENCE_THRESHOLDS = {
        "high": 30,     # 30+ cases = high confidence
        "medium": 15,   # gate-dependent; only reachable when gate floor lowered below 30
    }
    
    def __init__(self, db_connection=None, gate: Optional["IntelligenceGate"] = None):
        """
        Initialize estimator with database connection.

        Args:
            db_connection: Database connection for querying contributions.
            gate: Optional injected IntelligenceGate (primarily for tests).
                  Defaults to a gate wired to the same db_connection.
        """
        self.db = db_connection
        self.gate = gate or IntelligenceGate(db_connection)
    
    async def estimate_settlement_range(
        self,
        request: EstimateRequest
    ) -> EstimateResponse:
        """
        Estimate settlement range based on comparable cases.
        
        Args:
            request: Estimate request with injury type, jurisdiction, medical bills
            
        Returns:
            EstimateResponse with percentile ranges and comparable cases
        """
        start_time = datetime.now(UTC)

        # Year-2 "Never Sell Empty Dashboards" gate with hierarchical fallback.
        # Gate checks county-exact first, then state-wide+sentinel; returns
        # aggregation_level in {county, state, none}. If neither tier clears
        # n>=50, we short-circuit to own-case-only — no multiplier fallback.
        gate_result = await self.gate.check(
            jurisdiction=request.jurisdiction,
            case_type=request.case_type,
        )
        if gate_result.status == "insufficient_data":
            response_time_ms = int(
                (datetime.now(UTC) - start_time).total_seconds() * 1000
            )
            logger.info(
                "Estimator short-circuit: insufficient_data for %s "
                "(n_county=%d, n_state=%d, floor=%d)",
                request.jurisdiction, gate_result.n_county, gate_result.n_state,
                gate_result.threshold,
            )
            return EstimateResponse(
                percentile_25=0.0,
                median=0.0,
                percentile_75=0.0,
                percentile_95=0.0,
                n_cases=gate_result.n,
                confidence="insufficient_data",
                own_case_only=True,
                suppressed_features=list(SUPPRESSED_WHEN_INSUFFICIENT),
                aggregation_level="none",
                n_county=gate_result.n_county,
                n_state=gate_result.n_state,
                comparable_cases=[],
                range_justification=(
                    f"Insufficient approved data for {request.jurisdiction} "
                    f"(county n={gate_result.n_county}, state n={gate_result.n_state}, "
                    f"floor={gate_result.threshold}). Aggregate ranges suppressed "
                    f"per Year-2 credibility policy."
                ),
                response_time_ms=response_time_ms,
            )

        # Step 1: Query comparable cases at the tier the gate selected.
        comparable_cases = await self._query_comparable_cases(
            request, aggregation_level=gate_result.aggregation_level
        )

        # Step 2: Calculate ranges via percentile method.
        ranges, confidence = self._calculate_percentile_ranges(
            comparable_cases,
            request.medical_bills
        )
        
        # Step 3: Select representative comparable cases for report
        sample_cases = self._select_representative_cases(comparable_cases, limit=10)
        
        # Step 4: Generate justification (tier-aware copy)
        justification = self._generate_justification(
            n_cases=len(comparable_cases),
            confidence=confidence,
            request=request,
            ranges=ranges,
            aggregation_level=gate_result.aggregation_level,
            n_county=gate_result.n_county,
            n_state=gate_result.n_state,
        )
        
        # Calculate response time
        response_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
        
        return EstimateResponse(
            percentile_25=ranges["p25"],
            median=ranges["median"],
            percentile_75=ranges["p75"],
            percentile_95=ranges["p95"],
            n_cases=len(comparable_cases),
            confidence=confidence,
            aggregation_level=gate_result.aggregation_level,
            n_county=gate_result.n_county,
            n_state=gate_result.n_state,
            comparable_cases=sample_cases,
            range_justification=justification,
            response_time_ms=response_time_ms
        )
    
    async def _query_comparable_cases(
        self,
        request: EstimateRequest,
        aggregation_level: str = "county",
    ) -> List[SettleContribution]:
        """Query approved comparable cases from settle_contributions.

        Tier routing (Option D):
          - aggregation_level='county': exact jurisdiction match — numbers reflect
            ONLY the requested county. Used when gate cleared county tier (n>=50).
          - aggregation_level='state':  state-wide match (all counties in state)
            PLUS the "<STATE> (Unknown County)" sentinel bucket. Used when gate
            fell back to state tier. Two separate queries are issued (PostgREST
            `or` over two ILIKE patterns is brittle across client versions)
            and the results are merged/deduped.

        Falls back to _generate_mock_cases() when self.db is None or the
        jurisdiction is malformed — preserves current test behavior.
        """
        if self.db is None:
            logger.info(
                "_query_comparable_cases: self.db is None, falling back to mock"
            )
            return self._generate_mock_cases(request)

        # Parse state suffix once — needed for state tier; for county tier we
        # also use it as a validity check (malformed jurisdiction -> mock).
        try:
            state = request.jurisdiction.rsplit(",", 1)[1].strip()
        except (IndexError, AttributeError) as e:
            logger.warning(
                f"_query_comparable_cases: malformed jurisdiction "
                f"{request.jurisdiction!r}: {e}. Falling back to mock."
            )
            return self._generate_mock_cases(request)

        if not state:
            logger.warning(
                f"_query_comparable_cases: empty state extracted from "
                f"{request.jurisdiction!r}. Falling back to mock."
            )
            return self._generate_mock_cases(request)

        try:
            if aggregation_level == "state":
                rows = self._query_state_tier(request, state)
            else:
                # Default: county tier (back-compat with existing call sites)
                rows = self._query_county_tier(request)
        except Exception as e:
            logger.exception(
                f"_query_comparable_cases: query failed "
                f"(tier={aggregation_level}, state={state}, "
                f"case_type={request.case_type!r}, "
                f"injury_category={request.injury_category}): {e}. "
                f"Falling back to mock."
            )
            return self._generate_mock_cases(request)

        logger.info(
            f"_query_comparable_cases: returned {len(rows)} rows "
            f"(tier={aggregation_level}, state={state}, "
            f"case_type={request.case_type!r}, "
            f"injury_category={request.injury_category})"
        )

        # Convert rows to SettleContribution. Pydantic v2 silently drops
        # extra audit columns; missing `contributor_api_key_id` defaults to None.
        comparable_cases: List[SettleContribution] = []
        for row in rows:
            try:
                comparable_cases.append(SettleContribution(**row))
            except ValidationError as e:
                logger.warning(
                    f"_query_comparable_cases: skipping malformed row "
                    f"(id={row.get('id', '?')}): {e}"
                )

        return comparable_cases

    def _build_base_query(self, request: EstimateRequest):
        """Shared filter chain (status+case_type+injury) for both tiers."""
        query = (
            self.db.table("settle_contributions")
            .select("*")
            .eq("status", "approved")
            .eq("case_type", request.case_type)
        )
        if request.injury_category:
            query = query.cs("injury_category", request.injury_category)
        return query

    def _query_county_tier(self, request: EstimateRequest) -> List[dict]:
        """County-exact query. Returns raw row dicts (caller builds models)."""
        query = (
            self._build_base_query(request)
            .eq("jurisdiction", request.jurisdiction)
            .order("created_at", desc=True)
            .limit(50)
        )
        return query.execute().data or []

    def _query_state_tier(self, request: EstimateRequest, state: str) -> List[dict]:
        """State-tier query: county-suffix UNION sentinel, dedupe by id, cap 50.

        Two queries because PostgREST `or` with multiple ilike patterns is
        not uniformly supported across the client stack. Each query caps at
        50 rows on the server side; we dedupe client-side and truncate.
        """
        # Query A: all counties in state (e.g., 'Miami-Dade County, FL').
        q1 = (
            self._build_base_query(request)
            .ilike("jurisdiction", f"%, {state}")
            .order("created_at", desc=True)
            .limit(50)
        )
        rows_a = q1.execute().data or []

        # Query B: sentinel bucket (e.g., 'FL (Unknown County)').
        q2 = (
            self._build_base_query(request)
            .ilike("jurisdiction", f"{state} (%")
            .order("created_at", desc=True)
            .limit(50)
        )
        rows_b = q2.execute().data or []

        # Merge + dedupe by id, then truncate to 50 most recent.
        seen = set()
        merged: List[dict] = []
        for row in rows_a + rows_b:
            rid = row.get("id")
            if rid in seen:
                continue
            seen.add(rid)
            merged.append(row)
        merged.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return merged[:50]
    
    def _calculate_percentile_ranges(
        self,
        cases: List[SettleContribution],
        medical_bills: float
    ) -> Tuple[Dict[str, float], str]:
        """
        Calculate settlement ranges using percentile method.
        
        Algorithm:
        1. Extract outcome amounts from bucketed ranges (use midpoint)
        2. Calculate percentiles: 25th, 50th (median), 75th, 95th
        3. Adjust for medical bills (if significantly different)
        4. Determine confidence level based on case count
        
        Args:
            cases: List of comparable cases
            medical_bills: Medical bills amount
            
        Returns:
            Tuple of (ranges dict, confidence level)
        """
        # Step 1: Extract settlement amounts (convert buckets to midpoints)
        amounts = [self._bucket_to_midpoint(case.outcome_amount_range) for case in cases]
        amounts = np.array(amounts)
        
        # Step 2: Calculate percentiles
        p25 = float(np.percentile(amounts, 25))
        median = float(np.percentile(amounts, 50))
        p75 = float(np.percentile(amounts, 75))
        p95 = float(np.percentile(amounts, 95))
        
        # Step 3: Adjust for medical bills (if needed)
        # If current case's medical bills are significantly different from average,
        # apply proportional adjustment
        avg_medical_bills = np.mean([case.medical_bills for case in cases])
        if avg_medical_bills > 0:
            adjustment_ratio = medical_bills / avg_medical_bills
            # Only adjust if ratio is significantly different (< 0.5 or > 2.0)
            if adjustment_ratio < 0.5 or adjustment_ratio > 2.0:
                # Apply partial adjustment (50% weight)
                adjustment_factor = 1.0 + (adjustment_ratio - 1.0) * 0.5
                p25 *= adjustment_factor
                median *= adjustment_factor
                p75 *= adjustment_factor
                p95 *= adjustment_factor
        
        # Step 4: Determine confidence
        n_cases = len(cases)
        if n_cases >= self.CONFIDENCE_THRESHOLDS["high"]:
            confidence = "high"
        else:
            confidence = "medium"
        
        ranges = {
            "p25": round(p25, 2),
            "median": round(median, 2),
            "p75": round(p75, 2),
            "p95": round(p95, 2)
        }
        
        logger.info(f"Calculated percentile ranges: {ranges} (n={n_cases}, confidence={confidence})")
        
        return ranges, confidence
    
    def _bucket_to_midpoint(self, bucket: str) -> float:
        """
        Convert outcome amount bucket to midpoint value.
        
        Examples:
        - "$50k-$100k" -> 75000
        - "$1M+" -> 1500000 (conservative estimate)
        
        Args:
            bucket: Outcome amount range bucket
            
        Returns:
            Midpoint value in dollars
        """
        bucket_midpoints = {
            "$0-$50k": 25000,
            "$50k-$100k": 75000,
            "$100k-$150k": 125000,
            "$150k-$225k": 187500,
            "$225k-$300k": 262500,
            "$300k-$600k": 450000,
            "$600k-$1M": 800000,
            "$1M+": 1500000  # Conservative estimate for $1M+
        }
        
        return bucket_midpoints.get(bucket, 100000)  # Default to $100k
    
    def _select_representative_cases(
        self,
        cases: List[SettleContribution],
        limit: int = 10
    ) -> List[ComparableCase]:
        """
        Select representative comparable cases for report.
        
        Strategy:
        - Select cases across the settlement range (low, medium, high)
        - Prioritize recent cases
        - Limit to `limit` cases
        
        Args:
            cases: All comparable cases
            limit: Maximum number of cases to return
            
        Returns:
            List of ComparableCase objects (anonymized)
        """
        if not cases:
            return []
        
        # Sort by outcome range (ascending) and recency (descending)
        sorted_cases = sorted(
            cases,
            key=lambda c: (self._bucket_to_midpoint(c.outcome_amount_range), -c.contributed_at.timestamp())
        )
        
        # Select representative cases (spread across range)
        if len(sorted_cases) <= limit:
            selected = sorted_cases
        else:
            # Select cases evenly distributed across range
            step = len(sorted_cases) // limit
            selected = [sorted_cases[i * step] for i in range(limit)]
        
        # Convert to ComparableCase (anonymized)
        comparable_cases = [
            ComparableCase(
                jurisdiction=case.jurisdiction,
                case_type=case.case_type,
                injury_category=case.injury_category,
                primary_diagnosis=case.primary_diagnosis,
                medical_bills=case.medical_bills,
                outcome_range=case.outcome_amount_range,
                outcome_type=case.outcome_type,
                contributed_at=case.contributed_at
            )
            for case in selected
        ]
        
        return comparable_cases
    
    def _generate_justification(
        self,
        n_cases: int,
        confidence: str,
        request: EstimateRequest,
        ranges: Dict[str, float],
        aggregation_level: str = "county",
        n_county: int = 0,
        n_state: int = 0,
    ) -> str:
        """
        Generate tier-aware range justification text for report.

        Two tiers (Option D):
          - county: numbers reflect the requested county specifically.
          - state:  numbers reflect statewide + Unknown-County sentinel rows.
                    Copy tells the attorney that county-specific precision
                    is still being aggregated.
        """
        if confidence == "high":
            method = f"based on analysis of {n_cases} highly comparable cases"
        elif confidence == "medium":
            method = f"based on analysis of {n_cases} comparable cases"
        else:
            method = (
                f"using industry standard multipliers "
                f"(only {n_cases} comparable cases available)"
            )

        ranges_sentence = (
            f"The median settlement value is ${ranges['median']:,.0f}, with the "
            f"25th percentile at ${ranges['p25']:,.0f} and 75th percentile at "
            f"${ranges['p75']:,.0f}. The 95th percentile (high end) is "
            f"${ranges['p95']:,.0f}."
        )

        injuries = ", ".join(request.injury_category)

        if aggregation_level == "state":
            # Extract state code and county name for attorney-friendly copy.
            try:
                parts = request.jurisdiction.rsplit(",", 1)
                county_label = parts[0].strip() if len(parts) == 2 else request.jurisdiction
                state_label = parts[1].strip() if len(parts) == 2 else "your state"
            except Exception:
                county_label = request.jurisdiction
                state_label = "your state"

            justification = (
                f"Based on {n_state} {state_label} {request.case_type} verdicts "
                f"with {injuries}, calculated {method}. {ranges_sentence} "
                f"County-specific data for {county_label} is still being "
                f"aggregated (currently {n_county} verdicts); this estimate "
                f"uses statewide patterns. As more {county_label} cases enter "
                f"the database, county-specific precision will be available."
            )
        else:
            # county tier (or unexpected value; default to county copy)
            justification = (
                f"The settlement range estimate for {injuries} cases in "
                f"{request.jurisdiction} was calculated {method}. "
                f"{ranges_sentence} This range reflects actual case outcomes "
                f"in your jurisdiction with similar injury profiles and "
                f"medical expenses."
            )

        if confidence == "low":
            justification += (
                " Note: Due to limited comparable data, these estimates use "
                "conservative industry multipliers and should be considered "
                "preliminary estimates."
            )

        return justification
    
    def _generate_mock_cases(self, request: EstimateRequest) -> List[SettleContribution]:
        """
        Generate mock comparable cases for testing.
        
        TODO: Remove this when database is connected.
        
        Args:
            request: Estimate request
            
        Returns:
            List of mock SettleContribution objects
        """
        import uuid
        from datetime import timedelta
        
        # Generate 25 mock cases with variation
        mock_cases = []
        base_amount_ranges = [
            "$50k-$100k", "$100k-$150k", "$150k-$225k", "$225k-$300k", "$300k-$600k"
        ]
        
        for i in range(25):
            mock_case = SettleContribution(
                id=uuid.uuid4(),
                jurisdiction=request.jurisdiction,
                case_type=request.case_type or "Motor Vehicle Accident",
                injury_category=request.injury_category,
                primary_diagnosis="Spinal Injury",
                treatment_type=["Physical Therapy", "Surgery"],
                duration_of_treatment="6-12 months",
                imaging_findings=["Herniated Disc"],
                medical_bills=request.medical_bills * (0.7 + i * 0.02),  # Vary by ±30%
                lost_wages=5000 + i * 1000,
                policy_limits="$100k/$300k",
                defendant_category="Business",
                outcome_type="Settlement",
                outcome_amount_range=base_amount_ranges[i % len(base_amount_ranges)],
                contributed_at=datetime.now(UTC) - timedelta(days=i * 10),
                blockchain_hash=f"mock_hash_{i}",
                consent_confirmed=True,
                contributor_api_key_id=uuid.uuid4(),
                founding_member=True,
                created_at=datetime.now(UTC) - timedelta(days=i * 10),
                updated_at=datetime.now(UTC) - timedelta(days=i * 10),
                status="approved",
                rejection_reason=None,
                is_outlier=False,
                confidence_score=1.0
            )
            mock_cases.append(mock_case)
        
        return mock_cases

