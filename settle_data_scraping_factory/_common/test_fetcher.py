"""
Standalone smoke test for _common/fetcher.py (Level-0 fetcher).

Run:  python settle_data_scraping_factory/_common/test_fetcher.py
Exits 0 on success, 1 on failure. Uses a throwaway cache dir.
Hits a real zero-blocker endpoint (Caselaw Access Project metadata).
"""

import sys
import tempfile
from pathlib import Path

# fetcher.py lives in the same directory as this script.
from fetcher import Fetcher

URL = "https://static.case.law/JurisdictionsMetadata.json"


def main() -> int:
    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        f = Fetcher(min_delay=0.3, cache_dir=tmp, use_cache=True)
        try:
            print("Fetch #1 (network):")
            r1 = f.get_json(URL)
            check("status 200", r1.status_code == 200)
            check("content non-empty", len(r1.content) > 0)
            check("not from cache", r1.from_cache is False)
            check("sha256 present (64 hex)", isinstance(r1.sha256, str) and len(r1.sha256) == 64)

            data = r1.json()
            check("JSON parses", data is not None)
            check("JSON non-empty", bool(data))

            prov = r1.provenance()
            check("provenance has source_url", prov.get("source_url") == URL)
            check("provenance has sha256", prov.get("sha256") == r1.sha256)
            check("provenance has fetched_at", bool(prov.get("fetched_at")))

            print("Fetch #2 (should hit cache):")
            r2 = f.get_json(URL)
            check("from cache", r2.from_cache is True)
            check("sha256 stable across cache", r2.sha256 == r1.sha256)
            check("content identical from cache", r2.content == r1.content)

            # Light relevance peek (full parsing is Piece 2's job).
            blob = r1.text().lower()
            check("mentions a jurisdiction we care about (cal/fla)",
                  ("cal" in blob) or ("fla" in blob) or ("florida" in blob) or ("california" in blob))
        finally:
            f.close()

    print()
    if failures:
        print(f"RESULT: FAILED ({len(failures)} checks) -> {failures}")
        return 1
    print("RESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
