# SETTLE Feature Roadmap — Phased Planning Document

## Executive Summary

This document maps all planned features for TrueVow SETTLE across five phases. It incorporates:
- Internal verdict research engine (ALM VerdictSearch competitor)
- Customer-facing data quality scoring (SettleCase DSI equivalent)
- Full SettleCase.ai feature inventory with selective adoption plan
- Litigation outcome prediction (deferred to later phase)
- Docket/litigation tracker (separate service, future expansion)

---

## Phase 1: Internal Verdict Research Engine (Build Now, Internal Only)

**Rationale:** We don't have community settlement data yet. Scraped verdict data is our starting point. Build a VerdictSearch competitor internally to seed research capabilities, then graduate features to the customer-facing platform once community data matures.

**Not customer-facing.** Used by SETTLE team for research, data validation, and benchmark calibration.

### 1.1 Verdict Database Schema (Internal)

| Field | Type | Notes |
|---|---|---|
| `verdict_id` | UUID | Primary key |
| `case_name` | string | Anonymized for internal use |
| `jurisdiction` | string | County, ST format |
| `court` | string | Court name |
| `case_type` | enum | Auto accident, slip/fall, medical malpractice, etc. |
| `injury_type` | enum[] | Maps to InjuryTag 17-tag system |
| `plaintiff_age_range` | enum | Under 18, 18-30, 31-45, 46-60, 61-75, 75+ |
| `liability_tier` | enum | Clear, contested, shared, unknown |
| `comparative_negligence_pct` | float | 0-100% |
| `medical_bills` | float | Actual (internal only) |
| `economic_damages` | float | Lost wages, future medical, etc. |
| `non_economic_damages` | float | Pain and suffering |
| `punitive_damages` | float | If awarded |
| `total_verdict` | float | Sum of all damages |
| `settlement_amount` | float | If settled pre-verdict |
| `outcome_type` | enum | Verdict plaintiff, verdict defense, settlement, dismissed |
| `defendant_category` | enum | Individual, business, government, unknown |
| `defendant_industry` | string | Healthcare, automotive, retail, etc. |
| `insurance_carrier` | string | Carrier name (internal research) |
| `policy_limit_indicator` | enum | Below limits, at limits, above limits, unknown |
| `expert_witnesses_plaintiff` | int | Count |
| `expert_witnesses_defense` | int | Count |
| `trial_duration_days` | int | If verdict |
| `judge_name` | string | Internal research |
| `verdict_date` | date | Date of outcome |
| `source` | enum | Scraped, manual entry, partner data |
| `source_url` | string | Original source for verification |
| `confidence_score` | float | 0.0-1.0 data quality |
| `created_at` | timestamp | |
| `updated_at` | timestamp | |

### 1.2 15+ Filter Search Engine (Internal)

Mirrors ALM VerdictSearch specificity. All filters combinable with AND/OR logic.

| # | Filter | Type | Values |
|---|---|---|---|
| 1 | Jurisdiction | Dropdown | All 50 states + county drilldown |
| 2 | Case Type | Multi-select | Auto, slip/fall, med mal, product liability, etc. |
| 3 | Injury Type | Multi-select | 17 InjuryTag categories |
| 4 | Outcome Type | Multi-select | Verdict P, Verdict D, Settlement, Dismissed |
| 5 | Verdict Amount Range | Range slider | $0-$10M+ in buckets |
| 6 | Medical Bills Range | Range slider | $0-$500K+ in buckets |
| 7 | Liability Tier | Dropdown | Clear, contested, shared, unknown |
| 8 | Comparative Negligence | Range | 0-100% |
| 9 | Defendant Category | Multi-select | Individual, business, government |
| 10 | Defendant Industry | Multi-select | Healthcare, auto, retail, construction, etc. |
| 11 | Plaintiff Age Range | Multi-select | Under 18 through 75+ |
| 12 | Date Range | Date picker | Verdict/settlement date window |
| 13 | Insurance Carrier | Text search | Carrier name lookup |
| 14 | Expert Witness Count | Range | 0-10+ per side |
| 15 | Trial Duration | Range | Days (verdict cases only) |
| 16 | Source Type | Dropdown | Scraped, manual, partner |
| 17 | Confidence Score | Range | 0.0-1.0 data quality filter |

