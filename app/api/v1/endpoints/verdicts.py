"""
Internal Verdict Research API — Phase 1
17-filter search engine, internal dashboard, scraping pipeline connector.
Admin-only access. NOT customer-facing.
"""

import logging
from typing import Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.core.auth import require_admin
from app.core.database import get_db
from app.models.verdicts import (
    VerdictSearchFilter,
    VerdictSearchResponse,
    VerdictStatsResponse,
    VerdictCreateRequest,
    VerdictUpdateRequest,
    VerdictRecord,
    VerdictScrapeJobResponse,
    ScrapeJobCreateRequest,
    ScrapeJobListResponse,
)
from app.services import verdict_search as verdict_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verdicts", tags=["internal-verdicts"])


# ============================================================================
# 17-FILTER SEARCH
# ============================================================================

@router.post("/search", response_model=VerdictSearchResponse)
async def search_verdicts(
    filters: VerdictSearchFilter,
    admin=Depends(require_admin),
):
    """
    Internal 17-filter verdict search.

    All filters are optional and combinable with AND logic.
    Admin access required. NOT customer-facing.
    """
    try:
        result = await verdict_service.search_verdicts(filters)
        return result
    except Exception as e:
        logger.error(f"Verdict search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# ============================================================================
# DASHBOARD STATISTICS
# ============================================================================

@router.get("/stats", response_model=VerdictStatsResponse)
async def get_verdict_stats(
    admin=Depends(require_admin),
):
    """
    Get aggregate statistics for internal verdict dashboard.

    Admin access required. NOT customer-facing.
    """
    try:
        result = await verdict_service.get_verdict_stats()
        return result
    except Exception as e:
        logger.error(f"Verdict stats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Stats failed: {str(e)}")


# ============================================================================
# HEALTH CHECK  (declared BEFORE /{verdict_id} so the UUID route can't shadow it)
# ============================================================================

@router.get("/health")
async def verdict_health_check():
    """Internal verdict service health check."""
    try:
        db = await get_db()
        if db is None:
            return {
                "status": "degraded",
                "service": "internal-verdict-research",
                "message": "no database (mock mode or unconfigured)",
            }
        result = db.table("settle_verdicts").select("id", count="exact").limit(1).execute()
        return {
            "status": "healthy",
            "service": "internal-verdict-research",
            "total_records": result.count or 0,
        }
    except Exception as e:
        return {"status": "unhealthy", "service": "internal-verdict-research", "error": str(e)}


# ============================================================================
# CRUD OPERATIONS
# ============================================================================

@router.get("/{verdict_id}", response_model=VerdictRecord)
async def get_verdict(
    verdict_id: UUID,
    admin=Depends(require_admin),
):
    """Get a single verdict record by ID."""
    result = await verdict_service.get_verdict_by_id(verdict_id)
    if not result:
        raise HTTPException(status_code=404, detail="Verdict not found")
    return result


@router.post("/", response_model=VerdictRecord, status_code=201)
async def create_verdict(
    data: VerdictCreateRequest,
    admin=Depends(require_admin),
):
    """Manually create a verdict record."""
    result = await verdict_service.create_verdict(data)
    return result


@router.patch("/{verdict_id}", response_model=VerdictRecord)
async def update_verdict(
    verdict_id: UUID,
    data: VerdictUpdateRequest,
    admin=Depends(require_admin),
):
    """Update a verdict record."""
    result = await verdict_service.update_verdict(verdict_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Verdict not found")
    return result


@router.delete("/{verdict_id}", status_code=204)
async def delete_verdict(
    verdict_id: UUID,
    deleted_by: Optional[UUID] = Query(None),
    admin=Depends(require_admin),
):
    """Soft-delete a verdict record."""
    success = await verdict_service.delete_verdict(verdict_id, deleted_by)
    if not success:
        raise HTTPException(status_code=404, detail="Verdict not found")
    return JSONResponse(status_code=204, content=None)


# ============================================================================
# SCRAPING PIPELINE
# ============================================================================

@router.post("/scrape/bulk-insert")
async def bulk_insert_verdicts(
    records: list[dict],
    admin=Depends(require_admin),
):
    """
    Bulk insert verdict records from scraping pipeline.

    Returns counts: inserted, skipped (duplicates), failed.
    """
    try:
        inserted, skipped, failed = await verdict_service.bulk_insert_verdicts(records)
        return {
            "inserted": inserted,
            "skipped": skipped,
            "failed": failed,
            "total_processed": inserted + skipped + failed,
        }
    except Exception as e:
        logger.error(f"Bulk insert error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Bulk insert failed: {str(e)}")


@router.post("/scrape/jobs", response_model=VerdictScrapeJobResponse)
async def create_scrape_job(
    data: ScrapeJobCreateRequest,
    admin=Depends(require_admin),
):
    """
    Register a new scraping job run.

    This creates a tracking record. The actual scraping is done
    by external scripts that call the bulk-insert endpoint.
    """
    try:
        insert_data = {
            "source": data.source,
            "status": "running",
            "source_config": data.source_config,
        }
        db = await get_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not configured (mock mode); scrape-job tracking unavailable")
        result = db.table("settle_verdict_scrape_jobs").insert(insert_data).execute()
        if not result.data:
            raise HTTPException(status_code=502, detail="Scrape job insert returned no data")
        return VerdictScrapeJobResponse(**result.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create scrape job error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create scrape job: {str(e)}")


@router.patch("/scrape/jobs/{job_id}")
async def update_scrape_job(
    job_id: UUID,
    status: str = Query(..., description="running, completed, failed, partial"),
    records_found: Optional[int] = None,
    records_inserted: Optional[int] = None,
    records_skipped: Optional[int] = None,
    records_failed: Optional[int] = None,
    error_log: Optional[str] = None,
    admin=Depends(require_admin),
):
    """Update a scraping job status."""
    try:
        update_data = {"status": status}
        if records_found is not None:
            update_data["records_found"] = records_found
        if records_inserted is not None:
            update_data["records_inserted"] = records_inserted
        if records_skipped is not None:
            update_data["records_skipped"] = records_skipped
        if records_failed is not None:
            update_data["records_failed"] = records_failed
        if error_log is not None:
            update_data["error_log"] = error_log
        if status in ("completed", "failed", "partial"):
            update_data["completed_at"] = datetime.utcnow().isoformat()

        db = await get_db()
        if db is None:
            raise HTTPException(status_code=503, detail="Database not configured (mock mode); scrape-job tracking unavailable")
        result = db.table("settle_verdict_scrape_jobs").update(update_data).eq("id", str(job_id)).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Scrape job not found")
        return VerdictScrapeJobResponse(**result.data[0])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update scrape job error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update scrape job: {str(e)}")


@router.get("/scrape/jobs", response_model=ScrapeJobListResponse)
async def list_scrape_jobs(
    source: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    admin=Depends(require_admin),
):
    """List scraping jobs with optional filters."""
    try:
        db = await get_db()
        if db is None:
            return ScrapeJobListResponse(jobs=[], total=0)
        query = db.table("settle_verdict_scrape_jobs").select("*").order("started_at", desc=True).limit(limit)

        if source:
            query = query.eq("source", source)
        if status:
            query = query.eq("status", status)

        result = query.execute()
        jobs = [VerdictScrapeJobResponse(**row) for row in result.data or []]

        # Get total count
        count_query = db.table("settle_verdict_scrape_jobs").select("id", count="exact")
        if source:
            count_query = count_query.eq("source", source)
        if status:
            count_query = count_query.eq("status", status)
        count_result = count_query.execute()

        return ScrapeJobListResponse(jobs=jobs, total=count_result.count or 0)
    except Exception as e:
        logger.error(f"List scrape jobs error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list scrape jobs: {str(e)}")

