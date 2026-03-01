"""
Report and Query Data Models
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime, UTC
from uuid import UUID


class SettleQuery(BaseModel):
    """Database model for settlement queries"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    
    # Query parameters
    injury_type: str
    state: str
    county: Optional[str] = None
    medical_bills: Optional[float] = None
    
    # Results
    percentile_25: Optional[float] = None
    median: Optional[float] = None
    percentile_75: Optional[float] = None
    percentile_95: Optional[float] = None
    n_cases: Optional[int] = None
    confidence: Optional[str] = None  # low, medium, high
    
    # API key
    api_key_id: Optional[UUID] = None
    
    # Metadata
    queried_at: datetime
    response_time_ms: Optional[int] = None


class SettleReport(BaseModel):
    """Database model for generated reports"""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    query_id: Optional[UUID] = None
    report_url: Optional[str] = None
    ots_hash: Optional[str] = None  # OpenTimestamps hash
    format: str = "pdf"  # pdf, json, html
    
    api_key_id: Optional[UUID] = None
    
    generated_at: datetime
    downloaded_at: Optional[datetime] = None


class ReportRequest(BaseModel):
    """Request model for report generation"""
    
    query_id: Optional[UUID] = Field(None, description="Query ID (if re-generating)")
    estimate_id: Optional[str] = Field(None, description="Estimate ID (legacy)")
    format: str = Field(default="pdf", description="Report format: pdf, json, html")
    
    # If no query_id provided, allow inline query parameters
    injury_type: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None
    medical_bills: Optional[float] = None
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        """Validate report format"""
        valid_formats = ['pdf', 'json', 'html']
        if v not in valid_formats:
            raise ValueError(f"Format must be one of: {', '.join(valid_formats)}")
        return v.lower()


class ReportResponse(BaseModel):
    """Response model for report generation"""
    
    report_id: UUID
    query_id: Optional[UUID] = None
    report_url: str = Field(..., description="URL to download report")
    ots_hash: str = Field(..., description="OpenTimestamps blockchain hash")
    format: str = Field(..., description="Report format")
    
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Report metadata
    summary: Optional[dict] = Field(
        None,
        description="Report summary (if format=json)"
    )
    
    message: str = Field(
        default="Report generated successfully. Download link valid for 7 days."
    )


class ReportSummary(BaseModel):
    """Summary data included in reports"""
    
    case_overview: dict = Field(..., description="Case parameters")
    settlement_range: dict = Field(..., description="Statistical ranges")
    comparable_cases_count: int = Field(..., description="Number of comparable cases")
    confidence_level: str = Field(..., description="low, medium, high")
    jurisdiction: str = Field(..., description="County and state")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # 4-page structure metadata
    pages: dict = Field(
        default_factory=lambda: {
            "page_1": "Summary - Case overview and range (unweighted + weighted)",
            "page_2": "Comparable Cases - Table with similar cases (no narratives)",
            "page_3": "Range Justification - Multiplier math, county clusters",
            "page_4": "Compliance & Integrity - No PHI statement, OpenTimestamps hash"
        }
    )
