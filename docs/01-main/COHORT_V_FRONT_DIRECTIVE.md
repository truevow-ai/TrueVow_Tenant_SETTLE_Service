# Cohort V-front — Frontend Pilot Wiring + Customer Portal Git Init

**Date drafted:** 2026-05-16
**Status:** DRAFTED (awaiting Yasha trigger `go V-front` to execute)
**Drafted by:** Interim architect+executor (post-Hyperagent handoff)
**Cohort scope:** Customer Portal repo (`Truevow_Tenant_Customer_Portal_Service`) — first commit + pilot wiring against backend Cohort T v2 + U-back

---

## 1. Cohort goal (one sentence)

Initialize the customer portal repo, then wire it to honor backend Pilot Mode by forwarding Clerk userId, replacing `MOCK_INTEL` fixtures with live SETTLE calls, and rendering pilot-mode disclosure on responses where `is_pilot_response === true`.

## 2. Pre-flight assumptions (recon-confirmed)

| Concern | Confirmed state |
|---|---|
| Customer portal path | `C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow_Tenant_Customer_Portal_Service` |
| Git status | No `.git` directory present — repo NOT yet initialized |
| Target remote | `https://github.com/truevow-ai/TrueVow_Tenant_Customer_Portal_Service.git` |
| Package manager | npm (package-lock.json present, no pnpm-lock) |
| Framework | Next.js 14.2 App Router + React 18 + TypeScript 5.3 + Clerk 5.0 + Tailwind + Playwright |
| Existing settle integration | 6 proxy routes (`app/api/settle/{activate,analysis,consume,contribute,quote,reports}`); `lib/api/settle-client.ts` exists; `app/(dashboard)/dashboard/settle/analysis/page.tsx` renders MOCK_INTEL |
| Middleware auth | `app/api/(.*)` is PUBLIC per `middleware.ts` line 11; proxy routes must call `auth()` from `@clerk/nextjs/server` to get userId |
| Analysis route current size | 20 lines (`app/api/settle/analysis/route.ts`) — trivial edit |
| Analysis page size | 28.8KB (do NOT read until execution time — read budget) |
| Tests directory | `tests/e2e/` exists with Playwright config; safe to add `settle-pilot-mode.spec.ts` |
| Backend HEAD on remote | `f97d285` (bank cache); pilot infra ready at `c43d81a` + bridge at `91a775f` |
| `EstimateResponse` shape drift | Frontend has nested `settlement_range.confidence_level`; backend has top-level `confidence: str` AND `is_pilot_response: bool` — frontend types ARE stale on both axes |

## 3. Pre-resolved architectural decisions

| # | Question | Decision | Rationale |
|---|---|---|---|
| 1 | Local branch name for first commit | `master` (push to `origin/main`) | Matches backend convention; same refspec muscle memory |
| 2 | Initial commit granularity | Single baseline commit | Per outgoing-architect lean; preserve historical noise as artifact rather than fabricate cleaner history |
| 3 | Initial commit message | `chore(initial): import customer portal baseline (Cohort V-front prep)` | Marks the baseline import as deliberate |
| 4 | `.gitignore` additions BEFORE init | **CRITICAL** — see §4.2 | Prevent secret leakage on initial commit |
| 5 | Anonymous traffic header behavior | Conditional: skip header when Clerk userId is null | Backend falls back to api-key-owner; no header is the safe default |
| 6 | Backend CORS allowance for new header | Defer recon to execution time; if backend's CORSMiddleware uses `allow_headers=["*"]` → no change needed; else add `"x-settle-user-id"` | Don't preemptively edit backend; minimize risk |
| 7 | Default branch on GitHub remote | `main` (refspec `master:main`) | Matches GitHub convention |
| 8 | Confidence shape reconciliation | Update frontend `EstimateResponse` interface to mirror backend exactly (top-level `confidence: string`, add `is_pilot_response: boolean`, preserve `settlement_range` numeric subfields) | Backend is source of truth per Cohort T v2 |
| 9 | PilotModeBanner placement | `components/settle/PilotModeBanner.tsx` (new dir) | Mirror `components/intake/`, `components/connect/` pattern |
| 10 | E2e mocking strategy | Playwright route interception (`page.route()`) to mock backend responses | Standard pattern; no live backend needed for e2e |

## 4. Execution plan (autonomous on `go V-front`)

