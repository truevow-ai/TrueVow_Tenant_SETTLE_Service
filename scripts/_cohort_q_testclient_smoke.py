"""
Cohort Q TestClient smoke — verifies /api/v1/query/estimate returns a
hierarchical-gate response after the auth + event_emitter fixes.

Standalone script (not a pytest test) so it can be run one-shot and piped
to a log file. Uses dependency_overrides to bypass auth (same pattern as
Stage 2.3d.B postflip verify).
"""
import json
import os
import sys

# Make sure we're running from repo root so `app.*` imports resolve.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Ensure mock mode so the test doesn't hit Supabase.
os.environ.setdefault("USE_MOCK_DATA", "true")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.auth import require_any_auth  # noqa: E402


def _bypass_auth():
    """Match the dict shape returned by legacy APIKeyAuth."""
    return {
        "user_id": "smoke-test",
        "api_key_id": "smoke-key",
        "access_level": "admin",
        "is_expired": False,
        "is_revoked": False,
    }


app.dependency_overrides[require_any_auth] = _bypass_auth

client = TestClient(app)

payload = {
    "jurisdiction": "Miami-Dade County, FL",
    "case_type": "Motor Vehicle Accident",
    "injury_category": ["traumatic_brain_injury"],
    "medical_bills": 10000.0,
}

response = client.post("/api/v1/query/estimate", json=payload)

print(f"status: {response.status_code}")
try:
    body = response.json()
except Exception as exc:  # noqa: BLE001
    print(f"JSON decode failed: {exc}")
    print(f"raw body (first 500 chars): {response.text[:500]}")
    sys.exit(2)

print(f"aggregation_level: {body.get('aggregation_level')!r}")
print(f"n_county:          {body.get('n_county')!r}")
print(f"n_state:           {body.get('n_state')!r}")
print(f"n_cases:           {body.get('n_cases')!r}")
print(f"confidence:        {body.get('confidence')!r}")
print(f"own_case_only:     {body.get('own_case_only')!r}")
print(f"median:            {body.get('median')!r}")
print(
    "justification snippet: "
    + repr((body.get("range_justification") or "")[:240])
)

# Full body also dumped for architect evidence (truncated keys).
print("\n--- FULL BODY (pretty) ---")
print(json.dumps(body, default=str, indent=2)[:2000])
