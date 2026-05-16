"""
Functional Tests - End-to-End API Testing

These tests make REAL HTTP requests to the API endpoints.
They verify actual behavior with real data.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.services.intelligence_gate import AggregateGateResult, MIN_AGGREGATE_N

client = TestClient(app)


# Year-2 mandatory v2 fields — every /submit payload must carry these.
_V2_FIELDS = {
    "intake_version_id": "v2",
    "economic_strength_at_intake": "moderate",
    "final_treatment_escalation": "injections",
    "settlement_band": "150k_500k",
    "policy_limit_known": True,
    "time_to_resolution": "12_24_months",
    "litigation_filed": False,
}


@pytest.fixture
def patch_gate_sufficient():
    """
    Patch IntelligenceGate.check to return sufficient — lets the estimator
    run the percentile path against mock cases without needing a live DB.
    """
    stub_result = AggregateGateResult(
        status="sufficient",
        n=120,
        threshold=MIN_AGGREGATE_N,
        own_case_only=False,
        suppressed_features=[],
    )
    with patch(
        "app.services.estimator.IntelligenceGate.check",
        new=AsyncMock(return_value=stub_result),
    ):
        yield


def test_health_endpoint():
    """Test root health endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "TrueVow Settle™ Service"
    assert response.json()["status"] == "operational"


def test_query_estimate_endpoint(auth_headers, patch_gate_sufficient):
    """Test settlement range estimation endpoint"""
    
    request_data = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Auto Accident",
        "injury_category": ["Spinal Injury"],
        "medical_bills": 50000.00
    }
    
    response = client.post("/api/v1/query/estimate", json=request_data, headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "percentile_25" in data
    assert "median" in data
    assert "percentile_75" in data
    assert "percentile_95" in data
    assert "n_cases" in data
    assert "confidence" in data
    assert "comparable_cases" in data
    assert "response_time_ms" in data
    
    # Verify data integrity
    assert data["percentile_25"] < data["median"] < data["percentile_75"] < data["percentile_95"]
    assert data["n_cases"] > 0
    assert data["confidence"] in ["low", "medium", "high"]
    assert data["response_time_ms"] < 1000  # <1 second


def test_query_estimate_validation_error(auth_headers):
    """Test validation error handling"""
    
    # Invalid: missing required fields
    request_data = {
        "case_type": "Auto Accident"
        # Missing jurisdiction, injury_category, medical_bills
    }
    
    response = client.post("/api/v1/query/estimate", json=request_data, headers=auth_headers)
    assert response.status_code == 422  # Validation error


def test_contribution_endpoint(auth_headers):
    """Test settlement contribution endpoint"""
    
    contribution_data = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Motor Vehicle Accident",
        "injury_category": ["Spinal Injury"],
        "primary_diagnosis": "Spinal Injury",
        "treatment_type": ["Physical Therapy", "Surgery"],
        "duration_of_treatment": "6-12 months",
        "imaging_findings": ["Herniated Disc"],
        "medical_bills": 50000.00,
        "lost_wages": 10000.00,
        "policy_limits": "$100k/$300k",
        "defendant_category": "Business",
        "outcome_type": "Settlement",
        "outcome_amount_range": "$300k-$600k",
        "consent_confirmed": True,
        **_V2_FIELDS,
    }
    
    response = client.post(
        "/api/v1/contribute/submit", json=contribution_data, headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "contribution_id" in data
    assert "blockchain_hash" in data
    assert "message" in data
    assert "status" in data
    
    # Verify blockchain hash format
    assert data["blockchain_hash"].startswith("ots_")
    assert data["status"] == "pending"


def test_contribution_validation_error(auth_headers):
    """Test contribution validation error"""
    
    # Invalid: consent not confirmed
    contribution_data = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Motor Vehicle Accident",
        "injury_category": ["Spinal Injury"],
        "treatment_type": ["Physical Therapy"],
        "duration_of_treatment": "6-12 months",
        "imaging_findings": ["Herniated Disc"],
        "medical_bills": 50000.00,
        "defendant_category": "Business",
        "outcome_type": "Settlement",
        "outcome_amount_range": "$300k-$600k",
        "consent_confirmed": False,  # Invalid
        **_V2_FIELDS,
    }
    
    response = client.post(
        "/api/v1/contribute/submit", json=contribution_data, headers=auth_headers
    )
    assert response.status_code == 400  # Validation error