### 4.1 Setup todos
Use `todo_write` to track:
- vf1: Recon analysis page (read for MOCK_INTEL location)
- vf2: Update `.gitignore` (CRITICAL secret protection)
- vf3: git init + remote add + sanity-list of files-to-be-committed
- vf4: Initial baseline commit + push to origin/main
- vf5: Update `lib/api/settle-client.ts` types
- vf6: Update `app/api/settle/analysis/route.ts` (Clerk userId forwarding)
- vf7: Create `components/settle/PilotModeBanner.tsx`
- vf8: Modify `app/(dashboard)/dashboard/settle/analysis/page.tsx` (replace MOCK_INTEL, conditional banner, insufficient_data UI)
- vf9: Create `tests/e2e/settle-pilot-mode.spec.ts`
- vf10: Quality gates (npm install + lint + type-check + build + e2e)
- vf11: Feature commit + push as Cohort V-front

### 4.2 Pre-init `.gitignore` additions (DO BEFORE `git init`)

Append to `.gitignore`:
```
# Cohort V-front additions
.qoder/
.env.backup*
seed-output.txt
diff_output.txt
temp_*
check_*.py
*.png
!tests/screenshots/**/*.png
!public/**/*.png
```

**Rationale per line:**
- `.qoder/` — local agent metadata, never push
- `.env.backup*` — **CRITICAL**: `.env.backup.ini` (27.7KB) is NOT covered by `.env*.local` or `.env` globs; would leak credentials
- `seed-output.txt`, `diff_output.txt` — dev artifacts, no longer relevant
- `temp_*`, `check_*.py` — one-off scripts (`temp_billing_main.py`, `check_schema.py`)
- `*.png` with `!tests/screenshots/**/*.png` allowlist — strips 7 root-level PNG screenshots (~250KB bloat) but preserves test artifacts and public assets

### 4.3 Git init + initial commit (Prep stage)

```powershell
cd C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow_Tenant_Customer_Portal_Service
# Verify still no .git
Test-Path .git    # Should be False
git init -b master
git remote add origin https://github.com/truevow-ai/TrueVow_Tenant_Customer_Portal_Service.git
git fetch origin 2>&1 | Tee-Object -FilePath ..\TrueVow_Tenant_SETTLE-Service\logs\v_front_init_fetch.log
# Confirm remote is empty (no clobber risk) — fetch should return no refs
git status
```

**Pre-commit safety gate:**
- `git ls-files --others --exclude-standard` to enumerate exactly what's about to be committed
- Scan output for any `.env*`, `*.pem`, `*credentials*`, `*secret*`, `*key*` paths — surface for review if found
- If clean, proceed:
```powershell
git add -A
git status --short    # Final review of staged set
git commit -F ..\TrueVow_Tenant_SETTLE-Service\logs\v_front_initial_commit_msg.txt
git push origin master:main 2>&1 | Tee-Object -FilePath ..\TrueVow_Tenant_SETTLE-Service\logs\v_front_initial_push.log
git rev-parse HEAD; git rev-parse origin/main    # Verify
```

**Initial commit message (written to `logs/v_front_initial_commit_msg.txt`):**
```
chore(initial): import customer portal baseline (Cohort V-front prep)

First commit. Imports the existing Next.js 14.2 App Router + Clerk +
Tailwind customer portal as a single baseline snapshot. No code changes
in this commit — pure history bootstrap.

Excluded via .gitignore: .env*, .env.backup*, .qoder/, *.png at root,
dev-artifact text/script files.

Next: Cohort V-front feature wiring (pilot bridge + MOCK_INTEL replacement).
```

### 4.4 Feature edits (after baseline lands)

**A. `lib/api/settle-client.ts` — type alignment**

Replace current `EstimateResponse` with shape matching backend:
```typescript
export interface EstimateResponse {
  estimate_id: string;
  settlement_range: {
    low: number;
    mid: number;
    high: number;
  };
  confidence: string;             // top-level, was nested as confidence_level
  comparable_cases: number;
  data_quality_score: number;
  factors_considered: string[];
  jurisdiction: string;
  case_type: string;
  created_at: string;
  is_pilot_response: boolean;     // NEW from Cohort T v2
}
```

**Note:** at execution time, cross-check exact backend response by reading `app/services/estimator.py` `EstimateResponse` Pydantic model in the SETTLE repo to lock the wire-shape. If backend has additional fields (e.g., `justification`, `gate_metadata`), include them as optional `?:` properties.

**B. `app/api/settle/analysis/route.ts` — Clerk userId forwarding**

