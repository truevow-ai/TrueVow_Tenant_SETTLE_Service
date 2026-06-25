# DEPRECATED — `scripts/data-collection/`

**Status: deprecated (pre-factory). Do not use these scripts to populate the verdict database.**

Everything in this directory predates the current scraping architecture (it was last
touched 2026-03, before the `settle_data_scraping_factory/` build-out). Each script here
carries its **own bespoke, un-hardened classifier** for PI relevance / injuries / dollar
amounts. Those home-grown classifiers:

- have **no shared false-positive guard** (e.g. they would treat criminal-statute
  "bodily injury" language or enforcement charge labels like "negligence" as personal
  injury, and grab the first `$` in an article as the verdict amount);
- do **not abstain** when unsure and do **not carry a source snippet / provenance**;
- duplicate logic that now lives in one place.

## Use the factory instead

`settle_data_scraping_factory/` is the supported pipeline:

- **`_common/extract.py`** — the single, deterministic PI-relevance + outcome/injury/amount
  extractor (zero-fabrication; criminal/enforcement precision guard; every amount carries
  the exact source snippet).
- **`_common/fetcher.py`** — polite L0 HTTP with retries, caching, and built-in provenance
  (url + sha256 + fetched_at).
- **Source adapters** (`court_dockets_records/cds_*.py`: CAP, CourtListener, MoreLaw, FJC
  IDB, news enrichment) yield normalized records that flow through
  `cds_cap_pipeline.build_candidate` → validate / score / dedup / route → `cds_cap_loader`
  into the admin **review queue** (nothing is auto-published).

Each adapter has a `--selftest`. Add new sources as `cds_*` adapters, never as standalone
scripts with their own classifier.

## If you need something here

Port the useful bits (casemine, legal-blogs, settlement-news) into a new `cds_*` factory
adapter so they inherit the shared extractor and provenance. Do not extend these files.
They may be removed in a future cleanup.
