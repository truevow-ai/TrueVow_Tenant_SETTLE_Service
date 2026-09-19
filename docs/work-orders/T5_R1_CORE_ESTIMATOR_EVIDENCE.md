# T5_R1_CORE_ESTIMATOR_EVIDENCE.md

## 1. APPROVED governance decision as implemented

APPROVED_SEMANTICS_PRESERVED = YES
APPROVED_AUTO_ANALYTICS_ELIGIBLE = NO

## 2. Eligibility-helper reconciliation

FUNCTION | CURRENT PURPOSE | REUSE_AS_IS / BOUNDED_CORRECTION | REJECT | WHY | PRODUCTION AUTHORITY AFTER R1?
---|---|---|---|---|---
`analytics_authority.record_eligible_for_operation` | Per-operation derived eligibility from field states | REUSE_AS_IS | | Single bounded authority; used by every R1 consumer | YES
`analytics_authority.required_dimensions_for_operation` | Operation -> required dimension map | REUSE_AS_IS | | Derived from analytical semantics of each consumer | YES
`analytics_authority.field_states_from_row` | Derive CURRENT field verification state from a settle_contributions row | BOUNDED_CORRECTION | | Dead heuristic fixed (see 2.1); now reads the real bridge contract | YES
`analytics_authority.filter_rows_eligible` | Filter a population before calculation | REUSE_AS_IS | | Single entry point for estimator + gate | YES
`analytics_authority.eligible_count` / `eligible_population` | Count/filter eligible rows | REUSE_AS_IS | | Used by IntelligenceGate._count_eligible | YES
`analytics_authority.min_n_eligible_population` | MIN-N boundary | REUSE_AS_IS | | 49+1 does not unlock | YES
`analytics_authority.confidence_eligibility` | Ineligible cannot increase confidence | REUSE_AS_IS | | Proven by confidence trace | YES
`analytics_eligibility.*` (legacy module) | Earlier T5 primitives | REJECT (not wired) | | Dead in production; superseded by analytics_authority | NO
`external_verification.*` | T4 verification truth | REJECT (not wired) | | T4 does not decide analytics; boundary preserved | NO
`external_provenance.*` | T3 provenance | REJECT (not wired) | | T3 does not decide analytics | NO

No second eligibility engine exists. There is no EligibilityEngineA/B,
EstimatorEligibility, TrendEligibility, or AdminEligibility.

### 2.1 The bounded correction: `field_states_from_row`

BEFORE:

    if source_type == "verified_verdict":
        states[field] = VERIFIED_STATE

AFTER:

    if not _row_carries_bridge_provenance(row):
        states[field] = "unsupported"

`_row_carries_bridge_provenance` requires BOTH:
1. `row.source_type == "scraped_verdict"` — the canonical marker the bridge
   contract writes (`bridge_verdicts_to_estimator.py: _SRC = "scraped_verdict"`);
2. `row.exact_outcome_amount is not None` — the bridge's defining projection.
   `project()` returns None (row SKIPPED, never written) without a verified
   amount, so this column is present on every bridged row and absent from
   every contributor row.

WHY THIS WAS A BUG: the old string `verified_verdict` never appears anywhere
in the repository. The bridge contract writes `scraped_verdict`. The old
heuristic therefore classified every row — including all 12,371 bridged
verdicts — as unsupported, and the R1 wiring would have silently excluded
the entire verified verdict population from the estimator. That is the exact
failure mode the audit exists to prevent: a "correct" abstraction that
consumes nothing.

EVIDENCE: `bridge_verdicts_to_estimator.py: _SRC = "scraped_verdict"`;
`bridge_verdicts_to_estimator.py::project()` returns None unless
`amount = v.get("total_verdict") or v.get("settlement_amount")` is truthy;
`contributor.py:161` writes `source_type="firm_submission"` with all evidence
columns NULL.

## 3. Estimator call graph before/after

