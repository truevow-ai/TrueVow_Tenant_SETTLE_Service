"""
DOCKET-Service Search Service
17-filter search engine for court docket cases.
"""

import time
import logging
from typing import List, Dict, Any, Optional
from datetime import date

from app.core.database import get_db
from app.models.docket import (
    DocketSearchFilter,
    DocketSearchResult,
    DocketSearchResponse,
    DocketStatsResponse,
    DocketCreateRequest,
    DocketUpdateRequest,
    DocketCase,
)

logger = logging.getLogger(__name__)


async def search_dockets(filters: DocketSearchFilter) -> DocketSearchResponse:
    """Execute a multi-filter search against the docket database."""
    start_time = time.time()
    db = await get_db()

    query = db.table("docket_cases").select("*", count="exact")

    # Soft-delete filter
    query = query.is_("deleted_at", None)

    # Apply filters
    if filters.court_id:
        query = query.eq("court_id", filters.court_id)
    if filters.case_number:
        query = query.ilike("case_number", f"%{filters.case_number}%")
    if filters.case_name:
        query = query.ilike("case_name", f"%{filters.case_name}%")
    if filters.case_type:
        query = query.eq("case_type", filters.case_type)
    if filters.status:
        query = query.eq("status", filters.status)
    if filters.judge_name:
        query = query.ilike("judge_name", f"%{filters.judge_name}%")
    if filters.plaintiff_attorney:
        query = query.ilike("plaintiff_attorney", f"%{filters.plaintiff_attorney}%")
    if filters.defense_attorney:
        query = query.ilike("defense_attorney", f"%{filters.defense_attorney}%")
    if filters.plaintiff_firm:
        query = query.ilike("plaintiff_firm", f"%{filters.plaintiff_firm}%")
    if filters.defense_firm:
        query = query.ilike("defense_firm", f"%{filters.defense_firm}%")
    if filters.filing_date_from:
        query = query.gte("filing_date", filters.filing_date_from.isoformat())
    if filters.filing_date_to:
        query = query.lte("filing_date", filters.filing_date_to.isoformat())
    if filters.damages_min is not None:
        query = query.gte("damages_awarded", filters.damages_min)
    if filters.damages_max is not None:
        query = query.lte("damages_awarded", filters.damages_max)
    if filters.source:
        query = query.eq("source", filters.source)

    # Sorting
    valid_sort = ["filing_date", "created_at", "damages_awarded", "settlement_amount", "case_name"]
    sort_field = filters.sort_by if filters.sort_by in valid_sort else "filing_date"
    query = query.order(sort_field, desc=(filters.sort_order == "desc"))

    # Pagination
    offset = (filters.page - 1) * filters.page_size
    query = query.limit(filters.page_size)

    result = await query.execute()

    response_time_ms = int((time.time() - start_time) * 1000)

    rows = result.data if result.data else []
    total_count = result.count if result.count is not None else len(rows)
    total_pages = (total_count + filters.page_size - 1) // filters.page_size

    search_results = [DocketSearchResult(**row) for row in rows]

    return DocketSearchResponse(
        results=search_results,
        total_count=total_count,
        page=filters.page,
        page_size=filters.page_size,
        total_pages=total_pages,
        has_next=filters.page < total_pages,
        has_prev=filters.page > 1,
        response_time_ms=response_time_ms,
    )


async def get_docket_stats() -> DocketStatsResponse:
    """Get aggregate docket statistics."""
    db = await get_db()

    # Total count
    total_result = await db.table("docket_cases").select("id", count="exact").is_("deleted_at", None).execute()
    total_count = total_result.count if total_result.count else 0

    # By case type
    ct_result = await db.table("docket_cases").select("case_type").is_("deleted_at", None).execute()
    by_case_type = {}
    for row in ct_result.data or []:
        ct = row.get("case_type", "Unknown")
        by_case_type[ct] = by_case_type.get(ct, 0) + 1

    # By status
    status_result = await db.table("docket_cases").select("status").is_("deleted_at", None).execute()
    by_status = {}
    for row in status_result.data or []:
        s = row.get("status", "Unknown")
        by_status[s] = by_status.get(s, 0) + 1

    # By source
    source_result = await db.table("docket_cases").select("source").is_("deleted_at", None).execute()
    by_source = {}
    for row in source_result.data or []:
        s = row.get("source", "Unknown")
        by_source[s] = by_source.get(s, 0) + 1

    # By judge
    judge_result = await db.table("docket_cases").select("judge_name").is_("deleted_at", None).execute()
    by_judge = {}
    for row in judge_result.data or []:
        j = row.get("judge_name", "Unknown")
        if j:
            by_judge[j] = by_judge.get(j, 0) + 1

    # Averages
    numeric_result = await db.table("docket_cases").select("damages_awarded, settlement_amount").is_("deleted_at", None).execute()
    rows = numeric_result.data or []
    damages = [r.get("damages_awarded") for r in rows if r.get("damages_awarded")]
    settlements = [r.get("settlement_amount") for r in rows if r.get("settlement_amount")]

    avg_damages = sum(damages) / len(damages) if damages else None
    avg_settlements = sum(settlements) / len(settlements) if settlements else None

    # Date range
    date_min_result = await db.table("docket_cases").select("filing_date").is_("deleted_at", None).not_.is_("filing_date", None).order("filing_date", desc=False).limit(1).execute()
    date_max_result = await db.table("docket_cases").select("filing_date").is_("deleted_at", None).not_.is_("filing_date", None).order("filing_date", desc=True).limit(1).execute()

    min_date = date_min_result.data[0]["filing_date"] if date_min_result.data else None
    max_date = date_max_result.data[0]["filing_date"] if date_max_result.data else None

    return DocketStatsResponse(
        total_cases=total_count,
        by_case_type=by_case_type,
        by_status=by_status,
        by_source=by_source,
        by_judge=by_judge,
        avg_damages_awarded=round(avg_damages, 2) if avg_damages else None,
        avg_settlement_amount=round(avg_settlements, 2) if avg_settlements else None,
        date_range={"min": min_date, "max": max_date},
    )


async def get_docket_by_id(docket_id: str) -> Optional[DocketCase]:
    """Get a single docket case by ID."""
    db = await get_db()
    result = await db.table("docket_cases").select("*").eq("id", docket_id).execute()
    if result.data and len(result.data) > 0:
        return DocketCase(**result.data[0])
    return None


async def create_docket(data: DocketCreateRequest, source: str = "manual") -> DocketCase:
    """Create a new docket case."""
    db = await get_db()
    insert_data = data.model_dump(exclude_none=True)
    insert_data["source"] = source

    result = await db.table("docket_cases").insert(insert_data).execute()
    return DocketCase(**result.data[0])


async def update_docket(docket_id: str, data: DocketUpdateRequest) -> Optional[DocketCase]:
    """Update a docket case."""
    db = await get_db()
    update_data = data.model_dump(exclude_none=True)

    result = await db.table("docket_cases").update(update_data).eq("id", docket_id).execute()
    if result.data and len(result.data) > 0:
        return DocketCase(**result.data[0])
    return None


async def delete_docket(docket_id: str) -> bool:
    """Soft-delete a docket case."""
    db = await get_db()
    from datetime import datetime, UTC
    update_data = {"deleted_at": datetime.now(UTC).isoformat()}

    result = await db.table("docket_cases").update(update_data).eq("id", docket_id).execute()
    return result.data is not None and len(result.data) > 0
