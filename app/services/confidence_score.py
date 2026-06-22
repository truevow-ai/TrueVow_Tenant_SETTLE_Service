"""
Demand Confidence Score Service — Phase 2.1

Customer-facing 0-100 confidence score (SettleCase DSI equivalent).
Transforms existing admin-only confidence_score into a structured,
multi-factor score returned with every estimate.

7 weighted factors (clamped 10-95):
  1. Comp set depth (20%) — n>=50 max, n>=20 partial, n<20 suppressed
  2. Reputation distribution (15%) — avg contributor reputation
  3. Jurisdiction coverage (15%) — county vs state vs sentinel
  4. Injury type specificity (15%) — tag match depth
  5. Data recency (10%) — days since last submission
  6. Outlier rate (15%) — % flagged as outliers
  7. Completeness (10%) — required field fill rate
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC, timedelta

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIDENCE SCORE MODELS
# ============================================================================

class ConfidenceFactor(BaseModel):
    """Single factor in the confidence score breakdown."""
    score: int = Field(..., ge=0, le=10, description="Factor score 0-10")
    max: int = Field(default=10, description="Maximum possible score")
    weight: float = Field(..., ge=0, le=1, description="Factor weight (0-1)")
    detail: str = Field(..., description="Human-readable explanation")


class ConfidenceScoreResponse(BaseModel):
    """Customer-facing confidence score (0-100)."""
    overall: int = Field(..., ge=10, le=95, description="Overall confidence score (clamped 10-95)")
    label: str = Field(..., description="Very Strong, Strong, Moderate, Cautious, or Insufficient Data")
    factors: Dict[str, ConfidenceFactor] = Field(..., description="Breakdown by factor")
    warnings: List[str] = Field(default_factory=list, description="Actionable warnings for the user")


# ============================================================================
# SCORING CONSTANTS
# ============================================================================

# Factor weights (must sum to 1.0)
FACTOR_WEIGHTS = {
    "comp_set_depth": 0.20,
    "reputation_distribution": 0.15,
    "jurisdiction_coverage": 0.15,
    "injury_type_specificity": 0.15,
    "data_recency": 0.10,
    "outlier_rate": 0.15,
    "completeness": 0.10,
}

# Label thresholds
LABEL_THRESHOLDS = [
    (80, "Very Strong"),
    (65, "Strong"),
    (50, "Moderate"),
    (35, "Cautious"),
    (0, "Insufficient Data"),
]

# Clamping range
SCORE_MIN = 10
SCORE_MAX = 95


# ============================================================================
# CONFIDENCE SCORE CALCULATOR
# ============================================================================

class ConfidenceScoreCalculator:
    """
    Calculates the customer-facing Demand Confidence Score.

    Usage:
        calc = ConfidenceScoreCalculator()
        score = await calc.calculate(
            n_cases=64,
            aggregation_level="county",
            n_county=64,
            n_state=200,
            injury_category=["Spinal Injury"],
            cases=comparable_cases,  # List of SettleContribution
        )
    """

    async def calculate(
        self,
        n_cases: int,
        aggregation_level: str,
        n_county: int,
        n_state: int,
        injury_category: List[str],
        cases: Optional[List[Any]] = None,
    ) -> ConfidenceScoreResponse:
        """
        Calculate the full confidence score with factor breakdown.

        Args:
            n_cases: Number of comparable cases used in the estimate
            aggregation_level: "county", "state", or "none"
            n_county: County-level case count
            n_state: State-level case count
            injury_category: List of injury tags requested
            cases: List of comparable case objects (for recency/outlier/completeness)
        """
        factors = {}
        warnings = []

        # 1. Comp set depth (20%)
        comp_score, comp_detail = self._score_comp_set_depth(n_cases, n_county, n_state)
        factors["comp_set_depth"] = ConfidenceFactor(
            score=comp_score,
            max=10,
            weight=FACTOR_WEIGHTS["comp_set_depth"],
            detail=comp_detail,
        )
        if n_cases < 20:
            warnings.append(f"Limited comparable cases ({n_cases}). Score will improve as more data is contributed.")

        # 2. Reputation distribution (15%)
        rep_score, rep_detail = self._score_reputation(cases)
        factors["reputation_distribution"] = ConfidenceFactor(
            score=rep_score,
            max=10,
            weight=FACTOR_WEIGHTS["reputation_distribution"],
            detail=rep_detail,
        )

        # 3. Jurisdiction coverage (15%)
        jur_score, jur_detail = self._score_jurisdiction(aggregation_level, n_county, n_state)
        factors["jurisdiction_coverage"] = ConfidenceFactor(
            score=jur_score,
            max=10,
            weight=FACTOR_WEIGHTS["jurisdiction_coverage"],
            detail=jur_detail,
        )
        if aggregation_level == "state":
            warnings.append("Using statewide data — county-specific data will improve precision.")

        # 4. Injury type specificity (15%)
        injury_score, injury_detail = self._score_injury_specificity(injury_category, cases)
        factors["injury_type_specificity"] = ConfidenceFactor(
            score=injury_score,
            max=10,
            weight=FACTOR_WEIGHTS["injury_type_specificity"],
            detail=injury_detail,
        )

        # 5. Data recency (10%)
        recency_score, recency_detail = self._score_recency(cases)
        factors["data_recency"] = ConfidenceFactor(
            score=recency_score,
            max=10,
            weight=FACTOR_WEIGHTS["data_recency"],
            detail=recency_detail,
        )
        if recency_score <= 4:
            warnings.append("Data recency could be improved — no recent submissions in this category.")

        # 6. Outlier rate (15%)
        outlier_score, outlier_detail = self._score_outlier_rate(cases)
        factors["outlier_rate"] = ConfidenceFactor(
            score=outlier_score,
            max=10,
            weight=FACTOR_WEIGHTS["outlier_rate"],
            detail=outlier_detail,
        )

        # 7. Completeness (10%)
        completeness_score, completeness_detail = self._score_completeness(cases)
        factors["completeness"] = ConfidenceFactor(
            score=completeness_score,
            max=10,
            weight=FACTOR_WEIGHTS["completeness"],
            detail=completeness_detail,
        )

        # Calculate weighted total (0-10 scale)
        raw_score = sum(
            f.score * f.weight for f in factors.values()
        )

        # Convert to 0-100 scale
        scaled_score = raw_score * 10

        # Clamp to 10-95
        overall = max(SCORE_MIN, min(SCORE_MAX, int(scaled_score)))

        # Determine label
        label = self._get_label(overall)

        return ConfidenceScoreResponse(
            overall=overall,
            label=label,
            factors=factors,
            warnings=warnings,
        )

    def _score_comp_set_depth(self, n_cases: int, n_county: int, n_state: int) -> tuple:
        """Score based on comparable case count."""
        if n_cases >= 100:
            return 10, f"{n_cases} comparable cases found — excellent data depth"
        elif n_cases >= 50:
            return 8, f"{n_cases} comparable cases found — strong data depth"
        elif n_cases >= 30:
            return 6, f"{n_cases} comparable cases found — moderate data depth"
        elif n_cases >= 20:
            return 4, f"{n_cases} comparable cases found — limited data"
        else:
            return 2, f"{n_cases} comparable cases found — minimal data"

    def _score_reputation(self, cases: Optional[List[Any]]) -> tuple:
        """Score based on contributor reputation distribution."""
        if not cases:
            return 5, "Reputation data unavailable — default score applied"

        reputations = []
        for case in cases:
            rep = getattr(case, "confidence_score", None)
            if rep is not None:
                reputations.append(rep)

        if not reputations:
            return 5, "Reputation data unavailable — default score applied"

        avg_rep = sum(reputations) / len(reputations)

        if avg_rep >= 0.85:
            return 10, f"High contributor reputation (avg {avg_rep:.2f})"
        elif avg_rep >= 0.70:
            return 8, f"Good contributor reputation (avg {avg_rep:.2f})"
        elif avg_rep >= 0.50:
            return 6, f"Moderate contributor reputation (avg {avg_rep:.2f})"
        elif avg_rep >= 0.30:
            return 4, f"Lower contributor reputation (avg {avg_rep:.2f})"
        else:
            return 2, f"Low contributor reputation (avg {avg_rep:.2f})"

    def _score_jurisdiction(self, aggregation_level: str, n_county: int, n_state: int) -> tuple:
        """Score based on jurisdiction coverage level."""
        if aggregation_level == "county" and n_county >= 50:
            return 10, f"County-level data available ({n_county} cases)"
        elif aggregation_level == "county" and n_county >= 20:
            return 8, f"County-level data with moderate coverage ({n_county} cases)"
        elif aggregation_level == "state":
            return 6, f"Statewide data ({n_state} cases) — less precise than county-level"
        else:
            return 2, "No jurisdiction-specific data available"

    def _score_injury_specificity(self, injury_category: List[str], cases: Optional[List[Any]]) -> tuple:
        """Score based on injury tag match depth."""
        if not cases or not injury_category:
            return 5, "Injury specificity data unavailable"

        # Check how many cases match the requested injury tags
        matching = 0
        for case in cases:
            case_injuries = getattr(case, "injury_category", [])
            if any(tag in case_injuries for tag in injury_category):
                matching += 1

        match_rate = matching / len(cases) if cases else 0

        if match_rate >= 0.8:
            return 10, f"High injury specificity ({len(injury_category)} tags, {match_rate:.0%} match rate)"
        elif match_rate >= 0.5:
            return 7, f"Moderate injury specificity ({len(injury_category)} tags, {match_rate:.0%} match rate)"
        elif match_rate >= 0.3:
            return 5, f"Low injury specificity ({len(injury_category)} tags, {match_rate:.0%} match rate)"
        else:
            return 3, f"Very low injury specificity ({len(injury_category)} tags, {match_rate:.0%} match rate)"

    def _score_recency(self, cases: Optional[List[Any]]) -> tuple:
        """Score based on data recency."""
        if not cases:
            return 5, "Recency data unavailable"

        now = datetime.now(UTC)
        dates = []
        for case in cases:
            created = getattr(case, "created_at", None)
            if created:
                if isinstance(created, str):
                    try:
                        created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        continue
                if hasattr(created, "tzinfo") and created.tzinfo is None:
                    created = created.replace(tzinfo=UTC)
                dates.append(created)

        if not dates:
            return 5, "Recency data unavailable"

        most_recent = max(dates)
        days_old = (now - most_recent).days

        if days_old <= 30:
            return 10, f"Very recent data (last submission {days_old} days ago)"
        elif days_old <= 90:
            return 8, f"Recent data (last submission {days_old} days ago)"
        elif days_old <= 180:
            return 6, f"Moderately recent data (last submission {days_old} days ago)"
        elif days_old <= 365:
            return 4, f"Older data (last submission {days_old} days ago)"
        else:
            return 2, f"Stale data (last submission {days_old} days ago)"

    def _score_outlier_rate(self, cases: Optional[List[Any]]) -> tuple:
        """Score based on outlier rate in the dataset."""
        if not cases:
            return 7, "Outlier data unavailable — default score applied"

        total = len(cases)
        outliers = sum(1 for c in cases if getattr(c, "is_outlier", False))
        outlier_rate = outliers / total if total > 0 else 0

        if outlier_rate <= 0.05:
            return 10, f"Very low outlier rate ({outlier_rate:.0%})"
        elif outlier_rate <= 0.10:
            return 8, f"Low outlier rate ({outlier_rate:.0%})"
        elif outlier_rate <= 0.20:
            return 6, f"Moderate outlier rate ({outlier_rate:.0%})"
        elif outlier_rate <= 0.30:
            return 4, f"High outlier rate ({outlier_rate:.0%})"
        else:
            return 2, f"Very high outlier rate ({outlier_rate:.0%})"

    def _score_completeness(self, cases: Optional[List[Any]]) -> tuple:
        """Score based on data completeness (required field fill rate)."""
        if not cases:
            return 7, "Completeness data unavailable — default score applied"

        required_fields = [
            "jurisdiction", "case_type", "injury_category", "medical_bills",
            "defendant_category", "outcome_type", "outcome_amount_range",
        ]

        completeness_scores = []
        for case in cases:
            filled = 0
            for field in required_fields:
                val = getattr(case, field, None)
                if val is not None and val != [] and val != "":
                    filled += 1
            completeness_scores.append(filled / len(required_fields))

        if not completeness_scores:
            return 7, "Completeness data unavailable"

        avg_completeness = sum(completeness_scores) / len(completeness_scores)

        if avg_completeness >= 0.95:
            return 10, f"Excellent data completeness ({avg_completeness:.0%} fields filled)"
        elif avg_completeness >= 0.85:
            return 8, f"Good data completeness ({avg_completeness:.0%} fields filled)"
        elif avg_completeness >= 0.70:
            return 6, f"Moderate data completeness ({avg_completeness:.0%} fields filled)"
        elif avg_completeness >= 0.50:
            return 4, f"Low data completeness ({avg_completeness:.0%} fields filled)"
        else:
            return 2, f"Very low data completeness ({avg_completeness:.0%} fields filled)"

    def _get_label(self, score: int) -> str:
        """Get the label for a given score."""
        for threshold, label in LABEL_THRESHOLDS:
            if score >= threshold:
                return label
        return "Insufficient Data"


# Singleton instance
confidence_calculator = ConfidenceScoreCalculator()