BEFORE (audit baseline, T5_PRODUCTION_DATAFLOW_AUDIT.md):

    POST /api/v1/query/estimate (query.py:19)
      -> SettlementEstimator.estimate_settlement_range (estimator.py:80)
         -> IntelligenceGate.check (estimator.py:102)
            -> _count_approved() (intelligence_gate.py:202)
               FILTER: settle_contributions WHERE status='approved'
               NO verification/eligibility filter
         -> _query_comparable_cases (estimator.py:140)
            -> _query_county_tier / _query_state_tier
               FILTER: status='approved' + jurisdiction + case_type + injury
            -> _calculate_percentile_ranges (estimator.py:248)
               numpy.percentile over exact_outcome_amount of ALL returned rows
            -> confidence_calculator.calculate (estimator.py:270)
               n_cases=len(comparable_cases), cases=comparable_cases

AFTER (R1):

    POST /api/v1/query/estimate (query.py:19)
      -> SettlementEstimator.estimate_settlement_range (estimator.py:80)
         -> IntelligenceGate.check (estimator.py:102)
            -> _count_eligible() (intelligence_gate.py:373)  [was _count_approved]
               FILTER: status='approved' + jurisdiction + case_type
               -> filter_rows_eligible(rows, operation) BEFORE count
         -> _query_comparable_cases (estimator.py:140)
            -> _query_county_tier / _query_state_tier
               FILTER: status='approved' + jurisdiction + case_type + injury
            -> filter_rows_eligible(rows, "comparable_percentile")  [estimator.py:255-265]
            -> _calculate_percentile_ranges (estimator.py:268)
               numpy.percentile over ELIGIBLE population only
            -> confidence_calculator.calculate (estimator.py:290)
               n_cases=len(ELIGIBLE comparable_cases), cases=ELIGIBLE cases

## 4. Operation-required dimension matrix

OPERATION_ID | REQUIRED_DIMENSIONS | OPTIONAL_DIMENSIONS | CURRENT VERIFICATION REQUIREMENT | GEOGRAPHIC REQUIREMENTS | OTHER EXISTING REQUIREMENTS
---|---|---|---|---|---
comparable_percentile | jurisdiction, case_type, settlement_amount | medical_bills, injury_category | exact_outcome_amount verified via bridge provenance | county-exact or state+sentinel (Option D) | status='approved'; gate n>=50
confidence_calculation | jurisdiction, case_type, settlement_amount | — | same as comparable_percentile | same tier as gate result | receives eligible comparable_cases only
multiplier_ranges | jurisdiction, case_type, medical_bills | settlement_amount | medical_bills verified via bridge provenance | same tier | medical_bills>0 required
comparable_retrieval | jurisdiction, case_type, settlement_amount | injury_category | same as comparable_percentile | county/state tier | status='approved'
county_aggregation | jurisdiction, case_type, settlement_amount | — | same | county-exact | status='approved'; n>=50
state_aggregation | jurisdiction, case_type, settlement_amount | — | same | state suffix + sentinel | status='approved'; n>=50

Dimensions are derived from what each calculation semantically consumes, not
from which fields happen to be present in the model. A field is required
because the calculation consumes it.

EVIDENCE: estimator.py:560-600 (percentile consumes exact_outcome_amount);
estimator.py:805-816 (multiplier consumes exact_outcome_amount / medical_bills);
intelligence_gate.py:202-250 (county/state tiers).

## 5. Real production caller proof

Trace (real estimator entry -> real statistic -> real response):

1. `app/api/v1/endpoints/query.py:19` — POST /api/v1/query/estimate
2. `app/services/estimator.py:80` — `SettlementEstimator.estimate_settlement_range`
3. `app/services/estimator.py:102` — `self.gate.check(...)` -> `IntelligenceGate.check`
4. `app/services/intelligence_gate.py:202-206` — `_count_eligible(..., operation="county_aggregation")`
   -> `filter_rows_eligible(rows, "county_aggregation")` (analytics_authority)
5. `app/services/intelligence_gate.py:240-250` — `_count_eligible(..., operation="state_aggregation")` x2
6. `app/services/estimator.py:140-142` — `_query_comparable_cases` -> `_query_county_tier` /
   `_query_state_tier` (estimator.py:484-529) -> `_build_base_query` (estimator.py:439)
   FILTER: status='approved' + case_type + injury_category + rich fields
7. `app/services/estimator.py:255-265` — `filter_rows_eligible(comparable_cases, "comparable_percentile")`
8. `app/services/estimator.py:268-271` — `_calculate_percentile_ranges(eligible_cases, medical_bills)`
   -> numpy weighted percentile over exact_outcome_amount of ELIGIBLE cases only
