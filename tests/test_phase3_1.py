"""
Tests for Phase 3.1: Multiplier Model Layer
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import MagicMock

from app.models.case_bank import EstimateRequest
from app.services.estimator import SettlementEstimator


class TestMultiplierModelLayer:
    """Tests for the multiplier-based estimation method."""

    @pytest.fixture
    def estimator(self):
        return SettlementEstimator(db_connection=None)

    def _make_mock_case(self, outcome_range="$50k-$100k", exact_amount=None, confidence_score=0.8):
        """Create a mock SettleContribution."""
        case = MagicMock()
        case.outcome_amount_range = outcome_range
        case.exact_outcome_amount = exact_amount
        case.confidence_score = confidence_score
        case.source_type = "firm_submission"
        case.contributed_at = datetime.now(UTC)
        case.jurisdiction = "Test County, TX"
        case.case_type = "Motor Vehicle Accident"
        case.injury_category = ["Spinal Injury"]
        case.medical_bills = 25000
        case.defendant_category = "Business"
        case.outcome_type = "Settlement"
        return case

    def test_model_c_standard_multiplier_table(self, estimator):
        """Test Model C: Standard multiplier table when n<20."""
        cases = [self._make_mock_case() for _ in range(10)]  # n<20
        request = EstimateRequest(
            jurisdiction="Test County, TX",
            case_type="Motor Vehicle Accident",
            injury_category=["Spinal Injury"],
            medical_bills=25000,
        )

        result = estimator._calculate_multiplier_ranges(cases, 25000, request)

        assert "low" in result
        assert "median" in result
        assert "high" in result
        assert "model_label" in result
        assert "base_multiplier" in result
        assert result["low"] > 0
        assert result["median"] > result["low"]
        assert result["high"] > result["median"]

    def test_model_a_community_comp_set(self, estimator):
        """Test Model A: Community Comp Set when n>=50."""
        cases = [self._make_mock_case(exact_amount=87500) for _ in range(60)]  # n>=50
        request = EstimateRequest(
            jurisdiction="Test County, TX",
            case_type="Motor Vehicle Accident",
            injury_category=["Spinal Injury"],
            medical_bills=25000,
        )

        result = estimator._calculate_multiplier_ranges(cases, 25000, request)

        assert "Community Comp Set" in result["model_label"]
        assert result["base_multiplier"] > 0
        assert result["low"] > 0
        assert result["median"] > result["low"]
        assert result["high"] > result["median"]

    def test_model_b_statewide_benchmark(self, estimator):
        """Test Model B: Statewide Benchmark when n>=20 and n<50."""
        cases = [self._make_mock_case(exact_amount=87500) for _ in range(30)]  # 20<=n<50
        request = EstimateRequest(
            jurisdiction="Test County, TX",
            case_type="Motor Vehicle Accident",
            injury_category=["Spinal Injury"],
            medical_bills=25000,
        )

        result = estimator._calculate_multiplier_ranges(cases, 25000, request)

        assert "Statewide Benchmark" in result["model_label"]
        assert result["base_multiplier"] > 0

    def test_zero_medical_bills(self, estimator):
        """Test handling of zero medical bills."""
        cases = [self._make_mock_case() for _ in range(10)]
        request = EstimateRequest(
            jurisdiction="Test County, TX",
            case_type="Motor Vehicle Accident",
            injury_category=["Spinal Injury"],
            medical_bills=0,
        )

        result = estimator._calculate_multiplier_ranges(cases, 0, request)

        assert result["low"] == 0
        assert result["median"] == 0
        assert result["high"] == 0

    def test_government_defendant_adjustment(self, estimator):
        """Test government defendant adjustment."""
        cases = [self._make_mock_case(exact_amount=87500) for _ in range(60)]
        request = EstimateRequest(
            jurisdiction="Test County, TX",
            case_type="Motor Vehicle Accident",
            injury_category=["Spinal Injury"],
            medical_bills=25000,
            defendant_category="Government Entity",
        )

        result = estimator._calculate_multiplier_ranges(cases, 25000, request)

        assert len(result["adjustments_applied"]) > 0
        assert any("Government" in label for label in result["adjustments_applied"])

    def test_comparative_negligence_adjustment(self, estimator):
        """Test comparative negligence adjustment."""
        cases = [self._make_mock_case(exact_amount=87500) for _ in range(60)]
        request = EstimateRequest(
            jurisdiction="Test County, TX",
            case_type="Motor Vehicle Accident",
            injury_category=["Spinal Injury"],
            medical_bills=25000,
            comparative_negligence_min=30.0,
        )

        result = estimator._calculate_multiplier_ranges(cases, 25000, request)

        assert len(result["adjustments_applied"]) > 0
        assert any("comparative negligence" in label.lower() for label in result["adjustments_applied"])
