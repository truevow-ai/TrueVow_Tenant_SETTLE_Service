"""
DOCKET-Service API Router
"""

from fastapi import APIRouter
from app.api.v1.endpoints import dockets

api_router = APIRouter()
api_router.include_router(dockets.router, prefix="/dockets", tags=["dockets"])