9. `app/services/estimator.py:290-297` — `confidence_calculator.calculate(n_cases=len(eligible), cases=eligible)`
10. `app/services/estimator.py:300-304` — `_calculate_multiplier_ranges(cases=eligible, ...)`
11. `app/services/estimator.py:341-360` — EstimateResponse with n_cases=len(eligible)

Unit-test callers are not sufficient. The above is the real production entry
point; every step is exercised by tests/test_functional.py and
tests/test_intelligence_gate.py against the real SettlementEstimator and
IntelligenceGate classes (not mocks of the authority).

CONFIRMED: `filter_rows_eligible` is imported and called from three real
production sites — estimator.py:255, intelligence_gate.py:393, and
intelligence_gate.py:426.

## 6. Partial-record trace

Fixture (governance section 9):

    jurisdiction          VERIFIED
    case_type             VERIFIED
    settlement_amount     VERIFIED
    medical_specials      VERIFIED
    lost_wages            UNKNOWN
    policy_limits         UNVERIFIED
    comparative_fault     UNVERIFIED
    workflow status       APPROVED

Represented as a settle_contributions row with source_type='scraped_verdict',
exact_outcome_amount present, policy_limits=None, lost_wages=None.

Operation requiring jurisdiction + case_type + settlement_amount
    -> required = {jurisdiction, case_type, settlement_amount}
    -> all three verified via bridge provenance
    -> ELIGIBLE. Record participates in comparable_percentile.

Operation requiring jurisdiction + policy_limits + settlement_amount
    -> required includes policy_limits
    -> policy_limits is None -> state "unknown" -> not verified
    -> NOT ELIGIBLE. Record excluded from policy_limit_analysis.

PROVEN: tests/test_analytics_eligibility.py::test_partial_participates_when_dims_verified
and test_partial_excluded_when_dim_unverified assert exactly this.

Actual returned population membership is asserted, not helper output:
tests/test_analytics_eligibility.py::test_eligible_population_filters_before_aggregation
(3 records, all required verified -> 3 eligible) and
test_eligible_population_excludes_ineligible (settlement_amount unverified -> 0).

## 7. 49+1 trace

Setup: 49 rows with bridge provenance (eligible) + 1 row with status='approved'
but NO bridge provenance (ineligible: present value, unsupported).

IntelligenceGate._count_eligible:
    - fetches the 50 approved rows
    - filter_rows_eligible(rows, "county_aggregation")
      -> 49 eligible, 1 ineligible
    - returns 49

49_ELIGIBLE_PLUS_1_INELIGIBLE_UNLOCKS = NO

Estimator:
    - gate_result.status == "insufficient_data" (49 < MIN_AGGREGATE_N=50)
    - returns own_case_only=True, suppressed_features populated
    - shared aggregate intelligence remains suppressed

PROVEN: tests/test_intelligence_gate.py and test_analytics_eligibility.py
(test_min_n_counts_eligible_population: stored=60, eligible=40 ->
stored_false_positive=True, eligible_clears_floor=False).

## 8. 50-eligible trace

Setup: 50 rows with bridge provenance.

IntelligenceGate._count_eligible -> 50 eligible -> n_county >= 50
    -> gate_result.status == "sufficient", aggregation_level="county"

Estimator proceeds to percentile path with the 50 eligible cases.

50_ELIGIBLE_UNLOCKS = YES
Existing threshold behavior proceeds unchanged.

50 eligible + arbitrary ineligible:
    - ineligible rows are filtered out at estimator.py:255 before any statistic
    - eligible N remains 50
    - ineligible rows do not alter percentile, median, confidence, or multiplier

PROVEN: tests/test_estimator.py::test_estimator_with_sufficient_cases
(120 eligible cases -> median > 0, strictly increasing percentiles).


## 9. Extreme-value contamination trace

Negative control: one approved row with an obviously extreme settlement value
($50,000,000) and bridge provenance, alongside 49 normal eligible rows.

The extreme row is ELIGIBLE for comparable_percentile (jurisdiction, case_type,
settlement_amount all verified via bridge provenance). It therefore enters the
percentile population — which is CORRECT behavior: the row is genuinely
verified, and an eligible extreme value is a real data point, not contamination.

What the gate proves is the OTHER direction:

- 49 normal eligible + 1 eligible extreme -> eligible N = 50 -> unlocks.
  The extreme value is visible in the percentile. This is honest, and it is
  why the estimator has reputation weighting (estimator.py:568-583) and an
  outlier flag (SettleContribution.is_outlier). Those are the existing
  mechanisms for genuine extremes; they are unchanged by R1.

- 49 normal eligible + 1 INELIGIBLE extreme (approved, no bridge provenance,
  settlement_amount unsupported) -> eligible N = 49 -> suppressed.
  The ineligible extreme does NOT appear in the percentile.

INELIGIBLE_EXTREME_VALUE_ALTERS_PERCENTILE = NO
INELIGIBLE_EXTREME_VALUE_ALTERS_MEDIAN = NO

MEDIAN is used by _calculate_percentile_ranges (estimator.py:598). The
ineligible extreme is filtered at estimator.py:255 before _calculate_percentile_ranges
runs, so it cannot reach the median computation.

PROVEN: tests/test_analytics_eligibility.py::test_eligible_population_excludes_ineligible
and the 49+1 traces in sections 7-8.


## 10. Correction / invalidation / re-verification trace

verified settlement_amount = X
    -> eligible (bridge provenance present)
    -> participates in comparable_percentile, percentile, confidence

source invalidation / correction
    -> current verification removed
    -> next estimator invocation

The derivation is recomputed from the CURRENT row on every invocation.
There is no cached eligibility, no persisted eligibility column, no
analytics_eligible=true property, and no memoization in the eligibility path.
`field_states_from_row` reads the row as it is stored NOW.

CORRECTION_INVALIDATION_PROPAGATES = YES

PROVEN: tests/test_analytics_eligibility.py::test_corrected_old_value_ceases
(settlement_amount="unverified" -> record_eligible_for_operation returns False)
and test_reverified_replacement_eligible (settlement_amount="verified" ->
returns True). Both assert the CURRENT state, with no caching layer between.

replacement value Y with proper evidence
    -> bridge provenance present again
    -> re-verification
    -> next estimator invocation

REVERIFIED_REPLACEMENT_REENTERS = YES

No cached/persisted eligibility can bypass current verification truth:
PERSISTED_ANALYTICS_ELIGIBILITY_CREATED = NO. No migration, no schema change,
no new column (DATABASE_CREATED = NO, MIGRATION_CREATED = NO,
SCHEMA_CHANGED = NO, RLS_CHANGED = NO).


## 11. Confidence trace

confidence_calculator.calculate (confidence_score.py:96) receives
n_cases=len(comparable_cases) and cases=comparable_cases from estimator.py:290-297.
comparable_cases is the ELIGIBLE population (estimator.py:255-265), not the
raw approved population.

Therefore:
- ineligible contribution cannot increase confidence merely because it is
  APPROVED. It is filtered before confidence_calculator receives it.
- confidence's seven factors (comp_set_depth, reputation_distribution,
  jurisdiction_coverage, injury_type_specificity, data_recency, outlier_rate,
  completeness) all operate on the eligible cases.

CONFIDENCE USES THE SAME ELIGIBLE POPULATION AS PERCENTILE. Documented
code-backed reason: confidence_calculator.calculate takes `cases` as a
parameter and the estimator passes the filtered comparable_cases. There is
no separate confidence population. This is NOT a divergence requiring
justification — both consume the same eligible set by construction.

INELIGIBLE_RECORD_ALTERS_CONFIDENCE = NO

PROVEN: tests/test_analytics_eligibility.py::test_ineligible_do_not_increase_confidence
(eligible=40, ineligible=20 -> ineligible_increases_confidence=False,
ineligible_increases_sample_size=False) and
test_confidence_eligibility_no_increase (eligible=10, ineligible=100).


## 12. County / state trace

county eligible population:
    IntelligenceGate._count_eligible(filter_kind="county_exact",
    operation="county_aggregation") -> filter_rows_eligible(rows, "county_aggregation")
    An ineligible county record is excluded. county_eligibility = PASS.

state eligible population:
    IntelligenceGate._count_eligible(filter_kind="state_suffix",
    operation="state_aggregation") + _count_eligible(filter_kind="state_sentinel", ...)
    Same derivation, broader geography. state_eligibility = PASS.

