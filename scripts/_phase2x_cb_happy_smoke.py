"""Stage 2.3c.b \u2014 Happy-path direct estimator smoke (injected permissive gate).

Target pair: ('Miami-Dade County, FL', 'Motor Vehicle Accident'), n=13.
Permissive gate lowers MIN_AGGREGATE_N to 1 so the production code path
runs end-to-end without gate suppression.

Validates:
  * Gate check passes (permissive); _query_comparable_cases IS invoked
  * State parse from jurisdiction works ('Miami-Dade County, FL' -> 'FL')
  * ilike('%, FL') + cs(injury_category) + status=approved all functional
  * SettleContribution rows convert to ComparableCase via
    _select_representative_cases
  * Percentile computation produces monotonic, positive values
  * _generate_mock_cases is NOT invoked (real DB path exercised)
"""
from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))


class _Tee:
    """Duplicate stdout/stderr to UTF-8 log file from inside script."""

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


LOG_PATH = SERVICE_ROOT / "logs" / "phase2x_cb_happy_smoke.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
_log_fh = LOG_PATH.open("w", encoding="utf-8")
sys.stdout = _Tee(sys.__stdout__, _log_fh)
sys.stderr = _Tee(sys.__stderr__, _log_fh)

from app.core.config import settings  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.models.case_bank import ComparableCase, EstimateRequest  # noqa: E402
from app.services.estimator import SettlementEstimator  # noqa: E402
from app.services.intelligence_gate import IntelligenceGate  # noqa: E402


class PermissiveGate(IntelligenceGate):
    """TEST-ONLY subclass that lowers MIN_AGGREGATE_N to 1 so happy-path
    tests can run against the current limited approved-row population.

    PRODUCTION must NEVER use this \u2014 it bypasses the Year-2 credibility floor.
    """
    MIN_AGGREGATE_N = 1


