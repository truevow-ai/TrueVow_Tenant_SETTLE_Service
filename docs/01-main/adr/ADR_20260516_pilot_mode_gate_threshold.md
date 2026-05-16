# ADR: Pilot-Mode Gate Threshold (ADR S-2)

Date: 2026-05-16
Status: Accepted
Cohort: Cohort T (Pilot Mode launch enablement)

## Context

The IntelligenceGate enforces a production aggregation floor of `MIN_AGGREGATE_N = 50`
matching cases (county-tier preferred, state-tier fallback) before any aggregate
estimate is returned. This floor is the structural defense for the
**"Never Sell Empty Dashboards"** principle: customers must never see an estimate
generated from too few comparable cases, regardless of marketing pressure.

Phase 3.5 acquisition completed at 310/439 narratives (70.6%). Aggregate
state-tier coverage in several pilot states sits in the 10–40 range — sufficient
to demonstrate the product to a bounded set of vetted pilot users, but
insufficient to clear the production gate. We need a path to deliver real
estimates to a small, named pilot cohort while preserving the production
guarantee for all other users and a clear graduation criterion to
auto-disable pilot mode once the production floor is reached.

## Decision

Introduce **Pilot Mode**: a fail-closed, three-layer relaxation of the
state-tier gate that is enforceable only for explicitly enrolled pilot user IDs,
only when a feature flag is on, and only when the relaxed pool meets stricter
quality criteria.

### Three-layer transparency (defense-in-depth)

The "Never Sell Empty Dashboards" principle is preserved at three independent
layers — each layer is a hard gate, not a heuristic:

1. **State-tier-only relaxation.** County tier still requires `MIN_AGGREGATE_N = 50`.
   Pilot Mode never lowers the county floor. Only the state-tier fallback is
   relaxed to `PILOT_MIN_AGGREGATE_N = 10`.

2. **Sentinel injury-tag exclusion.** Rows whose `injury_category` is one of
   the 9 sentinel/unclassified variants
   (`general_personal_injury`, `motor_vehicle_accident`,
   `Unspecified`/`unspecified`/`UNSPECIFIED`,
   `Unknown`/`unknown`,
   `N/A`/`n/a`)
   do NOT count toward the pilot floor. Only rows with a real `InjuryTag`
   enum value count. Defense-in-depth case folding ensures scraper output
   variants are caught regardless of casing.

3. **Displayable-cases secondary gate.** After the gate passes, the estimator
   queries comparable cases and applies `PILOT_NARRATIVE_FLOOR = 5`: at least 5
   of the comparable cases must have a non-empty `case_narrative`. If fewer
   than 5 narrative-bearing cases survive the query, the response is
   suppressed (insufficient_data) — even if the count gate passed.

### Pilot user identification (fail-closed)

Pilot identification is bound to JWT user IDs: `auth.get("user_id", "") or ""`,
matched against a comma-separated allowlist in `SETTLE_PILOT_USER_IDS`.
There is **no `api_key` fallback**. An empty `user_id` resolves to
`is_pilot_user = False` regardless of feature-flag state. This guarantees
that anonymous or service-token traffic can never trigger pilot relaxation.

### UI signal (no confidence override)

Pilot responses are flagged via a dedicated `is_pilot_response: bool` field on
`AggregateGateResult` (propagated to `EstimateResponse`). The `confidence` field
is **NOT** overridden to a pilot-specific label. This is intentional:
downstream consumers (frontend, BI exports, partner integrations) treat
`confidence` as a stable enum (`high`/`medium`/`low`/`insufficient_data`).
Introducing a `pilot_phase` value would break that contract. UI surfaces the
pilot disclosure copy via `is_pilot_response`, while machine consumers continue
to read `confidence` unchanged.

### Justification copy

When `is_pilot_response = True`, the estimator's `_generate_justification`
emits a PILOT MODE disclosure paragraph that supersedes the standard
county/state branches. The copy explicitly states: pilot phase, statewide
aggregation, narrative-bearing case count, and the structural transparency
posture.

## Configuration

