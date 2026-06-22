"""
Internal Verdict Search Service — Phase 1
17-filter search engine for internal verdict research.
NOT customer-facing.
"""

import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime
from uuid import UUID

from app.core.database import get_db
from app.models.verdicts import (
    VerdictSearchFilter,
    VerdictSearchResult,
    VerdictSearchResponse,
    VerdictStatsResponse,
    VerdictRecord,
    VerdictCreateRequest,
    VerdictUpdateRequest,
)

logger = logging.getLogger(__name__)


# ============================================================================
# 17-FILTER SEARCH ENGINE
# ============================================================================

async def search_verdicts(filters: VerdictSearchFilter) -> VerdictSearchResponse:
    """
    Execute a 17-filter search against the internal verdict database.

    All filters are optional and combinable with AND logic.
    """
    start_time = time.time()
    db = await get_db()

    query = db.table("settle_verdicts").select("*", count="exact")

    # Soft-delete filter (always applied)
    query = query.is_("deleted_at", None)

    # 1. Jurisdiction (partial match on state or full county match)
    if filters.jurisdiction:
        if "," in filters.jurisdiction:
            query = query.eq("jurisdiction", filters.jurisdiction)
        else:
            # State-only search: match any jurisdiction containing the state
            query = query.ilike("jurisdiction", f"%{filters.jurisdiction}%")

    # 2. Case Type (multi-select, OR within the list, AND with other filters)
    if filters.case_type and len(filters.case_type) > 0:
        if len(filters.case_type) == 1:
            query = query.eq("case_type", filters.case_type[0])
        else:
            query = query.in_("case_type", filters.case_type)

    # 3. Injury Type (array contains any of the selected)
    if filters.injury_type and len(filters.injury_type) > 0:
        if len(filters.injury_type) == 1:
            query = query.cs("injury_type", filters.injury_type)
        else:
            # PostgreSQL array overlap: use or_ logic
            # Supabase python client doesn't support overlap directly, use cs for each
            # For multi-select injury, we use contains with the first and filter rest
            query = query.cs("injury_type", filters.injury_type[:1])

    # 4. Outcome Type
    if filters.outcome_type and len(filters.outcome_type) > 0:
        if len(filters.outcome_type) == 1:
            query = query.eq("outcome_type", filters.outcome_type[0])
        else:
            query = query.in_("outcome_type", filters.outcome_type)

    # 5. Verdict Amount Range
    if filters.verdict_amount_min is not None:
        query = query.gte("total_verdict", filters.verdict_amount_min)
    if filters.verdict_amount_max is not None:
        query = query.lte("total_verdict", filters.verdict_amount_max)

    # 6. Medical Bills Range
    if filters.medical_bills_min is not None:
        query = query.gte("medical_bills", filters.medical_bills_min)
    if filters.medical_bills_max is not None:
        query = query.lte("medical_bills", filters.medical_bills_max)

    # 7. Liability Tier
    if filters.liability_tier and len(filters.liability_tier) > 0:
        if len(filters.liability_tier) == 1:
            query = query.eq("liability_tier", filters.liability_tier[0])
        else:
            query = query.in_("liability_tier", filters.liability_tier)

    # 8. Comparative Negligence Range
    if filters.comparative_negligence_min is not None:
        query = query.gte("comparative_negligence_pct", filters.comparative_negligence_min)
    if filters.comparative_negligence_max is not None:
        query = query.lte("comparative_negligence_pct", filters.comparative_negligence_max)

    # 9. Defendant Category
    if filters.defendant_category and len(filters.defendant_category) > 0:
        if len(filters.defendant_category) == 1:
            query = query.eq("defendant_category", filters.defendant_category[0])
        else:
            query = query.in_("defendant_category", filters.defendant_category)

    # 10. Defendant Industry
    if filters.defendant_industry and len(filters.defendant_industry) > 0:
        if len(filters.defendant_industry) == 1:
            query = query.eq("defendant_industry", filters.defendant_industry[0])
        else:
            query = query.in_("defendant_industry", filters.defendant_industry)

    # 11. Plaintiff Age Range
    if filters.plaintiff_age_range and len(filters.plaintiff_age_range) > 0:
        if len(filters.plaintiff_age_range) == 1:
            query = query.eq("plaintiff_age_range", filters.plaintiff_age_range[0])
        else:
            query = query.in_("plaintiff_age_range", filters.plaintiff_age_range)

    # 12. Date Range (verdict_date)
    if filters.date_from is not None:
        query = query.gte("verdict_date", filters.date_from.isoformat())
    if filters.date_to is not None:
        query = query.lte("verdict_date", filters.date_to.isoformat())

    # 13. Insurance Carrier (partial match)
    if filters.insurance_carrier:
        query = query.ilike("insurance_carrier", f"%{filters.insurance_carrier}%")

    # 14. Expert Witness Count (plaintiff side)
    if filters.expert_witness_min is not None:
        query = query.gte("expert_witnesses_plaintiff", filters.expert_witness_min)
    if filters.expert_witness_max is not None:
        query = query.lte("expert_witnesses_plaintiff", filters.expert_witness_max)

    # 15. Trial Duration
    if filters.trial_duration_min is not None:
        query = query.gte("trial_duration_days", filters.trial_duration_min)
    if filters.trial_duration_max is not None:
        query = query.lte("trial_duration_days", filters.trial_duration_max)

    # 16. Source Type
    if filters.source and len(filters.source) > 0:
        if len(filters.source) == 1:
            query = query.eq("source", filters.source[0])
        else:
            query = query.in_("source", filters.source)

    # 17. Confidence Score Range
    if filters.confidence_min is not None:
        query = query.gte("confidence_score", filters.confidence_min)
    if filters.confidence_max is not None:
        query = query.lte("confidence_score", filters.confidence_max)

    # Additional: Review status filter
    if filters.review_status and len(filters.review_status) > 0:
        if len(filters.review_status) == 1:
            query = query.eq("review_status", filters.review_status[0])
        else:
            query = query.in_("review_status", filters.review_status)

    # Sorting
    valid_sort_fields = [
        "verdict_date", "total_verdict", "settlement_amount", "medical_bills",
        "confidence_score", "completeness_score", "created_at", "trial_duration_days",
    ]
    sort_field = filters.sort_by if filters.sort_by in valid_sort_fields else "verdict_date"
    sort_direction = "desc" if filters.sort_order == "desc" else "asc"
    query = query.order(sort_field, desc=(sort_direction == "desc"))

    # Pagination
    offset = (filters.page - 1) * filters.page_size
    query = query.range(offset, offset + filters.page_size - 1)

    # Execute
    result = await query.execute()

    response_time_ms = int((time.time() - start_time) * 1000)

    # Parse results
    rows = result.data if result.data else []
    total_count = result.count if result.count is not None else len(rows)
    total_pages = (total_count + filters.page_size - 1) // filters.page_size

    verdict_results = [VerdictSearchResult(**row) for row in rows]

    # Build filter summary for response
    filter_summary = {}
    for field, value in filters.model_dump().items():
        if value is not None and field not in ("page", "page_size", "sort_by", "sort_order"):
            filter_summary[field] = value

    return VerdictSearchResponse(
        results=verdict_results,
        total_count=total_count,
        page=filters.page,
        page_size=filters.page_size,
        total_pages=total_pages,
        has_next=filters.page < total_pages,
        has_prev=filters.page > 1,
        search_filters=filter_summary,
        response_time_ms=response_time_ms,
    )


