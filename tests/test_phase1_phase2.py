"""
Tests for Phase 1-2.3 new features:
- Confidence Score Service (Phase 2.1)
- Internal Verdict Search (Phase 1)
- Carrier Pattern Analytics (Phase 2.3)
"""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.confidence_score import ConfidenceScoreCalculator, ConfidenceScoreResponse
from app.services.carrier_patterns import (
    get_carrier_patterns,
    _estimate_amount_from_range,
    _percentile,
    CarrierPattern,
    CarrierPatternsResponse,
)
from app.models.verdicts import (
    VerdictSearchFilter,
    VerdictSearchResponse,
    VerdictStatsResponse,
)


# ============================================================================
# CONFIDENCE SCORE TESTS (Phase 2.1)
# ============================================================================

class TestConfidenceScoreCalculator:
    """Tests for the Demand Confidence Score calculator."""

    @pytest.fixture
    def calculator(self):
        return ConfidenceScoreCalculator()

    @pytest.mark.asyncio
    async def test_high_confidence_score(self, calculator):
        """Test high confidence with excellent data."""
        mock_cases = self._make_mock_cases(
            count=64,
            confidence_scores=[0.9] * 64,
            days_old=10,
            outlier_rate=0.02,
        )

        result = await calculator.calculate(
            n_cases=64,
            aggregation_level="county",
            n_county=64,
            n_state=200,
            injury_category=["Spinal Injury"],
            cases=mock_cases,
        )

        assert isinstance(result, ConfidenceScoreResponse)
        assert result.overall >= 50  # Should be at least "Moderate"
        assert len(result.factors) == 7

    @pytest.mark.asyncio
    async def test_low_confidence_score(self, calculator):
        """Test low confidence with minimal data."""
        mock_cases = self._make_mock_cases(
            count=20,
            confidence_scores=[0.3] * 20,
            days_old=400,
            outlier_rate=0.35,
        )

        result = await calculator.calculate(
            n_cases=20,
            aggregation_level="state",
            n_county=5,
            n_state=80,
            injury_category=["Soft Tissue"],
            cases=mock_cases,
        )

        assert isinstance(result, ConfidenceScoreResponse)
        assert result.overall <= 50  # Should be "Moderate" or lower
        assert result.label in ("Moderate", "Cautious", "Insufficient Data")

    @pytest.mark.asyncio
    async def test_score_clamped_10_95(self, calculator):
        """Test that score is clamped between 10 and 95."""
        # Best case scenario
        mock_cases = self._make_mock_cases(
            count=200,
            confidence_scores=[1.0] * 200,
            days_old=1,
            outlier_rate=0.0,
        )

        result = await calculator.calculate(
            n_cases=200,
            aggregation_level="county",
            n_county=200,
            n_state=500,
            injury_category=["Spinal Injury"],
            cases=mock_cases,
        )

        assert 10 <= result.overall <= 95

    @pytest.mark.asyncio
    async def test_warnings_generated(self, calculator):
        """Test that warnings are generated for poor data."""
        mock_cases = self._make_mock_cases(
            count=15,
            confidence_scores=[0.4] * 15,
            days_old=500,
            outlier_rate=0.25,
        )

        result = await calculator.calculate(
            n_cases=15,
            aggregation_level="state",
            n_county=5,
            n_state=60,
            injury_category=["Soft Tissue"],
            cases=mock_cases,
        )

        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_no_cases_returns_default_scores(self, calculator):
        """Test behavior when no cases are provided."""
        result = await calculator.calculate(
            n_cases=0,
            aggregation_level="none",
            n_county=0,
            n_state=0,
            injury_category=[],
            cases=None,
        )

        assert isinstance(result, ConfidenceScoreResponse)
        assert 10 <= result.overall <= 95

    def _make_mock_cases(self, count, confidence_scores, days_old, outlier_rate):
        """Create mock case objects for testing."""
        cases = []
        outlier_count = int(count * outlier_rate)
        for i in range(count):
            case = MagicMock()
            case.confidence_score = confidence_scores[i] if i < len(confidence_scores) else 0.5
            case.created_at = datetime.now(UTC) - timedelta(days=days_old)
            case.is_outlier = i < outlier_count
            case.injury_category = ["Spinal Injury"]
            case.jurisdiction = "Test County, TX"
            case.case_type = "Motor Vehicle Accident"
            case.medical_bills = 50000
            case.defendant_category = "Business"
            case.outcome_type = "Settlement"
            case.outcome_amount_range = "$50k-$100k"
            cases.append(case)
        return cases