Rewrite to:
```typescript
import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

const SETTLE_URL = process.env.SETTLE_SERVICE_URL || 'http://localhost:3041';
const SETTLE_KEY = process.env.SETTLE_SERVICE_API_KEY || '';

export async function POST(req: NextRequest) {
  try {
    const { userId } = auth();
    const body = await req.json();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-API-Key': SETTLE_KEY,
    };
    // Forward Clerk userId for backend pilot identification (ADR S-2 addendum).
    // Backend honors X-Settle-User-Id ONLY when API-key auth path succeeds.
    if (userId) {
      headers['X-Settle-User-Id'] = userId;
    }

    const res = await fetch(SETTLE_URL + '/api/v1/query/estimate', {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'SETTLE service unavailable' }, { status: 503 });
  }
}
```

**C. `components/settle/PilotModeBanner.tsx` — NEW**

```tsx
'use client';

interface PilotModeBannerProps {
  comparableCases?: number;
}

export function PilotModeBanner({ comparableCases }: PilotModeBannerProps) {
  return (
    <div
      role="alert"
      className="border-l-4 border-amber-500 bg-amber-50 text-amber-900 px-4 py-3 rounded-md mb-4"
      data-testid="pilot-mode-banner"
    >
      <div className="flex items-start gap-2">
        <span aria-hidden="true">⚠️</span>
        <div>
          <strong className="font-semibold">PILOT MODE — Limited Data</strong>
          <p className="text-sm mt-1">
            This estimate is based on a smaller-than-production dataset
            {typeof comparableCases === 'number' ? ` (${comparableCases} comparable cases)` : ''}.
            Use as a directional reference; not a confidence-graded production estimate.
          </p>
        </div>
      </div>
    </div>
  );
}
```

**D. `app/(dashboard)/dashboard/settle/analysis/page.tsx` — pilot wiring**

Execution-time actions (file is 28.8KB; read first):
1. Locate the `MOCK_INTEL` constant + the render path that consumes it
2. Replace the fixture lookup with `settleClient.getEstimate(request)` async call
3. Add React state: loading, error, response
4. Conditionally render `<PilotModeBanner comparableCases={response.comparable_cases} />` when `response.is_pilot_response === true`
5. Add insufficient_data UI branch when `response.confidence === 'insufficient_data'`: friendly message ("Not enough comparable cases in this jurisdiction yet; please broaden your search or check back as our dataset grows")
6. Preserve existing chart/visualization code; only swap the data source

**Scope discipline:** if the page has unrelated features (e.g., contribution submission, draft mode), DO NOT touch them. Cohort V-front edits ONLY the analysis-rendering path.

**E. `tests/e2e/settle-pilot-mode.spec.ts` — NEW**

Three Playwright tests using `page.route()` to mock `/api/settle/analysis`:
1. Pilot response (`is_pilot_response: true`) → `[data-testid="pilot-mode-banner"]` is visible
2. Production response (`is_pilot_response: false`) → `[data-testid="pilot-mode-banner"]` is NOT in the DOM
3. Insufficient-data response (`confidence: "insufficient_data"`) → fallback UI text is visible, no banner

Test file template:
```typescript
import { test, expect } from '@playwright/test';

test.describe('SETTLE Pilot Mode', () => {
  test('pilot response renders banner', async ({ page }) => {
    await page.route('**/api/settle/analysis', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          estimate_id: 'test-1',
          settlement_range: { low: 10000, mid: 25000, high: 50000 },
          confidence: 'medium',
          comparable_cases: 12,
          data_quality_score: 0.6,
          factors_considered: ['jurisdiction', 'case_type'],
          jurisdiction: 'Miami-Dade, FL',
          case_type: 'Auto Accident',
          created_at: new Date().toISOString(),
          is_pilot_response: true,
        }),
      })
    );
    // Navigate to analysis page (handle Clerk dev bypass via ?preview=bypass)
    await page.goto('/dashboard/settle/analysis?preview=bypass');
    // Trigger query (form submit) — exact selector TBD at execution
    // ...
    await expect(page.getByTestId('pilot-mode-banner')).toBeVisible();
  });
  // ... production + insufficient_data tests follow same pattern
});
```

**Caveat:** Clerk's dev preview bypass uses `?preview=bypass` per `middleware.ts:18`. Use this for e2e to avoid Clerk session setup.

### 4.5 Quality gates (in this order)

