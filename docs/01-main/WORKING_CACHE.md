# WORKING CACHE — TrueVow Multi-Repo

**Last Updated:** 2026-05-17 (post Cohort V-front-2)

---

## Repo Map (TWO repos, both git-tracked)

| Repo | Path | Type | Branch refspec |
|---|---|---|---|
| **SETTLE backend** | `C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\TrueVow_Tenant_SETTLE-Service` | Python FastAPI | `master:main` → `origin/main` |
| **Customer portal** | `C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow_Tenant_Customer_Portal_Service` | Next.js 14 (npm) | `master:main` → `origin/main` |

**Git remotes:**
- Backend: `https://github.com/truevow-ai/TrueVow_Tenant_SETTLE_Service.git`
- Customer portal: `https://github.com/truevow-ai/TrueVow_Tenant_Customer_Portal_Service.git`

---

## Truth Commands

### Backend (Python)
```powershell
cd C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\TrueVow_Tenant_SETTLE-Service
python -m pytest tests/ -v 2>&1 | Tee-Object -FilePath logs\pytest.log
alembic upgrade head
```

### Customer portal (npm)
```powershell
cd C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow_Tenant_Customer_Portal_Service
npm install
npm run type-check
npm run lint
npm run build
```
Package manager: **npm** (`package-lock.json` present, no pnpm-lock).

---

## Current Status

| Concern | State |
|---|---|
| Backend HEAD (local = origin/main) | `f97d285` (docs cache refresh) |
| Customer portal HEAD (local = origin/main) | `5d11ef1` (Cohort V-front-2) |
| Backend tests | 43/43 PASS |
| Customer portal typecheck | PASS (0 errors) |
| Customer portal lint | PASS (exit 0, `next/core-web-vitals`) |
| Customer portal build | PASS (76/76 static pages) |
| Pilot infrastructure (backend) | LIVE, DORMANT (default-off flags) |
| Pilot infrastructure (frontend) | Banner + types + Clerk proxy LIVE; analysis page NOW wired to live API |
| `.github/workflows/pricing-snapshot.yml` | Untracked on disk — push needs PAT `workflow` scope |

**Overall:** Backend DONE. Customer portal DONE through Cohort V-front-2 (all truth gates pass, analysis page wired to live backend API).

---

## Active Modules (most recently touched — Cohort V-front-2)

- `lib/api/settle-client.ts` — EstimateResponse fully aligned with backend Pydantic shape + ComparableCase type
- `app/(dashboard)/dashboard/settle/analysis/page.tsx` — MOCK_INTEL removed; live API fetch + PilotModeBanner + own_case_only guardrail
- `app/(dashboard)/dashboard/settle/query/page.tsx` — updated to use aligned field names (percentile_25/median/percentile_75, confidence, n_cases, query_id)

---

## Known Failing Commands

**None.** All truth gates pass for both repos.

---

## Architectural Anchors (read-only references)

- `docs/01-main/MILESTONE_COHORT_V_FRONT_2_CHECKPOINT.md` — most recent unit-of-work
- `docs/01-main/MILESTONE_COHORT_H_CHECKPOINT.md` — hygiene cohort
- `docs/01-main/MILESTONE_COHORT_V_FRONT_CHECKPOINT.md` — V-front cohort
- `docs/01-main/adr/ADR_20260516_pilot_mode_gate_threshold.md` — ADR S-2
- `.qoder/skills/cross-workspace-shipping.md` — PowerShell + cross-workspace patterns

---

## Trigger Vocabulary (in effect)

| Trigger | Effect |
|---|---|
| `go push` | Push current local HEAD to origin |
| `pause` | Stop, hold state |

---

## Next Single Action

**Pick next work item:**

1. **Workflow scope grant** — user grants PAT `workflow` scope, push `.github/workflows/pricing-snapshot.yml`.
2. **MOCK_CASES removal** — analysis page still uses MOCK_CASES for case input display; replace with intake API when intake service is live.
3. **End-to-end integration test** — deploy backend + portal, verify live billing flow + analysis fetch cycle.

---

## Operating mode

**Architect + Executor combined** (interim, since 2026-05-16 when Hyperagent Opus credits depleted).

**Autonomy Calibration in effect:** unit-scoped end-to-end execution; pause-and-surface ONLY on pre-defined triggers (secret leak, fetch returns existing refs, CORS block, gate failure needing arch decision, scope mismatch). End-of-unit report at completion.
