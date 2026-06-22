-- ============================================================================
-- DOCKET-Service — Docket/Litigation Tracker Schema (Phase 5)
-- ============================================================================
-- Purpose: Track court dockets, filings, and litigation outcomes
-- Separate from SETTLE DB — public record data (names/PII permissible)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLE 1: docket_cases
-- Purpose: Store docket/case data from various sources
-- ============================================================================
CREATE TABLE IF NOT EXISTS docket_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Case Identification
    court_id VARCHAR(50),
    case_number VARCHAR(100),
    case_name VARCHAR(500),              -- May contain party names (public record)

    -- Classification
    case_type VARCHAR(100),
    filing_date DATE,
    status VARCHAR(50),                   -- active, closed, appealed, etc.

    -- Participants
    judge_name VARCHAR(200),
    plaintiff_attorney VARCHAR(200),
    defense_attorney VARCHAR(200),
    plaintiff_firm VARCHAR(200),
    defense_firm VARCHAR(200),
    parties JSONB,                        -- Structured party data
    claims JSONB,                         -- Claims/causes of action

    -- Outcomes
    outcomes JSONB,                       -- Structured outcome data
    damages_claimed DECIMAL,
    damages_awarded DECIMAL,
    settlement_amount DECIMAL,

    -- Timing
    last_activity_date DATE,

    -- Source & Provenance
    source VARCHAR(100),                  -- 'pacer', 'courtlistener', 'scraped', 'manual'
    source_url TEXT,
    scraped_at TIMESTAMPTZ,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_docket_court_id ON docket_cases(court_id);
CREATE INDEX IF NOT EXISTS idx_docket_case_number ON docket_cases(case_number);
CREATE INDEX IF NOT EXISTS idx_docket_case_type ON docket_cases(case_type);
CREATE INDEX IF NOT EXISTS idx_docket_status ON docket_cases(status);
CREATE INDEX IF NOT EXISTS idx_docket_judge ON docket_cases(judge_name);
CREATE INDEX IF NOT EXISTS idx_docket_plaintiff_attorney ON docket_cases(plaintiff_attorney);
CREATE INDEX IF NOT EXISTS idx_docket_defense_attorney ON docket_cases(defense_attorney);
CREATE INDEX IF NOT EXISTS idx_docket_plaintiff_firm ON docket_cases(plaintiff_firm);
CREATE INDEX IF NOT EXISTS idx_docket_defense_firm ON docket_cases(defense_firm);
CREATE INDEX IF NOT EXISTS idx_docket_filing_date ON docket_cases(filing_date);
CREATE INDEX IF NOT EXISTS idx_docket_last_activity ON docket_cases(last_activity_date);
CREATE INDEX IF NOT EXISTS idx_docket_source ON docket_cases(source);

-- ============================================================================
-- TABLE 2: docket_scrape_jobs
-- Purpose: Track scraping job runs
-- ============================================================================
CREATE TABLE IF NOT EXISTS docket_scrape_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source TEXT NOT NULL,                 -- 'pacer', 'courtlistener', etc.
    status TEXT DEFAULT 'running',        -- 'running', 'completed', 'failed', 'partial'
    records_found INT DEFAULT 0,
    records_inserted INT DEFAULT 0,
    records_skipped INT DEFAULT 0,
    records_failed INT DEFAULT 0,
    error_log TEXT,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    created_by UUID
);

CREATE INDEX IF NOT EXISTS idx_docket_scrape_source ON docket_scrape_jobs(source);
CREATE INDEX IF NOT EXISTS idx_docket_scrape_status ON docket_scrape_jobs(status);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View: Active cases
CREATE OR REPLACE VIEW docket_active_cases AS
SELECT * FROM docket_cases
WHERE status = 'active' AND deleted_at IS NULL;

-- View: Cases by judge
CREATE OR REPLACE VIEW docket_cases_by_judge AS
SELECT
    judge_name,
    COUNT(*) as total_cases,
    COUNT(*) FILTER (WHERE status = 'active') as active_cases,
    COUNT(*) FILTER (WHERE status = 'closed') as closed_cases,
    AVG(damages_awarded) FILTER (WHERE damages_awarded IS NOT NULL) as avg_damages_awarded,
    AVG(settlement_amount) FILTER (WHERE settlement_amount IS NOT NULL) as avg_settlement
FROM docket_cases
WHERE judge_name IS NOT NULL AND deleted_at IS NULL
GROUP BY judge_name;

-- View: Cases by firm
CREATE OR REPLACE VIEW docket_cases_by_firm AS
SELECT
    plaintiff_firm,
    COUNT(*) as total_cases,
    COUNT(*) FILTER (WHERE damages_awarded IS NOT NULL) as cases_with_awards,
    AVG(damages_awarded) FILTER (WHERE damages_awarded IS NOT NULL) as avg_damages,
    AVG(settlement_amount) FILTER (WHERE settlement_amount IS NOT NULL) as avg_settlement
FROM docket_cases
WHERE plaintiff_firm IS NOT NULL AND deleted_at IS NULL
GROUP BY plaintiff_firm;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

CREATE OR REPLACE FUNCTION docket_update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_docket_cases_updated_at
    BEFORE UPDATE ON docket_cases
    FOR EACH ROW
    EXECUTE FUNCTION docket_update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE docket_cases IS 'Court docket and litigation tracking data — public records, separate from SETTLE';
COMMENT ON TABLE docket_scrape_jobs IS 'Tracking for docket scraping job runs';

DO $$
BEGIN
    RAISE NOTICE 'DOCKET-Service Schema Created Successfully!';
    RAISE NOTICE 'Tables: docket_cases, docket_scrape_jobs';
    RAISE NOTICE 'Views: docket_active_cases, docket_cases_by_judge, docket_cases_by_firm';
END $$;