# ============================================================================
# CARRIER PATTERN TESTS (Phase 2.3)
# ============================================================================

class TestCarrierPatterns:
    """Tests for carrier pattern analytics."""

    def test_estimate_amount_from_range(self):
        """Test range to amount estimation."""
        assert _estimate_amount_from_range("$0-$50k") == 25000
        assert _estimate_amount_from_range("$50k-$100k") == 75000
        assert _estimate_amount_from_range("$100k-$150k") == 125000
        assert _estimate_amount_from_range("$1M+") == 1500000
        assert _estimate_amount_from_range("invalid") is None

    def test_percentile_calculation(self):
        """Test percentile calculation."""
        data = [10, 20, 30, 40, 50]
        assert _percentile(data, 50) == 30.0
        assert _percentile(data, 25) == 20.0
        assert _percentile(data, 75) == 40.0
        assert _percentile([], 50) == 0.0

    @pytest.mark.asyncio
    async def test_empty_patterns(self):
        """Test empty result when no data."""
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute = MagicMock(
            return_value=MagicMock(data=None)
        )

        with patch("app.services.carrier_patterns.get_db", new_callable=AsyncMock) as mock_get_db:
            mock_get_db.return_value = mock_db

            result = await get_carrier_patterns()

            assert result.patterns == []
            assert result.total_cases == 0

    def test_carrier_pattern_model(self):
        """Test CarrierPattern model creation."""
        pattern = CarrierPattern(
            defendant_category="Business",
            defendant_industry="Healthcare",
            case_count=50,
            avg_settlement_range={"low": 40000, "median": 75000, "high": 120000},
            settlement_rate=0.78,
            avg_time_to_resolution_days=180,
            trial_rate=0.12,
            lowball_indicator=0.23,
            median_settlement=75000,
            p25_settlement=40000,
            p75_settlement=120000,
        )

        assert pattern.defendant_category == "Business"
        assert pattern.case_count == 50
        assert pattern.settlement_rate == 0.78

    def test_carrier_patterns_response_model(self):
        """Test CarrierPatternsResponse model."""
        response = CarrierPatternsResponse(
            patterns=[],
            total_cases=0,
            jurisdiction="Test County, TX",
            case_type="Motor Vehicle Accident",
        )

        assert response.jurisdiction == "Test County, TX"
        assert "Not predictive" in response.methodology


# ============================================================================
# VERDICT SEARCH MODEL TESTS (Phase 1)
# ============================================================================

class TestVerdictSearchModels:
    """Tests for verdict search models."""

    def test_verdict_search_filter_defaults(self):
        """Test default values for search filter."""
        filters = VerdictSearchFilter()
        assert filters.page == 1
        assert filters.page_size == 50
        assert filters.sort_by == "verdict_date"
        assert filters.sort_order == "desc"

    def test_verdict_search_filter_with_values(self):
        """Test search filter with values."""
        filters = VerdictSearchFilter(
            jurisdiction="Maricopa County, AZ",
            case_type=["Motor Vehicle Accident"],
            verdict_amount_min=50000,
            verdict_amount_max=500000,
            page=2,
            page_size=25,
        )

        assert filters.jurisdiction == "Maricopa County, AZ"
        assert filters.page == 2
        assert filters.page_size == 25

    def test_verdict_stats_response(self):
        """Test stats response model."""
        stats = VerdictStatsResponse(
            total_verdicts=100,
            by_outcome_type={"verdict_plaintiff": 40, "settlement": 50, "dismissed": 10},
            by_case_type={"Motor Vehicle Accident": 60, "Slip/Fall": 40},
            by_jurisdiction={"Maricopa County, AZ": 30},
            by_review_status={"verified": 80, "pending": 20},
            by_source={"scraped": 70, "manual_entry": 30},
            avg_confidence_score=0.75,
            avg_completeness_score=0.65,
            avg_total_verdict=125000,
            avg_settlement_amount=85000,
            avg_medical_bills=25000,
            avg_trial_duration_days=5.5,
            date_range={"min": "2020-01-01", "max": "2024-12-31"},
        )

        assert stats.total_verdicts == 100
        assert stats.avg_confidence_score == 0.75
