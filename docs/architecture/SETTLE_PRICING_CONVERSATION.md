# SETTLE™ — Comprehensive Pricing Architecture Document

**Version:** 6.0
**Date:** 2026-04-27
**Status:** Living Document — appended to as new context emerges
**Purpose:** Provide a single source of truth for all SETTLE pricing discussions, ensuring LLMs and human stakeholders share full context before proposing pricing structures.

---

## TABLE OF CONTENTS

1. [The Product Essence](#1-the-product-essence)
2. [Primary Audience](#2-primary-audience)
3. [Economic Conditions](#3-economic-conditions)
4. [Core Pain Points](#4-core-pain-points)
5. [What They Fear](#5-what-they-fear)
6. [Emotional Triggers](#6-emotional-triggers)
7. [Purpose & Mission Architecture](#7-purpose--mission-architecture)
8. [How SETTLE Works](#8-how-settle-works)
9. [The Contribution-Retrieval Economic Loop](#9-the-contribution-retrieval-economic-loop)
10. [Strategic Rollout Plan](#10-strategic-rollout-plan)
11. [Current Pricing Model](#11-current-pricing-model)
12. [Tier Architecture & Access Matrix](#12-tier-architecture--access-matrix)
13. [Technical Architecture (Pricing-Relevant)](#13-technical-architecture-pricing-relevant)
14. [Strategic Constraints on Pricing](#14-strategic-constraints-on-pricing)
15. [Revenue Projections](#15-revenue-projections)
16. [Open Questions & Tensions](#16-open-questions--tensions)

## PART II: PROPOSED PRICING MODEL ⚠️ SUPERSEDED — See Part IV for Final Approved Model

17. [The Core Economic Problem](#17-the-core-economic-problem)
18. [The Three-Actor Economic Model](#18-the-three-actor-economic-model)
19. [The Cash Flow Reality of Your Customer](#19-the-cash-flow-reality-of-your-customer)
20. [The Belief Curve](#20-the-belief-curve)
21. [The Contribution Incentive Problem](#21-the-contribution-incentive-problem)
22. [The Founding Member Economics](#22-the-founding-member-economics)
23. [The Pricing Framework Emerges](#23-the-pricing-framework-emerges)
24. [The Actual Pricing Model (3 Phases)](#24-the-actual-pricing-model-3-phases)
25. [The Contribution Credit Mechanism](#25-the-contribution-credit-mechanism)

## PART III: MARKET EXPANSION & STRATEGIC DECISIONS

26. [The Intake Intelligence Opportunity](#26-the-intake-intelligence-opportunity)
27. [The Ethical Pricing Constraints](#27-the-ethical-pricing-constraints)
28. [The Competitor Analysis (Colossus)](#28-the-competitor-analysis-colossus)
29. [The Revenue Trajectory](#29-the-revenue-trajectory)
30. [The Critical Decisions You Must Make](#30-the-critical-decisions-you-must-make)
31. [Final Pricing Recommendation: The Complete Model](#31-final-pricing-recommendation-the-complete-model)

## PART IV: FINAL APPROVED PRICING MODEL ✅

32. [Final Positioning — What SETTLE Actually Is](#32-final-positioning--what-settle-actually-is)
33. [Critical Constraint — Low Data Reality](#33-critical-constraint--low-data-reality)
34. [Final Approved Pricing Model](#34-final-approved-pricing-model)
35. [Ecosystem Pricing Advantage](#35-ecosystem-pricing-advantage)
36. [Optional Performance-Based Layer (Future)](#36-optional--performance-based-layer-future)
37. [Reality Check — Real Usage Scenarios](#37-reality-check--real-usage-scenarios)
38. [Why This Model Is Correct](#38-why-this-model-is-correct)
39. [What You MUST Avoid](#39-what-you-must-avoid)
40. [Final Ecosystem View](#40-final-ecosystem-view)
41. [Final Answer — The Complete Model](#41-final-answer--the-complete-model)

## PART V: MARKETING & POSITIONING

42. [Pricing Page Copy & Positioning](#42-pricing-page-copy--positioning)

## PART VI: IN-PRODUCT TRIGGER DESIGN

43. [Trigger Architecture & Principles](#43-trigger-architecture--principles)
44. [Trigger Catalog — All Decision Points](#44-trigger-catalog--all-decision-points)
45. [Anti-Triggers — When NOT to Show](#45-anti-triggers--when-not-to-show)
46. [First-Use Experience](#46-first-use-experience)
47. [Trigger Calendar & Frequency Rules](#47-trigger-calendar--frequency-rules)

---

## 1. THE PRODUCT ESSENCE

**SETTLE** is a blockchain-verified, attorney-owned settlement intelligence database that functions as the plaintiff bar's ethical counterweight to Colossus — the insurance industry's proprietary valuation tool. It transforms fragmented, siloed settlement knowledge into collective bargaining power through network-effect data aggregation.

**Core Mechanism:**
- Plaintiff attorneys contribute anonymized, structured settlement data via a 3-minute form
- SETTLE returns instant settlement range estimates (<1 second) with county-level comparables
- Blockchain verification (OpenTimestamps) ensures data integrity and creates audit-proof reports
- Every contribution strengthens the database, creating exponential value growth

**Tagline:** *"The Plaintiff-Side Settlement Intelligence Layer — Structured data to counter insurer lowballing."*

**Service Type:** External shared service (centralized, not per-tenant)
**Database:** `settle_db` (single centralized database for all settlements)
**Access:** Open to customers AND non-customers (via API keys)
**Deployment:** Shared container (not per-tenant)
**Port:** `8002` (development), `8004` (production)

**Key Differentiator:** SETTLE is NOT tenant-specific — a single database shared across all users, API key-based authentication, accessible to non-TrueVow customers.

---

## 2. PRIMARY AUDIENCE

### Demographic Profile

**Primary: Solo & Small Firm Plaintiff Attorneys**
- Firm Size: 1-10 attorneys
- Practice Focus: Personal injury, employment law, medical malpractice, civil rights
- Geographic Distribution: Secondary and tertiary markets (underserved by BigLaw infrastructure)
- Case Volume: 20-150 active cases annually
- Average Case Value: $15,000-$250,000 (bread-and-butter PI work)
- Technology Adoption: Moderate — uses Clio/MyCase but skeptical of "AI solutions"

**Secondary: Larger Plaintiff Firms**
- Want competitive intelligence across jurisdictions and adjuster behavior patterns

**Tertiary: The Entire Plaintiff Bar**
- SETTLE is designed to be the industry-standard truth layer that every plaintiff attorney eventually needs, creating a counterweight to insurer data monopolies

---

## 3. ECONOMIC CONDITIONS

### The Financial Pressure Cooker

**Revenue Model Reality:**
- Contingency-based (33-40% of settlements)
- Cash flow is lumpy and unpredictable
- 6-18 month payment cycles from case intake to settlement
- Operating on personal credit cards during dry spells is common

**Cost Structure Pain Points:**
- High CAC for client acquisition ($800-$3,500 per signed client)
- Expert witness fees ($3,000-$15,000 per case)
- Medical record retrieval costs
- Litigation financing interest (if used)
- Technology subscriptions creeping toward $500-$1,200/month

**The Profitability Trap:**
- Must maximize settlement value on EVERY case (no "loss leaders")
- Cannot afford to leave $10K-$50K on the table per settlement
- Typically settling 40-60% of cases (rest dismiss/trial/attrition)
- A 10% improvement in average settlement = 25-30% profit increase

**Typical Firm Revenue:**
- Solo practitioners: $150K-$400K/year
- Small firms: $500K-$2M/year

**Price Sensitivity Profile:**
- HIGH for subscriptions (they hate monthly SaaS that doesn't directly pay for itself)
- LOW for per-use tools that demonstrably increase settlement value
- A $49 report that adds $10K to a settlement is an instant buy

**Competitive Disadvantage:**
- Defense/insurance attorneys use Colossus (they know the "floor" value)
- Solo attorneys negotiate blind — relying on "gut feel" and scattered war stories
- No access to institutional knowledge BigLaw firms have
- Adjusters exploit information asymmetry ruthlessly

---

## 4. CORE PAIN POINTS (Ranked by Intensity)

### 1. Information Asymmetry = Money Left on Table
*"I'm negotiating blind while the adjuster is looking at Colossus data that I'll never see."*
- Adjusters make first offers based on Colossus valuations
- Attorney counters based on... previous cases? Lawyer Facebook groups? Gut instinct?
- No way to validate if adjuster's "final offer" is actually final
- Perpetual fear: *Did I just accept $75K when I could've gotten $125K?*

### 2. Isolation & Knowledge Fragmentation
*"I have 47 settlements in my files. The attorney across town has 52. Together we'd have meaningful data. Separately, we're guessing."*
- Settlement knowledge dies in file cabinets
- No structured way to learn from peer outcomes
- CLE courses teach theory, not "what actually settled in your county last month"
- Referral networks share war stories, not structured data

### 3. Time Poverty & Decision Fatigue
*"I'm managing 60 cases, doing my own intake calls, and negotiating settlements while trying to pick up my kid."*
- Every settlement negotiation requires 3-8 hours of "research" (often Googling verdicts)
- Demand letter preparation lacks data-backed confidence
- Cannot afford to hire associates or paralegals for case valuation research

### 4. Credibility Deficit with Clients
*"My client Googled their injury and thinks they're getting $500K. How do I explain reality without losing their trust?"*
- Clients arrive with unrealistic expectations from TV ads and Google
- Attorney must "sell" the settlement value without comparative data
- Risk of malpractice claims: "My cousin's lawyer got $200K for the same injury!"

### 5. Ethical Tightrope
*"I need data to negotiate effectively, but I can't compromise client confidentiality or bar rules."*
- Terrified of bar complaints or malpractice suits
- Skeptical of tools that aren't explicitly bar-compliant
- Prior data-sharing attempts felt legally risky

### 6. Insurer Lowballing (Structural)
- Insurance companies use Colossus to systematically undervalue claims
- Attorneys have NO comparable data to push back
- Insurers see millions of claims; a solo attorney sees maybe 50-100/year

---

## 5. WHAT THEY FEAR

### Financial Fears
- **Leaving money on the table** → Missing mortgage payments, unable to reinvest in firm growth
- **Cash flow collapse** → Accepting low-ball offers out of desperation because rent is due
- **Losing cases to better-resourced firms** → Clients leave for firms with "better technology"

### Professional Fears
- **Malpractice exposure** → Client sues claiming "You settled too low"
- **Bar complaints** → Ethical violations from improper data use or data sharing
- **Reputation damage** → Being known as the attorney who "gives up too easy" on settlements

### Existential Fears
- **Technological irrelevance** → "Will AI-powered BigLaw firms make me obsolete?"
- **Perpetual underdog status** → "I became a lawyer to level the playing field, but I'm always outgunned"
- **Burnout** → "I can't sustain this grind for another 10 years"

### Situational Fears
- **Being outgunned at mediation** → Walking in knowing the adjuster has Colossus data and they have nothing
- **Losing to firms with better data** → Competitor down the street has SETTLE access; referral sources notice
- **Being replaced** → If AI/insurtech makes settlement valuation fully automated, the attorney becomes a commodity

---

## 6. EMOTIONAL TRIGGERS

### ⚡ Righteous Anger (Primary Motivator)
*"Insurance companies have Colossus. Why the hell shouldn't WE have our own tool?"*
- Visceral resentment toward Colossus as a "rigged game"
- Moral injury from knowing adjusters are using data to lowball their clients
- David vs. Goliath narrative resonates deeply

### 💪 Collective Empowerment
*"Imagine if every plaintiff attorney in America contributed data. We'd be unstoppable."*
- Hunger for solidarity in a fragmented profession
- Pride in being an "owner" of the solution, not just a customer
- Desire to leave a legacy: "I helped build the thing that changed plaintiff work"

### 🛡️ Professional Dignity
*"I want to walk into a negotiation with the same data the adjuster has — and maybe better data."*
- Craving respect from opposing counsel and adjusters
- Confidence boost: "I'm not guessing anymore — I have the data"
- Validation: "I'm a professional, not a hustler"

### 🤝 Peer Proof & FOMO
*"If the attorney down the hall is using SETTLE and I'm not, am I falling behind?"*
- Small legal communities are tight-knit (word spreads fast)
- Success stories create viral adoption: "Jane got $40K more on a soft tissue case using SETTLE"
- Fear of being the last to adopt a standard tool

### 🧠 Ethical Clarity
*"I need to know this is 100% bar-compliant before I even consider it."*
- Need for explicit ethics opinions, bar association endorsements
- Desire for transparent methodology (blockchain audit trail is compelling here)
- Willingness to pay MORE for a solution that's ethically bulletproof

### 🏆 Status & Legacy
*"They're not buying data — they're buying influence."*
- **"Founding Intelligence Partner"** — status and legacy. They're not buying a tool; they're building the plaintiff-side Colossus
- **"Locked pricing — forever"** — scarcity + security. In an inflationary world, a locked price is gold
- **Recognition** ("Founding Contributor") matters more than cash discounts

---

## 7. PURPOSE & MISSION ARCHITECTURE

### For the Individual Attorney:
1. **Instantly estimate fair settlement ranges** using comparable cases in their jurisdiction
2. **Negotiate with confidence** backed by data, not guesswork
3. **Reduce time spent on case valuation** from hours to minutes
4. **Increase average settlement values** by 10-25% through informed negotiation
5. **Defend settlement recommendations to clients** with credible, exportable reports
6. **Prove settlements were reasonable** — the compliance safety net against bar complaints

### For the Plaintiff Bar Collectively:
1. **Create a counterweight to Colossus** by aggregating decentralized plaintiff-side knowledge
2. **End information asymmetry** that allows insurers to systematically underpay claims
3. **Build institutional memory** that doesn't die when attorneys retire
4. **Strengthen negotiating leverage** through transparent, crowdsourced benchmarks

### For the Legal System:
1. **Accelerate fair settlements** by reducing friction caused by valuation disputes
2. **Increase access to justice** by making sophisticated valuation tools affordable to small firms
3. **Promote ethical data use** through bar-compliant, blockchain-verified transparency

### Strategic Mission (3-Year Horizon)

> **Year 1: Data Acquisition + Structured Consistency** — Seed the database with verified contributions from a prestige Founding Member cohort. Monetize via lead revenue protection, not dashboard sales.
>
> **Year 2: Credible Aggregation** — 500+ structured settlements per state. Intelligence becomes a premium feature. Dashboards go public.
>
> **Year 3: Asymmetric Leverage** — Insurer pattern insights (e.g., "State Farm lowballs 37% below median"), defense firm settlement behavior, litigation vs. settlement ROI modeling, real-time adjuster negotiation alerts. SETTLE becomes the industry standard.

> *"You're not selling intelligence today. You're funding the truth layer."*

---

## 8. HOW SETTLE WORKS

### Phase 1: Data Contribution (The Deposit)

**Attorney Action:**
- Logs into SETTLE after settling a case
- Enters structured data via intuitive 3-minute form:
  - `jurisdiction` (county/state, e.g., "FL-Hillsborough")
  - `injuryType` / `injurySeverity`
  - `medicalExpenses` (special damages band)
  - `economicStrengthAtIntake` (High/Medium/Low)
  - `finalTreatmentEscalation` (Surgery completed/Conservative only/etc.)
  - `settlementBand` (Premium/Standard/Below Standard)
  - `policyLimitKnown` (true/false)
  - `timeToResolution` (days)
  - `litigationFiled` (true/false)
  - `insuranceCarrier` (optional but valuable)
  - `settlementAmount`

> **ZERO PHI. ZERO narratives. ZERO free text.** Only structured, banded fields.

**SETTLE Action:**
- Anonymizes data (strips names, dates, identifiers)
- Encrypts and stores
- TrueVow admin reviews and approves contribution
- Contribution enters the anonymized pool and is available for queries

**Psychological Moment:** *"I'm not just entering data — I'm arming my colleagues with intelligence the insurers don't want us to have."*

### Phase 2: Data Retrieval (The Withdrawal)

**Attorney Action:**
- Preparing a demand letter or negotiating a settlement
- Logs into SETTLE, enters case parameters (injury type, county, medicals, liability)
- Clicks "Generate Report"

**SETTLE Returns (<1 second):**
- **Settlement range estimate** (25th, 50th, 75th percentile)
- **County-level comparables** (e.g., "12 similar cases in Harris County, TX settled between $45K-$85K in past 18 months")
- **Key variables impact** (e.g., "Cases filed in court settled 22% higher on average")
- **Confidence level indicator**
- **Sample size transparency:** "Similar cases (n=47)"
- **Insurer behavior patterns** (aspirational): "Allstate settles soft tissue cases 15% lower than State Farm in this jurisdiction"
- **Blockchain-verified 4-page PDF report** (for client meetings, demand letters, or mediation)

**Report Structure (4-page template):**
1. **Page 1:** Settlement Range Summary — box plot visualization, confidence indicator, comparable case count
2. **Page 2:** Comparable Cases Table — 10-15 anonymized similar cases, color-coded by confidence
3. **Page 3:** Range Justification — methodology, county clustering, adjustment factors
4. **Page 4:** Compliance & Integrity — "ZERO PHI" statement, OpenTimestamps blockchain hash, QR verification, disclaimer

**Psychological Moment:** *"I'm walking into this negotiation with the same intel the adjuster has — maybe better."*

### Phase 3: Network Effect Compounding (The Moat)

| Milestone | Database Size | Capability |
|-----------|--------------|------------|
| **Month 6** | 5,000 cases | Useful in major metros, spotty elsewhere |
| **Month 18** | 50,000 cases | Credible benchmarks in top 50 metro areas |
| **Month 36** | 250,000 cases | County-level precision nationwide, insurer behavior scoring launches |
| **Year 5** | 500,000+ cases | Industry-standard truth layer, real-time adjuster reputation tracking, predictive settlement AI |

**The Compounding Value Proposition:**
- Early contributors get lifetime preferential pricing (reward pioneer risk)
- Late adopters pay premium rates (buying mature infrastructure)
- Non-contributors pay highest rates (extraction pricing — using community asset without contributing)

---

## 9. THE CONTRIBUTION-RETRIEVAL ECONOMIC LOOP

### The Two-Sided Market Dilemma

SETTLE must balance:
1. **Incentivizing contribution** — data IS the product
2. **Funding operations** — cannot be free
3. **Preventing free-riding** — non-contributors degrade community trust
4. **Maintaining ethical purity** — no pay-to-play dynamics

### The Chicken & Egg Solution

**The Problem:**
- Zero settlement data to start
- No one pays for empty dashboards
- No one contributes into a void

**The Solution (from Rollout Strategy):**
1. **Do not require minimum submissions** — require reporting only when cases resolve; incentivize high-quality submission
2. **Transparency in early data** — show their own cases; show early aggregated signals as they accumulate; show sample size counts openly
3. **Gamify depth, not compliance** — "Contribute to see deeper" not "Contribute because we said so"
4. **Seed with prestige, not promises** — Founding Members are building influence, not buying data

### The Value Creation Paradox

- **Year 1:** Database has 10,000 cases → Reports are "interesting" but not authoritative
- **Year 3:** Database has 200,000 cases → Reports are litigation-grade credible
- **Attorney who contributed in Year 1 created far more value than they captured**

**Pricing Implication:** Early contributors must be rewarded disproportionately through:
- Lifetime discounted/locked report pricing
- Credit/equity mechanisms
- Status recognition (founder tier, public recognition)

### Contribution-Weighted Access (Progressive Depth)

| Submission Tier | Unlocked Insight |
|----------------|------------------|
| 10 verified settlements | County-level distributions |
| 25 | Treatment-tier breakdowns |
| 50 | Policy-limit pattern analysis |
| 100 | Adjuster behavior scoring |

> No punishment — only progressive depth.

### The Free-Rider Problem

**Risk:** Attorneys want data but don't want to contribute ("I'll wait until others build it")

**Psychological Barrier:** *"Why should I give away my hard-won knowledge?"*

**Pricing Must Address:**
- Contribution cannot feel like an obligation or tax
- Non-contributor pricing must create enough friction to nudge toward contribution without being punitive enough to drive users away
- The "contribute to unlock deeper insights" model must feel like a privilege upgrade, not a paywall on quality

---

## 10. STRATEGIC ROLLOUT PLAN

### PHASE 1: SEEDING (Months 1-12)

- **Primary Offer:** Paid Lead Revenue Protection
- **Intelligence Narrative:** "Founding Intelligence Partners — Build the Plaintiff-Side Colossus"
- **No dashboard sales** — only **prestige access**
- **Pricing:** Via Billing Service API (`tier_features.per_use_price_cents`)

### Founding Partner Benefits

| Benefit | Source |
|---------|--------|
| Locked pricing | `founding_members.pricing_locked_until` in database |
| Early dashboard access | `founding_members.benefits_enabled` |
| Input on dashboard design | Cohort privilege |
| Recognition as founding contributor | `founding_members.recognition_display_name` |

> *"They're not buying data — they're buying influence."*

### Founding Intelligence Cohort Eligibility

| Requirement | Why |
|-------------|-----|
| 10+ unlocks/month | Data contribution |
| Submit structured reports | Verified dataset |
| Standardized classification | Comparability |
| Anonymized aggregation consent | Privacy |

### Dashboard Reality (Months 1-12)
- Shows **only their own cases**
- Shows **aggregated signals as they emerge** (even n=7)
- **Always displays sample size:** "Similar cases (n=12)"
- **No fake data** — transparency builds trust

### PHASE 2: CREDIBLE AGGREGATION (Year 2)

**Trigger:** 500+ structured settlements per state, minimum 3 states at threshold
- Intelligence becomes a premium feature
- Growth/Team tier includes basic dashboard
- Advanced views require contribution

### PHASE 3: ASYMMETRIC LEVERAGE (Year 3+)

**Capabilities:**
- Insurer pattern insights (e.g., "State Farm lowballs 37% below median")
- Defense firm settlement behavior
- Litigation vs. settlement ROI modeling
- Real-time adjuster negotiation alerts

**Strategic Positioning:**
> *"The Plaintiff-Side Settlement Intelligence Layer — Not a tool. Not a vendor. The industry standard."*

---

## 11. CURRENT PRICING MODEL

### From Phase 2 Implementation Plan

| Tier | Price | Access |
|------|-------|--------|
| **Founding Members** | Free forever | First 2,100 attorneys (prestige cohort, lifetime free) |
| **Standard Users** | $49 per report | One-time payment per settlement range report |
| **Premium Subscription** | $199/month unlimited | High-volume firms |
| **Enterprise** | Custom pricing | Large firms, insurance companies, institutional buyers |

### Pricing Architecture (from Billing Service)

| Tier | Price Source | SETTLE Access |
|------|-------------|---------------|
| **SOLO** | `tier_features.per_use_price_cents` + free monthly quota | Via API |
| **GROWTH** | `tiers.base_price_monthly` + overage at per-use price | Via API |
| **TEAM** | Via API | Via API |

> All tier pricing, features, and quotas are defined in Billing Service database.
> Query via: `GET /api/v1/billing/tenants/{tenant_id}/feature-access`

---

## 12. TIER ARCHITECTURE & ACCESS MATRIX

### Current Tier Definitions

| Tier | Intake | DRAFT | SETTLE Query | SETTLE Contribute |
|------|--------|-------|-------------|-------------------|
| **SOLO** | Via API | Via API | Via API | — |
| **GROWTH** | Via API | Via API | Via API | — |
| **TEAM** | Via API | Via API | Via API | — |
| **Founding Intelligence Cohort** | — | — | Free | Via API |

### SOLO Tier
- Price: From `tier_features.per_use_price_cents`
- Free unlocks: From `tier_features.monthly_quota` (lifetime tracked separately)

### GROWTH Tier
- Monthly price: From `tiers.base_price_monthly`
- Included credits: From `tier_features.monthly_quota`
- Overage price: From `tier_features.per_use_price_cents`

### SETTLE Launch Conditions

| Condition | Source |
|-----------|--------|
| Standard - Time | `launch_config.months_threshold` |
| Standard - Data | `launch_config.entries_threshold` |
| Early - Time | `launch_config.early_months_threshold` |
| Early - Data | `launch_config.early_entries_threshold` |

**Hard Gate:** SETTLE service **MUST NOT** operate until `settle_status.launched === true`.
- Force launch: admin `force_launch_date` passed
- Standard launch: months ≥ 6 OR entries ≥ 1000
- Early launch: months ≥ 4 AND entries ≥ 750

### Access Rules

| Condition | SETTLE Access |
|-----------|---------------|
| `settle_status.launched = false` | ❌ Blocked |
| `settle_status.launched = true` + GROWTH tier | ✅ Enabled |
| `settle_status.launched = true` + Founding member | ✅ Free access |

### Multi-Dimensional Feature Access

| Dimension | Source | Description |
|-----------|--------|-------------|
| **TIER** | Billing Service | SOLO, GROWTH, TEAM |
| **ADD-ONS** | Tenant Config | DRAFT add-on options |
| **COHORT** | Tenant Config | Founding Intelligence Cohort membership |

---

## 13. TECHNICAL ARCHITECTURE (Pricing-Relevant)

### System Position

SETTLE is part of TrueVow's **5-service enterprise architecture**:

| Service | Port | Role |
|---------|------|------|
| Platform Service | 3000 | Tenant Management, Billing & Subscriptions |
| Internal Ops | 3001 | Task Management, Time Tracking |
| Sales Service | 3002 | Pipeline, Lead Qualification |
| Support Service | 3003 | Ticket Management, Shared Inbox |
| Tenant Service | 8000 | INTAKE, DRAFT, BILLING |
| **SETTLE Service** | **8002** | **Settlement Database, Range Estimation, Reports** |

### Database Architecture

**Three Separate Databases:**

1. **Tenant Databases** (`intake_[firm]`) — Per-firm isolation, leads, contacts
2. **SaaS Admin DB** (`saas_admin_db`) — Shared control plane: `users`, `tenants`, `pricing_tiers`, `subscriptions`, `billing`
3. **SETTLE DB** (`settle_db`) ⭐ — Settlement data: `settle_contributions`, `settle_api_keys`, `settle_founding_members`, `settle_queries`, `settle_reports`

### Billing Service Data Tables (Pricing Source of Truth)

| Table | Purpose |
|-------|---------|
| `tiers` | Tier definitions with base prices |
| `services` | Service definitions (intake, settle, draft) |
| `tier_features` | Per-tier service inclusions, quotas, per-use prices |
| `addons` | Add-on definitions with pricing |
| `tenant_subscriptions` | Tenant tier assignments |
| `launch_config` | SETTLE launch thresholds |

### Feature Access API

**Endpoint:** `GET /api/v1/billing/tenants/{tenant_id}/feature-access?user_id={attorney_id}`

**Returns:**
- Tier features (intake/settle/draft with enabled/source/price/quota)
- Active add-ons
- Founding intelligence member status
- SETTLE launch status (launched, entries_count, months_since_start)

### User Roles & Access

| User Type | Access | Permissions |
|-----------|--------|-------------|
| **Super Admin** | SaaS Admin + SETTLE | Full access: approve, reject, configure pricing |
| **Admin** | SaaS Admin + SETTLE | Approve/reject, view analytics |
| **Founding Member** | SETTLE API only | Query, contribute, generate reports (unlimited, free) |
| **Standard User** | SETTLE API only | Query, contribute, generate reports (paid) |
| **Anonymous** | Public website only | Join waitlist only |

---

## 14. STRATEGIC CONSTRAINTS ON PRICING

| Constraint | Implication |
|------------|-------------|
| **Founding members stay free forever** | Price discrimination between cohorts. Founding members built the database — they can't be charged. Max 2,100. |
| **Never sell empty dashboards** | If n<50 in a state, show only own-case data. Pricing must account for thin-data periods. |
| **Prestige > discounts** | Founding partners get locked pricing + recognition, not cheaper per-use. Status matters more than dollar amount. |
| **Contribution = privilege, not obligation** | No "submit or lose access." Only "contribute to see deeper." Gamify depth, don't penalize. |
| **Per-use pricing must feel trivial vs. settlement value** | A $49 report on a $200K case = 0.025%. Must feel like a rounding error. |
| **Pricing is hot-configurable by SaaS admins** | All tiers, per-use prices, quotas live in DB tables — not hardcoded. |
| **API-first means volume pricing matters** | High-volume API consumers need predictable costs. Per-call pricing must scale down with volume. |
| **No "pay to influence settlement data"** | Pricing must be clean, transparent, and defensible before every state bar. Ethics compliance is a moat. |
| **Data integrity over speed** | Reject unstructured submissions. Require banded fields only. No PII ever. |
| **Idempotency** | `idempotency_key: settle:{caseId}:{reportId}` — no double-charging |
| **Transfer messages hidden** | Messages containing "Transferring" (e.g., "Transferring back to supervisor") are hidden in chat UI and show no action buttons |

### Compliance Language Guardrails

| Instead of | Use |
|------------|-----|
| "Predict settlements" | "Aggregated anonymized benchmarks" |
| "AI analysis" | "Structured data aggregation" |
| "Settlement guarantee" | "Historical settlement bands" |

---

## 15. REVENUE PROJECTIONS

### From Admin Dashboard Mockup (Moderate Scale)

| Revenue Stream | Calculation | Monthly |
|----------------|-------------|---------|
| Standard Reports | 345/day × $49 | $16,905 |
| Premium Subscriptions | 30 × $199 | $5,970 |
| **Total** | | **$22,875/month** |

### Key Metrics Tracked
- Total Contributions (approved/pending/flagged)
- Founding Members (active ratio)
- Jurisdiction Coverage (states/counties)
- Daily Activity (queries, reports, new contributions)
- Revenue (breakdown by stream)

---

## 16. OPEN QUESTIONS & TENSIONS

These are the pricing-relevant tensions that a pricing structure must resolve:

1. **How to price Year 1 thin data honestly** without killing adoption? Transparency (show n-count) is the stated strategy, but pricing must not feel like paying for guesswork.

2. **How steep should the contributor vs. non-contributor price delta be?** Too steep = feels punitive, drives users away. Too flat = no incentive to contribute.

3. **Should contributions earn credits toward report purchases?** A credit system creates tangible reward for contribution without forcing subscription commitment.

4. **What's the upgrade path from SOLO → GROWTH → TEAM?** The per-use vs. subscription breakpoint needs economic modeling — at what query volume does $49/report exceed $199/month?

5. **How does enterprise/custom pricing work without creating a two-tier fairness perception?** Founding members who built the database can't feel like their data is being sold to insurers at premium rates.

6. **Should the contribution-gated insight tiers (10/25/50/100 submissions) have a parallel dollar path?** i.e., can you buy access to adjuster behavior scoring without contributing 100 cases? Or is contribution the ONLY path to deeper insight?

7. **What happens when the 2,100 Founding Member slots fill?** Does a waitlist create scarcity value? Does a "Founding Member Alumni" tier at reduced pricing preserve the prestige ladder?

---

## APPENDIX: Why This Works (Strategic Summary)

| Problem | Solution |
|---------|----------|
| Chicken & Egg | Seed with prestige, not promises |
| Weak early data | Show only what exists — transparency builds trust |
| Contribution friction | Gamify depth, not compliance |
| Monetization timing | Unlock revenue funds intelligence build |

> *"The plaintiff-side Colossus isn't built in a quarter. It's built case by case, settlement by settlement, attorney by attorney."*

---

*This document is designed to be appended to. When new context emerges, add sections below this line.*

---

# PART II: PROPOSED PRICING MODEL

## 17. THE CORE ECONOMIC PROBLEM

### The Value Creation Paradox

SETTLE has an **inverted value curve**:

```
Traditional SaaS:
Day 1 → High value (product is complete)
Year 3 → Same value (feature parity)

SETTLE:
Day 1 → Low value (database is empty)
Year 3 → Exponential value (network effects compound)
```

**The Pricing Challenge:**
You must charge enough to fund operations when the product delivers minimal value, while not alienating the contributors who will create massive future value.

This is not a "product pricing" problem. This is a **collective investment financing** problem.

---

## 18. THE THREE-ACTOR ECONOMIC MODEL

Every SETTLE user plays one or more of these roles:

| Role | Economic Function | Value Created | Value Extracted |
|------|------------------|---------------|-----------------|
| **Contributor** | Data supplier | 100% | 0-20% |
| **Consumer** | Intelligence buyer | 0% | 80-100% |
| **Evangelist** | Network expander | 50% (recruits others) | 20-40% |

**Critical Insight:**
The person who contributes 50 settlement cases in Year 1 creates **10x more value** than they can personally consume. But the person who joins in Year 3 and never contributes extracts value created by others.

**Pricing Must Solve:** How do you capture value from extractors without penalizing creators?

---

## 19. THE CASH FLOW REALITY OF YOUR CUSTOMER

Let's model a typical solo PI attorney's economics:

### Annual Case Flow
- 40 cases signed
- 25 cases settled (62.5% settlement rate)
- 10 cases dismissed/withdrawn
- 5 cases pending into next year

### Revenue Reality
- Average settlement: $85,000
- Attorney fee (33%): $28,050 per case
- **Gross revenue: $700,000/year**

### But Cash Flow Is Brutal
- Case costs advanced: $3K-8K per case (experts, records, depos)
- Average time to settlement: 14 months
- Marketing spend: $40K-80K/year (client acquisition)
- Overhead: $60K-100K/year (rent, staff, insurance)

**Net income: $180K-280K/year** (before taxes)

### The Settlement Value Sensitivity

Here's what matters for pricing:

| Settlement Improvement | Additional Attorney Revenue | % Increase |
|------------------------|----------------------------|------------|
| +5% per case | +$35,000/year | +12.5% net income |
| +10% per case | +$70,000/year | +25% net income |
| +15% per case | +$105,000/year | +37.5% net income |

**Pricing Principle #1:**
Any tool that credibly improves settlements by **even 3-5%** is worth $10K-20K/year to this attorney. The question is not "will they pay?" but "do they believe it works?"

---

## 20. THE BELIEF CURVE (Why Traditional Pricing Fails)

The problem with charging high prices on Day 1:

### Year 1: Database Has 8,000 Cases
- Attorney queries: "Soft tissue back injury, rear-end collision, $12K medicals, Harris County, TX"
- SETTLE returns: **n=4 comparable cases**
- Range: $18K-$65K (huge spread, low confidence)

**Belief Level:** 3/10 ("This is interesting but not actionable")
**Willingness to Pay:** $0-50 per query

### Year 3: Database Has 350,000 Cases
- Same query
- SETTLE returns: **n=247 comparable cases**
- Range: $32K-$48K (tight distribution, high confidence)
- PLUS: "State Farm settles 12% below county median for this injury type"
- PLUS: "Cases filed in litigation settle 28% higher on average"

**Belief Level:** 9/10 ("This is litigation-grade intelligence")
**Willingness to Pay:** $200-500 per query

**Pricing Principle #2:**
You cannot charge the same price for n=4 and n=247. The product is fundamentally different.

---

## 21. THE CONTRIBUTION INCENTIVE PROBLEM

### The Free-Rider Equilibrium

Without pricing incentives, rational attorneys will:
1. Wait for others to build the database
2. Join once it's valuable
3. Never contribute (why give away competitive intel?)

This creates a **death spiral:**
- No contributions → No database growth
- No database growth → No new users
- No new users → No revenue
- No revenue → Product dies

### The Failed Model: Mandatory Contribution

*"You must contribute 5 cases to access the database."*

**Why This Fails:**
- New attorneys don't HAVE 5 past cases
- Busy attorneys won't spend time on data entry
- Creates barrier to entry → slows user growth
- Feels punitive, not collaborative

### The Winning Model: Economic Gradient

Make contribution **economically rational** through pricing:

```
Contribution Status → Price Per Intelligence Unit

Heavy Contributor (20+ cases) → Effective price: $X
Moderate Contributor (5-19 cases) → Effective price: $3X
Light Contributor (1-4 cases) → Effective price: $6X
Non-Contributor → Effective price: $10X
```

**Pricing Principle #3:**
Non-contributors must subsidize contributors. This isn't punishment — it's fair payment for using community-created assets.

---

## 22. THE FOUNDING MEMBER ECONOMICS

You've committed to 2,100 Founding Members with lifetime free access.

### The Opportunity Cost
Assume each Founding Member would generate $800/year in revenue over 10 years:
- 2,100 members × $800/year × 10 years = **$16.8M foregone revenue**

### Why This Is Strategically Correct

**Founding Members are not customers — they are equity holders without shares.**

They provide:
1. **Data seed corn** → First 10K-20K cases that make the database credible
2. **Social proof** → "2,100 plaintiff attorneys built this"
3. **Distribution** → Each Founding Member recruits 3-5 others over time
4. **Ethics validation** → "This tool was reviewed and approved by 2,100 bar members"

**Pricing Principle #4:**
Founding Members are a customer acquisition cost, not a revenue line. Their $0 price is a CAC investment that returns 10-20x in Years 2-5.

---

## 23. THE PRICING FRAMEWORK EMERGES

### Core Pricing Variables

1. **Database Maturity** (sample size)
2. **Contribution Status** (has user contributed?)
3. **Usage Frequency** (queries per month)
4. **Timing** (when did they join?)

### The Multi-Axis Pricing Matrix

Instead of simple per-report pricing, we need:

**AXIS 1: Access Tier (When You Joined)**
- Founding Members (0-2,100): Lifetime access included
- Pioneer Members (Months 1-12): Locked favorable pricing
- Growth Members (Months 13-36): Standard pricing
- Standard Members (Year 3+): Full pricing

**AXIS 2: Contribution Credit**
- Contribution credits are earned by submitting cases
- Credits multiply the value of your access tier
- Credits never expire (you're building equity)

**AXIS 3: Usage Model**
- Pay-per-use (for occasional users)
- Monthly quota (for regular users)
- Unlimited (for high-volume users)

---

## 24. THE ACTUAL PRICING MODEL (3 PHASES)

### Phase 1: Data Acquisition (Months 1-12)

**Goal:** Acquire 15,000-25,000 cases from early adopters

#### Founding Member Track (Cap: 2,100)
- **Price:** $0 forever
- **Included:** Unlimited queries, unlimited contributions, founding member badge
- **Rationale:** These 2,100 are building the foundation. They ARE the product.

#### Pioneer Track (Months 1-12, uncapped)

**The "Venture Investment" Model**

Instead of charging for reports, charge an **annual platform access fee** that's refundable through contribution:

- **Base Annual Fee:** $1,200/year ($100/month)
- **Contribution Refund:** $50 per case contributed (up to $1,200)
- **Net Cost:** $0 if you contribute 24 cases/year, or $1,200 if you contribute 0 cases

**What You Get:**
- Unlimited query access (even if n is low)
- All reports include sample size disclosure
- When database matures, your $1,200/year rate is locked forever

**The Psychology:**
- "I'm investing $1,200 to fund the build"
- "But I get it all back by contributing my data"
- "And I'm locking in incredible pricing for when this becomes industry-standard"

**Revenue Model:**
- 1,000 Pioneer Members × $1,200/year = **$1.2M Year 1 revenue**
- If they contribute average 12 cases each = 12,000 cases + $600 net revenue each
- Actual Year 1 revenue: **$600K** (after contribution credits)

---

### Phase 2: Credible Aggregation (Months 13-36)

**Goal:** Reach 75,000-150,000 cases, establish state-level credibility

By now, database has enough cases that reports are genuinely valuable. Pricing can reflect delivered value, not promised value.

#### Founding Members
- **Price:** $0 forever (locked in)

#### Pioneer Members (joined Months 1-12)
- **Price:** $1,200/year locked forever (even as standard rates rise)
- **Contribution credits:** Still earn $50/case credits

#### Growth Track (NEW members joining Months 13-36)

**The "Usage Quota" Model**

- **Base Tier:** $2,400/year ($200/month)
  - Includes 50 queries/year
  - Overage: $60/additional query
  - Contribution credits: $75/case (up to $1,200)

- **Unlimited Tier:** $4,800/year ($400/month)
  - Unlimited queries
  - Contribution credits: $100/case (up to $2,400)

**The Psychology:**
- "The database now has 100K cases — this is real"
- "I'm paying $200/month, but my competitor who joined earlier pays $100/month"
- "I should have joined earlier... I should tell my colleagues to join NOW before rates rise again"

**Revenue Model:**
- 500 new Growth members × $2,400/year average = **$1.2M/year**
- Plus Pioneer members: 1,000 × $600/year = **$600K/year**
- **Phase 2 Revenue: $1.8M/year**

---

### Phase 3: Industry Standard (Year 3+)

**Goal:** 200K+ cases, become the plaintiff-side Colossus

The database is now comprehensive. County-level insights are statistically significant. You can introduce premium intelligence layers.

#### All Legacy Members (Founding + Pioneer + Growth)
- **Locked at their original pricing** (sacred promise)

#### Standard Track (NEW members joining Year 3+)

**The "Tiered Intelligence" Model**

**Basic Tier:** $4,800/year
- 100 queries/year
- Settlement range estimates only
- County-level comparables

**Professional Tier:** $8,400/year
- Unlimited queries
- Settlement range estimates
- County-level comparables
- Insurer behavior patterns ("State Farm settles 15% below median in your county")

**Enterprise Tier:** $15,600/year
- Everything in Professional
- Adjuster reputation scoring (individual adjuster historical patterns)
- Predictive settlement probability modeling
- API access for practice management integration
- White-label reports

**Contribution Credits:** $150/case against any tier (up to 50% of annual fee)

**The Psychology:**
- "This is now industry-standard infrastructure"
- "I'm paying $400-1,300/month, but it's improving my settlements by $50K-200K/year"
- "My colleague who joined in Year 1 pays $100/month for the same thing — damn"

**Revenue Model:**
- 3,000 Standard members × $7,000 average = **$21M/year**
- 1,000 Pioneer members × $600/year = **$600K/year**
- 500 Growth members × $1,200/year = **$600K/year**
- **Phase 3 Revenue: $22.2M/year**

---

## 25. THE CONTRIBUTION CREDIT MECHANISM

### How It Works

**Contribution Value Schedule:**

| Database Phase | Credit Per Case | Annual Cap |
|---------------|----------------|------------|
| Months 1-12 (Pioneer) | $50 | $1,200 |
| Months 13-36 (Growth) | $75 | $1,800 |
| Year 3+ (Standard) | $150 | 50% of tier price |

**Key Mechanisms:**

1. **Credits are applied at year-end** (prevents gaming)
2. **Unused credits roll over** (you're building equity, not spending coupons)
3. **Credits can upgrade your tier** (24 contributions = free Professional tier)
4. **Top contributors get public recognition** (leaderboard, state champions)

### Why This Works

**For Contributors:**
- Every case contributed reduces your effective price
- Contribution feels like investment, not charity
- Heavy contributors essentially use SETTLE for free

**For Non-Contributors:**
- They pay full price (subsidizing contributors)
- They see exactly what they're missing: "$150 credit per case contributed"
- Economic incentive to start contributing

**For SETTLE:**
- Continuous data inflow (even post-Founding Member period)
- Revenue from extractors funds platform development
- Virtuous cycle: more data → more value → more willingness to pay → more revenue → better platform → more contributions

### The Ethics of the Gradient

This is not price discrimination — it's **value-source pricing.**

- If you help create the asset → you pay less
- If you only consume the asset → you pay market rate
- If you consume heavily → you pay premium rate

Every state bar would find this more ethical than flat pricing, because it aligns economic incentives with collective benefit.

---

## APPENDIX II: Pricing Model Summary Table

| Phase | Member Type | Annual Price | Effective Net | Queries | Status |
|-------|-------------|-------------|---------------|---------|--------|
| **Phase 1** | Founding | $0 | $0 | Unlimited | Locked forever |
| (Months 1-12) | Pioneer | $1,200 | $0-1,200 | Unlimited | Locked at $1,200 |
| **Phase 2** | Growth Base | $2,400 | $600-2,400 | 50/year | Locked at Phase 2 rates |
| (Months 13-36) | Growth Unlimited | $4,800 | $2,400-4,800 | Unlimited | Locked at Phase 2 rates |
| **Phase 3** | Standard Basic | $4,800 | $2,400-4,800 | 100/year | Market rate |
| (Year 3+) | Standard Pro | $8,400 | $4,200-8,400 | Unlimited | Market rate |
| | Standard Enterprise | $15,600 | $7,800-15,600 | Unlimited + API | Market rate |

*Effective net assumes maximum contribution credits applied.*

---

# PART III: MARKET EXPANSION & STRATEGIC DECISIONS

## 26. THE INTAKE INTELLIGENCE OPPORTUNITY

You mentioned this is a separate conversation, but it's critically important for pricing strategy.

### The Economic Reality

PI attorneys spend $500-$2,000 to acquire a signed client. But they sign bad cases constantly:

- Case they thought was worth $75K settles for $12K
- Client has pre-existing injuries (unwinnable)
- Liability is actually disputed (not the slam-dunk it seemed)
- Statute of limitations already ran

**Every bad case signed costs:**
- $800-$2K intake overhead (sunk cost)
- 20-40 hours attorney time (opportunity cost)
- $3K-8K in advanced costs if litigated

### The SETTLE Intake Solution

**Pre-Signing Case Valuation:**
- Prospect calls: "I was rear-ended, I have $8K in medicals, soft tissue back injury"
- Intake coordinator enters into SETTLE API during the call
- SETTLE returns: "Comparable cases in your county: $18K-$32K (n=67)"
- Attorney decides: Sign this case OR pass

**The Value:**
If SETTLE helps you avoid signing just **3 bad cases per year**, it's worth:
- 3 × $2,000 (sunk intake costs) = $6,000
- 3 × 30 hours × $200/hr opportunity cost = $18,000
- **Total value: $24,000/year**

### Intake Pricing (Separate Product)

**SETTLE Intake Intelligence Add-On:**

- **$600/month** ($7,200/year)
- Unlimited pre-signing valuations
- Not tied to contribution credits (different use case)
- Integrates with existing intake software (Lawmatics, Clio Grow)

**Target Market:**
- Firms doing 100+ intakes/year
- Firms with dedicated intake coordinators
- Firms spending >$50K/year on client acquisition

**Revenue Potential:**
- 500 firms × $7,200/year = **$3.6M/year incremental revenue**

---

## 27. THE ETHICAL PRICING CONSTRAINTS

### What You CANNOT Do

**❌ Pay for contributions**
- "We'll pay you $50 for every case you submit"
- Creates incentive to fabricate data
- Ethically suspect (buying influence over settlement intelligence)

**❌ Create data quality tiers**
- "Premium members see 'verified' settlements, basic members see unverified"
- Implies you can pay for better data
- Bar complaint magnet

**❌ Allow users to see who contributed what**
- "This settlement was contributed by Smith & Associates"
- Violates anonymization promise
- Client confidentiality concerns

**❌ Offer "priority" contribution review**
- "Premium members' contributions are reviewed within 24 hours"
- Suggests you can pay to get your favorable settlements into the database faster

### What You CAN Do

**✅ Price based on usage frequency**
- "Unlimited queries cost more than 50 queries/year"
- Defensible: heavy users consume more infrastructure

**✅ Discount for contribution**
- "Contributors get credits toward their subscription"
- Defensible: they're reducing your data acquisition costs

**✅ Lock in early adopter pricing**
- "Join in Year 1, pay $1,200/year forever"
- Defensible: rewards early risk-taking

**✅ Charge more as database matures**
- "Year 1 members pay $1,200/year, Year 3 members pay $4,800/year"
- Defensible: product value increases with network effects

---

## 28. THE COMPETITOR ANALYSIS (Colossus)

### Why Colossus Pricing Doesn't Matter

**Colossus Economics:**
- Sold to insurance companies at $500K-$2M+ enterprise licensing
- Adjusters don't pay per-use (their employer pays)
- Built on 40 years of claims data
- Zero marginal cost to insurers (sunk cost)

**You Cannot Compete On:**
- Price (they're "free" to end users)
- Database size (40-year head start)
- Brand recognition (industry standard for 20+ years)

**You Must Compete On:**
- **Mission alignment** ("This is OUR tool, not theirs")
- **Ethical framing** ("Attorney-owned, bar-compliant, transparent")
- **Collective power** ("2,000 of us vs. the insurance industry")

### The Pricing Implication

Don't try to be cheaper than free. Try to be worth paying for DESPITE the free alternative.

**The Pitch:**
> "Adjusters have Colossus. You've been negotiating blind for your entire career. For $200/month, you can walk into every settlement negotiation with YOUR OWN data. The insurance industry spent $500M building Colossus. We're building the plaintiff-side version for $1,200/year per attorney. Are you in?"

**Pricing Principle #5:**
You're selling collective action, not a cheaper alternative. Price like a union, not like a discount vendor.

---

## 29. THE REVENUE TRAJECTORY

### Conservative Growth Model

| Phase | Timeline | Members | Avg Price | Annual Revenue | Cumulative |
|-------|----------|---------|-----------|----------------|------------|
| **Founding** | Months 1-6 | 2,100 | $0 | $0 | $0 |
| **Pioneer** | Months 7-12 | +1,000 | $600 net | $600K | $600K |
| **Growth Early** | Months 13-24 | +1,500 | $2,000 | $3M | $3.9M |
| **Growth Late** | Months 25-36 | +2,000 | $2,500 | $5M | $9.5M |
| **Standard Year 1** | Months 37-48 | +3,000 | $6,000 | $18M | $28.1M |
| **Standard Year 2** | Months 49-60 | +4,000 | $7,000 | $28M | $56.6M |

**Key Assumptions:**
- 30% annual churn (competitive market)
- Legacy members stay at locked pricing (drag on ARPU)
- 60% of new members are contributors (reduces effective price by 30%)

### Aggressive Growth Model

Assumes SETTLE becomes industry-standard faster:

| Phase | Timeline | Members | Avg Price | Annual Revenue |
|-------|----------|---------|-----------|----------------|
| **Year 3** | Months 25-36 | 8,500 | $3,500 | $29.75M |
| **Year 4** | Months 37-48 | 15,000 | $5,000 | $75M |
| **Year 5** | Months 49-60 | 25,000 | $6,000 | $150M |

**This assumes:**
- State bar associations endorse SETTLE
- Major legal tech platforms (Clio, Filevine) integrate SETTLE
- Malpractice carriers recommend SETTLE for risk mitigation

---

## 30. THE CRITICAL DECISIONS YOU MUST MAKE

### Decision 1: How Long Is "Founding Member" Enrollment Open?

**Option A: Time-Based (12 months)**
- Pro: Creates urgency ("Join before Month 12")
- Con: Might hit 2,100 cap early (lose urgency lever)

**Option B: Capacity-Based (2,100 members)**
- Pro: Absolute scarcity ("Only 847 founding slots left")
- Con: If uptake is slow, you're stuck with low prices for 18+ months

**Option C: Milestone-Based (When database hits 20K cases)**
- Pro: Ties pricing to value delivery
- Con: Unpredictable timeline

**Recommendation: Hybrid**
- Founding enrollment closes at FIRST of: 2,100 members OR Month 12 OR 25,000 cases in database
- Creates urgency on multiple dimensions

### Decision 2: Should Contribution Credits Expire?

**Option A: Credits Never Expire**
- Pro: Feels like equity (building permanent value)
- Con: Heavy contributors could accumulate $10K+ in credits (revenue impact)

**Option B: Credits Expire Annually**
- Pro: Predictable revenue (use-it-or-lose-it)
- Con: Feels transactional, not ownership

**Recommendation: Credits Never Expire, But Annual Cap Exists**
- You can accumulate unlimited credits
- But you can only APPLY up to 50% of your tier price per year
- Excess credits roll forward indefinitely
- Psychology: "I have $4,800 in banked credits — I'm basically a lifetime free member"

### Decision 3: Do Founding Members Pay for Premium Features?

**The Tension:**
- Founding Members get "lifetime free access"
- But in Year 4, you launch "Adjuster Reputation Scoring" at +$300/month
- Do Founding Members get this free, or is it a paid add-on?

**Option A: Founding Members Get Everything Free Forever**
- Pro: Honor the "founder" promise completely
- Con: Your most engaged users generate $0 revenue ever

**Option B: Founding Members Get "Core Platform" Free, Pay for Premium Add-Ons**
- Pro: Generates revenue from engaged users
- Con: Feels like bait-and-switch ("You said lifetime free!")

**Recommendation: Founding Members Get Tier 1 Free Forever, 50% Off All Add-Ons**
- Settlement range queries: Free forever (core promise)
- Premium intelligence (adjuster scoring, predictive AI): 50% off
- Framing: "You're a founder of the core platform. Premium R&D modules are optional — and you get founder pricing."

### Decision 4: How Do You Price API Access for Resellers?

**The Risk:**
- A practice management software company integrates SETTLE
- They have 5,000 law firm customers
- They pay you... what?

**Option A: Per-Seat Licensing**
- $50/month per attorney using their software
- 5,000 attorneys × $50 = $250K/month

**Option B: Revenue Share**
- They charge their customers $100/month for "SETTLE integration"
- You get 60% = $60/month per customer
- More aligned incentives

**Option C: Tiered Volume Pricing**
- 0-100 seats: $80/seat/month
- 101-1,000 seats: $50/seat/month
- 1,001+ seats: $30/seat/month

**Recommendation: Hybrid Revenue Share + Minimum**
- 50% revenue share on what they charge for SETTLE integration
- Minimum $25/seat/month (prevents them from bundling for "free")
- Quarterly true-up based on actual usage

---

## 31. FINAL PRICING RECOMMENDATION: THE COMPLETE MODEL

### FOUNDING MEMBER TIER (0–2,100 members, Months 1-12)
- **Price:** $0 forever
- **Access:** Unlimited queries, unlimited contributions
- **Lock-In:** Lifetime free access to core platform
- **Premium Add-Ons:** 50% off (when launched in Year 3+)

---

### PIONEER TIER (Months 1-12, uncapped)
- **Price:** $1,200/year ($100/month)
- **Access:** Unlimited queries (even during thin-data phase)
- **Contribution Credits:** $50/case (up to $1,200/year refund)
- **Lock-In:** $1,200/year rate locked forever
- **Net Cost:** $0/year if you contribute 24+ cases
- **Value Prop:** "Lock in $100/month pricing before it doubles in Year 2"

---

### GROWTH TIER (Months 13-36, uncapped)

**Standard Plan:**
- **Price:** $2,400/year ($200/month)
- **Access:** 60 queries/year
- **Overage:** $50/additional query
- **Contribution Credits:** $75/case (up to $1,200/year)
- **Lock-In:** $2,400/year rate locked forever

**Unlimited Plan:**
- **Price:** $4,800/year ($400/month)
- **Access:** Unlimited queries
- **Contribution Credits:** $100/case (up to $2,400/year)
- **Lock-In:** $4,800/year rate locked forever

---

### PROFESSIONAL TIER (Year 3+, uncapped)

**Basic Plan:**
- **Price:** $4,800/year ($400/month)
- **Access:** 120 queries/year
- **Includes:** Settlement ranges, county comparables
- **Contribution Credits:** $150/case (up to $2,400/year)

**Professional Plan:**
- **Price:** $8,400/year ($700/month)
- **Access:** Unlimited queries
- **Includes:** Settlement ranges, county comparables, insurer behavior patterns
- **Contribution Credits:** $150/case (up to $4,200/year)

**Enterprise Plan:**
- **Price:** $15,600/year ($1,300/month)
- **Access:** Unlimited queries + API access
- **Includes:** Everything + adjuster reputation scoring + predictive AI + white-label reports
- **Contribution Credits:** $150/case (up to $7,800/year)

---

### INTAKE INTELLIGENCE ADD-ON (Available All Phases)
- **Price:** $7,200/year ($600/month)
- **Access:** Unlimited pre-signing case valuations
- **Integration:** Clio Grow, Lawmatics, custom CRM via API

---

## APPENDIX III: Complete Pricing Ladder (All Tiers, All Phases)

| Tier | Phase | Price/Year | Eff. Net | Queries | Add-On Discount | Lock-In |
|------|-------|-----------|----------|---------|-----------------|---------|
| **Founding** | 1 | $0 | $0 | Unlimited | 50% off | Lifetime |
| **Pioneer** | 1 | $1,200 | $0-1,200 | Unlimited | None | Lifetime at $1,200 |
| **Growth Std** | 2 | $2,400 | $600-2,400 | 60/yr | None | Lifetime at $2,400 |
| **Growth Unl** | 2 | $4,800 | $2,400-4,800 | Unlimited | None | Lifetime at $4,800 |
| **Pro Basic** | 3 | $4,800 | $2,400-4,800 | 120/yr | None | Market rate |
| **Pro Pro** | 3 | $8,400 | $4,200-8,400 | Unlimited | None | Market rate |
| **Pro Ent** | 3 | $15,600 | $7,800-15,600 | Unlimited+API | None | Market rate |
| **Intake Add-On** | All | $7,200 | $7,200 | Unlimited | N/A | Add-on price |

*Effective net assumes maximum contribution credits applied. Founding Members: 50% off premium add-ons; all other legacy tiers retain original pricing forever.*

---

# PART IV: FINAL APPROVED PRICING MODEL ✅

*This section supersedes the proposed model in Part II. The analysis in Parts I, II, and III remains valuable context, but the pricing below is the definitive go-to-market structure.*

---

## 32. FINAL POSITIONING — WHAT SETTLE ACTUALLY IS

Strip everything to its essence:

> **SETTLE = settlement decision engine**

Used at exactly 2 moments:

1. **Before making a demand** (letter, email, mediation brief)
2. **Before accepting an offer** (the final gut-check)

👉 That's it. Not analytics. Not dashboards. Not contribution tracking.

**If SETTLE doesn't increase money per case at the moment that matters most → it's dead.**

### Ecosystem Positioning

The three-product stack:

| Product | Role | Revenue Type |
|---------|------|-------------|
| INTAKE | Get cases into the firm | Recurring + usage |
| LEVERAGE | Shape how cases evolve | Recurring |
| SETTLE | Monetize cases at decision points | Per-use |

This structure is clean, scalable, and psychologically correct.

---

## 33. CRITICAL CONSTRAINT — LOW DATA REALITY

**You don't have a dataset yet.**

So pricing must:
- Work with low data early
- Scale as data improves
- NOT depend on perfection

Even at 60-70% accuracy, the tool must still feel useful. The price point must reflect this reality — it's a decision aid, not a crystal ball.

---

## 34. FINAL APPROVED PRICING MODEL

### Architecture: 2-Layer Pricing

1. **Transactional** (default entry point)
2. **Subscription** (upgrade for power users)

No credits. No gamification. No founding member tiers. No phased lock-ins.

---

### LAYER 1 — Pay Per Case (Primary Entry)

**Price:**

### **$39 per settlement analysis**

**What they get:**
- Settlement range (low / mid / high)
- Comparable cases (early: heuristic + public data + internal)
- Confidence score
- Simple negotiation signal

**Why this works:**
- Zero commitment — no contract, no subscription required
- Feels like a "tool," not software
- Aligns with case-based thinking (how lawyers actually work)

**Psychological anchor:**
> *"This costs less than 0.1% of your case value"*

*(On an average $85K case, $39 = 0.046%. On a $15K case, it's still only 0.26%.)*

---

### LAYER 2 — Bundles (For Regular Users)

**Pricing:**

| Bundle | Price | Effective Per-Report |
|--------|-------|---------------------|
| 10 reports | **$349** | $34.90 each |
| 25 reports | **$799** | $31.96 each |

**Why:**
- Encourages prepayment (improves cash flow for SETTLE)
- Increases usage (reduces friction per decision)
- Creates lock-in (prepaid credits are sticky)

---

### LAYER 3 — Power Users (Subscription)

**Plan:** **SETTLE PRO**

**Price:** **$299/month**

**Includes:**
- 15 reports per month (included)
- $25 per additional report
- Priority processing
- Deeper comparables (as data grows)

**Who buys this:**
- Firms using it regularly (not experimenting)
- Firms that trust it (repeat users)
- Firms doing 10-30 cases/month

---

## 35. ECOSYSTEM PRICING ADVANTAGE

### The Cross-Product Discount

**If they use INTAKE + LEVERAGE:**

They get: **$29 per report (instead of $39)**

👉 This is NOT a random discount.

This is: **rewarding ecosystem behavior.**

| Scenario | Price/Report |
|----------|-------------|
| SETTLE only (standalone) | $39 |
| INTAKE + SETTLE | $29 |
| INTAKE + LEVERAGE + SETTLE | $29 |

**Strategic Rationale:**
- The full-stack customer is worth more lifetime revenue
- Ecosystem users have lower churn
- Data flow between products improves all three
- The bundle discount pays for itself through retention

---

## 36. OPTIONAL — PERFORMANCE-BASED LAYER (Future)

⚠️ **Do NOT launch this now. Too early. Too messy. Too risky.**

**Future model (Year 3+, credible data):**
- 3-5% of uplift (settlement improvement above baseline)
- OR success fee on demonstrably improved settlement

**Preconditions for launch:**
- Database has 100K+ verified cases
- Statistical significance across counties
- Bar association ethics opinion on contingency-based legal-tech pricing
- Insurance carrier willing to accept SETTLE reports as evidence

---

## 37. REALITY CHECK — REAL USAGE SCENARIOS

### Solo Firm
- 3 cases/month
- Uses SETTLE on all 3
- **Cost: 3 × $39 = $117/month**

### Growth Firm
- 8 cases/month
- Bundle user (25-pack every 3 months)
- **Cost: ~$280/month**

### Team Firm (PRO)
- 20 cases/month
- PRO plan: $299 + (5 overage × $25)
- **Cost: ~$424/month**

### High-Volume Firm (PRO + Bundle)
- 30 cases/month
- PRO plan: $299 + (15 overage × $25)
- **Cost: ~$674/month**

👉 All realistic. All affordable relative to case value. All sustainable for SETTLE.

---

## 38. WHY THIS MODEL IS CORRECT

### 1. Matches How Lawyers Think

Lawyers think: **"per case,"** not per seat, not per month, not per user.

A $39 report maps directly to: *"I have a case. I need a number. I pay $39."*

### 2. No Trust Barrier

No:
- Long-term commitment
- Big upfront cost
- Annual contracts
- Credit card lock-in

A solo attorney can try it ONCE for $39. If it works, they come back.

### 3. Scales Naturally

More cases → more usage → more revenue.

No complex upgrade logic. No tier migrations. No grandfathering debates.

### 4. Works with Weak Data Early

Even at 60-70% accuracy, $39 feels fair for a directional signal. The bundle and PRO tiers kick in only when users trust the product enough to commit.

### 5. Clean Ecosystem Story

| Product | Role | Revenue |
|---------|------|---------|
| INTAKE | get cases | recurring + usage |
| LEVERAGE | shape cases | recurring |
| SETTLE | monetize cases | per-use |

Each product has ONE clear revenue model. No confusion.

---

## 39. WHAT YOU MUST AVOID

### ❌ Subscription-Only Pricing
Too early. No trust. Nobody subscribes to an empty database.

### ❌ Cheap Pricing ($9/report)
Destroys perceived value. At $9, they assume it's garbage. At $39, they assume it's professional.

### ❌ Overcomplicated Tiers
No credits. No gamification. No founding member lock-ins. No phased pricing ladders.

*This was the error of the earlier proposed model (Part II). Complexity kills adoption when trust is zero.*

### ❌ "Free Trial" That Feels Like Bait
Not: "First 3 reports free, then $39" — that trains them to expect free.

Instead: "$39 per report. If it doesn't help, don't buy another."

---

## 40. FINAL ECOSYSTEM VIEW

| Product | Role | Revenue Type | Entry Price |
|---------|------|-------------|-------------|
| **INTAKE** | Get cases | Recurring + usage | Per-tenant SaaS |
| **LEVERAGE** | Shape cases | Recurring | Per-tenant SaaS |
| **SETTLE** | Monetize cases | Per-use | $39/report |

👉 That structure is clean, scalable, and psychologically correct.
The full stack creates a revenue machine where INTAKE feeds LEVERAGE, and LEVERAGE creates the settlement moments that trigger SETTLE purchases.

---

## 41. FINAL ANSWER — THE COMPLETE MODEL

### SETTLE Pricing (Locked)

| Tier | Price | Details |
|------|-------|---------|
| **Pay Per Case** | **$39/report** | Default. No commitment. Use as needed. |
| **Bundle 10** | **$349** | $34.90/report. Prepaid. |
| **Bundle 25** | **$799** | $31.96/report. Prepaid. |
| **SETTLE PRO** | **$299/month** | 15 reports included. $25/additional. Priority. Deeper comparables. |
| **Ecosystem Discount** | **$29/report** | If using INTAKE + LEVERAGE. Per-report or applies to bundle/PRO overage. |

### What's NOT in the model (by design)
- ❌ Founding Member free tier
- ❌ Contribution credits
- ❌ Phased pricing (Pioneer/Growth/Standard)
- ❌ Gamification leaderboards
- ❌ Performance-based fees (future only)
- ❌ Annual lock-in contracts

### Fiduciary Verdict

This model is:
- **Simple** → One number to remember: $39
- **Aligned** → Per-case pricing matches lawyer behavior
- **Monetizable early** → Works even with thin data
- **Scalable later** → PRO tier captures power users as data matures

---

## APPENDIX IV: Model Comparison — Proposed vs. Final

| Dimension | Part II Proposed | Part IV Final |
|-----------|-----------------|---------------|
| **Core price** | $1,200/year Pioneers | $39/report |
| **Structure** | Multi-phase, multi-axis (timing × contribution × usage) | 2-layer (transactional + subscription) |
| **Founding Members** | 2,100 free forever + prestige | Removed |
| **Contribution credits** | $50-150/case toward subscription | Removed |
| **Early adopter lock-in** | Lifetime price locks across phases | No lock-in (ecosystem discount instead) |
| **Complexity** | High (6 tiers, 3 phases, credit math) | Low (3 tiers, 1 ecosystem discount) |
| **Trust requirement** | High (annual commitment Year 1) | Low ($39 one-time) |
| **Data maturity** | Assumes 8K+ cases at launch | Works at 0 cases (heuristic + public data) |

**Why the shift:** The proposed model solved a collective-investment financing problem. The final model solves an adoption problem. When trust is zero and data is thin, per-use transactional pricing removes every barrier to the first purchase.

---

# PART V: MARKETING & POSITIONING

## 42. PRICING PAGE COPY & POSITIONING

*This is the customer-facing articulation of the Part IV pricing model. Every word is chosen for psychological effect.*

---

### Page Philosophy

SETTLE is where you **actually capture value**, not just create it.

The page must make the visitor feel:

> *"I'd be stupid not to use this before making a decision."*

No analytics fluff. No AI talk. Just money.

---

### Section 1: Opening — The Pain Hook

## 💰 Most Attorneys Don't Know What Their Case Is Really Worth

So they:
- Settle too early
- Accept low offers
- Or overplay weak cases

👉 And never know what they left on the table.

---

### Section 2: The Promise — One Thing

## 🧠 SETTLE Gives You One Thing:

> **A clear, structured view of what your case is likely worth — before you decide.**

Use it:
- Before sending a demand
- Before accepting an offer

---

### Section 3: How It Works — The Output

# ⚡ How It Works

For any case, SETTLE gives you:
- Expected settlement range (low / mid / high)
- Comparable cases
- Confidence level
- Simple negotiation signal

---

👉 Not theory. Not dashboards.
👉 A decision you can act on.

---

### Section 4: Pricing — Pay-As-You-Go

# 💰 Simple, Pay-As-You-Go Pricing

No subscription required.

---

## 🧾 Per Case Analysis

**$39 per case**

Use it only when you need it.

---

👉 *Run it on your most important cases — where the decision actually matters.*

---

## 📦 Bundles (Save on Regular Use)

- **10 reports → $349**
- **25 reports → $799**

---

👉 *Lower cost per case for firms that use it consistently.*

---

## 🚀 SETTLE PRO (For Frequent Users)

**$299 / month**

- 15 reports included
- Additional reports: $25 each
- Priority processing
- Deeper case comparisons (as dataset grows)

---

👉 *Best for firms that rely on SETTLE as part of every negotiation.*

---

### Section 5: Ecosystem Cross-Sell

# 🔗 Better Together with INTAKE + LEVERAGE

If you're already using TrueVow:
- **$29 per case instead of $39**
- Faster, more accurate inputs
- Seamless case flow from intake → decision

---

👉 The more you use the system, the stronger your results.

---

### Section 6: Use Cases — When It Triggers

# ⚡ When Firms Use SETTLE

## Before a Demand
Know if you're underpricing the case.

## Before Accepting an Offer
Know if you're settling too low.

## During Negotiation
Adjust strategy with actual data.

---

### Section 7: Value Justification — ROI Math

# 🧾 What This Means in Real Terms

If SETTLE helps you improve:
- **just one case by $5,000+**

👉 it pays for itself many times over.

---

### Section 8: Risk Mitigation — What It's NOT

# ⚠️ What SETTLE Is NOT

- Not legal advice
- Not a replacement for your judgment
- Not a guarantee

👉 It's a decision tool — you stay in control.

---

### Section 9: CTA

# 🚀 Get Started

Stop guessing what your case is worth.

👉 **Run your first SETTLE analysis**

---

### Section 10: Strategy Notes — Why This Page Works

# 🧠 Why this page works (internal — do not publish)

| Tactic | Implementation |
|--------|---------------|
| **Fear anchor** | Opens with "Most attorneys don't know what their case is worth" — triggers fear of under-settling |
| **Single promise** | "One thing: a clear view of what your case is worth before you decide" — no feature list |
| **Case-based pricing** | $39 per case matches lawyer mental model, not SaaS subscription thinking |
| **Zero commitment** | "No subscription required" removes the biggest objection immediately |
| **Bundle psychology** | "Save on regular use" — frames bundles as smart, not upsells |
| **PRO as aspiration** | "For frequent users" — positions PRO as the tier you graduate to, not the one you're pushed into |
| **Ecosystem soft sell** | "Better Together" section is separate from pricing — doesn't dilute the standalone pitch |
| **ROI math** | "Improve just one case by $5,000" — makes $39 feel trivial; any attorney can think of a case where this applies |
| **Risk reversal** | "What SETTLE is NOT" section preempts bar ethics concerns and builds trust |
| **Decision triggers** | Explicit use cases (before demand, before accepting offer, during negotiation) — tells them WHEN to reach for SETTLE |
| **No AI language** | Not "AI-powered," not "machine learning" — just "structured view" and "comparable cases" |

---

### Copy Rules (For Any Future Pricing Page Edits)

1. **Never say "analytics"** — it sounds like a dashboard they'll never open
2. **Never say "AI"** — triggers skepticism in this audience
3. **Always tie to a decision moment** — "before you..." is the most powerful phrase
4. **Keep numbers concrete** — "$39" not "affordable pricing"
5. **One CTA** — don't give them multiple actions; one path to "run your first analysis"
6. **The $5,000 anchor must stay** — it's the single most important line for conversion

---

# PART VI: IN-PRODUCT TRIGGER DESIGN

## 43. TRIGGER ARCHITECTURE & PRINCIPLES

### Core Insight

SETTLE is NOT something attorneys will remember to use. It must appear **at the exact moment of decision** — when the attorney is staring at a case and thinking: *"What do I do next?"*

### Design Principles

| Principle | Rule | Why |
|-----------|------|-----|
| **Never block workflow** | SETTLE is a tool, not a gate. Prompts are suggestions, not requirements. | If they can't skip it, they'll resent it. |
| **Match the emotional state** | Pre-demand = confident. Offer received = anxious. Trigger tone must match. | Wrong tone at wrong moment = ignored. |
| **Show value before price** | The trigger sells the insight, not the $39. | They buy the decision confidence, not the report. |
| **One decision, one trigger** | Don't show multiple SETTLE prompts at once. | Cognitive load kills action. |
| **Respect recency** | If they ran SETTLE on this case in the last 7 days, suppress the trigger. | Redundant prompts = noise. |
| **First use is special** | New SETTLE users get different prompts than regulars. | You're building a habit, not just selling a report. |
| **Data-aware honesty** | If n<10 comparable cases, the prompt should say so. | Trust destroyed by overpromising is permanent. |

### Trigger Types

| Type | Use When | Intrusiveness | Examples |
|------|----------|--------------|----------|
| **Inline Banner** | Moderate decision moments | Low | Case detail page, case list |
| **Modal Prompt** | High-stakes decisions | High | Pre-demand, pre-acceptance |
| **Action Button** | Persistent availability | Minimal | Always-visible in case toolbar |
| **Email / Notification** | Calendar-based triggers | Medium | Mediation reminder, weekly digest |
| **Dashboard Widget** | Portfolio-level awareness | Minimal | "3 cases ready for analysis" |

---

## 44. TRIGGER CATALOG — ALL DECISION POINTS

---

### T1: PRE-DEMAND — "Ready to send your demand letter?"

**Priority:** 🔴 HIGH (highest conversion)
**Product:** LEVERAGE
**Trigger condition:** Case status changes to "Ready for Demand" OR attorney clicks "Prepare Demand Letter"
**Placement:** Modal (primary) + Inline Banner (secondary, in case detail view)

**Copy:**
```
┌─────────────────────────────────────────────────┐
│  🎯 Before You Send This Demand                 │
│                                                 │
│  You're about to put a number in writing.       │
│  Make sure it's the right one.                  │
│                                                 │
│  SETTLE shows you what similar cases in         │
│  [County Name] actually settled for — so you    │
│  know if you're leaving money on the table.     │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  ▶ Run SETTLE Analysis — $39           │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  Skip for now →                                 │
└─────────────────────────────────────────────────┘
```

**Psychological mechanism:** *"You're about to put a number in writing"* — triggers fear of commitment. The demand letter is a one-way door. Once sent, you can't un-send a low number.

**Frequency rule:** Show once per case, when status first enters "Ready for Demand." Suppress if SETTLE was run on this case in the last 7 days.

---

### T2: OFFER RECEIVED — "Insurance offered $X. Is that fair?"

**Priority:** 🔴 HIGH
**Product:** LEVERAGE
**Trigger condition:** Settlement offer logged in system (attorney enters offer amount)
**Placement:** Inline Banner (immediate, in offer entry confirmation) + Action Button (persistent)

**Copy:**
```
┌─────────────────────────────────────────────────┐
│  💰 $[Offer Amount] Received                    │
│                                                 │
│  Before you counter or accept — know where      │
│  this stands.                                   │
│                                                 │
│  SETTLE compares this offer to real outcomes    │
│  for similar [Injury Type] cases in             │
│  [County Name].                                 │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  ▶ See How This Compares — $39         │   │
│  └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**Psychological mechanism:** The adjuster just named a number. The attorney's immediate emotional response is either relief ("that's decent") or anger ("that's insulting"). Both are dangerous. The trigger inserts data between emotion and decision.

**Smart variant:** If the offer is below the typical range for that injury/county → stronger language: *"This offer appears low for [County]. See comparable settlements."*

**Frequency rule:** Show on every new offer logged. If multiple offers on same case, show each time (each offer is a new decision).

---

### T3: PRE-ACCEPTANCE — "About to accept $X?"

**Priority:** 🔴 HIGH
**Product:** LEVERAGE
**Trigger condition:** Case status changes to "Settlement Accepted" OR attorney clicks "Accept Offer"
**Placement:** Modal (must appear before confirmation)

**Copy:**
```
┌─────────────────────────────────────────────────┐
│  ⚠️ Final Decision                              │
│                                                 │
│  You're about to accept $[Offer Amount].        │
│                                                 │
│  Once accepted, there's no going back.          │
│                                                 │
│  Run a SETTLE analysis to confirm this is       │
│  a fair outcome before you close the case.      │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │  ▶ Confirm With SETTLE — $39           │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  I'm confident — accept without analysis →      │
└─────────────────────────────────────────────────┘
```

**Psychological mechanism:** *"Once accepted, there's no going back"* — this is the highest-anxiety moment in any case. The modal must feel like a safety check, not a sales pitch. The dismiss option ("I'm confident") is essential — it respects their judgment while making the responsible choice explicit.

**Frequency rule:** Show once per acceptance event. This is a safety net, not a nag.

---

### T4: MEDIATION PREP — "Mediation in 48 hours"

**Priority:** 🟡 MEDIUM
**Product:** LEVERAGE
**Trigger condition:** Mediation date is within 48 hours AND SETTLE not run on this case in last 14 days
**Placement:** Email notification (primary) + Dashboard Banner (secondary)

**Copy (Email):**
```
Subject: Mediation tomorrow — [Case Name]

You have mediation for [Case Name] tomorrow.

Attorneys who walk into mediation with SETTLE data
settle 18% higher on average.

Run your analysis now →

[Case: Johnson v. State Farm]
[Injury: Soft tissue back, $12K medicals]
[Jurisdiction: Harris County, TX]

▶ Get Settlement Range for This Case — $39
```

**Copy (Dashboard Banner):**
```
┌─────────────────────────────────────────────────┐
│  📅 Mediation Tomorrow                          │
│  [Case Name] • [County] • [Injury Type]         │
│  ▶ Get your walk-away number →                 │
└─────────────────────────────────────────────────┘
```

**Psychological mechanism:** Mediation is the highest-pressure settlement moment. The attorney will make binding decisions in hours. The 18% stat creates social proof. The "walk-away number" framing makes SETTLE feel like armor, not a tool.

**Frequency rule:** Email at 48 hours before mediation. Dashboard banner at 24 hours. Suppress both if SETTLE already used.

---

### T5: INTAKE QUALIFICATION — "See what this case might be worth"

**Priority:** 🟡 MEDIUM
**Product:** INTAKE
**Trigger condition:** Lead score ≥ 70 (qualified) AND case type is personal injury AND attorney hasn't signed yet
**Placement:** Inline Banner on lead detail page

**Copy:**
```
┌─────────────────────────────────────────────────┐
│  💡 Worth a Closer Look                         │
│                                                 │
│  This lead looks strong. See what similar       │
│  cases in [County] typically settle for         │
│  before you decide to sign.                     │
│                                                 │
│  ▶ Preview Settlement Range →                  │
└─────────────────────────────────────────────────┘
```

**Note:** This trigger leads to a **preview** (not the full paid report). The preview shows a generic sample report for that injury type and county — not the prospect's actual case. It demonstrates the product without giving away the analysis. The preview ends with: *"Ready to run this on your actual case? $39"*

**Psychological mechanism:** Intake is where bad cases get signed. This trigger positions SETTLE as a case-screening tool — preventing costly mistakes before they happen. The preview model respects the "no free reports" rule while still demonstrating value.

**Frequency rule:** Show for every qualified lead with PI case type. Max once per lead.

---

### T6: NEGOTIATION STALLED — "No movement in 21 days"

**Priority:** 🟢 LOWER
**Product:** LEVERAGE
**Trigger condition:** Last offer/counter logged >21 days ago AND case status is "In Negotiation" AND SETTLE not run in last 30 days
**Placement:** Inline Banner on case detail + Dashboard Widget

**Copy:**
```
┌─────────────────────────────────────────────────┐
│  ⏳ Negotiation Stalled                         │
│                                                 │
│  No movement on [Case Name] in 21 days.         │
│                                                 │
│  Fresh data might break the impasse.            │
│  See if your position is supported by           │
│  comparable settlements in [County].            │
│                                                 │
│  ▶ Get Updated Range — $39                     │
└─────────────────────────────────────────────────┘
```

**Psychological mechanism:** Stalled negotiations are frustrating. The attorney may be anchored to a number that isn't realistic. SETTLE provides an external reference point to re-anchor the negotiation.

**Frequency rule:** Show once at 21 days, again at 45 days if still stalled. Different copy on second trigger (stronger language).

---

### T7: WEEKLY CASE DIGEST — "3 cases ready for SETTLE"

**Priority:** 🟢 LOWER
**Product:** Cross-product (LEVERAGE + INTAKE)
**Trigger condition:** Weekly (every Monday, 8am local time) for users who have ≥1 qualified case AND haven't used SETTLE in 7+ days
**Placement:** Email (primary)

**Copy (Email):**
```
Subject: 3 cases that could use a SETTLE check

This week, you have [3] active cases where
a SETTLE analysis could make a difference:

1. [Case Name] — Ready for demand
   ▶ Get Settlement Range →

2. [Case Name] — Offer pending ($[X])
   ▶ See How It Compares →

3. [Case Name] — Mediation Friday
   ▶ Get Walk-Away Number →

Each analysis: $39. Bundle 10: $349.

[Run All 3 → $117]
```

**Psychological mechanism:** The digest creates a "to-do list" framing. Instead of selling reports, it's helping them manage their week. The per-case pricing means each line item has a clear price and a clear action.

**Frequency rule:** Weekly on Mondays. Suppress if they used SETTLE in the last 7 days (they're already engaged). Suppress if 0 qualified cases.

---

### T8: PERSISTENT TOOLBAR BUTTON — Always Available

**Priority:** 🟢 LOWER (passive)
**Product:** LEVERAGE (case detail view)
**Trigger condition:** Always visible on case detail toolbar for PI cases
**Placement:** Case detail toolbar, right side

**Copy:**
```
┌──────────────────┐
│  📊 SETTLE       │
│  $39             │
└──────────────────┘
```

**States:**
- Default: "📊 SETTLE — $39" (gray, inactive look)
- After running: "📊 SETTLE ✓" (green check, last run date tooltip)
- Hover: "View settlement range for this case"

**Psychological mechanism:** This is the zero-friction access point. No prompt, no modal — just a button. It exists for the attorney who already knows they want SETTLE and doesn't need to be sold.

**Frequency rule:** Always visible for PI cases. Hidden for non-PI case types (criminal, family law, etc. — irrelevant).

---

### T9: MILESTONE REACTIVATION — "Your data just got better"

**Priority:** 🟢 LOWER (retention)
**Product:** Cross-product
**Trigger condition:** Database crosses a significance threshold for that user's most common jurisdiction/injury combination AND user hasn't used SETTLE in 30+ days
**Placement:** Email

**Copy:**
```
Subject: SETTLE just got stronger for [County]

We now have [247] comparable cases in [County]
for [Injury Type] — enough for high-confidence
settlement ranges.

The last time you checked, we had [n].
Things have changed.

▶ Run a fresh analysis →

[Case Type] in [County]: now n=247
```

**Psychological mechanism:** This is the network-effect trigger. It tells the user: *"The product you tried before is now better."* It converts lapsed users by showing tangible improvement — not marketing, but data.

**Frequency rule:** Max once per 90 days. Only when the n-count has meaningfully improved (e.g., 2x or crossed a threshold like n=50, n=100, n=250).

---

## 45. ANTI-TRIGGERS — WHEN NOT TO SHOW

These rules prevent SETTLE from becoming annoying:

| Condition | Action |
|-----------|--------|
| **User ran SETTLE on this case in last 7 days** | Suppress ALL triggers for this case |
| **User dismissed a SETTLE trigger in last 48 hours** | Suppress same trigger type |
| **Case has been settled for >30 days** | Suppress all triggers (case is closed) |
| **Case type is NOT personal injury / employment / med mal** | Hide SETTLE button, suppress all triggers |
| **User has 0 payment method on file** | Show triggers but add "Add payment method" to CTA flow |
| **User is on free/legacy plan without SETTLE access** | Show triggers with "Upgrade to access SETTLE" CTA |
| **Database has <5 comparable cases for this query** | Suppress high-confidence language; show "Limited data available" variant |
| **User is in middle of active workflow** (e.g., mid-form, mid-document generation) | Defer trigger until workflow completes |

---

## 46. FIRST-USE EXPERIENCE

### The First Trigger Is Different

A user who has never used SETTLE needs a different experience than a regular:

**New User Flow (First Trigger Ever):**
1. Normal trigger appears (e.g., T1: Pre-Demand)
2. User clicks CTA
3. Instead of immediate payment → **Sample Report Preview**
   - Shows a generic, anonymized SETTLE report for their jurisdiction/injury type
   - Not their case — a demonstration of format and depth
   - Ends with: *"Ready to run this on [Case Name]? $39"*
4. User clicks "Run Analysis" → enters payment → gets their actual report
5. Payment method saved for future one-click purchases

**New User Flow (Second Trigger — Same Case):**
- Payment already on file
- One-click: *"Run SETTLE — $39"* → immediate report

**New User Flow (Third+ Trigger):**
- Same one-click experience
- Begin showing bundle upsell after 5th purchase: *"You've run 5 analyses. Save with a 10-pack: $349"*

---

## 47. TRIGGER CALENDAR & FREQUENCY RULES

### Per-Case Trigger Cadence

```
Case Lifecycle:

INTAKE ─────────────────────────────────────────────►
  │
  └─ T5: Lead qualified ── "See what this might be worth"

LEVERAGE ───────────────────────────────────────────►
  │
  ├─ T1: Ready for demand ── Modal: "Before you send"
  │
  ├─ T2: Offer received ── Banner: "Is this fair?"
  │
  ├─ T6: 21 days stalled ── Banner: "No movement"
  │
  ├─ T4: Mediation in 48h ── Email: "Walk-away number"
  │
  ├─ T2: New offer ── Banner: "Is this fair?" (repeat)
  │
  └─ T3: Pre-acceptance ── Modal: "Final decision"

CROSS-PRODUCT ───────────────────────────────────────►
  │
  ├─ T7: Weekly digest ── Email: "3 cases ready"
  │
  ├─ T8: Toolbar button ── Always visible on case detail
  │
  └─ T9: Milestone reactivation ── Email: "Data got better"
```

### Global Frequency Caps

| Cap | Rule |
|-----|------|
| **Modals** | Max 1 modal per user per day (across all cases) |
| **Banners** | Max 1 banner per case per session |
| **Emails** | Max 2 SETTLE emails per user per week |
| **Dashboard widgets** | Always visible, no cap |
| **Bundle upsells** | Show after 5th purchase, again after 15th |

---

## APPENDIX V: Trigger Copy Quick-Reference Card

| ID | Moment | Headline | CTA | Type | Priority |
|----|--------|----------|-----|------|----------|
| T1 | Pre-Demand | "Before you send this demand" | Run SETTLE Analysis — $39 | Modal | 🔴 |
| T2 | Offer Received | "$X received. Know where this stands." | See How This Compares — $39 | Banner | 🔴 |
| T3 | Pre-Acceptance | "Final decision" | Confirm With SETTLE — $39 | Modal | 🔴 |
| T4 | Mediation Prep | "Mediation tomorrow" | Get your walk-away number → | Email | 🟡 |
| T5 | Intake Qualified | "Worth a closer look" | Preview Settlement Range → | Banner | 🟡 |
| T6 | Negotiation Stalled | "No movement in 21 days" | Get Updated Range — $39 | Banner | 🟢 |
| T7 | Weekly Digest | "3 cases ready for SETTLE" | Run All 3 → $117 | Email | 🟢 |
| T8 | Always Available | "SETTLE — $39" | (Button click) | Toolbar | 🟢 |
| T9 | Data Milestone | "SETTLE just got stronger" | Run a fresh analysis → | Email | 🟢 |

---

*This document is designed to be appended to. When new context emerges, add sections below this line.*


# PART VII: CONFIDENCE-BASED BILLING & COPY CORRECTION

*This section corrects earlier pricing page copy (Section 42) that mixed old acquisition ideas with the final pricing model. The rules below supersede any conflicting language in Sections 42 and 44.*

---

## 48. CONFIDENCE-BASED BILLING RULES

### The Problem

The pricing page copy and several triggers reference county-level data as if always available. In the first two years, it will not be. Promising county-level certainty before the database supports it destroys trust on first use.

### The Solution

Do **not** promise county-level certainty in the first two years. Instead:

> *"When county-specific data is limited, SETTLE uses the closest available comparable signals -- state, region, injury type, treatment pattern, medical bill range, and liability profile -- and clearly labels confidence."*

That is credible.

### The 4-Tier Billing Rule

| Confidence | Data Available | User Pays? |
|-----------|----------------|------------|
| **High** | County-level or strong jurisdiction-specific comparable data | ✅ Full price |
| **Medium** | State/regional data; county sample limited | ✅ Full price + limitation disclosed |
| **Low** | Sparse data, directional range possible | ⚠️ User confirms before paying (preview shown) |
| **None** | Not enough data for meaningful output | ❌ No charge |

### Tier Detail

**High Confidence:** County-level data available. Charge full price.

**Medium Confidence:** State/regional data available, but county-specific sample is limited. Charge full price, but disclose the limitation clearly. Why? Because the report still has value -- it gives a directional signal backed by real data, just not county-specific data.

**Low Confidence:** Sparse data, but a directional range is possible. Show preview first:
> *"Limited data available. SETTLE can generate a directional report using state/regional comparables. Confidence: Low. Continue?"*
Charge only if user accepts.

**No Confidence:** Rare injury type, no regional signal, no comparable treatment pattern, no useful settlement range. Show:
> *"SETTLE does not yet have enough comparable data to produce a reliable report for this case. You have not been charged."*
No charge. This builds trust.

### Why This Balance Works

- **Doesn't make everything free** -- medium-confidence reports still have negotiation value
- **Doesn't charge for nothing** -- no-confidence reports are free
- **Gives users control** -- low-confidence reports are opt-in
- **Builds trust** -- honesty about limitations creates credibility for when data IS good

---

## 49. PRICING PAGE COPY CORRECTION

### Remove (from any prior draft copy)

> "After 11 FREE reports (90 days), it's $39 per report. INTAKE users get 3 FREE reports/month, then $29/report."

This line is from an older growth idea. It conflicts with the final pricing strategy in three ways:
1. **11 free reports** makes SETTLE feel cheap, beta, and confusing
2. **3 free reports/month forever** is too generous and creates confusion
3. It fights against the pricing page where SETTLE is positioned as a serious decision tool

### Replace With (Final Approved Copy)

> **SETTLE is $39 per report. TrueVow ecosystem users receive discounted access at $29 per report. New INTAKE users receive 3 complimentary SETTLE reports during onboarding. If SETTLE does not have enough data to generate a meaningful report, you are not charged.**

This is clean, honest, and commercially sane.

### Trigger Copy Updates Required (Section 44)

All trigger copy in Section 44 that references "[County Name]" should be revised to use confidence-aware language:

- **T1 (Pre-Demand):** Replace *"what similar cases in [County Name] actually settled for"* with *"what similar cases settled for (with confidence level clearly shown)"*
- **T2 (Offer Received):** Replace *"for similar [Injury Type] cases in [County Name]"* with *"for similar [Injury Type] cases, using the best available data"*
- **T4 (Mediation Prep):** The county reference in the email body is aspirational -- acceptable if tagged with confidence level in the actual report
- **T5 (Intake Qualified):** Replace *"what similar cases in [County] typically settle for"* with *"what similar cases typically settle for"*

---

## 50. CORRECTED PRICING & POLICY TABLE

### Final Billing Policy

| Scenario | User Pays? |
|----------|-----------|
| County-specific data available | ✅ Full price |
| State/regional comparable data available | ✅ Full price, with disclosure |
| Low-confidence directional report available | ⚠️ User confirms before paying |
| Not enough data for meaningful report | ❌ No charge |

### Final Pricing (Clean -- No Legacy Offers)

| User Type | SETTLE Pricing |
|-----------|---------------|
| Standalone | $39/report |
| INTAKE + LEVERAGE ecosystem | $29/report |
| SETTLE PRO | $299/month, 15 included, $25 extra |
| New INTAKE user onboarding | 3 complimentary reports (one-time, not monthly) |

### Explicitly Killed (Do Not Resurrect)

- ❌ 11 free reports for 90 days
- ❌ 3 free reports/month forever for INTAKE users
- ❌ County-level precision promises before data supports them
- ❌ Any language implying SETTLE has a mature dataset at launch

**Bluntly: no 11 free reports, no monthly free reports forever, no fake county precision.**

---

## APPENDIX VI: Section 42 & 44 Revision Notes

When implementing the pricing page and in-product triggers, apply these corrections:

**Section 42 (Pricing Page Copy) -- Lines to revise:**
- Remove any reference to "county" as a guaranteed data source; replace with "best available comparable data"
- Add the confidence disclosure language from Section 48 as a footnote or info tooltip on the pricing page
- Add near the pricing: *"If SETTLE cannot generate a meaningful report, you are not charged."*

**Section 44 (Trigger Catalog) -- Triggers to revise:**
- T1, T2, T4, T5: Remove county-name placeholders; replace with confidence-level placeholders
- All triggers that lead to a report: Pre-prompt with the confirmation step when confidence is Low

**Section 46 (First-Use Experience) -- Addition:**
- The sample report preview (for first-time users) should show a Medium Confidence example -- honest about limitations while demonstrating value

---

*This document is designed to be appended to. When new context emerges, add sections below this line.*



---

## 51. SETTLE PRO ROLLOVER BANK POLICY

### Problem

Tracking each unused report by issuance month sounds precise, but operationally it is annoying, harder to explain, and will create support disputes. A per-report expiration date creates an unnecessary bookkeeping headache for a product that needs to feel simple at the moment of decision.

### Solution: Rolling Annual Rollover Bank

Replace per-report expiration tracking with a **rolling annual rollover bank** capped at **63 reports**.

### The Clean Rule

> **Unused included reports roll into your Pro rollover bank while your subscription remains active, capped at 63 reports. Your rollover bank resets to zero at each annual subscription anniversary and does not carry over after cancellation.**

### How It Works

| Scenario | Rollover Bank |
|----------|--------------|
| Month 1: 4 unused | Bank = 4 |
| Month 2: 3 unused | Bank = 7 |
| Month 3: 7 unused | Bank = 14 |
| Month 4: 15 unused | Bank = 29 |
| Month 5: 15 unused | Bank = 44 |
| Month 6: 15 unused | Bank = 59 |
| Month 7: 4 unused | Bank = 63 (cap reached) |
| Month 8+: any unused | Bank stays at 63 (capped) |

### Usage Order (Consumption Priority)

When a Pro user runs a SETTLE report, consumption order is:

1. **Monthly included allocation** (15 reports) — used first
2. **Rollover bank** — used second
3. **Paid overage** ($25/report) — used last

Example: User has 10 rollover reports and runs 20 reports in a month:
- 15 from monthly allocation, depleted
- 5 from rollover bank, bank now 5
- No overage charged

### Rollover Bank Reset Rules

| Event | Rollover Bank Behavior |
|-------|----------------------|
| Subscription anniversary (12 months) | Resets to 0 |
| Subscription canceled | Balance lost immediately (does not carry over) |
| Subscription reactivated after cancellation | Starts fresh at 0 |
| Subscription paused | Balance frozen during pause; resumes on reactivation |

### Why This Is Better

**Easier to explain:**
> "Unused reports roll over during your subscription year, capped at 63. The rollover bank resets annually."

**Versus the rejected alternative:**
> "Each report expires 12 months after the month it was issued."

The rejected version is technically fair but creates:
- Per-report tracking overhead
- Support tickets about which reports expired when
- UI complexity showing per-report expiration dates
- Confusion during high-usage months

### Final Full Pro Wording

> **SETTLE Pro — $299/month**
>
> Includes 15 reports/month. Unused included reports roll into your Pro rollover bank while your subscription remains active, capped at 63 reports. Rollover reports are used before paid overage reports. Your rollover bank resets to zero at each annual subscription anniversary and does not carry over after cancellation. Additional reports beyond your monthly allocation and rollover balance are $25 each.

### Updated Pricing Table (with Rollover)

| User Type | SETTLE Pricing | Rollover |
|-----------|---------------|----------|
| Standalone | $39/report | None |
| INTAKE + LEVERAGE ecosystem | $29/report | None |
| SETTLE PRO | $299/month, 15 included, $25 extra | Rolling annual bank, capped at 63 |
| New INTAKE user onboarding | 3 complimentary reports (one-time) | None |

### Implementation Notes

- The rollover bank display in the UI should be simple: a single number (e.g., "Rollover: 47 reports")
- On subscription anniversary, show a brief notice: "Your rollover bank has reset for your new subscription year."
- Do NOT display per-report expiration dates or issuance months — that defeats the purpose of the simplified model
- The 63-report cap was chosen as roughly 4 months of full unused allocation, preventing indefinite hoarding while giving meaningful buffer

---

*This document is designed to be appended to. When new context emerges, add sections below this line.*


---

## 52. ECOSYSTEM BILLING REFINEMENT: NO BUNDLES, MONTHLY ARREARS

### Principle

Ecosystem users (INTAKE + LEVERAGE firms) are already paying TrueVow. Making them pre-buy bundles adds friction for no benefit. They should feel SETTLE is part of their workflow, not a separate credit store to manage.

### The Rule

> **Ecosystem users pay $29/report, billed monthly in arrears. No bundles. No prepayment.**

### Why Monthly Invoice Is Better for Ecosystem Users

Ecosystem users should feel:
> "SETTLE is just part of my TrueVow workflow."

Not:
> "Now I need to manage credits."

For ecosystem users:
- They run reports whenever needed
- Reports are tracked
- Usage is added to their monthly invoice
- Rate is always $29/report
- No prepayment required

This is better UX and better expansion revenue — lower friction means more usage.

### Important Constraint

Do **not** let ecosystem users stack bundle discounts. Avoid:
> ecosystem rate + 25-pack = effective rate lower than $29/report

That creates a pricing mess. Ecosystem rate is flat $29/report. No stacking.

---

## 53. FINAL SETTLE BILLING LADDER

| User type               | Billing model         | Price                          |
| ----------------------- | --------------------- | ------------------------------ |
| Standalone casual       | Pay per report        | $39/report                     |
| Standalone repeat       | 11-pack (prepaid)     | $385 ($35/report)              |
| Standalone spike volume | 25-pack (prepaid)     | $750 ($30/report)              |
| Ecosystem user          | Monthly usage invoice | $29/report (billed in arrears) |
| SETTLE Pro              | Subscription          | $299/mo, 15 included, $25 extra|

### Bundle Math (Standalone Only)

| Pack  | Price | Per Report | Savings vs $39 |
|-------|-------|-----------|-----------------|
| Single | $39  | $39.00    | —          |
| 11-pack | $385 | $35.00    | ~10%            |
| 25-pack | $750 | $30.00    | ~23%            |

Bundles are prepaid. Unused reports do not expire. No rollover bank — bundles are simple prepaid credits for standalone users.

---

## 54. FINAL ECOSYSTEM WORDING

> **TrueVow Ecosystem Rate**
>
> Firms using INTAKE + LEVERAGE get SETTLE reports at **$29/report**, automatically added to the monthly invoice. No bundles, credits, or prepayment required.

---

## 55. SHOULD ECOSYSTEM USERS GET PRO?

Yes, but only if they are high usage.

For ecosystem users:
- Regular ecosystem rate: **$29/report** (monthly arrears)
- Pro: **$299/month, 15 included, $25 extra**

Break-even at 11 reports/month:
- Ecosystem usage = 11 x $29 = $319
- Pro = $299

So Pro becomes logical at **11+ reports/month** for ecosystem users.

### Final Pro Upsell Line

> Reviewing 11+ cases per month? SETTLE Pro usually makes more sense.

---

## 56. CORRECTED PRICING TABLE (FINAL)

This supersedes the pricing table in Section 50.

| User Type | Billing Model | Price | Rollover |
|-----------|--------------|-------|----------|
| Standalone casual | Pay per report | $39/report | None |
| Standalone repeat | 11-pack (prepaid) | $385 | None (credits don't expire) |
| Standalone spike | 25-pack (prepaid) | $750 | None (credits don't expire) |
| Ecosystem user | Monthly invoice (arrears) | $29/report | None |
| SETTLE Pro | Subscription | $299/mo, 15 included, $25 extra | Rolling annual bank, capped at 63 |
| New INTAKE onboarding | Complimentary | 3 reports (one-time) | None |
| Founding Member | Legacy | Free forever | None |

### Explicitly Reaffirmed (Do Not Resurrect)

- Ecosystem users do NOT get bundles
- Bundles do NOT stack with ecosystem rate
- Ecosystem rate is always $29/report — no volume discount beyond that
- Ecosystem billing is monthly arrears, not prepaid

---

## 57. SUMMARY: THREE BILLING PATHS

```
STANDALONE                    ECOSYSTEM                     PRO
$39 single                    $29/report                    $299/month
11-pack $385                  billed monthly                15 included
25-pack $750                  no prepayment                 $25 overage
prepaid credits               auto-invoiced                 rollover bank
```

Three clean paths. No confusion. No credit-store complexity.

---

*This document is designed to be appended to. When new context emerges, add sections below this line.*