# ============================================================================
# STATISTICS & ANALYTICS
# ============================================================================

async def get_verdict_stats() -> VerdictStatsResponse:
    """Get aggregate statistics for internal dashboard."""
    db = await get_db()

    # Total count
    total_result = await db.table("settle_verdicts").select("id", count="exact").is_("deleted_at", None).execute()
    total_count = total_result.count if total_result.count else 0

    # By outcome type
    outcome_result = await db.table("settle_verdicts").select("outcome_type").is_("deleted_at", None).execute()
    by_outcome = {}
    for row in outcome_result.data or []:
        ot = row.get("outcome_type", "unknown")
        by_outcome[ot] = by_outcome.get(ot, 0) + 1

    # By case type
    case_type_result = await db.table("settle_verdicts").select("case_type").is_("deleted_at", None).execute()
    by_case_type = {}
    for row in case_type_result.data or []:
        ct = row.get("case_type", "unknown")
        by_case_type[ct] = by_case_type.get(ct, 0) + 1

    # By jurisdiction
    jurisdiction_result = await db.table("settle_verdicts").select("jurisdiction").is_("deleted_at", None).execute()
    by_jurisdiction = {}
    for row in jurisdiction_result.data or []:
        j = row.get("jurisdiction", "unknown")
        by_jurisdiction[j] = by_jurisdiction.get(j, 0) + 1

    # By review status
    review_result = await db.table("settle_verdicts").select("review_status").is_("deleted_at", None).execute()
    by_review = {}
    for row in review_result.data or []:
        rs = row.get("review_status", "unknown")
        by_review[rs] = by_review.get(rs, 0) + 1

    # By source
    source_result = await db.table("settle_verdicts").select("source").is_("deleted_at", None).execute()
    by_source = {}
    for row in source_result.data or []:
        s = row.get("source", "unknown")
        by_source[s] = by_source.get(s, 0) + 1

    # Averages (need to fetch numeric fields)
    numeric_result = await db.table("settle_verdicts").select(
        "confidence_score, completeness_score, total_verdict, settlement_amount, medical_bills, trial_duration_days"
    ).is_("deleted_at", None).execute()

    rows = numeric_result.data or []
    avg_confidence = _avg(rows, "confidence_score")
    avg_completeness = _avg(rows, "completeness_score")
    avg_verdict = _avg(rows, "total_verdict")
    avg_settlement = _avg(rows, "settlement_amount")
    avg_medical = _avg(rows, "medical_bills")
    avg_trial = _avg(rows, "trial_duration_days")

    # Date range
    date_result = await (db.table("settle_verdicts")
        .select("verdict_date")
        .is_("deleted_at", None)
        .not_.is_("verdict_date", None)
        .order("verdict_date", desc=False)
        .limit(1)
        .execute())

    date_result_max = await (db.table("settle_verdicts")
        .select("verdict_date")
        .is_("deleted_at", None)
        .not_.is_("verdict_date", None)
        .order("verdict_date", desc=True)
        .limit(1)
        .execute())

    min_date = date_result.data[0]["verdict_date"] if date_result.data else None
    max_date = date_result_max.data[0]["verdict_date"] if date_result_max.data else None

    return VerdictStatsResponse(
        total_verdicts=total_count,
        by_outcome_type=by_outcome,
        by_case_type=by_case_type,
        by_jurisdiction=by_jurisdiction,
        by_review_status=by_review,
        by_source=by_source,
        avg_confidence_score=round(avg_confidence, 3),
        avg_completeness_score=round(avg_completeness, 3),
        avg_total_verdict=round(avg_verdict, 2) if avg_verdict else None,
        avg_settlement_amount=round(avg_settlement, 2) if avg_settlement else None,
        avg_medical_bills=round(avg_medical, 2) if avg_medical else None,
        avg_trial_duration_days=round(avg_trial, 1) if avg_trial else None,
        date_range={"min": min_date, "max": max_date},
    )