def test_contribution_anonymization_error(auth_headers):
    """Test contribution anonymization check"""
    
    # Invalid: contains PHI (SSN)
    contribution_data = {
        "jurisdiction": "Maricopa County, AZ 123-45-6789",  # SSN in field
        "case_type": "Motor Vehicle Accident",
        "injury_category": ["Spinal Injury"],
        "treatment_type": ["Physical Therapy"],
        "duration_of_treatment": "6-12 months",
        "imaging_findings": ["Herniated Disc"],
        "medical_bills": 50000.00,
        "defendant_category": "Business",
        "outcome_type": "Settlement",
        "outcome_amount_range": "$300k-$600k",
        "consent_confirmed": True,
        **_V2_FIELDS,
    }
    
    response = client.post(
        "/api/v1/contribute/submit", json=contribution_data, headers=auth_headers
    )
    assert response.status_code == 400  # Anonymization error


def test_report_generation_endpoint(auth_headers):
    """Test report generation endpoint"""
    
    report_request = {
        "query_id": "12345678-1234-5678-1234-567812345678",  # Valid UUID
        "format": "json"
    }
    
    response = client.post("/api/v1/reports/generate", json=report_request, headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "report_id" in data
    assert "report_url" in data
    assert "ots_hash" in data
    assert "format" in data
    assert "summary" in data  # JSON format includes summary
    
    # Verify summary structure
    summary = data["summary"]
    assert "case_overview" in summary
    assert "settlement_range" in summary
    assert "comparable_cases_count" in summary
    assert "confidence_level" in summary


def test_report_template_endpoint():
    """Test report template endpoint"""
    
    response = client.get("/api/v1/reports/template")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "template_version" in data
    assert data["pages"] == 4
    assert "structure" in data
    
    # Verify 4-page structure
    structure = data["structure"]
    assert "page_1" in structure
    assert "page_2" in structure
    assert "page_3" in structure
    assert "page_4" in structure


def test_contribution_stats_endpoint():
    """Test contribution statistics endpoint"""
    
    response = client.get("/api/v1/contribute/stats")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "total_contributions" in data
    assert "approved_contributions" in data
    assert "pending_review" in data
    assert "founding_member_contributions" in data
    assert "jurisdictions_covered" in data


def test_service_health_endpoints():
    """Test health check endpoints for all services"""
    
    # Query service
    response = client.get("/api/v1/query/health")
    assert response.status_code == 200
    assert response.json()["service"] == "SETTLE Query Service"
    
    # Contribution service
    response = client.get("/api/v1/contribute/health")
    assert response.status_code == 200
    assert response.json()["service"] == "SETTLE Contribution Service"
    
    # Reports service
    response = client.get("/api/v1/reports/health")
    assert response.status_code == 200
    assert response.json()["service"] == "SETTLE Reports Service"


@pytest.mark.asyncio
async def test_end_to_end_workflow(auth_headers, patch_gate_sufficient):
    """
    Test complete workflow:
    1. Submit contribution
    2. Query settlement range
    3. Generate report
    """
    
    # Step 1: Submit contribution
    contribution_data = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Motor Vehicle Accident",
        "injury_category": ["Spinal Injury"],
        "treatment_type": ["Physical Therapy"],
        "duration_of_treatment": "6-12 months",
        "imaging_findings": ["Herniated Disc"],
        "medical_bills": 50000.00,
        "defendant_category": "Business",
        "outcome_type": "Settlement",
        "outcome_amount_range": "$300k-$600k",
        "consent_confirmed": True,
        **_V2_FIELDS,
    }
    
    response = client.post(
        "/api/v1/contribute/submit", json=contribution_data, headers=auth_headers
    )
    assert response.status_code == 200
    contribution_id = response.json()["contribution_id"]
    
    # Step 2: Query settlement range
    query_data = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Auto Accident",
        "injury_category": ["Spinal Injury"],
        "medical_bills": 50000.00
    }
    
    response = client.post("/api/v1/query/estimate", json=query_data, headers=auth_headers)
    assert response.status_code == 200
    estimate = response.json()
    
    # Step 3: Generate report
    report_data = {
        "query_id": "12345678-1234-5678-1234-567812345678",  # Valid UUID
        "format": "json"
    }
    
    response = client.post("/api/v1/reports/generate", json=report_data, headers=auth_headers)
    assert response.status_code == 200
    report = response.json()
    
    # Verify complete workflow
    assert contribution_id is not None
    assert estimate["n_cases"] > 0
    assert report["report_id"] is not None
    assert report["ots_hash"] is not None


