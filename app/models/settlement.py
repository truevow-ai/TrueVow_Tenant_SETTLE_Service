"""
Settlement Domain Models — SETTLE Resolution Ontology

Entities ENT-081 through ENT-106, aligned with the TrueVow Plaintiff Law Firm
Operations Ontology v1.0.

Product boundary: SETTLE records and supports the decision.
                  The client makes the settlement decision.

Entity mapping:
  ENT-081 Demand Package        -> DemandPackage
  ENT-082 Demand Draft          -> DemandDraft
  ENT-092 Demand Transmission   -> DemandTransmission
  ENT-093 Negotiation Round     -> NegotiationRound
  ENT-094 Offer                 -> Offer
  ENT-095 Counteroffer          -> Counteroffer
  ENT-096 Settlement Decision   -> SettlementDecision
  ENT-097 Settlement Agreement  -> SettlementAgreement
  ENT-098 Release               -> Release
  ENT-099 Settlement Payment    -> SettlementPayment
  ENT-100 Lien/Reimbursement    -> Lien
  ENT-101 Lien Resolution       -> LienResolution
  ENT-102 Settlement Allocation -> SettlementAllocation
  ENT-103 Trust Ledger Entry    -> TrustLedgerEntry
  ENT-104 Closing Statement     -> ClosingStatement
  ENT-105 Disbursement          -> Disbursement
  ENT-106 Matter Closure        -> MatterClosure
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, date
from uuid import UUID


# ============================================================================
# ENUMS & CONSTANTS
# ============================================================================

DemandPackageState = Literal[
    "assembling", "drafting", "attorney_review", "revision_required",
    "authorized", "sent", "superseded", "withdrawn"
]

DemandTransmissionStatus = Literal[
    "pending", "transmitted", "delivered", "failed", "returned"
]

OfferStatus = Literal[
    "offer_received", "client_notice_pending", "under_review",
    "counter_authorized", "accepted", "rejected",
    "expired", "documentation_pending", "fully_documented",
    "payment_pending", "funded"
]

SettlementDecisionType = Literal["accept", "reject", "counter"]

LienStatus = Literal[
    "asserted", "documents_requested", "under_review",
    "verified", "disputed", "negotiating", "resolved", "paid"
]

AllocationStatus = Literal["draft", "approved", "applied"]

DisbursementStatus = Literal["pending", "authorized", "completed", "failed", "reversed"]

MatterClosureState = Literal["active", "closed", "reopened"]

ReleaseStatus = Literal["draft", "attorney_reviewed", "sent", "signed", "executed", "archived"]

SettlementAgreementStatus = Literal["draft", "in_review", "client_approved", "fully_executed", "archived"]

PaymentStatus = Literal["pending", "received", "cleared", "disputed", "returned"]

TrustEntryType = Literal["deposit", "disbursement", "fee_transfer", "adjustment", "reversal"]


# ============================================================================
# ENT-081: DEMAND PACKAGE
# ============================================================================

class DemandPackage(BaseModel):
    """Versioned set of demand materials authorized for transmission."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    claim_ids: List[UUID] = Field(default_factory=list, description="Claims covered by this demand")
    version: int = Field(default=1, ge=1)
    state: DemandPackageState = Field(default="assembling")
    document_hash: Optional[str] = Field(None, description="SHA-256 hash of locked package version")
    authorized_by: Optional[UUID] = Field(None, description="Attorney who authorized transmission")
    authorized_at: Optional[datetime] = None
    superseded_by_id: Optional[UUID] = None
    superseded_at: Optional[datetime] = None
    withdrawn_by: Optional[UUID] = None
    withdrawn_at: Optional[datetime] = None
    withdrawn_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DemandPackageCreate(BaseModel):
    matter_id: UUID
    claim_ids: List[UUID] = Field(default_factory=list)


class DemandPackageUpdate(BaseModel):
    claim_ids: Optional[List[UUID]] = None
    state: Optional[DemandPackageState] = None

    @field_validator("state")
    @classmethod
    def validate_state_transition(cls, v):
        valid_states = {
            "assembling", "drafting", "attorney_review",
            "revision_required", "authorized", "sent",
            "superseded", "withdrawn"
        }
        if v not in valid_states:
            raise ValueError(f"Invalid state: {v}. Must be one of {valid_states}")
        return v


