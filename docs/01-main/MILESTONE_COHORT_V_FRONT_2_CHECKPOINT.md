# Milestone / Cohort V-front-2 Checkpoint
Date: 2026-05-17
Status: DONE

## Summary

Wired the customer portal analysis page (`settle/analysis/page.tsx`) to the live SETTLE backend API, replacing the `MOCK_INTEL` constant with a real `settleClient.getEstimate()` call that fires after the billing consume flow succeeds. Aligned the frontend `EstimateResponse` interface with the backend Pydantic model (flat percentile fields, `n_cases`, `confidence` string, `comparable_cases` array, pilot-mode + guardrail fields). Dropped 5 mock-only UI fields per Option A product decision. Updated `settle/query/page.tsx` to use the new aligned field names.

## What was built/changed

- `lib/api/settle-client.ts` — `EstimateResponse` fully aligned with backend `EstimateResponse` Pydantic model (dropped stale `settlement_range.{low,mid,high}`, `estimate_id`, `data_quality_score`, `factors_considered`, `jurisdiction`, `case_type`, `created_at`; replaced with flat `percentile_25/median/percentile_75/percentile_95`, `n_cases`, `confidence`, `comparable_cases: ComparableCase[]`, `range_justification`, `query_id`, `queried_at`, `response_time_ms`). Added new `ComparableCase` interface.
- `app/(dashboard)/dashboard/settle/analysis/page.tsx` — Removed `MOCK_INTEL` constant (was ~15 lines of mock data). Added `useEffect` that calls `settleClient.getEstimate()` after `queryState === 'ready'` (billing consume succeeded). Rewrote Section 2 (Settlement Intelligence) rendering to use backend response fields. Added `PilotModeBanner` rendering when `is_pilot_response === true`. Added `own_case_only` guardrail banner. Shows `aggregation_level` labels (county vs statewide). Displays `comparable_cases` (top 5) and `range_justification`. Unified leverage-import and case-based paths into single flow (SettleQueryButton for billing, then live estimate fetch).
- `app/(dashboard)/dashboard/settle/query/page.tsx` — Updated to use aligned field names: `estimate.percentile_25`/`.median`/`.percentile_75` (was `.settlement_range.low/.mid/.high`), `estimate.confidence` (was `.settlement_range.confidence_level`), `estimate.n_cases` (was `.comparable_cases`), `estimate.query_id` (was `.estimate_id`). Dropped `data_quality_score` widget and `factors_considered` tag list (no backend equivalent).

## Key decisions

- **Option A chosen:** Drop 5 mock-only UI fields (`jurisdiction_weight`, `confidence_score` as numeric, `confidence_reason`, `factors`, `risk_adjustments`, `insurer_behavior`) rather than extending backend. These can be added to backend in a future cohort if product requires them.
- **Full type alignment** over backward-compatible additive approach. The stale `settlement_range: { low, mid, high }` shape was already broken against the real backend API — `query/page.tsx` would have gotten `undefined` on a real call. Better to fix now.
- **MOCK_CASES kept** — case input display (Section 1) still uses `MOCK_CASES`. These should be replaced with intake API data in a future cohort; they are orthogonal to the settlement intelligence wire-up.

## Verification evidence

- Commands run:
  - `npm run type-check` → 0 errors
  - `npm run lint` → exit 0 (pre-existing warnings only)
  - `npm run build` → 76/76 static pages, exit 0
- Result: PASS
- Git: committed as `5d11ef1`, pushed to `origin/main` (`df3e057..5d11ef1`)

## Next steps

- **Workflow scope grant** — user grants PAT `workflow` scope, push `.github/workflows/pricing-snapshot.yml`
- **MOCK_CASES removal** — replace case input display with intake API when service is live
- **End-to-end integration test** — deploy both repos, verify live billing flow + analysis fetch cycle

## Token efficiency note

- Read these for next session: `WORKING_CACHE.md` → this checkpoint → `IMPLEMENTATION_PROGRESS.md`
- Only re-read `settle-client.ts` or `analysis/page.tsx` if touching SETTLE frontend
