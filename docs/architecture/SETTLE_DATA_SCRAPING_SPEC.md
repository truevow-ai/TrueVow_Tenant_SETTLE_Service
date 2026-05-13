# SETTLE Intelligence Agent — Data Scraping Specification

**Version:** 1.0
**Date:** 2026-04-27
**Status:** Draft — for review
**Purpose:** Define what external data SETTLE must acquire to give plaintiff attorneys asymmetric leverage in settlement negotiations.

---

## Why This Matters

Insurance carriers already have Colossus — a proprietary claims evaluation system that gives adjusters data-backed settlement ranges. Plaintiff attorneys walk into negotiations blind, armed only with anecdotal experience.

SETTLE is the plaintiff-side countermeasure. But it needs data. Lots of it.

The founding partner program (Year 1) generates structured settlement submissions from participating firms. That's the seed. But to accelerate value, SETTLE also needs to scrape publicly available data that insurers already use — and data they don't want attorneys to have.

---

## Data Categories — What to Scrape and Why

### 1. Jury Verdict & Settlement Data

**What it is:** Public records of jury verdicts, arbitration awards, and reported settlements by jurisdiction, injury type, and court.

**Why it matters:** This is the raw material. An attorney walking into a mediation for a cervical fusion case in Harris County, Texas needs to know: what did the last 50 similar cases actually settle for?

**Sources:**
- County court dockets (public record portals — e.g., Odyssey, Tyler Technologies)
- State court administrative offices (many publish annual caseload reports)
- Federal PACER (civil jury verdicts by district)
- Legal publisher verdict reporters (JVR, Westlaw Jury Verdicts — subscription but scrapable)
- State bar association settlement surveys
- AAJ (American Association for Justice) litigation packets

**Fields to capture:**

| Field | Type | Example |
|-------|------|---------|
| `jurisdiction` | string | "FL-Hillsborough" |
| `court_level` | enum | circuit, federal_district, appellate |
| `case_type` | enum | motor_vehicle, medical_malpractice, premises, product_liability, wrongful_death |
| `injury_category` | string | "cervical_spine", "tbi_mild", "shoulder_rotator_cuff" |
| `injury_severity` | enum | soft_tissue, fracture, surgical, catastrophic, fatal |
| `medical_specials` | integer | 52350 (past medical bills in dollars) |
| `lost_wages` | integer | 18400 |
| `verdict_amount` | integer | 275000 |
| `settlement_amount` | integer | 185000 (if reported) |
| `comparative_negligence_pct` | integer | 20 (if plaintiff found partially at fault) |
| `trial_duration_days` | integer | 4 |
| `jury_composition` | string | "5F_1M" (if available) |
| `defense_firm` | string | "Smith & Wesson Defense Group" |
| `defense_attorney` | string | "John Defense, Esq." |
| `plaintiff_firm` | string | (for benchmarking peers) |
| `insurance_carrier` | string | "State Farm", "Geico", "Progressive" |
| `policy_limit_known` | boolean | true |
| `policy_limit_amount` | integer | 250000 (if discoverable) |
| `date_of_verdict` | date | 2025-03-15 |
| `appeal_filed` | boolean | false |
| `appeal_outcome` | string | null |
| `case_citation` | string | "Smith v. Jones, 2025 WL 123456" |
| `docket_number` | string | "2023-CA-004567" |
| `judge_name` | string | "Hon. Patricia Bench" |

**Scraping difficulty:** High. Court docket systems are fragmented, inconsistently formatted, and often have CAPTCHA or paywalls. This is the hardest category — but also the highest value.

**Strategy:** Start with the 3-5 highest-volume injury jurisdictions (FL, TX, CA, NY, IL). Scrape what's free first. Budget for PACER API access ($0.10/page, capped at $3/document).

---

### 2. Insurance Carrier Behavior Data

**What it is:** Patterns in how specific insurance carriers handle claims — their settlement tendencies, trial rates, average initial offers, and lowball tactics by adjuster.

**Why it matters:** If SETTLE can tell an attorney "State Farm's median initial offer on cervical fusions in Florida is 62% below final settlement," that's a negotiation weapon. The attorney knows not to flinch at the first number.

