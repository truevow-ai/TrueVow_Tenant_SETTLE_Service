"""
Query Endpoints - Settlement Range Estimation
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class EstimateRequest(BaseModel):
    """Request model for settlement range estimation"""
    injury_type: str
    state: str
    county: str
    medical_bills: float
    treatment_type: Optional[list[str]] = None
    imaging: Optional[list[str]] = None
    policy_limits: Optional[str] = None


class EstimateResponse(BaseModel):
    """Response model for settlement range estimation"""
    percentile_25: float
    median: float
    percentile_75: float
    percentile_95: float
    n_cases: int
    confidence: str  # 'low', 'medium', 'high'
    comparable_cases: list[dict]


@router.post("/estimate")
async def estimate_settlement_range(
    request: EstimateRequest,
    # api_key: str = Depends(get_api_key)  # TODO: Implement auth
):
    """
    Estimate settlement range based on comparable cases.
    
    Returns statistical range (25th, median, 75th, 95th percentiles)
    based on historical settlement data.
    """
    # TODO: Implement estimator service
    # For now, return placeholder
    return EstimateResponse(
        percentile_25=150000,
        median=340000,
        percentile_75=520000,
        percentile_95=680000,
        n_cases=87,
        confidence="high",
        comparable_cases=[]
    )

