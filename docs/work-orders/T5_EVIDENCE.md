# T5 — Analytics Eligibility Enforcement

**Ticket:** T5 (SETTLE-CONTRIB-TO-TICKETS)
**Status:** PASS
**Date:** 2026-08-31

---

## Method

Inspected existing analytics code paths. Implemented bounded application-layer
analytics eligibility capability reusing existing authorities. No database
change, no migration, no schema change.

## Verdict

T5_STATUS = PASS

---

## Existing Analytics Authorities Reused

| Authority | File | Reused |
|---|---|---|
| IntelligenceGate | `intelligence_gate.py` (MIN_AGGREGATE_N=50, hierarchical tiers) | YES — second gate only |
| Gate count method | `_count_approved()` (status='approved') | YES — eligibility filtering added BEFORE this |
| Case Bank models | `case_bank.py` (EstimateRequest, EstimateResponse, ComparableCase) | YES |
| own_case_only | `EstimateResponse.own_case_only` | YES |
| suppressed_features | `EstimateResponse.suppressed_features` | YES |
| County/state hierarchy | `IntelligenceGate.check()` tier logic | YES |
| Percentile calculations | `SettlementEstimator.estimate_settlement_range()` | YES — eligibility applied before |
| Confidence | `confidence_score.py` | YES |
| Verification truth | T4 (`external_verification.py`) | YES |

**No new analytics model, percentile engine, or confidence methodology created.**

## Implementation

**New file:** `app/services/analytics_eligibility.py`

Functions:
- `stored_is_not_verified()` / `stored_is_not_eligible()` — stored != verified != eligible
- `record_status_implies_field_eligibility()` — must be False; record-level must not manufacture field-level
- `required_dimensions_for_operation()` — required verified dimensions per operation
- `field_eligible_for_operation()` — field eligibility for specific operation
- `record_eligible_for_operation()` — record eligibility for specific operation
- `eligible_population()` — filter BEFORE aggregation
- `aggregate_count_eligible()` — count eligible, not merely stored
- `minimum_n_preserved()` / `minimum_n_counts_eligible_population()` — MIN_AGGREGATE_N is SECOND gate
- `confidence_eligibility()` — ineligible records do not increase confidence
- `comparable_retrieval_eligibility()` / `county_state_eligibility()` — fallback excludes ineligible
- `external_origin_auto_eligible()` / `external_origin_auto_ineligible()` — origin neither grants nor denies
- `unknown_as_zero()` / `missing_as_zero()` / `stripped_analytics()` / `not_applicable_semantics()` — semantic preservation
- `own_case_only_behavior()` — visibility != shared analytics eligibility
- `tenant_privacy_preserved()` — cross-tenant isolation
- `analytics_eligibility_decision()` — deterministic eligibility decision consuming T4 truth

## Operation → Required Verified Dimensions

Derived from existing estimator/intelligence_gate code paths. Not guessed.

| Analytical Operation | Required Verified Dimensions | Eligibility Filter Location | MIN-N / Suppression | Confidence Impact | Test Evidence |
|---|---|---|---|---|---|
| comparable_percentile | jurisdiction, case_type, settlement_amount | eligible_population() before aggregation | minimum_n_preserved() | confidence_eligibility() | test_analytics_eligibility.py |
| county_aggregation | jurisdiction, case_type, settlement_amount | county_state_eligibility() before county count | minimum_n_preserved() | confidence_eligibility() | test_analytics_eligibility.py |
| state_aggregation | jurisdiction, case_type, settlement_amount | county_state_eligibility() before state count | minimum_n_preserved() | confidence_eligibility() | test_analytics_eligibility.py |
| comparable_retrieval | jurisdiction, case_type, settlement_amount | comparable_retrieval_eligibility() | N/A | confidence_eligibility() | test_analytics_eligibility.py |
| confidence_calculation | jurisdiction, case_type, settlement_amount | eligible_population() before confidence | minimum_n_preserved() | confidence_based_on_eligible | test_analytics_eligibility.py |
| policy_limit_analysis | jurisdiction, policy_limits, settlement_amount | field_eligible_for_operation() | N/A | N/A | test_analytics_eligibility.py |
| comparative_fault_analysis | jurisdiction, comparative_negligence_pct | field_eligible_for_operation() | N/A | N/A | test_analytics_eligibility.py |
| lost_wages_analysis | jurisdiction, lost_wages | field_eligible_for_operation() | N/A | N/A | test_analytics_eligibility.py |

## STORED vs ELIGIBLE Population

| Metric | Value |
|---|---|
| Stored records (status='approved') | counted by existing `_count_approved()` |
| Eligible analytical population | `aggregate_count_eligible()` — verified dimensions only |
| MIN_AGGREGATE_N | 50 — counts eligible population, not merely stored |

