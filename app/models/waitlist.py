"""
Waitlist Data Models
"""

from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from typing import Optional
from datetime import datetime, UTC
from uuid import UUID


class WaitlistEntry(BaseModel):
    """Database model for waitlist entries"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    email: EmailStr
    law_firm_name: Optional[str] = None
    practice_area: Optional[str] = None
    state: Optional[str] = None
    
    status: str = Field(default="pending", description="pending, approved, invited, converted")
    
    joined_at: datetime
    invited_at: Optional[datetime] = None
    converted_at: Optional[datetime] = None
    referral_source: Optional[str] = None
    notes: Optional[str] = None


class WaitlistRequest(BaseModel):
    """Request model for joining waitlist"""
    
    email: EmailStr = Field(..., description="Email address")
    law_firm_name: Optional[str] = Field(None, min_length=2, description="Law firm name")
    practice_area: Optional[str] = Field(None, description="Practice area")
    state: Optional[str] = Field(None, description="State (2-letter code)")
    referral_source: Optional[str] = Field(None, description="How they heard about SETTLE")
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v):
        """Validate state is 2-letter uppercase code"""
        if v and (len(v) != 2 or not v.isalpha()):
            raise ValueError("State must be 2-letter code (e.g., 'AZ', 'CA')")
        return v.upper() if v else None


class WaitlistResponse(BaseModel):
    """Response model for waitlist submission"""
    
    id: UUID
    email: EmailStr
    message: str = Field(default="You've been added to the SETTLE waitlist!")
    position: Optional[int] = Field(None, description="Position in waitlist")
    joined_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
