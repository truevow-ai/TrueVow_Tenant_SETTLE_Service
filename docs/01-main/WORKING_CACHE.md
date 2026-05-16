# WORKING CACHE — SETTLE Service

**Last Updated:** 2026-05-16

---

## Repo Info

- **Repo Type:** Python backend (FastAPI) — frontend lives in separate (not-yet-git-tracked) repo
- **Tech Stack:** Python 3.11 + FastAPI + Pydantic + Alembic + custom SupabaseRESTClient (httpx-based)
- **Local branch:** `master` → push refspec `master:main` → `origin/main`
- **GitHub:** `https://github.com/truevow-ai/TrueVow_Tenant_SETTLE_Service.git`
- **Database client:** `app/services/integrations/supabase_rest_client.py` (chainable query builder, synchronous despite async-flavored). Methods: `.table()`, `.select()`, `.eq()`, `.ilike()` (URL-encoded), `.cs()`, `.order()`, `.limit()`, `.execute()`.

---

## Truth Commands (Python backend)

```powershell
# Tests (43/43 expected)
python -m pytest tests/ -v 2>&1 | Tee-Object -FilePath logs\pytest.log

# Run service (dev)
python -m uvicorn app.main:app --reload --port 8002

# Alembic migrations
alembic upgrade head
```

PowerShell quirk: pytest-asyncio deprecation warning hits stderr → PS reports ExitCode 1 (false positive). Verify via summary line `"43 passed in Ns"`.

---

## Truth Commands (Frontend, when V-front lands)

Frontend is at `C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow_Tenant_Customer_Portal_Service`.

```powershell
cd C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow_Tenant_Customer_Portal_Service
npm install
npm run lint
npm run type-check   # if defined in package.json
npm run build
npx playwright test  # if e2e suite present
```

Package manager: **npm only** (`package-lock.json` present, no pnpm-lock).

---

## Current Status

**Status:** DONE for backend through Cohort U-back. Awaiting Yasha trigger for next cohort.

- Backend HEAD: `91a775f` (Cohort U-back X-Settle-User-Id bridge)
- origin/main: `91a775f` (synced)
- Tests: 43/43 PASS
- Pilot Mode infrastructure: LIVE but DORMANT (default-off flags)
- Customer portal: NOT git-tracked yet (Cohort V-front prep stage initializes it)

---

## Active Modules (most recently touched)

- `app/api/v1/endpoints/query.py` — `/estimate` endpoint with X-Settle-User-Id bridge
- `app/services/intelligence_gate.py` — county/state/pilot-tier gate
- `app/services/estimator.py` — pilot-aware integration
- `app/services/injury_classifier/` — deterministic 17-tag library
- `tests/conftest.py` — patches `settings.USE_MOCK_DATA` on live singleton
- `tests/test_functional.py` — includes `TestPilotUserIdentification` (3 new tests)

---

## Known Failing Commands

None. All truth commands green.

---

## Architectural Anchors (read-only references)

- `docs/01-main/adr/ADR_20260513_deterministic_injury_classifier.md` — ADR S-1.1
- `docs/01-main/adr/ADR_20260516_pilot_mode_gate_threshold.md` — ADR S-2 + 2026-05-16 X-Settle-User-Id addendum
- `docs/01-main/MILESTONE_COHORT_T_CHECKPOINT.md` — Pilot Mode landing
- `docs/01-main/MILESTONE_COHORT_U_BACK_CHECKPOINT.md` — X-Settle-User-Id bridge landing
- `docs/01-main/IMPLEMENTATION_PROGRESS.md` — full chronology

---

## Trigger Vocabulary (in effect)

| Trigger | Effect |
|---|---|
| `go push` | Push current local HEAD to origin (mandatory before any push) |
| `draft V-front` | Architect-mode: write Cohort V-front directive to file for review |
| `go V-front` | Execute Cohort V-front end-to-end (touches customer portal repo) |
| `pause` | Stop, hold state |

---

## Next Single Action

**Draft or fire Cohort V-front (frontend pilot wiring).**

Cohort V-front scope (from outgoing Hyperagent architect's recon):
1. Prep: git init customer portal, add remote, .gitignore, baseline commit, first push
2. Feature: forward Clerk userId via `X-Settle-User-Id` proxy header; replace MOCK_INTEL on analysis page; add `PilotModeBanner.tsx`; update `EstimateResponse` interface to include `is_pilot_response`
3. Tests: Playwright e2e for pilot/production response paths
4. Build/lint/type-check gates

Decisions pre-resolved (per outgoing architect): Auth bridge = Option A header forward; Mock-data scope = replace MOCK_INTEL entirely; Confidence shape = update frontend types to match backend (top-level `confidence: str`).
