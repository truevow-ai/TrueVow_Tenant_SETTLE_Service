# SETTLE Service — Implementation Progress

**Last Updated:** 2026-05-19
**Current Phase:** ALL PHASES COMPLETE (1-5) + E2E infrastructure ready
**Overall Status:** Backend DONE through Phase 5; 186/186 unit tests PASS; 23/24 DOCKET tests PASS; 14 E2E tests ready; Customer portal Phase 2.1-2.3 UI built and verified

---

## Operating model

- **Three-Mode Workflow:** Architect (plan) → Coder (implement) → QA (verify/commit/document)
- **Mode Switching:** `/mode architect` | `/mode coder` | `/mode qa`
- **Configuration:** `opencode.json` at repo root, `.opencode/skills/` for agent skills, `.opencode/rules/` for mode-specific rules
- **Founder:** Yasha (non-technical, self-funded, $30-50/month operating budget).
- **Backend repo:** this repo (`master` → `origin/main`).
- **Frontend repo:** `C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow_Tenant_Customer_Portal_Service` (NOT yet git-tracked; target remote `https://github.com/truevow-ai/TrueVow_Tenant_Customer_Portal_Service.git`).

---

## Milestone / Cohort Summary (chronological, newest first)

### Phase 1-5 Complete + E2E Infrastructure ✅ DONE
**Date:** 2026-05-19 · **Status:** DONE

**Phase 2.5 — Trend Studies / Market Reports:**
- `app/services/trend_reports.py` — quarterly reports, coverage gaps, founding member highlights
- `app/api/v1/endpoints/trend_reports.py` — 3 endpoints under `/api/v1/trends/`
- Tests: 6 new tests in `tests/test_phase2_5.py`

**Phase 3.1 — Multiplier Model Layer:**
- `app/services/estimator.py` — 3-tier multiplier (Community/State/Industry)
- `app/models/case_bank.py` — multiplier_method + active_method fields
- Tests: 6 new tests in `tests/test_phase3_1.py`

**Phase 3.2 — Overdemand Cliff Detection:**
- `app/services/overdemand_cliff.py` — cliff detection service
- `app/models/case_bank.py` — overdemand_cliff field
- Tests: 7 new tests in `tests/test_phase3_2.py`

**Phase 3.3 — Override Tracking:**
- `database/schemas/settle_override_tracking.sql` — override table
- `app/services/override_tracking.py` — tracking + analytics service
- `app/api/v1/endpoints/override_tracking.py` — admin endpoints
- Tests: 3 new tests in `tests/test_phase3_3.py`

**Phase 3.4 — Weekly Intelligence Digest:**
- `app/services/weekly_digest.py` — digest generator + HTML email template
- Tests: 2 new tests in `tests/test_phase3_4_5_6.py`

**Phase 3.5 — Recency Weighting:**
- `app/services/estimator.py` — time-decay factor (1.5x/<6mo → 0.7x/>2yr)

**Phase 4 — Litigation Outcome Distribution:**
- `app/services/outcome_distribution.py` — descriptive outcome analysis
- `app/models/case_bank.py` — outcome_distribution field
- Tests: 5 new tests in `tests/test_phase4.py`

**Phase 5 — Docket/Litigation Tracker (DOCKET-Service):**
- `DOCKET-Service/` — entire service scaffolded (app, models, services, API, tests)
- `DOCKET-Service/database/schemas/docket_supabase.sql` — 2 tables + 3 views
- `DOCKET-Service/app/services/scraping/courtlistener_scraper.py` — CourtListener scraper
- Tests: 23 tests (22 pass, 1 skipped)

**E2E Integration Testing:**
- `tests/test_e2e_integration.py` — 14 E2E API tests
- `scripts/run-e2e-tests.ps1` — automated test runner
- `docker-compose.e2e.yml` — full stack Docker Compose
- `docs/E2E_INTEGRATION_TESTING.md` — setup guide
- `docs/E2E_TEST_SUITE.md` — test scenario documentation

**Customer Portal UI:**
- Phase 2.1-2.3 UI built and verified (confidence score, advanced filters, carrier patterns)
- `CUSTOMER_PORTAL_UI_PLAN_REMAINING.md` — remaining UI plan (multiplier, cliff, outcome, digest)

**Test Results:**
- SETTLE-Service: 186/186 unit tests PASS
- DOCKET-Service: 23/24 tests PASS (1 skipped)
- E2E: 14 tests written, ready to run against live backend

**See:** `docs/01-main/MILESTONE_PHASE_1_5_CHECKPOINT.md` for full checkpoint

### Phase 1-2.3 + Three-Mode Workflow ✅ DONE
**Date:** 2026-05-19 · **Status:** DONE

**Phase 1 — Internal Verdict Research Engine:**
- `database/schemas/settle_verdicts_internal.sql` — 3 tables (settle_verdicts, settle_verdict_scrape_jobs, settle_verdict_search_history) + 4 analytics views
- `app/models/verdicts.py` — 10 Pydantic models for search, CRUD, scrape jobs
- `app/services/verdict_search.py` — 17-filter search engine, stats, CRUD, bulk insert with dedup
- `app/api/v1/endpoints/verdicts.py` — 9 endpoints under `/api/v1/internal/verdicts/` (admin-only)

