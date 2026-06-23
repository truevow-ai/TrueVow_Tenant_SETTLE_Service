"""
Litigation Outcome Distribution Service — Phase 4

Descriptive analysis of historical outcome distributions.
NOT predictive — "Historical data shows..." not "AI predicts..."

For a given case profile, shows the historical distribution of outcomes:
- Settlement rate and average amount
- Plaintiff verdict rate and average amount
- Defense verdict rate
- Dismissal rate
- Time to resolution by outcome type

Bar compliance: All language is descriptive, not predictive.
"""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.database import get_db

logger = logging.getLogger(__name__)


# ============================================================================
# OUTCOME DISTRIBUTION MODELS
# ============================================================================

class OutcomeTypeDistribution(BaseModel):
    """Distribution for a single outcome type."""
    rate: float = Field(..., description="Proportion of cases with this outcome")
    avg_amount: Optional[float] = Field(None, description="Average amount for this outcome type")
    count: int = Field(..., description="Number of cases with this outcome")


class TrialRiskIndicators(BaseModel):
    """Descriptive trial risk indicators."""
    trial_propensity: float = Field(..., description="Proportion of similar cases that went to trial")
    plaintiff_verdict_rate: float = Field(..., description="Plaintiff win rate in trials")
    defense_verdict_rate: float = Field(..., description="Defense win rate in trials")
    verdict_premium: Optional[float] = Field(None, description="How much verdicts exceed settlements on average")
    median_time_to_resolution_days: Optional[float] = Field(None, description="Median days to resolution")


class OutcomeDistributionResponse(BaseModel):
    """Complete outcome distribution analysis."""
    outcome_distribution: Dict[str, OutcomeTypeDistribution] = Field(
        default_factory=dict,
        description="Distribution of outcome types",
    )
    trial_risk_indicators: Optional[TrialRiskIndicators] = None
    sample_size: int = Field(..., description="Total cases analyzed")
    jurisdiction: Optional[str] = None
    case_type: Optional[str] = None
    injury_tags: List[str] = Field(default_factory=list)
    methodology: str = Field(
        default="Historical outcome distribution from anonymized settlement and verdict data. Descriptive statistics only, not predictive.",
    )


# ============================================================================
# OUTCOME DISTRIBUTION ANALYZER
# ============================================================================

class OutcomeDistributionAnalyzer:
    """Analyzes historical outcome distributions."""

    async def analyze(
        self,
        jurisdiction: Optional[str] = None,
        case_type: Optional[str] = None,
        injury_category: Optional[List[str]] = None,
    ) -> OutcomeDistributionResponse:
        """
        Analyze historical outcome distribution for a case profile.

        Args:
            jurisdiction: Optional jurisdiction filter
            case_type: Optional case type filter
            injury_category: Optional injury category filter

        Returns:
            OutcomeDistributionResponse with descriptive statistics
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

        result = query.execute()
        rows = result.data or []

        if not rows:
            return OutcomeDistributionResponse(
                sample_size=0,
                jurisdiction=jurisdiction,
                case_type=case_type,
                injury_tags=injury_category or [],
            )

        # Group by outcome type
        outcome_groups: Dict[str, List[dict]] = {}
        for row in rows:
            outcome = row.get("outcome_type", "Unknown")
            if outcome not in outcome_groups:
                outcome_groups[outcome] = []
            outcome_groups[outcome].append(row)

        total = len(rows)
        distribution = {}

        # Map outcome types to standardized categories
        outcome_mapping = {
            "Settlement": "settlement",
            "Jury Verdict": "plaintiff_verdict",
            "Judge's Decision": "plaintiff_verdict",
            "Arbitration Award": "settlement",
            "Mediation": "settlement",
        }

        mapped_groups: Dict[str, List[dict]] = {}
        for outcome, group_rows in outcome_groups.items():
            mapped = outcome_mapping.get(outcome, outcome.lower().replace(" ", "_"))
            if mapped not in mapped_groups:
                mapped_groups[mapped] = []
            mapped_groups[mapped].extend(group_rows)

        # Calculate distribution
        for outcome_type, group_rows in mapped_groups.items():
            amounts = []
            for row in group_rows:
                exact = row.get("exact_outcome_amount")
                if exact is not None:
                    amounts.append(exact)
                else:
                    estimated = _estimate_from_range(row.get("outcome_amount_range", ""))
                    if estimated:
                        amounts.append(estimated)

            avg_amount = sum(amounts) / len(amounts) if amounts else None

            distribution[outcome_type] = OutcomeTypeDistribution(
                rate=round(len(group_rows) / total, 3),
                avg_amount=round(avg_amount, 2) if avg_amount else None,
                count=len(group_rows),
            )

        # Trial risk indicators
        trial_count = sum(
            len(rows) for outcome, rows in mapped_groups.items()
            if "verdict" in outcome.lower()
        )
        settlement_count = sum(
            len(rows) for outcome, rows in mapped_groups.items()
            if "settlement" in outcome.lower()
        )

        plaintiff_verdict_count = len(mapped_groups.get("plaintiff_verdict", []))
        defense_verdict_count = len(mapped_groups.get("defense_verdict", []))
        total_trials = plaintiff_verdict_count + defense_verdict_count

        # Verdict premium (how much verdicts exceed settlements)
        settlement_amounts = []
        for row in mapped_groups.get("settlement", []):
            exact = row.get("exact_outcome_amount")
            if exact:
                settlement_amounts.append(exact)

        verdict_amounts = []
        for row in mapped_groups.get("plaintiff_verdict", []):
            exact = row.get("exact_outcome_amount")
            if exact:
                verdict_amounts.append(exact)

        avg_settlement = sum(settlement_amounts) / len(settlement_amounts) if settlement_amounts else None
        avg_verdict = sum(verdict_amounts) / len(verdict_amounts) if verdict_amounts else None
        verdict_premium = ((avg_verdict / avg_settlement) - 1) * 100 if avg_settlement and avg_verdict and avg_settlement > 0 else None

        trial_risk = TrialRiskIndicators(
            trial_propensity=round(trial_count / total, 3) if total > 0 else 0,
            plaintiff_verdict_rate=round(plaintiff_verdict_count / total_trials, 3) if total_trials > 0 else 0,
            defense_verdict_rate=round(defense_verdict_count / total_trials, 3) if total_trials > 0 else 0,
            verdict_premium=round(verdict_premium, 1) if verdict_premium else None,
        )

        return OutcomeDistributionResponse(
            outcome_distribution={k: v.model_dump() for k, v in distribution.items()},
            trial_risk_indicators=trial_risk,
            sample_size=total,
            jurisdiction=jurisdiction,
            case_type=case_type,
            injury_tags=injury_category or [],
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
outcome_distribution_analyzer = OutcomeDistributionAnalyzer()