### 1.3 Internal Analytics Dashboard

- Verdict trends by jurisdiction, case type, injury
- Average verdict vs. settlement ratios
- Carrier payout patterns (internal research)
- Judge tendency analysis (internal research)
- Data coverage heat map (which jurisdictions have data)

### 1.4 Scraping Pipeline Integration

- Existing scraping scripts (`settle_data_scraping_factory/`) feed into this internal DB
- Separate from settlement contribution pipeline
- Data quality scoring applied at ingestion
- Manual review queue for scraped entries

**Deliverables:**
- [x] Internal verdict database schema (Supabase migration) ✓ Implemented in `app/models/verdicts.py` → `settle_verdicts` table
- [x] 17-filter search API endpoint (`POST /api/v1/internal/verdicts/search`) ✓ Implemented in `app/services/verdict_search.py`
- [x] Internal dashboard (admin-only route) ✓ `GET /api/v1/internal/verdicts/stats`
- [x] Scraping pipeline → internal DB connector ✓ `POST /api/v1/internal/verdicts/scrape/bulk-insert` + scrape job tracking
- [x] Data quality scoring for verdict entries ✓ `completeness_score` + `confidence_score` calculated on ingest
- [ ] CourtListener scraper source ✓ Recovered — `settle_data_scraping_factory/court_dockets_records/cds_courtlistener.py` (2026-06-16)
- [ ] FJC IDB scraper source — `.pyc` exists, needs decompilation
- [ ] News enrichment scraper — `.pyc` exists, needs decompilation
- [ ] Insurance carrier scrapers — `.pyc` exists (cis_common), source missing

---

## Phase 2: Customer-Facing Enhancements (Near-Term)

### 2.1 Demand Confidence Score (Customer-Facing DSI)

**Existing foundation:** `confidence_score` (0.0-1.0) already exists on contributions, admin analytics at `/admin/analytics/data-quality`, outlier detection, completeness checks. Currently admin-only.

**Customer-facing version:** Transform into a 0-100 score returned with every estimate, similar to SettleCase's Demand Strength Index.

```json
{
  "estimate": {
    "p25": 45000,
    "median": 75000,
    "p75": 120000,
    "p95": 180000
  },
  "confidence_score": {
    "overall": 72,
    "label": "Strong",
    "factors": {
      "comp_set_depth": {"score": 8, "max": 10, "detail": "64 comparable cases found"},
      "reputation_distribution": {"score": 7, "max": 10, "detail": "Avg contributor reputation 0.78"},
      "jurisdiction_coverage": {"score": 8, "max": 10, "detail": "County-level data available"},
      "injury_type_specificity": {"score": 7, "max": 10, "detail": "3 matching injury tags"},
      "data_recency": {"score": 6, "max": 10, "detail": "Last submission 45 days ago"},
      "outlier_rate": {"score": 9, "max": 10, "detail": "3% flagged as outliers"},
      "completeness": {"score": 9, "max": 10, "detail": "All required fields present"}
    },
    "warnings": [
      "Data recency could be improved — no submissions in last 30 days"
    ]
  }
}
```

**Scoring factors (7 weighted, clamped 10-95):**

| Factor | Weight | Source |
|---|---|---|
| Comp set depth (n≥50 → max, n≥20 → partial, n<20 → suppressed) | 20% | Existing IntelligenceGate |
| Reputation distribution (avg contributor score) | 15% | Existing reputation_service |
| Jurisdiction coverage (county vs state vs sentinel) | 15% | Existing estimator fallback |
| Injury type specificity (tag match depth) | 15% | Existing injury_classifier |
| Data recency (days since last submission) | 10% | New: track `updated_at` |
| Outlier rate (% flagged) | 15% | Existing anomaly_detector |
| Completeness (required field fill rate) | 10% | Existing validator |

