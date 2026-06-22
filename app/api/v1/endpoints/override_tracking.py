"""
Override Tracking API — Phase 3.3

Tracks estimate vs actual outcome deltas.
Admin-only endpoint for analytics.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import require_admin
from app.services import override_tracking as override_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/overrides", tags=["admin-overrides"])


@router.post("/record")
async def record_override(
    query_id: Optional[str] = Query(None),
    contribution_id: Optional[str] = Query(None),
    estimate_median: float = Query(...),
    actual_outcome: float = Query(...),
    jurisdiction: str = Query(...),
    case_type: str = Query(...),
    injury_category: str = Query(...),  # Comma-separated
    medical_bills: float = Query(...),
    admin=Depends(require_admin),
):
    """Record an estimate override."""
    try:
        from uuid import UUID as UUIDType
        qid = UUIDType(query_id) if query_id else None
        cid = UUIDType(contribution_id) if contribution_id else None
        injuries = [i.strip() for i in injury_category.split(",") if i.strip()]

        result = await override_service.override_tracking_service.record_override(
            query_id=qid,
            contribution_id=cid,
            estimate_median=estimate_median,
            actual_outcome=actual_outcome,
            jurisdiction=jurisdiction,
            case_type=case_type,
            injury_category=injuries,
            medical_bills=medical_bills,
        )
        return result.model_dump()
    except Exception as e:
        logger.error(f"Record override error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics")
async def get_override_analytics(
    jurisdiction: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    admin=Depends(require_admin),
):
    """Get aggregate override analytics."""
    try:
        result = await override_service.override_tracking_service.get_analytics(
            jurisdiction=jurisdiction,
            case_type=case_type,
        )
        return result.model_dump()
    except Exception as e:
        logger.error(f"Override analytics error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
