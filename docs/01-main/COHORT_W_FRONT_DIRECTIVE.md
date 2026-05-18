# Cohort W-Front — Customer Portal Rich Field Integration + LEVERAGE Case Wiring

**Date:** 2026-05-17
**Status:** READY FOR EXECUTION
**Backend commit:** `a1b2c3d4e5f6` (12 new fields on `settle_contributions`)
**Customer portal repo:** `Truevow_Tenant_Customer_Portal_Service`

---

## 1. Cohort goal (one sentence)

Update the customer portal to (a) display and filter by the 12 new rich fields from SETTLE backend, and (b) wire SETTLE to work with any LEVERAGE case — replacing mock data with `leverageClient.listCases()` and adding "Run SETTLE" actions on LEVERAGE case cards.

---

## 1.5. Product decision: Option A — SETTLE works with any LEVERAGE case

**Decision:** SETTLE should pull case data from LEVERAGE, not require manual entry or be limited to intake-sourced cases.

**Rationale:**
- LEVERAGE already exists as the case management system — no duplicate case entry needed
- Billing is already per-case — LEVERAGE cases have real `case_id`s that map to SETTLE's billing model
- Customers who bring their own cases still get value from LEVERAGE's damages calculator, compliance tracking, etc.
- The `leverage_damages` flow already exists but is incomplete — just needs `jurisdiction`, `case_type`, `injury_category` passed through

**What this means for implementation:**
- Replace mock case data with `leverageClient.listCases()`
- Add `source=leverage_case` branch that fetches real case details
- Add "Run SETTLE" action on LEVERAGE case cards
- Pass missing fields (`jurisdiction`, `case_type`, `injury_category`) through the leverage damages flow

---

## 2. Backend changes (already shipped)

The SETTLE backend now returns these additional fields in estimate responses and comparable cases:

### `EstimateResponse` — unchanged shape (no new top-level fields)
The response contract is the same. Rich fields appear inside `comparable_cases[]`.

### `ComparableCase` — NEW fields:
```typescript
interface ComparableCase {
  jurisdiction: string;
  case_type: string;
  injury_category: string[];
  primary_diagnosis?: string;
  medical_bills: number;
  outcome_range: string;          // bucketed: "$50k-$100k"
  outcome_type: string;
  contributed_at: string;
  // NEW (Cohort W):
  insurance_carrier?: string;     // "State Farm", "Geico", etc.
  injury_severity?: string;       // "soft_tissue", "fracture", "surgical", "catastrophic", "fatal"
  court_level?: string;           // "circuit", "federal_district", "arbitration", etc.
  is_verdict?: boolean;           // true = jury verdict, false = settlement
  exact_outcome_amount?: number;  // exact dollar amount (prefer over bucket midpoint)
  comparative_negligence_pct?: number;  // 0-100
  date_of_verdict?: string;       // ISO date
}
```

### `EstimateRequest` — NEW optional filter fields:
```typescript
interface EstimateRequest {
  // existing fields...
  jurisdiction: string;
  case_type: string;
  injury_category: string[];
  medical_bills: number;
  // NEW (Cohort W):
  insurance_carrier?: string;
  injury_severity?: string;
  court_level?: string;
  is_verdict?: boolean;
}
```

---

## 3. Pre-flight recon (run these BEFORE editing)

```powershell
cd C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow_Tenant_Customer_Portal_Service

# Verify current state
npm run type-check 2>&1 | Select-String -Pattern "error"
npm run build 2>&1 | Select-String -Pattern "error|failed"

# Find the files that need changes
# 1. lib/api/settle-client.ts — EstimateResponse + ComparableCase types
# 2. app/(dashboard)/dashboard/settle/analysis/page.tsx — comparable case display
# 3. app/(dashboard)/dashboard/settle/query/page.tsx — query form + estimate display
# 4. components/settle/ — any components that render comparable cases
```

---

## 4. Execution plan

### Task 1: Update `lib/api/settle-client.ts` — type alignment

**File:** `lib/api/settle-client.ts`

