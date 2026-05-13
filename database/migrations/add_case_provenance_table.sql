-- ============================================================================
-- Migration: add_case_provenance_table
-- Adds: settle_case_provenance (PRIVATE / AUDIT ONLY)
-- ============================================================================
-- Version: 1.0.0
-- Last Updated: 2026-05-08
-- Status: Phase 2.1 — Three-table defense-in-depth architecture
--
-- Prerequisite: database/schemas/settle_supabase.sql must already be applied
-- (specifically settle_contributions, since this migration adds an FK to it).
--
-- This is additive. It does not modify any existing table.
--
-- Migration order in this folder:
--   1. (already in main schema) settle_contributions, settle_api_keys, etc.
--   2. add_waitlist_table.sql                  (additive, pre-existing)
--   3. add_case_provenance_table.sql           ← THIS FILE
--   4. add_source_documents_table.sql          (depends on this file)
--
-- ============================================================================
-- PURPOSE
-- ============================================================================
-- Store identifying fields (case_name, case_citation, judge_name,
-- docket_number, plaintiff/defense firm names, source URLs) that are
-- stripped from settle_contributions for AUDIT and DATA-PROVENANCE purposes.
--
-- These fields are NEEDED for:
--   (1) Re-validating source data when a verdict's accuracy is questioned
--   (2) Internal compliance / sub-poena response
--   (3) Founding-member dispute resolution (e.g., "is this case in your DB?")
--   (4) Periodic data-quality audits
--
-- These fields MUST NOT appear in:
--   (1) Any SETTLE report sent to attorneys
--   (2) Any API response served to non-internal callers
--   (3) Any view, function, or query that mixes anonymized + identifying data
--
-- ============================================================================
-- DESIGN RATIONALE
-- ============================================================================
-- DEFENSE-IN-DEPTH via PHYSICAL TABLE SEPARATION:
--   Even if the public API accidentally exposed extra columns, the
--   identifying data is unreachable because:
--     (a) it lives in a different table the public role can't see, AND
--     (b) RLS adds a second layer requiring service_role explicitly.
--
-- This is the same pattern used in healthcare (PHI tokenization) and
-- finance (PCI tokenization). The public table holds the bucketed/
-- anonymized data; the private table holds the de-identified-but-
-- traceable identifiers.
--
-- ============================================================================

-- ============================================================================
-- TABLE: settle_case_provenance
-- ============================================================================
CREATE TABLE IF NOT EXISTS settle_case_provenance (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Foreign Key to the public-facing contribution row
    -- 1:1 relationship enforced by UNIQUE constraint
    contribution_id UUID NOT NULL,

    -- ========================================================================
    -- IDENTIFYING / CONFIDENTIAL FIELDS
    -- (stripped from settle_contributions, preserved here for audit)
    -- ========================================================================
    case_name TEXT,                       -- "Smith v. Acme Corp"
    case_citation TEXT,                   -- "2024 FL Cir. Lexis 12345"
    docket_number TEXT,                   -- "2023-CA-001234"
    judge_name TEXT,                      -- "Hon. Jane Doe"
    plaintiff_firm TEXT,                  -- "Morgan & Morgan"
    defense_firm TEXT,                    -- "Kelley Kronenberg"

    -- ========================================================================
    -- SOURCE PROVENANCE (URLs that may name parties)
    -- ========================================================================
    source_url TEXT,                      -- TopVerdict / Verdix / aggregator URL
    news_provenance TEXT,                 -- Exa news article URL (cross-validation source)
    cl_docket_id TEXT,                    -- CourtListener docket ID
    pacer_case_id TEXT,                   -- PACER case ID
    raw_archive_path TEXT,                -- Local path to raw scrape archive (if any)

    -- ========================================================================
    -- ENRICHMENT METADATA (mirrored from canonical CSV for traceability)
    -- These also appear in settle_contributions but are kept here for
    -- self-contained audit queries that don't require a join.
    -- ========================================================================
    enrichment_status TEXT,               -- fully_enriched / cl_enriched / news_enriched / obscure_unenriched
    match_confidence TEXT,                -- high / medium / low / none

    -- ========================================================================
    -- AUDIT TRAIL FIELDS
    -- ========================================================================
    created_at TIMESTAMPTZ DEFAULT now(),
    created_by TEXT,                      -- e.g., "cds_settle_ingest:2026-05-08-fl-run"
    last_audit_access TIMESTAMPTZ,        -- updated when row is read for audit
    last_audit_accessor TEXT,             -- who/what accessed last (set by helper fn)
    internal_notes TEXT,                  -- free-text notes for compliance team

    -- Constraints
    CONSTRAINT fk_settle_case_provenance_contribution
        FOREIGN KEY (contribution_id)
        REFERENCES settle_contributions(id)
        ON DELETE CASCADE,
    CONSTRAINT unique_contribution_provenance
        UNIQUE (contribution_id),
    CONSTRAINT valid_enrichment_status_provenance CHECK (
        enrichment_status IS NULL OR enrichment_status IN (
            'fully_enriched', 'cl_enriched', 'news_enriched',
            'obscure_unenriched', 'sealed_unobtainable', 'invalid_citation'
        )
    ),
    CONSTRAINT valid_match_confidence_provenance CHECK (
        match_confidence IS NULL OR match_confidence IN ('high', 'medium', 'low', 'none')
    )
);