class DemandAuthorizationRequest(BaseModel):
    """Attorney authorizes the demand package for transmission."""
    package_id: UUID
    document_hash: str = Field(..., min_length=1, description="SHA-256 hash of the locked package version")
    authorized_by: UUID = Field(..., description="Attorney UUID")


class DemandTransmitRequest(BaseModel):
    """Transmit an authorized demand package."""
    package_id: UUID
    recipient: str = Field(..., description="Insurer, defense counsel, or adverse party")
    recipient_contact_id: Optional[UUID] = None
    method: Literal["email", "portal", "mail", "fax"] = "email"
    transmission_notes: Optional[str] = None


# ============================================================================
# ENT-082: DEMAND DRAFT
# ============================================================================

class DemandDraft(BaseModel):
    """Draft advocacy document requiring attorney review and authorization."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    matter_id: UUID
    package_id: Optional[UUID] = None
    version: int = Field(default=1, ge=1)
    title: str
    content_hash: Optional[str] = None
    generated_by: Optional[str] = Field(None, description="AI component or user that generated draft")
    is_ai_generated: bool = False
    state: Literal["drafting", "attorney_review", "revision_required", "authorized", "superseded"] = "drafting"
    attorney_reviewer_id: Optional[UUID] = None
    attorney_notes: Optional[str] = None
    authorized_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DemandDraftCreate(BaseModel):
    matter_id: UUID
    package_id: Optional[UUID] = None
    title: str = Field(default="Demand Letter")
    generated_by: Optional[str] = None
    is_ai_generated: bool = False


class DemandDraftReview(BaseModel):
    """Attorney review action on demand draft."""
    draft_id: UUID
    action: Literal["approve", "request_revision"]
    reviewer_id: UUID
    notes: Optional[str] = None


# ============================================================================
# ENT-092: DEMAND TRANSMISSION
# ============================================================================

class DemandTransmission(BaseModel):
    """Authorized delivery of a demand package to the recipient."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    package_id: UUID
    package_version: int
    recipient: str
    recipient_contact_id: Optional[UUID] = None
    method: str
    status: DemandTransmissionStatus = "pending"
    transmission_notes: Optional[str] = None
    transmitted_by: Optional[UUID] = None
    transmitted_at: Optional[datetime] = None
    delivery_confirmed_at: Optional[datetime] = None
    delivery_evidence: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# ENT-093: NEGOTIATION ROUND
# ============================================================================

class NegotiationRound(BaseModel):
    """Ordered set of communications relating to a settlement proposal."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    claim_ids: List[UUID] = Field(default_factory=list)
    round_number: int = Field(default=1, ge=1)
    opened_at: datetime
    closed_at: Optional[datetime] = None
    status: Literal["open", "closed", "stale"] = "open"
    created_at: datetime
    updated_at: datetime


class NegotiationRoundCreate(BaseModel):
    matter_id: UUID
    claim_ids: List[UUID] = Field(default_factory=list)


# ============================================================================
# ENT-094: OFFER
# ============================================================================

class Offer(BaseModel):
    """Proposal to resolve part or all of a claim."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    negotiation_round_id: UUID
    claim_ids: List[UUID] = Field(default_factory=list)
    source: Literal["insurer", "defense_counsel", "adverse_party", "attorney", "client"]
    source_contact_id: Optional[UUID] = None
    amount: float = Field(..., ge=0)
    is_global: bool = Field(default=False, description="Covers all claims in matter")
    terms_summary: Optional[str] = None
    expiration_date: Optional[datetime] = None
    status: OfferStatus = "offer_received"
    received_at: Optional[datetime] = None
    client_notified_at: Optional[datetime] = None
    authorized_by: Optional[UUID] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OfferCreate(BaseModel):
    matter_id: UUID
    negotiation_round_id: UUID
    claim_ids: List[UUID] = Field(default_factory=list)
    source: Literal["insurer", "defense_counsel", "adverse_party", "attorney", "client"]
    source_contact_id: Optional[UUID] = None
    amount: float = Field(..., ge=0)
    is_global: bool = False
    terms_summary: Optional[str] = None
    expiration_date: Optional[datetime] = None
    note: Optional[str] = None
    received_at: Optional[datetime] = Field(default_factory=datetime.utcnow)


