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
    """
    # Enable mock mode for testing
    os.environ["USE_MOCK_DATA"] = "true"
    
    yield
    
    # Cleanup after tests
    if "USE_MOCK_DATA" in os.environ:
        del os.environ["USE_MOCK_DATA"]


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