**Labels:**
- Very Strong (≥80)
- Strong (≥65)
- Moderate (≥50)
- Cautious (≥35)
- Insufficient Data (<35 — IntelligenceGate suppression)

**Deliverables:**
- [ ] `confidence_score` service module (extract from admin analytics)
- [ ] Add to estimate response schema
- [ ] Add to PDF report (Page 3: Range Justification)
- [ ] Frontend display (estimate results page)

### 2.2 Advanced Search Filters (Customer-Facing)

Expose existing estimator filters via public API. Currently the query endpoint accepts basic fields only.

**New query parameters for `POST /api/v1/query/estimate`:**

| Filter | Type | Notes |
|---|---|---|
| `liability_tier` | enum | Clear, contested, shared, unknown |
| `outcome_type` | enum | Settlement, verdict, mediation |
| `date_range_from` | date | Filter submissions by date |
| `date_range_to` | date | |
| `medical_bills_min` | float | |
| `medical_bills_max` | float | |
| `defendant_category` | enum | Individual, business, government |
| `exclude_outliers` | bool | Default true |
| `min_reputation_score` | float | Filter by contributor reputation |

**Deliverables:**
- [ ] Update `EstimateRequest` model with optional filter fields
- [ ] Update estimator query builder to apply filters
- [ ] Update IntelligenceGate to count filtered results
- [ ] API documentation

### 2.3 Insurer/Carrier Pattern Analytics

**Already in Year 3 roadmap.** Move to Year 2. Defense side already has this (SigmaSight, CLARA).

**What it shows:**
- Which carrier categories lowball vs. settle fair
- Average settlement speed by carrier category
- Trial vs. settlement rate by carrier category
- Payout distribution by carrier category + injury type

**Data source:** Existing `defendant_category` field + outcome data. No new data collection needed. Carrier names are NOT stored (PHI risk) — only categories (Individual/Business/Government/Unknown) with optional industry sub-category.

**API endpoint:** `GET /api/v1/analytics/carrier-patterns`

```json
{
  "carrier_patterns": [
    {
      "defendant_category": "Business",
      "industry": "Healthcare",
      "case_count": 342,
      "avg_settlement_range": {"low": 52000, "median": 89000, "high": 145000},
      "settlement_rate": 0.78,
      "avg_time_to_settlement_days": 180,
      "trial_rate": 0.12,
      "lowball_indicator": 0.23
    }
  ],
  "methodology": "Descriptive statistics from anonymized settlement contributions. Not predictive."
}
```

**Deliverables:**
- [ ] Carrier pattern aggregation service
- [ ] API endpoint with jurisdiction/case_type filters
- [ ] PDF report section (optional Page 5)
- [ ] Bar-compliance review (ensure descriptive framing)

### 2.4 CRM Integrations

**Target CRMs:** Filevine, Clio, SmartAdvocate, CSV import

**Two-way sync:**
- **Inbound:** Auto-submit settled cases from CRM → SETTLE (increases contribution volume)
- **Outbound:** Query SETTLE ranges during case intake in CRM

**Architecture:**
- OAuth or API key auth per CRM
- Webhook listeners for case status changes
- Field mapping layer (CRM fields → SETTLE schema)
- Conflict resolution (duplicate detection)

**Deliverables:**
- [ ] CRM integration framework (abstract adapter pattern)
- [ ] Filevine adapter (highest priority — largest PI market share)
- [ ] Clio adapter
- [ ] CSV import/export utility
- [ ] Webhook handler for case status triggers
- [ ] Duplicate detection service

### 2.5 Trend Studies / Market Reports

Package existing analytics into shareable content. Marketing + retention multiplier.

