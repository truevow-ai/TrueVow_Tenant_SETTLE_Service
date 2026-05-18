"""
Admin Endpoints - SaaS Admin Management Interface

These endpoints are called by the SaaS Admin platform to manage:
- Contribution approvals/rejections
- Founding Member management
- API key management
- Analytics and reporting
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict
from uuid import UUID, uuid4
from datetime import datetime, timedelta, UTC
import logging

from app.models.case_bank import ContributionResponse
from app.models.api_keys import FoundingMember, APIKeyResponse
from app.services.contributor import ContributionService
from app.core.auth import require_admin
from app.core.database import get_db
from app.core.security import generate_api_key, hash_api_key

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# CONTRIBUTION MANAGEMENT
# ============================================================================

@router.get("/contributions/pending")
async def get_pending_contributions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Get contributions pending admin review.
    
    **SaaS Admin Use Case:**
    - Display pending contributions in admin dashboard
    - Review for PII violations
    - Review for outliers
    
    **Returns:**
    - List of pending contributions with full details
    - Total count for pagination
    """
    try:
        logger.info(f"Admin {admin_data['user_id']} fetching pending contributions")
        
        # Get database connection
        db = await get_db()
        
        if db:
            # Query pending contributions
            result = db.table('settle_contributions') \
                .select('*') \
                .eq('status', 'pending') \
                .order('created_at', desc=True) \
                .range(offset, offset + limit - 1) \
                .execute()
            
            # Get total count
            count_result = db.table('settle_contributions') \
                .select('id', count='exact') \
                .eq('status', 'pending') \
                .execute()
            
            total = count_result.count if hasattr(count_result, 'count') else 0
            
            logger.info(f"Found {total} pending contributions")
            
            return {
                "contributions": result.data if result.data else [],
                "total": total,
                "limit": limit,
                "offset": offset
            }
        else:
            # Mock mode or database unavailable
            logger.warning("Database not available, returning mock data")
            return {
                "contributions": [],
                "total": 0,
                "limit": limit,
                "offset": offset
            }
    except Exception as e:
        logger.error(f"Error fetching pending contributions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.get("/contributions/{contribution_id}")
async def get_contribution_details(
    contribution_id: UUID,
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Get detailed information about a specific contribution.
    
    **SaaS Admin Use Case:**
    - Review contribution details before approval/rejection
    - Check anonymization status
    - View blockchain hash
    """
    try:
        logger.info(f"Admin {admin_data['user_id']} fetching contribution {contribution_id}")
        
        # Get database connection
        db = await get_db()
        
        if db:
            result = db.table('settle_contributions') \
                .select('*') \
                .eq('id', str(contribution_id)) \
                .execute()
            
            if not result.data or len(result.data) == 0:
                raise HTTPException(
                    status_code=404,
                    detail={"message": "Contribution not found", "contribution_id": str(contribution_id)}
                )
            
            return result.data[0]
        else:
            # Mock mode
            logger.warning("Database not available, returning 404")
            raise HTTPException(
                status_code=404,
                detail={"message": "Contribution not found (database unavailable)", "contribution_id": str(contribution_id)}
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching contribution {contribution_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.post("/contributions/{contribution_id}/approve")
async def approve_contribution(
    contribution_id: UUID,
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Approve a contribution for inclusion in database.
    
    **SaaS Admin Use Case:**
    - Admin reviews contribution and approves it
    - Contribution status changes from 'pending' to 'approved'
    - Contribution becomes available for queries
    - Contributor reputation is updated
    
    **Workflow:**
    1. Verify contribution is valid (no PII, correct format)
    2. Update status to 'approved'
    3. Log approval action in audit trail
    4. Update contributor reputation score
    5. If Founding Member: Update their contribution count
    """
    try:
        logger.info(f"Admin {admin_data['user_id']} approving contribution {contribution_id}")
        
        # Get database connection
        db = await get_db()
        
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Get contributor_user_id before updating
        existing = db.table('settle_contributions') \
            .select('contributor_user_id') \
            .eq('id', str(contribution_id)) \
            .execute()
        
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(
                status_code=404,
                detail={"message": "Contribution not found", "contribution_id": str(contribution_id)}
            )
        
        contributor_user_id = existing.data[0].get('contributor_user_id')
        
        # Use ContributionService to approve (wires in reputation update)
        service = ContributionService(db_connection=db)
        success, error = await service.approve_contribution(
            contribution_id=contribution_id,
            approved_by=admin_data['user_id'],
            contributor_user_id=UUID(contributor_user_id) if contributor_user_id else None,
        )
        
        if not success:
            raise HTTPException(status_code=404, detail=error)
        
        logger.info(f"Contribution {contribution_id} approved by admin {admin_data['user_id']}")
        
        return {
            "status": "approved",
            "contribution_id": str(contribution_id),
            "approved_at": datetime.now(UTC).isoformat(),
            "message": "Contribution approved successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving contribution {contribution_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.post("/contributions/{contribution_id}/reject")
async def reject_contribution(
    contribution_id: UUID,
    reason: str = Query(..., description="Reason for rejection"),
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Reject a contribution (PII detected, invalid data, etc.).
    
    **SaaS Admin Use Case:**
    - Admin detects PII in contribution
    - Admin flags invalid data or outliers
    - Contribution status changes to 'rejected'
    - Contributor reputation is updated
    - Attorney is notified (via SaaS Admin)
    
    **Common Rejection Reasons:**
    - "PII detected: Contains client name or identifying information"
    - "Outlier: Settlement amount exceeds 50× medical bills"
    - "Invalid data: Missing required fields"
    - "Antitrust violation: Contains defendant-specific information"
    """
    try:
        logger.warning(f"Admin {admin_data['user_id']} rejecting contribution {contribution_id}: {reason}")
        
        # Get database connection
        db = await get_db()
        
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Get contributor_user_id before updating
        existing = db.table('settle_contributions') \
            .select('contributor_user_id') \
            .eq('id', str(contribution_id)) \
            .execute()
        
        if not existing.data or len(existing.data) == 0:
            raise HTTPException(
                status_code=404,
                detail={"message": "Contribution not found", "contribution_id": str(contribution_id)}
            )
        
        contributor_user_id = existing.data[0].get('contributor_user_id')
        
        # Use ContributionService to reject (wires in reputation update)
        service = ContributionService(db_connection=db)
        success, error = await service.reject_contribution(
            contribution_id=contribution_id,
            rejection_reason=reason,
            rejected_by=admin_data['user_id'],
            contributor_user_id=UUID(contributor_user_id) if contributor_user_id else None,
        )
        
        if not success:
            raise HTTPException(status_code=404, detail=error)
        
        logger.warning(f"Contribution {contribution_id} rejected by admin {admin_data['user_id']}: {reason}")
        
        return {
            "status": "rejected",
            "contribution_id": str(contribution_id),
            "reason": reason,
            "rejected_at": datetime.now(UTC).isoformat(),
            "message": "Contribution rejected successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting contribution {contribution_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


# ============================================================================
# FOUNDING MEMBER MANAGEMENT
# ============================================================================

@router.get("/founding-members")
async def get_founding_members(
    status: Optional[str] = Query(None, description="Filter by status: active, inactive, suspended"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Get all Founding Members with contribution statistics.
    
    **SaaS Admin Use Case:**
    - View all Founding Members
    - Track monthly contributions (1-3/month requirement)
    - Monitor compliance with contribution requirements
    
    **Returns:**
    - List of Founding Members with contribution stats
    - Total count
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        query = db.table("settle_founding_members").select("*")
        if status:
            query = query.eq("status", status)
        
        count_result = db.table("settle_founding_members").select("id", count="exact")
        if status:
            count_result = count_result.eq("status", status)
        count_result = count_result.execute()
        total = count_result.count if hasattr(count_result, "count") else 0
        
        result = query.order("joined_at", desc=True).range(offset, offset + limit - 1).execute()
        
        members = result.data or []
        
        return {
            "members": members,
            "total": total,
            "limit": limit,
            "offset": offset,
            "max_members": 2100,
            "slots_remaining": 2100 - total,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching founding members: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.get("/founding-members/{member_id}")
async def get_founding_member_details(
    member_id: UUID,
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Get detailed information about a specific Founding Member.
    
    **SaaS Admin Use Case:**
    - View member's contribution history
    - Check monthly contribution compliance
    - View member status and enrollment date
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        member_result = db.table("settle_founding_members") \
            .select("*") \
            .eq("id", str(member_id)) \
            .execute()
        
        if not member_result.data:
            raise HTTPException(status_code=404, detail="Founding Member not found")
        
        member = member_result.data[0]
        
        # Get contribution count for this member
        contrib_result = db.table("settle_contributions") \
            .select("id", count="exact") \
            .eq("contributor_user_id", member.get("tenant_id")) \
            .execute()
        contrib_count = contrib_result.count if hasattr(contrib_result, "count") else 0
        
        # Get recent contributions
        recent = db.table("settle_contributions") \
            .select("id, jurisdiction, case_type, status, created_at") \
            .eq("contributor_user_id", member.get("tenant_id")) \
            .order("created_at", desc=True) \
            .limit(10) \
            .execute()
        
        return {
            **member,
            "contribution_count": contrib_count,
            "recent_contributions": recent.data or [],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching founding member {member_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.post("/founding-members/{member_id}/status")
async def update_founding_member_status(
    member_id: UUID,
    status: str = Query(..., description="New status: active, inactive, suspended"),
    reason: Optional[str] = Query(None, description="Reason for status change"),
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Update Founding Member status.
    
    **SaaS Admin Use Case:**
    - Suspend member for non-compliance (not meeting 1-3/month requirement)
    - Reactivate member after compliance restored
    - Deactivate member (if they request removal)
    
    **Status Values:**
    - `active`: Member is active and compliant
    - `inactive`: Member is inactive (voluntary or removed)
    - `suspended`: Member is suspended for non-compliance
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        if status not in ("active", "inactive", "suspended"):
            raise HTTPException(status_code=400, detail="Invalid status value")
        
        result = db.table("settle_founding_members") \
            .update({
                "status": status,
                "updated_at": datetime.now(UTC).isoformat(),
                "status_change_reason": reason,
                "status_changed_by": admin_data.get("user_id", "admin"),
            }) \
            .eq("id", str(member_id)) \
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Founding Member not found")
        
        logger.info(f"Founding Member {member_id} status updated to {status}")
        
        return {
            "member_id": str(member_id),
            "status": status,
            "updated_at": datetime.now(UTC).isoformat(),
            "reason": reason,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating founding member {member_id} status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.get("/founding-members/contributions")
async def get_founding_member_contributions(
    month: Optional[str] = Query(None, description="Month filter: YYYY-MM"),
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Get monthly contribution tracking for all Founding Members.
    
    **SaaS Admin Use Case:**
    - Track which members have met 1-3/month requirement
    - Identify members who need reminders
    - Generate compliance reports
    
    **Returns:**
    - List of members with monthly contribution counts
    - Compliance status (compliant, needs reminder, non-compliant)
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        target_month = month or datetime.now(UTC).strftime("%Y-%m")
        month_start = f"{target_month}-01T00:00:00+00:00"
        next_month = datetime.strptime(target_month, "%Y-%m")
        if next_month.month == 12:
            next_month = next_month.replace(year=next_month.year + 1, month=1)
        else:
            next_month = next_month.replace(month=next_month.month + 1)
        month_end = f"{next_month.strftime('%Y-%m')}-01T00:00:00+00:00"
        
        # Get all founding members
        members = db.table("settle_founding_members").select("id, tenant_id, firm_name, contact_email, status").execute()
        member_rows = members.data or []
        
        tracking = []
        for m in member_rows:
            contrib_count = db.table("settle_contributions") \
                .select("id", count="exact") \
                .eq("contributor_user_id", m.get("tenant_id")) \
                .eq("status", "approved") \
                .gte("created_at", month_start) \
                .lt("created_at", month_end) \
                .execute()
            count = contrib_count.count if hasattr(contrib_count, "count") else 0
            
            if count >= 1:
                compliance = "compliant"
            elif m.get("status") == "active":
                compliance = "needs_reminder"
            else:
                compliance = "non_compliant"
            
            tracking.append({
                "member_id": m["id"],
                "firm_name": m.get("firm_name"),
                "contact_email": m.get("contact_email"),
                "status": m.get("status"),
                "contributions_this_month": count,
                "compliance_status": compliance,
            })
        
        compliant = sum(1 for t in tracking if t["compliance_status"] == "compliant")
        needs_reminder = sum(1 for t in tracking if t["compliance_status"] == "needs_reminder")
        non_compliant = sum(1 for t in tracking if t["compliance_status"] == "non_compliant")
        
        return {
            "month": target_month,
            "members": tracking,
            "compliant_count": compliant,
            "needs_reminder_count": needs_reminder,
            "non_compliant_count": non_compliant,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching founding member contributions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


# ============================================================================
# API KEY MANAGEMENT
# ============================================================================

@router.post("/api-keys/create")
async def create_api_key_for_tenant(
    tenant_id: UUID = Query(..., description="Tenant ID from SaaS Admin"),
    access_level: str = Query("standard", description="Access level: founding_member, standard, premium, external"),
    name: Optional[str] = Query(None, description="Key name/description"),
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Create SETTLE API key for a tenant.
    
    **SaaS Admin Use Case:**
    - When tenant subscribes to SETTLE, create API key
    - Issue key to tenant for integration
    - Store key in SaaS Admin database (encrypted)
    
    **Returns:**
    - API key (one-time display, must be stored securely)
    - Key ID for future reference
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        if access_level not in ("founding_member", "standard", "premium", "external"):
            raise HTTPException(status_code=400, detail="Invalid access level")
        
        api_key, key_hash = generate_api_key()
        key_id = str(uuid4())
        
        db.table("settle_api_keys").insert({
            "id": key_id,
            "tenant_id": str(tenant_id),
            "api_key_hash": key_hash,
            "name": name or f"API Key for tenant {tenant_id}",
            "access_level": access_level,
            "status": "active",
            "is_active": True,
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": admin_data.get("user_id", "admin"),
        }).execute()
        
        logger.info(f"API key created for tenant {tenant_id} with access level {access_level}")
        
        return {
            "tenant_id": str(tenant_id),
            "api_key": f"settle_{api_key}",
            "key_id": key_id,
            "access_level": access_level,
            "created_at": datetime.now(UTC).isoformat(),
            "note": "Save this API key securely. It won't be shown again.",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating API key for tenant {tenant_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.get("/api-keys/{tenant_id}")
async def get_tenant_api_key(
    tenant_id: UUID,
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Get tenant's SETTLE API key (for SaaS Admin reference).
    
    **SaaS Admin Use Case:**
    - View tenant's API key (for support purposes)
    - Check key status and usage
    - Verify key exists before integration
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        result = db.table("settle_api_keys") \
            .select("id, tenant_id, name, access_level, status, is_active, created_at, last_used_at, requests_used, requests_limit") \
            .eq("tenant_id", str(tenant_id)) \
            .execute()
        
        keys = result.data or []
        
        if not keys:
            raise HTTPException(status_code=404, detail="No API keys found for tenant")
        
        return {
            "tenant_id": str(tenant_id),
            "keys": keys,
            "total": len(keys),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching API key for tenant {tenant_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.post("/api-keys/{key_id}/rotate")
async def rotate_api_key(
    key_id: UUID,
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Rotate (regenerate) an API key.
    
    **SaaS Admin Use Case:**
    - Security: Rotate compromised keys
    - Maintenance: Regular key rotation
    - Tenant request: Tenant requests new key
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Get existing key info
        existing = db.table("settle_api_keys") \
            .select("*") \
            .eq("id", str(key_id)) \
            .execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="API key not found")
        
        old_key = existing.data[0]
        
        # Generate new key
        api_key, key_hash = generate_api_key()
        
        # Deactivate old key
        db.table("settle_api_keys") \
            .update({"is_active": False, "status": "rotated"}) \
            .eq("id", str(key_id)) \
            .execute()
        
        # Create new key with same tenant/access_level
        new_key_id = str(uuid4())
        db.table("settle_api_keys").insert({
            "id": new_key_id,
            "tenant_id": old_key.get("tenant_id"),
            "api_key_hash": key_hash,
            "name": old_key.get("name", ""),
            "access_level": old_key.get("access_level", "standard"),
            "status": "active",
            "is_active": True,
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": admin_data.get("user_id", "admin"),
            "rotated_from": str(key_id),
        }).execute()
        
        logger.info(f"API key {key_id} rotated → {new_key_id}")
        
        return {
            "old_key_id": str(key_id),
            "new_key_id": new_key_id,
            "new_api_key": f"settle_{api_key}",
            "rotated_at": datetime.now(UTC).isoformat(),
            "note": "Save this API key securely. It won't be shown again.",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rotating API key {key_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: UUID,
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Revoke (delete) an API key.
    
    **SaaS Admin Use Case:**
    - Tenant cancels subscription
    - Security: Revoke compromised keys
    - Compliance: Revoke keys for violations
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        result = db.table("settle_api_keys") \
            .update({
                "is_active": False,
                "status": "revoked",
                "revoked_at": datetime.now(UTC).isoformat(),
                "revoked_by": admin_data.get("user_id", "admin"),
            }) \
            .eq("id", str(key_id)) \
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="API key not found")
        
        logger.warning(f"API key {key_id} revoked by admin {admin_data['user_id']}")
        
        return {
            "key_id": str(key_id),
            "status": "revoked",
            "revoked_at": datetime.now(UTC).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking API key {key_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


# ============================================================================
# ANALYTICS & REPORTING
# ============================================================================

@router.get("/analytics/dashboard")
async def get_analytics_dashboard(
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Get comprehensive analytics dashboard.
    
    **SaaS Admin Use Case:**
    - Display overview of SETTLE metrics
    - Show Founding Member progress
    - Track database growth
    - Monitor query/report volume
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Founding members
        fm_total = db.table("settle_founding_members").select("id", count="exact").execute()
        fm_active = db.table("settle_founding_members").select("id", count="exact").eq("status", "active").execute()
        fm_total_count = fm_total.count if hasattr(fm_total, "count") else 0
        fm_active_count = fm_active.count if hasattr(fm_active, "count") else 0
        
        # Contributions by status
        contrib_total = db.table("settle_contributions").select("id", count="exact").execute()
        contrib_approved = db.table("settle_contributions").select("id", count="exact").eq("status", "approved").execute()
        contrib_pending = db.table("settle_contributions").select("id", count="exact").eq("status", "pending").execute()
        contrib_flagged = db.table("settle_contributions").select("id", count="exact").eq("status", "flagged").execute()
        contrib_rejected = db.table("settle_contributions").select("id", count="exact").eq("status", "rejected").execute()
        
        # Jurisdictions
        jurisdictions = db.table("settle_contributions").select("jurisdiction").eq("status", "approved").execute()
        unique_jurisdictions = set()
        states = set()
        case_types = set()
        for row in (jurisdictions.data or []):
            j = row.get("jurisdiction", "")
            if j:
                unique_jurisdictions.add(j)
                if "," in j:
                    states.add(j.rsplit(",", 1)[1].strip())
            ct = row.get("case_type")
            if ct:
                case_types.add(ct)
        
        return {
            "founding_members": {
                "total": fm_total_count,
                "active": fm_active_count,
                "capacity": 2100,
                "slots_remaining": 2100 - fm_total_count,
            },
            "contributions": {
                "total": contrib_total.count or 0,
                "approved": contrib_approved.count or 0,
                "pending": contrib_pending.count or 0,
                "flagged": contrib_flagged.count or 0,
                "rejected": contrib_rejected.count or 0,
            },
            "queries": {
                "total": 0,
                "today": 0,
                "this_week": 0,
                "this_month": 0,
            },
            "reports": {
                "total": 0,
                "pdf": 0,
                "json": 0,
                "html": 0,
            },
            "database": {
                "jurisdictions_covered": len(unique_jurisdictions),
                "states_covered": len(states),
                "case_types": len(case_types),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analytics dashboard: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.get("/analytics/usage")
async def get_usage_analytics(
    start_date: Optional[str] = Query(None, description="Start date: YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date: YYYY-MM-DD"),
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Get SETTLE service usage analytics.
    
    **SaaS Admin Use Case:**
    - Track report generation volume
    - Monitor API usage per tenant
    - Calculate billing data (for $49/report users)
    - Identify usage trends
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        start = start_date or (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%d")
        end = end_date or datetime.now(UTC).strftime("%Y-%m-%d")
        
        # Count contributions in period
        contrib_count = db.table("settle_contributions") \
            .select("id", count="exact") \
            .gte("created_at", f"{start}T00:00:00+00:00") \
            .lte("created_at", f"{end}T23:59:59+00:00") \
            .execute()
        
        # Count founding member vs standard contributions
        fm_contrib = db.table("settle_contributions") \
            .select("id", count="exact") \
            .eq("founding_member", True) \
            .gte("created_at", f"{start}T00:00:00+00:00") \
            .lte("created_at", f"{end}T23:59:59+00:00") \
            .execute()
        
        # Unique contributors
        contributors = db.table("settle_contributions") \
            .select("contributor_user_id") \
            .gte("created_at", f"{start}T00:00:00+00:00") \
            .lte("created_at", f"{end}T23:59:59+00:00") \
            .execute()
        unique_tenants = len(set(row.get("contributor_user_id") for row in (contributors.data or []) if row.get("contributor_user_id")))
        
        return {
            "period": {
                "start": start,
                "end": end,
            },
            "total_contributions": contrib_count.count or 0,
            "total_api_calls": 0,  # Would require request logging
            "unique_tenants": unique_tenants,
            "founding_member_contributions": fm_contrib.count or 0,
            "standard_user_contributions": (contrib_count.count or 0) - (fm_contrib.count or 0),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching usage analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.get("/analytics/contributions")
async def get_contribution_analytics(
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Get contribution statistics and analytics.
    
    **SaaS Admin Use Case:**
    - View total contributions by state/jurisdiction
    - Track contribution growth over time
    - Identify data gaps (jurisdictions with <15 cases)
    - Monitor data quality metrics
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Total counts
        total = db.table("settle_contributions").select("id", count="exact").execute()
        approved = db.table("settle_contributions").select("id", count="exact").eq("status", "approved").execute()
        pending = db.table("settle_contributions").select("id", count="exact").eq("status", "pending").execute()
        rejected = db.table("settle_contributions").select("id", count="exact").eq("status", "rejected").execute()
        fm = db.table("settle_contributions").select("id", count="exact").eq("founding_member", True).execute()
        
        # Jurisdiction breakdown
        jurisdictions = db.table("settle_contributions") \
            .select("jurisdiction") \
            .eq("status", "approved") \
            .execute()
        
        jurisdiction_counts: Dict[str, int] = {}
        for row in (jurisdictions.data or []):
            j = row.get("jurisdiction", "Unknown")
            jurisdiction_counts[j] = jurisdiction_counts.get(j, 0) + 1
        
        # Data gaps: jurisdictions with <15 cases
        data_gaps = [
            {"jurisdiction": j, "count": c}
            for j, c in jurisdiction_counts.items()
            if c < 15
        ]
        data_gaps.sort(key=lambda x: x["count"])
        
        return {
            "total_contributions": total.count or 0,
            "approved_contributions": approved.count or 0,
            "pending_review": pending.count or 0,
            "rejected_contributions": rejected.count or 0,
            "founding_member_contributions": fm.count or 0,
            "jurisdictions_covered": len(jurisdiction_counts),
            "data_gaps": data_gaps,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching contribution analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.get("/analytics/compliance")
async def get_compliance_analytics(
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Get compliance monitoring metrics.
    
    **SaaS Admin Use Case:**
    - Track PII detection incidents
    - Monitor anonymization verification rates
    - Track blockchain hash generation
    - Generate compliance reports for bar committees
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Count rejected (proxy for PII/anonymization failures)
        rejected = db.table("settle_contributions").select("id", count="exact").eq("status", "rejected").execute()
        
        # Count with blockchain hash
        all_contrib = db.table("settle_contributions").select("id, blockchain_hash").execute()
        with_hash = sum(1 for row in (all_contrib.data or []) if row.get("blockchain_hash"))
        
        # Count flagged
        flagged = db.table("settle_contributions").select("id", count="exact").eq("status", "flagged").execute()
        
        # Anomaly flags count
        anomaly_count = db.table("settle_anomaly_flags").select("id", count="exact").execute()
        
        return {
            "pii_detections": rejected.count or 0,
            "anonymization_verified": (all_contrib.count or 0) - (rejected.count or 0),
            "blockchain_hashes_generated": with_hash,
            "compliance_violations": flagged.count or 0,
            "anomaly_flags_total": anomaly_count.count or 0,
            "last_audit": datetime.now(UTC).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching compliance analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.get("/analytics/data-quality")
async def get_data_quality_analytics(
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Get data quality metrics.
    
    **SaaS Admin Use Case:**
    - Track outlier detection
    - Monitor data completeness
    - Identify data quality issues
    - Track confidence scores
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Outliers
        outliers = db.table("settle_contributions").select("id", count="exact").eq("is_outlier", True).execute()
        
        # Approved contributions for quality analysis
        approved = db.table("settle_contributions") \
            .select("id, confidence_score, jurisdiction, case_type, injury_category, medical_bills, outcome_amount_range") \
            .eq("status", "approved") \
            .execute()
        
        rows = approved.data or []
        
        # Average confidence
        scores = [row.get("confidence_score", 0) for row in rows if row.get("confidence_score") is not None]
        avg_confidence = sum(scores) / len(scores) if scores else 0.0
        
        # Data completeness: check required fields
        required_fields = ["jurisdiction", "case_type", "injury_category", "medical_bills", "outcome_amount_range"]
        complete = 0
        quality_issues = []
        
        for row in rows:
            missing = [f for f in required_fields if not row.get(f)]
            if not missing:
                complete += 1
            else:
                quality_issues.append({
                    "contribution_id": row.get("id"),
                    "missing_fields": missing,
                })
        
        completeness = complete / len(rows) if rows else 0.0
        
        return {
            "outliers_flagged": outliers.count or 0,
            "average_confidence_score": round(avg_confidence, 3),
            "data_completeness": round(completeness, 3),
            "total_approved": len(rows),
            "quality_issues": quality_issues[:20],  # Limit to first 20
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching data quality analytics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.get("/health")
async def admin_service_health():
    """Health check for admin service"""
    return {
        "service": "SETTLE Admin Service",
        "status": "operational",
        "endpoints": [
            "/contributions/pending",
            "/contributions/{id}/approve",
            "/contributions/{id}/reject",
            "/founding-members",
            "/api-keys/create",
            "/analytics/usage",
            "/analytics/contributions",
            "/analytics/compliance"
        ]
    }


# ============================================================================
# RICH FIELD CONTRIBUTION MANAGEMENT (Cohort W — 2026-05-17)
# ============================================================================

@router.get("/contributions")
async def get_all_contributions(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected, flagged"),
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    case_type: Optional[str] = Query(None, description="Filter by case type"),
    insurance_carrier: Optional[str] = Query(None, description="Filter by insurance carrier"),
    injury_severity: Optional[str] = Query(None, description="Filter by injury severity"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    is_verdict: Optional[bool] = Query(None, description="Filter by verdict vs settlement"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Get all contributions with rich field filters.
    
    **SaaS Admin Use Case:**
    - Browse all contributions with advanced filtering
    - Filter by new rich fields (carrier, severity, source_type, etc.)
    - Pagination support for large datasets
    """
    try:
        logger.info(f"Admin {admin_data['user_id']} fetching contributions with filters")
        
        db = await get_db()
        
        if db:
            query = db.table('settle_contributions').select('*')
            
            if status:
                query = query.eq('status', status)
            if jurisdiction:
                query = query.ilike('jurisdiction', f'%{jurisdiction}%')
            if case_type:
                query = query.eq('case_type', case_type)
            if insurance_carrier:
                query = query.eq('insurance_carrier', insurance_carrier)
            if injury_severity:
                query = query.eq('injury_severity', injury_severity)
            if source_type:
                query = query.eq('source_type', source_type)
            if is_verdict is not None:
                query = query.eq('is_verdict', is_verdict)
            
            # Get total count
            count_query = db.table('settle_contributions').select('id', count='exact')
            if status:
                count_query = count_query.eq('status', status)
            if jurisdiction:
                count_query = count_query.ilike('jurisdiction', f'%{jurisdiction}%')
            if case_type:
                count_query = count_query.eq('case_type', case_type)
            if insurance_carrier:
                count_query = count_query.eq('insurance_carrier', insurance_carrier)
            if injury_severity:
                count_query = count_query.eq('injury_severity', injury_severity)
            if source_type:
                count_query = count_query.eq('source_type', source_type)
            if is_verdict is not None:
                count_query = count_query.eq('is_verdict', is_verdict)
            
            count_result = count_query.execute()
            total = count_result.count if hasattr(count_result, 'count') else 0
            
            result = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
            
            return {
                "contributions": result.data if result.data else [],
                "total": total,
                "limit": limit,
                "offset": offset
            }
        else:
            return {"contributions": [], "total": 0, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"Error fetching contributions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error", "error": str(e)})


@router.patch("/contributions/{contribution_id}")
async def update_contribution_fields(
    contribution_id: UUID,
    updates: Dict,
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Update rich fields on a contribution (admin-only).
    
    **SaaS Admin Use Case:**
    - Manually set insurance_carrier, injury_severity, etc.
    - Correct scraped data errors
    - Enrich contributions with additional information
    """
    try:
        logger.info(f"Admin {admin_data['user_id']} updating contribution {contribution_id}")
        
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        allowed_fields = {
            'insurance_carrier', 'comparative_negligence_pct', 'exact_outcome_amount',
            'is_verdict', 'date_of_verdict', 'court_level', 'injury_severity',
            'policy_limit_amount', 'source_type', 'trial_duration_days',
            'appeal_filed', 'appeal_outcome', 'status', 'rejection_reason',
            'is_outlier', 'confidence_score'
        }
        
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        if not filtered_updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        result = db.table('settle_contributions') \
            .update(filtered_updates) \
            .eq('id', str(contribution_id)) \
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Contribution not found")
        
        return {"status": "updated", "contribution_id": str(contribution_id), "data": result.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating contribution {contribution_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error", "error": str(e)})


# ============================================================================
# INJURY TAG MANAGEMENT (Cohort W)
# ============================================================================

@router.get("/injury-tags")
async def get_injury_tags(admin_data: dict = Depends(require_admin)) -> Dict:
    """
    Get all injury tags with their rule metadata.
    
    **SaaS Admin Use Case:**
    - View all 17 InjuryTag enum values
    - See rule counts and classification stats per tag
    - Monitor tag usage across contributions
    """
    try:
        from app.services.injury_classifier import InjuryTag
        from app.services.injury_classifier.rules import TAG_RULES
        
        tags = []
        for tag in InjuryTag:
            rule = TAG_RULES.get(tag)
            tags.append({
                "value": tag.value,
                "name": tag.name,
                "pattern_count": len(rule.patterns) if rule else 0,
                "confidence": rule.confidence if rule else None,
                "co_occurrence_required": list(rule.co_occurrence_required) if rule else [],
                "co_occurrence_forbidden": list(rule.co_occurrence_forbidden) if rule else [],
            })
        
        return {"tags": tags, "total": len(tags)}
    except Exception as e:
        logger.error(f"Error fetching injury tags: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error", "error": str(e)})


@router.get("/injury-tags/usage-stats")
async def get_injury_tag_usage_stats(admin_data: dict = Depends(require_admin)) -> Dict:
    """
    Get usage statistics for each injury tag across contributions.
    
    **SaaS Admin Use Case:**
    - See which tags are most/least common
    - Identify tags that need more training data
    - Monitor classification quality
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        result = db.table('settle_contributions') \
            .select('id, injury_category, injury_classification') \
            .eq('status', 'approved') \
            .execute()
        
        rows = result.data or []
        tag_counts: Dict[str, int] = {}
        
        for row in rows:
            tags = row.get('injury_category') or []
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "total_approved": len(rows),
            "tag_counts": [{"tag": t, "count": c} for t, c in sorted_tags],
            "unique_tags": len(tag_counts)
        }
    except Exception as e:
        logger.error(f"Error fetching tag usage stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error", "error": str(e)})


# ============================================================================
# INJURY REVIEW QUEUE MANAGEMENT (Cohort W)
# ============================================================================

@router.get("/review-queue")
async def get_review_queue(
    status: Optional[str] = Query(None, description="Filter by status: pending, accepted, modified, rejected"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Get items in the injury review queue.
    
    **SaaS Admin Use Case:**
    - Review flagged classifications from the injury classifier
    - Accept, modify, or reject automated tags
    - Track review progress
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        query = db.table('injury_review_queue').select('*')
        if status:
            query = query.eq('status', status)
        
        count_result = db.table('injury_review_queue').select('id', count='exact')
        if status:
            count_result = count_result.eq('status', status)
        count_result = count_result.execute()
        total = count_result.count if hasattr(count_result, 'count') else 0
        
        result = query.order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        
        return {
            "items": result.data if result.data else [],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error fetching review queue: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error", "error": str(e)})


@router.post("/review-queue/{queue_id}/review")
async def submit_review(
    queue_id: UUID,
    review_data: Dict,
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Submit a review decision for a queued item.
    
    **SaaS Admin Use Case:**
    - Accept the classifier's tags as-is
    - Modify tags (provide corrected tags)
    - Reject the classification as unrecoverable
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        action = review_data.get('action')
        if action not in ('accept', 'modify', 'reject'):
            raise HTTPException(status_code=400, detail="Action must be 'accept', 'modify', or 'reject'")
        
        updates = {
            'status': action,
            'reviewed_by': admin_data.get('user_id', 'admin'),
            'reviewed_at': datetime.now(UTC).isoformat(),
            'review_action': action,
        }
        
        if action == 'modify':
            updates['final_tags'] = review_data.get('final_tags', [])
        if 'review_notes' in review_data:
            updates['review_notes'] = review_data['review_notes']
        
        result = db.table('injury_review_queue') \
            .update(updates) \
            .eq('id', str(queue_id)) \
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Review queue item not found")
        
        return {"status": "reviewed", "queue_id": str(queue_id), "action": action}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting review for {queue_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error", "error": str(e)})


# ============================================================================
# ENHANCED ANALYTICS WITH RICH FIELDS (Cohort W)
# ============================================================================

@router.get("/analytics/rich-fields")
async def get_rich_field_analytics(admin_data: dict = Depends(require_admin)) -> Dict:
    """
    Get analytics broken down by rich fields.
    
    **SaaS Admin Use Case:**
    - See case distribution by insurance carrier
    - View injury severity breakdown
    - Monitor source type mix (firm submissions vs scraped)
    - Track verdict vs settlement ratio
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        rows = db.table('settle_contributions') \
            .select('insurance_carrier, injury_severity, source_type, is_verdict, court_level, jurisdiction') \
            .eq('status', 'approved') \
            .execute()
        
        data = rows.data or []
        
        carrier_counts: Dict[str, int] = {}
        severity_counts: Dict[str, int] = {}
        source_counts: Dict[str, int] = {}
        verdict_count = 0
        settlement_count = 0
        court_level_counts: Dict[str, int] = {}
        jurisdiction_states: Dict[str, int] = {}
        
        for row in data:
            carrier = row.get('insurance_carrier')
            if carrier:
                carrier_counts[carrier] = carrier_counts.get(carrier, 0) + 1
            
            severity = row.get('injury_severity')
            if severity:
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            source = row.get('source_type')
            if source:
                source_counts[source] = source_counts.get(source, 0) + 1
            
            is_verdict = row.get('is_verdict')
            if is_verdict:
                verdict_count += 1
            elif is_verdict is False:
                settlement_count += 1
            
            court_level = row.get('court_level')
            if court_level:
                court_level_counts[court_level] = court_level_counts.get(court_level, 0) + 1
            
            jurisdiction = row.get('jurisdiction', '')
            if ',' in jurisdiction:
                state = jurisdiction.rsplit(',', 1)[1].strip()
                jurisdiction_states[state] = jurisdiction_states.get(state, 0) + 1
        
        return {
            "total_approved": len(data),
            "insurance_carriers": sorted([{"carrier": k, "count": v} for k, v in carrier_counts.items()], key=lambda x: x["count"], reverse=True),
            "injury_severity": sorted([{"severity": k, "count": v} for k, v in severity_counts.items()], key=lambda x: x["count"], reverse=True),
            "source_types": sorted([{"source": k, "count": v} for k, v in source_counts.items()], key=lambda x: x["count"], reverse=True),
            "verdict_vs_settlement": {
                "verdicts": verdict_count,
                "settlements": settlement_count,
                "unspecified": len(data) - verdict_count - settlement_count
            },
            "court_levels": sorted([{"level": k, "count": v} for k, v in court_level_counts.items()], key=lambda x: x["count"], reverse=True),
            "states": sorted([{"state": k, "count": v} for k, v in jurisdiction_states.items()], key=lambda x: x["count"], reverse=True),
        }
    except Exception as e:
        logger.error(f"Error fetching rich field analytics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error", "error": str(e)})


# ============================================================================
# PROVENANCE VIEWER (Audit-Only — service_role required)
# ============================================================================

@router.get("/provenance/{contribution_id}")
async def get_case_provenance(
    contribution_id: UUID,
    admin_data: dict = Depends(require_admin)
) -> Dict:
    """
    Get case provenance data for a contribution (audit-only).
    
    **SaaS Admin Use Case:**
    - View identifying fields stripped from public contributions
    - Verify source URLs, case citations, docket numbers
    - Access audit trail for compliance reviews
    
    **Security:** This endpoint accesses the private settle_case_provenance table.
    Only service_role can query this table directly.
    """
    try:
        db = await get_db()
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        result = db.table('settle_case_provenance') \
            .select('*') \
            .eq('contribution_id', str(contribution_id)) \
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Provenance not found")
        
        provenance = result.data[0]
        
        # Log the access for audit trail
        db.table('settle_case_provenance') \
            .update({
                'last_audit_access': datetime.now(UTC).isoformat(),
                'last_audit_accessor': admin_data.get('user_id', 'admin')
            }) \
            .eq('contribution_id', str(contribution_id)) \
            .execute()
        
        return provenance
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching provenance for {contribution_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail={"message": "Internal server error", "error": str(e)})