**Sources:**
- NAIC (National Association of Insurance Commissioners) market conduct reports
- State insurance department complaint databases (public records)
- Annual statement filings (Schedule P — loss development data)
- SEC filings (for publicly traded carriers — claims reserve disclosures)
- Consumer complaint databases (state DOI websites)
- J.D. Power claims satisfaction studies (summary data is public)
- Bad faith lawsuit records (court dockets — searchable by carrier as defendant)

**Fields to capture:**

| Field | Type | Example |
|-------|------|---------|
| `carrier_name` | string | "State Farm Mutual" |
| `carrier_NAIC_code` | string | "25178" |
| `jurisdiction` | string | "CA-Los Angeles" |
| `claim_type` | enum | auto_bodily_injury, homeowners_liability, commercial_auto |
| `avg_days_to_first_offer` | integer | 45 |
| `avg_initial_offer_pct_of_final` | float | 0.62 |
| `trial_rate_pct` | float | 0.03 (3% of BI claims go to trial) |
| `mediation_settlement_rate` | float | 0.88 |
| `avg_settlement_amount` | integer | 18500 |
| `complaints_per_1000_claims` | float | 2.3 |
| `bad_faith_judgments_last_5yr` | integer | 4 |
| `market_share_in_state` | float | 0.18 (18% of state auto insurance market) |
| `financial_strength_rating` | string | "A++" |
| `year` | integer | 2025 |

**Scraping difficulty:** Medium. NAIC and state DOI data is public but buried in PDF reports. SEC filings require EDGAR parsing. The real value is in combining carrier data with verdict data to spot patterns.

---

### 3. Medical Cost Benchmarks

**What it is:** Typical medical treatment costs by injury type, procedure, and geographic region — both charged amounts and actual paid amounts.

**Why it matters:** Medical specials are the anchor of most injury claims. If an attorney knows the fair-market cost of a lumbar laminectomy in Phoenix, they can challenge inflated lien claims and defend reasonable medical expenses.

**Sources:**
- CMS (Centers for Medicare & Medicaid Services) physician fee schedules
- CMS hospital chargemaster data (now public under price transparency rules)
- FAIR Health consumer cost lookup (aggregated claims data)
- Workers' compensation fee schedules (state-specific, all public)
- State hospital associations (many publish cost reports)
- Healthcare Bluebook (commercial, but summary data accessible)

**Fields to capture:**

| Field | Type | Example |
|-------|------|---------|
| `procedure_code` | string | "CPT-63030" |
| `procedure_description` | string | "Lumbar laminectomy" |
| `region` | string | "AZ-Maricopa" |
| `medicare_allowed_amount` | integer | 1890 |
| `median_charged_amount` | integer | 12000 |
| `median_paid_amount` | integer | 3200 |
| `workers_comp_fee_schedule` | integer | 2450 |
| `typical_pt_visits` | integer | 12 |
| `typical_chiro_visits` | integer | 24 |
| `source_year` | integer | 2025 |

**Scraping difficulty:** Medium. CMS data is freely available via API and bulk download. Workers' comp fee schedules are published as PDFs or simple HTML tables by each state. Hospital chargemaster data is messy (every hospital formats differently) but increasingly available as machine-readable JSON.

---

### 4. Judicial & Venue Analytics

**What it is:** Data about specific judges and venues — their trial tendencies, median awards, summary judgment rates, and demographic profiles of jury pools.

**Why it matters:** An attorney choosing between filing in state court vs. federal court, or deciding whether to accept a judge's settlement recommendation, needs data. "Judge Henderson's median jury award in PI cases is 28% above the county median" changes strategy.

**Sources:**
- Judicial performance evaluation reports (many states publish these)
- Court annual reports (filing statistics by judge and division)
- PACER (federal civil case outcomes by judge)
- State judicial election/vetting materials (biographies, endorsements)
- Jury pool demographic data (census-tract-based jury commission reports)
- Ballotpedia / judicial election results
- State bar judicial evaluation surveys

**Fields to capture:**