**Phase 2.1 — Demand Confidence Score:**
- `app/services/confidence_score.py` — 7-factor weighted scoring (clamped 10-95), labels, warnings
- `app/models/case_bank.py` — ConfidenceScoreData + ConfidenceFactor added to EstimateResponse
- Estimator integration: confidence score calculated and returned with every estimate
- PDF report: factor breakdown table with visual bars on Page 3

**Phase 2.2 — Advanced Search Filters:**
- `app/models/case_bank.py` — 9 new optional filters on EstimateRequest (outcome_type, date ranges, medical bills range, exclude_outliers, min_reputation, comparative negligence)
- `app/services/estimator.py` — all filters applied in `_build_base_query`

**Phase 2.3 — Carrier Pattern Analytics:**
- `app/services/carrier_patterns.py` — aggregation by defendant category + industry, settlement rates, lowball indicators
- `app/api/v1/endpoints/carrier_analytics.py` — `GET /api/v1/analytics/carrier-patterns` (authenticated)
- PDF report: top 5 defendant category patterns table on Page 3

**Three-Mode Workflow Setup:**
- `opencode.json` — three-mode configuration (architect, coder, qa) with model settings, skills, rules
- `.opencode/skills/architect.md` — Architect agent skill documentation
- `.opencode/skills/coder.md` — Expert Coder agent skill documentation
- `.opencode/skills/qa.md` — QA & Testing agent skill documentation
- `.opencode/rules/architect-rules.md` — Architect mode rules
- `.opencode/rules/coder-rules.md` — Coder mode rules
- `.opencode/rules/qa-rules.md` — QA mode rules
- `.opencode/rules/architecture-validation.md` — Architecture validation checklist with phase matrix
- `.vscode/settings.json` — VSCode settings with opencode mode configuration
- `.vscode/extensions.json` — Recommended VSCode extensions
- `.cursor/rules/settle-rules.md` — Cursor agent rules
- `scripts/truth-check.ps1` — Automated truth command script
- `tests/test_phase1_phase2.py` — 13 new tests for all Phase 1-2.3 features

**Test Results:** 142/142 tests PASS (129 existing + 13 new)

**See:** `SETTLE_FEATURE_ROADMAP.md` for full roadmap; `.opencode/` for agent configuration

### Cohort V-front-2 — Analysis page wired to live backend API ✅ DONE

### Cohort V-front-2 — Analysis page wired to live backend API ✅ DONE
**Date:** 2026-05-17 · **Customer portal commit:** `5d11ef1` · **Status:** DONE

- Removed `MOCK_INTEL` constant; analysis page now fetches live estimate via `settleClient.getEstimate()` after billing consume flow
- Aligned frontend `EstimateResponse` with backend Pydantic shape (flat percentiles, `n_cases`, `confidence`, `ComparableCase[]`, pilot/guardrail fields)
- `PilotModeBanner` renders when `is_pilot_response === true`; `own_case_only` guardrail banner shows when applicable
- Updated `settle/query/page.tsx` to use aligned field names
- Dropped 5 mock-only UI fields per Option A product decision (jurisdiction_weight, confidence_score, confidence_reason, factors, risk_adjustments, insurer_behavior)
- All truth gates PASS: `npm run type-check` (0 errors), `npm run lint` (exit 0), `npm run build` (76/76 pages)
- See `docs/01-main/MILESTONE_COHORT_V_FRONT_2_CHECKPOINT.md`

### Cohort H — Customer portal hygiene (TS errors + ESLint + build) ✅ DONE
**Date:** 2026-05-16 · **Customer portal commit:** `df3e057` · **Status:** DONE

- Cleared all 8 pre-existing TS errors across 5 files (zero new code, just type alignment)
- Configured ESLint: `next/core-web-vitals` base + `no-unescaped-entities` off
- Fixed `server-only` import chain in `certificates.ts` (webpackIgnore on dynamic Clerk imports)
- All truth gates PASS: `npm run type-check` (0 errors), `npm run lint` (exit 0), `npm run build` (76/76 pages)
- See `docs/01-main/MILESTONE_COHORT_H_CHECKPOINT.md`

### Cohort V-front — Frontend pilot wiring + customer portal repo init ⚠ UNVERIFIED
**Date:** 2026-05-07 · **Customer portal commits:** `c0e4aa0` (baseline) + `0cbc4c9` (feature) · **Status:** UNVERIFIED

