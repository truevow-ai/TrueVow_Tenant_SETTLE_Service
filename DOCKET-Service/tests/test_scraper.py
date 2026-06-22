"""
Tests for DOCKET-Service CourtListener Scraper
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.scraping.courtlistener_scraper import (
    CourtListenerScraper,
    _map_case_type,
    _map_status,
    _parse_date,
)


class TestCourtListenerScraperHelpers:
    """Tests for scraper helper functions."""

    def test_map_case_type_civil(self):
        assert _map_case_type({"nature_of_suit": "civil"}) == "Civil"

    def test_map_case_type_criminal(self):
        assert _map_case_type({"nature_of_suit": "criminal"}) == "Criminal"

    def test_map_case_type_bankruptcy(self):
        assert _map_case_type({"nature_of_suit": "bankruptcy"}) == "Bankruptcy"

    def test_map_case_type_personal_injury(self):
        assert _map_case_type({"nature_of_suit": "personal injury"}) == "Personal Injury"

    def test_map_case_type_contract(self):
        assert _map_case_type({"nature_of_suit": "contract"}) == "Contract Dispute"

    def test_map_case_type_employment(self):
        assert _map_case_type({"nature_of_suit": "employment"}) == "Employment"

    def test_map_case_type_unknown(self):
        assert _map_case_type({"nature_of_suit": "unknown"}) is None

    def test_map_status_active(self):
        assert _map_status({"date_terminated": None}) == "active"

    def test_map_status_closed(self):
        assert _map_status({"date_terminated": "2024-01-15"}) == "closed"

    def test_parse_date_valid(self):
        assert _parse_date("2024-01-15T00:00:00Z") == "2024-01-15"

    def test_parse_date_none(self):
        assert _parse_date(None) is None

    def test_parse_date_empty(self):
        assert _parse_date("") is None


class TestCourtListenerScraper:
    """Tests for the CourtListener scraper."""

    def test_init_with_api_key(self):
        scraper = CourtListenerScraper(api_key="test-key")
        assert scraper.headers["Authorization"] == "Token test-key"

    def test_init_without_api_key(self):
        with patch("app.services.scraping.courtlistener_scraper.settings") as mock_settings:
            mock_settings.COURT_LISTENER_API_KEY = "env-key"
            scraper = CourtListenerScraper()
            assert scraper.headers["Authorization"] == "Token env-key"

    @pytest.mark.asyncio
    async def test_fetch_dockets_empty_response(self):
        """Test fetching dockets with empty API response."""
        scraper = CourtListenerScraper(api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {"results": [], "next": None}
        mock_response.raise_for_status = MagicMock()

        scraper.client.get = AsyncMock(return_value=mock_response)

        results = await scraper.fetch_dockets(limit=10)

        assert results == []
        await scraper.close()

    @pytest.mark.asyncio
    async def test_fetch_dockets_with_results(self):
        """Test fetching dockets with API results."""
        scraper = CourtListenerScraper(api_key="test-key")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "court": "caed",
                    "docket_number": "2:24-cv-01234",
                    "case_name": "Smith v. Jones",
                    "date_filed": "2024-01-15",
                    "nature_of_suit": "civil",
                }
            ],
            "next": None,
        }
        mock_response.raise_for_status = MagicMock()

        scraper.client.get = AsyncMock(return_value=mock_response)

        results = await scraper.fetch_dockets(limit=10)

        assert len(results) == 1
        assert results[0]["case_name"] == "Smith v. Jones"
        await scraper.close()