# ============================================================================
# ENT-095: COUNTEROFFER
# ============================================================================

class Counteroffer(BaseModel):
    """Responsive proposal in negotiation. Requires client/attorney authority per policy."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    negotiation_round_id: UUID
    responds_to_offer_id: UUID
    claim_ids: List[UUID] = Field(default_factory=list)
    amount: float = Field(..., ge=0)
    is_global: bool = False
    terms_summary: Optional[str] = None
    expiration_date: Optional[datetime] = None
    authorized_by_client: bool = False
    client_authorization_id: Optional[UUID] = Field(None, description="Reference to settlement decision")
    authorized_by_attorney: Optional[UUID] = None
    sent_at: Optional[datetime] = None
    status: Literal["draft", "authorized", "sent", "accepted", "rejected", "expired"] = "draft"
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CounterofferCreate(BaseModel):
    matter_id: UUID
    negotiation_round_id: UUID
    responds_to_offer_id: UUID
    claim_ids: List[UUID] = Field(default_factory=list)
    amount: float = Field(..., ge=0)
    is_global: bool = False
    terms_summary: Optional[str] = None
    expiration_date: Optional[datetime] = None
    note: Optional[str] = None


class CounterofferAuthorize(BaseModel):
    """Authorize a counteroffer (requires client authority)."""
    counteroffer_id: UUID
    attorney_id: UUID
    client_decision_id: UUID


# ============================================================================
# ENT-096: SETTLEMENT DECISION
# ============================================================================

class SettlementDecision(BaseModel):
    """Client-attributable accept, reject, or counter decision.

    INV-005: No settlement acceptance transition occurs without an attributable
    client or valid representative decision.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    offer_id: UUID
    decision: SettlementDecisionType
    decided_by: UUID = Field(..., description="Client UUID (or authorized representative)")
    representative_authority_id: Optional[UUID] = Field(None, description="If decided by a representative, reference to authority record")
    attorney_recommendation_id: Optional[UUID] = Field(None, description="Reference to attorney recommendation record")
    attorney_advised_at: Optional[datetime] = None
    informed_consent_confirmed: bool = False
    rationale: Optional[str] = None
    counter_amount: Optional[float] = Field(None, ge=0)
    counter_terms: Optional[str] = None
    decided_at: datetime
    recorded_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class SettlementDecisionCreate(BaseModel):
    matter_id: UUID
    offer_id: UUID
    decision: SettlementDecisionType
    decided_by: UUID
    representative_authority_id: Optional[UUID] = None
    attorney_recommendation_id: Optional[UUID] = None
    attorney_advised_at: Optional[datetime] = None
    informed_consent_confirmed: bool = False
    rationale: Optional[str] = None
    counter_amount: Optional[float] = Field(None, ge=0)
    counter_terms: Optional[str] = None

    @field_validator("counter_amount")
    @classmethod
    def counter_requires_amount(cls, v, info):
        if info.data.get("decision") == "counter" and (v is None or v == 0):
            raise ValueError("Counteroffer amount is required when decision is 'counter'")
        return v


# ============================================================================
# ENT-097: SETTLEMENT AGREEMENT
# ============================================================================

