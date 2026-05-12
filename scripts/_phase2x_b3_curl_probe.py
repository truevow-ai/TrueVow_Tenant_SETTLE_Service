"""Stage 2.3b.3.5 \u2014 Empirical wire verification for PostgREST ilike encoding.

Ground-truth: which URL-encoded form does PostgREST actually accept?

Tests three patterns by hitting Supabase directly with httpx. No
SupabaseRESTClient, no estimator \u2014 we cut out every intermediate layer so
the probe measures wire behavior, not our abstraction's behavior.

Hypotheses:
- Pattern A (current broken):   `%%2C%20FL`       \u2192 500 (bare % invalid URL)
- Pattern B (proposed fix):     `%25%2C%20FL`     \u2192 200 with rows (fully encoded)
- Pattern C (control):          `%25%2C%20XX`     \u2192 200 with [] (fix works, no XX rows)

All 3 hypotheses matching = Option X is empirically correct.
Any hypothesis failing = need a new theory before patching.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx

# Add SETTLE service root to sys.path (script lives in scripts/ subdir)
SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))


def _load_env() -> tuple[str, str]:
    """Load .env.local and return (base_url, service_key). Fail loudly."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("[env] FATAL: python-dotenv not installed", file=sys.stderr)
        sys.exit(10)

    env_path = SERVICE_ROOT / ".env.local"
    if not env_path.is_file():
        print(f"[env] FATAL: {env_path} not found", file=sys.stderr)
        sys.exit(11)

    load_dotenv(env_path)

    # Mirror settings.supabase_url chain priority (SETTLE_DATABASE_URL first)
    base_url = (
        os.getenv("SETTLE_DATABASE_URL")
        or os.getenv("SETTLE_SUPABASE_URL")
        or os.getenv("DATABASE_URL")
        or os.getenv("SUPABASE_URL")
    )
    # Mirror settings.supabase_service_key chain priority
    service_key = (
        os.getenv("SETTLE_SUPABASE_SERVICE_KEY")
        or os.getenv("SETTLE_DATABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )

    if not base_url:
        print("[env] FATAL: no SETTLE_DATABASE_URL / *SUPABASE_URL found",
              file=sys.stderr)
        sys.exit(12)
    if not service_key:
        print("[env] FATAL: no SETTLE_SUPABASE_SERVICE_KEY / *SERVICE_ROLE_KEY "
              "found", file=sys.stderr)
        sys.exit(13)

    # Only print the project-id part of the URL; never print the service key
    print(f"[env] base_url = {base_url}")
    print(f"[env] service_key = ...{service_key[-8:]} (len={len(service_key)})")
    return base_url, service_key


def _probe(
    label: str,
    pattern_fragment: str,
    base_url: str,
    service_key: str,
    hypothesis: str,
) -> dict:
    """Hit PostgREST with the given ilike fragment. Return result dict."""
    # Build URL manually so httpx doesn't re-encode our pattern fragment.
    # httpx preserves already-encoded URL strings when passed directly.
    url = (
        f"{base_url.rstrip('/')}/rest/v1/settle_contributions"
        f"?jurisdiction=ilike.{pattern_fragment}"
        f"&status=eq.approved"
        f"&select=id,jurisdiction"
        f"&limit=5"
    )
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }

    print(f"\n[{label}] pattern={pattern_fragment!r}")
    print(f"  hypothesis: {hypothesis}")
    print(f"  URL: {url}")

    result = {"label": label, "pattern": pattern_fragment, "status": None,
              "body_preview": None, "row_count": None, "first_jurisdiction": None}

    try:
        resp = httpx.get(url, headers=headers, timeout=15.0)
        result["status"] = resp.status_code
        print(f"  status: {resp.status_code}")

        if resp.status_code == 200:
            try:
                rows = resp.json()
                result["row_count"] = len(rows) if isinstance(rows, list) else None
                print(f"  rows returned: {result['row_count']}")
                if rows and isinstance(rows, list):
                    first = rows[0]
                    result["first_jurisdiction"] = first.get("jurisdiction")
                    print(f"  first row: id={first.get('id')!r}, "
                          f"jurisdiction={first.get('jurisdiction')!r}")
            except Exception as e:
                print(f"  json parse failed: {type(e).__name__}: {e}")
                result["body_preview"] = resp.text[:300]
                print(f"  body preview: {result['body_preview']!r}")
        else:
            result["body_preview"] = resp.text[:300]
            print(f"  body preview: {result['body_preview']!r}")

    except Exception as e:
        print(f"  EXCEPTION: {type(e).__name__}: {e}")
        result["body_preview"] = f"{type(e).__name__}: {e}"

    return result


def main() -> int:
    print("=" * 72)
    print("Stage 2.3b.3.5 \u2014 Empirical wire verification (Option Z)")
    print("=" * 72)

    base_url, service_key = _load_env()

    # Pattern A: current broken form (bare % followed by 2C)
    result_a = _probe(
        "A",
        "%%2C%20FL",
        base_url,
        service_key,
        "500 expected \u2014 bare % invalid URL syntax",
    )

    # Pattern B: proposed fix (% -> %25)
    result_b = _probe(
        "B",
        "%25%2C%20FL",
        base_url,
        service_key,
        "200 + >=1 row expected \u2014 Nassau County, FL is approved in DB",
    )

    # Pattern C: control (fix works, no XX-suffixed jurisdiction)
    result_c = _probe(
        "C",
        "%25%2C%20XX",
        base_url,
        service_key,
        "200 + 0 rows expected \u2014 fix works but no rows end with ', XX'",
    )

    # -------------------------------------------------------------------
    # Evaluate hypotheses
    # -------------------------------------------------------------------
    print()
    print("=" * 72)
    print("Hypothesis evaluation:")
    print("=" * 72)

    # A: expect non-200 (server rejects bare %)
    a_match = result_a["status"] is not None and result_a["status"] != 200
    print(f"  [A] current-broken status={result_a['status']} "
          f"{'MATCH' if a_match else 'MISS'} "
          f"(expected non-200)")

    # B: expect 200 + row_count >= 1
    b_match = (
        result_b["status"] == 200
        and result_b["row_count"] is not None
        and result_b["row_count"] >= 1
    )
    print(f"  [B] proposed-fix status={result_b['status']}, "
          f"rows={result_b['row_count']} "
          f"{'MATCH' if b_match else 'MISS'} "
          f"(expected 200 + >=1 row)")

    # C: expect 200 + row_count == 0
    c_match = (
        result_c["status"] == 200
        and result_c["row_count"] == 0
    )
    print(f"  [C] control status={result_c['status']}, "
          f"rows={result_c['row_count']} "
          f"{'MATCH' if c_match else 'MISS'} "
          f"(expected 200 + 0 rows)")

    all_match = a_match and b_match and c_match

    print()
    print("=" * 72)
    if all_match:
        print("VERIFY: PASS \u2014 Option X is empirically correct")
        return 0
    else:
        print("VERIFY: FAIL \u2014 need new theory (see mismatches above)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
