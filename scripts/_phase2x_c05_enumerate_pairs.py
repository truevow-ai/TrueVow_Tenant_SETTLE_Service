"""Stage 2.3c.0.5 \u2014 Enumerate approved (jurisdiction, case_type) pairs.

Goal: find natural high-n pairs so 2.3c.b can test the happy path WITHOUT
injecting a permissive gate (cleaner than monkey-patching production code).

Ground truth from Stage 2.3c.0: 440 approved rows across all states.
Gate threshold: MIN_AGGREGATE_N = 50.

Verdicts:
- NATURAL: AVAILABLE \u2014 at least one (juris, case_type) pair has n>=50
- NATURAL: NONE     \u2014 all pairs are below 50; gate injection required
"""
from __future__ import annotations

import asyncio
import sys
from collections import Counter
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))


class _Tee:
    """Duplicate stdout to a log file. Belt-and-suspenders against flaky
    PowerShell pipe/redirection capture observed in this session.
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


LOG_PATH = SERVICE_ROOT / "logs" / "phase2x_c05_enumerate_pairs.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
_log_fh = LOG_PATH.open("w", encoding="utf-8")
sys.stdout = _Tee(sys.__stdout__, _log_fh)
sys.stderr = _Tee(sys.__stderr__, _log_fh)

from app.core.config import settings  # noqa: E402
from app.core.database import get_db  # noqa: E402


async def _boot_db():
    return await get_db()


def main() -> int:
    print("=" * 72)
    print("Stage 2.3c.0.5 \u2014 Pair enumeration")
    print("=" * 72)

    orig_use_mock = settings.USE_MOCK_DATA
    orig_settle_use_mock = settings.SETTLE_USE_MOCK_DATA
    print(f"[env] original USE_MOCK_DATA={orig_use_mock}, "
          f"SETTLE_USE_MOCK_DATA={orig_settle_use_mock}")

    verdict = "NATURAL: NONE \u2014 probe did not complete"
    exit_code = 2

    try:
        settings.USE_MOCK_DATA = False
        settings.SETTLE_USE_MOCK_DATA = False
        print(f"[env] forced USE_MOCK_DATA=False, SETTLE_USE_MOCK_DATA=False, "
              f"use_mock_data(property)={settings.use_mock_data}")

        db = asyncio.run(_boot_db())
        if db is None:
            print("[boot] FATAL: get_db() returned None \u2014 cannot probe")
            return 3
        print(f"[boot] db type = {type(db).__name__}")

        # Pull all approved (jurisdiction, case_type) tuples.
        response = (
            db.table("settle_contributions")
            .select("jurisdiction, case_type")
            .eq("status", "approved")
            .limit(1000)  # safety ceiling well above the 440 we know exists
            .execute()
        )
        rows = response.data or []
        print(f"[boot] pulled {len(rows)} approved rows (expected ~440)")

        # Group by (jurisdiction, case_type).
        pairs = Counter(
            (r.get("jurisdiction"), r.get("case_type")) for r in rows
        )

        # Summary stats.
        print(f"[stats] unique (jurisdiction, case_type) pairs: {len(pairs)}")
        print(
            f"[stats] max n in any pair: "
            f"{max(pairs.values()) if pairs else 0}"
        )
        median_n = (
            sorted(pairs.values())[len(pairs) // 2] if pairs else 0
        )
        print(f"[stats] median n: {median_n}")
        pass_count = sum(1 for n in pairs.values() if n >= 50)
        fail_count = sum(1 for n in pairs.values() if n < 50)
        print(f"[stats] pairs with n >= 50 (would PASS gate): {pass_count}")
        print(f"[stats] pairs with n < 50  (would FAIL gate): {fail_count}")

        # Top-25 pairs with PASS/FAIL marker.
        print("\n[top-25 pairs by approved count, gate threshold = 50]")
        print(f"{'marker':<6} {'n':>4}  jurisdiction | case_type")
        print("-" * 80)
        for (juris, ct), n in pairs.most_common(25):
            marker = "PASS" if n >= 50 else "fail"
            print(f"  [{marker}] {n:>4}  {juris} | {ct}")

        # Fallback jurisdictions-only view if no pair clears the bar.
        max_pair_n = max(pairs.values(), default=0)
        if max_pair_n < 50:
            juris_counts = Counter(r.get("jurisdiction") for r in rows)
            print(
                "\n[fallback] No (juris, case_type) pair >= 50. "
                "Top 5 jurisdictions only:"
            )
            for juris, n in juris_counts.most_common(5):
                marker = "PASS" if n >= 50 else "fail"
                print(f"  [{marker}] {n:>4}  {juris}")

            case_type_counts = Counter(r.get("case_type") for r in rows)
            print("\n[fallback] Top 5 case_types only:")
            for ct, n in case_type_counts.most_common(5):
                marker = "PASS" if n >= 50 else "fail"
                print(f"  [{marker}] {n:>4}  {ct}")

        # Verdict.
        print()
        print("=" * 72)
        if max_pair_n >= 50:
            top_pair, top_n = pairs.most_common(1)[0]
            juris, ct = top_pair
            verdict = (
                f"NATURAL: AVAILABLE \u2014 pair ({juris!r}, {ct!r}) "
                f"with n={top_n} can serve as the happy-path test target "
                f"without gate injection"
            )
            exit_code = 0
        else:
            verdict = (
                f"NATURAL: NONE \u2014 all pairs are below 50 "
                f"(max={max_pair_n}); 2.3c.b will require injected "
                f"permissive gate"
            )
            exit_code = 1
        print(verdict)

    finally:
        settings.USE_MOCK_DATA = orig_use_mock
        settings.SETTLE_USE_MOCK_DATA = orig_settle_use_mock
        print(f"[env] restored USE_MOCK_DATA={orig_use_mock}, "
              f"SETTLE_USE_MOCK_DATA={orig_settle_use_mock}")
        print("=" * 72)
        print(f"Stage 2.3c.0.5 exit_code={exit_code}")
        print("=" * 72)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
