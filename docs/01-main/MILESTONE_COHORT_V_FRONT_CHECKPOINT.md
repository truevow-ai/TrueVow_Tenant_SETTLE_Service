# Cohort V-front Checkpoint — Frontend Pilot Wiring + Customer Portal Repo Init

**Date:** 2026-05-07
**Status:** UNVERIFIED (typecheck FAIL pre-existing, lint not configured) — code shipped to `origin/main` of customer portal repo

---

## Summary

Initialized customer portal git repo, pushed baseline to GitHub, then shipped V-front feature cohort: pilot-mode disclosure infrastructure (banner component + additive `EstimateResponse` type fields + Clerk `userId` forward proxy). Page wire-up + e2e DEFERRED — analysis page recon revealed scope mismatch requiring product decision (5 UI-only mock fields backend doesn't return).

## What was built/changed

**Customer portal repo (NEW git history at `https://github.com/truevow-ai/TrueVow_Tenant_Customer_Portal_Service.git`):**

- `c0e4aa0` chore(initial): baseline commit — 254 files (full project minus `.github/workflows/pricing-snapshot.yml`)
- `0cbc4c9` feat(settle): V-front feature cohort
  - `components/settle/PilotModeBanner.tsx` (NEW, +59) — reusable disclosure banner, three-layer transparency design (banner + confidence preserved as statistical + range_justification). Props: `nCases`, `stateLabel?`, `className?`. `data-testid="pilot-mode-banner"` for future e2e.
  - `lib/api/settle-client.ts` (+12/-2) — additive optional fields on `EstimateResponse`: `is_pilot_response`, `own_case_only`, `suppressed_features`, `aggregation_level`, `n_county`, `n_state`. Existing fields (`settlement_range`, `data_quality_score`, `factors_considered`) preserved for `settle/query/page.tsx` consumer.
  - `app/api/settle/analysis/route.ts` (+18/-5) — Clerk `await auth()` (v5+ async), conditional `X-Settle-User-Id` header forward.
  - `app/(dashboard)/dashboard/settle/reports/page.tsx` (+9/-5) — restored 6 escape-stripped mock strings (`$35k+`, `$9k-$12k`, `($100k)`, `$85k-$110k`, `$150k+`, `$15k-$25k`) to unblock typecheck of the V-front feature commit.
  - `.gitignore` (appended) — secret protection: `.env.backup*`, `.qoder/`, `test-results/`, `seed-output.txt`, `diff_output.txt`, `temp_*`, `check_*.py`, PNGs at root.

**SETTLE backend repo:** No source changes. Logs only at `logs/v_front_*`.

## Key decisions

- **Architect call: defer page wire-up** — analysis page recon (589 lines) revealed `MOCK_INTEL` has 5 UI-only fields backend doesn't return. Replacing it requires product decision (drop UI fields vs extend backend). Shipped reusable infrastructure instead so the page wire-up cohort lands in 1-2 hours when the product call is made. (No ADR — operational scope adjustment, not architectural.)
- **Additive types** on `EstimateResponse` instead of full alignment with backend Pydantic — preserves existing `settle/query/page.tsx` consumer.
- **Two-commit baseline pattern** — clean reviewer diff (chore baseline + feat V-front).
- **Surface-and-document** for 8 pre-existing TS errors in 5 unrelated files — out of V-front scope, captured in feature commit message.
- **Banner is render-conditional from caller** — banner does NOT check `is_pilot_response` itself; caller decides. Simplifies test surface and prevents banner from coupling to response shape.

## Verification evidence

**Truth commands run (customer portal, npm):**
- `git push origin master:main` — `c0e4aa0..0cbc4c9 master -> main` (verified `git ls-remote origin main` matches local HEAD)
- `npm run type-check` — FAIL with 8 pre-existing errors (zero introduced by V-front)
- `npm run lint` — NOT CONFIGURED (interactive ESLint setup prompt)
- `npm run build` — SKIPPED (would fail same as typecheck)

**Outputs captured:**
- `logs/v_front_remote_check.log`, `logs/v_front_init.log`
- `logs/v_front_baseline_msg.txt`, `logs/v_front_baseline_commit.log`, `logs/v_front_baseline_push.log`
- `logs/v_front_typecheck.log` (8 pre-existing errors documented)
- `logs/v_front_lint.log` (interactive prompt hang)
- `logs/v_front_feature_msg.txt`, `logs/v_front_feature_commit.log`, `logs/v_front_feature_push.log`

**Result:** PUSH DONE / typecheck UNVERIFIED (pre-existing, not V-front-caused) / lint UNVERIFIED (not configured)

## Pre-existing errors discovered (out of V-front scope, deferred to hygiene cohort)

8 TS errors across 5 files — captured verbatim in feature commit message body. Files:
- `app/(dashboard)/dashboard/settle/intake/lead/[id]/page.tsx:368` — `qualification_grade` not on `Lead`
- `app/(dashboard)/dashboard/settle/leverage/disbursement/page.tsx:117` — `net_to_client` missing
- `app/(dashboard)/dashboard/settle/leverage/history/page.tsx:6,29` — `ValidationHistoryItem`, `items`
- `app/(dashboard)/dashboard/settle/leverage/validate/page.tsx:174,176,177` — `suggestion` not on `ValidationError`
- `app/(dashboard)/dashboard/settle/query/page.tsx:82` — `getEstimate(req, apiKey)` 1-arg signature drift

## Three deferred items requiring user/product decision

1. **Page wire-up + e2e** (`app/(dashboard)/dashboard/settle/analysis/page.tsx`) — needs product call: keep mock UX (drop 5 UI-only fields), or extend backend response shape with `factors`, `risk_adjustments`, `insurer_behavior`, `confidence_score: number 0-10`, `confidence_reason`.
2. **Hygiene cohort** — 8 pre-existing TS errors above + ESLint config decision (Strict/Base).
3. **GitHub PAT `workflow` scope grant** — `.github/workflows/pricing-snapshot.yml` remains untracked on disk. Push refused until PAT scope is granted.

## Next steps

- Pick ONE of the three deferred items above as next cohort.
- **Recommended:** Hygiene cohort first (clears typecheck → unlocks `npm run build` truth gate → enables verifiable status on every future frontend cohort).

## Token efficiency note

**For the next session, read in this order:**
1. `docs/01-main/WORKING_CACHE.md` (current state, truth commands, next action)
2. This file (V-front cohort detail)
3. Cross-workspace skill: `.qoder/skills/cross-workspace-shipping.md`

**Don't re-read unless touching:**
- `lead-developer-playbook.md` / `staged-wiring-workflow.md` — stable companion skills
- Customer portal source files — only open when modifying them
