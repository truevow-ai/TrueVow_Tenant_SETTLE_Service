-- ============================================================================
-- TrueVow SETTLE™ Service - Internal Verdict Database Schema
-- ============================================================================
-- Version: 1.0.0
-- Last Updated: May 18, 2026
-- Status: Internal Research Only — NOT customer-facing
--
-- Purpose: Internal verdict research engine (ALM VerdictSearch competitor)
-- Used by SETTLE team for research, data validation, and benchmark calibration.
-- Fed by scraping pipeline (settle_data_scraping_factory/).
--
-- IMPORTANT: This is INTERNAL ONLY. Contains case names, judge names, carrier
-- names, and other data NOT permitted in the customer-facing SETTLE DB.
-- ============================================================================

-- ============================================================================
-- TABLE 1: settle_verdicts (Internal Verdict Database)
-- Purpose: Store scraped and manually-entered verdict/settlement case data
-- ============================================================================
CREATE TABLE IF NOT EXISTS settle_verdicts (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- ========================================================================
    -- CASE IDENTIFICATION (Internal only — not exposed to customers)
    -- ========================================================================
    case_name TEXT,                               -- May contain party names (internal research)
    case_number TEXT,                             -- Court docket number
    jurisdiction TEXT NOT NULL,                   -- e.g., "Maricopa County, AZ"
    court TEXT,                                   -- Court name (e.g., "Superior Court")
    judge_name TEXT,                              -- Judge name (internal research)

    -- ========================================================================
    -- CASE CLASSIFICATION
    -- ========================================================================
    case_type TEXT NOT NULL,                      -- Maps to VALID_CASE_TYPES
    injury_type TEXT[],                           -- Maps to InjuryTag 17-tag system
    plaintiff_age_range TEXT,                     -- 'under_18', '18_30', '31_45', '46_60', '61_75', '75_plus'
    liability_tier TEXT,                          -- 'clear', 'contested', 'shared', 'unknown'
    comparative_negligence_pct NUMERIC,           -- 0-100%

    -- ========================================================================
    -- FINANCIAL DATA (Internal — exact amounts stored)
    -- ========================================================================
    medical_bills NUMERIC,                        -- Exact medical bills
    economic_damages NUMERIC,                     -- Lost wages, future medical, etc.
    non_economic_damages NUMERIC,                 -- Pain and suffering
    punitive_damages NUMERIC,                     -- If awarded
    total_verdict NUMERIC,                        -- Sum of all damages
    settlement_amount NUMERIC,                    -- If settled pre-verdict
    policy_limit_indicator TEXT,                  -- 'below_limits', 'at_limits', 'above_limits', 'unknown'

    -- ========================================================================
    -- OUTCOME
    -- ========================================================================
    outcome_type TEXT NOT NULL,                   -- 'verdict_plaintiff', 'verdict_defense', 'settlement', 'dismissed'
    defendant_category TEXT,                      -- 'Individual', 'Business', 'Government', 'Unknown'
    defendant_industry TEXT,                      -- 'Healthcare', 'Automotive', 'Retail', 'Construction', etc.
    insurance_carrier TEXT,                       -- Carrier name (internal research)

    -- ========================================================================
    -- TRIAL DATA (Verdict cases only)
    -- ========================================================================
    expert_witnesses_plaintiff INT,               -- Count
    expert_witnesses_defense INT,                 -- Count
    trial_duration_days INT,                      -- Days (verdict cases only)

    -- ========================================================================
    -- TIMING
    -- ========================================================================
    verdict_date DATE,                            -- Date of outcome
    filing_date DATE,                             -- Date case was filed
    resolution_date DATE,                         -- Date case was resolved

    -- ========================================================================
    -- SOURCE & PROVENANCE
    -- ========================================================================
    source TEXT NOT NULL,                         -- 'scraped', 'manual_entry', 'partner_data'
    source_url TEXT,                              -- Original source URL for verification
    source_notes TEXT,                            -- Notes about the source

    -- ========================================================================
    -- DATA QUALITY
    -- ========================================================================
    confidence_score NUMERIC DEFAULT 0.5,         -- 0.0-1.0 data quality score
    completeness_score NUMERIC DEFAULT 0.0,       -- 0.0-1.0 field completeness
    review_status TEXT DEFAULT 'pending',         -- 'pending', 'reviewed', 'verified', 'rejected'
    reviewer_notes TEXT,                          -- Notes from manual review

    -- ========================================================================
    -- METADATA
    -- ========================================================================
    scraped_at TIMESTAMPTZ,                       -- When this was scraped
    created_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID,                              -- User who created (manual entry)
    updated_at TIMESTAMPTZ DEFAULT now(),
    updated_by UUID,
    deleted_at TIMESTAMPTZ,                       -- Soft-delete
    deleted_by UUID,
    row_version INTEGER NOT NULL DEFAULT 1,

    -- Constraints
    CONSTRAINT valid_verdict_outcome_type CHECK (
        outcome_type IN ('verdict_plaintiff', 'verdict_defense', 'settlement', 'dismissed')
    ),
    CONSTRAINT valid_verdict_review_status CHECK (
        review_status IN ('pending', 'reviewed', 'verified', 'rejected')
    ),
    CONSTRAINT valid_verdict_source CHECK (
        source IN ('scraped', 'manual_entry', 'partner_data')
    ),
    CONSTRAINT valid_verdict_liability_tier CHECK (
        liability_tier IN ('clear', 'contested', 'shared', 'unknown')
    ),
    CONSTRAINT valid_verdict_plaintiff_age CHECK (
        plaintiff_age_range IN ('under_18', '18_30', '31_45', '46_60', '61_75', '75_plus')
    ),
    CONSTRAINT valid_verdict_policy_limit CHECK (
        policy_limit_indicator IN ('below_limits', 'at_limits', 'above_limits', 'unknown')
    ),
    CONSTRAINT valid_verdict_confidence CHECK (confidence_score >= 0 AND confidence_score <= 1),
    CONSTRAINT valid_verdict_completeness CHECK (completeness_score >= 0 AND completeness_score <= 1),
    CONSTRAINT valid_verdict_comparative_negligence CHECK (
        comparative_negligence_pct IS NULL OR (comparative_negligence_pct >= 0 AND comparative_negligence_pct <= 100)
    )
);