| Field | Type | Example |
|-------|------|---------|
| `judge_name` | string | "Hon. Maria Gonzalez" |
| `court` | string | "Miami-Dade Circuit Court" |
| `division` | string | "Civil Division" |
| `years_on_bench` | integer | 14 |
| `prior_practice_area` | string | "plaintiff_personal_injury" or "insurance_defense" |
| `civil_jury_trial_count_annual` | integer | 18 |
| `median_jury_award` | integer | 215000 |
| `plaintiff_verdict_rate` | float | 0.62 |
| `summary_judgment_grant_rate_defense` | float | 0.14 |
| `avg_days_to_trial_from_filing` | integer | 420 |
| `settlement_conference_settlement_rate` | float | 0.72 |
| `jury_pool_median_income` | integer | 58000 |
| `jury_pool_college_pct` | float | 0.34 |
| `jury_pool_political_lean` | string | "lean_conservative" (based on precinct data) |
| `venue_jdx` | string | "TX-Harris" |

**Scraping difficulty:** Medium-High. Public but fragmented. Judicial evaluation reports exist for ~35 states. Federal judge data is accessible via PACER and FJC (Federal Judicial Center) Biographical Directory. Jury pool demographics require creative cross-referencing of census data with jury commission boundaries.

---

### 5. Statutory & Regulatory Framework

**What it is:** State-specific laws that directly affect settlement value — damage caps, collateral source rules, modified comparative negligence thresholds, statute of limitations, lien laws, and UM/UIM requirements.

**Why it matters:** A settlement is not just about medical bills and pain. It's about what the law allows. California's MICRA cap on non-economic damages in med mal cases changes the math completely. An attorney in a pure comparative negligence state vs. a 51% bar state faces different settlement equations.

**Sources:**
- State legislative websites (statutory codes)
- NCSL (National Conference of State Legislatures) policy databases
- State supreme court rules and administrative orders
- State department of insurance regulations
- Legal publisher 50-state surveys (practically oriented summaries)

**Fields to capture:**

| Field | Type | Example |
|-------|------|---------|
| `state` | string | "CA" |
| `rule_name` | string | "non_economic_damages_cap_med_mal" |
| `rule_value` | string | "250000" (MICRA cap — non-economic damages) |
| `rule_type` | enum | damage_cap, collateral_source, comparative_negligence, sol, lien_superpriority, um_uim_required |
| `statute_citation` | string | "Cal. Civ. Code § 3333.2" |
| `effective_date` | date | 1975-01-01 |
| `last_amended` | date | 2022-01-01 |
| `notes` | string | "Does not apply to wrongful death; adjusted for inflation?" |
| `verified_date` | date | 2026-01-15 |

**Scraping difficulty:** Low-Medium. Laws change infrequently. This is mostly one-time research per state with periodic update checks. NCSL does good 50-state surveys. Main challenge is parsing legal text into structured boolean/numeric fields.

---

### 6. Economic & Demographic Data

**What it is:** Wage loss benchmarks, life expectancy tables, discount rates, inflation data, and local economic conditions that affect damages calculations.

**Why it matters:** Lost earning capacity and future medical costs are present-value calculations. An attorney needs defensible numbers: what does a 42-year-old construction worker in Ohio realistically earn over a remaining 25-year work life, discounted to present value? What's the life care plan cost for a T4 paraplegic?

**Sources:**
- BLS (Bureau of Labor Statistics) wage data by occupation and region
- SSA (Social Security Administration) actuarial life tables
- CMS life care planning cost data
- Federal Reserve discount rate (present value calculations)
- Census Bureau American Community Survey (local demographics)
- BEA (Bureau of Economic Analysis) regional price parities

**Fields to capture:**

| Field | Type | Example |
|-------|------|---------|
| `occupation_code` | string | "47-2061" |
| `occupation_title` | string | "Construction Laborer" |
| `region` | string | "OH-Cuyahoga" |
| `median_annual_wage` | integer | 48000 |
| `median_annual_wage_with_benefits` | integer | 62000 |
| `work_life_expectancy_at_age_40` | float | 22.3 |
| `life_expectancy_at_age_40` | float | 39.8 |
| `discount_rate_federal` | float | 0.042 |
| `inflation_rate_cpi` | float | 0.032 |
| `regional_price_parity` | float | 0.91 |
| `source_year` | integer | 2025 |

**Scraping difficulty:** Low. All government-published, all available via API or bulk CSV download. BLS, SSA, and Census have excellent data portals. This is the easiest category to automate.

---

## Scraping Priority Matrix

Not all data is equally valuable or equally hard to get. Here's the prioritized sequence:

