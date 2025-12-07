"""
API Router for SETTLE Service
"""

from fastapi import APIRouter
from app.api.v1.endpoints import query, contribute, reports, admin

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(contribute.router, prefix="/contribute", tags=["contribute"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])

# Admin endpoints (for SaaS Admin platform)
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

