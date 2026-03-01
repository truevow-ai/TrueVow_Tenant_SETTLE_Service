"""
TrueVow Settle™ Service - Main FastAPI Application

Centralized settlement intelligence service for plaintiff attorneys.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.monitoring import initialize_sentry

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Sentry monitoring (Phase 2)
if settings.ENVIRONMENT in ["staging", "production"]:
    initialize_sentry(
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 0.5,
        profiles_sample_rate=0.1
    )
    logger.info("Sentry monitoring initialized")
else:
    logger.info("Sentry monitoring disabled for development")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info("SETTLE Service starting up...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Documentation: http://localhost:8002/docs")
    yield
    # Shutdown
    logger.info("SETTLE Service shutting down...")


app = FastAPI(
    title="TrueVow Settle™ Service",
    description="Settlement intelligence service for plaintiff attorneys",
    version="1.0.0 (Phase 2)",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "TrueVow Settle™ Service",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "environment": settings.environment
    }