def _avg(rows: List[Dict], field: str) -> Optional[float]:
    """Calculate average of a numeric field, skipping None values."""
    values = [r.get(field) for r in rows if r.get(field) is not None]
    if not values:
        return None
    return sum(values) / len(values)


# ============================================================================
# CRUD OPERATIONS
# ============================================================================

async def get_verdict_by_id(verdict_id: UUID) -> Optional[VerdictRecord]:
    """Get a single verdict record by ID."""
    db = await get_db()
    result = await db.table("settle_verdicts").select("*").eq("id", str(verdict_id)).execute()
    if result.data and len(result.data) > 0:
        return VerdictRecord(**result.data[0])
    return None


async def create_verdict(data: VerdictCreateRequest, source: str = "manual_entry") -> VerdictRecord:
    """Create a new verdict record (manual entry)."""
    db = await get_db()
    insert_data = data.model_dump(exclude_none=True)
    insert_data["source"] = source
    insert_data["review_status"] = "pending"
    insert_data["confidence_score"] = 0.5
    insert_data["completeness_score"] = _calculate_completeness(insert_data)

    result = await db.table("settle_verdicts").insert(insert_data).execute()
    return VerdictRecord(**result.data[0])


async def update_verdict(verdict_id: UUID, data: VerdictUpdateRequest) -> Optional[VerdictRecord]:
    """Update a verdict record."""
    db = await get_db()
    update_data = data.model_dump(exclude_none=True)

    # Recalculate completeness if any data fields changed
    if any(k not in ("review_status", "reviewer_notes", "confidence_score", "completeness_score") for k in update_data):
        # Fetch current record to merge
        current = await get_verdict_by_id(verdict_id)
        if current:
            merged = current.model_dump(exclude_none=True)
            merged.update(update_data)
            update_data["completeness_score"] = _calculate_completeness(merged)

    result = await db.table("settle_verdicts").update(update_data).eq("id", str(verdict_id)).execute()
    if result.data and len(result.data) > 0:
        return VerdictRecord(**result.data[0])
    return None