Update the `ComparableCase` interface to add the 7 new fields:

```typescript
export interface ComparableCase {
  jurisdiction: string;
  case_type: string;
  injury_category: string[];
  primary_diagnosis?: string;
  medical_bills: number;
  outcome_range: string;
  outcome_type: string;
  contributed_at: string;
  // Cohort W — rich fields
  insurance_carrier?: string;
  injury_severity?: string;
  court_level?: string;
  is_verdict?: boolean;
  exact_outcome_amount?: number;
  comparative_negligence_pct?: number;
  date_of_verdict?: string;
}
```

Also update `EstimateRequest` if it exists as a type in this file:

```typescript
export interface EstimateRequest {
  jurisdiction: string;
  case_type: string;
  injury_category: string[];
  medical_bills: number;
  // Cohort W — optional filters
  insurance_carrier?: string;
  injury_severity?: string;
  court_level?: string;
  is_verdict?: boolean;
}
```

### Task 2: Update comparable case display cards

**File:** `app/(dashboard)/dashboard/settle/analysis/page.tsx` (and any `components/settle/` case card components)

Where comparable cases are rendered as cards/rows, add these display elements:

**For each comparable case card, show (when data is available):**

```tsx
{/* Insurance carrier badge */}
{case.insurance_carrier && (
  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
    {case.insurance_carrier}
  </span>
)}

{/* Injury severity badge */}
{case.injury_severity && (
  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
    case.injury_severity === 'fatal' ? 'bg-red-100 text-red-800' :
    case.injury_severity === 'catastrophic' ? 'bg-orange-100 text-orange-800' :
    case.injury_severity === 'surgical' ? 'bg-yellow-100 text-yellow-800' :
    case.injury_severity === 'fracture' ? 'bg-purple-100 text-purple-800' :
    'bg-gray-100 text-gray-800'
  }`}>
    {case.injury_severity}
  </span>
)}