-- ============================================================================
-- INDEXES (internal-audit-only — there are no user-facing queries)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_settle_case_provenance_contribution_id
    ON settle_case_provenance(contribution_id);
CREATE INDEX IF NOT EXISTS idx_settle_case_provenance_docket
    ON settle_case_provenance(docket_number);
CREATE INDEX IF NOT EXISTS idx_settle_case_provenance_citation
    ON settle_case_provenance(case_citation);
CREATE INDEX IF NOT EXISTS idx_settle_case_provenance_created_at
    ON settle_case_provenance(created_at);
CREATE INDEX IF NOT EXISTS idx_settle_case_provenance_enrichment_status
    ON settle_case_provenance(enrichment_status);

-- ============================================================================
-- ROW-LEVEL SECURITY (default deny — only service_role can access)
-- ============================================================================
ALTER TABLE settle_case_provenance ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role only access to settle_case_provenance"
    ON settle_case_provenance;

CREATE POLICY "Service role only access to settle_case_provenance"
ON settle_case_provenance
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- INTENTIONALLY: no policy granted to 'authenticated' or 'anon' roles.
-- Default-deny RLS will block any access from those roles. This is the
-- second layer of defense — even if a query somehow targeted this table
-- from the public API, RLS would deny it.

-- Revoke any default privileges (extra safety on Supabase managed instances)
REVOKE ALL ON TABLE settle_case_provenance FROM PUBLIC;
REVOKE ALL ON TABLE settle_case_provenance FROM authenticated;
REVOKE ALL ON TABLE settle_case_provenance FROM anon;

-- ============================================================================
-- COMMENTS — make access policy discoverable in psql \d+ and pgAdmin
-- ============================================================================
COMMENT ON TABLE settle_case_provenance IS
    'PRIVATE / AUDIT ONLY. Stores case identifying fields stripped from settle_contributions. NEVER join to settle_contributions in user-facing queries. Access via service_role only.';

COMMENT ON COLUMN settle_case_provenance.contribution_id IS
    'FK to settle_contributions(id). DO NOT expose this in any view that includes user-readable fields.';

COMMENT ON COLUMN settle_case_provenance.case_name IS
    'Identifying. Audit only. Never appears in SETTLE reports.';

COMMENT ON COLUMN settle_case_provenance.judge_name IS
    'Identifying. Audit only. Never appears in SETTLE reports.';

COMMENT ON COLUMN settle_case_provenance.docket_number IS
    'Identifying. Audit only. Never appears in SETTLE reports.';

