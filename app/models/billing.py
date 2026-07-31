"""
Billing Usage Models — SETTLE Product Service

SETTLE owns operational facts. It does NOT calculate customer prices.
The Billing Service is authoritative for pricing, entitlements, and charges.

Meters:
  settle_finalized_report — billable when report state reaches FINALIZED
  settle_pro_subscription   — $299/month, 15 included credits, $25/report overage
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from uuid import UUID


class BillingUsageEvent(BaseModel):
    """Operational fact emitted by SETTLE to the Billing Usage Ledger.

    Billing applies final qualification rules (not SETTLE).
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    meter_code: str = Field(..., description="e.g., settle_finalized_report")
    event_type: str = Field(..., description="e.g., settle.report.finalized")
    source_entity_type: str = Field(..., description="e.g., settle_report")
    source_entity_id: UUID
    occurred_at: datetime
    payload: Dict[str, Any] = Field(default_factory=dict)
    is_test: bool = False
    is_duplicate: bool = False
    billing_qualification_hint: Optional[str] = None
    created_at: datetime


class BillingUsageEventCreate(BaseModel):
    """Create a billing usage event."""
    tenant_id: UUID
    meter_code: str = "settle_finalized_report"
    event_type: str = "settle.report.finalized"
    source_entity_type: str = "settle_report"
    source_entity_id: UUID
    payload: Dict[str, Any] = Field(default_factory=dict)
    is_test: bool = False
    is_duplicate: bool = False
    billing_qualification_hint: Optional[str] = None


class EntitlementGrant(BaseModel):
    """What a tenant is entitled to use for a product."""
    model_config = ConfigDict(from_attributes=True)

    tenant_id: UUID
    product_code: str
    plan_code: str
    subscription_status: Literal[
        "PENDING", "TRIAL", "ACTIVE", "PAST_DUE", "GRACE",
        "SUSPENDED", "CANCELLED", "EXPIRED",
    ]
    capabilities: List[str] = Field(default_factory=list)
    limits: Dict[str, Any] = Field(default_factory=dict)
    usage: Dict[str, Any] = Field(default_factory=dict)
    credits: Dict[str, Any] = Field(default_factory=dict)
    effective_from: datetime
    effective_until: Optional[datetime] = None
    grace_until: Optional[datetime] = None
    catalog_version: Optional[str] = None


class SubscriptionGateResult(BaseModel):
    """Result of a subscription gate check."""
    allowed: bool
    reason: Optional[str] = None
    subscription_status: Optional[str] = None
    required_capability: Optional[str] = None
    tenant_id: UUID
    product_code: str = "SETTLE"


SETTLE_METER_CODES = {
    "finalized_report": "settle_finalized_report",
    "pro_subscription": "settle_pro_subscription",
}

SETTLE_CAPABILITIES = {
    "per_case": [
        "SETTLE_REPORT_GENERATE",
        "SETTLE_REPORT_VIEW",
        "SETTLE_ESTIMATE_QUERY",
        "SETTLE_CONTRIBUTE",
    ],
    "pro": [
        "SETTLE_REPORT_GENERATE",
        "SETTLE_REPORT_VIEW",
        "SETTLE_ESTIMATE_QUERY",
        "SETTLE_CONTRIBUTE",
        "SETTLE_TREND_ANALYTICS",
        "SETTLE_CARRIER_ANALYTICS",
        "SETTLE_OUTCOME_DISTRIBUTION",
        "SETTLE_CONFIDENCE_SCORE",
        "SETTLE_ADVANCED_REPORTS",
    ],
}

SETTLE_PLAN_BILLING = {
    "settle_per_case_v1": {
        "type": "per_case",
        "report_price_cents": 7900,
        "description": "Per Case",
    },
    "settle_pro_v1": {
        "type": "subscription",
        "monthly_price_cents": 29900,
        "included_report_credits": 15,
        "overage_price_cents": 2500,
        "description": "Pro",
    },
}
