# T4 — Verification, Partial Verification, Correction & Re-verification

**Ticket:** T4 (SETTLE-CONTRIB-TO-TICKETS)
**Status:** PASS
**Date:** 2026-08-31

---

## Method

Inspected existing verification infrastructure. Implemented bounded application-layer verification lifecycle reusing existing authorities. No database change, no migration, no schema change.

## Verdict

T4_STATUS = PASS

---

## Existing Authorities Reused

| Authority | File | Reused |
|---|---|---|
| No-fabrication gate | `no_fabrication_gate.py` (`verify_record`) | YES |
| Verdict validator | `verdict_validator.py` (`normalize_and_validate`) | YES |
| Record-level status | `settle_verdicts.review_status` (pending/reviewed/verified/rejected/needs_review) | YES |
| Field evidence | `settle_verdicts.field_evidence` | YES |
| Corroboration | `settle_verdicts.corroboration_count/corroborating_sources` | YES |
| Audit events | `audit_store.py` (append-only, tenant-scoped) | YES |
| Tenant authority | `tenant_core.py` | YES |
| Privacy boundary | `AnonymizationValidator.validate_contribution()` (T2) | YES |

## Implementation

**New file:** `app/services/external_verification.py`

Functions:
- `summarize_record_status()` — record-level status from actual field states
- `field_verification_state()` — field-level state per existing evidence rules
- `field_is_verified()` — only verified per existing rules
- `record_status_implies_all_fields()` — must be False for partial verification
- `check_contradiction()` — contradicting sources without silent promotion
- `check_duplicate_source()` — duplicate sources not independent corroboration
- `apply_correction()` — correction preserving audit history
- `stale_verification_after_correction()` — stale verification guard
- `reverify_field()` — re-verification recalculated from current evidence
- `reverify_after_source_invalidation()` — source invalidation handling
- `is_unknown()` / `is_missing()` / `is_not_applicable()` — semantic preservation
- `semantic_distinct()` — UNKNOWN/MISSING/NOT_APPLICABLE/zero remain distinct
- `stripped_cannot_become_verified()` — STRIPPED guard
- `analytics_eligibility_undelegated()` — T4 does NOT decide analytics
- `verification_truth_for_analytics()` — exposes state for T5
- `tenant_can_modify()` — cross-tenant modification guard
- `run_external_verification()` — full gate sequence orchestration

**No new enum values, no new columns, no new tables, no new models.**

## Partial Verification

Field-level states: verified / supported / unverified / unknown.

`field_verification_state()` attributes verification only when:
1. evidence exists for the field, AND
2. no contradiction, AND
3. independent corroboration per existing rules

Without independent corroboration: "supported" (not "verified").

Record-level status summarizes actual field states:
- all verified → verified
- any rejected → rejected
- some verified → reviewed
- none verified → pending

`record_status_implies_all_fields()` returns False for partial verification.

## Correction

`apply_correction()`:
- preserves prior audit history (caller records prior state)
- preserves provenance of replacement value
- does not mutate historical evidence invisibly
- invalidates prior verification where appropriate
- `stale_verification_inherited: False`

Stale verification after correction: `stale_verification_after_correction()` returns True when prior was verified and new is not.

## Re-verification

`reverify_field()` recalculates state from current evidence:
- source lost → unverified
- contradicted → unverified
- independent valid source → verified
- source only → supported

`reverify_after_source_invalidation()`:
- other independent valid source → verified (existing corroboration rules)
- no other source → unverified

## Source Invalidation

Facts depending on invalidated SOURCE A are no longer verified solely because of old state. If another independent valid source supports the same fact, existing corroboration rules apply. Analytics invalidation not implemented here — T5 owns that.

## Analytics Boundary

`analytics_eligibility_undelegated()` returns "T5_OWNED". T4 determines verification truth; T4 does NOT decide whether a verified field enters comparable retrieval, percentile calculations, aggregates, or confidence calculations.

## Tests

**New file:** `tests/test_external_verification.py` (36 tests, all passing)

| Test | Result |
|---|---|
| Fully supported reaches correct verification state | PASS |
| Partially supported remains partial | PASS |
| Verified field does not verify sibling fields | PASS |
| UNKNOWN remains non-zero and unverified | PASS |
| MISSING distinct from UNKNOWN/zero | PASS |
| NOT_APPLICABLE distinct from MISSING/UNKNOWN | PASS |
| STRIPPED cannot become verified | PASS |
| Independent agreeing sources preserve corroboration | PASS |
| Duplicate source not independent | PASS |
| Contradictory sources prevent promotion | PASS |
| Correction preserves audit history | PASS |
| Stale verification not inherited | PASS |
| Re-verification establishes new state | PASS |
| Re-verification invalidates when source lost | PASS |
| Invalidated source reconsiders dependent | PASS |
| Other valid source preserves verification | PASS |
| Cross-tenant modification not permitted | PASS |
| Privacy boundary intact | PASS |
| No-fabrication intact | PASS |
| T3 provenance regression green | PASS |
| Existing anonymizer regression green | PASS |
| Analytics eligibility not implemented in T4 | PASS |
| Verification truth for analytics exposes state | PASS |
| Record status summaries (all/none/partial/rejected) | PASS |
| Field verification states (verified/supported/unverified/unknown) | PASS |
| External verification routes through gate sequence | PASS |

## Regression

Existing regression suite: 56/56 passing
- test_anonymizer.py: 9
- test_no_fabrication_gate.py: 16
- test_privacy_acceptance_boundary.py: 12
- test_external_provenance.py: 19

Total: 92/92 passing

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
DOWNSTREAM_T5_T8 = NOT_EXECUTED
ANALYTICS_ELIGIBILITY_IMPLEMENTED = NO

## Governance Dependency

PHI_POLICY_GOVERNANCE_DEPENDENCY = OPEN

The canonical TrueVow privacy policy definition remains absent as a standalone repository file. Does not block T4 — T4 operates on contributions that have already survived the T2 privacy boundary.