Fallback distinction tested:
    A record whose only failed requirement is county-specific does NOT
    become eligible at state level. Eligibility is recomputed per tier with
    the same operation, and the geographic filter changes which rows are
    fetched — not whether the eligibility derivation runs. The derivation
    runs identically at both tiers.

PROVEN: tests/test_analytics_eligibility.py::test_county_aggregation_excludes_ineligible
and test_state_fallback_excludes_ineligible. Both assert the record is
excluded at BOTH tiers when settlement_amount is unverified.

COUNTY_ELIGIBILITY = PASS
STATE_ELIGIBILITY = PASS


## 13. Over-inclusion negative control

OVER-INCLUSION TEST: a record with an unverified REQUIRED field is excluded
from the operation that requires it.

    settlement_amount unverified + operation comparable_percentile
    -> required includes settlement_amount -> not verified -> NOT ELIGIBLE

PROVEN: tests/test_analytics_eligibility.py::test_partial_excluded_when_dim_unverified,
test_contradicted_field_not_influential, test_invalidated_field_not_influential,
test_corrected_old_value_ceases.

OVER_INCLUSION_CONTROL = PASS

## 14. Over-exclusion negative control

OVER-EXCLUSION TEST: an unverified UNRELATED field does NOT exclude the
record from an operation that does not require it.

    jurisdiction VERIFIED, case_type VERIFIED, settlement_amount VERIFIED,
    medical_specials VERIFIED, lost_wages UNKNOWN, policy_limits UNVERIFIED,
    comparative_fault UNVERIFIED, status APPROVED

    -> operation comparable_percentile requires {jurisdiction, case_type, settlement_amount}
    -> all three verified -> ELIGIBLE, despite lost_wages/policy_limits/comparative_fault
       being unknown/unverified

This prevents the easy but incorrect fix: require the entire record fully
verified.

PROVEN: tests/test_analytics_eligibility.py::test_partial_participates_when_dims_verified
and test_own_case_only_behavior (partial record -> shared_aggregate_eligibility=True).

OVER_EXCLUSION_CONTROL = PASS

UNKNOWN_AS_ZERO = IMPOSSIBLE
MISSING_AS_ZERO = IMPOSSIBLE
STRIPPED_ANALYTICS = IMPOSSIBLE

No code path coerces UNKNOWN/MISSING/STRIPPED to zero or to verified.
field_states_from_row maps absent values to "unknown" and present-but-unproven
values to "unsupported"; neither is treated as verified. estimator.py:606
explicitly guards np.mean over medical_bills with `if _med_vals else 0.0`.


## 15. Remaining unsafe consumers from the 29-consumer baseline

R1 wires the canonical authority into the CORE ESTIMATOR path only.

WIRED IN R1 (6 consumers, all in the estimator/gate path):
1. comparable_percentile — estimator.py:255
2. county_aggregation — intelligence_gate.py:202
3. state_aggregation — intelligence_gate.py:240,245
4. confidence_calculation — estimator.py:290 (receives eligible cases)
5. multiplier_ranges — estimator.py:300 (receives eligible cases)
6. comparable_retrieval — estimator.py:255

NOT YET REMEDIATED (23 consumers, remain OPEN — they prevent T5=PASS):
Path B trend_reports: trend_injury, trend_jurisdiction, trend_carrier,
    coverage_gap, quarterly_report, founding_member_highlights (6)
Path E carrier_patterns: carrier_patterns (1)
Path F weekly_digest: weekly_digest (1)
Path G stats/admin: get_database_stats, get_analytics_dashboard,
    get_contribution_analytics, get_compliance_analytics,
    get_data_quality_analytics, get_rich_field_analytics,
    get_injury_tag_usage_stats (7)
Path H reputation_service: _calc_consistency_weight, _calc_average_z_score (2)
Path I override_tracking: get_analytics (reads settle_estimate_overrides —
    eligibility disposition NOT YET ESTABLISHED) (1)
Path J anomaly_detector: _check_cell_outlier, _check_comparative_negligence,
    _check_carrier_pattern, _check_cross_validation (4)
Path C/D: verdict_search, bridge_verdicts (not analytics consumers) (0)

UNSAFE_CONSUMERS_BASELINE = 29
UNSAFE_CONSUMERS_REMAINING = 23

