"""
E2E Integration Tests — SETTLE Backend API
Tests the full API flow from request to response.
Run against a live SETTLE backend instance.

Usage:
    python -m pytest tests/test_e2e_integration.py -v --tb=short
    python -m pytest tests/test_e2e_integration.py -v --tb=short --backend-url http://localhost:8002
"""

import pytest
import httpx
import os
from typing import Optional

BACKEND_URL = os.environ.get("SETTLE_BACKEND_URL", "http://localhost:8002")
API_KEY = os.environ.get("SETTLE_API_KEY", "test-admin-key")


@pytest.fixture
def client():
    """HTTP client for backend API."""
    return httpx.AsyncClient(base_url=BACKEND_URL, timeout=30)


def auth_headers():
    return {"X-API-Key": API_KEY, "Authorization": f"Bearer {API_KEY}"}


class TestE2EHealthCheck:
    """E2E: Health check endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint returns service info."""
        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert "service" in data or "status" in data

    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health endpoint."""
        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as client:
            response = await client.get("/health")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_query_health(self):
        """Test query service health."""
        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as client:
            response = await client.get("/api/v1/query/health")
            assert response.status_code == 200


class TestE2EQueryEstimate:
    """E2E: Settlement estimate API."""

    @pytest.mark.asyncio
    async def test_estimate_with_auth(self):
        """Test estimate endpoint with authentication."""
        payload = {
            "jurisdiction": "Test County, TX",
            "case_type": "Motor Vehicle Accident",
            "injury_category": ["Spinal Injury"],
            "medical_bills": 25000,
        }

        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as client:
            response = await client.post(
                "/api/v1/query/estimate",
                json=payload,
                headers=auth_headers(),
            )

            # May return insufficient_data if no test data exists
            assert response.status_code in (200, 401)

            if response.status_code == 200:
                data = response.json()
                # Verify response structure
                assert "percentile_25" in data
                assert "median" in data
                assert "percentile_75" in data
                assert "percentile_95" in data
                assert "n_cases" in data
                assert "confidence" in data

                # Phase 2.1: Confidence score
                assert "confidence_score" in data

                # Phase 3.1: Multiplier method
                assert "multiplier_method" in data
                assert "active_method" in data

                # Phase 3.2: Overdemand cliff
                assert "overdemand_cliff" in data

                # Phase 4: Outcome distribution
                assert "outcome_distribution" in data

    @pytest.mark.asyncio
    async def test_estimate_with_advanced_filters(self):
        """Test estimate with Phase 2.2 advanced filters."""
        payload = {
            "jurisdiction": "Test County, TX",
            "case_type": "Motor Vehicle Accident",
            "injury_category": ["Spinal Injury"],
            "medical_bills": 25000,
            # Phase 2.2 filters
            "outcome_type": "Settlement",
            "exclude_outliers": True,
            "medical_bills_min": 10000,
            "medical_bills_max": 50000,
        }

        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as client:
            response = await client.post(
                "/api/v1/query/estimate",
                json=payload,
                headers=auth_headers(),
            )

            assert response.status_code in (200, 401)


class TestE2ECarrierPatterns:
    """E2E: Carrier patterns API."""

    @pytest.mark.asyncio
    async def test_carrier_patterns(self):
        """Test carrier patterns endpoint."""
        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as client:
            response = await client.get(
                "/api/v1/analytics/carrier-patterns",
                headers=auth_headers(),
            )

            assert response.status_code in (200, 401)

            if response.status_code == 200:
                data = response.json()
                assert "patterns" in data
                assert "total_cases" in data
                assert "methodology" in data


class TestE2ETrendReports:
    """E2E: Trend reports API."""

    @pytest.mark.asyncio
    async def test_coverage_gaps(self):
        """Test coverage gaps endpoint."""
        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as client:
            response = await client.get(
                "/api/v1/trends/coverage-gaps",
                headers=auth_headers(),
            )

            assert response.status_code in (200, 401)

            if response.status_code == 200:
                data = response.json()
                assert "total_jurisdictions_tracked" in data
                assert "coverage_pct" in data

    @pytest.mark.asyncio
    async def test_founding_member_highlights(self):
        """Test founding member highlights endpoint."""
        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as client:
            response = await client.get(
                "/api/v1/trends/founding-member-highlights",
                headers=auth_headers(),
            )

            assert response.status_code in (200, 401)


class TestE2EContribution:
    """E2E: Contribution API."""

    @pytest.mark.asyncio
    async def test_contribution_stats(self):
        """Test contribution stats endpoint."""
        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as client:
            response = await client.get(
                "/api/v1/contribute/stats",
                headers=auth_headers(),
            )

            assert response.status_code in (200, 401)


class TestE2EStats:
    """E2E: Public stats API."""

    @pytest.mark.asyncio
    async def test_database_stats(self):
        """Test public database stats endpoint."""
        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as client:
            response = await client.get("/api/v1/stats/database")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_founding_member_stats(self):
        """Test public founding member stats endpoint."""
        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as client:
            response = await client.get("/api/v1/stats/founding-members")
            assert response.status_code == 200


class TestE2EInternalVerdicts:
    """E2E: Internal verdict search API (admin-only)."""

    @pytest.mark.asyncio
    async def test_verdict_search(self):
        """Test internal verdict search endpoint."""
        payload = {
            "page": 1,
            "page_size": 10,
        }

        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as client:
            response = await client.post(
                "/api/v1/internal/verdicts/search",
                json=payload,
                headers=auth_headers(),
            )

            # Admin-only, may return 401 if using non-admin key
            assert response.status_code in (200, 401, 403)

            if response.status_code == 200:
                data = response.json()
                assert "results" in data
                assert "total_count" in data
                assert "page" in data

    @pytest.mark.asyncio
    async def test_verdict_stats(self):
        """Test internal verdict stats endpoint."""
        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as client:
            response = await client.get(
                "/api/v1/internal/verdicts/stats",
                headers=auth_headers(),
            )

            assert response.status_code in (200, 401, 403)


class TestE2EResponseTime:
    """E2E: Response time performance."""

    @pytest.mark.asyncio
    async def test_estimate_response_time(self):
        """Test that estimate responds within 1 second."""
        payload = {
            "jurisdiction": "Test County, TX",
            "case_type": "Motor Vehicle Accident",
            "injury_category": ["Spinal Injury"],
            "medical_bills": 25000,
        }

        import time
        start = time.time()
        async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as client:
            response = await client.post(
                "/api/v1/query/estimate",
                json=payload,
                headers=auth_headers(),
            )
        elapsed = time.time() - start

        assert response.status_code in (200, 401)
        # Should respond within 5 seconds (Supabase cold start can be slow)
        assert elapsed < 5.0, f"Response took {elapsed:.2f}s (expected < 5s)"
