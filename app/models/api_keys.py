"""
API Key and Founding Member Data Models
"""

from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict
from typing import Optional
from datetime import datetime, UTC
from uuid import UUID


class APIKey(BaseModel):
    """Database model for API keys"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    api_key: str = Field(..., description="Hashed API key")
    api_key_prefix: str = Field(..., description="First 8 characters for display")
    
    access_level: str = Field(
        ...,
        description="founding_member, standard, premium, admin, external"
    )
    
    # User info
    user_email: Optional[EmailStr] = None
    law_firm_name: Optional[str] = None
    
    # Usage tracking
    requests_used: int = 0
    requests_limit: Optional[int] = None  # NULL = unlimited (founding members)
    last_used_at: Optional[datetime] = None
    
    # Status
    is_active: bool = True
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    notes: Optional[str] = None


class APIKeyRequest(BaseModel):
    """Request model for creating API key"""
    
    user_email: EmailStr = Field(..., description="User email")
    law_firm_name: Optional[str] = Field(None, description="Law firm name")
    access_level: str = Field(..., description="Access level")
    requests_limit: Optional[int] = Field(None, description="Request limit (NULL = unlimited)")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    notes: Optional[str] = Field(None, description="Internal notes")
    
    @field_validator('access_level')
    @classmethod
    def validate_access_level(cls, v):
        """Validate access level"""
        valid_levels = ['founding_member', 'standard', 'premium', 'admin', 'external']
        if v not in valid_levels:
            raise ValueError(f"Access level must be one of: {', '.join(valid_levels)}")
        return v


class APIKeyResponse(BaseModel):
    """Response model for API key creation"""
    
    id: UUID
    api_key: str = Field(..., description="Full API key (only shown once!)")
    api_key_prefix: str = Field(..., description="Prefix for display")
    access_level: str
    requests_limit: Optional[int] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    message: str = Field(
        default="API key created successfully. Store it securely - it won't be shown again!"
    )


class FoundingMember(BaseModel):
    """Database model for Founding Members"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    email: EmailStr
    law_firm_name: str
    bar_number: Optional[str] = None
    state: str
    
    api_key_id: Optional[UUID] = None
    
    status: str = Field(default="active", description="active, inactive, revoked")
    joined_at: datetime
    
    # Stats
    contributions_count: int = 0
    queries_count: int = 0
    reports_generated: int = 0
    
    referral_source: Optional[str] = None
    notes: Optional[str] = None


class FoundingMemberRequest(BaseModel):
    """Request model for Founding Member enrollment"""
    
    email: EmailStr = Field(..., description="Email address")
    law_firm_name: str = Field(..., min_length=2, description="Law firm name")
    bar_number: Optional[str] = Field(None, description="State bar number")
    state: str = Field(..., description="State (2-letter code)")
    referral_source: Optional[str] = Field(None, description="How they heard about SETTLE")
    
    @field_validator('state')
    @classmethod
    def validate_state(cls, v):
        """Validate state is 2-letter uppercase code"""
        if len(v) != 2 or not v.isalpha():
            raise ValueError("State must be 2-letter code (e.g., 'AZ', 'CA')")
        return v.upper()


class FoundingMemberResponse(BaseModel):
    """Response model for Founding Member enrollment"""
    
    id: UUID
    email: EmailStr
    law_firm_name: str
    state: str
    status: str
    joined_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    api_key: str = Field(..., description="API key for unlimited access")
    
    message: str = Field(
        default="Welcome to the Founding Member program! You have unlimited access forever."
    )
    
    benefits: list[str] = Field(
        default_factory=lambda: [
            "Unlimited settlement range queries",
            "Unlimited report generation",
            "Free forever (no subscription fees)",
            "Priority support",
            "Early access to new features",
            "Voting rights on database policies"
        ]
    )
