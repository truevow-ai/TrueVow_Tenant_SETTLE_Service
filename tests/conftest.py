"""
Pytest configuration for SETTLE Service tests
"""

import pytest
import os


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up test environment variables.
    This runs once per test session.

    NOTE (Cohort U-back, 2026-05-16): the env-var assignment alone is not
    enough — `app.core.config.settings` is a Pydantic BaseSettings instance
    instantiated at module import time, BEFORE this fixture runs. The
    `settings.USE_MOCK_DATA` field is therefore frozen to whatever .env.local
    supplied at import (currently `false` via SETTLE_USE_MOCK_DATA). We must
    also patch the live settings object so `app.core.auth` (which reads
    `settings.USE_MOCK_DATA` directly, not the property) takes the mock path.
    """
    # Enable mock mode for testing (env var — retained for any direct
    # `os.environ` lookups elsewhere in the code path).
    os.environ["USE_MOCK_DATA"] = "true"

    # Patch the live settings singleton so module-level imports of
    # `settings.USE_MOCK_DATA` see the mock-mode value. Snapshot prior
    # values so the cleanup phase can restore them faithfully.
    from app.core.config import settings
    _prior_use_mock_data = settings.USE_MOCK_DATA
    _prior_settle_use_mock_data = settings.SETTLE_USE_MOCK_DATA
    settings.USE_MOCK_DATA = True
    settings.SETTLE_USE_MOCK_DATA = True

    yield

    # Cleanup after tests
    if "USE_MOCK_DATA" in os.environ:
        del os.environ["USE_MOCK_DATA"]
    settings.USE_MOCK_DATA = _prior_use_mock_data
    settings.SETTLE_USE_MOCK_DATA = _prior_settle_use_mock_data


@pytest.fixture
def auth_headers():
    """
    Provide authentication headers for testing.
    In mock mode, any API key is accepted.
    """
    return {
        "Authorization": "Bearer settle_test_key_12345"
    }


@pytest.fixture
def admin_auth_headers():
    """
    Provide admin authentication headers for testing.
    """
    return {
        "Authorization": "Bearer settle_admin_test_key_67890"
    }
