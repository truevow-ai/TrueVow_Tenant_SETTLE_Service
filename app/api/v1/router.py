"""
API Router for SETTLE Service
"""

from fastapi import APIRouter
from app.api.v1.endpoints import query, contribute, reports, admin, waitlist, stats, verdicts, carrier_analytics, trend_reports, override_tracking

api_router = APIRouter()

# Public endpoints
api_router.include_router(waitlist.router, prefix="/waitlist", tags=["waitlist"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])

# Authenticated endpoints
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(contribute.router, prefix="/contribute", tags=["contribute"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(carrier_analytics.router, tags=["analytics"])
api_router.include_router(trend_reports.router, prefix="/trends", tags=["trends"])

# Admin endpoints (for SaaS Admin platform)
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(override_tracking.router, tags=["admin-overrides"])

# Internal endpoints (admin-only, not customer-facing)
api_router.include_router(verdicts.router, prefix="/internal", tags=["internal"])

