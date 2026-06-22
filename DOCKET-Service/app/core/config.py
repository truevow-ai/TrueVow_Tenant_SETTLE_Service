"""
DOCKET-Service Configuration
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """DOCKET-Service settings."""

    model_config = ConfigDict(env_prefix="DOCKET_", env_file=".env")

    # Service
    SERVICE_NAME: str = "docket"
    DEBUG: bool = False

    # Database (Supabase)
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]

    # CourtListener API
    COURT_LISTENER_API_KEY: str = ""
    COURT_LISTENER_BASE_URL: str = "https://www.courtlistener.com/api/rest/v4"

    # PACER
    PACER_USERNAME: str = ""
    PACER_PASSWORD: str = ""

    # Scraping
    SCRAPE_INTERVAL_HOURS: int = 24
    MAX_CONCURRENT_SCRAPES: int = 5


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
