# Data Acquisition Strategy — Florida & California

**Date:** 2026-06-23
**Target:** FL: grow from 440 → 1,123+ approved rows. CA: grow from 0 → 500+ rows.
**Budget:** $0 (free sources only, dev-time only)
**Timeline:** 2-3 months of intermittent scraping

---

## Current State

| State | Approved Rows | Max County n | Counties Covered | Target |
|---|---|---|---|---|
| Florida | 440 | 3 | Partial (67 total) | 1,123+ rows, all 67 counties at n>=50 per triple |
| California | 0 | 0 | None (58 total) | 500+ rows, top 10 counties |

**Empirical reality:** Real-county pairs at n>=50 = 0. Max real-county n=3. Pilot mode (n>=10 at state-tier) is the operating model for 6-12+ months.

---

## Available Data Sources (All Free, $0 Cost)

### Tier 1 — Highest Yield, Already Built

| Source | Scraper | Status | Expected FL Yield | Expected CA Yield | Notes |
|---|---|---|---|---|---|
| **CourtListener** | `settle_data_scraping_factory/court_dockets_records/cds_courtlistener.py` | Recovered, ready | 100-200 cases | 150-300 cases | Federal + some state. Free API. RECAP data. |
| **TopVerdict.com** | `scripts/data-collection/extract-*.py` (multiple variants) | Built, ~200 FL failures from Phase 3.5 | 100-150 cases (retry) | 100-200 cases | Settlement/verdict listings. Headless browser needed for failures. |
| **ForThePeople.com** | Scripts in data-collection/ | Built, 37 FL failures | 20-30 cases (retry) | 10-20 cases | FL plaintiff firm website |
| **News Enrichment** | `settle_data_scraping_factory/court_dockets_records/cds_enrich_via_news.py` | Recovered, ready | Enrichment only | Enrichment only | Adds narratives to existing rows via ExaSearch ($2-3 per batch) |

### Tier 2 — Never Tried, Free

| Source | Type | Expected FL Yield | Expected CA Yield | Effort |
|---|---|---|---|---|
| **JuryVerdicts.net** | Verdict/settlement database | 50-100 | 100-200 | New scraper needed (~4 hours) |
| **MoreLaw.com** | Legal news aggregator | 30-50 | 50-100 | New scraper needed (~3 hours) |
| **Jurimatic** | Legal analytics | 20-40 | 30-60 | New scraper needed (~3 hours) |

### Tier 3 — Plaintiff Firm Websites (Manual/Semi-Auto)

**Florida Top 5 PI Firms** (publish settlement wins as marketing):
1. Pajcic & Pajcic (Jacksonville) — pajcic.com/results
2. Florin Roebig (Tampa) — florinroebig.com/results
3. Hilliard Martinez Gonzales (Corpus Christi/FL) — hmglawfirm.com
4. Searcy Denney Scarola Barnhart Shipley (West Palm Beach) — searcylaw.com
5. Paul Knopf Bigger (South FL) — paulknopfbigger.com

**California Top 5 PI Firms:**
1. Bisnar Chase (Newport Beach) — bisnarchase.com/case-results
2. The Barnes Firm (San Diego/LA) — thebarnesfirm.com/results
3. Arash Law (statewide) — arashlaw.com/results
4. JT Legal Group (LA) — jtlegalgroup.com/case-results
5. Baric Law (San Francisco) — bariclaw.com/results

Expected yield: 20-50 cases per firm = 200-500 total across 10 firms.

### Tier 4 — FL Court Portals (Priority Counties)

| County | Population | Portal | Effort |
|---|---|---|---|
| Miami-Dade | 2.7M | mycase.miami-dadeclerk.com | High (ASP.NET, viewstate) |
| Broward | 1.9M | courthouse.broward.org | Medium |
| Palm Beach | 1.5M | myclerk.co.palm-beach.fl.us | Medium |
| Hillsborough | 1.5M | hillsclerk.com | Medium |
| Orange | 1.4M | myeclerk.myorangeclerk.com | Medium |

Expected yield: 50-100 per county if accessible = 250-500 total.

### Tier 5 — FJC Integrated Database (Federal Cases)

| Source | Scraper | Status | Expected Yield |
|---|---|---|---|
| FJC IDB | `settle_data_scraping_factory/court_dockets_records/cds_fjc_idb.py` | Recovered, ready | 200-500 FL federal, 300-700 CA federal |

---

## Execution Plan

### Phase A: Retry Existing Failures (Week 1)
- Retry 200 TopVerdict FL failures with headless browser (Playwright)
- Retry 37 ForThePeople FL failures
- Expected yield: **120-180 new FL rows**
- Cost: $0 (dev time only)

### Phase B: CourtListener + FJC Scraping (Weeks 2-3)
- Run CourtListener scraper for FL + CA
- Run FJC IDB scraper for FL + CA federal cases
- Expected yield: **300-500 FL rows, 450-1000 CA rows**
- Cost: $0 (free API, no key required for basic access)

### Phase C: News Enrichment (Week 3)
- Enrich all new rows with real narratives via ExaSearch
- Expected yield: enrichment only (adds narratives to existing rows)
- Cost: **$3-5** (ExaSearch API)

### Phase D: New Source Scrapers (Weeks 4-6)
- Build JuryVerdicts.net scraper
- Build MoreLaw scraper
- Build Jurimatic scraper
- Expected yield: **100-190 FL rows, 180-360 CA rows**
- Cost: $0 (dev time only)

### Phase E: Plaintiff Firm Websites (Weeks 6-8)
- Semi-automated scraping of 10 firm result pages
- Expected yield: **200-500 cases across FL + CA**
- Cost: $0

### Phase F: FL Court Portals (Weeks 8-12, if needed)
- Build scrapers for top 5 FL county portals
- Expected yield: **250-500 FL rows**
- Cost: $0 (but high dev effort — ASP.NET viewstate flows)

---

## Projected Totals

| State | Current | Phase A | Phase B | Phase C | Phase D | Phase E | Phase F | Total |
|---|---|---|---|---|---|---|---|---|
| Florida | 440 | +150 | +400 | enrichment | +145 | +200 | +375 | **~1,710** |
| California | 0 | +0 | +700 | enrichment | +270 | +250 | N/A | **~1,220** |

**Florida target (1,123): achievable by end of Phase D (Week 6).**
**California target (500): achievable by end of Phase B (Week 3).**

---

## Data Quality Controls

- All scraped data goes through the existing contribution pipeline (anonymizer, validator, anomaly detector)
- Injury classifier (17-tag deterministic) auto-classifies all new rows
- Reputation service assigns trust scores
- Admin review queue for flagged contributions
- `source_url` and `scraped_at` tracked for provenance

---

## Technical Notes

- All scrapers should output data in the `settle_contributions` schema format
- Use `seed-database.py` or `seed-via-supabase-client.py` for bulk ingestion
- The `cds_enrich_via_news.py` script uses ExaSearch for narrative enrichment — only free source that costs money (~$0.01/query)
- CourtListener API has rate limits (unauthenticated: ~100/hour, authenticated: ~5000/hour)
- FJC IDB data is bulk downloadable as CSV from fjc.gov
