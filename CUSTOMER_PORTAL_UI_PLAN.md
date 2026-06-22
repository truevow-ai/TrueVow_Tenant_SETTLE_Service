# Customer Portal UI Plan — SETTLE Phase 2.1, 2.2, 2.3 Features

**Source:** TrueVow SETTLE Backend (`TrueVow_Tenant_SETTLE-Service`)
**Target:** Customer Portal (`Truevow_Tenant_Customer_Portal_Service`)
**Date:** 2026-05-19

---

## Scope

### In scope (this repo)
1. Confidence Score display on analysis and query pages
2. Advanced filter controls on query page
3. Carrier Patterns analytics page

### Out of scope (belongs in SaaS Admin MDM)
- Internal verdict search UI
- Admin contribution management
- Admin analytics dashboard
- API key management

---

## 1. Update Types — `lib/api/settle-client.ts`

### Add these types

```typescript
// Confidence Score (Phase 2.1)
export interface ConfidenceFactor {
  score: number;       // 0-10
  max: number;         // 10
  weight: number;      // 0-1
  detail: string;
}

export interface ConfidenceScoreData {
  overall: number;     // 10-95
  label: string;       // "Very Strong" | "Strong" | "Moderate" | "Cautious" | "Insufficient Data"
  factors: Record<string, ConfidenceFactor>;
  warnings: string[];
}

// Carrier Patterns (Phase 2.3)
export interface CarrierPattern {
  defendant_category: string;
  defendant_industry: string | null;
  case_count: number;
  avg_settlement_range: { low: number; median: number; high: number };
  settlement_rate: number;
  avg_time_to_resolution_days: number | null;
  trial_rate: number;
  lowball_indicator: number;
  median_settlement: number | null;
  p25_settlement: number | null;
  p75_settlement: number | null;
}

export interface CarrierPatternsResponse {
  patterns: CarrierPattern[];
  total_cases: number;
  jurisdiction: string | null;
  case_type: string | null;
  methodology: string;
}
```

### Update `EstimateResponse` — add this field

```typescript
export interface EstimateResponse {
  // ... existing fields ...

  // Phase 2.1: Demand Confidence Score
  confidence_score: ConfidenceScoreData | null;
}
```

### Update `EstimateRequest` — add these optional fields

```typescript
export interface EstimateRequest {
  // ... existing fields ...

  // Phase 2.2: Advanced search filters
  outcome_type?: string;
  date_range_from?: string;     // ISO date string
  date_range_to?: string;       // ISO date string
  medical_bills_min?: number;
  medical_bills_max?: number;
  exclude_outliers?: boolean;
  min_reputation_score?: number;
  comparative_negligence_min?: number;
  comparative_negligence_max?: number;
}
```

### Add new client method

```typescript
async getCarrierPatterns(params?: {
  jurisdiction?: string;
  case_type?: string;
  injury_category?: string[];
  defendant_category?: string;
  min_case_count?: number;
}): Promise<CarrierPatternsResponse> {
  const query = new URLSearchParams();
  if (params?.jurisdiction) query.set('jurisdiction', params.jurisdiction);
  if (params?.case_type) query.set('case_type', params.case_type);
  if (params?.injury_category) params.injury_category.forEach(i => query.append('injury_category', i));
  if (params?.defendant_category) query.set('defendant_category', params.defendant_category);
  if (params?.min_case_count) query.set('min_case_count', String(params.min_case_count));

  const qs = query.toString();
  return this.get(`/api/settle/carrier-patterns${qs ? `?${qs}` : ''}`);
}
```

---

## 2. Confidence Score UI — Analysis Page

### File: `app/(dashboard)/dashboard/settle/analysis/page.tsx`

Add a new section after the percentile ranges display and before the comparable cases section.

### UI Design

```
┌─────────────────────────────────────────────────┐
│ Data Confidence Score: 72/100 (Strong)          │
│ ┌─────────────────────────────────────────────┐ │
│ │ Factor          Score  Bar     Detail        │ │
│ │ Comp Set Depth   8/10  ████████  64 cases    │ │
│ │ Reputation      10/10  ██████████ High rep   │ │
│ │ Jurisdiction    10/10  ██████████ County     │ │
│ │ Injury Spec     10/10  ██████████ 100% match │ │
│ │ Data Recency     6/10  ██████    45 days ago │ │
│ │ Outlier Rate    10/10  ██████████ 3% outliers│ │
│ │ Completeness    10/10  ██████████ All filled │ │
│ └─────────────────────────────────────────────┘ │
│ ⚠ Data recency could be improved                │
└─────────────────────────────────────────────────┘
```

