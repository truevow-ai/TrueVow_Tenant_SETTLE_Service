"""
Query Endpoints - Settlement Range Estimation
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional
import logging

from app.models.case_bank import EstimateRequest, EstimateResponse
from app.services.estimator import SettlementEstimator
from app.services.validator import DataValidator
from app.core.auth import require_any_auth
from app.core.config import settings
from app.core.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_settlement_range(
    request: EstimateRequest,
    http_request: Request,
    auth: dict = Depends(require_any_auth)
):
    """
    Estimate settlement range based on comparable cases.
    
    **Authentication:**
    - Supports API Key (legacy): Authorization: Bearer settle_xxx
    - Supports Clerk JWT: Authorization: Bearer eyJxxx
    - Both methods provide user_id and optional tenant_id for audit
    
    **Algorithm:**
    - Calls IntelligenceGate to verify cohort credibility (Year-2 'Credible
      Aggregation' floor: MIN_AGGREGATE_N=50 approved cases for jurisdiction + case_type).
    - If gate returns `sufficient`: queries comparable cases (state-suffix +
      case_type + injury_category overlap), computes percentiles
      (25th/median/75th/95th), returns full estimate.
    - If gate returns `insufficient_data`: returns suppressed response with
      `own_case_only=true` and aggregate widgets blocked (no multiplier
      fallback — synthesizing ranges from sub-threshold data is the
      anti-pattern this gate exists to prevent).

    **Confidence labels:**
    - `insufficient_data` — gate floor not met.
    - `high` — gate passed AND n >= 30 (production-reachable for all passing
      requests, since gate floor 50 exceeds tier threshold 30).
    - `medium` — gate passed AND n < 30 (only reachable under a lowered gate
      floor for testing; not production-reachable today).
    
    **Returns:**
    - Settlement range with comparable cases
    - Response time <1 second (p95)
    
    **Compliance:**
    - Only descriptive statistics (never predictive)
    - No legal advice or case strategy
    - All data is anonymized
    """
    try:
        # Log authenticated user. Legacy APIKeyAuth returns a dict; use .get()
        # with safe defaults since auth_method/scope/tenant_id are not present
        # on the legacy contract (they were part of the stashed unified-auth work).
        logger.info(
            f"Estimate request from user={auth.get('user_id')}, "
            f"auth_method={auth.get('auth_method', 'api_key')}, "
            f"scope={auth.get('scope', 'user')}, "
            f"tenant_id={auth.get('tenant_id')}"
        )
        
        # Validate query request
        validator = DataValidator()
        request_dict = request.model_dump()
        is_valid, errors = validator.validate_query_request(request_dict)
        
        if not is_valid:
            logger.warning(f"Query validation failed: {errors}")
            raise HTTPException(
                status_code=400,
                detail={"message": "Invalid query parameters", "errors": errors}
            )
        
        # Get database connection
        db = await get_db()
        
        # Initialize estimator service
        estimator = SettlementEstimator(db_connection=db)
        
        # Pilot-mode user identification (ADR S-2 v2 + 2026-05-16 addendum).
        # Source of user_id, in priority order:
        #   1. X-Settle-User-Id header — used when a trusted proxy (e.g., the
        #      customer portal) forwards the end-user's Clerk userId. Honored
        #      ONLY when the auth path is API-key, since the trust model is
        #      "shared X-API-Key gates the proxy" (ADR S-2 addendum). The guard
        #      defaults `auth_method` to "api_key" so today's single-auth-path
        #      behavior is preserved; when JWT auth lands and sets
        #      auth_method="jwt", the guard naturally locks the override out.
        #   2. API-key-owner user_id — legacy/direct-call path.
        # No fallback to `api_key` literal — fail-closed if neither surfaces.
        is_api_key_auth = auth.get("auth_method", "api_key") == "api_key"
        forwarded_user_id = (
            http_request.headers.get("X-Settle-User-Id", "").strip()
            if is_api_key_auth
            else ""
        )
        api_key_owner_id = auth.get("user_id", "") or ""
        user_id = forwarded_user_id or api_key_owner_id

        pilot_user_ids = {
            uid.strip()
            for uid in (settings.SETTLE_PILOT_USER_IDS or "").split(",")
            if uid.strip()
        }
        is_pilot_user = bool(user_id) and str(user_id) in pilot_user_ids
        
        # Calculate settlement range
        response = await estimator.estimate_settlement_range(
            request, is_pilot_user=is_pilot_user,
        )
        
        logger.info(
            f"Settlement range estimated for {request.jurisdiction}: "
            f"median=${response.median:,.0f}, n_cases={response.n_cases}, "
            f"confidence={response.confidence}, response_time={response.response_time_ms}ms"
        )
        
        # NOTE: behavioral-event emission (SettleEventEmitter) was removed in
        # Cohort Q because app.core.event_emitter was parked on the stash
        # branch. Telemetry will be restored when the emitter module is
        # rewritten; the estimator response contract is unaffected.
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error estimating settlement range: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"message": "Internal server error", "error": str(e)}
        )


@router.get("/health")
async def query_service_health():
    """Health check for query service"""
    return {
        "service": "SETTLE Query Service",
        "status": "operational",
        "endpoints": ["/estimate"]
    }

