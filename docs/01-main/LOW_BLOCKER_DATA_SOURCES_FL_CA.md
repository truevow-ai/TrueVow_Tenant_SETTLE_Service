# Low-Blocker / Free Data Source Options — Florida & California (Verified)

**Date:** 2026-06-23
**Status:** Fresh, web-verified research (each source below was checked live on 2026-06-23).
**Goal:** 1,000+ usable Florida rows, 2,000+ usable California rows, on a ~$5–10 budget.
**Companion docs:** `DATA_ACQUISITION_STRATEGY_FL_CA.md`, `SCRAPING_TOOLING_AND_HUMAN_EMULATION.md`, `REMAINING_GAPS.md`.

> **Honesty note:** Yield figures below are *estimates* grounded in what each source actually contains, not guarantees. They are deliberately conservative. All sources were verified reachable on the date above.

---

## 0. Two corrections to the existing strategy doc (important)

1. **CourtListener API is NOT 5,000 requests/hour.** The verified free limit is **5 requests/min, 50/hour, 125/day** (rolling window). At 125 req/day you cannot crawl thousands of cases via the API. → **Use CourtListener BULK DATA (free CSV dumps), not the live API, for volume.** The API is for targeted/recent lookups and enrichment only. (A free Free Law Project membership raises limits somewhat.)
2. The biggest free sources give us **case records (jurisdiction, case type, parties, dates) in huge volume**, but **the settlement/verdict dollar amount is the scarce field** — see §1.

---

## 1. The core problem: dollar amounts are the bottleneck (read this first)

There are two very different things:

- **(A) Case records** — jurisdiction, case type, parties (defendant = insurer/company), filing/disposition dates, nature-of-suit. These are **abundant and free** in bulk.
- **(B) The $ outcome** (settlement or verdict amount) — this is **scarce**:
  - **Settlements are usually confidential** → almost never in court records.
  - **Verdict amounts ARE public**, but they live inside **opinion text** (must be NLP-extracted) or in **verdict reporters / news / firm marketing pages**.

So our pipeline must **combine** high-volume record sources (for coverage, jurisdiction, defendant identity) with dollar-amount sources (verdict reporters, news, firm results, text-mined verdict opinions). Hitting the targets with *usable* rows means rows that have an extractable outcome figure or bucket.

---

## 2. Verified source catalog

Blocker legend (ties to the escalation ladder in `SCRAPING_TOOLING_AND_HUMAN_EMULATION.md`):
**L0** = plain HTTP/bulk download (no emulation) · **L1** = TLS impersonation · **L2** = stealth browser · **L3** = challenge solver.

### Tier A — Free, bulk, ZERO blockers (build on these first)

| # | Source | Access (verified) | Blocker | Has $? | FL est. | CA est. | Notes |
|---|---|---|---|---|---|---|---|
| A1 | **CourtListener BULK DATA** (Free Law Project) | Public-domain CSV dumps on S3 (`com-courtlistener-storage`), regenerated quarterly. Dockets, Opinion Clusters & Opinions, Courts, **FJC IDB merged**. Download via plain HTTPS / `aws s3 --no-sign-request`. | **L0** | In opinion text (verdicts) → NLP | 400–800 | 800–1,500 | The backbone. Millions of dockets/opinions. Filter locally by court (FL/CA state + federal) + PI signals. No rate limit on bulk. |
| A2 | **Caselaw Access Project** — `static.case.law` (Harvard LIL) | Public-domain static files per reporter + metadata JSON. **CA reporters present:** `cal`, `cal-2d…5th`, `cal-app…app-5th`, `cal-rptr-3d`, **`cal-super-ct`** (trial court), `cal-unrep`. **FL:** `fla`, `fla-supp/2d`, **`so/so2d/so3d`** (Southern Reporter). | **L0** | In opinion text → NLP | 600–1,200 | 1,000–2,000 | Huge bulk corpus of published opinions. **Coverage ~through 2020** (digitization cutoff) — pair with A1/A3 for recency. |
| A3 | **CourtListener REST API v4** | Free token. **5/min · 50/hr · 125/day.** FJC IDB endpoint, full-text search, RECAP dockets, parties/attorneys. | **L0** | Metadata; $ via opinion text | enrich | enrich | Use for *recent* (2020→now) PI cases and targeted enrichment, NOT bulk. Respect the tiny daily cap. |
| A4 | **FJC Integrated Database** (fjc.gov/research/idb) | Free SAS / tab-delimited downloads + interactive tool. Federal civil filings/terminations 1970→present, nature-of-suit codes (PI: 340s–360s). | **L0** | Mostly metadata (limited award fields) | 150–400 | 250–600 | Federal PI cases only. Best for jurisdiction/defendant/volume; weak on $ amounts. Already have `cds_fjc_idb.py`. |
| A5 | **Harvard LIL "cold-cases"** (HuggingFace `harvard-lil/cold-cases`) | Free dataset download. | **L0** | In text → NLP | incl. | incl. | Alternative bulk packaging of case law; convenient for ML/NLP pipelines. |
| A6 | **BJS Civil Justice Survey of State Courts (CJSSC)** | Free via ICPSR/NACJD (DOI 10.3886/ICPSR23862). Structured case-level: case type, plaintiff/defendant type, **total damages awarded, punitive damages**, processing time. | **L0** | **YES (clean $)** | calib. | calib. | **Includes the 75 most populous counties → LA County & Miami-Dade.** BUT latest data is **2005 (inactive)**. Use as **historical calibration / methodology baseline**, flagged as stale per our >5yr guardrail — not as current rows. |

