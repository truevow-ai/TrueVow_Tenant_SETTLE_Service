"""Stage 2.3c.a \u2014 Suppressed-path direct estimator smoke.

Target pair: ('Miami-Dade County, FL', 'Motor Vehicle Accident'), n=13.
Gate should fire (13 < MIN_AGGREGATE_N=50), estimator should short-circuit
to own-case-only BEFORE calling _query_comparable_cases.

Validates:
  * Gate contract is honored end-to-end (count round-trips from gate to response)
  * EstimateResponse shape is correct for insufficient_data
  * Full short-circuit: _query_comparable_cases is NOT invoked
  * All 7 dashboard widgets are marked suppressed
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))


class _Tee:
    """Duplicate stdout/stderr to a UTF-8 log file from inside the script.

    Avoids PowerShell pipe/redirection flakes observed in this session.
    """

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


LOG_PATH = SERVICE_ROOT / "logs" / "phase2x_ca_suppressed_smoke.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
_log_fh = LOG_PATH.open("w", encoding="utf-8")
sys.stdout = _Tee(sys.__stdout__, _log_fh)
sys.stderr = _Tee(sys.__stderr__, _log_fh)

from app.core.config import settings  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.models.case_bank import EstimateRequest  # noqa: E402
from app.services.estimator import SettlementEstimator  # noqa: E402


def main() -> int:
    print("=" * 72)
    print("Stage 2.3c.a \u2014 Suppressed-path direct estimator smoke")
    print("=" * 72)

    orig_use_mock = settings.USE_MOCK_DATA
    orig_settle_use_mock = settings.SETTLE_USE_MOCK_DATA
    print(f"[env] original USE_MOCK_DATA={orig_use_mock}, "
          f"SETTLE_USE_MOCK_DATA={orig_settle_use_mock}")

    exit_code = 2

    try:
        settings.USE_MOCK_DATA = False
        settings.SETTLE_USE_MOCK_DATA = False
        print(f"[env] forced USE_MOCK_DATA=False, SETTLE_USE_MOCK_DATA=False, "
              f"use_mock_data(property)={settings.use_mock_data}")

        db = asyncio.run(get_db())
        assert db is not None, "get_db() returned None \u2014 cannot probe"
        print(f"[boot] db type = {type(db).__name__}")

        # Build the suppressed-path test request.
        request = EstimateRequest(
            jurisdiction="Miami-Dade County, FL",
            case_type="Motor Vehicle Accident",
            injury_category=["traumatic_brain_injury"],
            medical_bills=10000.0,
        )
        print(f"[request] jurisdiction={request.jurisdiction!r}")
        print(f"[request] case_type={request.case_type!r}")
        print(f"[request] injury_category={request.injury_category}")
        print(f"[request] medical_bills={request.medical_bills}")

        # Construct estimator with production gate (NO injection).
        estimator = SettlementEstimator(db_connection=db)
        print(f"[estimator] type = {type(estimator).__name__}")
        print(f"[estimator] gate type = {type(estimator.gate).__name__}")

        # Spy on _query_comparable_cases to verify the gate short-circuits.
        call_log = {"count": 0}
        original_query = estimator._query_comparable_cases

        async def _spy(req):
            call_log["count"] += 1
            return await original_query(req)

        estimator._query_comparable_cases = _spy
        print("[spy] installed on estimator._query_comparable_cases")

        # Run the full estimator.
        print("\n[run] calling estimator.estimate_settlement_range(request)...")
        result = asyncio.run(estimator.estimate_settlement_range(request))

        # Print the full result shape.
        print("\n" + "-" * 72)
        print("[result] inspection")
        print("-" * 72)
        print(f"[result] type = {type(result).__name__}")
        print(f"[result] confidence = {result.confidence!r}")
        print(f"[result] own_case_only = {result.own_case_only}")
        print(f"[result] n_cases = {result.n_cases}")
        print(
            f"[result] percentile_25/median/75/95 = "
            f"{result.percentile_25}/{result.median}/"
            f"{result.percentile_75}/{result.percentile_95}"
        )
        print(
            f"[result] suppressed_features count = "
            f"{len(result.suppressed_features)}"
        )
        print(f"[result] suppressed_features = {result.suppressed_features}")
        print(
            f"[result] comparable_cases len = {len(result.comparable_cases)}"
        )
        print(f"[result] range_justification = {result.range_justification!r}")
        print(f"[result] response_time_ms = {result.response_time_ms}")
        print(f"[spy] _query_comparable_cases call count = {call_log['count']}")

        # Assertions \u2014 collect all, don't crash on first failure.
        assertions = [
            (
                "confidence == 'insufficient_data'",
                result.confidence == "insufficient_data",
            ),
            ("own_case_only is True", result.own_case_only is True),
            ("percentile_25 == 0.0", result.percentile_25 == 0.0),
            ("median == 0.0", result.median == 0.0),
            ("percentile_75 == 0.0", result.percentile_75 == 0.0),
            ("percentile_95 == 0.0", result.percentile_95 == 0.0),
            (
                "n_cases is non-negative integer",
                isinstance(result.n_cases, int) and result.n_cases >= 0,
            ),
            (
                "n_cases matches enumeration ground truth (13)",
                result.n_cases == 13,
            ),
            (
                "suppressed_features has 7 items",
                len(result.suppressed_features) == 7,
            ),
            (
                "'percentile_ranges' in suppressed_features",
                "percentile_ranges" in result.suppressed_features,
            ),
            (
                "comparable_cases is empty list",
                result.comparable_cases == [],
            ),
            (
                "range_justification mentions 'Insufficient approved data'",
                result.range_justification is not None
                and "Insufficient approved data" in result.range_justification,
            ),
            (
                "range_justification mentions jurisdiction",
                result.range_justification is not None
                and "Miami-Dade County, FL" in result.range_justification,
            ),
            (
                "_query_comparable_cases NOT called (gate short-circuit)",
                call_log["count"] == 0,
            ),
            (
                "response_time_ms is positive int",
                isinstance(result.response_time_ms, int)
                and result.response_time_ms >= 0,
            ),
        ]

        passed = sum(1 for _, ok in assertions if ok)
        total = len(assertions)
        print(f"\n[assertions] {passed}/{total} passed")
        for label, ok in assertions:
            print(f"  [{'PASS' if ok else 'FAIL'}] {label}")

        print()
        print("=" * 72)
        if passed == total:
            verdict = "SUPPRESSED: PASS"
            exit_code = 0
        else:
            verdict = (
                f"SUPPRESSED: FAIL ({total - passed} assertions failed)"
            )
            exit_code = 1
        print(verdict)

    except Exception as exc:
        print(f"\n[error] probe crashed: {type(exc).__name__}: {exc}")
        import traceback
        traceback.print_exc()
        exit_code = 3

    finally:
        settings.USE_MOCK_DATA = orig_use_mock
        settings.SETTLE_USE_MOCK_DATA = orig_settle_use_mock
        print(f"[env] restored USE_MOCK_DATA={orig_use_mock}, "
              f"SETTLE_USE_MOCK_DATA={orig_settle_use_mock}")
        print("=" * 72)
        print(f"Stage 2.3c.a exit_code={exit_code}")
        print("=" * 72)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
