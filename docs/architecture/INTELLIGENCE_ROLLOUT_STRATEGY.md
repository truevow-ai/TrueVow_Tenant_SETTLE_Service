# TRUEVOW INTELLIGENCE ROLLOUT STRATEGY

**Version:** 1.0
**Date:** 2026-02-22
**Status:** ARCHITECTURAL PRINCIPLE

---

## CORE PRINCIPLE

> **Year 1 = Data Acquisition + Structured Consistency**
> **Year 2 = Credible Aggregation**
> **Year 3 = Asymmetric Leverage**

---

## PHASE 1: SEEDING (Months 1-12)

### Product Positioning

- **Primary Offer:** Paid Lead Revenue Protection
- **Intelligence Narrative:** "Founding Intelligence Partners — Build the Plaintiff-Side Colossus"
- **No dashboard sales** — only **prestige access**
- **Pricing**: See Billing Service API (`tier_features.per_use_price_cents`)

### Founding Partner Benefits

| Benefit | Source |
|---------|--------|
| Locked pricing | From `founding_members.pricing_locked_until` in database |
| Early dashboard access | From `founding_members.benefits_enabled` |
| Input on dashboard design | Cohort privilege |
| Recognition as founding contributor | From `founding_members.recognition_display_name` |

> Theyre not buying data  theyre buying influence.

---

## FOUNDING INTELLIGENCE COHORT

### Eligibility Requirements
| Requirement | Why |
|-------------|-----|
| 10+ unlocks/month | Data contribution |
| Submit structured reports | Verified dataset |
| Standardized classification | Comparability |
| Anonymized aggregation consent | Privacy |

### Cohort Benefits
| Benefit | Value |
|---------|-------|
| Locked pricing | Predictable |
| Early dashboard | First-mover |
| State distributions | Jurisdiction |
| Adjuster insights | Lowball ID |

---

### Settlement Reporting Rules

- **No minimum submissions**
- **Only report when cases resolve**
- **Incentivize quality:**
  - Verified submissions  unlock deeper insights later
  - No penalties for non-reporting

### Dashboard Reality (Months 1-12)

- Shows **only their own cases**
- Shows **aggregated signals as they emerge** (even n=7)
- **Always displays sample size:** "Similar cases (n=12)"
- **No fake data**  transparency builds trust

---

## PHASE 2: CREDIBLE AGGREGATION (Year 2)

### Trigger Condition

- **500+ structured settlements per state**
- **Minimum 3 states at threshold**

### Monetization Shift

- **Intelligence becomes a premium feature**
- **Growth/Team tier includes basic dashboard**
- **Advanced views require contribution**

### Contribution-Weighted Access

| Submission Tier | Unlocked Insight |
|----------------|------------------|
| 10 verified settlements | County-level distributions |
| 25 | Treatment-tier breakdowns |
| 50 | Policy-limit pattern analysis |
| 100 | Adjuster behavior scoring |

> No punishment  only progressive depth.

### Pricing Architecture

| Tier | Price | SETTLE Access | Includes |
|------|-------|---------------|----------|
| **SOLO** | Via API | No SETTLE | Via API |
| **GROWTH** | Via API | Via API | Via API |
| **TEAM** | Via API | Via API | Via API |

> All tier pricing, features, and quotas are defined in Billing Service database.
> Query via: `GET /api/v1/billing/tenants/{tenant_id}/feature-access`

---

## BILLING & SUBSCRIPTION ARCHITECTURE

### Data Source: Database

All values are configured in Billing Service database tables:

| Table | Purpose |
|-------|---------|
| `tiers` | Tier definitions with base prices |
| `services` | Service definitions (intake, settle, draft) |
| `tier_features` | Per-tier service inclusions, quotas, per-use prices |
| `addons` | Add-on definitions with pricing |
| `tenant_subscriptions` | Tenant tier assignments |
| `launch_config` | SETTLE launch thresholds |

### Query Example

```typescript
// Get actual values from API
const access = await billing.getFeatureAccess(tenantId);
// Returns: tier base price, per-use prices, monthly quotas
```

### SOLO Tier

- **Source**: Tier config in database
- **Price**: From `tier_features.per_use_price_cents`
- **Free unlocks**: From `tier_features.monthly_quota` (lifetime tracked separately)

### GROWTH Tier

