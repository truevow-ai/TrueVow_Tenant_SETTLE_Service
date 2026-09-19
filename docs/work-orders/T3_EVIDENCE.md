# T3 — Provenance + Evidence Capability

**Ticket:** T3 (SETTLE-CONTRIB-TO-TICKETS)
**Status:** PASS
**Date:** 2026-08-31

---

## Method

Inspected existing provenance/evidence structures. Implemented bounded application-layer capability reusing existing authorities. No database change, no migration, no schema change.

## Verdict

T3_STATUS = PASS

---

## Existing Authorities Reused

| Authority | File | Reused |
|---|---|---|
| Provenance fields | `settle_verdicts` (source, source_url, source_notes, validated_field_count, validation_counts, field_evidence, review_status, corroboration_count, corroborating_sources) | YES |
| No-fabrication gate | `no_fabrication_gate.py` (`verify_record`) | YES |
| Verdict validator | `verdict_validator.py` (`normalize_and_validate`) | YES |
| Enrichment with snippets | `_common/enrich.py` | YES (pattern reference) |
| Provenance mapping pattern | `cds_cap_loader.py` (`map_candidate_to_verdict`) | YES |
| Privacy boundary | `AnonymizationValidator.validate_contribution()` (T2) | YES |
| Tenant authority | `tenant_core.py` | YES |

## Implementation

**New file:** `app/services/external_provenance.py`

Functions:
- `map_external_to_provenance()` — maps external/historical contribution data into existing provenance fields
- `build_external_record()` — routes through existing verify-and-persist gate sequence
- `check_contradictory_sources()` — detects contradicting sources without silently promoting
- `check_duplicate_source()` — prevents duplicate sources masquerading as independent corroboration
- `is_unknown_or_missing()` — preserves UNKNOWN/MISSING/NOT_APPLICABLE semantics
- `stripped_cannot_be_evidence()` — guard ensuring STRIPPED never becomes evidence

**No new models, tables, or evidence representations created.**

## Source Provenance

External source types reuse existing canonical values:
- `firm_submission` — attorney/firm case-management export
- `court_docket` — court/verdict record
- `news_report` — news report
- `settlement_survey` — settlement survey
- `scraped_verdict` — scraped verdict

`source_url` is NOT mandatory for all source types. Sources without URLs leave the field absent rather than fabricating one. Unknown source types return None — caller must STOP and report the ontology/governance dependency.

## Field Evidence

Reuses existing `field_evidence` architecture. One source supports multiple fields where evidence actually supports them. Different fields supported by different sources preserve that distinction. No second evidence representation created.

## No-Fabrication

`verify_record()` runs FIRST. Unverified fields are STRIPPED. Unsupported fields are not promoted merely because the record has a source. No missing evidence, source snippets, source URLs, verification counts, corroborating sources, unknown values, policy limits, damages, or settlement values are synthesized.

## Multi-Source Support

Preserves existing corroboration architecture. Tests verify:
- One source supports multiple facts
- Multiple independent sources support the same fact
- Contradictory sources do not silently promote
- Source supports settlement outcome but not another analytical field
- Duplicate copies of same source do not masquerade as independent corroboration

## External/Historical Origin

No requirement for:
- INTAKE session
- TRACE matter
- TRACE evidence record
- prior SETTLE lifecycle
- matter.activated
- fake TrueVow lifecycle records

Historical/external provenance truthfully represents its external origin. TRACE not modified.

## Privacy Boundary

All provenance/evidence handling continues through T2-established privacy boundary. Prohibited sensitive source content is not persisted merely because provenance is required. Evidence auditability does not automatically mean raw source-document retention. Prefers smallest evidence representation.

## UNKNOWN / MISSING / NOT_APPLICABLE / STRIPPED

Preserved:
- UNKNOWN: relevant value genuinely unknown
- MISSING: expected/applicable value not supplied or adequately supported
- NOT_APPLICABLE: concept does not apply
- STRIPPED: removed/redacted content that must not become analytical data

No source evidence fabricated for UNKNOWN/MISSING/NOT_APPLICABLE. STRIPPED never becomes field evidence.

## Tests

**New file:** `tests/test_external_provenance.py` (19 tests, all passing)

| Test | Result |
|---|---|
| External origin maps provenance without TRACE lifecycle | PASS |
| Supported field persists field_evidence | PASS |
| Unsupported field not promoted (record has source) | PASS |
| One source supports multiple fields | PASS |
| Different sources support different fields | PASS |
| Contradictory source handling | PASS |
| Duplicate source independence | PASS |
| Missing/UNKNOWN/NOT_APPLICABLE no fabricated evidence | PASS |
| STRIPPED cannot become evidence | PASS |
| Prohibited content still rejected (T2 boundary) | PASS |
| Contributor tenant/user attribution preserved | PASS |
| No-fabrication remains intact | PASS |
| Existing anonymizer regression | PASS |
| Unknown source type not invented | PASS |
| source_url not mandatory for all sources | PASS |
| No source type leaves source absent | PASS |
| External record routes through gate sequence | PASS |

## Regression

Existing regression suite: 37/37 passing (test_anonymizer.py 9, test_no_fabrication_gate.py 16, test_privacy_acceptance_boundary.py 12)

## Database Governance

DATABASE_CREATED = NO
MIGRATION_CREATED = NO
SCHEMA_CHANGED = NO
RLS_CHANGED = NO
T_PERSIST = NOT_REQUIRED

## Protected Boundaries

REC_000_MODIFIED = NO
C2_C7_C12_MODIFIED = NO
TRACE_MODIFIED = NO
CUSTOMER_PORTAL_MODIFIED = NO
DOWNSTREAM_T4_T8 = NOT_EXECUTED

## Governance Dependency

PHI_POLICY_GOVERNANCE_DEPENDENCY = OPEN

The canonical TrueVow privacy policy definition is not present as a standalone repository file. Coverage remains PARTIAL against the categories represented in the accepted specification and the anonymizer's own patterns. Complete coverage requires the canonical policy definition to be located or established.