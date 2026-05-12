"""
Query Endpoints - Settlement Range Estimation
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import logging

from app.models.case_bank import EstimateRequest, EstimateResponse
from app.services.estimator import SettlementEstimator
from app.services.validator import DataValidator
from app.core.auth import require_any_auth, require_unified_auth, AuthContext
from app.core.database import get_db
from app.core.event_emitter import SettleEventEmitter

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_settlement_range(
    request: EstimateRequest,
    auth: AuthContext = Depends(require_unified_auth)
):
    """
    Estimate settlement range based on comparable cases.
    
    **Authentication:**
    - Supports API Key (legacy): Authorization: Bearer settle_xxx
    - Supports Clerk JWT: Authorization: Bearer eyJxxx
    - Both methods provide user_id and optional tenant_id for audit
    
    **Algorithm:**
    - Queries database for comparable cases (jurisdiction, case type, injury)
    - If >= 15 cases: Uses percentile calculation (25th, median, 75th, 95th)
    - If < 15 cases: Uses multiplier fallback (medical bills * industry multipliers)
    - Assigns confidence level: high (30+), medium (15-29), low (<15)
    
    **Returns:**
    - Settlement range with comparable cases
    - Response time <1 second (p95)
    
    **Compliance:**
    - Only descriptive statistics (never predictive)
    - No legal advice or case strategy
    - All data is anonymized
    """
    try:
        # Log authenticated user (supports both API Key and Clerk JWT)
        logger.info(
            f"Estimate request from user={auth.user_id}, "
            f"auth_method={auth.auth_method}, "
            f"scope={auth.scope}, "
            f"tenant_id={auth.tenant_id}"
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
        
        # Calculate settlement range
        response = await estimator.estimate_settlement_range(request)
        
        logger.info(
            f"Settlement range estimated for {request.jurisdiction}: "
            f"median=${response.median:,.0f}, n_cases={response.n_cases}, "
            f"confidence={response.confidence}, response_time={response.response_time_ms}ms"
        )
        
        # ── Behavioral event ─────────────────────────────────────────────────
        emitter = SettleEventEmitter(
            tenant_id=getattr(auth, "tenant_id", None),
            user_id=getattr(auth, "user_id", None),
        )
        import asyncio
        asyncio.ensure_future(emitter.emit(
            "settlement_query_run",
            metadata={
                "jurisdiction": request.jurisdiction,
                "confidence": response.confidence,
                "n_cases": response.n_cases,
            },
        ))
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