class SettlementAgreement(BaseModel):
    """Agreement resolving specified claims or matters."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    settlement_decision_id: UUID
    claim_ids: List[UUID] = Field(default_factory=list, description="Claims resolved by this agreement")
    document_hash: Optional[str] = None
    document_version: int = Field(default=1, ge=1)
    status: SettlementAgreementStatus = "draft"
    agreement_date: Optional[date] = None
    effective_date: Optional[date] = None
    gross_amount: Optional[float] = Field(None, ge=0)
    is_confidential: bool = False
    attorney_approved_by: Optional[UUID] = None
    attorney_approved_at: Optional[datetime] = None
    client_signed_by: Optional[UUID] = None
    client_signed_at: Optional[datetime] = None
    firm_signed_by: Optional[UUID] = None
    firm_signed_at: Optional[datetime] = None
    fully_executed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SettlementAgreementCreate(BaseModel):
    matter_id: UUID
    settlement_decision_id: UUID
    claim_ids: List[UUID] = Field(default_factory=list)
    gross_amount: Optional[float] = Field(None, ge=0)
    is_confidential: bool = False
    agreement_date: Optional[date] = None


# ============================================================================
# ENT-098: RELEASE
# ============================================================================

class Release(BaseModel):
    """Document relinquishing specified claims or rights.

    Requires legal review and client authorization (AUTH-017).
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    settlement_agreement_id: UUID
    document_hash: Optional[str] = None
    version: int = Field(default=1, ge=1)
    status: ReleaseStatus = "draft"
    attorney_reviewed_by: Optional[UUID] = None
    attorney_reviewed_at: Optional[datetime] = None
    sent_to_client_at: Optional[datetime] = None
    client_signed_by: Optional[UUID] = None
    client_signed_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    release_scope: Optional[str] = Field(None, description="Summary of claims released")
    is_mutual: bool = False
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ReleaseCreate(BaseModel):
    matter_id: UUID
    settlement_agreement_id: UUID
    release_scope: Optional[str] = None
    is_mutual: bool = False
    note: Optional[str] = None


class ReleaseReviewRequest(BaseModel):
    """Attorney reviews and approves the release."""
    release_id: UUID
    attorney_id: UUID
    approved: bool
    notes: Optional[str] = None


# ============================================================================
# ENT-099: SETTLEMENT PAYMENT
# ============================================================================

class SettlementPayment(BaseModel):
    """Payment received or expected under settlement or judgment."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    settlement_agreement_id: UUID
    payer: str = Field(..., description="Insurer, adverse party, or other payor")
    payer_contact_id: Optional[UUID] = None
    amount: float = Field(..., ge=0)
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    status: PaymentStatus = "pending"
    expected_date: Optional[date] = None
    received_date: Optional[date] = None
    cleared_date: Optional[date] = None
    deposited_to_trust: bool = False
    trust_ledger_entry_id: Optional[UUID] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SettlementPaymentCreate(BaseModel):
    matter_id: UUID
    settlement_agreement_id: UUID
    payer: str
    payer_contact_id: Optional[UUID] = None
    amount: float = Field(..., ge=0)
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    expected_date: Optional[date] = None
    note: Optional[str] = None


class PaymentReceiveRequest(BaseModel):
    """Record receipt of a settlement payment."""
    payment_id: UUID
    received_date: date = Field(default_factory=date.today)
    deposited_to_trust: bool = True
    reference_number: Optional[str] = None


# ============================================================================
# ENT-100: LIEN / REIMBURSEMENT CLAIM
# ============================================================================

class Lien(BaseModel):
    """Asserted claim against proceeds or recovery."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    claimant: str = Field(..., description="Claimant name (e.g., Medicare, health insurer, provider)")
    claimant_type: Literal["medicare", "medicaid", "private_health", "hospital", "workers_comp",
                           "child_support", "attorney", "creditor", "other"]
    claim_basis: Optional[str] = Field(None, description="Legal basis for the lien")
    asserted_amount: Optional[float] = Field(None, ge=0)
    verified_amount: Optional[float] = Field(None, ge=0)
    status: LienStatus = "asserted"
    asserted_date: Optional[date] = None
    documents_received: bool = False
    documents_requested_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    verified_by: Optional[UUID] = None
    disputed_reason: Optional[str] = None
    negotiated_amount: Optional[float] = Field(None, ge=0)
    resolution_date: Optional[date] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class LienCreate(BaseModel):
    matter_id: UUID
    claimant: str
    claimant_type: Literal["medicare", "medicaid", "private_health", "hospital", "workers_comp",
                           "child_support", "attorney", "creditor", "other"]
    claim_basis: Optional[str] = None
    asserted_amount: Optional[float] = Field(None, ge=0)
    asserted_date: Optional[date] = None
    note: Optional[str] = None


