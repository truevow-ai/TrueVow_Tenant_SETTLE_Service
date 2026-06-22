"""
DOCKET-Service API Endpoints
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.docket import (
    DocketSearchFilter,
    DocketSearchResponse,
    DocketStatsResponse,
    DocketCase,
    DocketCreateRequest,
    DocketUpdateRequest,
)
from app.services import docket_search as docket_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# SEARCH
# ============================================================================

@router.post("/search", response_model=DocketSearchResponse)
async def search_dockets(filters: DocketSearchFilter):
    """Multi-filter docket search."""
    try:
        result = await docket_service.search_dockets(filters)
        return result
    except Exception as e:
        logger.error(f"Docket search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STATS
# ============================================================================

@router.get("/stats", response_model=DocketStatsResponse)
async def get_docket_stats():
    """Get aggregate docket statistics."""
    try:
        result = await docket_service.get_docket_stats()
        return result
    except Exception as e:
        logger.error(f"Docket stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CRUD
# ============================================================================

@router.get("/{docket_id}", response_model=DocketCase)
async def get_docket(docket_id: str):
    """Get a single docket case."""
    result = await docket_service.get_docket_by_id(docket_id)
    if not result:
        raise HTTPException(status_code=404, detail="Docket not found")
    return result


@router.post("/", response_model=DocketCase, status_code=201)
async def create_docket(data: DocketCreateRequest):
    """Create a new docket case."""
    result = await docket_service.create_docket(data)
    return result


@router.patch("/{docket_id}", response_model=DocketCase)
async def update_docket(docket_id: str, data: DocketUpdateRequest):
    """Update a docket case."""
    result = await docket_service.update_docket(docket_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Docket not found")
    return result


@router.delete("/{docket_id}", status_code=204)
async def delete_docket(docket_id: str):
    """Soft-delete a docket case."""
    success = await docket_service.delete_docket(docket_id)
    if not success:
        raise HTTPException(status_code=404, detail="Docket not found")
    return None