**Quarterly reports:**
- "State of Settlement: Q1 2026"
- Injury type trends (by state, by quarter)
- Carrier category payout trends
- Jurisdiction coverage gaps
- Founding Member contribution highlights

**Format:** PDF + web page + API endpoint for embedding

**Deliverables:**
- [ ] Trend report generation service
- [ ] PDF template (branded, shareable)
- [ ] Public landing page for reports
- [ ] API endpoint (`GET /api/v1/reports/trends/{period}`)

---

## Phase 3: SettleCase.ai Feature Parity (Mid-Term)

### 3.1 Complete SettleCase.ai Feature Inventory

Every feature from SettleCase.ai, mapped to SETTLE architecture, with adoption decision.

| # | SettleCase Feature | Description | SETTLE Equivalent | Adopt? | Phase |
|---|---|---|---|---|---|
| 1 | **Demand Strength Index (DSI)** | 0-100 score for demand before sending | Phase 2.1: Demand Confidence Score | YES — Already planned | Phase 2 |
| 2 | **Sticky-note kanban pipeline** | Visual case tracking board | No equivalent | NO — Case management, not SETTLE scope | — |
| 3 | **Benchmark table by injury type** | Compare firm yield vs. benchmarks | Existing comparable cases table | YES — Enhance with firm-private overlay | Phase 3 |
| 4 | **Demand Advisor (AI-powered)** | AI calculates demand amount | Existing estimator (percentile-based) | PARTIAL — Keep descriptive, add multiplier model | Phase 3 |
| 5 | **Negotiation coaching library** | 8 playbooks for negotiation tactics | No equivalent | NO — Content product, not data product | — |
| 6 | **Multi-attorney pipeline** | Firm-wide case tracking | No equivalent | NO — Case management | — |
| 7 | **CRM sync** | Filevine, Clio, SmartAdvocate | Phase 2.4 | YES — Already planned | Phase 2 |
| 8 | **Firm-wide yield analytics** | Analytics by attorney and injury type | No equivalent (single shared DB) | PARTIAL — Via API key grouping | Phase 3 |
| 9 | **Weekly AI intelligence digest** | Email digest with counters, stale cases, gaps | No equivalent | YES — Automated email report | Phase 3 |
| 10 | **Demand queue management** | Track pending demands across firm | No equivalent | NO — Case management | — |
| 11 | **Comp Set Model (Model 01)** | Personal multiplier from 5+ matched cases | Existing percentile estimator | YES — Add multiplier layer on top | Phase 3 |
| 12 | **Broadened Comp Model (Model 02)** | Broader match when tight set too small | Existing jurisdiction fallback | YES — Already similar logic | Phase 3 |
| 13 | **Standard Multiplier Model (Model 03)** | Industry-standard multiplier fallback | No equivalent | YES — Fallback when n<50 | Phase 3 |
| 14 | **Yield Probability Score (Model 04)** | Probability of settling within 60 days at target | No equivalent | PARTIAL — Reframe as "Data Confidence" not probability | Phase 3 |
| 15 | **Overdemand Cliff detection** | Demand band above which settlement rate drops | No equivalent | YES — Valuable insight, descriptive framing | Phase 3 |
| 16 | **Override tracking** | Track when user overrides recommendation | No equivalent | YES — Learn from overrides over time | Phase 3 |
| 17 | **HIPAA-safe design** | No PII stored | Existing anonymizer | YES — Already core principle | Built-in |
| 18 | **Recency weighting** | Recent cases weighted 2x | Existing reputation weighting | YES — Add time-decay factor | Phase 3 |
| 19 | **Insurer-specific patterns** | Carrier behavior analysis | Phase 2.3 | YES — Already planned | Phase 2 |
| 20 | **Treatment gap detection** | Flag gaps in medical treatment | No equivalent | NO — Requires medical record data (PHI risk) | — |

### 3.2 Adopted Features — Detailed Specs