class LienVerify(BaseModel):
    """Verify a lien after reviewing supporting documentation."""
    lien_id: UUID
    verified_amount: float = Field(..., ge=0)
    verified_by: UUID
    note: Optional[str] = None


class LienResolve(BaseModel):
    """Record lien resolution — negotiated, waived, adjudicated, or paid."""
    lien_id: UUID
    resolution_type: Literal["negotiated", "waived", "adjudicated", "paid", "reduced"]
    final_amount: float = Field(..., ge=0)
    resolved_by: UUID
    note: Optional[str] = None


# ============================================================================
# ENT-102: SETTLEMENT ALLOCATION
# ============================================================================

class SettlementAllocation(BaseModel):
    """Approved distribution model among client, fees, costs, liens, and others.

    INV-013: Must reconcile to gross proceeds.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    settlement_agreement_id: UUID
    version: int = Field(default=1, ge=1)
    gross_proceeds: float = Field(..., ge=0)
    attorney_fees: float = Field(default=0, ge=0)
    attorney_fee_pct: Optional[float] = Field(None, ge=0, le=100)
    costs_advanced: float = Field(default=0, ge=0)
    lien_payments: float = Field(default=0, ge=0)
    other_deductions: float = Field(default=0, ge=0)
    client_net: float = Field(default=0, ge=0)
    reconciliation_status: Literal["balanced", "unbalanced", "reconciled"] = "unbalanced"
    status: AllocationStatus = "draft"
    approved_by_attorney: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    client_acknowledged: bool = False
    client_acknowledged_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SettlementAllocationCreate(BaseModel):
    matter_id: UUID
    settlement_agreement_id: UUID
    gross_proceeds: float = Field(..., ge=0)
    attorney_fees: float = Field(default=0, ge=0)
    attorney_fee_pct: Optional[float] = Field(None, ge=0, le=100)
    costs_advanced: float = Field(default=0, ge=0)
    lien_payments: float = Field(default=0, ge=0)
    other_deductions: float = Field(default=0, ge=0)
    note: Optional[str] = None


class AllocationApproveRequest(BaseModel):
    """Attorney approval of settlement allocation (AUTH-018)."""
    allocation_id: UUID
    attorney_id: UUID
    client_acknowledged: bool = True


# ============================================================================
# ENT-103: TRUST LEDGER ENTRY
# ============================================================================

class TrustLedgerEntry(BaseModel):
    """Matter-specific accounting entry for safeguarded funds.

    Append-only and reconcilable.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    settlement_payment_id: Optional[UUID] = None
    disbursement_id: Optional[UUID] = None
    entry_type: TrustEntryType
    amount: float
    running_balance: float = Field(default=0)
    description: Optional[str] = None
    reference_number: Optional[str] = None
    posted_by: Optional[UUID] = None
    posted_at: datetime
    reconciled: bool = False
    reconciled_at: Optional[datetime] = None
    created_at: datetime


class TrustLedgerEntryCreate(BaseModel):
    matter_id: UUID
    settlement_payment_id: Optional[UUID] = None
    disbursement_id: Optional[UUID] = None
    entry_type: TrustEntryType
    amount: float
    description: Optional[str] = None
    reference_number: Optional[str] = None


# ============================================================================
# ENT-104: CLOSING STATEMENT
# ============================================================================

