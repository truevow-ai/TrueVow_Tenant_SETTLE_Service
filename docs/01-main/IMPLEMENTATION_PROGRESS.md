# SETTLE Service — Implementation Progress

**Last Updated:** 2026-05-16
**Current Phase:** Cohort U-back complete; Cohort V-front pending
**Overall Status:** DONE (backend pilot infrastructure live in remote; frontend pilot wiring pending)

---

## Operating model

- **Architect + Executor:** Currently combined (interim Qoder-only mode after Hyperagent architect credits depleted on 2026-05-16). Yasha drives priority via trigger words; agent designs cohorts + executes.
- **Founder:** Yasha (non-technical, self-funded, $30-50/month operating budget).
- **Backend repo:** this repo (`master` → `origin/main`).
- **Frontend repo:** `C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow_Tenant_Customer_Portal_Service` (NOT yet git-tracked; target remote `https://github.com/truevow-ai/TrueVow_Tenant_Customer_Portal_Service.git`).

---

## Milestone / Cohort Summary (chronological, newest first)

### Cohort U-back — X-Settle-User-Id header bridge ✅ SHIPPED
**Date:** 2026-05-16 · **Commit:** `91a775f` · **Status:** DONE (on origin/main)

- `app/api/v1/endpoints/query.py` — added `Request` param + `X-Settle-User-Id` header forwarding with auth-method guard
- `tests/test_functional.py` — added `TestPilotUserIdentification` (3 tests, estimator-spy pattern)
- `tests/conftest.py` — patched `settings.USE_MOCK_DATA` on live Pydantic singleton (side-effect: fixed 4 pre-existing 401 failures)
- `docs/01-main/adr/ADR_20260516_pilot_mode_gate_threshold.md` — 2026-05-16 addendum (trust model + future ADR S-3)
- 43/43 tests PASS · See `docs/01-main/MILESTONE_COHORT_U_BACK_CHECKPOINT.md`

### Cohort T v2 — Pilot Mode Gate ✅ SHIPPED
**Date:** 2026-05-16 · **Commit:** `c43d81a` · **Status:** DONE (on origin/main, DORMANT via default-off flags)

- ADR S-2 implementation: three-layer transparency (state-tier-only relaxation, sentinel-tag exclusion via `INJURY_PILOT_INELIGIBLE`, displayable-cases secondary gate)
- New env vars: `SETTLE_PILOT_MODE`, `SETTLE_PILOT_USER_IDS`, `SETTLE_PILOT_GATE_FLOOR=10`, `SETTLE_PILOT_NARRATIVE_FLOOR=5`
- `EstimateResponse.is_pilot_response: bool` field for UI signaling
- Activation = env-var commit (no code release); rollback = unset env var
- See `docs/01-main/MILESTONE_COHORT_T_CHECKPOINT.md`

### Phase 3.5 — Real-narrative acquisition ✅ SHIPPED
**Commit:** `0106555`

- Fetched real prose narratives from `news_provenance` URLs (90.7% coverage, 310/439 populated, 70.6% overall)
- 24 upgrades from `structured_field_inference` → `rule_engine_*`; 286 newly-classified rows
- Top tags: death=57, TBI=41, fracture=38, spinal=37, soft_tissue=34
- **Empirical finding:** Real-county pairs at n≥50 = 0 (max real-county n=3). Confirmed gap is data-volume, not classification quality.

### Phase 3 B/C — Schema migration + pseudo-narrative pass ✅ SHIPPED
**Commits:** `fd70a04`, `0cc3303`

- Added `injury_classification` JSONB, `case_narrative` TEXT, `injury_review_queue` table
- Lifted 42/469 rows with legacy tags into audit trail
- Pseudo-narrative reclassification: 47 reclassifications, 5 truly-new cells. **Limited yield confirmed** — structured fields alone don't carry contextual signals.

### Cohort S-1.1 — Deterministic injury classifier ✅ SHIPPED
**Commit:** `fd7e70a` · **Library:** `app/services/injury_classifier/`