### Implementation notes
- Only render when `estimate.confidence_score` is not null
- Use existing card/badge patterns from the repo
- Bar color: green (score >= 7), amber (score >= 4), red (score < 4)
- Warnings render as amber info-box below the table
- Follow existing section header pattern: `<h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-3">`

---

## 3. Confidence Score UI — Query Page

### File: `app/(dashboard)/dashboard/settle/query/page.tsx`

Add the same confidence score section after the estimate results display. Same design as analysis page.

---

## 4. Advanced Filter Controls — Query Page

### File: `app/(dashboard)/dashboard/settle/query/page.tsx`

Add an expandable "Advanced Filters" section below the existing basic filters (jurisdiction, case type, injury category, medical bills).

### New Filter Fields

| Field | UI Control | Type |
|---|---|---|
| `outcome_type` | Dropdown | Settlement, Jury Verdict, Arbitration Award, Mediation, Judge's Decision |
| `date_range_from` | Date input | ISO date string |
| `date_range_to` | Date input | ISO date string |
| `medical_bills_min` | Number input | Float |
| `medical_bills_max` | Number input | Float |
| `exclude_outliers` | Checkbox | Boolean (default: true) |
| `min_reputation_score` | Range slider 0-1 | Float, step 0.1 |
| `comparative_negligence_min` | Number input 0-100 | Float |
| `comparative_negligence_max` | Number input 0-100 | Float |

### UI Design

```
┌─────────────────────────────────────────────────┐
│ Advanced Filters ▼                              │
│ ┌─────────────────────────────────────────────┐ │
│ │ Outcome Type:    [Settlement        ▼]      │ │
│ │ Date Range:      [2024-01-01] to [2026-05-19]│
│ │ Medical Bills:   $[     ] to $[     ]       │ │
│ │ Comp. Negligence: [  ]% to [  ]%            │ │
│ │ Min Reputation:  [████████░░] 0.8           │ │
│ │ ☑ Exclude Outliers                           │ │
│ │ [Apply Filters] [Clear]                      │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

### Implementation notes
- Collapsible section (use existing collapsible pattern from analysis page)
- All fields are optional — only include in request if user provides a value
- "Clear" button resets all advanced filters to defaults
- Pass all filter values through to `settleClient.getEstimate(request)`

---

## 5. Carrier Patterns Analytics Page

### New file: `app/(dashboard)/dashboard/settle/carrier-patterns/page.tsx`

### Route: `/dashboard/settle/carrier-patterns`

### UI Design

```
┌─────────────────────────────────────────────────────────────────┐
│ Defendant Category Settlement Patterns                          │
│ Historical data from anonymized settlement contributions.       │
│ Not predictive.                                                 │
│                                                                 │
│ Filters: [Jurisdiction ▼] [Case Type ▼] [Injury Category ▼]    │
│                                                                 │
│ ┌──────────┬──────┬─────────┬────────────┬─────────────┬───────┐│
│ │ Category │ Cases│ Median  │ Settle Rate│ Below Median │ Trial ││
│ ├──────────┼──────┼─────────┼────────────┼─────────────┼───────┤│
│ │ Business │  342 │ $89,000 │    78%     │     23%     │  12%  ││
│ │ (Health) │      │         │            │             │       ││
│ ├──────────┼──────┼─────────┼────────────┼─────────────┼───────┤│
│ │ Business │  198 │ $67,000 │    82%     │     18%     │   8%  ││
│ │ (Auto)   │      │         │            │             │       ││
│ ├──────────┼──────┼─────────┼────────────┼─────────────┼───────┤│
│ │ Govt     │   87 │ $125K   │    91%     │     12%     │   3%  ││
│ │ Entity   │      │         │            │             │       ││
│ └──────────┴──────┴─────────┴────────────┴─────────────┴───────┘│
│                                                                 │
│ 1,247 total cases analyzed                                      │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation notes
- Use existing dashboard layout pattern (section headers, stat cards, tables)
- Fetch data via `settleClient.getCarrierPatterns()` on mount and when filters change
- Show loading state while fetching
- Show empty state when no patterns available (n < min_case_count)
- Include methodology disclaimer: "Descriptive statistics from anonymized settlement contributions. Not predictive."
- Currency formatting: `new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)`
- Percentage formatting: `(rate * 100).toFixed(0)%`

