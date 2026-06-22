"""
Trend Studies / Market Reports API — Phase 2.5

Quarterly "State of Settlement" reports, coverage gap analysis,
and Founding Member highlights. Public (authenticated) endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import require_any_auth
from app.services import trend_reports as trend_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["trend-reports"])


@router.get("/trends/{period}")
async def get_trend_report(
    period: str,
    auth=Depends(require_any_auth),
):
    """
    Get a quarterly trend report.

    Period format: "Q{quarter}-{year}" (e.g., "Q1-2026", "Q4-2025")
    """
    try:
        parts = period.upper().split("-")
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Period format: Q{quarter}-{year} (e.g., Q1-2026)")

        quarter_str = parts[0].replace("Q", "")
        year = int(parts[1])
        quarter = int(quarter_str)

        if quarter not in (1, 2, 3, 4):
            raise HTTPException(status_code=400, detail="Quarter must be 1-4")
        if year < 2020 or year > 2030:
            raise HTTPException(status_code=400, detail="Year must be between 2020 and 2030")

        result = await trend_service.trend_report_generator.generate_quarterly_report(year, quarter)
        return result.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trend report error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate trend report: {str(e)}")


@router.get("/coverage-gaps")
async def get_coverage_gaps(
    auth=Depends(require_any_auth),
):
    """
    Get jurisdiction coverage gap analysis.

    Shows which jurisdictions have adequate (n>=50), growing (n>=10),
    or thin (n<10) data coverage.
    """
    try:
        result = await trend_service.trend_report_generator.generate_coverage_gap_analysis()
        return result.model_dump()
    except Exception as e:
        logger.error(f"Coverage gap error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate coverage analysis: {str(e)}")


@router.get("/founding-member-highlights")
async def get_founding_member_highlights(
    auth=Depends(require_any_auth),
):
    """
    Get Founding Member contribution highlights.

    Shows total members, active contributors, top contributors,
    and milestone achievements.
    """
    try:
        result = await trend_service.trend_report_generator.generate_founding_member_highlights()
        return result.model_dump()
    except Exception as e:
        logger.error(f"Founding member highlights error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate highlights: {str(e)}")
