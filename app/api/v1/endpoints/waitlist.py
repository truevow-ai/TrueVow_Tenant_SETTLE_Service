"""
Waitlist Endpoints

Public and admin endpoints for SETTLE waitlist management.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from uuid import uuid4
from datetime import datetime, UTC
import logging

from app.core.database import get_db
from app.core.auth import require_admin

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class WaitlistJoinRequest(BaseModel):
    """Request to join SETTLE waitlist"""
    firm_name: str
    contact_name: str
    email: EmailStr
    phone: Optional[str] = None
    practice_areas: List[str]
    jurisdiction: Optional[str] = None
    referral_source: Optional[str] = None


class WaitlistJoinResponse(BaseModel):
    """Response after joining waitlist"""
    waitlist_id: str
    message: str
    position: Optional[int] = None


class WaitlistEntry(BaseModel):
    """Waitlist entry details"""
    id: str
    firm_name: str
    contact_name: str
    email: str
    phone: Optional[str]
    practice_areas: List[str]
    jurisdiction: Optional[str]
    status: str  # 'pending', 'approved', 'rejected'
    created_at: str
    reviewed_at: Optional[str]
    reviewed_by: Optional[str]


class WaitlistApprovalRequest(BaseModel):
    """Request to approve/reject waitlist entry"""
    notes: Optional[str] = None


# Public Endpoints (No Auth Required)
@router.post("/join", response_model=WaitlistJoinResponse)
async def join_waitlist(request: WaitlistJoinRequest, db = Depends(get_db)):
    """
    Join the SETTLE waitlist.
    
    Public endpoint - no authentication required.
    Attorneys can sign up for early access to SETTLE.
    """
    
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Check if email already exists
        existing = db.table("settle_waitlist") \
            .select("id") \
            .eq("email", request.email) \
            .execute()
        
        if existing.data and len(existing.data) > 0:
            raise HTTPException(
                status_code=400,
                detail="This email is already on the waitlist"
            )
        
        # Generate waitlist ID
        waitlist_id = str(uuid4())
        
        # Insert into database
        insert_data = {
            "id": waitlist_id,
            "firm_name": request.firm_name,
            "contact_name": request.contact_name,
            "email": request.email,
            "phone": request.phone,
            "practice_areas": request.practice_areas,
            "jurisdiction": request.jurisdiction,
            "referral_source": request.referral_source,
            "status": "pending",
            "joined_at": datetime.now(UTC).isoformat(),
        }
        
        result = db.table("settle_waitlist").insert(insert_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to join waitlist")
        
        # Calculate position in queue
        pending = db.table("settle_waitlist") \
            .select("id", count="exact") \
            .eq("status", "pending") \
            .execute()
        
        position = pending.count if hasattr(pending, "count") and pending.count else 0
        
        logger.info(f"Waitlist join: {request.email} from {request.firm_name} (ID: {waitlist_id})")
        
        return WaitlistJoinResponse(
            waitlist_id=waitlist_id,
            message=f"Thank you for your interest in SETTLE! We'll contact you at {request.email} when approved.",
            position=position
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error joining waitlist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to join waitlist: {str(e)}")


# Admin Endpoints (Auth Required)
@router.get("/entries", response_model=List[WaitlistEntry], dependencies=[Depends(require_admin)])
async def list_waitlist_entries(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db = Depends(get_db)
):
    """
    List waitlist entries (Admin only).
    
    Filter by status: 'pending', 'approved', 'rejected'
    """
    
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        query = db.table("settle_waitlist").select(
            "id, firm_name, contact_name, email, phone, "
            "practice_areas, jurisdiction, status, "
            "joined_at, reviewed_at, reviewed_by"
        )
        
        if status:
            query = query.eq("status", status)
        
        query = query.order("joined_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()
        
        rows = result.data or []
        entries = []
        for row in rows:
            entries.append(WaitlistEntry(
                id=row['id'],
                firm_name=row['firm_name'],
                contact_name=row['contact_name'],
                email=row['email'],
                phone=row.get('phone'),
                practice_areas=row.get('practice_areas', []),
                jurisdiction=row.get('jurisdiction'),
                status=row['status'],
                created_at=row['joined_at'] if isinstance(row['joined_at'], str) else row['joined_at'].isoformat(),
                reviewed_at=row.get('reviewed_at'),
                reviewed_by=row.get('reviewed_by'),
            ))
        
        return entries
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing waitlist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list waitlist: {str(e)}")


@router.get("/entries/{entry_id}", response_model=WaitlistEntry, dependencies=[Depends(require_admin)])
async def get_waitlist_entry(entry_id: str, db = Depends(get_db)):
    """
    Get waitlist entry details (Admin only).
    """
    
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        result = db.table("settle_waitlist") \
            .select("id, firm_name, contact_name, email, phone, "
                    "practice_areas, jurisdiction, status, "
                    "joined_at, reviewed_at, reviewed_by") \
            .eq("id", entry_id) \
            .execute()
        
        if not result.data or len(result.data) == 0:
            raise HTTPException(status_code=404, detail="Waitlist entry not found")
        
        row = result.data[0]
        
        return WaitlistEntry(
            id=row['id'],
            firm_name=row['firm_name'],
            contact_name=row['contact_name'],
            email=row['email'],
            phone=row.get('phone'),
            practice_areas=row.get('practice_areas', []),
            jurisdiction=row.get('jurisdiction'),
            status=row['status'],
            created_at=row['joined_at'] if isinstance(row['joined_at'], str) else row['joined_at'].isoformat(),
            reviewed_at=row.get('reviewed_at'),
            reviewed_by=row.get('reviewed_by'),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting waitlist entry: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get waitlist entry: {str(e)}")


@router.post("/entries/{entry_id}/approve", dependencies=[Depends(require_admin)])
async def approve_waitlist_entry(
    entry_id: str,
    request: WaitlistApprovalRequest,
    auth: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """
    Approve waitlist entry and create Founding Member (Admin only).
    
    This will:
    1. Update waitlist status to 'approved'
    2. Create a Founding Member record
    3. Generate an API key
    4. Send welcome email (if email service configured)
    """
    
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Get waitlist entry
        entry_result = db.table("settle_waitlist") \
            .select("*") \
            .eq("id", entry_id) \
            .execute()
        
        if not entry_result.data or len(entry_result.data) == 0:
            raise HTTPException(status_code=404, detail="Waitlist entry not found")
        
        entry = entry_result.data[0]
        
        if entry['status'] != 'pending':
            raise HTTPException(
                status_code=400,
                detail=f"Entry already {entry['status']}"
            )
        
        # Update waitlist status
        db.table("settle_waitlist").update({
            "status": "approved",
            "reviewed_at": datetime.now(UTC).isoformat(),
            "reviewed_by": auth.get('user_id', 'admin'),
        }).eq("id", entry_id).execute()
        
        # Create Founding Member record
        member_id = str(uuid4())
        tenant_id = str(uuid4())  # New tenant ID for this firm
        
        db.table("settle_founding_members").insert({
            "id": member_id,
            "tenant_id": tenant_id,
            "firm_name": entry['firm_name'],
            "contact_email": entry['email'],
            "status": 'active',
            "total_contributions": 0,
            "approved_contributions": 0,
            "joined_at": datetime.now(UTC).isoformat(),
        }).execute()
        
        # Generate API key
        from app.core.security import generate_api_key, hash_api_key
        
        api_key = generate_api_key()
        hashed_key = hash_api_key(api_key)
        
        db.table("settle_api_keys").insert({
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "api_key_hash": hashed_key,
            "name": f"API Key for {entry['firm_name']}",
            "status": 'active',
            "created_at": datetime.now(UTC).isoformat(),
        }).execute()
        
        logger.info(f"Waitlist entry approved: {entry_id} → Member: {member_id}, Tenant: {tenant_id}")
        
        # Send welcome email with API key
        try:
            from app.services.notifications import get_email_service
            email_service = get_email_service()
            email_sent = await email_service.send_founding_member_welcome(
                to_email=entry['email'],
                law_firm_name=entry['firm_name'],
                api_key=api_key
            )
            if email_sent:
                logger.info(f"Welcome email sent to {entry['email']}")
            else:
                logger.warning(f"Failed to send welcome email to {entry['email']}")
        except Exception as e:
            logger.error(f"Error sending welcome email: {str(e)}")
            # Don't fail the approval if email fails
        
        return {
            "message": "Waitlist entry approved successfully",
            "member_id": member_id,
            "tenant_id": tenant_id,
            "api_key": api_key,  # Only shown once!
            "note": "Save this API key securely. It won't be shown again."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving waitlist entry: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to approve entry: {str(e)}")


@router.post("/entries/{entry_id}/reject", dependencies=[Depends(require_admin)])
async def reject_waitlist_entry(
    entry_id: str,
    request: WaitlistApprovalRequest,
    auth: dict = Depends(require_admin),
    db = Depends(get_db)
):
    """
    Reject waitlist entry (Admin only).
    """
    
    try:
        if not db:
            raise HTTPException(status_code=503, detail="Database unavailable")
        
        # Get waitlist entry
        entry_result = db.table("settle_waitlist") \
            .select("*") \
            .eq("id", entry_id) \
            .execute()
        
        if not entry_result.data or len(entry_result.data) == 0:
            raise HTTPException(status_code=404, detail="Waitlist entry not found")
        
        entry = entry_result.data[0]
        
        if entry['status'] != 'pending':
            raise HTTPException(
                status_code=400,
                detail=f"Entry already {entry['status']}"
            )
        
        # Update waitlist status
        db.table("settle_waitlist").update({
            "status": "rejected",
            "reviewed_at": datetime.now(UTC).isoformat(),
            "reviewed_by": auth.get('user_id', 'admin'),
        }).eq("id", entry_id).execute()
        
        logger.info(f"Waitlist entry rejected: {entry_id}")
        
        # Send rejection email
        try:
            from app.services.notifications import get_email_service
            email_service = get_email_service()
            email_sent = await email_service.send_waitlist_rejection(
                to_email=entry['email'],
                law_firm_name=entry['firm_name'],
                reason=request.notes or "Application did not meet current criteria"
            )
            if email_sent:
                logger.info(f"Rejection email sent to {entry['email']}")
            else:
                logger.warning(f"Failed to send rejection email to {entry['email']}")
        except Exception as e:
            logger.error(f"Error sending rejection email: {str(e)}")
            # Don't fail the rejection if email fails
        
        return {
            "message": "Waitlist entry rejected",
            "entry_id": entry_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting waitlist entry: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reject entry: {str(e)}")
