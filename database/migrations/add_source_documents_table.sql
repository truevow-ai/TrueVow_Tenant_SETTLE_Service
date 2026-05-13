-- ============================================================================
-- Migration: add_source_documents_table
-- Adds: settle_source_documents (PRIVATE / AUDIT ONLY)
-- ============================================================================
-- Version: 1.0.0
-- Last Updated: 2026-05-08
-- Status: Phase 2.1 — Three-table defense-in-depth architecture
--
-- Prerequisites (apply in order):
--   1. database/schemas/settle_supabase.sql       (creates settle_contributions et al.)
--   2. database/migrations/add_waitlist_table.sql (pre-existing additive migration)
--   3. database/migrations/add_case_provenance_table.sql  (creates settle_case_provenance)
--   4. THIS FILE (creates settle_source_documents with FK to settle_case_provenance)
--
-- This is additive. It does not modify any existing table.
--
-- ============================================================================
-- PURPOSE
-- ============================================================================
-- Store the literal scraped source documents (news articles, court opinions,
-- plaintiff-firm announcements, aggregator entries) that justify each
-- contribution row. URL alone is insufficient because:
--   - Link rot: ~25% of news links break within 7 years
--   - Paywall hardening: archives become unreadable over time
--   - Silent post-publication edits: figures change without notice
--
-- This table is the cryptographically verifiable source-of-record. It exists
-- to make defense possible when a verdict figure is challenged years later.
--
-- ============================================================================
-- DESIGN
-- ============================================================================
--   - DB row holds metadata + extracted clean text (FTS-indexed)
--   - Raw bytes (HTML/PDF) live in Supabase Storage; only the path is in DB
--   - SHA-256 of raw bytes stored at fetch time for integrity verification
--   - OpenTimestamps proof path reserved (TODO — implement in Phase 2.2)
--   - 1:N relationship — one provenance row can have many source documents
--     (primary news article + cross-validation article + court PR + etc.)
--
-- ============================================================================
-- ACCESS POLICY
-- ============================================================================
--   - service_role only (RLS enforced)
--   - authenticated and anon explicitly REVOKED
--   - All audit reads should go through settle_audit_lookup_source_document()
--     (logs every access into last_accessed / last_accessor)
-- ============================================================================

CREATE TABLE IF NOT EXISTS settle_source_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- FK to provenance row (1:N — one case can have many source documents)
    provenance_id UUID NOT NULL,

    -- ========================================================================
    -- SOURCE IDENTIFICATION
    -- ========================================================================
    source_type TEXT NOT NULL,            -- news_article / court_opinion / etc.
    source_domain TEXT,                   -- 'miamiherald.com'
    source_url TEXT NOT NULL,             -- canonical URL we fetched
    publication_name TEXT,                -- 'Miami Herald'
    publication_date DATE,                -- when the article was published

    -- ========================================================================
    -- CONTENT (split between DB and object storage)
    -- ========================================================================
    extracted_text TEXT,                  -- clean Readability text (FTS-indexed)
    extracted_text_word_count INT,
    raw_archive_path TEXT,                -- 'sources/{prov_id}/{hash16}.html'
    raw_mime_type TEXT,
    raw_size_bytes BIGINT,

    -- ========================================================================
    -- CRYPTOGRAPHIC VERIFICATION
    -- ========================================================================
    content_sha256 TEXT NOT NULL,         -- SHA-256 of raw bytes
    content_sha256_extracted TEXT,        -- SHA-256 of extracted_text
    ots_proof_path TEXT,                  -- OpenTimestamps proof file path (TODO)
    ots_proof_timestamp TIMESTAMPTZ,      -- when timestamped (TODO)

    -- ========================================================================
    -- FETCH METADATA
    -- ========================================================================
    fetched_at TIMESTAMPTZ NOT NULL,
    fetched_via TEXT,                     -- 'cds_archive_source' / 'manual'
    fetched_status_code INT,              -- HTTP status at fetch
    fetched_user_agent TEXT,

    -- ========================================================================
    -- COPYRIGHT + ACCESS FLAGS
    -- ========================================================================
    copyright_status TEXT,                -- public_domain / fair_use_audit / paywalled_metadata_only
    redistribution_blocked BOOLEAN DEFAULT TRUE,

    -- ========================================================================
    -- CROSS-VALIDATION ROLE
    -- ========================================================================
    role_in_validation TEXT,              -- primary / cross_validation / tertiary

    -- ========================================================================
    -- AUDIT TRAIL
    -- ========================================================================
    created_at TIMESTAMPTZ DEFAULT now(),
    created_by TEXT,
    last_accessed TIMESTAMPTZ,
    last_accessor TEXT,

    -- ========================================================================
    -- FULL-TEXT SEARCH SUPPORT
    -- ========================================================================
    extracted_text_tsv TSVECTOR,

    -- Constraints
    CONSTRAINT fk_settle_source_documents_provenance
        FOREIGN KEY (provenance_id)
        REFERENCES settle_case_provenance(id)
        ON DELETE CASCADE,
    CONSTRAINT valid_source_type CHECK (source_type IN (
        'news_article', 'court_opinion', 'plaintiff_firm_announcement',
        'aggregator_entry', 'press_release', 'pdf_filing', 'other'
    )),
    CONSTRAINT valid_copyright_status CHECK (
        copyright_status IS NULL OR copyright_status IN (
            'public_domain', 'fair_use_audit', 'licensed', 'paywalled_metadata_only'
        )
    ),
    CONSTRAINT valid_role CHECK (
        role_in_validation IS NULL OR role_in_validation IN (
            'primary', 'cross_validation', 'tertiary'
        )
    ),
    CONSTRAINT valid_sha256 CHECK (content_sha256 ~ '^[a-f0-9]{64}$')
);

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_settle_source_documents_provenance_id
    ON settle_source_documents(provenance_id);