- **Source**: Tier config in database
- **Monthly price**: From `tiers.base_price_monthly`
- **Included credits**: From `tier_features.monthly_quota`
- **Overage price**: From `tier_features.per_use_price_cents`

---

### SETTLE Launch Conditions

| Condition | Source |
|-----------|--------|
| Standard - Time | From `launch_config.months_threshold` |
| Standard - Data | From `launch_config.entries_threshold` |
| Early - Time | From `launch_config.early_months_threshold` |
| Early - Data | From `launch_config.early_entries_threshold` |

> Launch conditions are configured in `launch_config` database table.

### Feature Access API Endpoint

**Route:** `GET /api/v1/billing/tenants/{tenant_id}/feature-access`

**Query Parameters:**
- `tenant_id` (path, required)
- `user_id` (query, optional) - For attorney-level founding intelligence benefits

**Response:**
- Tier features (intake/settle/draft with enabled/source/price/quota)
- Active add-ons
- Founding intelligence member status
- SETTLE launch status (launched, entries_count, months_since_start)

**SaaS Admin Usage:**
```typescript
const access = await billingClient.getFeatureAccess(tenantId, userId);
// Returns complete feature access + founding member status
```

---

## SETTLE Service Agent Requirements

### Critical: Launch Status Check

SETTLE agent MUST check `settle_status.launched` before allowing any operations.

```typescript
// Check SETTLE launch status + access
GET /api/v1/billing/tenants/{tenant_id}/feature-access
```

### Required Response Fields

```typescript
{
  settle_status: {
    launched: boolean,      // Don't allow access if false
    entries_count: number,
    months_since_start: number
  },
  features: {
    settle: {
      enabled: boolean,     // False if not launched OR no access
      source: 'tier' | 'founding_benefit',
      per_use_price_cents: 0  // 0 if founding member
    }
  },
  founding_intelligence: {
    is_member: boolean,
    benefits_enabled: boolean,
    verified_submissions: number
  }
}
```

### Access Rules

| Condition | SETTLE Access |
|-----------|---------------|
| `settle_status.launched = false` | ❌ Blocked |
| `settle_status.launched = true` + GROWTH tier | ✅ Enabled |
| `settle_status.launched = true` + Founding member | ✅ Free access |

---

### SETTLE Service Agent Integration Spec

#### Launch Gate Requirement
SETTLE service **MUST NOT** operate until `settle_status.launched === true`. Hard gate.

#### Endpoint
`GET /api/v1/billing/tenants/{tenant_id}/feature-access?user_id={attorney_id}`

#### Access Validation
```typescript
if (!featureAccess.settle_status.launched) return false;
if (source === 'founding_benefit') return 0;  // Free
```

#### Launch Conditions
| Condition | Trigger |
|-----------|---------|
| Force | Admin `force_launch_date` passed |
| Standard | Months >= 6 OR entries >= 1000 |
| Early | Months >= 4 AND entries >= 750 |

#### Idempotency
`idempotency_key: settle:${caseId}:${reportId}`

#### Errors
| Status | Action |
|--------|--------|
| 404 | Tenant not found |
| launched=false | ServiceNotReadyError |
| 500 | Fail closed (deny) |

---

### Multi-Dimensional Feature Access

| Dimension | Source | Description |
|-----------|--------|-------------|
| **TIER** | Billing Service | SOLO, GROWTH, FOUNDING_INTELLIGENCE |
| **ADD-ONS** | Tenant Config | DRAFT add-on options |
| **COHORT** | Tenant Config | Founding Intelligence Cohort membership |

### Access Matrix

| Service | SOLO | GROWTH | GROWTH + DRAFT | Cohort Member |
|---------|------|--------|----------------|---------------|
| INTAKE | Via API | Via API | Via API | Via API |
| DRAFT | Via API | Via API | Via API | Via API |
| SETTLE Query | Via API | Via API | Via API | Via API |
| SETTLE Contribute | - | - | - | Via API |

### Data Sources

| Data | Source API |
|------|------------|
| All tier/pricing | `GET /api/v1/billing/tenants/{id}/feature-access` |
| Tier features | From `features.*.enabled` and `features.*.source` |
| Pricing | From `features.*.per_use_price_cents` |
| Founding status | From `founding_intelligence.*` |

