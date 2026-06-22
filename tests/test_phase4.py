"""
Tests for Phase 4: Litigation Outcome Distribution
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.outcome_distribution import (
    OutcomeDistributionAnalyzer,
    OutcomeDistributionResponse,
    OutcomeTypeDistribution,
    TrialRiskIndicators,
    _estimate_from_range,
)


class TestOutcomeDistributionModels:
    """Tests for outcome distribution models."""

    def test_outcome_type_distribution(self):
        """Test OutcomeTypeDistribution model."""
        dist = OutcomeTypeDistribution(
            rate=0.72,
            avg_amount=85000.0,
            count=144,
        )

        assert dist.rate == 0.72
        assert dist.count == 144

    def test_trial_risk_indicators(self):
        """Test TrialRiskIndicators model."""
        indicators = TrialRiskIndicators(
            trial_propensity=0.18,
            plaintiff_verdict_rate=0.65,
            defense_verdict_rate=0.35,
            verdict_premium=45.0,
        )

        assert indicators.trial_propensity == 0.18
        assert indicators.verdict_premium == 45.0

    def test_outcome_distribution_response(self):
        """Test OutcomeDistributionResponse model."""
        response = OutcomeDistributionResponse(
            outcome_distribution={
                "settlement": {"rate": 0.72, "avg_amount": 85000, "count": 144},
            },
            trial_risk_indicators=TrialRiskIndicators(
                trial_propensity=0.18,
                plaintiff_verdict_rate=0.65,
                defense_verdict_rate=0.35,
            ),
            sample_size=200,
            jurisdiction="Maricopa County, AZ",
            case_type="Motor Vehicle Accident",
            injury_tags=["Spinal Injury"],
        )

        assert response.sample_size == 200
        assert "not predictive" in response.methodology.lower()


class TestEstimateFromRange:
    """Tests for range estimation utility."""

    def test_all_ranges(self):
        assert _estimate_from_range("$0-$50k") == 25000
        assert _estimate_from_range("$50k-$100k") == 75000
        assert _estimate_from_range("$1M+") == 1500000
        assert _estimate_from_range("invalid") is None


class TestOutcomeDistributionAnalyzer:
    """Tests for the outcome distribution analyzer."""

    @pytest.fixture
    def analyzer(self):
        return OutcomeDistributionAnalyzer()

    @pytest.mark.asyncio
    async def test_analyze_empty_data(self, analyzer):
        """Test analysis with no data."""
        with patch("app.services.outcome_distribution.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(
                return_value=MagicMock(data=None)
            )
            mock_get_db.return_value = mock_db

            result = await analyzer.analyze()

            assert result.sample_size == 0
            assert result.outcome_distribution == {}

    @pytest.mark.asyncio
    async def test_analyze_with_settlement_data(self, analyzer):
        """Test analysis with settlement data."""
        rows = [
            {"outcome_type": "Settlement", "exact_outcome_amount": 75000, "outcome_amount_range": "$50k-$100k"},
            {"outcome_type": "Settlement", "exact_outcome_amount": 95000, "outcome_amount_range": "$50k-$100k"},
            {"outcome_type": "Jury Verdict", "exact_outcome_amount": 150000, "outcome_amount_range": "$100k-$150k"},
        ]

        with patch("app.services.outcome_distribution.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(
                return_value=MagicMock(data=rows)
            )
            mock_get_db.return_value = mock_db

            result = await analyzer.analyze()

            assert result.sample_size == 3
            assert "settlement" in result.outcome_distribution
            assert result.trial_risk_indicators is not None