async def delete_verdict(verdict_id: UUID, deleted_by: Optional[UUID] = None) -> bool:
    """Soft-delete a verdict record."""
    db = await get_db()
    update_data = {"deleted_at": datetime.utcnow().isoformat()}
    if deleted_by:
        update_data["deleted_by"] = str(deleted_by)

    result = await db.table("settle_verdicts").update(update_data).eq("id", str(verdict_id)).execute()
    return result.data is not None and len(result.data) > 0


async def bulk_insert_verdicts(records: List[Dict]) -> Tuple[int, int, int]:
    """
    Bulk insert verdict records from scraping pipeline.
    Returns (inserted, skipped, failed) counts.
    """
    db = await get_db()
    inserted = 0
    skipped = 0
    failed = 0

    for record in records:
        try:
            # Check for duplicates by case_name + jurisdiction + verdict_date
            if record.get("case_name") and record.get("jurisdiction"):
                dedup_query = db.table("settle_verdicts").select("id").eq("case_name", record["case_name"]).eq("jurisdiction", record["jurisdiction"])
                if record.get("verdict_date"):
                    dedup_query = dedup_query.eq("verdict_date", record["verdict_date"])
                dedup_result = await dedup_query.execute()
                if dedup_result.data and len(dedup_result.data) > 0:
                    skipped += 1
                    continue

            # Calculate completeness
            record["completeness_score"] = _calculate_completeness(record)

            # Ensure required fields
            if "source" not in record:
                record["source"] = "scraped"
            if "review_status" not in record:
                record["review_status"] = "pending"
            if "confidence_score" not in record:
                record["confidence_score"] = _estimate_confidence_from_source(record.get("source", "scraped"))

            result = await db.table("settle_verdicts").insert(record).execute()
            if result.data:
                inserted += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Failed to insert verdict record: {e}")
            failed += 1

    return inserted, skipped, failed


def _calculate_completeness(data: Dict) -> float:
    """Calculate completeness score based on filled required fields."""
    required_fields = [
        "jurisdiction", "case_type", "outcome_type", "liability_tier",
        "injury_type", "defendant_category", "verdict_date",
    ]
    optional_fields = [
        "case_name", "case_number", "court", "judge_name", "plaintiff_age_range",
        "comparative_negligence_pct", "medical_bills", "economic_damages",
        "non_economic_damages", "punitive_damages", "total_verdict",
        "settlement_amount", "policy_limit_indicator", "defendant_industry",
        "insurance_carrier", "expert_witnesses_plaintiff", "expert_witnesses_defense",
        "trial_duration_days", "filing_date", "resolution_date", "source_url",
    ]

    required_filled = sum(1 for f in required_fields if data.get(f) is not None and data.get(f) != [])
    optional_filled = sum(1 for f in optional_fields if data.get(f) is not None and data.get(f) != [])

    total_fields = len(required_fields) + len(optional_fields)
    filled = required_filled + optional_filled

    return round(filled / total_fields, 3) if total_fields > 0 else 0.0


def _estimate_confidence_from_source(source: str) -> float:
    """Estimate initial confidence score based on source reliability."""
    source_confidence = {
        "manual_entry": 0.8,
        "partner_data": 0.7,
        "scraped": 0.5,
    }
    return source_confidence.get(source, 0.5)