```python
# app/core/config.py
SETTLE_PILOT_MODE: bool = False              # Master flag; default off
SETTLE_PILOT_GATE_FLOOR: int = 10            # Reserved for future tunability
SETTLE_PILOT_NARRATIVE_FLOOR: int = 5        # Reserved for future tunability
SETTLE_PILOT_USER_IDS: str = ""              # Comma-separated allowlist
```

```python
# app/services/intelligence_gate.py (class constants)
PILOT_MIN_AGGREGATE_N: int = 10
PILOT_NARRATIVE_FLOOR: int = 5
INJURY_PILOT_INELIGIBLE: frozenset = frozenset({
    "general_personal_injury", "motor_vehicle_accident",
    "Unspecified", "unspecified", "UNSPECIFIED",
    "Unknown", "unknown", "N/A", "n/a",
})
```

## Implementation surface

| File | Change |
|---|---|
| `app/core/config.py` | +4 pilot settings |
| `app/services/intelligence_gate.py` | `is_pilot_response` field, pilot constants, sentinel set, `is_pilot_user` parameter on `check()`, pilot-mode branch after state-tier fail, `_count_pilot_eligible_state` helper |
| `app/models/case_bank.py` | `case_narrative` on `SettleContribution`; `is_pilot_response` on `EstimateResponse` |
| `app/services/estimator.py` | `is_pilot_user` parameter; displayable-cases secondary gate; pilot disclosure copy in `_generate_justification`; propagate `is_pilot_response` |
| `app/api/v1/endpoints/query.py` | Pilot user identification (no `api_key` fallback); pass `is_pilot_user` to estimator |
| `tests/test_intelligence_gate.py` | `TestPilotMode` (6 tests) |
| `tests/test_estimator.py` | `TestPilotModeEstimator` (4 tests) |

## Decision points (alternatives considered)

1. **PostgREST array-overlap operator for sentinel exclusion.**
   Rejected. Array-overlap operator support varies across PostgREST wrapper
   versions. Implemented Python-side post-filter instead: pull
   `(id, injury_category)` for state-tier rows (suffix + sentinel queries),
   filter against `InjuryTag` enum and the sentinel frozenset in Python, dedupe
   by id. Wrapper-agnostic and testable with simple Mock stubs.

2. **Override `confidence` to `pilot_phase` for pilot responses.**
   Rejected. Breaks the `confidence` enum contract for downstream consumers.
   Dedicated `is_pilot_response: bool` is a forward-compatible UI signal that
   does not perturb existing machine readers.

3. **Identify pilot users by API key.**
   Rejected. JWT `user_id` is the canonical identity. API keys are service
   tokens and should never carry pilot relaxation. Fail-closed on empty
   `user_id`.

4. **Single gate (just lower the count to 10).**
   Rejected. A single relaxation is brittle: a state with 10 sentinel-only
   rows and zero narratives would clear the gate and produce an empty
   dashboard. Three-layer defense ensures structural transparency at the
   data-quality, classification, and presentation layers.

## Graduation criteria (auto-disable)

Pilot Mode is a transitional posture. It SHOULD be disabled per state once
that state's real-tag, narrative-bearing case count clears the production
floor (`MIN_AGGREGATE_N = 50`). Operationally, this is achieved by removing
the state's pilot users from `SETTLE_PILOT_USER_IDS` once the production gate
clears for them naturally — they become production users with no code change.
Once all pilot users have graduated, set `SETTLE_PILOT_MODE = False`.

## Verification

- `tests/test_intelligence_gate.py::TestPilotMode` — 6 tests covering: flag
  off, pilot user passes at n=10, sentinel-only rows excluded, mixed tags
  partially count, non-pilot user blocked, county tier preserved.
- `tests/test_estimator.py::TestPilotModeEstimator` — 4 tests covering:
  displayable gate fires below floor, confidence not overridden, justification
  contains pilot disclosure copy, comparable_cases excludes non-narrative rows.
- All 29 tests in the two suites pass green
  (`logs/cohort_t_pytest.log`).

## Status

Accepted and shipped under Cohort T. Default flag state is OFF
(`SETTLE_PILOT_MODE = False`). Pilot launch is a configuration change, not a
code release.