#### 3.2.1 Multiplier Model Layer (SettleCase Models 01-03)

Add multiplier-based estimation alongside existing percentile estimator. Three-tier hierarchy:

**Model A: Community Comp Set (n≥50 matched)**
```
base_multiplier = weighted_avg(settlement ÷ medical_bills) across comp set
low = medical_bills × (base_multiplier × 0.90)
high = medical_bills × (base_multiplier × 1.10)
```
Adjustments: contested liability (-15%), shared fault (-25%), high outlier rate (-10%)

**Model B: State + Sentinel (n≥20, n<50 exact match)**
Same formula, broader comp set. Label: "Statewide Benchmark"

**Model C: Standard Multiplier Table (n<20)**
Fallback to industry-standard multipliers by injury type:

| Injury Type | Multiplier Range |
|---|---|
| Soft Tissue | 2.5x – 4.0x |
| Herniated Disc | 3.5x – 5.0x |
| Fracture | 4.0x – 6.5x |
| Surgical | 5.0x – 8.5x |
| TBI / Concussion | 6.0x – 10.0x |
| Wrongful Death | 8.0x – 15.0x |

Label: "Industry Baseline — Not Personalized"

**Response schema:**
```json
{
  "estimate": {
    "percentile_method": {"p25": 45000, "median": 75000, "p75": 120000},
    "multiplier_method": {"low": 52000, "median": 85000, "high": 130000},
    "active_method": "multiplier_method",
    "method_label": "Community Comp Set (64 cases)"
  }
}
```

#### 3.2.2 Overdemand Cliff Detection

Identify the demand band above which settlement rate drops significantly.

**Algorithm:**
1. Group historical cases by injury type + defendant category
2. Calculate settlement rate by outcome amount bucket
3. Identify the "cliff" — the bucket where settlement rate drops >20% from previous bucket
4. Return cliff threshold with estimate

**Response:**
```json
{
  "overdemand_cliff": {
    "threshold": 180000,
    "settlement_rate_below": 0.72,
    "settlement_rate_above": 0.31,
    "warning": "Demands above $180K in this injury category settle 57% less often"
  }
}
```

**Bar compliance:** Descriptive framing only — "Historical data shows..." not "You should demand..."

#### 3.2.3 Override Tracking

When user submits a case that differs significantly from the estimate they received, track the delta.

**Schema:**
```sql
CREATE TABLE settle_estimate_overrides (
    id UUID PRIMARY KEY,
    query_id UUID REFERENCES settle_queries(id),
    contribution_id UUID REFERENCES settle_contributions(id),
    estimate_median DECIMAL,
    actual_outcome DECIMAL,
    delta_pct DECIMAL,
    delta_direction VARCHAR(10), -- 'above' or 'below'
    created_at TIMESTAMPTZ
);
```

**Analytics:**
- Override rate per user
- Override accuracy (do overrides outperform estimates?)
- Learn from consistent overriders (adjust their personal multiplier)

#### 3.2.4 Weekly Intelligence Digest

Automated email to active users with:
- New comparable cases in their jurisdictions (count)
- Stale data alerts (no submissions in X days)
- Coverage gaps (injury types with n<50 in their state)
- Trend highlights (notable settlement shifts)

**Service:** Extend existing `email_service.py` with digest template.

#### 3.2.5 Recency Weighting

Add time-decay factor to percentile calculations:

```python
def recency_weight(submission_date: datetime, reference_date: datetime) -> float:
    days_old = (reference_date - submission_date).days
    if days_old <= 180:
        return 1.5  # Last 6 months: 1.5x weight
    elif days_old <= 365:
        return 1.2  # 6-12 months: 1.2x weight
    elif days_old <= 730:
        return 1.0  # 1-2 years: baseline
    else:
        return 0.7  # 2+ years: 0.7x weight
```

Integrate into existing `weighted_percentile()` in `estimator.py`.

#### 3.2.6 Firm-Wide Yield Analytics (via API Key Grouping)