- 17 closed-set `InjuryTag` enum values, regex-based, zero LLM dependencies
- Audit-trail JSONB schema; fixed confidence schedule (0.99/0.95/0.80/0.70/0.60/0.00)
- 7 review-trigger rules; `INJURY_PILOT_INELIGIBLE` frozenset for sentinel exclusion
- Version `1.1.0` (Phase 3.B added `synthesize_pseudo_narrative()`)

### Cohort R — Hierarchical gate ✅ SHIPPED
County → state → suppressed fallback. State-tier pools all FL data including `FL (Unknown County)` sentinel.

### Phase 2.X — IntelligenceGate + estimator wiring ✅ SHIPPED
**Commits:** `059e74b`, `3c602cb`, `0c6e338`, `7847c54`, others

- `IntelligenceGate` service + unit tests
- `SettlementEstimator` wired through gate + ilike-based cohort query
- Hierarchical gate fallback + stashed-dependency purge
- Empty-pool guards for state-tier-pass + injury-filter-empty

### Milestone 3 — Core API Implementation ✅ SHIPPED (Feb 28, 2026)
Database-backed API key auth (SHA-256), admin auth with access levels, all endpoints connected, email notifications via Resend, 29/29 tests passing. See `docs/01-main/MILESTONE_3_CHECKPOINT.md`.

### Milestones 1-2 ✅ SHIPPED
Project cleanup + organization (1); database + stats implementation (2).

---

## ADRs landed

| ADR | File | Topic |
|---|---|---|
| S-1.1 | `ADR_20260513_deterministic_injury_classifier.md` | 17-tag classifier, regex, zero LLM |
| S-2 | `ADR_20260516_pilot_mode_gate_threshold.md` | Pilot Mode gate threshold + X-Settle-User-Id addendum |

Three untracked draft ADRs at `docs/01-main/adr/ADR_20260507_*.md` (demand-driven scraper orchestration, multi-tag injury reclassification, query demand log) — preserved out-of-scope, may land in a future hygiene cohort.

---

## Current Status

| Concern | State |
|---|---|
| Backend HEAD (local + origin/main) | `91a775f` (Cohort U-back) |
| Commits ahead/behind | 0/0 ✅ |
| Backend tests | 43/43 PASS |
| Pilot infrastructure | Live, DORMANT (default-off flags) |
| Customer Portal → Backend integration | Proxies exist, MOCK_INTEL still renders, Clerk userId NOT forwarded yet |
| Database (Supabase) | 440 approved + 29 pending + 0 rejected = 469 total |
| Real-county pairs at n≥50 | **0** (max real-county n=3) |
| Alembic head | `ed2900358f69` |
| Frontend repo | NOT git-tracked yet |
| Stash branch | `abandoned-auth-rewrite-202605` (local-only WIP, future ADR S-4 decision) |

---

## What changed today (2026-05-16)

- Pushed Cohort U-back to origin/main (`c43d81a..91a775f`)
- Backend pilot infrastructure FULL in remote (T v2 + U-back bridge)
- Bank-cache refresh: this file, `WORKING_CACHE.md`, two missing checkpoints created
- Operating mode transitioned to interim architect+executor (Hyperagent credits depleted)

---

## Next single action

**Cohort V-front** — Frontend pilot wiring + customer portal git initialization. Awaiting Yasha trigger:
- `draft V-front` → I draft directive to `docs/01-main/COHORT_V_FRONT_DIRECTIVE.md` for review
- `go V-front` → I execute end-to-end (git init customer portal + wire pilot bridge + tests)

---

## Token efficiency note

**Read these in order for new session orientation:**
1. `docs/01-main/WORKING_CACHE.md` — current state, truth commands, next action
2. `docs/01-main/IMPLEMENTATION_PROGRESS.md` — this file
3. `docs/01-main/MILESTONE_COHORT_U_BACK_CHECKPOINT.md` — most recent unit-of-work
4. `docs/01-main/adr/ADR_20260516_pilot_mode_gate_threshold.md` — live pilot mode design

**Don't re-read unless touching:**
- Implementation files (auth.py, estimator.py, intelligence_gate.py) — stable and tested
- Archive documentation — historical reference only
