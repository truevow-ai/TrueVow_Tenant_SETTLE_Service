"""
Tests for Phase 2.5: Trend Studies / Market Reports
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.trend_reports import (
    TrendReportGenerator,
    InjuryTypeTrend,
    JurisdictionTrend,
    CarrierCategoryTrend,
    QuarterlyTrendReport,
    CoverageGapAnalysis,
    FoundingMemberHighlights,
    _percentile,
)


class TestTrendReportModels:
    """Tests for trend report Pydantic models."""

    def test_injury_type_trend(self):
        """Test InjuryTypeTrend model."""
        trend = InjuryTypeTrend(
            injury_type="Spinal Injury",
            total_cases=64,
            avg_settlement=89000.0,
            median_settlement=75000.0,
            p25_settlement=52000.0,
            p75_settlement=120000.0,
            avg_medical_bills=25000.0,
            avg_multiplier=3.56,
            case_count_change_pct=15.0,
        )

        assert trend.injury_type == "Spinal Injury"
        assert trend.total_cases == 64
        assert trend.avg_multiplier == 3.56

    def test_jurisdiction_trend(self):
        """Test JurisdictionTrend model."""
        trend = JurisdictionTrend(
            jurisdiction="Maricopa County, AZ",
            state="AZ",
            total_cases=120,
            avg_settlement=95000.0,
            median_settlement=82000.0,
            case_count_change_pct=22.5,
            coverage_status="adequate",
        )

        assert trend.jurisdiction == "Maricopa County, AZ"
        assert trend.coverage_status == "adequate"

    def test_carrier_category_trend(self):
        """Test CarrierCategoryTrend model."""
        trend = CarrierCategoryTrend(
            defendant_category="Business",
            defendant_industry="Healthcare",
            total_cases=342,
            avg_settlement=89000.0,
            settlement_rate=0.78,
            trial_rate=0.12,
            lowball_indicator=0.23,
        )

        assert trend.defendant_category == "Business"
        assert trend.settlement_rate == 0.78

    def test_quarterly_trend_report(self):
        """Test QuarterlyTrendReport model."""
        report = QuarterlyTrendReport(
            report_id="trend-2026-q1",
            period="Q1 2026",
            generated_at=datetime.utcnow(),
            total_contributions=500,
            total_queries=1200,
            total_reports_generated=350,
            active_contributors=45,
            injury_type_trends=[],
            jurisdiction_trends=[],
            carrier_category_trends=[],
            top_jurisdictions_by_volume=[],
            fastest_growing_injury_types=[],
        )

        assert report.report_id == "trend-2026-q1"
        assert report.period == "Q1 2026"
        assert "Not predictive" in report.methodology

    def test_coverage_gap_analysis(self):
        """Test CoverageGapAnalysis model."""
        analysis = CoverageGapAnalysis(
            total_jurisdictions_tracked=100,
            jurisdictions_with_adequate_data=20,
            jurisdictions_with_growing_data=30,
            jurisdictions_with_thin_data=50,
            coverage_pct=50.0,
            gaps=[{"jurisdiction": "Rural County, WY", "state": "WY", "case_count": 2}],
            recommendations=["Focus Founding Member recruitment in thin-data areas."],
        )

        assert analysis.total_jurisdictions_tracked == 100
        assert analysis.coverage_pct == 50.0

    def test_founding_member_highlights(self):
        """Test FoundingMemberHighlights model."""
        highlights = FoundingMemberHighlights(
            total_founding_members=2100,
            active_contributors=450,
            total_contributions=5000,
            avg_contributions_per_member=11.1,
            top_contributors=[{"member_id": "abc123", "contributions": 150}],
            milestone_achievements=["Member abc123... reached 100+ contributions"],
        )

        assert highlights.total_founding_members == 2100
        assert highlights.avg_contributions_per_member == 11.1


class TestPercentileCalculation:
    """Tests for the percentile utility function."""

    def test_percentile_median(self):
        """Test median calculation."""
        data = [10, 20, 30, 40, 50]
        assert _percentile(data, 50) == 30.0

    def test_percentile_p25(self):
        """Test 25th percentile."""
        data = [10, 20, 30, 40, 50]
        assert _percentile(data, 25) == 20.0

    def test_percentile_p75(self):
        """Test 75th percentile."""
        data = [10, 20, 30, 40, 50]
        assert _percentile(data, 75) == 40.0

    def test_percentile_empty_data(self):
        """Test empty data returns None."""
        assert _percentile([], 50) is None

    def test_percentile_single_value(self):
        """Test single value returns that value."""
        assert _percentile([42], 50) == 42.0


class TestTrendReportGenerator:
    """Tests for the trend report generator."""

    @pytest.fixture
    def generator(self):
        return TrendReportGenerator()

    @pytest.mark.asyncio
    async def test_generate_quarterly_report_empty_data(self, generator):
        """Test report generation with no data."""
        with patch("app.services.trend_reports.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.table.return_value.select.return_value.eq.return_value.gte.return_value.lte.return_value.execute = MagicMock(
                return_value=MagicMock(data=None)
            )
            mock_get_db.return_value = mock_db

            result = await generator.generate_quarterly_report(2026, 1)

            assert result.report_id == "trend-2026-q1"
            assert result.period == "Q1 2026"
            assert result.total_contributions == 0
            assert result.injury_type_trends == []
            assert result.jurisdiction_trends == []

    @pytest.mark.asyncio
    async def test_generate_coverage_gap_analysis_empty(self, generator):
        """Test coverage gap analysis with no data."""
        with patch("app.services.trend_reports.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.table.return_value.select.return_value.eq.return_value.execute = MagicMock(
                return_value=MagicMock(data=None)
            )
            mock_get_db.return_value = mock_db

            result = await generator.generate_coverage_gap_analysis()

            assert result.total_jurisdictions_tracked == 0
            assert result.coverage_pct == 0

    @pytest.mark.asyncio
    async def test_generate_founding_member_highlights_empty(self, generator):
        """Test founding member highlights with no data."""
        with patch("app.services.trend_reports.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_chain = MagicMock()
            mock_chain.execute = MagicMock(return_value=MagicMock(data=None))
            mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value = mock_chain
            mock_db.table.return_value.select.return_value.execute = MagicMock(return_value=MagicMock(data=None))
            mock_get_db.return_value = mock_db

            result = await generator.generate_founding_member_highlights()

            assert result.total_founding_members == 0
            assert result.active_contributors == 0
            assert result.total_contributions == 0
