# WORKING CACHE — TrueVow SETTLE Service

**Last Updated:** 2026-05-19 (post Phase 1-5 complete + E2E ready)

---

## Repo Map

| Repo | Path | Type | Branch refspec |
|---|---|---|---|
| **SETTLE backend** | `C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\TrueVow_Tenant_SETTLE-Service` | Python FastAPI | `master:main` → `origin/main` |
| **Customer portal** | `C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow_Tenant_Customer_Portal_Service` | Next.js 14 (npm) | `master:main` → `origin/main` |
| **DOCKET-Service** | `C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\TrueVow_Tenant_SETTLE-Service\DOCKET-Service` | Python FastAPI | Same repo |

**Git remotes:**
- Backend: `https://github.com/truevow-ai/TrueVow_Tenant_SETTLE_Service.git`
- Customer portal: `https://github.com/truevow-ai/TrueVow_Tenant_Customer_Portal_Service.git`

---

## Truth Commands

### Backend (Python)
```powershell
cd C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\TrueVow_Tenant_SETTLE-Service
python -m pytest tests/ -v --tb=short --ignore=tests/test_customer_scenarios.py --ignore=tests/test_automated_integration.py --ignore=tests/test_functional.py --ignore=tests/comprehensive_test_suite.py
```

### E2E Tests
```powershell
python -m pytest tests/test_e2e_integration.py -v --tb=short --timeout=30
```

### Customer portal (npm)
```powershell
cd C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow_Tenant_Customer_Portal_Service
npm run type-check
npm run lint
npm run build
```

---

## Current Status

| Concern | State |
|---|---|
| Backend HEAD (local) | Phase 1-5 complete (not yet committed) |
| Backend running | ✅ `http://localhost:8002` (PID 29612) |
| Supabase connection | ✅ Connected — 440 approved contributions |
| Unit tests | **186/186 PASS** |
| DOCKET-Service tests | **23/24 PASS** (1 skipped) |
| E2E tests | 14 written, ready to run |
| Customer portal Phase 2.1-2.3 | ✅ Built and verified |
| Customer portal remaining UI | 📋 Plan in `CUSTOMER_PORTAL_UI_PLAN_REMAINING.md` |

**Overall:** All backend phases complete. E2E infrastructure ready. Customer portal UI partially built.

---

## Active Modules (most recently touched)

**Phase 4 — Outcome Distribution:**
- `app/services/outcome_distribution.py` — NEW
- `app/services/estimator.py` — updated (integrated outcome distribution)
- `app/models/case_bank.py` — updated (added outcome_distribution field)

**Phase 5 — DOCKET-Service:**
- `DOCKET-Service/` — entire service scaffolded
- `DOCKET-Service/app/services/scraping/courtlistener_scraper.py` — NEW

**E2E Testing:**
- `tests/test_e2e_integration.py` — 14 E2E tests
- `scripts/run-e2e-tests.ps1` — test runner
- `docker-compose.e2e.yml` — full stack
- `docs/E2E_INTEGRATION_TESTING.md` — setup guide

---

## Known Failing Commands

**None.** All unit tests pass. E2E tests ready to run against live backend.

---

## Architectural Anchors (read-only references)

- `docs/01-main/MILESTONE_PHASE_1_5_CHECKPOINT.md` — THIS FILE, current checkpoint
- `docs/01-main/IMPLEMENTATION_PROGRESS.md` — full milestone tracker
- `SETTLE_FEATURE_ROADMAP.md` — full 5-phase roadmap
- `CUSTOMER_PORTAL_UI_PLAN_REMAINING.md` — remaining UI work
- `.opencode/skills/` — three-mode agent skills

---

## Next Single Action

**Run E2E tests against live backend:**
```powershell
python -m pytest tests/test_e2e_integration.py -v --tb=short --timeout=30
```

Expected: 14/14 PASS (previously 7 passed, 7 timed out — DB now connected).

---

## Operating mode

**Three-Mode Workflow** (Architect → Coder → QA) configured via `opencode.json`.

**Mode switching:** `/mode architect` | `/mode coder` | `/mode qa`
