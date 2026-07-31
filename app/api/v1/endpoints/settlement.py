"""
Settlement Workflow API Endpoints — SETTLE Domain

Routes for the full resolution lifecycle:
  /settle/demand      — Demand packages, drafts, transmissions
  /settle/negotiation  — Negotiation rounds, offers, counteroffers
  /settle/decision    — Settlement decisions, attorney recommendations
  /settle/agreement   — Settlement agreements, releases
  /settle/lien        — Liens and lien resolutions
  /settle/financial   — Payments, trust ledger, allocations, closings, disbursements
  /settle/closure     — Matter closure and reopening
  /settle/audit       — Audit trail retrieval
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import require_auth
from app.models.settlement import (
    DemandPackageCreate, DemandAuthorizationRequest, DemandTransmitRequest,
    NegotiationRoundCreate, OfferCreate, CounterofferCreate, CounterofferAuthorize,
    SettlementDecisionCreate, AttorneyRecommendationCreate,
    SettlementAgreementCreate, ReleaseCreate, ReleaseReviewRequest,
    LienCreate, LienVerify, LienResolve,
    SettlementPaymentCreate, PaymentReceiveRequest,
    SettlementAllocationCreate, AllocationApproveRequest,
    ClosingStatementCreate,
    DisbursementCreate, DisbursementAuthorize,
    MatterClosureRequest, MatterReopenRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settle", tags=["settlement"])


# ============================================================================
# DEPENDENCIES
# ============================================================================

def _get_tenant_id(request: dict) -> UUID:
    tenant_id = request.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id required")
    return UUID(tenant_id)


# ============================================================================
# DEMAND ENDPOINTS
# ============================================================================

@router.post("/demand/packages", response_model=dict)
async def create_demand_package(
    data: DemandPackageCreate,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.demand import demand_service
    tenant_id = _get_tenant_id(user)
    result = await demand_service.create_demand_package(
        tenant_id=tenant_id,
        data=data,
        created_by=UUID(user.get("user_id")),
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create demand package")
    return result.model_dump()


@router.get("/demand/packages/{package_id}", response_model=dict)
async def get_demand_package(
    package_id: UUID,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.demand import demand_service
    result = await demand_service.get_demand_package(package_id)
    if not result:
        raise HTTPException(status_code=404, detail="Demand package not found")
    return result.model_dump()


@router.get("/demand/matter/{matter_id}/packages", response_model=list)
async def get_matter_demand_packages(
    matter_id: UUID,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.demand import demand_service
    return [p.model_dump() for p in await demand_service.get_demand_packages_by_matter(matter_id)]


@router.post("/demand/packages/{package_id}/authorize", response_model=dict)
async def authorize_demand_package(
    package_id: UUID,
    data: DemandAuthorizationRequest,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.demand import demand_service
    tenant_id = _get_tenant_id(user)
    data.package_id = package_id
    result = await demand_service.authorize_demand(
        tenant_id=tenant_id,
        matter_id=UUID(user.get("matter_id", str(data.authorized_by))),
        request=data,
        actor_role=user.get("role", "attorney"),
    )
    if not result:
        raise HTTPException(status_code=403, detail="Demand authorization denied or failed")
    return result.model_dump()


@router.post("/demand/transmit", response_model=dict)
async def transmit_demand(
    data: DemandTransmitRequest,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.demand import demand_service
    tenant_id = _get_tenant_id(user)
    result = await demand_service.create_demand_transmission(
        tenant_id=tenant_id,
        matter_id=UUID(user.get("matter_id", "")),
        request=data,
        transmitted_by=UUID(user.get("user_id")),
        actor_role=user.get("role", "attorney"),
    )
    if not result:
        raise HTTPException(status_code=403, detail="Demand transmission failed")
    return result.model_dump()


# ============================================================================
# NEGOTIATION ENDPOINTS
# ============================================================================

@router.post("/negotiation/rounds", response_model=dict)
async def create_negotiation_round(
    data: NegotiationRoundCreate,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.negotiation import negotiation_service
    tenant_id = _get_tenant_id(user)
    result = await negotiation_service.create_negotiation_round(
        tenant_id=tenant_id,
        data=data,
        created_by=UUID(user.get("user_id")),
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create negotiation round")
    return result.model_dump()


@router.get("/negotiation/matter/{matter_id}/rounds", response_model=list)
async def get_negotiation_rounds(
    matter_id: UUID,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.negotiation import negotiation_service
    return [r.model_dump() for r in await negotiation_service.get_negotiation_rounds_by_matter(matter_id)]


@router.post("/negotiation/offers", response_model=dict)
async def record_offer(
    data: OfferCreate,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.negotiation import negotiation_service
    tenant_id = _get_tenant_id(user)
    result = await negotiation_service.record_offer(
        tenant_id=tenant_id,
        data=data,
        recorded_by=UUID(user.get("user_id")),
        actor_role=user.get("role", "attorney"),
    )
    if not result:
        raise HTTPException(status_code=403, detail="Offer recording failed")
    return result.model_dump()


@router.get("/negotiation/offers/{offer_id}", response_model=dict)
async def get_offer(
    offer_id: UUID,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.negotiation import negotiation_service
    result = await negotiation_service.get_offer(offer_id)
    if not result:
        raise HTTPException(status_code=404, detail="Offer not found")
    return result.model_dump()


@router.get("/negotiation/matter/{matter_id}/offers", response_model=list)
async def get_matter_offers(
    matter_id: UUID,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.negotiation import negotiation_service
    return [o.model_dump() for o in await negotiation_service.get_offers_by_matter(matter_id)]


@router.post("/negotiation/counteroffers", response_model=dict)
async def create_counteroffer(
    data: CounterofferCreate,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.negotiation import negotiation_service
    tenant_id = _get_tenant_id(user)
    result = await negotiation_service.create_counteroffer(
        tenant_id=tenant_id,
        data=data,
        created_by=UUID(user.get("user_id")),
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create counteroffer")
    return result.model_dump()


@router.post("/negotiation/counteroffers/{counter_id}/authorize", response_model=dict)
async def authorize_counteroffer(
    counter_id: UUID,
    data: CounterofferAuthorize,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.negotiation import negotiation_service
    tenant_id = _get_tenant_id(user)
    data.counteroffer_id = counter_id
    result = await negotiation_service.authorize_counteroffer(
        tenant_id=tenant_id,
        matter_id=UUID(user.get("matter_id", "")),
        data=data,
        actor_role=user.get("role", "client"),
    )
    if not result:
        raise HTTPException(status_code=403, detail="Counteroffer authorization denied")
    return result.model_dump()


# ============================================================================
# DECISION ENDPOINTS
# ============================================================================

@router.post("/decision/recommendations", response_model=dict)
async def create_recommendation(
    data: AttorneyRecommendationCreate,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.decision import decision_service
    tenant_id = _get_tenant_id(user)
    result = await decision_service.create_attorney_recommendation(
        tenant_id=tenant_id,
        matter_id=data.matter_id,
        offer_id=data.offer_id,
        data=data,
        recommended_by=UUID(user.get("user_id")),
        actor_role=user.get("role", "attorney"),
    )
    if not result:
        raise HTTPException(status_code=403, detail="Attorney recommendation creation denied")
    return result.model_dump()


@router.post("/decision/record", response_model=dict)
async def record_settlement_decision(
    data: SettlementDecisionCreate,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.decision import decision_service
    tenant_id = _get_tenant_id(user)
    result = await decision_service.record_settlement_decision(
        tenant_id=tenant_id,
        data=data,
        recorded_by=UUID(user.get("user_id")),
    )
    if not result:
        raise HTTPException(status_code=403, detail="Settlement decision recording denied")
    return result.model_dump()


@router.get("/decision/matter/{matter_id}", response_model=list)
async def get_matter_decisions(
    matter_id: UUID,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.decision import decision_service
    return [d.model_dump() for d in await decision_service.get_decisions_by_matter(matter_id)]


# ============================================================================
# AGREEMENT & RELEASE ENDPOINTS
# ============================================================================

@router.post("/agreement", response_model=dict)
async def create_agreement(
    data: SettlementAgreementCreate,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.agreement import agreement_service
    tenant_id = _get_tenant_id(user)
    result = await agreement_service.create_settlement_agreement(
        tenant_id=tenant_id,
        data=data,
        created_by=UUID(user.get("user_id")),
        actor_role=user.get("role", "attorney"),
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create settlement agreement")
    return result.model_dump()


@router.post("/agreement/{agreement_id}/approve", response_model=dict)
async def approve_agreement(
    agreement_id: UUID,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.agreement import agreement_service
    tenant_id = _get_tenant_id(user)
    result = await agreement_service.approve_agreement(
        agreement_id=agreement_id,
        attorney_id=UUID(user.get("user_id")),
        tenant_id=tenant_id,
        matter_id=UUID(user.get("matter_id", "")),
        actor_role=user.get("role", "attorney"),
    )
    if not result:
        raise HTTPException(status_code=403, detail="Agreement approval denied")
    return result.model_dump()


@router.post("/release", response_model=dict)
async def create_release(
    data: ReleaseCreate,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.agreement import agreement_service
    tenant_id = _get_tenant_id(user)
    result = await agreement_service.create_release(
        tenant_id=tenant_id,
        data=data,
        created_by=UUID(user.get("user_id")),
        actor_role=user.get("role", "attorney"),
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create release")
    return result.model_dump()


@router.post("/release/{release_id}/review", response_model=dict)
async def review_release(
    release_id: UUID,
    data: ReleaseReviewRequest,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.agreement import agreement_service
    tenant_id = _get_tenant_id(user)
    data.release_id = release_id
    result = await agreement_service.attorney_review_release(
        tenant_id=tenant_id,
        matter_id=UUID(user.get("matter_id", "")),
        review=data,
        actor_role=user.get("role", "attorney"),
    )
    if not result:
        raise HTTPException(status_code=403, detail="Release review denied")
    return result.model_dump()


# ============================================================================
# LIEN ENDPOINTS
# ============================================================================

@router.post("/lien", response_model=dict)
async def create_lien(
    data: LienCreate,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.lien import lien_service
    tenant_id = _get_tenant_id(user)
    result = await lien_service.create_lien(
        tenant_id=tenant_id,
        data=data,
        created_by=UUID(user.get("user_id")),
        actor_role=user.get("role", "attorney"),
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create lien")
    return result.model_dump()


@router.post("/lien/{lien_id}/verify", response_model=dict)
async def verify_lien(
    lien_id: UUID,
    data: LienVerify,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.lien import lien_service
    tenant_id = _get_tenant_id(user)
    data.lien_id = lien_id
    result = await lien_service.verify_lien(
        tenant_id=tenant_id,
        matter_id=UUID(user.get("matter_id", "")),
        data=data,
        actor_role=user.get("role", "paralegal"),
    )
    if not result:
        raise HTTPException(status_code=403, detail="Lien verification failed")
    return result.model_dump()


@router.post("/lien/{lien_id}/resolve", response_model=dict)
async def resolve_lien(
    lien_id: UUID,
    data: LienResolve,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.lien import lien_service
    tenant_id = _get_tenant_id(user)
    data.lien_id = lien_id
    result = await lien_service.resolve_lien(
        tenant_id=tenant_id,
        matter_id=UUID(user.get("matter_id", "")),
        data=data,
        actor_role=user.get("role", "attorney"),
    )
    if not result:
        raise HTTPException(status_code=403, detail="Lien resolution denied")
    return result.model_dump()


@router.get("/lien/matter/{matter_id}", response_model=list)
async def get_matter_liens(
    matter_id: UUID,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.lien import lien_service
    return [li.model_dump() for li in await lien_service.get_liens_by_matter(matter_id)]


# ============================================================================
# FINANCIAL ENDPOINTS
# ============================================================================

@router.post("/financial/payments", response_model=dict)
async def create_payment(
    data: SettlementPaymentCreate,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.financial import payment_service
    tenant_id = _get_tenant_id(user)
    result = await payment_service.create_settlement_payment(
        tenant_id=tenant_id,
        data=data,
        created_by=UUID(user.get("user_id")),
        actor_role=user.get("role", "attorney"),
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create payment")
    return result.model_dump()


@router.post("/financial/payments/{payment_id}/receive", response_model=dict)
async def receive_payment(
    payment_id: UUID,
    data: PaymentReceiveRequest,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.financial import payment_service
    tenant_id = _get_tenant_id(user)
    data.payment_id = payment_id
    result = await payment_service.receive_payment(
        tenant_id=tenant_id,
        matter_id=UUID(user.get("matter_id", "")),
        data=data,
        received_by=UUID(user.get("user_id")),
        actor_role=user.get("role", "trust_accounting"),
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to receive payment")
    return result.model_dump()


@router.get("/financial/matter/{matter_id}/ledger", response_model=list)
async def get_trust_ledger(
    matter_id: UUID,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.financial import payment_service
    return await payment_service.get_trust_ledger(matter_id)


@router.get("/financial/matter/{matter_id}/balance", response_model=dict)
async def get_trust_balance(
    matter_id: UUID,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.financial import payment_service
    balance = await payment_service.get_trust_balance(matter_id)
    return {"matter_id": str(matter_id), "trust_balance": balance}


@router.post("/financial/allocations", response_model=dict)
async def create_allocation(
    data: SettlementAllocationCreate,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.financial import allocation_service
    tenant_id = _get_tenant_id(user)
    result = await allocation_service.create_allocation(
        tenant_id=tenant_id,
        data=data,
        created_by=UUID(user.get("user_id")),
        actor_role=user.get("role", "attorney"),
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create allocation")
    return result.model_dump()


@router.post("/financial/allocations/{alloc_id}/approve", response_model=dict)
async def approve_allocation(
    alloc_id: UUID,
    data: AllocationApproveRequest,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.financial import allocation_service
    tenant_id = _get_tenant_id(user)
    data.allocation_id = alloc_id
    result = await allocation_service.approve_allocation(
        tenant_id=tenant_id,
        matter_id=UUID(user.get("matter_id", "")),
        data=data,
        actor_role=user.get("role", "attorney"),
    )
    if not result:
        raise HTTPException(status_code=403, detail="Allocation approval denied")
    return result.model_dump()


@router.post("/financial/closing-statements", response_model=dict)
async def create_closing_statement(
    data: ClosingStatementCreate,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.financial import allocation_service
    tenant_id = _get_tenant_id(user)
    result = await allocation_service.create_closing_statement(
        tenant_id=tenant_id,
        data=data,
        created_by=UUID(user.get("user_id")),
        actor_role=user.get("role", "attorney"),
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create closing statement")
    return result.model_dump()


@router.post("/financial/disbursements", response_model=dict)
async def create_disbursement(
    data: DisbursementCreate,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.financial import allocation_service
    tenant_id = _get_tenant_id(user)
    result = await allocation_service.create_disbursement(
        tenant_id=tenant_id,
        data=data,
        created_by=UUID(user.get("user_id")),
        actor_role=user.get("role", "trust_accounting"),
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create disbursement")
    return result.model_dump()


@router.post("/financial/disbursements/{disb_id}/authorize", response_model=dict)
async def authorize_disbursement(
    disb_id: UUID,
    data: DisbursementAuthorize,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.financial import allocation_service
    tenant_id = _get_tenant_id(user)
    data.disbursement_id = disb_id
    result = await allocation_service.authorize_disbursement(
        tenant_id=tenant_id,
        matter_id=UUID(user.get("matter_id", "")),
        data=data,
        actor_role=user.get("role", "trust_accounting"),
    )
    if not result:
        raise HTTPException(status_code=403, detail="Disbursement authorization denied")
    return result.model_dump()


# ============================================================================
# CLOSURE ENDPOINTS
# ============================================================================

@router.post("/closure/close", response_model=dict)
async def close_matter(
    data: MatterClosureRequest,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.closure import closure_service
    tenant_id = _get_tenant_id(user)
    result = await closure_service.close_matter(
        tenant_id=tenant_id,
        data=data,
        actor_role=user.get("role", "attorney"),
    )
    if not result:
        raise HTTPException(status_code=403, detail="Matter closure denied")
    return result.model_dump()


@router.post("/closure/reopen", response_model=dict)
async def reopen_matter(
    data: MatterReopenRequest,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.closure import closure_service
    tenant_id = _get_tenant_id(user)
    result = await closure_service.reopen_matter(
        tenant_id=tenant_id,
        data=data,
        actor_role=user.get("role", "attorney"),
    )
    if not result:
        raise HTTPException(status_code=403, detail="Matter reopening denied")
    return result.model_dump()


@router.get("/closure/matter/{matter_id}/status", response_model=dict)
async def get_closure_status(
    matter_id: UUID,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.closure import closure_service
    result = await closure_service.get_closure_status(matter_id)
    if not result:
        return {"matter_id": str(matter_id), "state": "active"}
    return result.model_dump()


# ============================================================================
# AUDIT ENDPOINTS
# ============================================================================

@router.get("/audit/matter/{matter_id}/timeline", response_model=list)
async def get_settlement_timeline(
    matter_id: UUID,
    user: dict = Depends(require_auth),
):
    from app.services.settlement.audit import settlement_audit
    return await settlement_audit.get_settlement_timeline(matter_id)


@router.get("/audit/matter/{matter_id}/entity/{entity_type}", response_model=list)
async def get_entity_audit(
    matter_id: UUID,
    entity_type: str,
    entity_id: Optional[UUID] = Query(None),
    user: dict = Depends(require_auth),
):
    from app.services.settlement.audit import settlement_audit
    return await settlement_audit.get_audit_trail(
        matter_id=matter_id,
        entity_type=entity_type,
        entity_id=entity_id,
    )
