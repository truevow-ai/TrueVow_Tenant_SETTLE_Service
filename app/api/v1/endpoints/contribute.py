"""
Contribution Endpoints - Submit Settlement Data
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from uuid import UUID
import logging

from app.models.case_bank import ContributionRequest, ContributionResponse
from app.services.contributor import ContributionService
from app.core.database import get_db
from app.core.auth import require_any_auth

router = APIRouter()
logger = logging.getLogger(__name__)


def _safe_uuid(value: Optional[str]) -> Optional[UUID]:
    """Parse a UUID string, returning None for invalid/non-UUID values."""
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


@router.post("/submit", response_model=ContributionResponse)
async def submit_contribution(
    request: ContributionRequest,
    api_key_data: dict = Depends(require_any_auth),
):
    """
    Submit anonymous settlement data contribution.
    
    **Authentication:** Requires valid API key (any access level).
    
    **Workflow:**
    1. Validate data (completeness, correctness)
    2. Check anonymization (NO PHI/PII allowed)
    3. Run anomaly detection (statistical checks)
    4. Generate blockchain hash (OpenTimestamps)
    5. Store in database (status='pending' or 'flagged' based on anomaly)
    6. Track Founding Member stats (if applicable)
    7. Return confirmation with blockchain receipt
    
    **Compliance Requirements:**
    - ❌ NO client names, SSNs, DOBs, medical record numbers
    - ❌ NO free-text narratives (injury descriptions, fault assessments)
    - ❌ NO specific business names or case numbers
    - ✅ ONLY drop-down values, generic categories, bucketed amounts
    - ✅ Consent must be confirmed
    
    **Returns:**
    - Contribution ID and blockchain hash for verification
    - Founding Member stats (if applicable)
    """
    try:
        # Extract authenticated user info
        api_key_id = api_key_data.get("api_key_id")
        user_id = api_key_data.get("user_id")
        access_level = api_key_data.get("access_level", "")
        is_founding_member = access_level in ("founding_member", "admin")
        
        # Initialize contribution service with DB connection
        db = await get_db()
        contributor = ContributionService(db_connection=db)
        
        # Submit contribution
        success, response, error_msg = await contributor.submit_contribution(
            request=request,
            api_key_id=_safe_uuid(api_key_id),
            contributor_user_id=_safe_uuid(user_id),
            is_founding_member=is_founding_member,
        )
        
        if not success:
            logger.warning(f"Contribution submission failed: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail={"message": "Contribution validation failed", "error": error_msg}
            )
        
        logger.info(
            f"Contribution {response.contribution_id} submitted successfully. "
            f"Status: {response.status}, "
            f"Blockchain hash: {response.blockchain_hash}"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting contribution: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.get("/stats")
async def get_contribution_stats():
    """
    Get database contribution statistics.
    
    Public endpoint showing database size and growth.
    """
    try:
        db = await get_db()
        if not db:
            return {
                "total_contributions": 0,
                "approved_contributions": 0,
                "pending_review": 0,
                "founding_member_contributions": 0,
                "jurisdictions_covered": 0,
                "last_updated": None,
            }
        
        # Count by status
        total = db.table("settle_contributions").select("id", count="exact").execute()
        approved = db.table("settle_contributions").select("id", count="exact").eq("status", "approved").execute()
        pending = db.table("settle_contributions").select("id", count="exact").eq("status", "pending").execute()
        founding = db.table("settle_contributions").select("id", count="exact").eq("founding_member", True).execute()
        
        # Count distinct jurisdictions
        jurisdictions = db.table("settle_contributions").select("jurisdiction").eq("status", "approved").execute()
        unique_jurisdictions = len(set(row.get("jurisdiction", "") for row in (jurisdictions.data or [])))
        
        return {
            "total_contributions": total.count or 0,
            "approved_contributions": approved.count or 0,
            "pending_review": pending.count or 0,
            "founding_member_contributions": founding.count or 0,
            "jurisdictions_covered": unique_jurisdictions,
            "last_updated": None,
        }
    except Exception as e:
        logger.error(f"Error fetching contribution stats: {str(e)}", exc_info=True)
        return {
            "total_contributions": 0,
            "approved_contributions": 0,
            "pending_review": 0,
            "founding_member_contributions": 0,
            "jurisdictions_covered": 0,
            "last_updated": None,
        }


@router.get("/health")
async def contribute_service_health():
    """Health check for contribution service"""
    return {
        "service": "SETTLE Contribution Service",
        "status": "operational",
        "endpoints": ["/submit", "/stats"]
    }
