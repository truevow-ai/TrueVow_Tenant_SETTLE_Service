# ARCHIVED — ungated pre-factory data-collection (2026-07-11)

**Status: archived, DISABLED, preserved for possible re-verification. Do NOT run. Do NOT re-seed from these.**

## Why these are here
Every script in this folder predates the no-fabrication factory. They carry
their own un-hardened classifiers (grab the first `$` as the verdict amount,
treat criminal-statute "bodily injury" as personal injury, no abstention, no
per-field source snippet) and — critically — the `seed-*` scripts insert
straight into the database **bypassing both no-fabrication gates**:

    scrape-*.py / collect-*.py / extract-*.py
        -> prepare-for-seeding.py
        -> seed-via-supabase-client.py / seed-*.py
        -> settle_contributions   (NO GATE, NO PROVENANCE)

That pipe is what seeded the 469 ungated 2026-05-11 `settle_contributions`
rows (0 user_id / 0 blockchain_hash / 0 source_url) that were later quarantined.

Under AGENTS.md RULE 0 (no fabrication, ever), these cannot feed the DB.

## Preserved, not destroyed
Per RULE 0, rejected/quarantined material is preserved so it can be
re-verified against its sources later and recovered IF it legitimately passes
the gate. The scraped JSON + debug HTML are kept alongside the scripts here.

## The ONLY supported way to add data
`settle_data_scraping_factory/` — a gated `cds_*` adapter yields raw
`opinion_text` + `source_url` + `sha256`, and the shared, gated extractor does
all field extraction:

    cds_*  ->  _common/extract  ->  no_fabrication_gate.verify_record
           ->  verdict_validator.normalize_and_validate  ->  loader  ->  DB

To (re)add Casemine or legal-blogs, write a `cds_casemine` / `cds_legalblogs`
factory adapter. Never re-enable anything in this archive.

## Each script still has a hard kill-switch
`_killswitch.py` here makes every guarded script exit(2) if run. The kill-switch
is intentional and must not be removed.
