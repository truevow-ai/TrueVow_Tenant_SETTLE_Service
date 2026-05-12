"""
Settlement Range Estimator Service

Core algorithm for calculating settlement ranges based on comparable cases.
Uses percentile-based calculation (25th, median, 75th, 95th) with multiplier fallback.

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
    Settlement Range Estimator using percentile-based calculation.
    
    Algorithm:
    1. Query database for comparable cases (jurisdiction, case type, injury)
    2. If >= 15 cases: Calculate percentiles (25th, median, 75th, 95th)
    3. If < 15 cases: Use multiplier fallback (medical bills * industry multipliers)
    4. Assign confidence level: high (30+), medium (15-29), low (<15)
    5. Return range with comparable cases
    """
    
    # Industry standard multipliers for fallback
    MEDICAL_MULTIPLIERS = {
        "low": {"min": 1.5, "typical": 2.0, "high": 3.0},
        "medium": {"min": 2.0, "typical": 3.5, "high": 5.0},
        "high": {"min": 3.0, "typical": 5.0, "high": 8.0}
    }
    
    # Confidence thresholds
    CONFIDENCE_THRESHOLDS = {
        "high": 30,     # 30+ cases = high confidence
        "medium": 15,   # 15-29 cases = medium confidence
        "low": 0        # <15 cases = low confidence (use multipliers)
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

        # Year-2 "Never Sell Empty Dashboards" gate — runs BEFORE we query.
        # If fewer than MIN_AGGREGATE_N approved rows match, we short-circuit
        # to own-case-only. No multiplier fallback — synthesizing a range from
        # zero comparable cases is exactly the anti-pattern this gate blocks.
        gate_result = await self.gate.check(
            jurisdiction=request.jurisdiction,
            case_type=request.case_type,
        )
        if gate_result.status == "insufficient_data":
            response_time_ms = int(
                (datetime.now(UTC) - start_time).total_seconds() * 1000
            )
            logger.info(
                "Estimator short-circuit: insufficient_data for %s (n=%d, floor=%d)",
                request.jurisdiction, gate_result.n, gate_result.threshold,
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
                comparable_cases=[],
                range_justification=(
                    f"Insufficient approved data in {request.jurisdiction} "
                    f"(n={gate_result.n}, floor={gate_result.threshold}). "
                    f"Aggregate ranges suppressed per Year-2 credibility policy."
                ),
                response_time_ms=response_time_ms,
            )

        # Step 1: Query comparable cases (gate already passed, so n>=50)
        comparable_cases = await self._query_comparable_cases(request)

        # Step 2: Calculate ranges via percentile method.
        # Multiplier fallback is retired — see _calculate_multiplier_ranges TODO.
        ranges, confidence = self._calculate_percentile_ranges(
            comparable_cases,
            request.medical_bills
        )
        
        # Step 3: Select representative comparable cases for report
        sample_cases = self._select_representative_cases(comparable_cases, limit=10)
        
        # Step 4: Generate justification
        justification = self._generate_justification(
            n_cases=len(comparable_cases),
            confidence=confidence,
            request=request,
            ranges=ranges
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
            comparable_cases=sample_cases,
            range_justification=justification,
            response_time_ms=response_time_ms
        )
    
    async def _query_comparable_cases(
        self, request: EstimateRequest
    ) -> List[SettleContribution]:
        """Query approved comparable cases from settle_contributions.

        Filters: same state (parsed from jurisdiction), same case_type,
        overlapping injury_category (array-contains), status='approved'.
        Returns at most 50 most recent cases.

        Falls back to _generate_mock_cases() when self.db is None — preserves
        current behavior until SETTLE_USE_MOCK_DATA is flipped to false.
        """
        # Mock fallback — preserves current behavior when DB client isn't wired
        if self.db is None:
            logger.info(
                "_query_comparable_cases: self.db is None, falling back to mock"
            )
            return self._generate_mock_cases(request)

        # Parse state from jurisdiction (e.g. "Miami-Dade County, FL" -> "FL")
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

        # Build query: approved + state-suffix + case_type + overlapping injury_category
        try:
            query = (
                self.db.table("settle_contributions")
                .select("*")
                .eq("status", "approved")
                .eq("case_type", request.case_type)
                .ilike("jurisdiction", f"%, {state}")
            )

            # Array-contains: only rows where injury_category contains ALL
            # requested categories. Skip filter when request list is empty.
            if request.injury_category:
                query = query.cs("injury_category", request.injury_category)

            # Cap at 50 most recent (statistical ceiling for percentile calc)
            query = query.order("created_at", desc=True).limit(50)

            response = query.execute()  # synchronous per SupabaseRESTQuery contract
            rows = response.data or []

        except Exception as e:
            logger.exception(
                f"_query_comparable_cases: query failed "
                f"(state={state}, case_type={request.case_type!r}, "
                f"injury_category={request.injury_category}): {e}. "
                f"Falling back to mock."
            )
            return self._generate_mock_cases(request)

        logger.info(
            f"_query_comparable_cases: returned {len(rows)} rows "
            f"(state={state}, case_type={request.case_type!r}, "
            f"injury_category={request.injury_category})"
        )

        # Convert rows to SettleContribution (direct path confirmed by Stage 2.3b.1 probe).
        # Pydantic v2 silently drops the 13 extra audit columns; missing
        # `contributor_api_key_id` defaults to None.
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
    
    def _calculate_multiplier_ranges(
        self,
        medical_bills: float,
        n_cases: int
    ) -> Tuple[Dict[str, float], str]:
        """
        Calculate settlement ranges using multiplier fallback method.

        TODO Year-2: RETIRED. The IntelligenceGate now short-circuits any
        request with n<50 to own_case_only instead of synthesizing a range
        from industry multipliers. Kept here only to avoid a churny diff;
        remove once all callers are audited.

        Used when insufficient comparable cases (<15).
        
        Algorithm:
        1. Determine severity level (based on medical bills)
        2. Apply industry standard multipliers
        3. Generate conservative range
        
        Args:
            medical_bills: Medical bills amount
            n_cases: Number of comparable cases found
            
        Returns:
            Tuple of (ranges dict, confidence level = 'low')
        """
        # Determine severity level based on medical bills
        if medical_bills < 5000:
            severity = "low"
        elif medical_bills < 25000:
            severity = "medium"
        else:
            severity = "high"
        
        # Get multipliers
        multipliers = self.MEDICAL_MULTIPLIERS[severity]
        
        # Calculate ranges
        p25 = medical_bills * multipliers["min"]
        median = medical_bills * multipliers["typical"]
        p75 = medical_bills * multipliers["high"]
        p95 = medical_bills * multipliers["high"] * 1.5  # Extra cushion for 95th
        
        ranges = {
            "p25": round(p25, 2),
            "median": round(median, 2),
            "p75": round(p75, 2),
            "p95": round(p95, 2)
        }
        
        logger.warning(
            f"Insufficient cases (n={n_cases}). Using multiplier fallback: {ranges}"
        )
        
        return ranges, "low"
    
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
        ranges: Dict[str, float]
    ) -> str:
        """
        Generate range justification text for report.
        
        Args:
            n_cases: Number of comparable cases
            confidence: Confidence level
            request: Original request
            ranges: Calculated ranges
            
        Returns:
            Justification text
        """
        if confidence == "high":
            method = f"based on analysis of {n_cases} highly comparable cases"
        elif confidence == "medium":
            method = f"based on analysis of {n_cases} comparable cases"
        else:
            method = f"using industry standard multipliers (only {n_cases} comparable cases available)"
        
        justification = (
            f"The settlement range estimate for {', '.join(request.injury_category)} cases in "
            f"{request.jurisdiction} was calculated {method}. "
            f"The median settlement value is ${ranges['median']:,.0f}, with the "
            f"25th percentile at ${ranges['p25']:,.0f} and 75th percentile at "
            f"${ranges['p75']:,.0f}. The 95th percentile (high end) is "
            f"${ranges['p95']:,.0f}. This range reflects actual case outcomes "
            f"in your jurisdiction with similar injury profiles and medical expenses."
        )
        
        if confidence == "low":
            justification += (
                " Note: Due to limited comparable data in this jurisdiction, "
                "these estimates use conservative industry multipliers and should "
                "be considered preliminary estimates."
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