def main() -> int:
    print("=" * 72)
    print("Stage 2.3c.b \u2014 Happy-path direct estimator smoke")
    print("=" * 72)

    # Transparency note: two assertions from the architect's spec were
    # stale against the actual response-model shape. Applying the Case-4
    # self-correction pattern:
    #   (a) 'each case has a UUID id' \u2014 dropped. ComparableCase has no id
    #       field (verified via app/models/case_bank.py lines 95-107). The
    #       underlying truth being asserted (cases are DB-shaped, not mock
    #       dicts) is preserved via isinstance(c, ComparableCase).
    #   (b) 'case.outcome_amount_range' \u2014 renamed to 'outcome_range'.
    #       outcome_amount_range exists on the internal SettleContribution
    #       model; ComparableCase (the response-model) exposes it as
    #       outcome_range (case_bank.py line 105).
    # Flagged to architect in the post-run report.
    print("[note] response-model field fix-up applied per Case-4 "
          "self-correction pattern; see assertion block")

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

        # Happy-path request.
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

        # Injected permissive gate \u2014 bypass credibility floor for test.
        permissive = PermissiveGate(db_connection=db)
        estimator = SettlementEstimator(db_connection=db, gate=permissive)
        print(f"[init] estimator type = {type(estimator).__name__}")
        print(f"[init] estimator gate class = {type(estimator.gate).__name__}")
        print(f"[init] gate.MIN_AGGREGATE_N = {estimator.gate.MIN_AGGREGATE_N}")

        # Spy 1: _query_comparable_cases (async).
        query_log = {"count": 0}
        original_query = estimator._query_comparable_cases

        async def _query_spy(req):
            query_log["count"] += 1
            return await original_query(req)

        estimator._query_comparable_cases = _query_spy

        # Spy 2: _generate_mock_cases. Probe its signature \u2014 it MAY be sync
        # or async. Factual: source shows `def _generate_mock_cases(...)`
        # (sync), but we detect rather than assume.
        mock_log = {"count": 0}
        original_mock = estimator._generate_mock_cases
        is_async_mock = inspect.iscoroutinefunction(original_mock)
        print(f"[spy] _generate_mock_cases is_async = {is_async_mock}")

        if is_async_mock:
            async def _mock_spy(req):
                mock_log["count"] += 1
                return await original_mock(req)
        else:
            def _mock_spy(req):
                mock_log["count"] += 1
                return original_mock(req)

        estimator._generate_mock_cases = _mock_spy
        print("[spy] both spies installed")

        # Run the estimator.
        print("\n[run] calling estimator.estimate_settlement_range(request)...")
        result = asyncio.run(estimator.estimate_settlement_range(request))

        # Result inspection.
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
        print(f"[result] suppressed_features = {result.suppressed_features}")
        print(
            f"[result] comparable_cases len = {len(result.comparable_cases)}"
        )
        for i, case in enumerate(result.comparable_cases[:3]):
            print(
                f"[case {i}] type={type(case).__name__}, "
                f"jurisdiction={case.jurisdiction!r}, "
                f"case_type={case.case_type!r}, "
                f"outcome_range={case.outcome_range!r}, "
                f"outcome_type={case.outcome_type!r}"
            )
        print(f"[result] range_justification = {result.range_justification!r}")
        print(f"[result] response_time_ms = {result.response_time_ms}")
        print(f"[spy] _query_comparable_cases call count = {query_log['count']}")
        print(f"[spy] _generate_mock_cases call count = {mock_log['count']}")

        # Assertions.
        assertions = [
            # Gate passed (not suppressed).
            (
                "confidence in {'low','medium','high'}",
                result.confidence in {"low", "medium", "high"},
            ),
            ("own_case_only is False", result.own_case_only is False),
            (
                "suppressed_features is empty list",
                result.suppressed_features == [],
            ),
            # Real query ran, mock did NOT.
            (
                "_query_comparable_cases called exactly once",
                query_log["count"] == 1,
            ),
            (
                "_generate_mock_cases NOT called (state parse worked)",
                mock_log["count"] == 0,
            ),
            # Cases present and response-model shaped (NOT mock dicts or
            # internal SettleContribution instances).
            (
                "comparable_cases has >=1 items",
                len(result.comparable_cases) >= 1,
            ),
            (
                "each case is a ComparableCase instance "
                "(replaced architect's 'UUID id' check \u2014 ComparableCase "
                "has no id field per case_bank.py)",
                all(
                    isinstance(c, ComparableCase)
                    for c in result.comparable_cases
                ),
            ),
            (
                "each case jurisdiction ends with ', FL'",
                all(
                    str(c.jurisdiction).endswith(", FL")
                    for c in result.comparable_cases
                ),
            ),
            (
                "each case case_type == 'Motor Vehicle Accident'",
                all(
                    c.case_type == "Motor Vehicle Accident"
                    for c in result.comparable_cases
                ),
            ),
            (
                "each case outcome_range is non-empty string "
                "(renamed from spec's outcome_amount_range \u2014 that field "
                "is on SettleContribution, not ComparableCase)",
                all(
                    isinstance(c.outcome_range, str)
                    and len(c.outcome_range) > 0
                    for c in result.comparable_cases
                ),
            ),
            # Percentiles populated and monotonic.
            ("percentile_25 > 0", result.percentile_25 > 0),
            ("median > 0", result.median > 0),
            ("percentile_75 > 0", result.percentile_75 > 0),
            ("percentile_95 > 0", result.percentile_95 > 0),
            (
                "percentile_25 <= median",
                result.percentile_25 <= result.median,
            ),
            (
                "median <= percentile_75",
                result.median <= result.percentile_75,
            ),
            (
                "percentile_75 <= percentile_95",
                result.percentile_75 <= result.percentile_95,
            ),
            # n_cases reflects query result, not gate count.
            (
                "n_cases == len(comparable_cases)",
                result.n_cases == len(result.comparable_cases),
            ),
            # Justification is normal-path (not suppressed).
            (
                "range_justification does NOT mention 'Insufficient'",
                result.range_justification is not None
                and "Insufficient" not in result.range_justification,
            ),
            (
                "range_justification is non-empty string",
                isinstance(result.range_justification, str)
                and len(result.range_justification) > 0,
            ),
            # Response time sensible.
            (
                "response_time_ms is non-negative int",
                isinstance(result.response_time_ms, int)
                and result.response_time_ms >= 0,
            ),
        ]

        passed = sum(1 for _, ok in assertions if ok)
        total = len(assertions)
        print(f"\n[assertions] {passed}/{total} passed")
        for label, ok in assertions:
            # Truncate label in display if >90 chars so table stays readable.
            short = label if len(label) <= 90 else label[:87] + "..."
            print(f"  [{'PASS' if ok else 'FAIL'}] {short}")

        print()
        print("=" * 72)
        if passed == total:
            verdict = "HAPPY: PASS"
            exit_code = 0
        else:
            verdict = f"HAPPY: FAIL ({total - passed} assertions failed)"
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
        print(f"Stage 2.3c.b exit_code={exit_code}")
        print("=" * 72)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
