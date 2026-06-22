"""
Tests for Phase 3.3: Override Tracking
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.override_tracking import (
    OverrideTrackingService,
    OverrideRecord,
    OverrideAnalytics,
)


class TestOverrideModels:
    """Tests for override tracking models."""

    def test_override_record(self):
        """Test OverrideRecord model."""
        record = OverrideRecord(
            id=uuid4(),
            query_id=uuid4(),
            contribution_id=uuid4(),
            estimate_median=75000.0,
            actual_outcome=95000.0,
            delta_pct=26.67,
            delta_direction="above",
            jurisdiction="Maricopa County, AZ",
            case_type="Motor Vehicle Accident",
            injury_category=["Spinal Injury"],
            medical_bills=25000.0,
            created_at=datetime.now(UTC),
        )

        assert record.delta_direction == "above"
        assert record.delta_pct == 26.67

    def test_override_analytics(self):
        """Test OverrideAnalytics model."""
        analytics = OverrideAnalytics(
            total_overrides=100,
            avg_delta_pct=15.5,
            above_estimate_pct=60.0,
            below_estimate_pct=40.0,
            by_jurisdiction=[{"jurisdiction": "Maricopa County, AZ", "count": 30, "avg_delta_pct": 12.0}],
            by_case_type=[{"case_type": "Motor Vehicle Accident", "count": 50, "avg_delta_pct": 18.0}],
        )

        assert analytics.total_overrides == 100
        assert analytics.above_estimate_pct == 60.0


class TestOverrideTrackingService:
    """Tests for the override tracking service."""

    @pytest.fixture
    def service(self):
        return OverrideTrackingService()

    @pytest.mark.asyncio
    async def test_record_override(self, service):
        """Test recording an override."""
        mock_record = {
            "id": str(uuid4()),
            "query_id": str(uuid4()),
            "contribution_id": str(uuid4()),
            "estimate_median": 75000.0,
            "actual_outcome": 95000.0,
            "delta_pct": 26.67,
            "delta_direction": "above",
            "jurisdiction": "Maricopa County, AZ",
            "case_type": "Motor Vehicle Accident",
            "injury_category": ["Spinal Injury"],
            "medical_bills": 25000.0,
            "created_at": datetime.now(UTC).isoformat(),
        }

        with patch("app.services.override_tracking.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.table.return_value.insert.return_value.execute = AsyncMock(
                return_value=MagicMock(data=[mock_record])
            )
            mock_get_db.return_value = mock_db

            result = await service.record_override(
                query_id=uuid4(),
                contribution_id=uuid4(),
                estimate_median=75000.0,
                actual_outcome=95000.0,
                jurisdiction="Maricopa County, AZ",
                case_type="Motor Vehicle Accident",
                injury_category=["Spinal Injury"],
                medical_bills=25000.0,
            )

            assert result.delta_direction == "above"
            assert result.delta_pct == 26.67

    @pytest.mark.asyncio
    async def test_get_analytics_empty(self, service):
        """Test analytics with no data."""
        with patch("app.services.override_tracking.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.table.return_value.select.return_value.execute = AsyncMock(
                return_value=MagicMock(data=None)
            )
            mock_get_db.return_value = mock_db

            result = await service.get_analytics()

            assert result.total_overrides == 0