Stored false positive example: 60 stored records, 40 eligible.
Stored would clear floor (True), eligible would not (False).

## Eligibility Before Aggregation

Correct order:
1. verification / eligibility
2. eligible analytical population
3. aggregation
4. minimum-N / privacy suppression
5. result

NOT: calculate using all records → hide/suppress unsafe output afterward.

## Record-Level vs Field-Level

Record-level eligibility must not manufacture field-level eligibility.
`record_status_implies_field_eligibility()` returns False for non-verified
fields. One unverified optional field does not make every verified field
ineligible unless the specific operation requires that field.

## Correction / Invalidation Propagation

T4 proved verification recalculates after material correction or source
invalidation. T5 proves analytics uses CURRENT eligibility:
- corrected old value ceases influencing future analytics
- re-verified replacement value may become eligible per existing rules
- invalidated field does not influence operation requiring that field

## Partial Verification

Preserved. NOT: if record != FULLY_VERIFIED, exclude everything. NOT: if record
has one verified field, include entire record. Eligibility is operation/dimension
aware.

## Semantic Absence

UNKNOWN, MISSING, NOT_APPLICABLE, STRIPPED preserved.
- UNKNOWN != numeric zero and != evidenced analytical value
- MISSING != numeric zero and != evidence of absence
- STRIPPED never analytics-eligible
- NOT_APPLICABLE preserves canonical behavior

## MIN_AGGREGATE_N

SECOND gate after eligibility. `minimum_n_counts_eligible_population()` proves
N counts eligible records, not merely stored records.

## Own-Case-Only

Visibility as own submitted record: True. Own-case context: True. Shared aggregate
eligibility: determined by `record_eligible_for_operation()`. Visibility != shared
analytics eligibility.

## Confidence

Ineligible records do not increase confidence, sample size, confidence factors,
or confidence labels. Confidence based on eligible analytical population.

## External Origin

External origin neither grants nor denies eligibility. Trust derives from
governed provenance and verification, not origin.

## Tests

**New file:** `tests/test_analytics_eligibility.py` (46 tests, all passing)

| Test | Result |
|---|---|
| Stored unverified does not influence | PASS |
| Verified eligible influences | PASS |
| Partially verified participates when dims verified | PASS |
| Same record excluded when dim unverified | PASS |
| Record status does not manufacture field eligibility | PASS |
| Unsupported field not influential | PASS |
| Contradicted field not influential | PASS |
| Invalidated field not influential | PASS |
| Corrected old value ceases | PASS |
| Re-verified replacement eligible | PASS |
| UNKNOWN not zero | PASS |
| MISSING not zero | PASS |
| STRIPPED never eligible | PASS |
| NOT_APPLICABLE semantics | PASS |
| MIN_N counts eligible population | PASS |
| Ineligible cannot clear floor | PASS |
| Eligible population preserves behavior | PASS |
| County aggregation excludes ineligible | PASS |
| State fallback excludes ineligible | PASS |
| Comparable retrieval excludes ineligible | PASS |
| Ineligible do not increase confidence | PASS |
| Duplicate rules intact | PASS |
| own_case_only consistent | PASS |
| External origin auto-eligible = NO | PASS |
| External origin auto-ineligible = NO | PASS |
| Tenant privacy intact | PASS |
| T2 privacy regression | PASS |
| T3 provenance regression | PASS |
| T4 verification regression | PASS |
| Case Bank regression | PASS |
| Full regression suite | PASS |

## Regression

Existing regression suite: 92/92 passing
- test_anonymizer.py: 9
- test_no_fabrication_gate.py: 16
- test_privacy_acceptance_boundary.py: 12
- test_external_provenance.py: 19
- test_external_verification.py: 36

Total: 138/138 passing

## Database Governance

DATABASE_CREATED = NO
MIGRATION_CREATED = NO
SCHEMA_CHANGED = NO
RLS_CHANGED = NO
T_PERSIST = NOT_REQUIRED

No analytics_eligible column added. T1 proved existing persistence + application
logic sufficient.

## Protected Boundaries

REC_000_MODIFIED = NO
C2_C7_C12_MODIFIED = NO
TRACE_MODIFIED = NO
CUSTOMER_PORTAL_MODIFIED = NO
DOWNSTREAM_T6_T8 = NOT_EXECUTED
NEW_ANALYTICS_MODEL_CREATED = NO

## Governance Dependency

PHI_POLICY_GOVERNANCE_DEPENDENCY = OPEN

The canonical TrueVow privacy policy definition remains absent as a standalone
repository file. Does not block T5 — T5 operates on contributions that have
already survived the T2 privacy boundary.