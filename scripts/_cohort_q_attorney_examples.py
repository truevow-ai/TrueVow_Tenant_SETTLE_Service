"""
Cohort Q post-push attorney-facing examples.

Hits the live /estimate endpoint with three illustrative scenarios so we can
show Yasha what an attorney sees in each tier (county / state / insufficient).
Outputs JSON-formatted responses so the structure is glanceable.
"""
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

os.environ.setdefault("USE_MOCK_DATA", "true")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.auth import require_any_auth  # noqa: E402


def _bypass_auth():
    return {
        "user_id": "demo-attorney",
        "api_key_id": "demo-key",
        "access_level": "founding_member",
        "is_expired": False,
        "is_revoked": False,
    }


app.dependency_overrides[require_any_auth] = _bypass_auth
client = TestClient(app)

scenarios = [
    {
        "label": "1. FL county WITH data — Miami-Dade MVA TBI (state-tier fallback)",
        "payload": {
            "jurisdiction": "Miami-Dade County, FL",
            "case_type": "Motor Vehicle Accident",
            "injury_category": ["traumatic_brain_injury"],
            "medical_bills": 250000.0,
        },
    },
    {
        "label": "2. Smaller FL county — Broward MVA spinal injury",
        "payload": {
            "jurisdiction": "Broward County, FL",
            "case_type": "Motor Vehicle Accident",
            "injury_category": ["spinal_injury"],
            "medical_bills": 75000.0,
        },
    },
    {
        "label": "3. Out-of-state (no FL data tier) — Maricopa AZ MVA",
        "payload": {
            "jurisdiction": "Maricopa County, AZ",
            "case_type": "Motor Vehicle Accident",
            "injury_category": ["traumatic_brain_injury"],
            "medical_bills": 100000.0,
        },
    },
    {
        "label": "4. Rare case type in FL — premises liability slip-and-fall",
        "payload": {
            "jurisdiction": "Orange County, FL",
            "case_type": "Premises Liability",
            "injury_category": ["soft_tissue"],
            "medical_bills": 30000.0,
        },
    },
]

for s in scenarios:
    print("=" * 78)
    print(s["label"])
    print(f"REQUEST: {json.dumps(s['payload'])}")
    print("=" * 78)
    r = client.post("/api/v1/query/estimate", json=s["payload"])
    print(f"HTTP {r.status_code}")
    try:
        body = r.json()
    except Exception:  # noqa: BLE001
        print(r.text[:400])
        print()
        continue
    summary = {
        "aggregation_level": body.get("aggregation_level"),
        "n_county": body.get("n_county"),
        "n_state": body.get("n_state"),
        "n_cases": body.get("n_cases"),
        "confidence": body.get("confidence"),
        "own_case_only": body.get("own_case_only"),
        "median": body.get("median"),
        "percentile_25": body.get("percentile_25"),
        "percentile_75": body.get("percentile_75"),
        "percentile_95": body.get("percentile_95"),
        "suppressed_features": body.get("suppressed_features"),
    }
    print("SUMMARY:")
    print(json.dumps(summary, default=str, indent=2))
    print("\nJUSTIFICATION (full):")
    print(body.get("range_justification") or "(none)")
    print()
