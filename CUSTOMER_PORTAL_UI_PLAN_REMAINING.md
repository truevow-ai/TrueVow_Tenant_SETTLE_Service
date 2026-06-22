# Customer Portal UI Plan — Remaining Backend Features

**Source:** TrueVow SETTLE Backend (`TrueVow_Tenant_SETTLE-Service`)
**Target:** Customer Portal (`Truevow_Tenant_Customer_Portal_Service`)
**Date:** 2026-05-19

---

## Context

Phase 2.1 (Confidence Score), 2.2 (Advanced Filters), and 2.3 (Carrier Patterns) UI are already built and verified. This plan covers the **remaining backend features** that need frontend display.

---

## 1. Phase 3.1: Multiplier Model Layer UI

### What the backend provides

The `EstimateResponse` now includes two new fields:

```typescript
// In lib/api/settle-client.ts — already added to EstimateResponse
multiplier_method: {
  low: number;
  median: number;
  high: number;
  model_label: string;      // "Community Comp Set (64 cases)" | "Statewide Benchmark (30 cases)" | "Industry Baseline — Not Personalized"
  base_multiplier: number;  // e.g., 3.5
  adjustments_applied: string[];  // e.g., ["Government defendant: -15%"]
} | null;
active_method: string;      // "percentile" (primary) or "multiplier"
```

### What to build

Add a **dual-method comparison** section on the analysis page and query page, below the existing percentile display.

### UI Design

