"""
verify_manifest.py — Verifiable truth assertions for the govdata skill.

Each entry is a verifiable claim about a public data source. Used as
a smoke-test manifest to confirm the govdata pipeline is working correctly.
"""

MANIFEST: list[dict] = [
    {
        "id": "ssa_life_m35",
        "description": "SSA period life expectancy: male age 35",
        "verifier": "ssa_life_expectancy",
        "gender": "M",
        "age": 35,
        "expected": "absolute",
        "source_url": "https://www.ssa.gov/oact/STATS/table4c6.html",
    },
    {
        "id": "cms_pfs_22551_fl03_fac",
        "description": "CMS PFS CPT 22551 @ FL-03 (Fort Lauderdale) facility CY2025",
        "verifier": "cms_pfs_allowed",
        "cpt": "22551",
        "locality": "FL-03",
        "place": "facility",
        "expected": "absolute",
        "source_url": "https://www.cms.gov/files/zip/rvu25a.zip (PPRRVU25_JAN.csv, GPCI2025.csv)",
    },
    {
        "id": "cms_pfs_22551_fl99_fac",
        "description": "CMS PFS CPT 22551 @ FL-99 (Rest of Florida) facility CY2025",
        "verifier": "cms_pfs_allowed",
        "cpt": "22551",
        "locality": "FL-99",
        "place": "facility",
        "expected": "absolute",
        "source_url": "https://www.cms.gov/files/zip/rvu25a.zip",
    },
]