class ClosingStatement(BaseModel):
    """Client-facing accounting of gross recovery and deductions.

    Requires approval and delivery evidence.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    settlement_agreement_id: UUID
    allocation_id: UUID
    document_hash: Optional[str] = None
    version: int = Field(default=1, ge=1)
    gross_recovery: float = Field(..., ge=0)
    total_deductions: float = Field(default=0, ge=0)
    net_to_client: float = Field(default=0, ge=0)
    line_items: List[Dict[str, Any]] = Field(default_factory=list, description="Itemized deductions")
    approved_by_attorney: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    client_acknowledged: bool = False
    client_acknowledged_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    delivery_evidence: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ClosingStatementCreate(BaseModel):
    matter_id: UUID
    settlement_agreement_id: UUID
    allocation_id: UUID


# ============================================================================
# ENT-105: DISBURSEMENT
# ============================================================================

class Disbursement(BaseModel):
    """Authorized transfer of funds to a payee.

    AUTH-019: Requires authorized firm user under legal/accounting controls.
    Never based solely on workflow completion.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    allocation_id: UUID
    payee: str
    payee_type: Literal["client", "attorney_fees", "lienholder", "cost_vendor", "other"]
    amount: float = Field(..., ge=0)
    status: DisbursementStatus = "pending"
    authorized_by: Optional[UUID] = None
    authorized_at: Optional[datetime] = None
    trust_ledger_entry_id: Optional[UUID] = None
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[UUID] = None
    error_message: Optional[str] = None
    reversed_at: Optional[datetime] = None
    reversed_by: Optional[UUID] = None
    reversal_reason: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DisbursementCreate(BaseModel):
    matter_id: UUID
    allocation_id: UUID
    payee: str
    payee_type: Literal["client", "attorney_fees", "lienholder", "cost_vendor", "other"]
    amount: float = Field(..., ge=0)
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    note: Optional[str] = None


class DisbursementAuthorize(BaseModel):
    """Authorize a disbursement (AUTH-019)."""
    disbursement_id: UUID
    authorized_by: UUID


# ============================================================================
# ENT-106: MATTER CLOSURE
# ============================================================================

class MatterClosure(BaseModel):
    """Formal operational end state with unresolved-item checks.

    INV-019: Closed matters remain subject to retention, access, accounting,
    and continuing-duty rules.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    state: MatterClosureState = "active"
    closure_type: Optional[Literal["settlement", "verdict", "dismissal", "withdrawal", "other"]] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[UUID] = None
    closure_authorized_by: Optional[UUID] = Field(None, description="Attorney authorizing closure")
    unresolved_items: List[Dict[str, Any]] = Field(default_factory=list, description="Items remaining unresolved at closure")
    reopened_at: Optional[datetime] = None
    reopened_by: Optional[UUID] = None
    reopen_reason: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MatterClosureRequest(BaseModel):
    """Request to close a matter."""
    matter_id: UUID
    closure_type: Literal["settlement", "verdict", "dismissal", "withdrawal", "other"]
    authorized_by: UUID
    note: Optional[str] = None


class MatterReopenRequest(BaseModel):
    """Request to reopen a closed matter."""
    matter_id: UUID
    reason: str
    authorized_by: UUID


# ============================================================================
# ATTORNEY SETTLEMENT RECOMMENDATION
# ============================================================================

class AttorneyRecommendation(BaseModel):
    """Attorney's settlement recommendation to the client.

    AUTH-015: Recommendation must be attorney-controlled.
    AI may support analysis only.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    offer_id: UUID
    recommended_action: Literal["accept", "reject", "counter"]
    recommended_counter_amount: Optional[float] = Field(None, ge=0)
    analysis_summary: Optional[str] = None
    considerations: List[str] = Field(default_factory=list)
    ai_supported: bool = False
    ai_analysis_reference: Optional[str] = None
    recommended_by: UUID = Field(..., description="Attorney UUID")
    recommended_at: datetime
    created_at: datetime
    updated_at: datetime


class AttorneyRecommendationCreate(BaseModel):
    matter_id: UUID
    offer_id: UUID
    recommended_action: Literal["accept", "reject", "counter"]
    recommended_counter_amount: Optional[float] = Field(None, ge=0)
    analysis_summary: Optional[str] = None
    considerations: List[str] = Field(default_factory=list)


# ============================================================================
# AUDIT EVENT FOR SETTLEMENT DOMAIN
# ============================================================================

class SettlementAuditEvent(BaseModel):
    """Immutable audit event for all material settlement actions."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    matter_id: UUID
    event_type: str = Field(..., description="e.g., offer.received, settlement.accepted_by_client")
    actor_id: Optional[UUID] = None
    actor_type: Optional[str] = None
    authority_source: Optional[str] = Field(None, description="ATTY-AUTH, CLIENT-AUTH, etc.")
    prior_state: Optional[str] = None
    resulting_state: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    policy_version: Optional[str] = None
    occurred_at: datetime
    created_at: datetime