-- Indexes for fast search
CREATE INDEX IF NOT EXISTS idx_verdicts_jurisdiction ON settle_verdicts(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_verdicts_case_type ON settle_verdicts(case_type);
CREATE INDEX IF NOT EXISTS idx_verdicts_injury_type ON settle_verdicts USING GIN(injury_type);
CREATE INDEX IF NOT EXISTS idx_verdicts_outcome_type ON settle_verdicts(outcome_type);
CREATE INDEX IF NOT EXISTS idx_verdicts_liability_tier ON settle_verdicts(liability_tier);
CREATE INDEX IF NOT EXISTS idx_verdicts_defendant_category ON settle_verdicts(defendant_category);
CREATE INDEX IF NOT EXISTS idx_verdicts_defendant_industry ON settle_verdicts(defendant_industry);
CREATE INDEX IF NOT EXISTS idx_verdicts_insurance_carrier ON settle_verdicts(insurance_carrier);
CREATE INDEX IF NOT EXISTS idx_verdicts_plaintiff_age ON settle_verdicts(plaintiff_age_range);
CREATE INDEX IF NOT EXISTS idx_verdicts_verdict_date ON settle_verdicts(verdict_date);
CREATE INDEX IF NOT EXISTS idx_verdicts_total_verdict ON settle_verdicts(total_verdict);
CREATE INDEX IF NOT EXISTS idx_verdicts_medical_bills ON settle_verdicts(medical_bills);
CREATE INDEX IF NOT EXISTS idx_verdicts_review_status ON settle_verdicts(review_status);
CREATE INDEX IF NOT EXISTS idx_verdicts_source ON settle_verdicts(source);
CREATE INDEX IF NOT EXISTS idx_verdicts_confidence ON settle_verdicts(confidence_score);
CREATE INDEX IF NOT EXISTS idx_verdicts_court ON settle_verdicts(court);
CREATE INDEX IF NOT EXISTS idx_verdicts_judge ON settle_verdicts(judge_name);

-- Composite index for common search pattern
CREATE INDEX IF NOT EXISTS idx_verdicts_search_pattern
ON settle_verdicts(jurisdiction, case_type, outcome_type, review_status)
WHERE review_status IN ('reviewed', 'verified');

-- Composite index for financial analysis
CREATE INDEX IF NOT EXISTS idx_verdicts_financial
ON settle_verdicts(case_type, injury_type, outcome_type)
WHERE total_verdict IS NOT NULL;

-- Soft-delete index
CREATE INDEX IF NOT EXISTS idx_verdicts_deleted_at
ON settle_verdicts(deleted_at)
WHERE deleted_at IS NULL;

-- ============================================================================
-- TABLE 2: settle_verdict_scrape_jobs
-- Purpose: Track scraping job runs for monitoring and debugging
-- ============================================================================
CREATE TABLE IF NOT EXISTS settle_verdict_scrape_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source TEXT NOT NULL,                         -- 'casemine', 'law360', 'verdictsearch', etc.
    status TEXT DEFAULT 'running',                -- 'running', 'completed', 'failed', 'partial'
    records_found INT DEFAULT 0,
    records_inserted INT DEFAULT 0,
    records_skipped INT DEFAULT 0,
    records_failed INT DEFAULT 0,
    error_log TEXT,                               -- JSON error details
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    created_by UUID,

    CONSTRAINT valid_scrape_status CHECK (
        status IN ('running', 'completed', 'failed', 'partial')
    )
);

