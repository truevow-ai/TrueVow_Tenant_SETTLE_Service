# Milestone Checkpoint — Cohort U-back (X-Settle-User-Id Header Bridge)
**Date:** 2026-05-16
**Commit:** `91a775f`
**Status:** DONE (shipped to origin/main)
**ADR:** S-2 addendum (`docs/01-main/adr/ADR_20260516_pilot_mode_gate_threshold.md`, 2026-05-16 section)

---

## Summary

Backend now honors a sidecar `X-Settle-User-Id` header forwarded by the customer portal proxy, using it as the pilot-identification user_id when API-key auth has succeeded. Closes the trust-bridge between Clerk-authenticated end users (frontend) and the backend's pilot allowlist. Forward-compatible: a guard on `auth.get("auth_method", "api_key") == "api_key"` ensures that when future JWT auth lands (ADR S-3), the override is correctly rejected — JWT identity must come from the JWT itself.

## What was built/changed

- `app/api/v1/endpoints/query.py` (+22/-9)
  - Added `Request` to `fastapi` imports
  - Added `http_request: Request` to `estimate_settlement_range` signature
  - Replaced single-source user-id resolution with priority chain: `X-Settle-User-Id` header (when API-key auth) → API-key-owner `user_id` (legacy/direct path) → no fallback (fail-closed)
- `tests/test_functional.py` (+121/-0)
  - Added `TestPilotUserIdentification` class with 3 tests
  - Uses estimator-spy pattern (`patch.object(SettlementEstimator, "estimate_settlement_range", spy)`) to capture `is_pilot_user` kwarg
  - Tests: header-overrides-api-key-owner / no-header-falls-back-to-owner / header-not-in-allowlist-is-not-pilot
- `tests/conftest.py` (+23/-3)
  - Session-autouse fixture now patches `settings.USE_MOCK_DATA = True` and `settings.SETTLE_USE_MOCK_DATA = True` directly on the live Pydantic singleton (with snapshot+restore on teardown)
  - Side-effect benefit: fixed 4 pre-existing `test_functional.py` 401 failures (test infra rot)
- `docs/01-main/adr/ADR_20260516_pilot_mode_gate_threshold.md` (+60/-0)
  - 2026-05-16 addendum: Problem, Decision, Trust model, Forward-compat guard, Allowlist authority, Future direction (ADR S-3), Verification

## Key decisions

- **Trust model:** "Shared X-API-Key gates the proxy." The customer portal already authenticates via shared service-to-service API key; the architectural choice was to extend that trust to a sidecar header rather than require Clerk JWT validation at the backend.
- **Forward-compatible auth-method guard:** `auth.get("auth_method", "api_key") == "api_key"` defaults today's single-auth-path behavior and locks the override out when JWT auth lands. Caught during pre-fire recon — legacy `APIKeyAuth` doesn't populate `auth_method` reliably.
- **Allowlist remains authoritative:** Header forwarding only identifies the user; pilot eligibility still requires explicit allowlist membership via `SETTLE_PILOT_USER_IDS`.
- **Pre-existing test infra rot folded atomically:** Root cause was Pydantic BaseSettings module-import-time singleton instantiation occurring BEFORE the conftest `os.environ` assignment. Fix on the live singleton resolved both new test enablement AND 4 latent failures. Surfaced as Option A/B/C; A chosen and executed.

## Verification evidence

- **Commands run (capture mode):**
  - `python -m pytest tests/ -v` (post-Option A) → 43/43 PASS in 20.78s
  - `git push origin master:main` → `c43d81a..91a775f` fast-forward
- **Logs:**
  - `logs/cohort_u_back_pytest.log` (initial run, 7 failed = 3 new blocked + 4 pre-existing)
  - `logs/baseline_pre_uback.log` (stash-and-revert HEAD baseline, confirmed 4 failures were pre-existing)
  - `logs/cohort_u_back_pytest_v2.log` (post-Option A, 43/43 PASS)
  - `logs/cohort_u_back_push.log` (push transcript)
  - `logs/cohort_u_back_commit_msg.txt` (commit message body, 43 lines)
- **Post-push verification:**
  - `git rev-parse HEAD` = `91a775fd5840e00f5bb31c646d19f91cdcb46fb2`
  - `git rev-parse origin/main` = `91a775fd5840e00f5bb31c646d19f91cdcb46fb2`
  - `git rev-list --count origin/main..HEAD` = 0 (synced)
- **Result:** ✅ PASS

## Diff stats (atomic commit)

| File | Lines |
|---|---|
| `app/api/v1/endpoints/query.py` | +22 / -9 |
| `tests/test_functional.py` | +121 / -0 |
| `tests/conftest.py` | +23 / -3 |
| `docs/01-main/adr/ADR_20260516_pilot_mode_gate_threshold.md` | +60 / -0 |
| **Total** | **+226 / -12** |

## Production behavior at SHIP time

- Without `X-Settle-User-Id` header → legacy API-key-owner `user_id` path (unchanged)
- With `X-Settle-User-Id` header AND API-key auth → header value used as user_id (new)
- With `X-Settle-User-Id` header AND non-API-key auth (future JWT) → header IGNORED, fail-closed
- Allowlist check (`SETTLE_PILOT_USER_IDS`) remains authoritative regardless of source

## Next single action

Cohort V-front (frontend pilot wiring). Customer portal must:
1. Be git-initialized + pushed to its target remote
2. Forward `X-Settle-User-Id: <clerk_user_id>` from proxy routes
3. Replace MOCK_INTEL on analysis page with live `settleClient.getEstimate()` call
4. Render `is_pilot_response` banner conditionally

Awaiting Yasha trigger: `draft V-front` or `go V-front`.

## Token efficiency note

For new session orientation: read `WORKING_CACHE.md` + this checkpoint + ADR S-2 addendum only. Source diff is minimal (4 files); reading `query.py` is sufficient — gate/estimator pilot paths unchanged from Cohort T.
