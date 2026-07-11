"""
_killswitch.py — Hard kill-switch for the deprecated, UNGATED data-collection
scripts in this directory.

These scripts (casemine/legal-blogs/extract-500/manual-collection/automated-
pipeline scrapers + the seed-via-supabase-client / seed-* seeders) predate the
no-fabrication factory. They carry their own un-hardened classifiers and, worse,
insert straight into the database bypassing BOTH gates
(no_fabrication_gate.verify_record + verdict_validator.normalize_and_validate).

Per AGENTS.md RULE 0, nothing may enter the DB without verbatim evidence +
provenance. Running these scripts would poison the database. They are therefore
DISABLED.

Any script that imports `abort_if_killed()` and calls it at startup will refuse
to run and point the operator at the supported factory pipeline.

Use instead:
    settle_data_scraping_factory/  (cds_* adapters -> shared extractor ->
    no_fabrication_gate -> verdict_validator -> loader). Nothing auto-published.
"""

import sys

_MSG = """
================================================================================
 DISABLED — ungated data-collection script (AGENTS.md RULE 0: no fabrication)
================================================================================
This script inserts data WITHOUT the no-fabrication + validation gates and
would poison settle_verdicts / settle_contributions with unverifiable values.

It has been permanently disabled. Use the supported, gated pipeline instead:

    settle_data_scraping_factory/court_dockets_records/
        cds_*  -> _common/extract -> no_fabrication_gate -> verdict_validator
              -> load_direct_supabase.py / cds_cap_loader.py

To port a source (e.g. Casemine) safely, add a cds_* factory adapter that
yields raw opinion_text + source_url + sha256 and lets the shared, gated
extractor do all field extraction. Never re-enable this script.
================================================================================
"""


def abort_if_killed() -> None:
    """Print the notice and exit non-zero. No override — this is intentional."""
    sys.stderr.write(_MSG)
    sys.exit(2)