{/* Verdict vs Settlement indicator */}
{case.is_verdict !== null && case.is_verdict !== undefined && (
  <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
    case.is_verdict ? 'bg-amber-100 text-amber-800' : 'bg-green-100 text-green-800'
  }`}>
    {case.is_verdict ? 'Verdict' : 'Settlement'}
  </span>
)}

{/* Exact amount (if available, show alongside bucketed range) */}
{case.exact_outcome_amount && (
  <span className="text-sm font-semibold text-gray-900">
    ${case.exact_outcome_amount.toLocaleString()}
  </span>
)}

{/* Comparative negligence (if available) */}
{case.comparative_negligence_pct !== null && case.comparative_negligence_pct !== undefined && (
  <span className="text-xs text-gray-500">
    Negligence: {case.comparative_negligence_pct}%
  </span>
)}

{/* Court level */}
{case.court_level && (
  <span className="text-xs text-gray-500">
    {case.court_level}
  </span>
)}
```

**Display priority:** Show the most important fields first:
1. Insurance carrier (high value for negotiation context)
2. Injury severity (quick scan)
3. Verdict vs Settlement (critical distinction)
4. Exact amount (if available, prefer over bucket)
5. Comparative negligence (if available)
6. Court level (if available)

### Task 3: Update query page filters (optional but recommended)

**File:** `app/(dashboard)/dashboard/settle/query/page.tsx`

Add optional filter fields to the query form:

```tsx
{/* Insurance Carrier filter */}
<div>
  <label className="block text-sm font-medium text-gray-700">Insurance Carrier (optional)</label>
  <input
    type="text"
    value={filters.insurance_carrier || ''}
    onChange={(e) => setFilters(prev => ({ ...prev, insurance_carrier: e.target.value || undefined }))}
    placeholder="e.g., State Farm"
    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
  />
</div>

{/* Injury Severity filter */}
<div>
  <label className="block text-sm font-medium text-gray-700">Injury Severity (optional)</label>
  <select
    value={filters.injury_severity || ''}
    onChange={(e) => setFilters(prev => ({ ...prev, injury_severity: e.target.value || undefined }))}
    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
  >
    <option value="">Any</option>
    <option value="soft_tissue">Soft Tissue</option>
    <option value="fracture">Fracture</option>
    <option value="surgical">Surgical</option>
    <option value="catastrophic">Catastrophic</option>
    <option value="fatal">Fatal</option>
  </select>
</div>

{/* Verdict vs Settlement filter */}
<div>
  <label className="block text-sm font-medium text-gray-700">Outcome Type (optional)</label>
  <select
    value={filters.is_verdict === undefined ? '' : filters.is_verdict ? 'verdict' : 'settlement'}
    onChange={(e) => setFilters(prev => ({
      ...prev,
      is_verdict: e.target.value === '' ? undefined : e.target.value === 'verdict'
    }))}
    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
  >
    <option value="">Any</option>
    <option value="verdict">Verdict Only</option>
    <option value="settlement">Settlement Only</option>
  </select>
</div>
```

Pass these filters through to the `settleClient.getEstimate()` call:

```typescript
const response = await settleClient.getEstimate({
  jurisdiction,
  case_type,
  injury_category,
  medical_bills,
  // Pass new filters if set
  ...(filters.insurance_carrier && { insurance_carrier: filters.insurance_carrier }),
  ...(filters.injury_severity && { injury_severity: filters.injury_severity }),
  ...(filters.court_level && { court_level: filters.court_level }),
  ...(filters.is_verdict !== undefined && { is_verdict: filters.is_verdict }),
});
```

### Task 4: Update estimate display to show verdict-derived label

Where the estimate is displayed (analysis page), add a label when the data source is verdict-derived:

```tsx
{/* Data source label */}
{estimate.comparable_cases.some(c => c.is_verdict === true) && (
  <div className="mt-2 flex items-center gap-2 text-xs text-amber-700 bg-amber-50 px-3 py-1.5 rounded-md">
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
    </svg>
    <span>Estimate includes verdict-derived data (not all settlements)</span>
  </div>
)}

{/* Sample size with severity breakdown */}
<div className="text-sm text-gray-500">
  {estimate.n_cases} comparable cases
  {estimate.comparable_cases.some(c => c.insurance_carrier) && (
    <span> · {new Set(estimate.comparable_cases.map(c => c.insurance_carrier).filter(Boolean)).size} carriers represented</span>
  )}
</div>
```

---

## 5. Quality gates (run in this order)

```powershell
cd C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow_Tenant_Customer_Portal_Service

npm install
npm run type-check
npm run lint
npm run build
```

**First-failure fix loop:** if any gate fails, fix the FIRST failure only, re-run that gate, then continue.

---

## 6. Commit message

```
feat(settle): integrate rich fields from backend Cohort W

Update ComparableCase interface with 7 new fields from SETTLE backend:
insurance_carrier, injury_severity, court_level, is_verdict,
exact_outcome_amount, comparative_negligence_pct, date_of_verdict.

- lib/api/settle-client.ts — type alignment
- settle/analysis/page.tsx — display carrier, severity, verdict/settlement badges
- settle/query/page.tsx — optional filter fields for carrier, severity, outcome type
- Comparable case cards show exact amount when available (prefer over bucket)
- Verdict-derived data disclosure label on estimates

Verification: typecheck, lint, build all green.
```

---

## 7. Pause-and-surface triggers

Pause and ask Yasha if:
- `ComparableCase` interface doesn't exist in `settle-client.ts` (may be named differently)
- The analysis page structure is significantly different from what's described (file may have been refactored since Cohort V-front-2)
- Any quality gate fails with errors that suggest a backend/frontend contract mismatch
- Build fails due to missing dependencies

---

## 8. Token efficiency note

Files to read at execution time:
1. `lib/api/settle-client.ts` — find current `ComparableCase` and `EstimateRequest` types
2. `app/(dashboard)/dashboard/settle/analysis/page.tsx` — find comparable case rendering
3. `app/(dashboard)/dashboard/settle/query/page.tsx` — find query form and estimate display

Total expected: ~3 file reads + many edits. Within budget.
