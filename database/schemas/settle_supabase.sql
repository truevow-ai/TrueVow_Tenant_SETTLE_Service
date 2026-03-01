-- ============================================================================
-- TrueVow SETTLE™ Service - Supabase Schema (Production)
-- ============================================================================
-- Version: 1.0.0
-- Last Updated: December 7, 2025
-- Status: Production-Ready, Bar-Compliant, Zero-PHI
--
-- IMPORTANT: This schema REFERENCES existing central tables:
--   - users (from SaaS Admin) - for attorney accounts
--   - NO contacts table - SETTLE doesn't need contact info
--
-- All tables use settle_ prefix for clear separation
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- SETTLE SCHEMA
-- ============================================================================

-- Create settle schema (optional, can use public)
-- CREATE SCHEMA IF NOT EXISTS settle;

-- ============================================================================
-- TABLE 1: settle_contributions
-- Purpose: Store anonymous settlement data contributions
-- Compliance: Zero PHI, all drop-downs, bucketed amounts
-- ============================================================================
CREATE TABLE IF NOT EXISTS settle_contributions (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- ========================================================================
    -- STEP 1: VENUE & CASE TYPE
    -- ========================================================================
    jurisdiction TEXT NOT NULL,                     -- e.g., "Maricopa County, AZ"
    case_type TEXT NOT NULL,                        -- drop-down: "Motor Vehicle Accident", etc.
    
    -- ========================================================================
    -- STEP 2: INJURY & TREATMENT SNAPSHOT
    -- ========================================================================
    injury_category TEXT[] NOT NULL,                -- multi-select: ["Spinal Injury", "Traumatic Brain Injury"]
    primary_diagnosis TEXT,                         -- drop-down: 120+ ICD-10 categories (generic only)
    treatment_type TEXT[],                          -- multi-select: ["Surgery", "Physical Therapy"]
    duration_of_treatment TEXT,                     -- drop-down: "<3 months", "3-6 months", etc.
    imaging_findings TEXT[],                        -- multi-select: ["Fracture", "Herniated Disc"]
    
    -- ========================================================================
    -- STEP 3: FINANCIAL SNAPSHOT
    -- ========================================================================
    medical_bills NUMERIC NOT NULL,                 -- $ amount (free-form number)
    lost_wages NUMERIC,                             -- $ amount (optional)
    policy_limits TEXT,                             -- drop-down: "$15k/$30k", "$100k/$300k", etc.
    
    -- ========================================================================
    -- STEP 4: LIABILITY CONTEXT (BAR-SAFE VERSION)
    -- ========================================================================
    defendant_category TEXT NOT NULL,               -- drop-down: "Individual", "Business", "Government", "Unknown"
    
    -- ========================================================================
    -- STEP 5: OUTCOME (FOR DATA CONTRIBUTORS ONLY)
    -- ========================================================================
    outcome_type TEXT NOT NULL,                     -- drop-down: "Settlement", "Jury Verdict", etc.
    outcome_amount_range TEXT NOT NULL,            -- BUCKETED: "$0-$50k", "$50k-$100k", etc.
    
    -- ========================================================================
    -- COMPLIANCE & AUDIT FIELDS
    -- ========================================================================
    contributed_at TIMESTAMPTZ DEFAULT now(),
    blockchain_hash TEXT,                           -- OpenTimestamps receipt hash
    consent_confirmed BOOLEAN DEFAULT TRUE,         -- Pre-checked ethics toggle
    
    -- ========================================================================
    -- CONTRIBUTOR TRACKING (REFERENCES CENTRAL users TABLE)
    -- ========================================================================
    contributor_user_id UUID,                       -- References users.user_id from SaaS Admin
    -- Note: NOT creating foreign key constraint to allow cross-database flexibility
    founding_member BOOLEAN DEFAULT FALSE,          -- True if contributor is Founding Member
    
    -- ========================================================================
    -- METADATA
    -- ========================================================================
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    status TEXT DEFAULT 'pending',                  -- 'pending', 'approved', 'rejected', 'flagged'
    rejection_reason TEXT,                          -- If rejected, why?
    
    -- ========================================================================
    -- DATA QUALITY FLAGS
    -- ========================================================================
    is_outlier BOOLEAN DEFAULT FALSE,               -- Flagged for manual review
    confidence_score NUMERIC DEFAULT 1.0,           -- 0.0-1.0 (data quality score)
    
    -- Constraints
    CONSTRAINT valid_outcome_range CHECK (
        outcome_amount_range IN (
            '$0-$50k', '$50k-$100k', '$100k-$150k', '$150k-$225k',
            '$225k-$300k', '$300k-$600k', '$600k-$1M', '$1M+'
        )
    ),
    CONSTRAINT valid_status CHECK (
        status IN ('pending', 'approved', 'rejected', 'flagged')
    ),
    CONSTRAINT valid_medical_bills CHECK (medical_bills >= 0 AND medical_bills <= 10000000),
    CONSTRAINT valid_confidence_score CHECK (confidence_score >= 0 AND confidence_score <= 1)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_settle_contributions_jurisdiction ON settle_contributions(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_settle_contributions_case_type ON settle_contributions(case_type);
CREATE INDEX IF NOT EXISTS idx_settle_contributions_injury_category ON settle_contributions USING GIN(injury_category);
CREATE INDEX IF NOT EXISTS idx_settle_contributions_outcome_range ON settle_contributions(outcome_amount_range);
CREATE INDEX IF NOT EXISTS idx_settle_contributions_status ON settle_contributions(status);
CREATE INDEX IF NOT EXISTS idx_settle_contributions_created_at ON settle_contributions(created_at);
CREATE INDEX IF NOT EXISTS idx_settle_contributions_medical_bills ON settle_contributions(medical_bills);
CREATE INDEX IF NOT EXISTS idx_settle_contributions_contributor ON settle_contributions(contributor_user_id);

-- Composite index for common query pattern
CREATE INDEX IF NOT EXISTS idx_settle_contributions_query_pattern 
ON settle_contributions(jurisdiction, case_type, status) 
WHERE status = 'approved';

-- ============================================================================
-- TABLE 2: settle_api_keys
-- Purpose: API key management and access control
-- ============================================================================
CREATE TABLE IF NOT EXISTS settle_api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- API Key
    api_key_hash TEXT UNIQUE NOT NULL,              -- Hashed API key (SHA-256)
    api_key_prefix TEXT NOT NULL,                   -- First 8 chars for display
    
    -- Access Level
    access_level TEXT NOT NULL,                     -- 'founding_member', 'standard', 'premium', 'admin', 'external'
    
    -- User Information (references central users table)
    user_id UUID,                                   -- References users.user_id from SaaS Admin
    user_email TEXT,                                -- Email (cached for convenience)
    law_firm_name TEXT,                             -- Law firm name
    
    -- Usage Tracking
    requests_used INT DEFAULT 0,
    requests_limit INT,                             -- NULL = unlimited (founding members)
    last_used_at TIMESTAMPTZ,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,                         -- NULL = never expires
    
    -- Metadata
    notes TEXT,
    
    -- Constraints
    CONSTRAINT valid_access_level CHECK (
        access_level IN ('founding_member', 'standard', 'premium', 'admin', 'external')
    ),
    CONSTRAINT valid_requests_used CHECK (requests_used >= 0),
    CONSTRAINT valid_requests_limit CHECK (requests_limit IS NULL OR requests_limit > 0)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_settle_api_keys_level ON settle_api_keys(access_level);
CREATE INDEX IF NOT EXISTS idx_settle_api_keys_active ON settle_api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_settle_api_keys_prefix ON settle_api_keys(api_key_prefix);
CREATE INDEX IF NOT EXISTS idx_settle_api_keys_user ON settle_api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_settle_api_keys_email ON settle_api_keys(user_email);

-- ============================================================================
-- TABLE 3: settle_founding_members
-- Purpose: Track Founding Member program (2,100 attorneys, free forever)
-- ============================================================================
CREATE TABLE IF NOT EXISTS settle_founding_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Member Information (references central users table)
    user_id UUID,                                   -- References users.user_id from SaaS Admin
    email TEXT UNIQUE NOT NULL,
    law_firm_name TEXT NOT NULL,
    bar_number TEXT,                                -- State bar number (optional)
    state TEXT NOT NULL,                            -- State of practice
    
    -- API Key
    api_key_id UUID REFERENCES settle_api_keys(id) ON DELETE SET NULL,
    
    -- Status
    status TEXT DEFAULT 'active',                   -- 'active', 'inactive', 'revoked'
    joined_at TIMESTAMPTZ DEFAULT now(),
    
    -- Contribution Stats
    contributions_count INT DEFAULT 0,
    queries_count INT DEFAULT 0,
    reports_generated INT DEFAULT 0,
    
    -- Metadata
    referral_source TEXT,                           -- How they found us
    notes TEXT,
    
    -- Constraints
    CONSTRAINT valid_founding_member_status CHECK (
        status IN ('active', 'inactive', 'revoked')
    ),
    CONSTRAINT valid_contributions_count CHECK (contributions_count >= 0),
    CONSTRAINT valid_queries_count CHECK (queries_count >= 0),
    CONSTRAINT valid_reports_generated CHECK (reports_generated >= 0)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_settle_founding_members_email ON settle_founding_members(email);
CREATE INDEX IF NOT EXISTS idx_settle_founding_members_status ON settle_founding_members(status);
CREATE INDEX IF NOT EXISTS idx_settle_founding_members_joined ON settle_founding_members(joined_at);
CREATE INDEX IF NOT EXISTS idx_settle_founding_members_user ON settle_founding_members(user_id);
CREATE INDEX IF NOT EXISTS idx_settle_founding_members_api_key ON settle_founding_members(api_key_id);

-- ============================================================================
-- TABLE 4: settle_queries
-- Purpose: Track settlement range queries (analytics)
-- ============================================================================
CREATE TABLE IF NOT EXISTS settle_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Query Parameters
    injury_type TEXT NOT NULL,
    state TEXT NOT NULL,
    county TEXT,
    medical_bills NUMERIC,
    
    -- Results
    percentile_25 NUMERIC,
    median NUMERIC,
    percentile_75 NUMERIC,
    percentile_95 NUMERIC,
    n_cases INT,
    confidence TEXT,                                -- 'low', 'medium', 'high'
    
    -- API Key (for usage tracking)
    api_key_id UUID REFERENCES settle_api_keys(id) ON DELETE SET NULL,
    
    -- Metadata
    queried_at TIMESTAMPTZ DEFAULT now(),
    response_time_ms INT,                           -- Performance tracking
    
    -- Constraints
    CONSTRAINT valid_confidence CHECK (
        confidence IN ('low', 'medium', 'high')
    ),
    CONSTRAINT valid_response_time CHECK (response_time_ms >= 0)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_settle_queries_injury ON settle_queries(injury_type);
CREATE INDEX IF NOT EXISTS idx_settle_queries_state ON settle_queries(state);
CREATE INDEX IF NOT EXISTS idx_settle_queries_queried_at ON settle_queries(queried_at);
CREATE INDEX IF NOT EXISTS idx_settle_queries_api_key ON settle_queries(api_key_id);

-- ============================================================================
-- TABLE 5: settle_reports
-- Purpose: Track generated SETTLE reports
-- ============================================================================
CREATE TABLE IF NOT EXISTS settle_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Report Details
    query_id UUID REFERENCES settle_queries(id) ON DELETE SET NULL,
    report_url TEXT,
    ots_hash TEXT,                                  -- OpenTimestamps hash
    format TEXT DEFAULT 'pdf',                      -- 'pdf', 'json', 'html'
    
    -- API Key (for billing)
    api_key_id UUID REFERENCES settle_api_keys(id) ON DELETE SET NULL,
    
    -- Metadata
    generated_at TIMESTAMPTZ DEFAULT now(),
    downloaded_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT valid_format CHECK (
        format IN ('pdf', 'json', 'html')
    )
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_settle_reports_query ON settle_reports(query_id);
CREATE INDEX IF NOT EXISTS idx_settle_reports_api_key ON settle_reports(api_key_id);
CREATE INDEX IF NOT EXISTS idx_settle_reports_generated ON settle_reports(generated_at);

-- ============================================================================
-- TABLE 6: settle_waitlist
-- Purpose: Pre-launch waitlist for non-customers
-- ============================================================================
CREATE TABLE IF NOT EXISTS settle_waitlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Contact Information
    email TEXT UNIQUE NOT NULL,
    law_firm_name TEXT,
    practice_area TEXT,
    state TEXT,
    
    -- Status
    status TEXT DEFAULT 'pending',                  -- 'pending', 'approved', 'invited', 'converted'
    
    -- Metadata
    joined_at TIMESTAMPTZ DEFAULT now(),
    invited_at TIMESTAMPTZ,
    converted_at TIMESTAMPTZ,
    referral_source TEXT,
    notes TEXT,
    
    -- Constraints
    CONSTRAINT valid_waitlist_status CHECK (
        status IN ('pending', 'approved', 'invited', 'converted')
    ),
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_settle_waitlist_email ON settle_waitlist(email);
CREATE INDEX IF NOT EXISTS idx_settle_waitlist_status ON settle_waitlist(status);
CREATE INDEX IF NOT EXISTS idx_settle_waitlist_joined ON settle_waitlist(joined_at);

-- ============================================================================
-- VIEWS FOR ANALYTICS
-- ============================================================================

-- View: Approved contributions only (for queries)
CREATE OR REPLACE VIEW settle_approved_contributions AS
SELECT * FROM settle_contributions
WHERE status = 'approved';

-- View: Founding member statistics
CREATE OR REPLACE VIEW settle_founding_member_stats AS
SELECT
    COUNT(*) as total_members,
    COUNT(*) FILTER (WHERE status = 'active') as active_members,
    SUM(contributions_count) as total_contributions,
    SUM(queries_count) as total_queries,
    SUM(reports_generated) as total_reports
FROM settle_founding_members;

-- View: API usage by access level
CREATE OR REPLACE VIEW settle_api_usage_by_level AS
SELECT
    access_level,
    COUNT(*) as total_keys,
    COUNT(*) FILTER (WHERE is_active = TRUE) as active_keys,
    SUM(requests_used) as total_requests
FROM settle_api_keys
GROUP BY access_level;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function: Update updated_at timestamp
CREATE OR REPLACE FUNCTION settle_update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto-update updated_at on settle_contributions
DROP TRIGGER IF EXISTS update_settle_contributions_updated_at ON settle_contributions;
CREATE TRIGGER update_settle_contributions_updated_at
    BEFORE UPDATE ON settle_contributions
    FOR EACH ROW
    EXECUTE FUNCTION settle_update_updated_at_column();

-- ============================================================================
-- ROW-LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on sensitive tables
ALTER TABLE settle_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE settle_founding_members ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (prevents errors on re-run)
DROP POLICY IF EXISTS "Service role has full access to settle_api_keys" ON settle_api_keys;
DROP POLICY IF EXISTS "Service role has full access to settle_founding_members" ON settle_founding_members;
DROP POLICY IF EXISTS "Users can read their own API key info" ON settle_api_keys;

-- Policy: Service role has full access
CREATE POLICY "Service role has full access to settle_api_keys"
ON settle_api_keys
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "Service role has full access to settle_founding_members"
ON settle_founding_members
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Policy: API keys can read their own info
CREATE POLICY "Users can read their own API key info"
ON settle_api_keys
FOR SELECT
TO authenticated
USING (user_email = auth.jwt() ->> 'email');

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE settle_contributions IS 'Anonymous settlement data contributions (zero PHI, bar-compliant)';
COMMENT ON TABLE settle_api_keys IS 'API key management for SETTLE service access control';
COMMENT ON TABLE settle_founding_members IS 'Founding Member program tracking (2,100 attorneys, free forever)';
COMMENT ON TABLE settle_queries IS 'Settlement range query tracking for analytics and billing';
COMMENT ON TABLE settle_reports IS 'Generated SETTLE reports (4-page PDF/JSON/HTML)';
COMMENT ON TABLE settle_waitlist IS 'Pre-launch waitlist for non-customer attorneys';

COMMENT ON COLUMN settle_contributions.contributor_user_id IS 'References users.user_id from central SaaS Admin users table';
COMMENT ON COLUMN settle_contributions.outcome_amount_range IS 'Bucketed ranges: $0-$50k, $50k-$100k, $100k-$150k, $150k-$225k, $225k-$300k, $300k-$600k, $600k-$1M, $1M+';
COMMENT ON COLUMN settle_api_keys.user_id IS 'References users.user_id from central SaaS Admin users table';

-- ============================================================================
-- SAMPLE DATA (for testing)
-- ============================================================================

-- Insert sample API key (admin key for testing)
INSERT INTO settle_api_keys (
    api_key_hash, 
    api_key_prefix, 
    access_level, 
    user_email, 
    law_firm_name,
    requests_limit,
    is_active
) VALUES (
    'sample_hashed_key_for_testing_only',
    'test1234',
    'admin',
    'admin@truevow.law',
    'TrueVow Internal',
    NULL,  -- Unlimited
    TRUE
) ON CONFLICT DO NOTHING;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

-- Success message
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'SETTLE Service Schema Created Successfully!';
    RAISE NOTICE '============================================================================';
    RAISE NOTICE 'Tables Created:';
    RAISE NOTICE '  1. settle_contributions (with indexes)';
    RAISE NOTICE '  2. settle_api_keys (with RLS)';
    RAISE NOTICE '  3. settle_founding_members (with RLS)';
    RAISE NOTICE '  4. settle_queries';
    RAISE NOTICE '  5. settle_reports';
    RAISE NOTICE '  6. settle_waitlist';
    RAISE NOTICE '';
    RAISE NOTICE 'Views Created:';
    RAISE NOTICE '  - settle_approved_contributions';
    RAISE NOTICE '  - settle_founding_member_stats';
    RAISE NOTICE '  - settle_api_usage_by_level';
    RAISE NOTICE '';
    RAISE NOTICE 'Next Steps:';
    RAISE NOTICE '  1. Run: SELECT * FROM settle_founding_member_stats;';
    RAISE NOTICE '  2. Generate API keys using app/core/security.py';
    RAISE NOTICE '  3. Start SETTLE service: uvicorn app.main:app --reload';
    RAISE NOTICE '============================================================================';
END $$;

