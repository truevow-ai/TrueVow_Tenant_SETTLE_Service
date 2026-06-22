"""
Carrier Pattern Analytics API — Phase 2.3

Descriptive statistics about defendant/insurance carrier settlement patterns.
Public endpoint (authenticated). Bar-compliant framing.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import require_any_auth
from app.services import carrier_patterns as carrier_service
from app.services.carrier_patterns import CarrierPatternsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/carrier-patterns", response_model=CarrierPatternsResponse)
async def get_carrier_patterns(
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction (e.g., 'Maricopa County, AZ')"),
    case_type: Optional[str] = Query(None, description="Filter by case type"),
    injury_category: Optional[List[str]] = Query(None, description="Filter by injury category (multi-select)"),
    defendant_category: Optional[str] = Query(None, description="Filter by defendant category"),
    min_case_count: int = Query(5, ge=1, le=50, description="Minimum cases per pattern"),
    auth=Depends(require_any_auth),
):
    """
    Get defendant/insurance carrier settlement patterns.

    Descriptive statistics only — not predictive. Shows which carrier
    categories settle faster, pay more, or go to trial more often.

    Bar compliance: Framed as "Historical data shows..." not recommendations.
    """
    try:
        result = await carrier_service.get_carrier_patterns(
            jurisdiction=jurisdiction,
            case_type=case_type,
            injury_category=injury_category,
            defendant_category=defendant_category,
            min_case_count=min_case_count,
        )
        return result
    except Exception as e:
        logger.error(f"Carrier patterns error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get carrier patterns: {str(e)}")