-- ============================================================================
-- HELPER FUNCTION — internal-audit lookup (logs every access)
-- ============================================================================
-- All audit reads should go through this function so we have a record of
-- who looked at identifying data and when. Never SELECT directly from the
-- table for audit purposes — use this function instead.
--
-- Example:
--   SELECT * FROM settle_audit_lookup_provenance(
--       'a1b2c3d4-...'::uuid,
--       'compliance-review-ticket-1234'
--   );
-- ============================================================================
CREATE OR REPLACE FUNCTION settle_audit_lookup_provenance(
    p_contribution_id UUID,
    p_accessor TEXT
)
RETURNS TABLE (
    id UUID,
    contribution_id UUID,
    case_name TEXT,
    case_citation TEXT,
    docket_number TEXT,
    judge_name TEXT,
    plaintiff_firm TEXT,
    defense_firm TEXT,
    source_url TEXT,
    news_provenance TEXT,
    enrichment_status TEXT,
    match_confidence TEXT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    -- Validate accessor was provided (force traceability)
    IF p_accessor IS NULL OR length(trim(p_accessor)) = 0 THEN
        RAISE EXCEPTION 'settle_audit_lookup_provenance: p_accessor required for traceability';
    END IF;

    -- Log the access first (atomic with the read)
    UPDATE settle_case_provenance
    SET last_audit_access = now(),
        last_audit_accessor = p_accessor
    WHERE settle_case_provenance.contribution_id = p_contribution_id;

    -- Then return identifying fields
    RETURN QUERY
    SELECT
        scp.id,
        scp.contribution_id,
        scp.case_name,
        scp.case_citation,
        scp.docket_number,
        scp.judge_name,
        scp.plaintiff_firm,
        scp.defense_firm,
        scp.source_url,
        scp.news_provenance,
        scp.enrichment_status,
        scp.match_confidence,
        scp.created_at
    FROM settle_case_provenance scp
    WHERE scp.contribution_id = p_contribution_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE ALL ON FUNCTION settle_audit_lookup_provenance(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION settle_audit_lookup_provenance(UUID, TEXT) TO service_role;

COMMENT ON FUNCTION settle_audit_lookup_provenance(UUID, TEXT) IS
    'Internal audit lookup. Logs every read into last_audit_access/last_audit_accessor. Always use this instead of SELECTing the table directly.';

-- ============================================================================
-- AUDIT VIEW — admin-only, logs not enforced (use sparingly)
-- ============================================================================
-- Sometimes ops needs a quick scan; this view is only visible to service_role
-- via the same RLS rules. It does NOT log access — prefer the function above.
-- ============================================================================
CREATE OR REPLACE VIEW settle_case_provenance_admin_view AS
SELECT
    scp.id,
    scp.contribution_id,
    scp.case_name,
    scp.case_citation,
    scp.docket_number,
    scp.judge_name,
    scp.plaintiff_firm,
    scp.defense_firm,
    scp.enrichment_status,
    scp.match_confidence,
    scp.created_at,
    scp.last_audit_access,
    scp.last_audit_accessor,
    sc.jurisdiction,
    sc.case_type,
    sc.outcome_amount_range,
    sc.status
FROM settle_case_provenance scp
JOIN settle_contributions sc ON sc.id = scp.contribution_id;

REVOKE ALL ON settle_case_provenance_admin_view FROM PUBLIC;
REVOKE ALL ON settle_case_provenance_admin_view FROM authenticated;
REVOKE ALL ON settle_case_provenance_admin_view FROM anon;
GRANT SELECT ON settle_case_provenance_admin_view TO service_role;

COMMENT ON VIEW settle_case_provenance_admin_view IS
    'ADMIN-ONLY view joining provenance to contribution. NEVER expose in user-facing API. service_role only.';

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'settle_case_provenance table created (PRIVATE / audit-only)';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE '⚠️  REMINDER: This table is for INTERNAL AUDIT ONLY';
    RAISE NOTICE '⚠️  SETTLE report queries must use settle_contributions, NOT this table';
    RAISE NOTICE '⚠️  RLS is enabled — only service_role can read/write';
    RAISE NOTICE '⚠️  Use settle_audit_lookup_provenance(id, accessor) for audit queries';
    RAISE NOTICE '⚠️  Anyone querying this table without a paper trail is doing it wrong';
    RAISE NOTICE '============================================================================';
END $$;

-- ============================================================================
-- END
-- ============================================================================
