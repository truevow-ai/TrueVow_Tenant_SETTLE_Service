"""Injury classifier version.

Semver discipline:
- MAJOR: tag added/removed from the closed-set taxonomy (e.g., adding DENTAL_INJURY → 2.0.0)
- MINOR: rule changes (new keyword added to strong_patterns, threshold adjusted)
- PATCH: bug fix in an existing rule (typo, regex correction, no semantic change)

Every InjuryClassification record stores this version. When the library evolves,
historical data can be re-run with the new version and produce side-by-side audit
of classification changes.
"""

CLASSIFIER_VERSION = "1.0.2"

# Used for rows lifted from pre-classifier era (legacy injury_category single-tags).
# These rows have no rule-engine provenance; classifier_version captures that fact.
LEGACY_CLASSIFIER_VERSION = "legacy"