CREATE INDEX IF NOT EXISTS idx_scrape_jobs_source ON settle_verdict_scrape_jobs(source);
CREATE INDEX IF NOT EXISTS idx_scrape_jobs_status ON settle_verdict_scrape_jobs(status);
CREATE INDEX IF NOT EXISTS idx_scrape_jobs_started ON settle_verdict_scrape_jobs(started_at);

-- ============================================================================
-- TABLE 3: settle_verdict_search_history
-- Purpose: Track internal search queries for analytics
-- ============================================================================
CREATE TABLE IF NOT EXISTS settle_verdict_search_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    search_filters JSONB,                         -- The filters used in the search
    result_count INT,
    response_time_ms INT,
    searched_by UUID,                             -- User who ran the search
    searched_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_search_history_searched_at ON settle_verdict_search_history(searched_at);
CREATE INDEX IF NOT EXISTS idx_search_history_searched_by ON settle_verdict_search_history(searched_by);

-- ============================================================================
-- VIEWS FOR ANALYTICS
-- ============================================================================

-- View: Verified verdicts only (for research)
CREATE OR REPLACE VIEW settle_verified_verdicts AS
SELECT * FROM settle_verdicts
WHERE review_status IN ('reviewed', 'verified')
  AND deleted_at IS NULL;

-- View: Verdict statistics by jurisdiction
CREATE OR REPLACE VIEW settle_verdict_stats_by_jurisdiction AS
SELECT
    jurisdiction,
    COUNT(*) as total_cases,
    COUNT(*) FILTER (WHERE outcome_type = 'verdict_plaintiff') as plaintiff_verdicts,
    COUNT(*) FILTER (WHERE outcome_type = 'verdict_defense') as defense_verdicts,
    COUNT(*) FILTER (WHERE outcome_type = 'settlement') as settlements,
    COUNT(*) FILTER (WHERE outcome_type = 'dismissed') as dismissed,
    AVG(total_verdict) FILTER (WHERE total_verdict IS NOT NULL) as avg_verdict_amount,
    AVG(settlement_amount) FILTER (WHERE settlement_amount IS NOT NULL) as avg_settlement_amount,
    AVG(confidence_score) as avg_confidence
FROM settle_verdicts
WHERE review_status IN ('reviewed', 'verified')
  AND deleted_at IS NULL
GROUP BY jurisdiction;