All commands run in customer portal directory, output Tee'd to SETTLE repo logs:
```powershell
npm install 2>&1 | Tee-Object -FilePath ..\TrueVow_Tenant_SETTLE-Service\logs\v_front_npm_install.log
npm run lint 2>&1 | Tee-Object -FilePath ..\TrueVow_Tenant_SETTLE-Service\logs\v_front_lint.log
npm run type-check 2>&1 | Tee-Object -FilePath ..\TrueVow_Tenant_SETTLE-Service\logs\v_front_typecheck.log
npm run build 2>&1 | Tee-Object -FilePath ..\TrueVow_Tenant_SETTLE-Service\logs\v_front_build.log
npm run test:e2e -- tests/e2e/settle-pilot-mode.spec.ts 2>&1 | Tee-Object -FilePath ..\TrueVow_Tenant_SETTLE-Service\logs\v_front_e2e.log
```

**First-failure fix loop:** if any gate fails, fix root cause of FIRST failure, re-run same gate, do not chain unrelated fixes (per discipline pattern #7).

### 4.6 Feature commit + push

```powershell
git add -A
git status --short
git commit -F ..\TrueVow_Tenant_SETTLE-Service\logs\v_front_feature_commit_msg.txt
git push origin master:main 2>&1 | Tee-Object -FilePath ..\TrueVow_Tenant_SETTLE-Service\logs\v_front_feature_push.log
git rev-parse HEAD; git rev-parse origin/main
```

Feature commit message (written to `logs/v_front_feature_commit_msg.txt`):
```
feat(settle): wire pilot bridge + replace MOCK_INTEL with live data (Cohort V-front)

Frontend integration with backend Cohort T v2 (Pilot Mode Gate) + Cohort
U-back (X-Settle-User-Id header bridge).

Changes:
- lib/api/settle-client.ts — align EstimateResponse with backend shape;
  add is_pilot_response: boolean, lift confidence to top-level
- app/api/settle/analysis/route.ts — forward Clerk userId via
  X-Settle-User-Id header for backend pilot identification
- components/settle/PilotModeBanner.tsx — new disclosure component
- app/(dashboard)/dashboard/settle/analysis/page.tsx — replace MOCK_INTEL
  with settleClient.getEstimate(); conditional pilot banner; insufficient-
  data fallback UI
- tests/e2e/settle-pilot-mode.spec.ts — Playwright coverage for pilot /
  production / insufficient_data response paths

Trust model: backend honors X-Settle-User-Id ONLY when API-key auth
succeeds (forward-compatible guard per ADR S-2 2026-05-16 addendum).
Anonymous traffic (Clerk userId null) → header omitted → backend falls
back to api-key-owner.

Verification: lint, type-check, build, e2e all green. See logs/v_front_*.log.
```

## 5. Pause-and-surface triggers (mid-execution)

I will pause and surface to Yasha ONLY if:
- Pre-commit secret scan in §4.3 finds any unexpected sensitive file
- `git fetch origin` in §4.3 returns existing refs (means remote isn't empty as expected; clobber risk)
- Backend CORS blocks the new header in e2e and requires backend code change
- Quality gate fails in a way that needs an architecture decision (e.g., type mismatch reveals shape drift > simple field-level)
- File I cannot read or modify due to filesystem error

Otherwise, the full cohort runs end-to-end and reports at completion.

## 6. End-of-unit report format (after `go V-front` runs)

| Field | Value |
|---|---|
| Backend HEAD (unchanged) | `f97d285` |
| Frontend initial commit | `<sha>` |
| Frontend feature commit | `<sha>` |
| Frontend origin/main HEAD | `<sha matches local>` |
| npm install | CLEAN / FAIL |
| npm run lint | CLEAN / FAIL |
| npm run type-check | CLEAN / FAIL |
| npm run build | CLEAN / FAIL |
| npm run test:e2e | N/N PASS |
| Diff stats (feature commit) | +N / -N across staged files |
| Logs | `logs/v_front_*.log` paths |

## 7. Token-efficiency note

Files this directive expects to read at execution time:
- `app/(dashboard)/dashboard/settle/analysis/page.tsx` (large, ~28.8KB)
- `app/services/estimator.py` from SETTLE repo (cross-check `EstimateResponse` Pydantic exact shape)
- `app/main.py` from SETTLE repo (cross-check CORS allow_headers config)
- 1-2 incidental files if e2e selector discovery requires more page context

Total expected at execution: ~5 file reads + many edits. Within QODER §3.5B budget for a fresh task.

## 8. Trigger for execution

`go V-front` — fires this directive end-to-end. No mid-unit check-ins unless §5 surface triggers fire.

If you want adjustments before firing, reply with the change (e.g., "use main not master for first commit", "don't add *.png to gitignore", etc.) and I'll revise the directive in place.