class TestPilotUserIdentification:
    """
    Cohort U-back: X-Settle-User-Id header bridge for proxy-mediated pilot
    identification (ADR S-2 + 2026-05-16 addendum).

    Verifies the endpoint's user_id resolution layer (NOT the gate's pilot
    relaxation logic, which is covered in test_intelligence_gate.py and
    test_estimator.py). The contract under test:
      - When a trusted proxy forwards X-Settle-User-Id and that ID is in
        the SETTLE_PILOT_USER_IDS allowlist, is_pilot_user=True is passed
        downstream.
      - Without the header, the API-key-owner user_id is used (legacy /
        direct-call path).
      - A forwarded ID outside the allowlist resolves to is_pilot_user=False.

    Mock-mode auth (conftest.py + auth.py L172-182) returns user_id=
    "mock_user_123", which serves as the API-key-owner ID for the fallback
    test below.
    """

    _BASE_REQUEST = {
        "jurisdiction": "Maricopa County, AZ",
        "case_type": "Auto Accident",
        "injury_category": ["Spinal Injury"],
        "medical_bills": 50000.00,
    }

    @staticmethod
    def _spy_estimator(captured: dict):
        """
        Build a patch context that spies on the estimator's is_pilot_user
        kwarg without altering its real behavior. Returns the patcher
        and the spy coroutine so callers can compose with `with` blocks.
        """
        from app.services.estimator import SettlementEstimator

        original = SettlementEstimator.estimate_settlement_range

        async def spy(self, request, is_pilot_user: bool = False):
            captured["is_pilot_user"] = is_pilot_user
            return await original(self, request, is_pilot_user=is_pilot_user)

        return patch.object(
            SettlementEstimator, "estimate_settlement_range", spy
        )

    def test_x_settle_user_id_header_overrides_api_key_owner(
        self, auth_headers, monkeypatch, patch_gate_sufficient
    ):
        """Header user in allowlist → is_pilot_user=True passed to estimator."""
        from app.core.config import settings as _settings

        monkeypatch.setattr(_settings, "SETTLE_PILOT_MODE", True)
        monkeypatch.setattr(_settings, "SETTLE_PILOT_USER_IDS", "clerk_user_abc123")

        captured: dict = {}
        with self._spy_estimator(captured):
            response = client.post(
                "/api/v1/query/estimate",
                json=self._BASE_REQUEST,
                headers={
                    **auth_headers,
                    "X-Settle-User-Id": "clerk_user_abc123",
                },
            )

        assert response.status_code == 200
        assert captured["is_pilot_user"] is True

    def test_no_x_settle_user_id_header_falls_back_to_api_key_owner(
        self, auth_headers, monkeypatch, patch_gate_sufficient
    ):
        """
        No forwarded header → API-key-owner user_id is used. In mock mode
        the owner id is "mock_user_123", so allowlisting it yields
        is_pilot_user=True, proving the fallback path works.
        """
        from app.core.config import settings as _settings

        monkeypatch.setattr(_settings, "SETTLE_PILOT_MODE", True)
        monkeypatch.setattr(_settings, "SETTLE_PILOT_USER_IDS", "mock_user_123")

        captured: dict = {}
        with self._spy_estimator(captured):
            response = client.post(
                "/api/v1/query/estimate",
                json=self._BASE_REQUEST,
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert captured["is_pilot_user"] is True

    def test_x_settle_user_id_not_in_allowlist_is_not_pilot(
        self, auth_headers, monkeypatch, patch_gate_sufficient
    ):
        """
        Forwarded ID outside allowlist → is_pilot_user=False even though
        SETTLE_PILOT_MODE is on. Confirms the override does not auto-grant
        pilot status; allowlist membership remains the gate.
        """
        from app.core.config import settings as _settings

        monkeypatch.setattr(_settings, "SETTLE_PILOT_MODE", True)
        monkeypatch.setattr(_settings, "SETTLE_PILOT_USER_IDS", "clerk_user_abc123")

        captured: dict = {}
        with self._spy_estimator(captured):
            response = client.post(
                "/api/v1/query/estimate",
                json=self._BASE_REQUEST,
                headers={
                    **auth_headers,
                    "X-Settle-User-Id": "clerk_user_NOT_IN_ALLOWLIST",
                },
            )

        assert response.status_code == 200
        assert captured["is_pilot_user"] is False
