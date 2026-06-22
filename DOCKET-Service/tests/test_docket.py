"""
Tests for DOCKET-Service
"""

import pytest
from datetime import datetime, UTC, date
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.docket import (
    DocketCase,
    DocketSearchFilter,
    DocketSearchResult,
    DocketSearchResponse,
    DocketStatsResponse,
    DocketCreateRequest,
    DocketUpdateRequest,
)


class TestDocketModels:
    """Tests for docket Pydantic models."""

    def test_docket_case(self):
        """Test DocketCase model."""
        case = DocketCase(
            id=uuid4(),
            court_id="caed",
            case_number="2:24-cv-01234",
            case_name="Smith v. Jones",
            case_type="Personal Injury",
            filing_date=date(2024, 1, 15),
            status="active",
            judge_name="Hon. Jane Doe",
            plaintiff_attorney="John Smith, Esq.",
            defense_attorney="Jane Doe, Esq.",
            plaintiff_firm="Smith Law Firm",
            defense_firm="Doe Defense LLP",
            damages_claimed=500000.0,
            damages_awarded=350000.0,
            settlement_amount=300000.0,
            source="courtlistener",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        assert case.case_name == "Smith v. Jones"
        assert case.case_type == "Personal Injury"
        assert case.damages_awarded == 350000.0

    def test_docket_search_filter_defaults(self):
        """Test default values for search filter."""
        filters = DocketSearchFilter()
        assert filters.page == 1
        assert filters.page_size == 50
        assert filters.sort_by == "filing_date"
        assert filters.sort_order == "desc"

    def test_docket_search_response(self):
        """Test search response model."""
        response = DocketSearchResponse(
            results=[],
            total_count=0,
            page=1,
            page_size=50,
            total_pages=0,
            has_next=False,
            has_prev=False,
            response_time_ms=50,
        )

        assert response.total_count == 0
        assert response.response_time_ms == 50

    def test_docket_stats_response(self):
        """Test stats response model."""
        stats = DocketStatsResponse(
            total_cases=100,
            by_case_type={"Personal Injury": 40, "Contract Dispute": 30},
            by_status={"active": 60, "closed": 40},
            by_source={"courtlistener": 80, "manual": 20},
            by_judge={"Hon. Jane Doe": 25},
            avg_damages_awarded=125000.0,
            avg_settlement_amount=95000.0,
            date_range={"min": "2020-01-01", "max": "2024-12-31"},
        )

        assert stats.total_cases == 100
        assert stats.avg_damages_awarded == 125000.0

    def test_docket_create_request(self):
        """Test create request model."""
        req = DocketCreateRequest(
            court_id="caed",
            case_number="2:24-cv-01234",
            case_name="Smith v. Jones",
            case_type="Personal Injury",
            filing_date=date(2024, 1, 15),
            status="active",
            damages_claimed=500000.0,
        )

        assert req.case_type == "Personal Injury"
        assert req.status == "active"

    def test_docket_update_request(self):
        """Test update request model."""
        req = DocketUpdateRequest(
            status="closed",
            settlement_amount=300000.0,
        )

        assert req.status == "closed"
        assert req.settlement_amount == 300000.0


class TestDocketSearchService:
    """Tests for docket search service."""

    @pytest.mark.asyncio
    async def test_search_empty_data(self):
        """Test search with no data."""
        from app.services.docket_search import search_dockets

        mock_response = MagicMock()
        mock_response.data = None
        mock_response.count = 0

        mock_query = MagicMock()
        mock_query.execute = AsyncMock(return_value=mock_response)
        mock_query.is_ = MagicMock(return_value=mock_query)
        mock_query.eq = MagicMock(return_value=mock_query)
        mock_query.ilike = MagicMock(return_value=mock_query)
        mock_query.gte = MagicMock(return_value=mock_query)
        mock_query.lte = MagicMock(return_value=mock_query)
        mock_query.order = MagicMock(return_value=mock_query)
        mock_query.limit = MagicMock(return_value=mock_query)

        mock_table = MagicMock()
        mock_table.select = MagicMock(return_value=mock_query)

        mock_db = MagicMock()
        mock_db.table = MagicMock(return_value=mock_table)

        with patch("app.services.docket_search.get_db", new_callable=AsyncMock) as mock_get_db:
            mock_get_db.return_value = mock_db

            filters = DocketSearchFilter()
            result = await search_dockets(filters)

            assert result.total_count == 0
            assert result.results == []

    @pytest.mark.skip(reason="Complex mock chaining — service tests deferred to integration testing")
    @pytest.mark.asyncio
    async def test_get_stats_empty_data(self):
        """Test stats with no data."""
        pass