| Priority | Data Category | Value to Attorney | Scraping Difficulty | Start When |
|----------|--------------|-------------------|---------------------|------------|
| **P0** | Statutory Framework | High — directly affects settlement math | Low | Immediately |
| **P0** | Economic Benchmarks | High — used in every damages calculation | Low | Immediately |
| **P1** | Medical Cost Benchmarks | High — anchors every injury claim | Medium | Month 1 |
| **P1** | Insurance Carrier Behavior | Very High — negotiation leverage | Medium | Month 2 |
| **P2** | Jury Verdict Data | Very High — the core product | High | Month 2 |
| **P2** | Judicial Analytics | High — venue/judge strategy | Medium-High | Month 3 |

---

## How This Data Integrates with SETTLE

The external scraped data serves three roles in the SETTLE intelligence engine:

1. **Cold start bootstrap.** Before the founding partner settlement database hits 500+ cases per state (the Phase 2 trigger), external data gives attorneys something useful immediately. A dashboard showing "median jury verdict in your county for your injury type" works at n=0 — because the data came from court records, not firm submissions.

2. **Blend and calibrate.** As firm-submitted data grows, SETTLE blends it with external data. Firm data is richer (structured fields, policy limit flags, treatment escalation detail). External data is broader (more cases, more jurisdictions). Together they produce the most credible ranges.

3. **Insurer-side intelligence.** Insurance carrier data — their settlement tendencies, trial rates, adjuster patterns — comes entirely from external scraping. Firms don't submit data about the *other side's* behavior. This is pure scraped intelligence that gives attorneys something insurers wish they didn't have.

---

## Data Quality Guardrails

The intelligence rollout strategy is clear: no fake data, always show sample sizes, never claim prediction. These apply to scraped data too:

- **Source tagging.** Every data point traces back to its origin (court docket, CMS database, NAIC filing). Attorneys can verify.
- **Sample size disclosure.** "Based on 47 reported verdicts in this county (2019-2025)."
- **Staleness flags.** Data older than 5 years carries a warning. Jury verdicts from 2008 are interesting but inflation and legal changes may erode relevance.
- **No PII scraping.** Court dockets contain names, but SETTLE stores only anonymized structured fields. No scraping of attorney-client privileged information. No scraping of sealed records.
- **Confidence bands, not point predictions.** Output is always a range with a confidence level, never a single number. "We estimate this case would settle between $180,000 and $320,000 based on comparable data. This is not a guarantee."

---

## Technical Architecture Notes

### Scraping Infrastructure

Each data source needs its own scraper module — they all have different formats, rate limits, and update cadences:

```
app/
  scrapers/
    court_dockets/         # PACER, Odyssey, Tyler → jury verdict records
    insurance_carriers/    # NAIC, SEC EDGAR, state DOI → carrier behavior
    medical_costs/         # CMS, workers comp fee schedules → cost benchmarks
    judicial/              # PACER analytics, FJC, state reports → judge data
    statutes/              # State legislative websites, NCSL → legal framework
    economic/              # BLS, SSA, Census → wage/life/discount data
```

### Update Cadences

| Data Category | Update Frequency | Why |
|---------------|-----------------|-----|
| Court verdicts | Weekly | New verdicts and settlements reported continuously |
| Insurance carrier data | Quarterly | NAIC filings, SEC quarterly reports |
| Medical costs | Annually | CMS fee schedules update yearly; workers' comp varies |
| Judicial analytics | Quarterly | Cumulative stats change slowly |
| Statutes | Monthly check, actually update on change | Laws change rarely but must be current |
| Economic data | Monthly | BLS releases monthly; SSA tables update annually |

### Storage Principle

All scraped data lives in the SETTLE Supabase database in source-specific tables that mirror the settlement contribution schema. This allows a unified query layer — the attorney doesn't care whether a data point came from a firm submission or a court docket scrape.

---

## Summary

Three things to remember for other coding agents building the scraping pipeline:

1. Priority zero is **statutory and economic data** — it's free, public, easy, and immediately useful in every settlement report.
2. The crown jewel is **jury verdict data by jurisdiction and injury type** — it's the hardest to scrape but the core of the product.
3. **Carrier behavior data** is the asymmetric weapon — insurers don't want plaintiff attorneys to have this, and that's exactly why SETTLE needs it.

Every scraped data point should answer one question for the attorney: **"What should this case actually settle for, and why?"**
