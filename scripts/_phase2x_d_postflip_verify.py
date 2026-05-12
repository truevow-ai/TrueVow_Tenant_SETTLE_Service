"""
Stage 2.3d.B — Post-flip verification probe.

Purpose:
  Verify that .env.local's SETTLE_USE_MOCK_DATA=false flows through to
  settings.use_mock_data at runtime, and that BOTH gate paths still produce
  correct responses WITHOUT any programmatic mock-mode override. Prior probes
  (2.3c.a / 2.3c.b) force-mutated the attribute in code; this probe does NOT.

Three checks:
  1) Suppressed path   — direct SettlementEstimator, no gate injection
                         (gate fires, n_cases=13, own_case_only=True)
  2) Happy path        — direct SettlementEstimator with PermissiveGate(MIN=1)
                         (gate passes, query runs, >=1 comparable case returned)
  3) FastAPI layer     — TestClient POST /api/v1/query/estimate with
                         auth dependency_overrides bypass (route + shape verify)

Verdict: POSTFLIP: PASS | POSTFLIP: PARTIAL
Run:    python scripts/_phase2x_d_postflip_verify.py
Log:    logs/phase2x_d_postflip_verify.log (self-teed UTF-8)
"""
from __future__ import annotations

import asyncio
import sys
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# sys.path wiring — add SETTLE service root so `from app...` imports resolve
# ---------------------------------------------------------------------------
SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

# ---------------------------------------------------------------------------
# Self-tee — duplicate stdout/stderr to a UTF-8 log. Standard pattern this
# session; bypasses PowerShell Tee-Object / pipe flakes.
# ---------------------------------------------------------------------------
LOG_PATH = SERVICE_ROOT / "logs" / "phase2x_d_postflip_verify.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class _Tee:
    def __init__(self, *streams):
        self._streams = streams

    def write(self, data):
        for s in self._streams:
            try:
                s.write(data)
                s.flush()
            except Exception:
                pass

    def flush(self):
        for s in self._streams:
            try:
                s.flush()
            except Exception:
                pass


_log_fh = LOG_PATH.open("w", encoding="utf-8")
sys.stdout = _Tee(sys.__stdout__, _log_fh)
sys.stderr = _Tee(sys.__stderr__, _log_fh)

print("=" * 72)
print("Stage 2.3d.B — POST-FLIP VERIFICATION PROBE")
print("=" * 72)

# ---------------------------------------------------------------------------
# BOOT BLOCK — verify .env.local flowed through to settings.use_mock_data
# CRITICAL: do NOT mutate settings.USE_MOCK_DATA / SETTLE_USE_MOCK_DATA anywhere
# ---------------------------------------------------------------------------
try:
    from app.core.config import settings

    boot_use_mock_property = settings.use_mock_data
    boot_use_mock_attr = getattr(settings, "USE_MOCK_DATA", "<MISSING>")
    boot_settle_attr = getattr(settings, "SETTLE_USE_MOCK_DATA", "<MISSING>")

    print(f"[boot] settings.use_mock_data (property) = {boot_use_mock_property}")
    print(f"[boot] settings.USE_MOCK_DATA attr        = {boot_use_mock_attr}")
    print(f"[boot] settings.SETTLE_USE_MOCK_DATA attr = {boot_settle_attr}")

    assert boot_use_mock_property is False, (
        f"FAIL: settings.use_mock_data is {boot_use_mock_property!r}, "
        f"expected False. The .env.local edit may not have taken effect. "
        f"Verify the file is at the SETTLE service root and the line is "
        f"SETTLE_USE_MOCK_DATA=false (no quotes, no spaces around =)."
    )
    print("[boot] settings.use_mock_data confirmed False — env.local flowed through correctly")
except Exception as exc:
    print(f"[boot] FAIL: {exc}")
    traceback.print_exc()
    print("\nPOSTFLIP: PARTIAL — boot check failed, cannot proceed")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Shared imports for the three checks
