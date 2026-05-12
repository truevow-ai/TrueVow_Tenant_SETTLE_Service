"""Stage 2.3c.0 \u2014 Count-plumbing probe.

Verifies that SupabaseRESTQuery.select(..., count="exact") correctly
populates the response's `count` attribute. This is a prerequisite for
trusting any IntelligenceGate output \u2014 if count plumbing is broken,
the gate silently gets n=0 and ALWAYS suppresses in production.

Stage 2.3b.3.5 ground-truth: there are \u22657 approved FL rows (likely more).
The global count of `status='approved'` rows is \u22657 (FL alone) and may be
larger if other states have approvals too. Assertion floor: count >= 7.

Three tests:
- A: gate's exact query shape (select("id", count="exact").eq("status","approved"))
- B: request-level inspection (URL/headers if introspectable)
- C: control without count= kwarg \u2014 baseline for "count missing/None"
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.database import get_db  # noqa: E402


async def _boot_db():
    return await get_db()


def main() -> int:
    print("=" * 72)
    print("Stage 2.3c.0 \u2014 Count-plumbing probe")
    print("=" * 72)

    # Save + force live-mode flags
    orig_use_mock = settings.USE_MOCK_DATA
    orig_settle_use_mock = settings.SETTLE_USE_MOCK_DATA
    print(f"[env] original USE_MOCK_DATA={orig_use_mock}, "
          f"SETTLE_USE_MOCK_DATA={orig_settle_use_mock}")

    verdict = "COUNT: AMBIGUOUS \u2014 probe did not complete"
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

        # ----------------------------------------------------------------
        # Test A \u2014 gate's exact query shape
        # ----------------------------------------------------------------
        print()
        print("-" * 72)
        print("[A] Gate's exact query shape: "
              ".select('id', count='exact').eq('status','approved')")
        print("-" * 72)

        q = db.table("settle_contributions").select("id", count="exact").eq(
            "status", "approved"
        )

        # Inspect the query builder BEFORE executing \u2014 does it carry count state?
        print(f"[A.pre] type(q) = {type(q).__name__}")
        q_pub_attrs = [a for a in dir(q) if not a.startswith("_")]
        q_priv_attrs = [a for a in dir(q) if a.startswith("_") and not a.startswith("__")]
        print(f"[A.pre] public attrs on q  = {q_pub_attrs}")
        print(f"[A.pre] private attrs on q = {q_priv_attrs}")
        for attr in ("_count_mode", "_count", "count_mode", "count"):
            if hasattr(q, attr):
                try:
                    print(f"[A.pre] q.{attr} = {getattr(q, attr)!r}")
                except Exception as e:
                    print(f"[A.pre] q.{attr} read failed: {e!r}")
        # Filters and select
        for attr in ("_filters", "_select_fields"):
            if hasattr(q, attr):
                try:
                    print(f"[A.pre] q.{attr} = {getattr(q, attr)!r}")
                except Exception as e:
                    print(f"[A.pre] q.{attr} read failed: {e!r}")

        r = q.execute()
        print(f"[A] type(r) = {type(r).__name__}")
        print(f"[A] hasattr(r, 'count') = {hasattr(r, 'count')}")
        count_val = getattr(r, "count", "<MISSING ATTR>")
        print(f"[A] r.count = {count_val!r}")
        data_len = len(r.data) if getattr(r, "data", None) else 0
        print(f"[A] len(r.data) = {data_len}")
        r_attrs = [a for a in dir(r) if not a.startswith("_")]
        print(f"[A] all public attrs on r = {r_attrs}")

        # ----------------------------------------------------------------
        # Test B \u2014 request-level inspection (URL/headers if introspectable)
        # ----------------------------------------------------------------
        print()
        print("-" * 72)
        print("[B] Request-level inspection (URL/headers if exposed)")
        print("-" * 72)
        url_attr = None
        for attr in ("_url", "url", "_built_url", "_query_url"):
            if hasattr(q, attr):
                try:
                    url_attr = (attr, getattr(q, attr))
                    break
                except Exception:
                    continue
        if url_attr:
            print(f"[B] q.{url_attr[0]} = {url_attr[1]!r}")
        else:
            print("[B] no URL attr exposed on query builder (skipped)")

        hdr_attr = None
        for attr in ("_headers", "headers", "_client_headers"):
            if hasattr(q, attr):
                try:
                    hdr_attr = (attr, getattr(q, attr))
                    break
                except Exception:
                    continue

        def _redact_headers(h):
            """Redact secret values. Print keys always; values only for
            non-sensitive headers, short-suffix-preview for sensitive ones.
            """
            if not isinstance(h, dict):
                return f"<non-dict headers: type={type(h).__name__}>"
            sensitive = {"apikey", "authorization", "x-api-key", "cookie",
                         "set-cookie", "x-supabase-auth"}
            out = {}
            for k, v in h.items():
                if k.lower() in sensitive and isinstance(v, str) and len(v) > 10:
                    out[k] = f"...{v[-8:]} (len={len(v)}, REDACTED)"
                else:
                    out[k] = v
            return out

        if hdr_attr:
            print(f"[B] q.{hdr_attr[0]} keys = {list(hdr_attr[1].keys()) if isinstance(hdr_attr[1], dict) else '<not a dict>'}")
            print(f"[B] q.{hdr_attr[0]} (redacted) = {_redact_headers(hdr_attr[1])}")
        else:
            # Check the parent client for headers
            client = getattr(q, "client", None)
            if client is not None and hasattr(client, "headers"):
                try:
                    ch = client.headers
                    print(f"[B] q.client.headers keys = {list(ch.keys()) if isinstance(ch, dict) else '<not a dict>'}")
                    print(f"[B] q.client.headers (redacted) = {_redact_headers(ch)}")
                except Exception as e:
                    print(f"[B] q.client.headers read failed: {e!r}")
            else:
                print("[B] no headers attr exposed on query builder or client")

        # ----------------------------------------------------------------
        # Test C \u2014 control: same query WITHOUT count= kwarg
        # ----------------------------------------------------------------
        print()
        print("-" * 72)
        print("[C] Control: same query WITHOUT count= kwarg")
        print("-" * 72)
        q2 = db.table("settle_contributions").select("id").eq(
            "status", "approved"
        )
        r2 = q2.execute()
        print(f"[C] type(r2) = {type(r2).__name__}")
        print(f"[C] hasattr(r2, 'count') = {hasattr(r2, 'count')}")
        count_val_2 = getattr(r2, "count", "<MISSING ATTR>")
        print(f"[C] r2.count = {count_val_2!r}")
        data_len_2 = len(r2.data) if getattr(r2, "data", None) else 0
        print(f"[C] len(r2.data) = {data_len_2}")

        # ----------------------------------------------------------------
        # Verdict
        # ----------------------------------------------------------------
        print()
        print("=" * 72)
        # "WORKS" iff Test A produced an int >= 7
        if isinstance(count_val, int) and count_val >= 7:
            verdict = (
                f"COUNT: WORKS \u2014 r.count returned {count_val} (>= 7), "
                f"matches Stage 2.3b.3.5 ground truth"
            )
            exit_code = 0
        elif isinstance(count_val, int) and count_val < 7:
            verdict = (
                f"COUNT: BROKEN \u2014 r.count is {count_val} "
                f"(expected int >= 7 per Stage 2.3b.3.5 ground truth). "
                f"Likely Prefer: count=exact header missing \u2014 "
                f"gate will silently report n<threshold forever."
            )
            exit_code = 1
        elif count_val is None or count_val == "<MISSING ATTR>":
            verdict = (
                f"COUNT: BROKEN \u2014 r.count is {count_val!r}. "
                f"Response object does not carry count \u2014 gate will ALWAYS "
                f"suppress in production regardless of DB contents."
            )
            exit_code = 1
        else:
            verdict = (
                f"COUNT: AMBIGUOUS \u2014 r.count={count_val!r} "
                f"(type={type(count_val).__name__}), data_len={data_len}. "
                f"Unexpected shape; architect should inspect."
            )
            exit_code = 2

        print(verdict)

    finally:
        settings.USE_MOCK_DATA = orig_use_mock
        settings.SETTLE_USE_MOCK_DATA = orig_settle_use_mock
        print(f"[env] restored USE_MOCK_DATA={orig_use_mock}, "
              f"SETTLE_USE_MOCK_DATA={orig_settle_use_mock}")
        print("=" * 72)
        print(f"Stage 2.3c.0 exit_code={exit_code}")
        print("=" * 72)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
