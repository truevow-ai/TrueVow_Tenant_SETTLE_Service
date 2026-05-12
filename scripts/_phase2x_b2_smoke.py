"""Stage 2.3b.2.smoke — verify _query_comparable_cases against live Supabase.

Directly exercises the private query function (bypasses IntelligenceGate).
Calls `_query_comparable_cases(request)` with the same request shape that
produced a live approved row in the 2.3b.1 probe.

Exit criteria:
- PASS: result is a list AND len(result) >= 1
- FAIL: result is empty (state filter too strict, or no FL+MVA+TBI intersection)
- CRASH: constructor signature surprise, DB client is None, or exception bubbles

Notes:
- `settings.use_mock_data` is a read-only @property — we flip the underlying
  USE_MOCK_DATA and SETTLE_USE_MOCK_DATA attributes (same pattern as 2.3b.1).
- SettlementEstimator signature is `(db_connection=None, gate=None)` — we
  pass db_connection=db and let gate default to None (which internally wires
  a fresh IntelligenceGate, but it's never invoked since we call the private
  _query_comparable_cases directly).
"""
from __future__ import annotations

import asyncio
import inspect
import sys
import traceback
from pathlib import Path

# Add SETTLE service root to sys.path (script lives in scripts/ subdir)
SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.models.case_bank import EstimateRequest  # noqa: E402
from app.services.estimator import SettlementEstimator  # noqa: E402


async def _boot_db():
    """Async helper — get_db() is an async def."""
    return await get_db()


async def _run_query(estimator: SettlementEstimator, request: EstimateRequest):
    """Async helper — _query_comparable_cases is an async def."""
    return await estimator._query_comparable_cases(request)


def main() -> int:
    print("=" * 72)
    print("Stage 2.3b.2.smoke — _query_comparable_cases live verification")
    print("=" * 72)

    # Echo the __init__ signature so architect can confirm the shape
    try:
        sig = inspect.signature(SettlementEstimator.__init__)
        print(f"[sig] SettlementEstimator.__init__{sig}")
    except Exception as e:
        print(f"[sig] could not introspect signature: {e}")

    # Save originals (both the class attr and the SETTLE-scoped override)
    orig_use_mock = settings.USE_MOCK_DATA
    orig_settle_use_mock = settings.SETTLE_USE_MOCK_DATA
    print(
        f"[env] original USE_MOCK_DATA={orig_use_mock}, "
        f"SETTLE_USE_MOCK_DATA={orig_settle_use_mock}"
    )

    exit_code = 1
    try:
        # Force mock-mode OFF so get_db() returns a real SupabaseRESTClient
        settings.USE_MOCK_DATA = False
        settings.SETTLE_USE_MOCK_DATA = False
        print(
            f"[env] forced USE_MOCK_DATA={settings.USE_MOCK_DATA}, "
            f"SETTLE_USE_MOCK_DATA={settings.SETTLE_USE_MOCK_DATA}, "
            f"use_mock_data(property)={settings.use_mock_data}"
        )

        # Boot the DB client (async)
        db = asyncio.run(_boot_db())
        assert db is not None, (
            "get_db() returned None \u2014 Option B may have regressed"
        )
        print(f"[boot] db type = {type(db).__name__}")

        # Build the request matching the 2.3b.1 live-row shape
        request = EstimateRequest(
            jurisdiction="Nassau County, FL",
            case_type="Motor Vehicle Accident",
            injury_category=["traumatic_brain_injury"],
            medical_bills=10000.0,
        )
        print(
            f"[req] jurisdiction={request.jurisdiction!r}, "
            f"case_type={request.case_type!r}, "
            f"injury_category={request.injury_category}, "
            f"medical_bills={request.medical_bills}"
        )

        # Construct estimator (gate defaults to None -> internal IntelligenceGate,
        # but never invoked since we call _query_comparable_cases directly)
        estimator = SettlementEstimator(db_connection=db)
        print(f"[init] estimator constructed: db={estimator.db is not None}, "
              f"gate={estimator.gate is not None}")

        # Run the query
        result = asyncio.run(_run_query(estimator, request))
        print(
            f"[result] type = {type(result).__name__}, "
            f"len = {len(result) if hasattr(result, '__len__') else 'n/a'}"
        )

        assert isinstance(result, list), (
            f"expected list, got {type(result).__name__}"
        )

        # Print first 3 rows
        for i, case in enumerate(result[:3]):
            try:
                print(
                    f"[row {i}] id={getattr(case, 'id', None)!r}, "
                    f"jurisdiction={getattr(case, 'jurisdiction', None)!r}, "
                    f"case_type={getattr(case, 'case_type', None)!r}, "
                    f"outcome_amount_range="
                    f"{getattr(case, 'outcome_amount_range', None)!r}"
                )
            except Exception as e:
                print(f"[row {i}] print failed: {type(e).__name__}: {e}")

        # Verdict
        if len(result) >= 1:
            print("SMOKE: PASS")
            exit_code = 0
        else:
            print(
                "SMOKE: FAIL \u2014 zero rows returned "
                "(state filter may be too strict, or test data is in wrong state)"
            )
            exit_code = 2

    except AssertionError as e:
        print(f"SMOKE: ASSERT_FAIL \u2014 {e}")
        traceback.print_exc()
        exit_code = 3
    except Exception as e:
        print(f"SMOKE: CRASH \u2014 {type(e).__name__}: {e}")
        traceback.print_exc()
        exit_code = 4
    finally:
        # Restore originals
        settings.USE_MOCK_DATA = orig_use_mock
        settings.SETTLE_USE_MOCK_DATA = orig_settle_use_mock
        print(
            f"[env] restored USE_MOCK_DATA={settings.USE_MOCK_DATA}, "
            f"SETTLE_USE_MOCK_DATA={settings.SETTLE_USE_MOCK_DATA}"
        )

    print("=" * 72)
    print(f"Stage 2.3b.2.smoke exit_code={exit_code}")
    print("=" * 72)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