### Tier B — Free, low blocker, and they actually carry dollar amounts

| # | Source | Access (verified) | Blocker | Has $? | FL est. | CA est. | Notes |
|---|---|---|---|---|---|---|---|
| B1 | **MoreLaw** (morelaw.com/verdicts) | Free searchable verdict DB (since 1996). Filter by State (FL, CA), field incl. **Verdict Type**, court, judge, attorneys; "Cases by Subject" (personal injury). | **L0→L1** | **YES** | 100–250 | 150–350 | Community verdict reporter. Static HTML, low blocker. Real verdict write-ups with amounts. Moderate volume. |
| B2 | **judyrecords** (judyrecords.com) | **Structured Objects API**: 650M+ cases, 1.2B parties; Full-Text API 750M+. **API-only** (scraping forbidden by ToS). Docs on Postman. | **L0 (API)** | Metadata + parties (limited $) | 200–600 | 400–1,000 | Enormous coverage incl. FL/CA state courts + **party/defendant identity** (great for carrier intel). **OPEN ITEM: pricing not published — must email api@judyrecords.com.** May be paid. |
| B3 | **News / press enrichment** (PR Newswire, BusinessWire, local news) + **ExaSearch** discovery | Free articles; ExaSearch ~$0.01/query. | **L0** | **YES (verdicts/large settlements)** | 150–400 | 200–500 | Big verdicts/settlements are reported in news. Already have `cds_enrich_via_news.py`. Primary paid spend (~$3–5 total). |
| B4 | **Plaintiff-firm "case results" pages** | Free static marketing pages (FL: Pajcic, Florin Roebig, Searcy Denney, Morgan & Morgan; CA: Bisnar Chase, Arash Law, The Barnes Firm). | **L0→L1/L3** | **YES** | 140–230 | 100–200 | Firms publish their settlements/verdicts. Low blocker; a few sit behind Cloudflare (→ L1/L3). |

### Tier C — Real data, but blocked / paid / restricted (use selectively)

| # | Source | Access (verified) | Blocker | Notes |
|---|---|---|---|---|
| C1 | **Fastcase / vLex (Docket Alarm)** | **FREE member benefit of The Florida Bar AND California Lawyers Association** (also L.A. Law Library + CA county bars). Worth ~$995/yr. Includes Docket Alarm verdict/settlement analytics + full case law. | Login-gated; **ToS = human research only** | **Strategic:** if you (or a partner attorney) hold FL Bar / CA Lawyers Assoc membership, this is free premium access for **manual high-value lookups + verification** — NOT bulk scraping. Excellent for spot-checking and hard-to-find amounts. |
| C2 | **Justia Verdicts & Settlements** (verdicts.justia.com) | Free content, but **returned HTTP 403 to our fetcher** → bot-protected. | **L2** | Has structured verdict/settlement entries; needs stealth browser. Medium priority. |
| C3 | **JuryVerdictAlert** (CA) | Public preview cards (case, county, amount, carrier). | **L2** | JS-rendered; previews are public. Good CA $ source via stealth browser. |
| C4 | **State trial-court portals** — Miami-Dade, Broward, LA Superior (lacourt.org), myflcourtaccess.com | Public but **ASP.NET/viewstate, some CAPTCHA; settlement amounts often confidential**; ToS may forbid automation. | **L2/L3 + CAPTCHA** | Highest effort, lowest clean-$ yield. **Defer** unless targets unmet. (See existing `court-records-research.md`.) |
| C5 | **Westlaw / VerdictSearch / LexisNexis** | Paid ($2,500+/yr). | — | Deferred until revenue justifies (per `REMAINING_GAPS.md` A7). |

---

## 3. Realistic path to the targets

**Florida — target 1,000+ (already have 440):**
- A2 CAP (So./Fla. opinion mining) 600–1,200 candidate → ~300–600 with extractable $
- A1 CourtListener bulk (FL state+federal) → +200–500 records, subset with $
- B1 MoreLaw FL +100–250 (clean $) · B3 news +150–400 (clean $) · B4 firm pages +140–230 (clean $)
- → **1,000+ usable rows is achievable from Tier A+B alone** (no high-blocker sources).

**California — target 2,000+ (start 0):**
- A2 CAP (Cal./Cal.App./Cal.Super.Ct. mining) 1,000–2,000 candidate → ~800–1,500 with extractable $
- A1 CourtListener bulk (CA state+federal) → +300–800
- B1 MoreLaw CA +150–350 · B3 news +200–500 · B4 firm pages +100–200 · C3 JuryVerdictAlert +200–400
- → **2,000+ is achievable**, with CAP opinion-mining + CourtListener as the volume engine and MoreLaw/news/JVA supplying clean dollar amounts.