---

## 6. Sidebar Navigation Update

### File: `app/(dashboard)/layout.tsx`

Add a link to the Carrier Patterns page under the SETTLE section in the sidebar.

```
Settlement Intelligence
├── Case Analysis          (/dashboard/settle)
├── Query                  (/dashboard/settle/query)
├── Reports                (/dashboard/settle/reports)
├── Contribute             (/dashboard/settle/contribute)
└── Carrier Patterns       (/dashboard/settle/carrier-patterns)  ← NEW
```

---

## 7. API Proxy Route

### New file: `app/api/settle/carrier-patterns/route.ts`

Create a Next.js API proxy route that forwards requests to the SETTLE backend:

```
GET /api/settle/carrier-patterns → GET {SETTLE_BACKEND_URL}/api/v1/analytics/carrier-patterns
```

Follow the existing proxy pattern used for other SETTLE endpoints in `app/api/settle/`.

---

## Backend Response Shapes (Reference)

### Confidence Score (included in existing estimate response)

```json
{
  "confidence_score": {
    "overall": 72,
    "label": "Strong",
    "factors": {
      "comp_set_depth": { "score": 8, "max": 10, "weight": 0.2, "detail": "64 comparable cases found" },
      "reputation_distribution": { "score": 10, "max": 10, "weight": 0.15, "detail": "High contributor reputation (avg 0.90)" },
      "jurisdiction_coverage": { "score": 10, "max": 10, "weight": 0.15, "detail": "County-level data available (64 cases)" },
      "injury_type_specificity": { "score": 10, "max": 10, "weight": 0.15, "detail": "High injury specificity (1 tags, 100% match rate)" },
      "data_recency": { "score": 6, "max": 10, "weight": 0.1, "detail": "Moderately recent data (last submission 45 days ago)" },
      "outlier_rate": { "score": 10, "max": 10, "weight": 0.15, "detail": "Very low outlier rate (3%)" },
      "completeness": { "score": 10, "max": 10, "weight": 0.1, "detail": "Excellent data completeness (100% fields filled)" }
    },
    "warnings": ["Data recency could be improved — no recent submissions in this category."]
  }
}
```

### Carrier Patterns

```json
{
  "patterns": [
    {
      "defendant_category": "Business",
      "defendant_industry": "Healthcare",
      "case_count": 342,
      "avg_settlement_range": { "low": 52000, "median": 89000, "high": 145000 },
      "settlement_rate": 0.78,
      "avg_time_to_resolution_days": 180,
      "trial_rate": 0.12,
      "lowball_indicator": 0.23,
      "median_settlement": 89000,
      "p25_settlement": 52000,
      "p75_settlement": 145000
    }
  ],
  "total_cases": 1247,
  "jurisdiction": null,
  "case_type": null,
  "methodology": "Descriptive statistics from anonymized settlement contributions. Not predictive."
}
```

---

## Implementation Order

1. **Update types** (`lib/api/settle-client.ts`) — add all new types and `getCarrierPatterns()` method
2. **Confidence Score UI** — add to analysis page, then query page
3. **Advanced Filters** — add filter controls to query page
4. **API Proxy Route** — create carrier-patterns proxy route
5. **Carrier Patterns page** — new page with table and filters
6. **Sidebar navigation** — add link to carrier patterns page

---

## Testing Checklist

- [ ] `npm run type-check` — 0 errors
- [ ] `npm run lint` — exit 0
- [ ] `npm run build` — all pages build
- [ ] Confidence score displays correctly on analysis page
- [ ] Confidence score displays correctly on query page
- [ ] Advanced filters pass through to backend correctly
- [ ] Carrier patterns page loads and displays data
- [ ] Carrier patterns filters work correctly
- [ ] Sidebar navigation includes new link

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
