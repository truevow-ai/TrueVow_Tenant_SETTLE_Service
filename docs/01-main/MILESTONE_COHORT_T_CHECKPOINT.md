# Milestone Checkpoint — Cohort T v2 (Pilot Mode Gate)
**Date:** 2026-05-16
**Commit:** `c43d81a`
**Status:** DONE (shipped to origin/main, DORMANT via default-off flags)
**ADR:** S-2 (`docs/01-main/adr/ADR_20260516_pilot_mode_gate_threshold.md`)

---

## Summary

Pilot Mode infrastructure implemented as a feature-flagged extension of the IntelligenceGate. Provides a launch path for self-funded operation: at-current-data-volume the production gate (n≥50 per county+injury+case_type triple) cannot be met, so an opt-in pilot tier with relaxed floor + transparency safeguards enables real attorney usage while preserving the "Never Sell Empty Dashboards" principle. Activation is a configuration commit, not a code release.

## What was built/changed

- `app/services/intelligence_gate.py` — pilot-tier gate logic with three-layer transparency
- `app/services/estimator.py` — pilot-aware integration; `is_pilot_user` plumbed through estimate path; displayable-cases secondary gate; updated justification copy
- `app/services/injury_classifier/rules.py` — added `INJURY_PILOT_INELIGIBLE` frozenset (filters scraper-fallback sentinel tags from pilot eligibility count)
- `app/core/config.py` — new env-var settings: `SETTLE_PILOT_MODE`, `SETTLE_PILOT_USER_IDS`, `SETTLE_PILOT_GATE_FLOOR=10`, `SETTLE_PILOT_NARRATIVE_FLOOR=5`
- `app/api/v1/endpoints/query.py` — pilot user identification (allowlist check); `EstimateResponse.is_pilot_response: bool` field for UI signaling
- `tests/test_intelligence_gate.py` + `tests/test_estimator.py` — pilot path coverage
- `docs/01-main/adr/ADR_20260516_pilot_mode_gate_threshold.md` — ADR S-2 (rationale, three-layer design, graduation criteria v2)

## Key decisions

- **State-tier-only relaxation:** county floor untouched at n≥50; pilot mode only relaxes the state-tier fallback to n≥10. Preserves "no false county precision" guarantee.
- **Sentinel-tag exclusion:** scraper-fallback tags (`general_personal_injury`, `motor_vehicle_accident`, etc.) excluded from pilot eligibility count via `INJURY_PILOT_INELIGIBLE` frozenset. Prevents pilot launch on junk-tagged rows.
- **Displayable-cases secondary gate:** `PILOT_NARRATIVE_FLOOR=5` minimum narrative-bearing rows required before pilot response renders. Ensures attorney sees real source material, not phantom data points.
- **Default-off flags + empty allowlist = no-op production deployment.** Canonical pattern for any feature-flagged launch. Rollback = unset env var, no code revert needed.
- **Architect-side v1→v2 pre-fire review** caught 6 transparency-critical gaps before code fired. Pattern banked.

## Verification evidence

- **Commands run:**
  - `python -m pytest tests/ -v` → 40/40 PASS at commit time (pre-U-back baseline)
  - `git push origin master:main` → `c43d81a` landed on origin/main
- **Logs:** `logs/cohort_t_pytest_v2.log`, `logs/cohort_t_push.log`
- **Result:** ✅ PASS

## Production behavior at SHIP time

- `SETTLE_PILOT_MODE` defaults to `false` → all attorney queries take production gate path → behavior UNCHANGED for live users
- `SETTLE_PILOT_USER_IDS` defaults to `""` → even if pilot mode flipped on accidentally, allowlist-empty = no users qualify
- Two-key safety: requires BOTH env var flip AND explicit user-id allowlisting

## Next steps (gated on Yasha)

- Cohort U-back (X-Settle-User-Id header bridge) — DONE at `91a775f`
- Cohort V-front (frontend pilot wiring) — PENDING
- Cohort W (deployment) — PENDING
- Cohort X (first pilot onboarding) — PENDING (depends on V-front + W)

## Token efficiency note

**For next-session orientation:** Read `IMPLEMENTATION_PROGRESS.md` + `WORKING_CACHE.md` + ADR S-2 only. Source files (`intelligence_gate.py`, `estimator.py`) are stable and tested; open only if a behavior bug surfaces.
