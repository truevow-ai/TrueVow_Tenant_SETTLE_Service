"""
Unit tests for Settlement Estimator Service
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock, AsyncMock

from app.services.estimator import SettlementEstimator
from app.services.intelligence_gate import AggregateGateResult, MIN_AGGREGATE_N
from app.models.case_bank import EstimateRequest, SettleContribution


def _sufficient_gate(n: int = 120) -> MagicMock:
    """Stub IntelligenceGate that always returns sufficient — lets the
    percentile branch run against the estimator's mock cases."""
    stub = MagicMock()
    stub.check = AsyncMock(return_value=AggregateGateResult(
        status="sufficient",
        n=n,
        threshold=MIN_AGGREGATE_N,
        own_case_only=False,
        suppressed_features=[],
    ))
    return stub


@pytest.mark.asyncio
async def test_estimator_with_sufficient_cases():
    """Test estimator with >=15 cases (percentile calculation)"""

    estimator = SettlementEstimator(gate=_sufficient_gate())

    request = EstimateRequest(
        jurisdiction="Maricopa County, AZ",
        case_type="Auto Accident",
        injury_category=["Spinal Injury", "Back Injury"],
        medical_bills=50000.00
    )

    response = await estimator.estimate_settlement_range(request)

    # Assertions
    assert response.n_cases >= 15, "Should have at least 15 cases"
    assert response.confidence in ["medium", "high"]
    assert response.percentile_25 < response.median < response.percentile_75 < response.percentile_95
    assert response.response_time_ms < 1000, "Should respond in <1 second"
    assert len(response.comparable_cases) > 0


@pytest.mark.asyncio
async def test_estimator_with_insufficient_cases():
    """Test estimator with <15 cases (multiplier fallback)"""
    
    estimator = SettlementEstimator()
    
    # Mock query that returns few cases
    # In production, this would query a jurisdiction with limited data
    
    request = EstimateRequest(
        jurisdiction="Test County, WY",  # Small state
        case_type="Rare Case Type",
        injury_category=["Rare Injury Type"],
        medical_bills=25000.00
    )
    
    # For this test, we'd mock the database to return <15 cases
    # Response should use multiplier fallback
    # confidence should be "low"


@pytest.mark.asyncio
async def test_bucket_to_midpoint():
    """Test outcome range bucket to midpoint conversion"""
    
    estimator = SettlementEstimator()
    
    assert estimator._bucket_to_midpoint("$50k-$100k") == 75000
    assert estimator._bucket_to_midpoint("$300k-$600k") == 450000
    assert estimator._bucket_to_midpoint("$1M+") == 1500000


@pytest.mark.asyncio
async def test_response_time():
    """Test that estimator responds within 1 second"""

    estimator = SettlementEstimator(gate=_sufficient_gate())

    request = EstimateRequest(
        jurisdiction="Maricopa County, AZ",
        case_type="Auto Accident",
        injury_category=["Spinal Injury"],
        medical_bills=50000.00
    )
    
    start_time = datetime.now(UTC)
    response = await estimator.estimate_settlement_range(request)
    elapsed_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
    
    assert elapsed_ms < 1000, f"Response took {elapsed_ms}ms, should be <1000ms"
    assert response.response_time_ms < 1000