Since SETTLE uses a single shared DB (not tenant-isolated), group by API key prefix or custom firm ID.

**Approach:**
- Add `firm_id` optional field to API keys
- All keys with same `firm_id` are grouped
- Analytics endpoint returns firm-aggregated stats

**Endpoint:** `GET /api/v1/analytics/firm-yield`

```json
{
  "firm_id": "firm_abc123",
  "total_contributions": 142,
  "total_queries": 389,
  "yield_by_injury_type": [
    {"injury": "Herniated Disc", "avg_settlement": 89000, "count": 34, "vs_community": "+12%"},
    {"injury": "Soft Tissue", "avg_settlement": 42000, "count": 67, "vs_community": "-5%"}
  ],
  "yield_by_attorney": [
    {"api_key_name": "Attorney A", "avg_settlement": 78000, "count": 89},
    {"api_key_name": "Attorney B", "avg_settlement": 95000, "count": 53}
  ]
}
```

---

## Phase 4: Litigation Outcome Prediction (Later Phase)

**Rationale:** Re-added per your direction. Deferred to later phase due to bar-compliance constraints and data maturity requirements.

**Key constraint:** SETTLE's design philosophy explicitly rejects "predictive modeling." This feature must be framed as **descriptive risk analysis**, not prediction.

### 4.1 Reframing for Bar Compliance

| Avoid | Use Instead |
|---|---|
| "Predict settlement" | "Historical outcome distribution" |
| "AI predicts" | "Statistical analysis of comparable cases" |
| "X% chance of winning" | "X% of similar cases resulted in plaintiff verdict" |
| "Recommended demand" | "Observed demand range in comparable cases" |
| "Case value" | "Historical settlement benchmarks" |

### 4.2 Feature Set

**4.2.1 Outcome Distribution Analysis**

For a given case profile, show the historical distribution of outcomes:

```json
{
  "outcome_distribution": {
    "settlement": {"rate": 0.72, "avg_amount": 85000, "count": 144},
    "plaintiff_verdict": {"rate": 0.18, "avg_amount": 210000, "count": 36},
    "defense_verdict": {"rate": 0.07, "avg_amount": 0, "count": 14},
    "dismissed": {"rate": 0.03, "count": 6}
  },
  "sample_size": 200,
  "jurisdiction": "Harris County, TX",
  "case_type": "Auto Accident",
  "injury_tags": ["Herniated Disc", "Soft Tissue"]
}
```

**4.2.2 Trial Risk Indicators**

Descriptive indicators based on historical patterns:

| Indicator | Description | Data Source |
|---|---|---|
| Trial propensity | % of similar cases that went to trial | Verdict DB + settlement DB |
| Verdict direction | Plaintiff vs. defense win rate in trials | Verdict DB |
| Verdict premium | How much verdicts exceed settlements on average | Both DBs |
| Time to resolution | Median days for each outcome type | Both DBs |

**4.2.3 ML Model Architecture (Future)**

When data maturity allows (10K+ contributions + 5K+ verdicts):

- **Input features:** jurisdiction, case_type, injury_tags[], medical_bills, liability_tier, defendant_category, outcome_type
- **Model:** Gradient boosting (XGBoost) or Random Forest — interpretable, feature-importance available
- **Output:** Probability distribution over outcome types + amount range
- **Explainability:** SHAP values for each prediction (why this outcome?)
- **Validation:** Cross-validation against held-out jurisdiction data

**4.2.4 Compliance Gates**

Before this feature goes customer-facing:
- [ ] Bar ethics opinion review (all 5 states)
- [ ] "Descriptive not predictive" language audit
- [ ] Disclaimer language in all outputs
- [ ] Opt-in consent from users
- [ ] No PHI/PII in training data
- [ ] Model transparency (methodology document)