-- View: Verdict statistics by case type
CREATE OR REPLACE VIEW settle_verdict_stats_by_case_type AS
SELECT
    case_type,
    COUNT(*) as total_cases,
    AVG(total_verdict) FILTER (WHERE total_verdict IS NOT NULL) as avg_verdict_amount,
    AVG(settlement_amount) FILTER (WHERE settlement_amount IS NOT NULL) as avg_settlement_amount,
    AVG(medical_bills) FILTER (WHERE medical_bills IS NOT NULL) as avg_medical_bills,
    COUNT(*) FILTER (WHERE review_status = 'verified') as verified_count
FROM settle_verdicts
WHERE review_status IN ('reviewed', 'verified')
  AND deleted_at IS NULL
GROUP BY case_type;

-- View: Carrier payout patterns (internal research)
CREATE OR REPLACE VIEW settle_verdict_carrier_patterns AS
SELECT
    insurance_carrier,
    defendant_industry,
    COUNT(*) as case_count,
    AVG(settlement_amount) FILTER (WHERE settlement_amount IS NOT NULL) as avg_settlement,
    AVG(total_verdict) FILTER (WHERE total_verdict IS NOT NULL) as avg_verdict,
    COUNT(*) FILTER (WHERE outcome_type = 'settlement') as settlement_count,
    COUNT(*) FILTER (WHERE outcome_type IN ('verdict_plaintiff', 'verdict_defense')) as trial_count,
    AVG(trial_duration_days) FILTER (WHERE trial_duration_days IS NOT NULL) as avg_trial_days
FROM settle_verdicts
WHERE review_status IN ('reviewed', 'verified')
  AND deleted_at IS NULL
  AND insurance_carrier IS NOT NULL
GROUP BY insurance_carrier, defendant_industry;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger: Auto-update updated_at on settle_verdicts
DROP TRIGGER IF EXISTS update_settle_verdicts_updated_at ON settle_verdicts;
CREATE TRIGGER update_settle_verdicts_updated_at
    BEFORE UPDATE ON settle_verdicts
    FOR EACH ROW
    EXECUTE FUNCTION settle_update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE settle_verdicts IS 'Internal verdict research database — NOT customer-facing. Contains case names, judge names, carrier names.';
COMMENT ON TABLE settle_verdict_scrape_jobs IS 'Tracking for scraping job runs';
COMMENT ON TABLE settle_verdict_search_history IS 'Internal search query analytics';

COMMENT ON COLUMN settle_verdicts.case_name IS 'May contain party names — internal research only, never exposed to customers';
COMMENT ON COLUMN settle_verdicts.judge_name IS 'Judge name — internal research only, never exposed to customers';
COMMENT ON COLUMN settle_verdicts.insurance_carrier IS 'Carrier name — internal research only, anonymized for customer-facing features';
COMMENT ON COLUMN settle_verdicts.confidence_score IS '0.0-1.0 data quality score based on source reliability and field completeness';
COMMENT ON COLUMN settle_verdicts.completeness_score IS '0.0-1.0 ratio of filled required fields';

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Internal Verdict Database Schema Created Successfully!';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Tables Created:';
    RAISE NOTICE '  1. settle_verdicts (internal verdict research)';
    RAISE NOTICE '  2. settle_verdict_scrape_jobs (scraping job tracking)';
    RAISE NOTICE '  3. settle_verdict_search_history (search analytics)';
    RAISE NOTICE '';
    RAISE NOTICE 'Views Created:';
    RAISE NOTICE '  - settle_verified_verdicts';
    RAISE NOTICE '  - settle_verdict_stats_by_jurisdiction';
    RAISE NOTICE '  - settle_verdict_stats_by_case_type';
    RAISE NOTICE '  - settle_verdict_carrier_patterns';
    RAISE NOTICE '';
    RAISE NOTICE 'WARNING: This schema contains internal-only data (case names,';
    RAISE NOTICE 'judge names, carrier names). NEVER expose these fields to customers.';
    RAISE NOTICE '============================================================================';
END $$;
