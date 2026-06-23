# Data Acquisition Strategy — Florida & California (v2 — Post Web Research)

**Date:** 2026-06-23 (updated with fresh web research)
**Target:** FL: grow from 440 → 1,500+ approved rows. CA: grow from 0 → 1,000+ rows.
**Budget:** ~$5-10 total (ExaSearch tokens only). All sources are free.
**Timeline:** 6-8 weeks of intermittent scraping

---

## Current State

| State | Approved Rows | Max County n | Target |
|---|---|---|---|
| Florida | 440 | 3 | 1,500+ rows |
| California | 0 | 0 | 1,000+ rows |

---

## Complete Source Inventory (Ranked by Yield/Effort)

### Tier 1 — Highest Yield, Already Built (Week 1-2)

| # | Source | Scraper | FL Yield | CA Yield | Cost | Notes |
|---|---|---|---|---|---|---|
| 1a | **CourtListener API v4** — `/fjc-integrated-database/` endpoint | `cds_courtlistener.py` (recovered) | 200-400 | 300-700 | $0 | Direct FJC IDB access via API. No bulk CSV download needed. Free account: 5K requests/hr. Query by nature_of_suit (PI codes: 360-368) + state. |
| 1b | **CourtListener API v4** — `/search/` + `/opinions/` | Same scraper | 100-200 | 200-300 | $0 | Full-text search for "settlement" + "personal injury" + state. Opinion clusters link related cases. |
| 1c | **RECAP Archive** (Free Law Project) | New: query via CourtListener API | 100-200 | 150-300 | $0 | Tens of millions of federal docket documents. Searchable PDFs. Also available as bulk data from Internet Archive. |
| 1d | **TopVerdict.com** — retry failures | Existing extraction scripts | 100-150 | 100-200 | $0 | 200 FL failures + 37 ForThePeople failures from Phase 3.5. Use Playwright for headless browser retry. |

**Tier 1 subtotal: FL ~500-950, CA ~750-1,500**

### Tier 2 — High Yield, New Scrapers Needed (Week 3-4)

| # | Source | Type | FL Yield | CA Yield | Cost | Notes |
|---|---|---|---|---|---|---|
| 2a | **JuryVerdictAlert.com** | CA verdict database | 0 | 200-400 | $0 (public previews) | Public preview pages contain: case name, county, amount ($), injury type, medical bills, insurance carrier, demands/offers, expert witnesses. Scrape public listings — no subscription needed for preview data. |
| 2b | **MoreLaw.com** | National verdict search | 100-200 | 100-200 | $0 | Free searchable database. Filter by State=Florida or California. Fields: case style, judge, court, attorneys, verdict type. Advanced search by subject (personal injury). |
| 2c | **ExaSearch** — discovery queries | News/press articles | 100-200 | 100-200 | ~$3-5 | Query pattern: "[County] County [State] [year] verdict personal injury settlement". Already used in Phase 3.5 (310/439 narratives enriched). Expand to new FL counties + all CA counties. |
| 2d | **FJC IDB bulk CSV** | Federal civil cases | 50-100 | 100-200 | $0 | Backup path if API rate-limited. Bulk download from fjc.gov. Already have `cds_fjc_idb.py` scraper recovered. |

**Tier 2 subtotal: FL ~250-500, CA ~500-1,000**

### Tier 3 — Plaintiff Firm Websites (Week 5-6)

Published settlement results as marketing. Semi-automated scraping of results/case-results pages.

**Florida firms:**
| # | Firm | URL | Expected Yield |
|---|---|---|---|
| 3a | Pajcic & Pajcic (Jacksonville) | pajcic.com/results | 30-50 |
| 3b | Florin Roebig (Tampa) | florinroebig.com/results | 30-50 |
| 3c | Searcy Denney (West Palm Beach) | searcylaw.com | 20-40 |
| 3d | Paul Knopf Bigger (South FL) | paulknopfbigger.com | 20-30 |
| 3e | Morgan & Morgan (statewide) | forthepeople.com/case-results | 40-60 |

**California firms:**
| # | Firm | URL | Expected Yield |
|---|---|---|---|
| 3f | Bisnar Chase (Newport Beach) | bisnarchase.com/case-results | 30-50 |
| 3g | The Barnes Firm (San Diego/LA) | thebarnesfirm.com/results | 20-40 |
| 3h | Arash Law (statewide) | arashlaw.com/results | 30-50 |
| 3i | JT Legal Group (LA) | jtlegalgroup.com/case-results | 20-30 |
| 3j | Bisnar | Chase (multi-office) | Already counted above |

**Tier 3 subtotal: FL ~140-230, CA ~100-170**

### Tier 4 — News & Press Enrichment (Week 6-7)