### Feature Access Resolution (Login Time)

```typescript
interface TenantFeatureAccess {
  tier: 'SOLO' | 'GROWTH' | 'FOUNDING_INTELLIGENCE';
  draftAddOn: boolean;
  settleAddOn: boolean;      // For SOLO - not used
  foundingIntelligenceCohort: boolean;
}

function resolveSettleAccess(access: TenantFeatureAccess): boolean {
  // SETTLE available if:
  // 1. GROWTH tier (bundled)
  // 2. Founding Intelligence Cohort member
  return access.tier === 'GROWTH' || access.foundingIntelligenceCohort;
}
```

---

## PHASE 3: ASYMMETRIC LEVERAGE (Year 3+)

### Capabilities

- **Insurer pattern insights** (e.g., "State Farm lowballs 37% below median")
- **Defense firm settlement behavior**
- **Litigation vs. settlement ROI modeling**
- **Real-time adjuster negotiation alerts**

### Strategic Positioning

> **The Plaintiff-Side Settlement Intelligence Layer**
> Not a tool. Not a vendor. **The industry standard.**

---

## CRITICAL GUARDRAILS

### 1. Never Sell Empty Dashboards

- If n < 50 in a state  show only **own-case data**
- **No extrapolation**  only verified, structured signals

### 2. Prestige > Discounts

- Founding Partners get **locked pricing**, not cheaper unlocks
- **Recognition** ("Founding Contributor") matters more than cash

### 3. Contribution = Privilege, Not Obligation

- **No "submit or lose access"**
- **Only "contribute to see deeper"**

### 4. Data Integrity Over Speed

- **Reject unstructured submissions**
- **Require banded fields only**
- **No PII ever**

---

## CHICKEN & EGG SOLUTION

### The Problem

- Zero settlement data to start
- No one pays for empty dashboards
- No one contributes into a void

### The Solution

1. **Do not require 3 reports/month immediately**
   - Require reporting only when cases resolve
   - Incentivize high-quality submission

2. **Transparency in early data**
   - Show their own cases
   - Show early aggregated signals as they accumulate
   - Show sample size counts openly

3. **Growth/Team tier reasoning**
   - Intelligence must materially improve revenue
   - Make: Contribute  unlock deeper insights
   - Not: Contribute because we said so

---

## SETTLEMENT REPORT STRUCTURE (Mandatory Fields)

All submissions must include:

```json
{
  "intakeVersionId": "v2",
  "economicStrengthAtIntake": "High",
  "finalTreatmentEscalation": "Surgery completed",
  "settlementBand": "Premium",
  "policyLimitKnown": true,
  "timeToResolution": 187,
  "litigationFiled": false,
  "jurisdiction": "FL-Hillsborough"
}
```

> No PII. No narratives. No free text.
> Only structured, banded fields.

---

## POSITIONING

### Homepage Headline (Future State)
> The Plaintiff-Side Settlement Intelligence Layer
> Structured data to counter insurer lowballing.

### Current Positioning (Bridge)
> Paid Lead Revenue Protection
> (Funded by per-use unlocks, powered by deterministic intake)
> Pricing: See Billing Service API

### Never Say
- "AI intake assistant"
- "Virtual receptionist"
- "Lead generation"

---

## COMPLIANCE LANGUAGE

| Instead of | Use |
|-----------|-----|
| "Predict settlements" | "Aggregated anonymized benchmarks" |
| "AI analysis" | "Structured data aggregation" |
| "Settlement guarantee" | "Historical settlement bands" |

---

## WHY THIS WORKS

| Problem | Solution |
|---------|----------|
| Chicken & Egg | Seed with prestige, not promises |
| Weak early data | Show only what exists  transparency builds trust |
| Contribution friction | Gamify depth, not compliance |
| Monetization timing | Unlock revenue funds intelligence build |

> Youre not selling intelligence today. Youre funding the truth layer.

---

## FINAL VERDICT

This phased approach:

- **Protects revenue** in Year 1
- **Builds credibility** in Year 2
- **Creates asymmetric leverage** in Year 3
- **Aligns with fiduciary mission**

**Execute exactly as written.**
Patience isnt optional  its your strategic advantage.

The plaintiff-side Colossus isnt built in a quarter.
Its built case by case, settlement by settlement, attorney by attorney.
