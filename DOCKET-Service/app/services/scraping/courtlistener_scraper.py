"""
CourtListener API Scraper — DOCKET-Service
Fetches docket data from CourtListener's free RECAP API.
https://www.courtlistener.com/help/api/rest/

Usage:
    python -m app.services.scraping.courtlistener_scraper
    python -m app.services.scraping.courtlistener_scraper --case-type "Civil" --limit 100
"""

import asyncio
import logging
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime, UTC

import httpx

from app.core.config import settings
from app.core.database import get_db
from app.services.docket_search import create_docket
from app.models.docket import DocketCreateRequest

logger = logging.getLogger(__name__)


# CourtListener API endpoints
CL_BASE_URL = "https://www.courtlistener.com/api/rest/v4"
CL_DOCKETS_ENDPOINT = f"{CL_BASE_URL}/dockets/"
CL_OPINIONS_ENDPOINT = f"{CL_BASE_URL}/opinions/"


class CourtListenerScraper:
    """Scraper for CourtListener RECAP API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.COURT_LISTENER_API_KEY
        self.headers = {}
        if self.api_key:
            self.headers["Authorization"] = f"Token {self.api_key}"

        self.client = httpx.AsyncClient(
            base_url=CL_BASE_URL,
            headers=self.headers,
            timeout=60,
        )

    async def fetch_dockets(
        self,
        case_type: Optional[str] = None,
        court_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch dockets from CourtListener API.

        Args:
            case_type: Filter by case type (e.g., "Civil", "Criminal")
            court_id: Filter by court ID (e.g., "caed", "nyed")
            date_from: Filter by filing date from (ISO format)
            date_to: Filter by filing date to (ISO format)
            limit: Maximum number of results to fetch

        Returns:
            List of docket data dictionaries
        """
        params = {
            "limit": min(limit, 100),  # API max per page
            "order_by": "-date_filed",
        }

        if court_id:
            params["court"] = court_id
        if date_from:
            params["date_filed__gte"] = date_from
        if date_to:
            params["date_filed__lte"] = date_to

        # Note: CourtListener doesn't have a direct case_type filter on dockets
        # We filter by nature of suit code if available
        if case_type:
            params["nature_of_suit"] = self._case_type_to_nos_code(case_type)

        all_results = []
        next_url = CL_DOCKETS_ENDPOINT

        while next_url and len(all_results) < limit:
            try:
                response = await self.client.get(next_url, params=params if next_url == CL_DOCKETS_ENDPOINT else None)
                response.raise_for_status()
                data = response.json()

                results = data.get("results", [])
                all_results.extend(results)

                next_url = data.get("next")
                params = {}  # Clear params for subsequent pages (URL already has them)

                logger.info(f"Fetched {len(results)} dockets (total: {len(all_results)})")

                if not next_url:
                    break

            except httpx.HTTPStatusError as e:
                logger.error(f"CourtListener API error: {e.response.status_code} — {e.response.text}")
                break
            except Exception as e:
                logger.error(f"CourtListener fetch error: {e}")
                break

        return all_results[:limit]

    async def fetch_opinions(
        self,
        court_id: Optional[str] = None,
        date_from: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch opinions from CourtListener API.

        Args:
            court_id: Filter by court ID
            date_from: Filter by date filed from
            limit: Maximum number of results

        Returns:
            List of opinion data dictionaries
        """
        params = {
            "limit": min(limit, 100),
            "order_by": "-date_filed",
        }

        if court_id:
            params["cluster__docket__court"] = court_id
        if date_from:
            params["date_filed__gte"] = date_from

        all_results = []
        next_url = CL_OPINIONS_ENDPOINT

        while next_url and len(all_results) < limit:
            try:
                response = await self.client.get(next_url, params=params if next_url == CL_OPINIONS_ENDPOINT else None)
                response.raise_for_status()
                data = response.json()

                results = data.get("results", [])
                all_results.extend(results)

                next_url = data.get("next")
                params = {}

                logger.info(f"Fetched {len(results)} opinions (total: {len(all_results)})")

                if not next_url:
                    break

            except Exception as e:
                logger.error(f"CourtListener opinion fetch error: {e}")
                break

        return all_results[:limit]

    def _case_type_to_nos_code(self, case_type: str) -> Optional[str]:
        """Map case type to CourtListener nature of suit code."""
        nos_mapping = {
            "Civil": "civil",
            "Criminal": "criminal",
            "Bankruptcy": "bankruptcy",
            "Personal Injury": "personal_injury",
            "Contract Dispute": "contract",
            "Employment": "employment",
            "Real Estate": "real_estate",
        }
        return nos_mapping.get(case_type)

    async def close(self):
        await self.client.aclose()


async def scrape_and_store(
    case_type: Optional[str] = None,
    court_id: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, int]:
    """
    Scrape dockets from CourtListener and store in DOCKET-Service database.

    Args:
        case_type: Filter by case type
        court_id: Filter by court ID
        limit: Maximum dockets to fetch

    Returns:
        Dict with counts: inserted, skipped, failed
    """
    scraper = CourtListenerScraper()
    stats = {"inserted": 0, "skipped": 0, "failed": 0}

    try:
        dockets = await scraper.fetch_dockets(
            case_type=case_type,
            court_id=court_id,
            limit=limit,
        )

        logger.info(f"Processing {len(dockets)} dockets for storage...")

        for docket_data in dockets:
            try:
                # Map CourtListener fields to our schema
                request = DocketCreateRequest(
                    court_id=docket_data.get("court"),
                    case_number=docket_data.get("docket_number"),
                    case_name=docket_data.get("case_name"),
                    case_type=_map_case_type(docket_data),
                    filing_date=_parse_date(docket_data.get("date_filed")),
                    status=_map_status(docket_data),
                    judge_name=docket_data.get("assigned_to_str"),
                    source="courtlistener",
                    source_url=docket_data.get("absolute_url"),
                )

                await create_docket(request, source="courtlistener")
                stats["inserted"] += 1

            except Exception as e:
                logger.warning(f"Failed to store docket {docket_data.get('docket_number')}: {e}")
                stats["failed"] += 1

        logger.info(f"Scraping complete: {stats}")

    finally:
        await scraper.close()

    return stats


def _map_case_type(docket_data: Dict[str, Any]) -> Optional[str]:
    """Map CourtListener docket data to our case type."""
    nos = docket_data.get("nature_of_suit", "")
    if "civil" in nos.lower():
        return "Civil"
    elif "criminal" in nos.lower():
        return "Criminal"
    elif "bankruptcy" in nos.lower():
        return "Bankruptcy"
    elif "personal" in nos.lower() or "injury" in nos.lower():
        return "Personal Injury"
    elif "contract" in nos.lower():
        return "Contract Dispute"
    elif "employment" in nos.lower():
        return "Employment"
    return None


def _map_status(docket_data: Dict[str, Any]) -> Optional[str]:
    """Map CourtListener docket data to our status."""
    terminated = docket_data.get("date_terminated")
    if terminated:
        return "closed"
    return "active"


def _parse_date(date_str: Optional[str]) -> Optional[str]:
    """Parse date string from CourtListener."""
    if not date_str:
        return None
    try:
        return date_str[:10]  # Return YYYY-MM-DD portion
    except Exception:
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="CourtListener Docket Scraper")
    parser.add_argument("--case-type", type=str, help="Filter by case type")
    parser.add_argument("--court-id", type=str, help="Filter by court ID (e.g., caed)")
    parser.add_argument("--limit", type=int, default=100, help="Maximum dockets to fetch")

    args = parser.parse_args()

    async def main():
        stats = await scrape_and_store(
            case_type=args.case_type,
            court_id=args.court_id,
            limit=args.limit,
        )
        print(f"\nScraping complete: {stats}")

    asyncio.run(main())
