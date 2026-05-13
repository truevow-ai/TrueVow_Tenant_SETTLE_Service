# SETTLE Database Migrations

This folder holds **additive** SQL migrations applied on top of the canonical schema (`database/schemas/settle_supabase.sql`).

Each migration is idempotent (`CREATE IF NOT EXISTS`, `DROP POLICY IF EXISTS`, etc.) so re-running is safe.

---

## Application order

Apply these to `settle-production` Supabase via SQL Editor → New query → paste → Run, in this order:

| # | File | Adds | Created |
|---|------|------|---------|
| 0 | `../schemas/settle_supabase.sql` | The base 6 tables (settle_contributions, settle_api_keys, settle_founding_members, settle_queries, settle_reports, settle_waitlist) | 2025-12-07 |
| 1 | `add_waitlist_table.sql` | Reapplies/normalizes settle_waitlist (kept for historical traceability — the canonical schema already creates it) | 2025-12-24 |
| 2 | `add_case_provenance_table.sql` | settle_case_provenance — private, RLS-locked, identifying-fields table; FK 1:1 to settle_contributions | 2026-05-08 |
| 3 | `add_source_documents_table.sql` | settle_source_documents — private, RLS-locked, source-of-record table; FK 1:N to settle_case_provenance; FTS-indexed | 2026-05-08 |

⚠️ **Migrations 2 and 3 must be applied in that order** — migration 3 has a foreign key that references the table created in migration 2.

---

## What each new migration adds (Phase 2.1)

### `add_case_provenance_table.sql`

Creates `settle_case_provenance` to hold case identifying fields (case_name, case_citation, judge_name, docket_number, plaintiff/defense firms, source URLs) that are deliberately stripped from `settle_contributions`. RLS-locked to `service_role` only.

Plus:
- Helper function `settle_audit_lookup_provenance(contribution_id, accessor)` — logs every audit access into `last_audit_access` / `last_audit_accessor`.

### `add_source_documents_table.sql`

Creates `settle_source_documents` to hold the literal scraped source documents (HTML/PDF) that justify each verdict, with SHA-256 chain of custody and FTS-indexed extracted text. RLS-locked to `service_role` only. Raw bytes live in Supabase Storage bucket `settle-source-archive`; only the storage path is in the DB row.

Plus:
- Helper function `settle_audit_lookup_source_document(doc_id, accessor)` — audit lookup with logging
- Helper function `settle_search_source_documents(query, limit)` — full-text search across the corpus
- TSVECTOR auto-update trigger on `extracted_text`

---

## Three-table architecture summary

```
settle_contributions     settle_case_provenance     settle_source_documents
(PUBLIC, anonymized)  ←→ (PRIVATE, identifying)  →  (PRIVATE, source bytes)
                      FK 1:1                      FK 1:N
```

- SETTLE attorney reports query `settle_contributions` ONLY
- `authenticated` and `anon` Supabase roles have ZERO privileges on the two private tables
- Audit reads always go through helper functions that log access

For the full architecture diagram and access-policy walkthrough, see `scripts/data-collection/cds_court_docket_scraping/COURT_DOCKET_SCRAPING_README.md`.

---

## Verifying after apply

After applying migrations 2 and 3, run this in SQL Editor to confirm structural integrity:

```sql
-- Tables exist and RLS is enabled on the private ones
SELECT
    relname AS table_name,
    relrowsecurity AS rls_enabled,
    (SELECT COUNT(*) FROM pg_policies WHERE tablename = relname) AS policy_count
FROM pg_class
WHERE relname IN (
    'settle_contributions',
    'settle_case_provenance',
    'settle_source_documents'
)
ORDER BY relname;
```

Expected: 3 rows. The two private tables (`settle_case_provenance`, `settle_source_documents`) show `rls_enabled = true` with `policy_count = 1`. `settle_contributions` may show `rls_enabled = false` (intentional — it's public-readable when `status='approved'`).

```sql
-- Helper functions exist
SELECT proname FROM pg_proc
WHERE proname IN (
    'settle_audit_lookup_provenance',
    'settle_audit_lookup_source_document',
    'settle_search_source_documents'
)
ORDER BY proname;
```

Expected: 3 rows.

If either query returns fewer rows than expected, the corresponding migration didn't fully apply. Re-run that migration's SQL file.

---

## After migrations are applied

The pipeline that populates these tables is in `scripts/data-collection/cds_court_docket_scraping/`. Specifically:

- `cds_settle_ingest.py` — atomic dual-table writer (settle_contributions + settle_case_provenance, single transaction)
- `cds_archive_source.py` — separate pass that fetches source URLs, extracts clean text, hashes raw bytes, uploads to the `settle-source-archive` storage bucket, inserts metadata into `settle_source_documents`

See those folders' `COURT_DOCKET_SCRAPING_README.md` and `YASHAS_RUNBOOK.md` for the operational walkthrough.

---

**Maintained by:** Hyperagent (lead developer for SETTLE data layer)
**Last updated:** 2026-05-08