# ---------------------------------------------------------------------------
from app.core.database import get_db
from app.models.case_bank import EstimateRequest, EstimateResponse, ComparableCase
from app.services.estimator import SettlementEstimator
from app.services.intelligence_gate import IntelligenceGate

# ---------------------------------------------------------------------------
# Canonical request (same shape as 2.3c.a / 2.3c.b)
# ---------------------------------------------------------------------------
CANONICAL_REQUEST = EstimateRequest(
    jurisdiction="Miami-Dade County, FL",
    case_type="Motor Vehicle Accident",
    injury_category=["traumatic_brain_injury"],
    medical_bills=10000.0,
)


# ---------------------------------------------------------------------------
# CHECK 1 — suppressed path (direct estimator, default gate)
# ---------------------------------------------------------------------------
def run_check_suppressed() -> tuple[bool, dict]:
    print("\n" + "-" * 72)
    print("[check 1/3] SUPPRESSED PATH — default IntelligenceGate, no injection")
    print("-" * 72)
    try:
        db = asyncio.run(get_db())
        if db is None:
            return False, {"error": "get_db() returned None after .env.local flip"}

        estimator = SettlementEstimator(db_connection=db)
        result = asyncio.run(estimator.estimate_settlement_range(CANONICAL_REQUEST))

        print(f"[suppressed] confidence     = {result.confidence}")
        print(f"[suppressed] own_case_only  = {result.own_case_only}")
        print(f"[suppressed] n_cases        = {result.n_cases}")
        print(f"[suppressed] len(comparable_cases) = {len(result.comparable_cases)}")
        print(f"[suppressed] response_time_ms      = {result.response_time_ms}")

        passed = (
            result.confidence == "insufficient_data"
            and result.own_case_only is True
            and result.n_cases == 13
            and len(result.comparable_cases) == 0
        )
        print(f"[suppressed] result: {'PASS' if passed else 'FAIL'}")
        return passed, {
            "confidence": result.confidence,
            "own_case_only": result.own_case_only,
            "n_cases": result.n_cases,
        }
    except Exception as exc:
        print(f"[suppressed] EXCEPTION: {exc}")
        traceback.print_exc()
        return False, {"error": str(exc)}


# ---------------------------------------------------------------------------
# CHECK 2 — happy path (direct estimator, PermissiveGate injection)
# ---------------------------------------------------------------------------
class PermissiveGate(IntelligenceGate):
    """TEST-ONLY subclass; lowers MIN_AGGREGATE_N to exercise the happy path
    against the current approved-row population. PROD must NEVER use this."""
    MIN_AGGREGATE_N = 1


def run_check_happy() -> tuple[bool, dict]:
    print("\n" + "-" * 72)
    print("[check 2/3] HAPPY PATH — PermissiveGate(MIN_AGGREGATE_N=1) injection")
    print("-" * 72)
    try:
        db = asyncio.run(get_db())
        if db is None:
            return False, {"error": "get_db() returned None"}

        permissive = PermissiveGate(db_connection=db)
        estimator = SettlementEstimator(db_connection=db, gate=permissive)
        result = asyncio.run(estimator.estimate_settlement_range(CANONICAL_REQUEST))

        print(f"[happy] confidence        = {result.confidence}")
        print(f"[happy] own_case_only     = {result.own_case_only}")
        print(f"[happy] n_cases           = {result.n_cases}")
        print(f"[happy] len(comparable_cases) = {len(result.comparable_cases)}")
        print(f"[happy] percentile_25     = {result.percentile_25}")
        print(f"[happy] median            = {result.median}")
        print(f"[happy] percentile_75     = {result.percentile_75}")
        print(f"[happy] response_time_ms  = {result.response_time_ms}")

        # Verify all comparable_cases are real response-model objects (not mock dicts)
        all_real = all(isinstance(c, ComparableCase) for c in result.comparable_cases)

        passed = (
            result.confidence in {"low", "medium", "high"}
            and result.own_case_only is False
            and len(result.comparable_cases) >= 1
            and result.percentile_25 > 0
            and all_real
        )
        print(f"[happy] all cases are ComparableCase instances: {all_real}")
        print(f"[happy] result: {'PASS' if passed else 'FAIL'}")
        return passed, {
            "confidence": result.confidence,
            "n_cases": result.n_cases,
            "len_cases": len(result.comparable_cases),
        }
    except Exception as exc:
        print(f"[happy] EXCEPTION: {exc}")
        traceback.print_exc()
        return False, {"error": str(exc)}


