# SETTLE Scraping Factory — Status & Resume Notes

_Last updated: 2026-07-08 (session: enrichment fix + carrier crawler bring-up)_

## Live processes
- **Supervisor** `crawl_supervisor.ps1` (auto-restarts 53 crawlers every 180s). Lock: `out/supervisor.lock`.
- **CourtListener crawler** (`cds_courtlistener_crawl.py`, 11 states, `--min-delay 700`) — RUNNING, resumable via `out/cl_crawl_florida/checkpoint.json`. Rides out throttles (900s backoff) without data loss.

## Court dockets harvest (~21,000 accepted records)
- **CAP fleet (50 states + DC): COMPLETE** — all `COMPLETE` markers present, all `*_accepted_enriched.jsonl` produced.
- **MoreLaw: COMPLETE + enriched** — 569 records across 11 states (deterministic offline enrichment done this session).
- **CourtListener: RUNNING** — ~2,891 accepted so far. NOT enriched yet (see below).

## Enrichment layers
1. **Deterministic** (`_common/enrich.py`, `cds_enrich_offline.py`) — regex/keyword, auditable. Applied to CAP + MoreLaw.
2. **Exa/news** (`cds_enrich_exa.py`, `cds_enrich_via_news.py`) — `EXA_API_KEY` set. Validated (bounded test) on FL CAP (400) + CA CAP (200). Adds carrier/age/medical from news.

### FIXED this session (was silently corrupting data)
- The carrier extractor `_INSURANCE_RE` used greedy `IGNORECASE` `[A-Z]` and captured whole sentence fragments (e.g. "withholds policy benefits in bad faith") as `insurance_carrier`. **86% of carrier values were garbage.**
- Fix: known-carrier registry + strict proper-noun+suffix pattern + `extract_carrier()` / `is_valid_carrier()` / `clean_carrier()` validators.
- `clean_carriers.py` scrubbed all existing enriched files: **3,547 bad values dropped, 208 normalised, 557 valid kept.**

### CL enrichment — DONE 2026-07-09 (offline, cache-only, no crawler contention)
- Enriched a 2,901-record snapshot of CL accepted (`cl_fl_accepted_snapshot_enriched.jsonl`). Opinion text resolved from the shared `_cache/` (51k+ files the crawler already populated) → **zero live API calls**, no contention with the still-running crawler.
- Fixed a SECOND carrier over-matching bug: the known-carrier registry matched ordinary words in opinion prose ("the general rule", "travelers on the highway", "nationwide"). Added ambiguous-carrier context gating (`_carrier_in_context`: an insurance indicator must appear within ±60 chars). Result: **1,142 clean carriers / 2,901 CL records** (State Farm 325, The Hartford 231, Liberty Mutual 225, Travelers, Allstate...).
- Bounded Exa/news pass on 200 CL records → `cl_fl_accepted_snapshot_exa_enriched.jsonl`.
- Note: enriched a SNAPSHOT to avoid racing the live crawler's append. When the crawl finishes, re-run on the final `courtlistener_florida_accepted.jsonl`.

### PENDING
- **MoreLaw Exa enrichment** and **full CAP Exa run** — bounded tests validated; scale up when ready (real API cost).
- Re-enrich final CL file once the crawler completes.

## Insurance Carrier Intelligence — NOW LIVE
- Orchestrator: `insurance_carriers_intelligence/cis_orchestrator.py` (registry of top 10 auto/PI carriers; each source isolated so throttles/failures don't cascade).
- First run: **10 carriers, 76 facts, 0 errors** → `insurance_carriers_intelligence/out/<slug>/{<slug>_facts.jsonl,_manifest.json}`.
- Sources: NAIC complaints (Texas Socrata), SEC EDGAR filings + loss reserves (public carriers), carrier profile. CourtListener bad-faith **skipped** (token in use by docket crawler).
- **FIXED**: `naic_complaints.py` queried the wrong dataset/columns (`naic` on the records table, which has no carrier column) → HTTP 400. Now uses the complaint-index dataset `pa9u-9s9w` (`naic_id`, `year`, `col1/2/3`). Verified real data (State Farm, Allstate, GEICO...).
  ```
  python cis_orchestrator.py --list
  python cis_orchestrator.py --top 10 --skip courtlistener
  python cis_orchestrator.py --all               # after CL crawl finishes, drop --skip
  ```

## DB / loading
- Loader (`batch_load_all.py` → `cds_cap_loader.py`) POSTs to SETTLE API `http://localhost:8002` (`SETTLE_API_URL`). API was DOWN this session, so nothing loaded. Start the API, then `python batch_load_all.py --dry-run` before a live load.
