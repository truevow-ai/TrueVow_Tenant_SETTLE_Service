# T5 PRODUCTION DATAFLOW AUDIT — Adversarial

**Ticket:** T5 (SETTLE-CONTRIB-TO-TICKETS)
**Status:** T5_ACCEPTANCE = WITHHELD
**Date:** 2026-08-31

---

## 1. Executive Verdict

**T5_AUDIT_VERDICT = T5_PRODUCTION_WIRING_INCOMPLETE**

T5 eligibility primitives are correct and unit-tested. **No production analytics
path consumes them.** Every analytics calculation reads `settle_contributions`
filtered only by `status='approved'` plus jurisdiction/case_type/injury filters.
Verification-aware eligibility filtering is not present at any consumption point.

`analytics_eligibility.py` has ZERO production callers. It is imported only by
its own test file. This is a DEAD primitive in production.

## 2. Production Call Graph

### Path A — Settlement Range Estimation (the primary shared-intelligence path)

`POST /api/v1/query/estimate` (`query.py:19`)
  -> `SettlementEstimator(db)` (`estimator.py:87`)
  -> `estimator.estimate_settlement_range(request)` (`estimator.py:80`)
     -> `IntelligenceGate.check()` (`estimator.py:102`)
        -> `_count_approved()` (`intelligence_gate.py:202`)
           FILTER: `settle_contributions` WHERE `status='approved'
              + jurisdiction + case_type + carrier
           NO verification/eligibility filter
     -> `_query_comparable_cases()` (`estimator.py:140`)
        -> `_query_county_tier()` or `_query_state_tier()`
           FILTER: `status='approved'` + jurisdiction + case_type + injury_category
           NO verification/eligibility filter
     -> `_calculate_percentile_ranges()` (`estimator.py:248`)
        -> numpy.percentile on exact_outcome_amount of ALL returned rows
     -> `confidence_calculator.calculate()` (`estimator.py:270`)
        -> n_cases=len(comparable_cases), cases=comparable_cases
     -> `_calculate_multiplier_ranges()` (`estimator.py:280`)
     -> `overdemand_cliff_detector.detect_cliff()` (`estimator.py:289`)
     -> `outcome_distribution_analyzer.analyze()` (`estimator.py:302`)

### Path B — Trend / Market Reports

`TrendReportService.generate_quarterly_report()` (`trend_reports.py:112`)
  -> `db.table("settle_contributions").select("*").eq("status","approved")`
     (`trend_reports.py:142,146`)
  -> `_calculate_injury_trends()` (`trend_reports.py:215`)
  -> `_calculate_jurisdiction_trends()` (`trend_reports.py:274`)
  -> `_calculate_carrier_trends()` (`trend_reports.py:331`)
  -> `generate_coverage_gap_analysis()` (`trend_reports.py:389`)
     -> `settle_contributions` WHERE `status='approved'` (`trend_reports.py:396`)
  -> `generate_founding_member_highlights()` (`trend_reports.py:435`)
     -> `settle_contributions` WHERE `status='approved'` (`trend_reports.py:446`)

### Path C — Verdicts Bridge (data source, not analytics)

`bridge_verdicts_to_estimator.py` — projects verified `settle_verdicts` rows
into `settle_contributions` with `status='approved'`. This is the production
source of the estimator's population. It writes `status='approved'` for rows
that ARE verified verdicts; it is a data pipeline, not an analytics gate.

### Path D — Internal Verdict Search (NOT customer-facing)

`VerdictSearchService.search_verdicts()` (`verdict_search.py:32`) — 17-filter
search. NOT customer-facing. Uses `settle_verdicts` with `review_status` filter.
NOT part of shared settlement intelligence.

### Path E — Carrier Pattern Analytics (customer-facing)

`CarrierPatternService.get_carrier_patterns()` (`carrier_patterns.py:62`)
  -> `db.table("settle_contributions").select("*").eq("status","approved")`
     (`carrier_patterns.py:92-94`)
  -> filters jurisdiction/case_type/defendant_category
  -> computes case_count, avg/median/p25/p75 settlement, settlement_rate,
     trial_rate, lowball_indicator, avg_time_to_resolution_days

### Path F — Weekly Digest

`WeeklyDigestService.generate_digest()` (`weekly_digest.py:49`)
  -> `settle_contributions WHERE status='approved'` (`weekly_digest.py:73,95,108,127`)
  -> counts by jurisdiction/case_type, stale-data check, totals

### Path G — Stats / Dashboard

`stats.py:110-133` — public endpoints counting by status
`admin.py:788-1000` — admin analytics dashboard: counts by status, jurisdictions
`admin.py:1055-1116` — data quality analytics: outliers, approved rows with
   confidence_score/jurisdiction/case_type/injury_category/medical_bills
`admin.py:1451` — rich field analytics on approved rows
`admin.py:1309` — injury tag usage stats on approved rows

### Path H — Reputation Service (indirect)

`reputation_service.py:151-477` — reads approved rows by
   contributor_user_id/jurisdiction/case_type for consistency weight and
   average z-score calculations

### Path I — Override Tracking

`OverrideTrackingService.get_analytics()` (`override_tracking.py:109`) — reads
   `settle_estimate_overrides`, not settle_contributions directly

### Path J — Anomaly Detector (per-submission)

`anomaly_detector.py:107-504` — `_check_cell_outlier`, `_check_comparative_negligence`,
   `_check_carrier_pattern`, `_check_cross_validation` all query
   `settle_contributions WHERE status='approved'` + jurisdiction + case_type

## 3. Analytics Authority Inventory

| Component | File | Consumes settle_contributions | Eligibility-aware |
|---|---|---|---|
| estimate_settlement_range | estimator.py:80 | YES | NO |
| _count_approved | intelligence_gate.py:202 | YES | NO |
| _query_county_tier | estimator.py | YES | NO |
| _query_state_tier | estimator.py | YES | NO |
| _calculate_percentile_ranges | estimator.py | YES (via comparable_cases) | NO |
| confidence_calculator | confidence_score.py | YES (via cases param) | NO |
| _calculate_multiplier_ranges | estimator.py | YES | NO |
| overdemand_cliff_detector | overdemand_cliff.py | YES | NO |
| outcome_distribution_analyzer | outcome_distribution.py | YES | NO |
| generate_quarterly_report | trend_reports.py:112 | YES | NO |
| _calculate_injury_trends | trend_reports.py:215 | YES | NO |
| _calculate_jurisdiction_trends | trend_reports.py:274 | YES | NO |
| _calculate_carrier_trends | trend_reports.py:331 | YES | NO |
| generate_coverage_gap_analysis | trend_reports.py:389 | YES | NO |
| generate_founding_member_highlights | trend_reports.py:435 | YES | NO |
| get_carrier_patterns | carrier_patterns.py:62 | YES | NO |
| generate_digest | weekly_digest.py:49 | YES | NO |
| get_database_stats | stats.py:110 | YES | NO |
| get_analytics_dashboard | admin.py:788 | YES | NO |
| get_contribution_analytics | admin.py:943 | YES | NO |
| get_compliance_analytics | admin.py:1006 | YES | NO |
| get_data_quality_analytics | admin.py:1055 | YES | NO |
| get_rich_field_analytics | admin.py:1451 | YES | NO |
| get_injury_tag_usage_stats | admin.py:1309 | YES | NO |
| _check_cell_outlier | anomaly_detector.py:197 | YES | NO |
| _check_comparative_negligence | anomaly_detector.py:326 | YES | NO |
| _check_carrier_pattern | anomaly_detector.py:385 | YES | NO |
| _check_cross_validation | anomaly_detector.py:481 | YES | NO |
| _calc_consistency_weight | reputation_service.py:378 | YES | NO |
| _calc_average_z_score | reputation_service.py:446 | YES | NO |
| search_verdicts | verdict_search.py:32 | NO (settle_verdicts) | NO |

**ANALYTICS_PRODUCTION_PATHS_FOUND = 29 consumers, 10 execution paths.**

## 4. Field-Level Contamination Matrix

Legend: SAFE = no contamination possible; UNSAFE = contamination possible;
NOT_USED = not part of shared intelligence.

| ANALYTICAL_OPERATION | REAL_ENTRY_POINT | DATA_QUERY | REQUIRED_DIMENSIONS | VERIFICATION_REQUIRED_PER_DIM? | ELIGIBILITY_FILTER_ACTUALLY_CALLED? | FILTER_LOCATION | POPULATION_USED | COUNT/DENOMINATOR_SOURCE | STATISTIC_SOURCE | CONFIDENCE_POPULATION | MIN_N_POPULATION | COUNTY_POPULATION | STATE_FALLBACK_POPULATION | COMPARABLE_POPULATION | INELIGIBLE_FIELD_CAN_ENTER? | INELIGIBLE_RECORD_CAN_ENTER? | STATUS | EVIDENCE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| comparable_percentile | estimator.py:80 -> _query_county_tier | settle_contributions WHERE status='approved' | jurisdiction, case_type, settlement_amount | NO | NO | none | approved rows | _count_approved() | _calculate_percentile_ranges() | comparable_cases | _count_approved() | _query_county_tier | _query_state_tier | _query_comparable_cases() | YES | YES | UNSAFE | estimator.py:140-142, intelligence_gate.py:202 |
| confidence_calculation | estimator.py:270 | confidence_calculator.calculate(cases=comparable_cases) | jurisdiction, case_type, settlement_amount | NO | NO | none | comparable_cases | n_cases=len(comparable_cases) | confidence factors | comparable_cases | n_cases | n/a | n/a | comparable_cases | YES | YES | UNSAFE | estimator.py:270-277 |
| multiplier_ranges | estimator.py:280 | _calculate_multiplier_ranges(cases=comparable_cases) | jurisdiction, case_type, medical_bills | NO | NO | none | comparable_cases | n_cases | multiplier | comparable_cases | n/a | n/a | n/a | comparable_cases | YES | YES | UNSAFE | estimator.py:280-284 |
| county_aggregation | intelligence_gate.py:202 | _count_approved(filter_kind=county_exact) | jurisdiction, case_type | NO | NO | none | approved rows | _count_approved() | n_county | n/a | n_county | _count_approved() | n/a | n/a | YES | YES | UNSAFE | intelligence_gate.py:202-206 |
| state_aggregation | intelligence_gate.py:239 | _count_approved(filter_kind=state_suffix/sentinel) | jurisdiction, case_type | NO | NO | none | approved rows | _count_approved() | n_state | n/a | n_state | n/a | _count_approved() | n/a | YES | YES | UNSAFE | intelligence_gate.py:239 |
| comparable_retrieval | estimator.py:140 | _query_comparable_cases() | jurisdiction, case_type, settlement_amount | NO | NO | none | approved rows | n/a | n/a | n/a | n/a | n/a | n/a | _query_comparable_cases() | YES | YES | UNSAFE | estimator.py:140 |
| trend_injury | trend_reports.py:215 | settle_contributions WHERE status='approved' | injury_category | NO | NO | none | approved rows | total_cases | avg/median/p25/p75 | n/a | n/a | n/a | n/a | n/a | YES | YES | UNSAFE | trend_reports.py:142-146 |
| trend_jurisdiction | trend_reports.py:274 | settle_contributions WHERE status='approved' | jurisdiction | NO | NO | none | approved rows | total_cases | avg/median | n/a | n/a | n/a | n/a | n/a | YES | YES | UNSAFE | trend_reports.py:142-146 |
| trend_carrier | trend_reports.py:331 | settle_contributions WHERE status='approved' | insurance_carrier | NO | NO | none | approved rows | total_cases | settlement_rate | n/a | n/a | n/a | n/a | n/a | YES | YES | UNSAFE | trend_reports.py:142-146 |
| coverage_gap | trend_reports.py:396 | settle_contributions WHERE status='approved' | jurisdiction | NO | NO | none | approved rows | count | n/a | n/a | n/a | n/a | n/a | n/a | YES | YES | UNSAFE | trend_reports.py:396 |
| overdemand_cliff | estimator.py:289 | overdemand_cliff_detector.detect_cliff() | jurisdiction, case_type, injury_category | NO | NO | none | approved rows | n/a | cliff | n/a | n/a | n/a | n/a | n/a | YES | YES | UNSAFE | estimator.py:289-294 |
| outcome_distribution | estimator.py:302 | outcome_distribution_analyzer.analyze() | jurisdiction, case_type, injury_category | NO | NO | none | approved rows | n/a | distribution | n/a | n/a | n/a | n/a | n/a | YES | YES | UNSAFE | estimator.py:302-307 |
| verdict_search | verdict_search.py:32 | settle_verdicts (review_status filter) | n/a | N/A | NO | none | verdict rows | total_count | n/a | n/a | n/a | n/a | n/a | n/a | N/A | N/A | NOT_USED | verdict_search.py:32 |

## 5. Adversarial Case A — Partially Verified

jurisdiction VERIFIED, case_type VERIFIED, settlement_amount VERIFIED,
medical_specials VERIFIED, lost_wages UNKNOWN, policy_limits UNVERIFIED,
comparative_fault UNVERIFIED.

| Question | Answer | Why |
|---|---|---|
| A. Can it enter comparable_percentile? | YES | Required dims jurisdiction+case_type+settlement_amount are present; query filters only status='approved' |
| B. Can it enter policy_limit_analysis? | YES — UNSAFE | No operation-specific gating exists; policy_limits field present in row |
| C. Can settlement_amount alter percentiles? | YES | _calculate_percentile_ranges() consumes exact_outcome_amount of all comparable_cases |
| D. Can unverified policy_limits affect any calculation? | YES — UNSAFE | trend_carrier and carrier_pattern services consume insurance_carrier |
| E. Can UNKNOWN lost_wages become zero? | NO at query level; YES in application | DB stores NULL; no code coerces to 0, but no code enforces non-coercion either |
| F. Can it increase population count? | YES | _count_approved() counts it |
| G. Can it help satisfy MIN_AGGREGATE_N? | YES | _count_approved() returns 50 including it |
| H. Can it increase confidence? | YES | confidence_calculator receives it as a case |
| I. Can it appear in comparable retrieval? | YES | _query_comparable_cases() returns it |
| J. Can it enter county population? | YES | _count_approved(county_exact) counts it |
| K. Can it enter state fallback population? | YES | _count_approved(state_suffix/sentinel) counts it |

**Verdict: the case correctly participates in percentile operations (A, C) and
correctly should not participate in policy-limit operations (B) — but current
code permits both because no operation-specific gating exists.**

## 6. Adversarial Case B — Stored But UnVERIFIED

jurisdiction present but UNVERIFIED, case_type present but UNVERIFIED,
settlement_amount present but UNVERIFIED, status=approved.

| Question | Answer | Why |
|---|---|---|
| Can it increment _count_approved()? | YES | _count_approved() filters status='approved' only |
| Can it contribute toward MIN_AGGREGATE_N? | YES | Counts toward n_county/n_state |
| Can it enter percentile population? | YES | _query_comparable_cases() returns it |
| Can it alter median? | YES | median computed over exact_outcome_amount of all returned rows |
| Can it alter confidence? | YES | confidence_calculator receives it |
| Can it appear as comparable? | YES | _query_comparable_cases() returns it |
| Can it affect county/state fallback? | YES | _count_approved() counts it |

**This is the critical defect. A record being "approved" is NOT treated as
equivalent to analytically verified. _count_approved() has no verification
check. `status='approved'` is the only gate, and it conflates stored with
eligible.**

## 7. Adversarial Case C — Partial Verification

jurisdiction VERIFIED, case_type VERIFIED, settlement_amount VERIFIED,
policy_limits UNVERIFIED.

Operation 1 requires jurisdiction + case_type + settlement_amount.
Operation 2 requires jurisdiction + policy_limits + settlement_amount.

| Question | Answer | Why |
|---|---|---|
| Does current code admit the case to Operation 1? | YES — correct | Required dims present; no gating exists |
| Does current code exclude it from Operation 2? | NO — UNSAFE | No operation-specific gating; policy_limits field present in row |

**Current code does NOT distinguish operations. It cannot exclude the case
from Operation 2. Operation-specific dimension gating does not exist in
production.**

## 8. Adversarial Case D — Corrected / Invalidated

settlement_amount = 100000, verified, previously analytically usable.
Source invalidated / correction occurs. Verification removed/reconsidered.

| Question | Answer | Why |
|---|---|---|
| Does next calculation stop counting old 100000? | NO | _count_approved() filters status='approved' only; no verification check |
| Does it stop using it in percentiles? | NO | _query_comparable_cases() returns it regardless of verification |
| Does it stop using it in median? | NO | median computed over all returned rows |
| Does it stop using it for confidence? | NO | confidence_calculator receives it |
| Does it stop using it as comparable? | NO | _query_comparable_cases() returns it |
| Does it stop counting toward MIN_N? | NO | _count_approved() counts it |

**T4 proved verification truth changes. T5 does NOT prove analytics actually
consumes CURRENT verification truth. All six answers are NO.**

## 9. MINIMUM-N Contamination Test

49 ELIGIBLE records + 1 INELIGIBLE stored/approved record = 50 STORED records,
but 49 ELIGIBLE records.

| Question | Answer |
|---|---|
| Does _count_approved() return 50? | YES |
| Does shared aggregate intelligence become available? | YES |
| Is this a launch-blocking contamination defect? | YES |

**49_ELIGIBLE_PLUS_1_INELIGIBLE_UNLOCKS_SHARED_ANALYTICS = YES — DEFECT CONFIRMED.**

50 eligible + N ineligible: denominator/statistical population is based on
approved rows, not the correct eligible population for the operation.

## 10. Population Consistency Analysis

| Population | Source | Same eligibility definition? |
|---|---|---|
| count/denominator | _count_approved() | approved rows |
| percentile population | _query_comparable_cases() | approved rows |
| median population | _calculate_percentile_ranges() | approved rows |
| comparable population | _query_comparable_cases() | approved rows |
| confidence population | confidence_calculator.calculate() | comparable_cases |
| MIN_N population | _count_approved() | approved rows |
| county population | _count_approved(county_exact) | approved rows |
| state fallback population | _count_approved(state) | approved rows |

**All populations use the same definition: approved rows. No population
divergence found within the current architecture — but the single shared
definition is `status='approved'`, which is NOT eligibility-aware.**

**POPULATION_DIVERGENCE_FOUND = NO — but the shared definition is unsafe.**

## 11. T5 Helper Caller Inventory

| Function | DEFINED | PRODUCTION_CALLERS | TEST_CALLERS | DEAD_IN_PRODUCTION |
|---|---|---|---|---|
| eligible_population() | YES | NONE | test_analytics_eligibility.py | YES |
| aggregate_count_eligible() | YES | NONE | test_analytics_eligibility.py | YES |
| record_eligible_for_operation() | YES | NONE | test_analytics_eligibility.py | YES |
| required_dimensions_for_operation() | YES | NONE | test_analytics_eligibility.py | YES |
| field_eligible_for_operation() | YES | NONE | test_analytics_eligibility.py | YES |
| analytics_eligibility_decision() | YES | NONE | test_analytics_eligibility.py | YES |
| minimum_n_counts_eligible_population() | YES | NONE | test_analytics_eligibility.py | YES |
| confidence_eligibility() | YES | NONE | test_analytics_eligibility.py | YES |
| comparable_retrieval_eligibility() | YES | NONE | test_analytics_eligibility.py | YES |
| county_state_eligibility() | YES | NONE | test_analytics_eligibility.py | YES |
| external_origin_auto_eligible() | YES | NONE | test_analytics_eligibility.py | YES |
| analytics_eligibility.py (module) | YES | NONE | NONE | YES |

**ELIGIBILITY_HELPERS_PRODUCTION_WIRED = NO. Every T5 helper is DEAD in
production. It is imported only by its own test file.**

## 12. Remediation Map — NOT IMPLEMENTED

| EXACT_FUNCTION | CURRENT_BEHAVIOR | CONTAMINATION_RISK | REQUIRED_ELIGIBILITY_INPUTS | CORRECT_INSERTION_POINT | T5_PRIMITIVE_REUSABLE? | EXPECTED_TEST | CROSS_EFFECTS |
|---|---|---|---|---|---|---|---|
| IntelligenceGate._count_approved() | Counts status='approved' rows only | 1 ineligible record clears MIN_AGGREGATE_N | per-operation required verified dimensions | Add eligibility-aware population parameter; gate consumes it | PARTIAL — needs per-operation dimension map | 49 eligible + 1 ineligible does not unlock shared analytics | Affects county and state tier counts |
| SettlementEstimator._query_comparable_cases() | Returns approved rows + jurisdiction/case_type/injury | unverified fields enter percentiles, median, confidence, multiplier | jurisdiction, case_type, settlement_amount verified | Filter returned rows per operation before percentile | PARTIAL — record_eligible_for_operation() reusable | Case A participates in percentile, excluded from policy-limit | Affects confidence and multiplier populations |
| _calculate_percentile_ranges() | numpy.percentile over all comparable_cases | unverified settlement_amount alters percentiles | settlement_amount verified | Only eligible population enters | YES | Case A settlement_amount verified -> enters; Case B does not | Depends on comparable retrieval fix |
| confidence_calculator.calculate() | n_cases=len(comparable_cases); all cases | ineligible records increase confidence | jurisdiction, case_type, settlement_amount verified | Base n_cases on eligible population | YES | Case B does not increase confidence | Depends on comparable retrieval fix |
| _calculate_multiplier_ranges() | multiplier over all comparable_cases | unverified medical_bills alter multiplier | jurisdiction, case_type, medical_bills verified | Only eligible population | PARTIAL | Case A with verified medical_bills enters | Depends on comparable retrieval fix |
| overdemand_cliff_detector.detect_cliff() | jurisdiction+case_type+injury over approved rows | unverified rows alter cliff | jurisdiction, case_type, injury_category verified | Eligible population | PARTIAL | Case B does not alter cliff | Independent |
| outcome_distribution_analyzer.analyze() | jurisdiction+case_type+injury over approved rows | unverified rows alter distribution | jurisdiction, case_type, injury_category verified | Eligible population | PARTIAL | Case B does not alter distribution | Independent |
| TrendReportService.generate_quarterly_report() | settle_contributions WHERE status='approved' | unverified rows in quarterly stats | per-report required dimensions | Eligible population per report type | PARTIAL | Case B does not appear in quarterly report | Independent |
| TrendReportService._calculate_jurisdiction_trends() | avg/median over approved rows | unverified rows alter jurisdiction trends | jurisdiction verified | Eligible population | PARTIAL | Case B does not alter jurisdiction trend | Independent |
| TrendReportService.generate_coverage_gap_analysis() | count of approved rows | unverified rows alter coverage gap | jurisdiction verified | Eligible population | PARTIAL | Case B does not alter coverage analysis | Independent |
| CarrierPatternService.get_carrier_patterns() | settle_contributions WHERE status='approved' | unverified rows alter carrier patterns | jurisdiction, case_type, insurance_carrier verified | Eligible population | PARTIAL | Case B does not alter carrier patterns | Independent |
| WeeklyDigestService.generate_digest() | settle_contributions WHERE status='approved' | unverified rows in digest stats | jurisdiction, case_type verified | Eligible population | PARTIAL | Case B does not appear in digest | Independent |
| AnomalyDetector._check_cell_outlier() | settle_contributions WHERE status='approved' + jurisdiction + case_type | unverified rows alter outlier detection | jurisdiction, case_type verified | Eligible population | PARTIAL | Case B does not alter outlier detection | Independent |
| AnomalyDetector._check_carrier_pattern() | settle_contributions WHERE status='approved' + insurance_carrier + case_type | unverified rows alter carrier pattern check | insurance_carrier, case_type verified | Eligible population | PARTIAL | Case B does not alter carrier pattern check | Independent |
| ReputationService._calc_consistency_weight() | settle_contributions WHERE status='approved' + jurisdiction + case_type | unverified rows alter consistency weight | jurisdiction, case_type verified | Eligible population | PARTIAL | Case B does not alter consistency weight | Independent |
| ReputationService._calc_average_z_score() | settle_contributions WHERE status='approved' + jurisdiction + case_type | unverified rows alter z-score | jurisdiction, case_type verified | Eligible population | PARTIAL | Case B does not alter z-score | Independent |
| Admin get_data_quality_analytics() | settle_contributions WHERE status='approved' | unverified rows in data quality stats | jurisdiction, case_type verified | Eligible population | PARTIAL | Case B does not appear in data quality | Independent |
| Admin get_rich_field_analytics() | settle_contributions WHERE status='approved' | unverified rows in rich field stats | jurisdiction, case_type verified | Eligible population | PARTIAL | Case B does not appear in rich field analytics | Independent |

## 13. Population-Divergence Matrix

Requirement: NOT that every calculation uses one universal population, but
that every operation uses the population justified by the dimensions and
authority required for THAT operation. Every divergence must have existing
code/contract/methodological justification.

| Population Pair | Divergence? | CLASSIFICATION | Justification Evidence |
|---|---|---|---|
| MIN_N population vs percentile population | SAME (both approved rows) | UNJUSTIFIED — single shared definition is status='approved' | No operation-specific justification; both use _count_approved / approved rows |
| MIN_N population vs confidence population | SAME (both derived from approved rows / comparable_cases) | UNJUSTIFIED | confidence_calculator receives comparable_cases which are approved rows |
| county population vs state population | SAME (both _count_approved) | UNJUSTIFIED | No additional geographic requirement beyond status='approved' |
| percentile population vs comparable population | SAME (both _query_comparable_cases) | UNJUSTIFIED | No separate comparable selection logic |
| confidence population vs percentile population | SAME (both comparable_cases) | UNJUSTIFIED | confidence_calculator receives the same comparable_cases |
| confidence vs MIN_N (hypothetical stricter) | SAME | N/A | No existing methodology grants confidence stricter requirements |
| comparable vs MIN_N | SAME | UNJUSTIFIED | No existing code distinguishes them |

**POPULATION_DIVERGENCES = 1 (single shared definition, counted once)**
**JUSTIFIED_DIVERGENCES = 0**
**UNJUSTIFIED_DIVERGENCES = 1**
**UNKNOWN_DIVERGENCES = 0**

**The single divergence is that all 8 population types share
`status='approved'`, which is not eligibility-aware. There is no operation
that legitimately uses a stricter or different population. The divergence is
UNJUSTIFIED because no existing code, contract, or methodology grants any
operation a different population definition.**

## 14. `status='approved'` Provenance Analysis

This is the semantic question behind the whole defect.

### 4.1 Producers of `status='approved'`

| Producer | File | Transition Authority | Evidence |
|---|---|---|---|
| Admin `approve_contribution()` | `admin.py:146` | Admin action: pending -> approved | Sets `status='approved'` after admin approval |
| Verdicts bridge `project()` | `bridge_verdicts_to_estimator.py:143` | Data pipeline: verified verdict -> approved | Writes `status='approved'` for rows projected from verified `settle_verdicts` |
| Admin `update_contribution_fields()` | `admin.py:1224` | Admin field edit (can set status among other fields) | Whitelist includes 'status' |

### 4.2 Consumers of `status='approved'`

29 consumers listed in section 3. Every one treats `status='approved'` as the
analytics population gate.

### 4.3 Transition authority

The only authoritative transition is `admin.py:146` (admin approval of a
pending contribution). The verdicts bridge writes `status='approved'` as a
data-pipeline convention for genuinely verified verdicts.

**There is NO canonical authority establishing that `status='approved'`
equals analytically verified.** The admin approval path is a workflow state,
not a verification gate. It does not check field-level evidence.

### 4.4 Two readings

**Reading A — `approved` IS the analytics trust gate (historical intent).**
Evidence: the bridge writes `status='approved'` only for verified verdicts;
the estimator and gate use `status='approved'` as the sole population filter.
If this is the intent, the defect is that the admin approval path does NOT
guarantee verification — external/historical contributions approved through
`admin.py:146` carry no field-level verification guarantee.
**Remediation implication: tighten how records become approved, not just bolt
field filtering onto every query.**

**Reading B — `approved` is merely contribution workflow state.**
Evidence: `admin.py:146` is a generic admin action with no verification check;
`status` has values pending/approved/rejected/flagged which are workflow
states, not verification states.
If this is the intent, using `status='approved'` as the MIN-N population is
clearly wrong — `approved` is workflow state, not eligibility.
**Remediation implication: eligibility must be a separate, explicit, derived
property, not inherited from workflow state.**

### 4.5 Verdict

**UNKNOWN with a lean toward Reading B.** No canonical document in the
repository defines `status='approved'` as analytically verified. The bridge
script is a data-pipeline convention, not an analytics eligibility rule.
`admin.py:146` is a workflow transition with no verification check.

**This distinction materially changes the correct fix:**
- If Reading A: tighten the approval transition so only verified records
  become `approved`, and keep `status='approved'` as the population gate.
- If Reading B: introduce a separate eligibility property derived from
  verification truth (T4), and stop using `status='approved'` as the
  analytics population.

**Do not casually reinterpret `approved` as "analytics eligible." Do not
assume it is merely workflow state. This is a governance question that
requires owner decision, not a coding agent assumption.**

## 15. Unresolved Questions

1. **What does `status='approved'` canonically mean?** UNKNOWN — see section 14.
   This is the highest-priority unresolved question and may change the entire
   remediation approach.

2. Does the admin approval path (`admin.py:146`) carry any verification
   guarantee? No. It is a workflow transition with no field-level check.

3. Does the verdicts bridge establish verification for bridged rows? Yes —
   it projects verified `settle_verdicts` rows. But external/historical
   contributions entering `settle_contributions` directly do not inherit it.

4. Is `review_status` on `settle_verdicts` consumed by any analytics path?
   No. `verdict_search.py` consumes it for internal search only.

5. Is there existing canonical justification for `status='approved'` = eligible?
   Not found in repository.

6. Should eligibility be a persisted column, a derived property, or a
   query-time filter? NOT DECIDED — depends on the Reading A / Reading B
   resolution.

## 14. Exact Evidence References

- `query.py:19-119` — public estimate entry point
- `estimator.py:80-329` — estimate_settlement_range full path
- `estimator.py:140-142` — _query_comparable_cases
- `estimator.py:248-251` — _calculate_percentile_ranges call
- `estimator.py:270-277` — confidence_calculator.calculate call
- `estimator.py:280-284` — _calculate_multiplier_ranges call
- `estimator.py:289-294` — overdemand_cliff_detector call
- `estimator.py:302-307` — outcome_distribution_analyzer call
- `intelligence_gate.py:202-206` — _count_approved county tier
- `intelligence_gate.py:239` — _count_approved state tier
- `trend_reports.py:142-146` — quarterly report query
- `trend_reports.py:215-331` — trend calculations
- `trend_reports.py:396` — coverage gap query
- `bridge_verdicts_to_estimator.py:109-148` — verdict projection with status='approved'
- `verdict_search.py:32` — internal verdict search (not customer-facing)
- `analytics_eligibility.py` — dead in production, imported only by tests

## 15. Terminal State

T5_ACCEPTANCE = WITHHELD

T5_AUDIT_STATUS = COMPLETE

T5_AUDIT_VERDICT = T5_PRODUCTION_WIRING_INCOMPLETE

ELIGIBILITY_HELPERS_PRODUCTION_WIRED = NO

COUNT_APPROVED_ELIGIBILITY_AWARE = NO

MIN_N_ELIGIBILITY_AWARE = NO

PERCENTILE_ELIGIBILITY_AWARE = NO

MEDIAN_ELIGIBILITY_AWARE = NO

COMPARABLE_ELIGIBILITY_AWARE = NO

CONFIDENCE_ELIGIBILITY_AWARE = NO

COUNTY_ELIGIBILITY_AWARE = NO

STATE_FALLBACK_ELIGIBILITY_AWARE = NO

CORRECTION_INVALIDATION_PROPAGATES_TO_ANALYTICS = NO

49_ELIGIBLE_PLUS_1_INELIGIBLE_UNLOCKS_SHARED_ANALYTICS = YES

POPULATION_DIVERGENCES = 1
JUSTIFIED_DIVERGENCES = 0
UNJUSTIFIED_DIVERGENCES = 1
UNKNOWN_DIVERGENCES = 0

UNSAFE_PRODUCTION_PATHS = 29

REMEDIATION_IMPLEMENTED = NO

T6_T8 = CLOSED

PERSISTENCE_VERDICT = EXISTING_PERSISTENCE_SUFFICIENT
T_PERSIST = NOT_REQUIRED

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

STOP