```
┌─────────────────────────────────────────────────────────────┐
│ Settlement Estimate Comparison                              │
│                                                             │
│ ┌─────────────────────┐  ┌──────────────────────────────┐  │
│ │ Percentile Method   │  │ Multiplier Method            │  │
│ │ (Primary)           │  │ (Secondary)                  │  │
│ │                     │  │                              │  │
│ │ P25: $45,000        │  │ Low:   $52,000              │  │
│ │ Median: $75,000     │  │ Median: $85,000             │  │
│ │ P75: $120,000       │  │ High:  $130,000             │  │
│ │                     │  │                              │  │
│ │ Based on 64 cases   │  │ Community Comp Set (64 cases)│  │
│ │                     │  │ Base multiplier: 3.5x        │  │
│ │                     │  │ Adjustments: None            │  │
│ └─────────────────────┘  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Implementation notes
- Only show multiplier section when `estimate.multiplier_method` is not null
- Use existing card patterns from the repo
- Label clearly which method is primary vs secondary
- Show adjustments applied (if any) in a small list below the multiplier numbers

---

## 2. Phase 3.2: Overdemand Cliff Warning UI

### What the backend provides

The `EstimateResponse` now includes:

```typescript
// In lib/api/settle-client.ts — already added to EstimateResponse
overdemand_cliff: {
  threshold: number | null;       // e.g., 180000
  settlement_rate_below: number | null;  // e.g., 0.72
  settlement_rate_above: number | null;  // e.g., 0.31
  warning: string | null;         // e.g., "Historical data shows demands above $180,000 settle 41% less often"
  has_cliff: boolean;
  methodology: string;
} | null;
```

### What to build

Add an **amber warning banner** on the analysis page and query page when `overdemand_cliff.has_cliff === true`.

### UI Design

```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ Historical Settlement Pattern Alert                      │
│                                                             │
│ Historical data shows demands above $180,000 in this        │
│ category settle 41% less often (72% vs 31%).                │
│                                                             │
│ This is based on anonymized settlement contributions.       │
│ Not predictive — individual case results may vary.          │
└─────────────────────────────────────────────────────────────┘
```

### Implementation notes
- Use existing amber alert banner pattern (`bg-amber-50 border-amber-200`)
- Only show when `overdemand_cliff.has_cliff === true`
- Place below the estimate comparison section
- Include the methodology disclaimer

---

## 3. Phase 3.4: Weekly Intelligence Digest UI

### What the backend provides

The backend generates weekly digest emails via `app/services/weekly_digest.py`. No new API endpoint needed — this is an email sent to users.

### What to build

Add a **notification preference toggle** in the SETTLE settings or user profile page to opt-in/out of weekly digest emails.

### UI Design

```
┌─────────────────────────────────────────────────────────────┐
│ Email Notifications                                         │
│                                                             │
│ ☑ Weekly Intelligence Digest                                │
│   Receive a weekly summary of new settlement data,          │
│   coverage gaps, and trend highlights in your jurisdictions.│
│                                                             │
│   [Preview Sample Digest]                                   │
└─────────────────────────────────────────────────────────────┘
```

### Implementation notes
- This may require a new backend endpoint for preference management
- If no backend endpoint exists yet, build a placeholder toggle that calls a future endpoint
- "Preview Sample Digest" button should show a modal with sample digest content (use the HTML template from backend)

---

## 4. Phase 4: Outcome Distribution UI

### What the backend provides

The `EstimateResponse` now includes:

```typescript
// In lib/api/settle-client.ts — already added to EstimateResponse
outcome_distribution: {
  outcome_distribution: {
    settlement: { rate: number; avg_amount: number | null; count: number };
    plaintiff_verdict: { rate: number; avg_amount: number | null; count: number };
    defense_verdict: { rate: number; avg_amount: number | null; count: number };
    dismissed: { rate: number; avg_amount: number | null; count: number };
  };
  trial_risk_indicators: {
    trial_propensity: number;        // e.g., 0.18
    plaintiff_verdict_rate: number;  // e.g., 0.65
    defense_verdict_rate: number;    // e.g., 0.35
    verdict_premium: number | null;  // e.g., 45.0 (verdicts are 45% higher than settlements)
  } | null;
  sample_size: number;
  methodology: string;
} | null;
```

### What to build

Add a **Historical Outcome Breakdown** section on the analysis page, below the estimate comparison and overdemand cliff warning.

### UI Design

```
┌─────────────────────────────────────────────────────────────┐
│ Historical Outcome Distribution                             │
│ Based on 200 similar cases. Descriptive statistics only.    │
│                                                             │
│ ┌──────────────────┬───────┬──────────┬──────────────┐     │
│ │ Outcome          │ Rate  │ Avg Amt  │ Count        │     │
│ ├──────────────────┼───────┼──────────┼──────────────┤     │
│ │ Settlement       │ 72%   │ $85,000  │ 144 cases    │     │
│ │ Plaintiff Verdict│ 18%   │ $210,000 │ 36 cases     │     │
│ │ Defense Verdict  │ 7%    │ $0       │ 14 cases     │     │
│ │ Dismissed        │ 3%    │ —        │ 6 cases      │     │
│ └──────────────────┴───────┴──────────┴──────────────┘     │
│                                                             │
│ Trial Risk Indicators:                                      │
│ • 18% of similar cases went to trial                        │
│ • Plaintiff win rate at trial: 65%                          │
│ • Verdicts average 45% higher than settlements              │
│                                                             │
│ Historical outcome distribution from anonymized data.       │
│ Descriptive statistics only, not predictive.                │
└─────────────────────────────────────────────────────────────┘
```

### Implementation notes
- Only show when `outcome_distribution` is not null and `sample_size > 0`
- Use existing table patterns from the repo
- Include the methodology disclaimer at the bottom
- Place below the overdemand cliff warning section

---

## 5. Type Updates Needed in `lib/api/settle-client.ts`

The following types are already defined in the backend. Verify they match the frontend interfaces, or add them if missing:

```typescript
// Add to EstimateResponse interface (if not already present)
multiplier_method: {
  low: number;
  median: number;
  high: number;
  model_label: string;
  base_multiplier: number;
  adjustments_applied: string[];
} | null;
active_method: string;
overdemand_cliff: {
  threshold: number | null;
  settlement_rate_below: number | null;
  settlement_rate_above: number | null;
  warning: string | null;
  has_cliff: boolean;
  methodology: string;
} | null;
outcome_distribution: {
  outcome_distribution: Record<string, { rate: number; avg_amount: number | null; count: number }>;
  trial_risk_indicators: {
    trial_propensity: number;
    plaintiff_verdict_rate: number;
    defense_verdict_rate: number;
    verdict_premium: number | null;
  } | null;
  sample_size: number;
  methodology: string;
} | null;
```

---

## Implementation Order

1. **Type verification** — Confirm `EstimateResponse` in `lib/api/settle-client.ts` has all new fields
2. **Multiplier Model UI** — Add dual-method comparison on analysis + query pages
3. **Overdemand Cliff UI** — Add amber warning banner on analysis + query pages
4. **Outcome Distribution UI** — Add historical outcome breakdown table on analysis page
5. **Weekly Digest toggle** — Add notification preference in settings (placeholder if no backend endpoint yet)

---

## Testing Checklist

- [ ] `npm run type-check` — 0 errors
- [ ] `npm run lint` — exit 0
- [ ] `npm run build` — all pages build
- [ ] Multiplier method displays correctly when data available
- [ ] Multiplier method hidden when null
- [ ] Overdemand cliff warning displays when `has_cliff === true`
- [ ] Overdemand cliff warning hidden when `has_cliff === false`
- [ ] Outcome distribution table displays correctly when data available
- [ ] Outcome distribution hidden when null
- [ ] Weekly digest toggle renders correctly

---

## UI Conventions (from existing codebase)

- **Stat Cards:** `bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-5`
- **Section Headers:** `text-xs font-semibold uppercase tracking-widest text-gray-400 mb-3`
- **Alert Banners:** `bg-amber-50 border-amber-200` (warnings), `bg-blue-50 border-blue-200` (info), `bg-green-50 border-green-200` (success)
- **Badges:** `inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-{color}-100 text-{color}-800`
- **Currency:** `new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)`
- **Icons:** `lucide-react`
- **ClassName utility:** `cn()` from `lib/utils`
- **Theme:** light/dark/neutral via CSS variables in `globals.css`
