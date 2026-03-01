"""
Waitlist Endpoints

Public and admin endpoints for SETTLE waitlist management.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from uuid import uuid4
from datetime import datetime
import logging

from app.core.database import get_db
from app.core.auth import APIKeyAuth

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
        # Check if email already exists
        existing = await db.fetch_one(
            "SELECT id FROM settle_waitlist WHERE email = $1",
            request.email
        )
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail="This email is already on the waitlist"
            )
        
        # Generate waitlist ID
        waitlist_id = str(uuid4())
        
        # Insert into database (using joined_at as created_at)
        await db.execute(
            """
            INSERT INTO settle_waitlist (
                id, firm_name, contact_name, email, phone, 
                practice_areas, jurisdiction, referral_source,
                status, joined_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            waitlist_id,
            request.firm_name,
            request.contact_name,
            request.email,
            request.phone,
            request.practice_areas,
            request.jurisdiction,
            request.referral_source,
            "pending",
            datetime.utcnow()
        )
        
        # Calculate position in queue
        position = await db.fetch_val(
            "SELECT COUNT(*) FROM settle_waitlist WHERE status = 'pending'"
        )
        
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
@router.get("/entries", response_model=List[WaitlistEntry], dependencies=[Depends(APIKeyAuth)])
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
        query = """
            SELECT 
                id, firm_name, contact_name, email, phone,
                practice_areas, jurisdiction, status,
                joined_at as created_at, reviewed_at, reviewed_by
            FROM settle_waitlist
        """
        
        if status:
            query += f" WHERE status = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3"
            rows = await db.fetch_all(query, status, limit, offset)
        else:
            query += " ORDER BY created_at DESC LIMIT $1 OFFSET $2"
            rows = await db.fetch_all(query, limit, offset)
        
        entries = []
        for row in rows:
            entries.append(WaitlistEntry(
                id=row['id'],
                firm_name=row['firm_name'],
                contact_name=row['contact_name'],
                email=row['email'],
                phone=row['phone'],
                practice_areas=row['practice_areas'],
                jurisdiction=row['jurisdiction'],
                status=row['status'],
                created_at=row['created_at'].isoformat(),
                reviewed_at=row['reviewed_at'].isoformat() if row['reviewed_at'] else None,
                reviewed_by=row['reviewed_by']
            ))
        
        return entries
        
    except Exception as e:
        logger.error(f"Error listing waitlist: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list waitlist: {str(e)}")


@router.get("/entries/{entry_id}", response_model=WaitlistEntry, dependencies=[Depends(APIKeyAuth)])
async def get_waitlist_entry(entry_id: str, db = Depends(get_db)):
    """
    Get waitlist entry details (Admin only).
    """
    
    try:
        row = await db.fetch_one(
            """
            SELECT 
                id, firm_name, contact_name, email, phone,
                practice_areas, jurisdiction, status,
                joined_at as created_at, reviewed_at, reviewed_by
            FROM settle_waitlist
            WHERE id = $1
            """,
            entry_id
        )
        
        if not row:
            raise HTTPException(status_code=404, detail="Waitlist entry not found")
        
        return WaitlistEntry(
            id=row['id'],
            firm_name=row['firm_name'],
            contact_name=row['contact_name'],
            email=row['email'],
            phone=row['phone'],
            practice_areas=row['practice_areas'],
            jurisdiction=row['jurisdiction'],
            status=row['status'],
            created_at=row['created_at'].isoformat(),
            reviewed_at=row['reviewed_at'].isoformat() if row['reviewed_at'] else None,
            reviewed_by=row['reviewed_by']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting waitlist entry: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get waitlist entry: {str(e)}")


@router.post("/entries/{entry_id}/approve", dependencies=[Depends(APIKeyAuth)])
async def approve_waitlist_entry(
    entry_id: str,
    request: WaitlistApprovalRequest,
    auth: dict = Depends(APIKeyAuth),
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
        # Get waitlist entry
        entry = await db.fetch_one(
            "SELECT * FROM settle_waitlist WHERE id = $1",
            entry_id
        )
        
        if not entry:
            raise HTTPException(status_code=404, detail="Waitlist entry not found")
        
        if entry['status'] != 'pending':
            raise HTTPException(
                status_code=400,
                detail=f"Entry already {entry['status']}"
            )
        
        # Update waitlist status
        await db.execute(
            """
            UPDATE settle_waitlist
            SET status = 'approved',
                reviewed_at = $1,
                reviewed_by = $2
            WHERE id = $3
            """,
            datetime.utcnow(),
            auth.get('tenant_id', 'admin'),
            entry_id
        )
        
        # Create Founding Member record
        member_id = str(uuid4())
        tenant_id = str(uuid4())  # New tenant ID for this firm
        
        await db.execute(
            """
            INSERT INTO settle_founding_members (
                id, tenant_id, firm_name, contact_email,
                status, total_contributions, approved_contributions,
                joined_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            member_id,
            tenant_id,
            entry['firm_name'],
            entry['email'],
            'active',
            0,
            0,
            datetime.utcnow()
        )
        
        # Generate API key
        from app.core.security import generate_api_key, hash_api_key
        
        api_key = generate_api_key()
        hashed_key = hash_api_key(api_key)
        
        await db.execute(
            """
            INSERT INTO settle_api_keys (
                id, tenant_id, key_hash, name, status, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6)
            """,
            str(uuid4()),
            tenant_id,
            hashed_key,
            f"API Key for {entry['firm_name']}",
            'active',
            datetime.utcnow()
        )
        
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


@router.post("/entries/{entry_id}/reject", dependencies=[Depends(APIKeyAuth)])
async def reject_waitlist_entry(
    entry_id: str,
    request: WaitlistApprovalRequest,
    auth: dict = Depends(APIKeyAuth),
    db = Depends(get_db)
):
    """
    Reject waitlist entry (Admin only).
    """
    
    try:
        # Get waitlist entry
        entry = await db.fetch_one(
            "SELECT * FROM settle_waitlist WHERE id = $1",
            entry_id
        )
        
        if not entry:
            raise HTTPException(status_code=404, detail="Waitlist entry not found")
        
        if entry['status'] != 'pending':
            raise HTTPException(
                status_code=400,
                detail=f"Entry already {entry['status']}"
            )
        
        # Update waitlist status
        await db.execute(
            """
            UPDATE settle_waitlist
            SET status = 'rejected',
                reviewed_at = $1,
                reviewed_by = $2
            WHERE id = $3
            """,
            datetime.utcnow(),
            auth.get('tenant_id', 'admin'),
            entry_id
        )
        
        logger.info(f"Waitlist entry rejected: {entry_id}")
        
        # Send rejection email
        try:
            from app.services.notifications import get_email_service
            email_service = get_email_service()
            email_sent = await email_service.send_waitlist_rejection(
                to_email=entry['email'],
                law_firm_name=entry['firm_name'],
                reason=request.rejection_reason or "Application did not meet current criteria"
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

