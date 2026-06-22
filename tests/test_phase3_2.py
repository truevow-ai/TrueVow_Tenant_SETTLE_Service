"""
Tests for Phase 3.2: Overdemand Cliff Detection
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.overdemand_cliff import (
    OverdemandCliffDetector,
    OverdemandCliffResponse,
    _estimate_from_range,
    AMOUNT_BUCKETS,
)


class TestOverdemandCliffModels:
    """Tests for overdemand cliff models."""

    def test_overdemand_cliff_response_with_cliff(self):
        """Test response when cliff is detected."""
        response = OverdemandCliffResponse(
            threshold=180000,
            settlement_rate_below=0.72,
            settlement_rate_above=0.31,
            has_cliff=True,
            warning="Historical data shows demands above $180,000 settle 41% less often.",
        )

        assert response.has_cliff is True
        assert response.threshold == 180000
        assert "Not predictive" in response.methodology

    def test_overdemand_cliff_response_no_cliff(self):
        """Test response when no cliff is detected."""
        response = OverdemandCliffResponse(
            has_cliff=False,
            warning="No significant overdemand cliff detected.",
        )

        assert response.has_cliff is False
        assert response.threshold is None


class TestEstimateFromRange:
    """Tests for the range estimation utility."""

    def test_all_ranges(self):
        """Test all range mappings."""
        assert _estimate_from_range("$0-$50k") == 25000
        assert _estimate_from_range("$50k-$100k") == 75000
        assert _estimate_from_range("$100k-$150k") == 125000
        assert _estimate_from_range("$150k-$225k") == 187500
        assert _estimate_from_range("$225k-$300k") == 262500
        assert _estimate_from_range("$300k-$600k") == 450000
        assert _estimate_from_range("$600k-$1M") == 800000
        assert _estimate_from_range("$1M+") == 1500000
        assert _estimate_from_range("invalid") is None


class TestAmountBuckets:
    """Tests for the amount bucket definitions."""

    def test_bucket_count(self):
        """Test correct number of buckets."""
        assert len(AMOUNT_BUCKETS) == 8

    def test_bucket_ranges(self):
        """Test bucket range boundaries."""
        assert AMOUNT_BUCKETS[0] == (0, 50000)
        assert AMOUNT_BUCKETS[1] == (50000, 100000)
        assert AMOUNT_BUCKETS[-1][0] == 1000000


class TestOverdemandCliffDetector:
    """Tests for the overdemand cliff detector."""

    @pytest.fixture
    def detector(self):
        return OverdemandCliffDetector()

    @pytest.mark.asyncio
    async def test_insufficient_data(self, detector):
        """Test with insufficient data."""
        with patch("app.services.overdemand_cliff.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(
                return_value=MagicMock(data=[])
            )
            mock_get_db.return_value = mock_db

            result = await detector.detect_cliff()

            assert result.has_cliff is False
            assert "Insufficient data" in result.warning

    @pytest.mark.asyncio
    async def test_no_cliff_detected(self, detector):
        """Test when no cliff is detected."""
        # Create mock data with consistent settlement rates
        rows = []
        for amount in [25000, 50000, 75000, 100000, 125000, 150000, 175000, 200000]:
            rows.append({
                "exact_outcome_amount": amount,
                "outcome_type": "Settlement",
                "outcome_amount_range": "$0-$50k",
            })

        with patch("app.services.overdemand_cliff.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.table.return_value.select.return_value.eq.return_value.execute = AsyncMock(
                return_value=MagicMock(data=rows)
            )
            mock_get_db.return_value = mock_db

            result = await detector.detect_cliff()

            # All settlements = no cliff
            assert result.has_cliff is False