**Deliverables:**
- [ ] Outcome distribution analysis service
- [ ] Trial risk indicator service
- [ ] Verdict DB ↔ Settlement DB join queries
- [ ] Compliance review package
- [ ] ML model prototype (internal only)
- [ ] Customer-facing API (post-compliance approval)

---

## Phase 5: Docket/Litigation Tracker (Future Expansion)

**Rationale:** Re-added per your direction. Separate service, not integrated into settlement platform. Scraped data only, no community contributions.

### 5.1 Scope

This is a **separate service** (`DOCKET-Service`) that runs parallel to SETTLE. It does NOT share the settlement database. Data may be cross-referenced in the future for expanded product offerings.

### 5.2 Data Sources

| Source | Type | Data |
|---|---|---|
| PACER/RECAP | Federal | Dockets, filings, orders, judgments |
| State court portals | State | Varies by jurisdiction |
| CourtListener API | Aggregator | Federal + some state dockets |
| Legal news sites | Scraped | Verdict announcements, settlement reports |
| Law360/VerdictSearch | Scraped | Published verdicts and settlements |

### 5.3 Schema (Separate Database)

```sql
CREATE TABLE docket_cases (
    id UUID PRIMARY KEY,
    court_id VARCHAR(50),
    case_number VARCHAR(100),
    case_name VARCHAR(500), -- May contain names (separate DB, different compliance)
    case_type VARCHAR(100),
    filing_date DATE,
    status VARCHAR(50),
    judge_name VARCHAR(200),
    plaintiff_attorney VARCHAR(200),
    defense_attorney VARCHAR(200),
    plaintiff_firm VARCHAR(200),
    defense_firm VARCHAR(200),
    parties JSONB,
    claims JSONB,
    outcomes JSONB,
    damages_claimed DECIMAL,
    damages_awarded DECIMAL,
    settlement_amount DECIMAL,
    last_activity_date DATE,
    source VARCHAR(100),
    source_url TEXT,
    scraped_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ
);
```

### 5.4 Features (Future)

- Docket search by attorney, firm, judge, jurisdiction
- Case timeline tracking
- Outcome aggregation by judge/court
- Filing pattern analysis
- Settlement vs. trial rate by firm
- Expert witness appearance tracking
- Damages trend analysis

### 5.5 Integration Points with SETTLE (Future)

| Integration | Description | Phase |
|---|---|---|
| Verdict enrichment | Cross-reference SETTLE settlements with docket verdicts | Phase 4 |
| Judge analytics | Judge tendency data for SETTLE reports | Phase 4 |
| Firm benchmarking | Compare firm settlements to docket outcomes | Phase 5+ |
| Expert witness data | Expert history for SETTLE carrier patterns | Phase 5+ |
| Case lifecycle tracking | Track SETTLE-contributed cases through docket | Phase 5+ |

### 5.6 Compliance Considerations

- Court data is public record — different compliance regime than SETTLE
- Names and PII are permissible (public records)
- Still need to consider terms of service for scraping sources
- PACER has usage limits and fees
- State court portals vary widely in access policies

**Deliverables:**
- [ ] Separate service scaffolding (`DOCKET-Service/`)
- [ ] PACER/RECAP scraper
- [ ] CourtListener API integration
- [ ] State court portal scrapers (priority jurisdictions first)
- [ ] Docket database schema
- [ ] Search API
- [ ] Cross-reference service (DOCKET ↔ SETTLE)

---

## Feature Priority Matrix