**Cross-cutting requirements**
- An **NLP "outcome extractor"** that pulls award/settlement figures + injury signals from opinion/news text is the single highest-leverage piece of new work. Without it, Tier A volume stays as metadata.
- Every row keeps **source tagging**, runs the existing pipeline (anonymizer → 17-tag injury classifier → anomaly detector → reputation scoring → admin review), and respects the staleness flag (BJS = clearly historical).

---

## 4. Recommended execution order

1. **A1 + A2 bulk download** (CourtListener CSVs + CAP CA/FL reporters). Pure L0, zero blockers, zero cost. Load, filter to FL/CA PI candidates.
2. **Build the outcome/injury NLP extractor** and run it over A1/A2 text → produces structured rows with $ buckets.
3. **B1 MoreLaw + B3 news/ExaSearch + B4 firm pages** for clean dollar amounts (L0/L1). This is where the small ~$5–10 budget goes (ExaSearch).
4. **A3 CourtListener API** for 2020→now recency gaps (mind the 125/day cap).
5. **C1 Fastcase-via-bar** for manual verification of high-value/ambiguous rows.
6. **B2 judyrecords API** — email for pricing; adopt if affordable (great for defendant/party coverage).
7. **C2/C3 (Justia/JVA) via L2 stealth**, then **C4 court portals** — only if targets fall short.

---

## 5. Open items to confirm (not yet verified)

- **judyrecords API pricing** — not published; email `api@judyrecords.com`. Could be the cheapest high-coverage option or could be paid.
- **CAP recency** — confirm exact end-year of FL/CA coverage (believed ~2018–2020).
- **Bar membership** — confirm whether you/a partner hold **The Florida Bar** and/or **California Lawyers Association** membership to unlock free Fastcase/Docket Alarm (C1).
- **FJC IDB award fields** — confirm which civil-IDB years include any monetary judgment field.

---

## 6. Compliance guardrails (unchanged, reinforced)

- Prefer **official APIs / bulk public-domain data** (A1, A2, A4, A6) over scraping.
- **Public / preview data only**; no PII, no sealed records, no privileged content. Case names used only for dedup, never stored.
- Respect **robots.txt / ToS**: judyrecords (API-only), Fastcase (human-use license) — honor these.
- Conservative pacing + checkpointing for any L2/L3 scraping (already implemented in `ANTI_BLOCKING_STRATEGIES.md`).

### 6a. Data integrity — ZERO fabrication (every entry validated & scored)

This is sensitive legal data that attorneys will rely on. **No value may ever be invented, guessed, estimated, hallucinated, or "filled in" by the scraper or any agent.** Every field must come from, and trace back to, an actual source record.

**Hard rules — non-negotiable:**

1. **No made-up numbers.** Settlement/verdict amounts, medical bills, dates, county names, carrier names, etc. must be extracted verbatim (or bucketed) from the source. If a field isn't present in the source, it is `null` — never approximated, never inferred from "similar" cases.
2. **No hallucination.** An NLP/LLM extractor may only return spans that exist in the source text. Every extracted value must carry the **source URL + the exact quoted snippet** it came from, so it is independently verifiable. If the extractor is not confident, it must abstain (return `null`), not guess.
3. **No mismatching.** Fields within a row must come from the **same** case (e.g., the amount, the injury, and the jurisdiction must all belong to that one case). Cross-field consistency checks must pass (e.g., amount currency/scale sane; jurisdiction is a real FL/CA county; date plausible) before acceptance.
4. **No duplicates.** Deduplicate on a stable key (court + docket number, or normalized case-name + county + year + amount) **before** insert. Near-duplicate detection across sources (the same verdict reported by CourtListener *and* a news article *and* a firm page) must merge to one row with multiple source citations — never counted multiple times toward the FL/CA targets.
5. **Provenance is mandatory.** Every row stores: `source`, `source_url`, `extraction_method` (bulk-field | regex | nlp | manual), `extracted_snippet`, and `ingested_at`. A row with no provenance is rejected.

**Each entry is validated AND scored before it counts:**

- **Validation gate** (must pass): required fields present, types/ranges valid, jurisdiction in FL/CA taxonomy, dedup key unique, provenance present → else route to reject/needs-review, not the live pool.
- **Confidence score** (0–1) per row, combining: source reliability (official bulk > verdict reporter > news > firm marketing), extraction method (structured field > deterministic parse > NLP), corroboration (number of independent sources), and field completeness. Low-confidence rows are quarantined for **admin review**, never auto-published.
- This runs through the **existing pipeline** — anonymizer → 17-tag injury classifier → **anomaly detector** → **reputation/confidence scoring** → **admin review queue** — and feeds the same `confidence_score` the estimator already consumes. No row enters the approved pool without passing validation and meeting the confidence threshold.
- **Counting honesty:** only **validated, deduped, scored** rows count toward "1,000+ FL / 2,000+ CA." Candidate/raw counts are reported separately from usable counts.
