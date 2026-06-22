"""
DOCKET-Service — Litigation Tracker
FastAPI application for court docket and litigation tracking.
Separate from SETTLE — public record data (names/PII permissible).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # Startup
    print("DOCKET-Service starting up...")
    yield
    # Shutdown
    print("DOCKET-Service shutting down...")


app = FastAPI(
    title="DOCKET-Service",
    description="Court docket and litigation tracking service. Public record data.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "service": "DOCKET-Service",
        "version": "1.0.0",
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "docket",
    }