| Priority | Feature | Phase | Effort | Impact |
|---|---|---|---|---|
| P0 | Internal Verdict Research Engine (15+ filters) | Phase 1 | Medium | High |
| P0 | Demand Confidence Score (customer-facing) | Phase 2 | Low | High |
| P0 | Advanced Search Filters (customer-facing) | Phase 2 | Low | Medium |
| P1 | Insurer/Carrier Pattern Analytics | Phase 2 | Medium | High |
| P1 | CRM Integrations (Filevine, Clio) | Phase 2 | High | High |
| P1 | Multiplier Model Layer (SettleCase Models 01-03) | Phase 3 | Medium | High |
| P1 | Overdemand Cliff Detection | Phase 3 | Medium | Medium |
| P2 | Override Tracking | Phase 3 | Low | Medium |
| P2 | Weekly Intelligence Digest | Phase 3 | Low | Medium |
| P2 | Recency Weighting | Phase 3 | Low | Medium |
| P2 | Firm-Wide Yield Analytics | Phase 3 | Medium | Medium |
| P2 | Trend Studies / Market Reports | Phase 2 | Low | Medium |
| P3 | Litigation Outcome Prediction (descriptive) | Phase 4 | High | High |
| P3 | ML Model Prototype | Phase 4 | High | Medium |
| P4 | Docket/Litigation Tracker (separate service) | Phase 5 | Very High | High |
| P4 | PACER/RECAP Integration | Phase 5 | High | Medium |

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA SOURCES                            │
├──────────────────┬──────────────────┬───────────────────────┤
│  Founding Member │  Web Scraping    │  CRM Integrations     │
│  Contributions   │  (Verdicts)      │  (Filevine, Clio)     │
└────────┬─────────┴────────┬─────────┴───────────┬───────────┘
         │                  │                     │
         ▼                  ▼                     ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  SETTLE DB       │ │  Internal        │ │  SETTLE DB       │
│  (settlements)   │ │  Verdict DB      │ │  (settlements)   │
│  Shared,         │ │  (verdicts)      │ │  Shared,         │
│  anonymized      │ │  Internal only   │ │  anonymized      │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                     │
         │              ┌─────┴─────┐               │
         │              │ Future:   │               │
         │              │ Cross-    │               │
         │              │ Reference │               │
         │              └───────────┘               │
         │                                          │
         ▼                                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     SETTLE SERVICES                         │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  Estimator   │  Intelligence│  Confidence  │  Carrier       │
│  (percentile │  Gate        │  Score       │  Patterns      │
│  + multiplier)│ (n≥50)      │  (0-100)     │  Analytics     │
└──────────────┴──────────────┴──────────────┴────────────────┘
         │                                          │
         ▼                                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     OUTPUT LAYER                            │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  API         │  PDF Reports │  Trend       │  Weekly        │
│  Responses   │  (4-page)    │  Reports     │  Digest        │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

---

## Compliance Checklist

| Requirement | Status | Notes |
|---|---|---|
| No PHI/PII in SETTLE DB | Enforced | Anonymizer service |
| No free-text narratives | Enforced | Dropdown-only fields |
| No predictive language | Enforced | Descriptive framing only |
| No liability assessment | Enforced | Generic defendant categories |
| No legal advice | Enforced | Disclaimer in all outputs |
| n≥50 credibility floor | Enforced | IntelligenceGate |
| Bar-compliant PDF reports | Enforced | 4-page template |
| Blockchain verification | Enforced | OpenTimestamps |
| Consent confirmed | Enforced | Required on submission |
| Outcome distribution (Phase 4) | Pending | Bar review required |
| ML prediction (Phase 4) | Pending | Descriptive reframing required |
| Docket data (Phase 5) | N/A | Separate service, public records |

---

## Open Questions

1. **Point 5 was cut off** — what is the fifth feature/direction you wanted to add?
2. **Internal verdict DB** — should it live in the same Supabase project (separate schema) or a completely separate project?
3. **CRM integration priority** — Filevine first, or Clio first? (Filevine has larger PI market share but Clio has better API docs)
4. **Multiplier table values** — should we calibrate these from scraped verdict data, or use published industry standards?
5. **Overdemand Cliff** — should this be returned with every estimate, or only on request?
6. **Firm grouping** — API key prefix vs. explicit `firm_id` field for firm-wide analytics?
7. **Weekly digest recipients** — all active users, or opt-in only?
8. **Docket service** — should it be a separate repo entirely, or a new service within this monorepo?
