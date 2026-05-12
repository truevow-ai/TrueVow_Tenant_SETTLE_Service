"""Stage 2.3b.3.0 — URL-sanity probe for SupabaseRESTQuery.like/ilike encoding.

Pure construction inspection. NO HTTP calls made.

Verifies that the Option B patch on like()/ilike() in app/core/database.py:
- URL-encodes PostgREST-reserved chars (comma, etc.) in the filter value
- Preserves SQL LIKE wildcards % (multi-char) and _ (single-char)

Run ONLY after the patch has landed; assertions will fail against the
pre-patch naive implementation.
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import unquote

# Add SETTLE service root to sys.path (script lives in scripts/ subdir)
SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.core.database import SupabaseRESTClient  # noqa: E402


def _check(label: str, cond: bool, detail: str = "") -> bool:
    """Tiny assertion helper. Returns True on pass, False on fail."""
    mark = "PASS" if cond else "FAIL"
    print(f"  [{mark}] {label}" + (f"  ({detail})" if detail else ""))
    return cond


def _round_trip(filter_str: str) -> str:
    """Simulate PostgREST's server-side URL-decode of a filter value.

    Given 'column=op.<encoded_value>', return unquote(<encoded_value>).
    """
    kv = filter_str.split("=", 1)[1]       # e.g. 'ilike.%25%2C%20FL'
    encoded_value = kv.split(".", 1)[1]    # e.g. '%25%2C%20FL'
    return unquote(encoded_value)


def main() -> int:
    print("=" * 72)
    print("Stage 2.3b.3.0 \u2014 URL-sanity probe for like/ilike encoding")
    print("=" * 72)

    # No network — fake URL + key are fine, we inspect internal state only
    # Constructor signature: SupabaseRESTClient(base_url, service_key)
    client = SupabaseRESTClient("https://fake.supabase.co", "fake-service-key")

    all_pass = True

    # ------------------------------------------------------------------
    # Case 1: ilike with a comma in the pattern (the bug-reproducer)
    # Expected: "%, FL" -> encoded as "%25%2C%20FL"
    #   - %  -> preserved (wildcard)
    #   - ,  -> %2C
    #   - ' ' -> %20
    # ------------------------------------------------------------------
    print("\n[case 1] ilike('jurisdiction', '%, FL')")
    q1 = client.table("settle_contributions").select("*").ilike("jurisdiction", "%, FL")
    filters_1 = q1._filters
    print(f"  filters = {filters_1}")
    filter_1 = filters_1[0] if filters_1 else ""

    all_pass &= _check(
        "comma encoded as %2C",
        "%2C" in filter_1,
        f"filter={filter_1!r}",
    )
    all_pass &= _check(
        "% wildcard preserved (raw % present)",
        "%" in filter_1,
        f"filter={filter_1!r}",
    )
    # Specifically: a raw unencoded comma must NOT appear in the filter string.
    # The encoded form is "%2C"; a bare "," would indicate the bug is still live.
    all_pass &= _check(
        "raw comma NOT in filter string",
        "," not in filter_1,
        f"filter={filter_1!r}",
    )
    all_pass &= _check(
        "filter still starts with 'jurisdiction=ilike.'",
        filter_1.startswith("jurisdiction=ilike."),
        f"filter={filter_1!r}",
    )
    # Wire-correctness — % MUST be URL-encoded as %25
    all_pass &= _check(
        "% wildcard encoded as %25 on the wire",
        "%25" in filter_1,
        f"filter={filter_1!r}",
    )
    # Round-trip: PostgREST's URL-decode should restore the SQL pattern
    decoded_1 = _round_trip(filter_1)
    all_pass &= _check(
        "round-trip decode → '%, FL'",
        decoded_1 == "%, FL",
        f"decoded={decoded_1!r}",
    )

    # ------------------------------------------------------------------
    # Case 2: ilike with an underscore wildcard — must NOT be encoded
    # Expected: "John_Smith" stays as "John_Smith", not "John%5FSmith"
    # ------------------------------------------------------------------
    print("\n[case 2] ilike('name', 'John_Smith')")
    q2 = client.table("users").select("*").ilike("name", "John_Smith")
    filters_2 = q2._filters
    print(f"  filters = {filters_2}")
    filter_2 = filters_2[0] if filters_2 else ""

    all_pass &= _check(
        "_ wildcard preserved (raw _ present)",
        "_" in filter_2,
        f"filter={filter_2!r}",
    )
    all_pass &= _check(
        "_ NOT encoded as %5F",
        "%5F" not in filter_2,
        f"filter={filter_2!r}",
    )
    # Round-trip: even without %, the decoded value must match the input pattern
    decoded_2 = _round_trip(filter_2)
    all_pass &= _check(
        "round-trip decode → 'John_Smith'",
        decoded_2 == "John_Smith",
        f"decoded={decoded_2!r}",
    )

    # ------------------------------------------------------------------
    # Case 3: like() gets the same treatment (symmetric patch)
    # Expected: comma encoded, % preserved
    # ------------------------------------------------------------------
    print("\n[case 3] like('jurisdiction', '%, FL')")
    q3 = client.table("settle_contributions").select("*").like("jurisdiction", "%, FL")
    filters_3 = q3._filters
    print(f"  filters = {filters_3}")
    filter_3 = filters_3[0] if filters_3 else ""

    all_pass &= _check(
        "comma encoded as %2C (like)",
        "%2C" in filter_3,
        f"filter={filter_3!r}",
    )
    all_pass &= _check(
        "% wildcard preserved (like)",
        "%" in filter_3,
        f"filter={filter_3!r}",
    )
    all_pass &= _check(
        "raw comma NOT in filter string (like)",
        "," not in filter_3,
        f"filter={filter_3!r}",
    )
    all_pass &= _check(
        "filter starts with 'jurisdiction=like.'",
        filter_3.startswith("jurisdiction=like."),
        f"filter={filter_3!r}",
    )
    # Wire-correctness — % MUST be URL-encoded as %25 (like)
    all_pass &= _check(
        "% wildcard encoded as %25 on the wire (like)",
        "%25" in filter_3,
        f"filter={filter_3!r}",
    )
    # Round-trip (like)
    decoded_3 = _round_trip(filter_3)
    all_pass &= _check(
        "round-trip decode → '%, FL' (like)",
        decoded_3 == "%, FL",
        f"decoded={decoded_3!r}",
    )

    # ------------------------------------------------------------------
    # Case 4: ilike with both % and _ mixed with comma — regression guard
    # Expected: both wildcards survive, comma encoded
    # ------------------------------------------------------------------
    print("\n[case 4] ilike('addr', '%_Main St, FL%')")
    q4 = client.table("addrs").select("*").ilike("addr", "%_Main St, FL%")
    filters_4 = q4._filters
    print(f"  filters = {filters_4}")
    filter_4 = filters_4[0] if filters_4 else ""

    all_pass &= _check(
        "% preserved in mixed-wildcard pattern",
        "%" in filter_4,
        f"filter={filter_4!r}",
    )
    all_pass &= _check(
        "_ preserved in mixed-wildcard pattern",
        "_" in filter_4,
        f"filter={filter_4!r}",
    )
    all_pass &= _check(
        "comma encoded as %2C in mixed pattern",
        "%2C" in filter_4,
        f"filter={filter_4!r}",
    )
    # Wire-correctness — % MUST be URL-encoded as %25 (mixed pattern)
    all_pass &= _check(
        "% wildcard encoded as %25 on the wire (mixed)",
        "%25" in filter_4,
        f"filter={filter_4!r}",
    )
    # Round-trip: decoded must equal the original mixed-wildcard SQL pattern
    decoded_4 = _round_trip(filter_4)
    all_pass &= _check(
        "round-trip decode → '%_Main St, FL%'",
        decoded_4 == "%_Main St, FL%",
        f"decoded={decoded_4!r}",
    )

    # ------------------------------------------------------------------
    # Verdict
    # ------------------------------------------------------------------
    print()
    print("=" * 72)
    if all_pass:
        print("SANITY: PASS \u2014 all encoding invariants hold")
        return 0
    else:
        print("SANITY: FAIL \u2014 one or more assertions failed (see above)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