# ---------------------------------------------------------------------------
# CHECK 3 — FastAPI endpoint layer (TestClient, auth bypass via override)
# ---------------------------------------------------------------------------
def run_check_api() -> tuple[bool, dict]:
    print("\n" + "-" * 72)
    print("[check 3/3] FASTAPI LAYER — TestClient POST /api/v1/query/estimate")
    print("-" * 72)
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        from app.core.auth import require_unified_auth, AuthContext

        # Override auth dep — we're verifying routing + shape, NOT auth layer.
        # The auth layer has its own dedicated tests.
        def _bypass_auth() -> AuthContext:
            return AuthContext(
                auth_method="api_key",
                user_id="postflip-probe-user",
                tenant_id="postflip-probe-tenant",
                access_level="admin",
                scope="read write",
                email=None,
                org_id=None,
            )

        app.dependency_overrides[require_unified_auth] = _bypass_auth
        try:
            client = TestClient(app)
            payload = {
                "jurisdiction": "Miami-Dade County, FL",
                "case_type": "Motor Vehicle Accident",
                "injury_category": ["traumatic_brain_injury"],
                "medical_bills": 10000.0,
            }
            response = client.post("/api/v1/query/estimate", json=payload)

            print(f"[api] status_code = {response.status_code}")
            if response.status_code == 200:
                body = response.json()
                print(f"[api] body keys   = {sorted(body.keys())}")
                print(f"[api] confidence  = {body.get('confidence')}")
                print(f"[api] n_cases     = {body.get('n_cases')}")
                print(f"[api] own_case_only = {body.get('own_case_only')}")
                print(f"[api] len(comparable_cases) = "
                      f"{len(body.get('comparable_cases') or [])}")
                passed = body.get("confidence") in {
                    "insufficient_data", "low", "medium", "high"
                }
                # Endpoint uses default gate, so expect insufficient_data
                print(f"[api] result: {'PASS' if passed else 'FAIL'}")
                return passed, {"status": response.status_code,
                                 "confidence": body.get("confidence")}
            else:
                print(f"[api] body preview = {response.text[:400]}")
                print("[api] result: FAIL")
                return False, {"status": response.status_code,
                                "body": response.text[:400]}
        finally:
            # Clean up dependency override no matter what
            app.dependency_overrides.pop(require_unified_auth, None)
    except Exception as exc:
        print(f"[api] EXCEPTION: {exc}")
        traceback.print_exc()
        return False, {"error": str(exc)}


# ---------------------------------------------------------------------------
# Run all three + emit verdict
# ---------------------------------------------------------------------------
supp_pass, supp_info = run_check_suppressed()
happy_pass, happy_info = run_check_happy()
api_pass, api_info = run_check_api()

print("\n" + "=" * 72)
print("POST-FLIP VERIFICATION SUMMARY")
print("=" * 72)
print(f"  suppressed path : {'PASS' if supp_pass else 'FAIL'}  {supp_info}")
print(f"  happy path      : {'PASS' if happy_pass else 'FAIL'}  {happy_info}")
print(f"  fastapi layer   : {'PASS' if api_pass else 'FAIL'}  {api_info}")
print("-" * 72)

if supp_pass and happy_pass and api_pass:
    print("\nPOSTFLIP: PASS — mock mode flipped successfully, all three paths verified")
else:
    print(f"\nPOSTFLIP: PARTIAL — supp={supp_pass}, happy={happy_pass}, api={api_pass}")

print(f"\n[log written] {LOG_PATH}")