CREATE INDEX IF NOT EXISTS idx_settle_source_documents_source_url
    ON settle_source_documents(source_url);
CREATE INDEX IF NOT EXISTS idx_settle_source_documents_content_sha256
    ON settle_source_documents(content_sha256);
CREATE INDEX IF NOT EXISTS idx_settle_source_documents_fetched_at
    ON settle_source_documents(fetched_at);
CREATE INDEX IF NOT EXISTS idx_settle_source_documents_copyright_status
    ON settle_source_documents(copyright_status);
CREATE INDEX IF NOT EXISTS idx_settle_source_documents_fts
    ON settle_source_documents USING GIN(extracted_text_tsv);

-- ============================================================================
-- TRIGGER: auto-update tsvector on insert/update of extracted_text
-- ============================================================================
CREATE OR REPLACE FUNCTION settle_source_documents_tsv_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.extracted_text_tsv := to_tsvector('english', COALESCE(NEW.extracted_text, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_settle_source_documents_tsv_update
    ON settle_source_documents;
CREATE TRIGGER trg_settle_source_documents_tsv_update
    BEFORE INSERT OR UPDATE OF extracted_text ON settle_source_documents
    FOR EACH ROW EXECUTE FUNCTION settle_source_documents_tsv_update();

-- ============================================================================
-- ROW-LEVEL SECURITY (default deny — service_role only)
-- ============================================================================
ALTER TABLE settle_source_documents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Service role only access to settle_source_documents"
    ON settle_source_documents;

CREATE POLICY "Service role only access to settle_source_documents"
ON settle_source_documents
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- INTENTIONALLY: no policy granted to 'authenticated' or 'anon' roles.
-- Default-deny RLS will block any access from those roles.

REVOKE ALL ON TABLE settle_source_documents FROM PUBLIC;
REVOKE ALL ON TABLE settle_source_documents FROM authenticated;
REVOKE ALL ON TABLE settle_source_documents FROM anon;

-- ============================================================================
-- COMMENTS — make access policy discoverable
-- ============================================================================
COMMENT ON TABLE settle_source_documents IS
    'PRIVATE / AUDIT ONLY. Source-of-record bytes (HTML/PDF) for case enrichment data. NEVER expose in user-facing API. service_role only.';

COMMENT ON COLUMN settle_source_documents.provenance_id IS
    'FK to settle_case_provenance(id). Multiple source documents per provenance row supported (1:N).';

COMMENT ON COLUMN settle_source_documents.content_sha256 IS
    'SHA-256 of raw bytes at fetch time. Used to detect post-fetch tampering and prove chain of custody.';

COMMENT ON COLUMN settle_source_documents.raw_archive_path IS
    'Path within Supabase Storage bucket (settle-source-archive). Object stored privately; only service_role can fetch.';

COMMENT ON COLUMN settle_source_documents.copyright_status IS
    'public_domain (court docs) / fair_use_audit (news for internal audit) / licensed / paywalled_metadata_only (NYT/WSJ — URL only, no body)';

-- ============================================================================
-- HELPER FUNCTION — internal-audit lookup (logs every access)
-- ============================================================================
-- All audit reads should go through this function so we have a record of
-- who looked at source documents and when.
--
-- Example:
--   SELECT * FROM settle_audit_lookup_source_document(
--       'a1b2c3d4-...'::uuid,
--       'compliance-ticket-1234'
--   );
-- ============================================================================
CREATE OR REPLACE FUNCTION settle_audit_lookup_source_document(
    p_doc_id UUID,
    p_accessor TEXT
)
RETURNS TABLE (
    id UUID,
    provenance_id UUID,
    source_type TEXT,
    source_url TEXT,
    publication_name TEXT,
    publication_date DATE,
    extracted_text TEXT,
    raw_archive_path TEXT,
    content_sha256 TEXT,
    ots_proof_timestamp TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ,
    copyright_status TEXT
) AS $$
BEGIN
    -- Validate accessor was provided (force traceability)
    IF p_accessor IS NULL OR length(trim(p_accessor)) = 0 THEN
        RAISE EXCEPTION 'settle_audit_lookup_source_document: p_accessor required for traceability';
    END IF;

    -- Log the access first (atomic with the read)
    UPDATE settle_source_documents
    SET last_accessed = now(),
        last_accessor = p_accessor
    WHERE settle_source_documents.id = p_doc_id;

    -- Then return the document
    RETURN QUERY
    SELECT ssd.id, ssd.provenance_id, ssd.source_type, ssd.source_url,
           ssd.publication_name, ssd.publication_date,
           ssd.extracted_text, ssd.raw_archive_path,
           ssd.content_sha256, ssd.ots_proof_timestamp,
           ssd.fetched_at, ssd.copyright_status
    FROM settle_source_documents ssd
    WHERE ssd.id = p_doc_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE ALL ON FUNCTION settle_audit_lookup_source_document(UUID, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION settle_audit_lookup_source_document(UUID, TEXT) TO service_role;

COMMENT ON FUNCTION settle_audit_lookup_source_document(UUID, TEXT) IS
    'Internal audit lookup for source documents. Logs every read into last_accessed/last_accessor. Always use this instead of direct SELECT.';

-- ============================================================================
-- FULL-TEXT SEARCH HELPER (admin-only)
-- ============================================================================
-- Search across all archived source documents for a phrase.
-- Returns matching documents with relevance ranking.
-- ============================================================================
CREATE OR REPLACE FUNCTION settle_search_source_documents(
    p_query TEXT,
    p_limit INT DEFAULT 50
)
RETURNS TABLE (
    id UUID,
    provenance_id UUID,
    source_url TEXT,
    publication_name TEXT,
    rank REAL,
    snippet TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ssd.id,
        ssd.provenance_id,
        ssd.source_url,
        ssd.publication_name,
        ts_rank(ssd.extracted_text_tsv, plainto_tsquery('english', p_query)) AS rank,
        ts_headline('english', ssd.extracted_text, plainto_tsquery('english', p_query),
                    'StartSel=<mark>, StopSel=</mark>, MaxFragments=2, MaxWords=30, MinWords=10') AS snippet
    FROM settle_source_documents ssd
    WHERE ssd.extracted_text_tsv @@ plainto_tsquery('english', p_query)
    ORDER BY rank DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE ALL ON FUNCTION settle_search_source_documents(TEXT, INT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION settle_search_source_documents(TEXT, INT) TO service_role;

COMMENT ON FUNCTION settle_search_source_documents(TEXT, INT) IS
    'Full-text search across archived source documents. service_role only.';

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'settle_source_documents table created (PRIVATE / audit-only)';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Architecture is now THREE tables:';
    RAISE NOTICE '  settle_contributions       (PUBLIC, anonymized, bucketed)';
    RAISE NOTICE '  settle_case_provenance     (PRIVATE, identifying metadata)';
    RAISE NOTICE '  settle_source_documents    (PRIVATE, source-of-record bytes)';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  Source bodies live in Supabase Storage bucket: settle-source-archive';
    RAISE NOTICE '⚠️  RLS locks all three private tables to service_role only';
    RAISE NOTICE '⚠️  Use settle_audit_lookup_source_document(id, accessor) for audit reads';
    RAISE NOTICE '⚠️  Use settle_search_source_documents(query) for full-text search';
    RAISE NOTICE '============================================================================';
END $$;

-- ============================================================================
-- END
-- ============================================================================
