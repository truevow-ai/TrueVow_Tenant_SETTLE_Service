"""Stage 2.3a sanity probe for SupabaseRESTQuery.cs() method.

Read-only: constructs query objects, inspects emitted filter strings.
No DB traffic. Delete after verification.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SupabaseRESTQuery


def main() -> int:
    # Case 1: single-value string shorthand
    q1 = SupabaseRESTQuery(None, "settle_contributions")
    q1.cs("injury_category", "Spinal Injury")
    print("case 1 (str shorthand)  :", q1._filters[0])

    # Case 2: single-value list
    q2 = SupabaseRESTQuery(None, "settle_contributions")
    q2.cs("injury_category", ["Spinal Injury"])
    print("case 2 (list 1-value)   :", q2._filters[0])

    # Case 3: multi-value, simple
    q3 = SupabaseRESTQuery(None, "settle_contributions")
    q3.cs("tags", ["alpha", "beta"])
    print("case 3 (list multi)     :", q3._filters[0])

    # Case 4: value with embedded comma (needs quoting)
    q4 = SupabaseRESTQuery(None, "settle_contributions")
    q4.cs("tags", ["x,y", "z"])
    print("case 4 (comma in val)   :", q4._filters[0])

    # Case 5: value with embedded double-quote (needs escape)
    q5 = SupabaseRESTQuery(None, "settle_contributions")
    q5.cs("tags", ['a"b'])
    print("case 5 (quote in val)   :", q5._filters[0])

    # Case 6: expected canonical form matches user-spec target
    expected_prefix = "injury_category=cs."
    assert q1._filters[0].startswith(expected_prefix), q1._filters[0]
    # URL-encoded braces present
    assert "%7B" in q1._filters[0] and "%7D" in q1._filters[0], q1._filters[0]
    print("asserts                 : OK (prefix + URL-encoded braces)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