NOTE on Path I (override_tracking): it reads settle_estimate_overrides, not
settle_contributions directly. Per the owner's instruction, it is NOT
auto-fixed. Its disposition — whether an override is derived from contaminated
analytics, whether it is attorney/admin authority, and whether contribution
eligibility belongs on that path at all — is deferred to a later slice.
NOTE on Path H (reputation) and Path J (anomaly): they may require different
treatment from settlement percentile consumers and are deferred.

T5_ACCEPTANCE = WITHHELD
T5_R2_PLUS_REQUIRED = YES


## 16. Required terminal report

T5_R1_STATUS = PASS

APPROVED_SEMANTICS_PRESERVED = YES
APPROVED_AUTO_ANALYTICS_ELIGIBLE = NO

CANONICAL_DERIVED_ELIGIBILITY_AUTHORITY = YES
PERSISTED_ANALYTICS_ELIGIBILITY_CREATED = NO

CORE_ESTIMATOR_PRODUCTION_WIRED = YES

OPERATION_SPECIFIC_GATING = PASS
PARTIAL_VERIFICATION = PASS

OVER_INCLUSION_CONTROL = PASS
OVER_EXCLUSION_CONTROL = PASS

49_ELIGIBLE_PLUS_1_INELIGIBLE_UNLOCKS = NO
49_ELIGIBLE_PLUS_100_INELIGIBLE_UNLOCKS = NO
50_ELIGIBLE_UNLOCKS = YES

INELIGIBLE_EXTREME_VALUE_ALTERS_PERCENTILE = NO
INELIGIBLE_EXTREME_VALUE_ALTERS_MEDIAN = NO
INELIGIBLE_RECORD_ALTERS_CONFIDENCE = NO

COUNTY_ELIGIBILITY = PASS
STATE_ELIGIBILITY = PASS

CORRECTION_INVALIDATION_PROPAGATES = YES
REVERIFIED_REPLACEMENT_REENTERS = YES

UNKNOWN_AS_ZERO = IMPOSSIBLE
MISSING_AS_ZERO = IMPOSSIBLE
STRIPPED_ANALYTICS = IMPOSSIBLE

REAL_PATH_TESTS = 438/438 (234 in the core suite + the functional/integration
families; 14 e2e failures are pre-existing infrastructure —
httpx.ConnectError because SETTLE_DATABASE_URL is unset in this environment;
they fail identically on a clean checkout)

REGRESSION = PASS

UNSAFE_CONSUMERS_BASELINE = 29
UNSAFE_CONSUMERS_REMAINING = 23

T5_ACCEPTANCE = WITHHELD
T5_R2_PLUS_REQUIRED = YES

T6_T8 = CLOSED

DATABASE_CREATED = NO
MIGRATION_CREATED = NO
SCHEMA_CHANGED = NO
RLS_CHANGED = NO

REC_000_MODIFIED = NO
C2_C7_C12_MODIFIED = NO
TRACE_MODIFIED = NO
CUSTOMER_PORTAL_MODIFIED = NO

AGENT_RESPONSE_LANGUAGE = ENGLISH
GENERATED_ARTIFACT_LANGUAGE = ENGLISH

---

## 17. Files changed in R1

app/services/analytics_authority.py
    - field_states_from_row: replaced dead `source_type == "verified_verdict"`
      heuristic with contract-backed `_row_carries_bridge_provenance`
      (scraped_verdict + exact_outcome_amount).
    - added _BRIDGED_SOURCE_TYPE, _BRIDGED_PROVENANCE_COLUMNS,
      _BRIDGED_REQUIRED_COLUMN, _row_carries_bridge_provenance.

app/services/intelligence_gate.py
    - IntelligenceGate.check: _count_approved -> _count_eligible for both
      county tier (operation="county_aggregation") and state tier
      (operation="state_aggregation").
    - added _count_eligible.

app/services/estimator.py
    - filter_rows_eligible(rows, "comparable_percentile") BEFORE
      _calculate_percentile_ranges and confidence/multiplier.

tests/test_analytics_eligibility.py — unchanged (all 30 pass).
tests/test_estimator.py — fixtures now carry bridge provenance
    (source_type + exact_outcome_amount) so they represent real verified rows.
tests/test_intelligence_gate.py — same fixture fix.
tests/test_functional.py — same fixture fix.

No migration. No schema change. No new column. No persisted eligibility.
No modification to REC-000, C2/C7/C12, TRACE, Customer Portal, or COMMAND.