- Customer portal repo initialized at `https://github.com/truevow-ai/TrueVow_Tenant_Customer_Portal_Service.git` (master → main)
- `components/settle/PilotModeBanner.tsx` NEW — reusable pilot-mode disclosure (ADR S-2 v2 three-layer transparency)
- `lib/api/settle-client.ts` — 6 additive optional fields on `EstimateResponse` (preserves existing consumer)
- `app/api/settle/analysis/route.ts` — Clerk `await auth()` + conditional `X-Settle-User-Id` header forward
- `app/(dashboard)/dashboard/settle/reports/page.tsx` — 6 escape-stripped mock strings restored
- `.gitignore` — secret protection (`.env.backup*`, `.qoder/`, dev artifacts)
- **Deferred:** analysis page wire-up (MOCK_INTEL replacement needs product decision); 8 pre-existing TS errors (hygiene cohort); `.github/workflows/pricing-snapshot.yml` push (needs PAT `workflow` scope)
- See `docs/01-main/MILESTONE_COHORT_V_FRONT_CHECKPOINT.md`

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
| Customer portal HEAD (local + origin/main) | `5d11ef1` (Cohort V-front-2) |
| Backend commits ahead/behind | 0/0 |
| Customer portal commits ahead/behind | 0/0 |
| Backend tests | 43/43 PASS |
| Customer portal typecheck | PASS (0 errors) |
| Customer portal lint | PASS (exit 0, `next/core-web-vitals` configured) |
| Customer portal build | PASS (76/76 static pages) |
| Pilot infrastructure (backend) | Live, DORMANT (default-off flags) |
| Pilot infrastructure (frontend) | Banner + types + Clerk proxy + analysis page wire-up ALL LIVE |
| Customer Portal -> Backend integration | Clerk userId forwarded via `X-Settle-User-Id`; analysis page calls live estimate API after billing flow |
| Database (Supabase) | 440 approved + 29 pending + 0 rejected = 469 total |
| Real-county pairs at n≥50 | **0** (max real-county n=3) |
| Alembic head | `ed2900358f69` |
| Frontend repo | git-tracked since 2026-05-07 |
| Stash branch | `abandoned-auth-rewrite-202605` (local-only WIP, future ADR S-4 decision) |
| GitHub PAT | LACKS `workflow` scope (blocks `.github/workflows/*.yml` push) |

---

## What changed today (2026-05-17, Cohort V-front-2)

- Aligned frontend `EstimateResponse` with backend Pydantic shape (3 files changed, +257/-173)
- Removed `MOCK_INTEL` constant; analysis page now wired to live backend API
- `PilotModeBanner` + `own_case_only` guardrail integrated into analysis page rendering
- `settle/query/page.tsx` updated to use aligned field names
- Customer portal committed as `5d11ef1`, pushed to `origin/main`

## What changed 2026-05-16 (Cohort H)

- Cleared all 8 pre-existing TS errors in customer portal (5 files, 7 type fixes)
- Configured ESLint with `next/core-web-vitals` base + disabled `no-unescaped-entities`
- Fixed `server-only` webpack import chain in `certificates.ts` (webpackIgnore directive)
- All three frontend truth gates now PASS: typecheck, lint, build
- Customer portal status upgraded from UNVERIFIED to DONE through Cohort H

## What changed 2026-05-07

- Cohort V-front shipped end-to-end on combined architect+executor mode (Autonomy Calibration unit-scoped pattern)
- Customer portal repo initialized — first git history (255 baseline files → 254 after dropping unpushable workflow file)
- Both customer portal commits live on `origin/main` (`c0e4aa0` baseline + `0cbc4c9` V-front feature)
- Pilot Mode disclosure infrastructure LIVE in customer portal (dormant until analysis page wire-up cohort)
- New skill captured: `.qoder/skills/cross-workspace-shipping.md` (PowerShell git hardening + Qoder sandbox + autonomy patterns)
- New checkpoint: `docs/01-main/MILESTONE_COHORT_V_FRONT_CHECKPOINT.md`

## What changed 2026-05-16

- Pushed Cohort U-back to origin/main (`c43d81a..91a775f`)
- Backend pilot infrastructure FULL in remote (T v2 + U-back bridge)
- Bank-cache refresh: this file, `WORKING_CACHE.md`, two missing checkpoints created
- Operating mode transitioned to interim architect+executor (Hyperagent credits depleted)

---

## Next single action

**Pick ONE of remaining items:**

1. **Workflow grant** — user grants PAT `workflow` scope, push `.github/workflows/pricing-snapshot.yml`.
2. **MOCK_CASES removal** — replace case input display with intake API data when intake service is live.
3. **End-to-end integration test** — deploy backend + portal, verify live billing flow + analysis fetch cycle.

**Recommended:** End-to-end integration test (validates the full V-front-2 wire-up against a running backend).

---

## Token efficiency note

**Read these in order for new session orientation:**
1. `docs/01-main/WORKING_CACHE.md` — current state, truth commands, next action
2. `docs/01-main/IMPLEMENTATION_PROGRESS.md` — this file
3. `docs/01-main/MILESTONE_COHORT_V_FRONT_2_CHECKPOINT.md` — most recent unit-of-work
4. `.qoder/skills/cross-workspace-shipping.md` — autonomy + PowerShell + cross-workspace patterns learned in V-front
5. `docs/01-main/adr/ADR_20260516_pilot_mode_gate_threshold.md` — live pilot mode design

**Don't re-read unless touching:**
- Implementation files (auth.py, estimator.py, intelligence_gate.py) — stable and tested
- Archive documentation — historical reference only
