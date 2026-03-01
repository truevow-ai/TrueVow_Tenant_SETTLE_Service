"""
Stats Endpoints

Public statistics and metrics about the SETTLE service.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from app.core.config import settings
from app.core.database import get_db_with_retry

logger = logging.getLogger(__name__)

router = APIRouter()


class FoundingMemberStats(BaseModel):
    """Founding Member program statistics"""
    total_members: int
    active_members: int
    slots_remaining: int
    total_capacity: int
    total_contributions: int
    total_queries: int
    total_reports: int


class DatabaseStats(BaseModel):
    """Database statistics"""
    total_contributions: int
    approved_contributions: int
    pending_contributions: int
    flagged_contributions: int
    jurisdictions_covered: int
    states_covered: int


@router.get("/founding-members", response_model=FoundingMemberStats)
async def get_founding_member_stats():
    """
    Get Founding Member program statistics.
    
    Public endpoint - shows program capacity and status.
    """
    
    try:
        db = await get_db_with_retry()
        
        # Get capacity from config/database
        total_capacity = settings.FOUNDING_MEMBER_LIMIT
        
        if db is None:
            # Mock mode - return zeros
            logger.debug("Mock mode: returning zero stats")
            return FoundingMemberStats(
                total_members=0,
                active_members=0,
                slots_remaining=total_capacity,
                total_capacity=total_capacity,
                total_contributions=0,
                total_queries=0,
                total_reports=0
            )
        
        # Query founding members
        founding_members = db.table("settle_founding_members").select("id, status, contribution_count").execute()
        
        # Calculate stats from database
        total_members = len(founding_members.data) if founding_members.data else 0
        active_members = sum(1 for m in founding_members.data if m.get("status") == "active") if founding_members.data else 0
        total_contributions = sum(m.get("contribution_count", 0) for m in founding_members.data) if founding_members.data else 0
        
        # Query total queries
        queries = db.table("settle_queries").select("id").execute()
        total_queries = len(queries.data) if queries.data else 0
        
        # Query total reports
        reports = db.table("settle_reports").select("id").execute()
        total_reports = len(reports.data) if reports.data else 0
        
        logger.info(f"Founding member stats: {total_members} members, {total_contributions} contributions")
        
        return FoundingMemberStats(
            total_members=total_members,
            active_members=active_members,
            slots_remaining=total_capacity - total_members,
            total_capacity=total_capacity,
            total_contributions=total_contributions,
            total_queries=total_queries,
            total_reports=total_reports
        )
        
    except Exception as e:
        logger.error(f"Error getting founding member stats: {str(e)}", exc_info=True)
        # Return zeros on error rather than failing
        return FoundingMemberStats(
            total_members=0,
            active_members=0,
            slots_remaining=settings.FOUNDING_MEMBER_LIMIT,
            total_capacity=settings.FOUNDING_MEMBER_LIMIT,
            total_contributions=0,
            total_queries=0,
            total_reports=0
        )


@router.get("/database", response_model=DatabaseStats)
async def get_database_stats():
    """
    Get database statistics.
    
    Public endpoint - shows database size and coverage.
    """
    
    try:
        from app.core.database import get_db
        
        db = await get_db()
        
        if db:
            # Query contribution statistics
            total_result = db.table('settle_contributions').select('id', count='exact').execute()
            approved_result = db.table('settle_contributions').select('id', count='exact').eq('status', 'approved').execute()
            pending_result = db.table('settle_contributions').select('id', count='exact').eq('status', 'pending').execute()
            flagged_result = db.table('settle_contributions').select('id', count='exact').eq('status', 'flagged').execute()
            
            # Query distinct jurisdictions
            jurisdictions_result = db.table('settle_contributions') \
                .select('jurisdiction') \
                .eq('status', 'approved') \
                .execute()
            
            # Extract unique jurisdictions and states
            unique_jurisdictions = set()
            unique_states = set()
            
            if jurisdictions_result.data:
                for row in jurisdictions_result.data:
                    jurisdiction = row.get('jurisdiction', '')
                    if jurisdiction:
                        unique_jurisdictions.add(jurisdiction)
                        # Extract state from jurisdiction (e.g., "Los Angeles, CA" -> "CA")
                        parts = jurisdiction.split(',')
                        if len(parts) > 1:
                            state = parts[-1].strip()
                            unique_states.add(state)
            
            return DatabaseStats(
                total_contributions=total_result.count if hasattr(total_result, 'count') else 0,
                approved_contributions=approved_result.count if hasattr(approved_result, 'count') else 0,
                pending_contributions=pending_result.count if hasattr(pending_result, 'count') else 0,
                flagged_contributions=flagged_result.count if hasattr(flagged_result, 'count') else 0,
                jurisdictions_covered=len(unique_jurisdictions),
                states_covered=len(unique_states)
            )
        else:
            # Mock mode or database unavailable
            logger.warning("Database not available, returning mock stats")
            return DatabaseStats(
                total_contributions=0,
                approved_contributions=0,
                pending_contributions=0,
                flagged_contributions=0,
                jurisdictions_covered=0,
                states_covered=0
            )
        
    except Exception as e:
        logger.error(f"Error getting database stats: {str(e)}", exc_info=True)
        return DatabaseStats(
            total_contributions=0,
            approved_contributions=0,
            pending_contributions=0,
            flagged_contributions=0,
            jurisdictions_covered=0,
            states_covered=0
        )