| # | Source | Type | FL Yield | CA Yield | Cost |
|---|---|---|---|---|---|
| 4a | **News enrichment** (existing `cds_enrich_via_news.py`) | Adds narratives to existing rows | enrichment | enrichment | ~$2-3 |
| 4b | **Google Scholar** — legal publications | Academic papers with verdict datasets | context only | context only | $0 |
| 4c | **PR Newswire / BusinessWire** | Large verdict press releases | 10-20 | 15-30 | $0 |
| 4d | **Legal blog aggregation** | `scrape-legal-blogs.py` (existing) | 20-30 | 20-30 | $0 |

**Tier 4 subtotal: FL ~30-50, CA ~35-60 (plus enrichment of all rows)**

### Tier 5 — State Court Portals (Week 7-8, if needed)

| # | County | Population | Portal | Effort | Expected Yield |
|---|---|---|---|---|---|
| 5a | Miami-Dade, FL | 2.7M | mycase.miami-dadeclerk.com | High (ASP.NET) | 50-100 |
| 5b | Broward, FL | 1.9M | courthouse.broward.org | Medium | 40-80 |
| 5c | Palm Beach, FL | 1.5M | myclerk.co.palm-beach.fl.us | Medium | 30-60 |
| 5d | Hillsborough, FL | 1.5M | hillsclerk.com | Medium | 30-50 |
| 5e | Orange, FL | 1.4M | myeclerk.myorangeclerk.com | Medium | 30-50 |
| 5f | Los Angeles, CA | 10M | lacourt.org | High | 100-200 |
| 5g | San Diego, CA | 3.3M | sdcourt.ca.gov | Medium | 40-80 |
| 5h | Orange County, CA | 3.2M | occourts.org | Medium | 30-60 |

**Tier 5 subtotal: FL ~180-340, CA ~170-340**

---

## Revised Projected Totals

| State | Current | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Tier 5 | **Total** |
|---|---|---|---|---|---|---|---|
| Florida | 440 | +725 | +375 | +185 | +40 | +260 | **~2,025** |
| California | 0 | +1,125 | +750 | +135 | +48 | +255 | **~2,313** |

**FL target (1,500): achievable by end of Tier 2 (Week 4).**
**CA target (1,000): achievable by end of Tier 1 (Week 2).**

Total cost: **~$5-10** (ExaSearch tokens only).

---

## Execution Priority

### Phase A: CourtListener + FJC (highest ROI, Week 1-2)
1. Run CourtListener API queries for FL + CA PI cases (nature_of_suit 360-368)
2. Run FJC IDB API queries for FL + CA federal civil cases
3. Process through contribution pipeline (anonymizer, classifier, quality scoring)
4. **Expected: 500-950 FL + 750-1,500 CA**

### Phase B: Retry Failures + JuryVerdictAlert (Week 2-3)
1. Retry 237 TopVerdict/ForThePeople failures with Playwright
2. Scrape JuryVerdictAlert.com public previews for CA data
3. Run MoreLaw.com searches for FL + CA
4. **Expected: 250-500 FL + 500-1,000 CA**

### Phase C: Firm Websites + ExaSearch (Week 4-5)
1. Scrape 10 plaintiff firm result pages
2. ExaSearch discovery for rural FL counties + CA counties
3. News enrichment for all new rows
4. **Expected: 170-280 FL + 135-230 CA**

### Phase D: Court Portals (Week 6-8, only if needed)
1. Build scrapers for top FL/CA county court portals
2. Only if Tier 1-3 haven't hit targets
3. **Expected: 180-340 FL + 170-340 CA**

---

## Key Technical Notes

- **CourtListener FJC IDB API:** `GET /api/rest/v4/fjc-integrated-database/?nature_of_suit__in=360,362,365,367,368&district__state=FL&date_filed__gte=2020-01-01`
- **Rate limits:** Unauthenticated 100/hr, free account 5,000/hr. Register at courtlistener.com for free.
- **JuryVerdictAlert.com scraping:** Public verdict previews show insurer, amounts, demands/offers. Extract these fields; don't scrape subscription-only content.
- **Data quality pipeline:** All rows go through anonymizer → injury classifier (17-tag) → anomaly detector → reputation scoring → admin review queue.
- **ExaSearch cost:** ~$0.01/query. Budget 300-500 queries per batch = $3-5 per run.
- **No PII:** All scraping extracts anonymized aggregate data only. Case names used for dedup but not stored in settle_contributions.

---

## New Discovery: CourtListener Has Everything

The web research revealed that **CourtListener API v4 is significantly more capable than previously assumed:**

1. **FJC IDB endpoint** — Direct programmatic access to the entire FJC Integrated Database. Previously we planned to download bulk CSVs.
2. **Full-text search** — Search for "settlement" within FL/CA federal opinions
3. **RECAP Archive** — Free mirror of PACER content, tens of millions of documents
4. **Parties + Attorneys** — Can identify defendant types (insurance companies) and plaintiff firms
5. **Docket alerts** — Can set up automated monitoring for new FL/CA PI settlements

**Recommendation:** Make CourtListener the primary data source. A single well-constructed API integration could yield 1,000-2,000+ cases across FL+CA with zero cost.
