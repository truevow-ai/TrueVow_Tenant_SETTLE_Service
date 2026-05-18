-- ============================================================================
-- SETTLE Migrations: Rich Fields + Reputation & Anomaly Detection
-- Generated: 2026-05-18
-- Applies on top of: ed2900358f69
-- Target revision: b2c3d4e5f6a7
-- ============================================================================
-- Run this entire file in the Supabase SQL Editor.
-- ============================================================================

BEGIN;

-- ============================================================================
-- Migration 1: Rich Fields (a1b2c3d4e5f6)
-- ============================================================================

-- Tier 1 — High impact on estimate quality
ALTER TABLE settle_contributions ADD COLUMN insurance_carrier TEXT;
ALTER TABLE settle_contributions ADD COLUMN comparative_negligence_pct NUMERIC;
ALTER TABLE settle_contributions ADD COLUMN exact_outcome_amount NUMERIC;
ALTER TABLE settle_contributions ADD COLUMN is_verdict BOOLEAN;
ALTER TABLE settle_contributions ADD COLUMN date_of_verdict TIMESTAMPTZ;

-- Tier 2 — Useful for filtering/display
ALTER TABLE settle_contributions ADD COLUMN court_level TEXT;
ALTER TABLE settle_contributions ADD COLUMN injury_severity TEXT;
ALTER TABLE settle_contributions ADD COLUMN policy_limit_amount NUMERIC;
ALTER TABLE settle_contributions ADD COLUMN source_type TEXT;

-- Tier 3 — Nice-to-have
ALTER TABLE settle_contributions ADD COLUMN trial_duration_days INTEGER;
ALTER TABLE settle_contributions ADD COLUMN appeal_filed BOOLEAN;
ALTER TABLE settle_contributions ADD COLUMN appeal_outcome TEXT;

-- Indexes
CREATE INDEX idx_settle_contributions_insurance_carrier ON settle_contributions (insurance_carrier);
CREATE INDEX idx_settle_contributions_source_type ON settle_contributions (source_type);
CREATE INDEX idx_settle_contributions_injury_severity ON settle_contributions (injury_severity);
CREATE INDEX idx_settle_contributions_is_verdict ON settle_contributions (is_verdict);
CREATE INDEX idx_settle_contributions_date_of_verdict ON settle_contributions (date_of_verdict);

-- Check constraints
ALTER TABLE settle_contributions ADD CONSTRAINT valid_source_type
    CHECK (source_type IS NULL OR source_type IN ('firm_submission', 'scraped_verdict', 'news_report', 'court_docket', 'settlement_survey'));

ALTER TABLE settle_contributions ADD CONSTRAINT valid_court_level
    CHECK (court_level IS NULL OR court_level IN ('circuit', 'federal_district', 'federal_appellate', 'state_appellate', 'arbitration', 'mediation'));

ALTER TABLE settle_contributions ADD CONSTRAINT valid_injury_severity
    CHECK (injury_severity IS NULL OR injury_severity IN ('soft_tissue', 'fracture', 'surgical', 'catastrophic', 'fatal'));

ALTER TABLE settle_contributions ADD CONSTRAINT valid_appeal_outcome
    CHECK (appeal_outcome IS NULL OR appeal_outcome IN ('affirmed', 'reversed', 'remanded', 'settled', 'dismissed', 'pending'));

ALTER TABLE settle_contributions ADD CONSTRAINT valid_comparative_negligence_pct
    CHECK (comparative_negligence_pct IS NULL OR (comparative_negligence_pct >= 0 AND comparative_negligence_pct <= 100));

ALTER TABLE settle_contributions ADD CONSTRAINT valid_exact_outcome_amount
    CHECK (exact_outcome_amount IS NULL OR (exact_outcome_amount >= 0 AND exact_outcome_amount <= 100000000));

ALTER TABLE settle_contributions ADD CONSTRAINT valid_policy_limit_amount
    CHECK (policy_limit_amount IS NULL OR (policy_limit_amount >= 0 AND policy_limit_amount <= 100000000));

ALTER TABLE settle_contributions ADD CONSTRAINT valid_trial_duration_days
    CHECK (trial_duration_days IS NULL OR (trial_duration_days >= 0 AND trial_duration_days <= 3650));

-- ============================================================================
-- Migration 2: Reputation & Anomaly Detection (b2c3d4e5f6a7)
-- ============================================================================

-- Table: settle_contribution_reputation
CREATE TABLE settle_contribution_reputation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contributor_user_id UUID NOT NULL,
    reputation_score NUMERIC NOT NULL DEFAULT 0.0,
    tier TEXT NOT NULL DEFAULT 'unverified',
    total_submissions INT NOT NULL DEFAULT 0,
    approved_submissions INT NOT NULL DEFAULT 0,
    rejected_submissions INT NOT NULL DEFAULT 0,
    flagged_submissions INT NOT NULL DEFAULT 0,
    average_z_score NUMERIC,
    last_submission_at TIMESTAMPTZ,
    last_reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_reputation_contributor UNIQUE (contributor_user_id),
    CONSTRAINT valid_reputation_score CHECK (reputation_score >= 0 AND reputation_score <= 1),
    CONSTRAINT valid_reputation_tier CHECK (tier IN ('unverified', 'probationary', 'trusted', 'founding')),
    CONSTRAINT valid_reputation_submissions CHECK (total_submissions >= 0 AND approved_submissions >= 0 AND rejected_submissions >= 0 AND flagged_submissions >= 0)
);

CREATE INDEX idx_reputation_user_id ON settle_contribution_reputation (contributor_user_id);
CREATE INDEX idx_reputation_tier ON settle_contribution_reputation (tier);
CREATE INDEX idx_reputation_score ON settle_contribution_reputation (reputation_score);

COMMENT ON TABLE settle_contribution_reputation IS 'Per-attorney reputation scores for contribution weighting. Scores affect estimate calculation and submission review requirements.';

-- Table: settle_anomaly_flags
CREATE TABLE settle_anomaly_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contribution_id UUID REFERENCES settle_contributions(id) ON DELETE CASCADE NOT NULL,
    flag_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    z_score NUMERIC,
    details JSONB,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_by UUID,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_anomaly_severity CHECK (severity IN ('warning', 'critical'))
);

CREATE INDEX idx_anomaly_flags_contribution ON settle_anomaly_flags (contribution_id);
CREATE INDEX idx_anomaly_flags_severity ON settle_anomaly_flags (severity);
CREATE INDEX idx_anomaly_flags_unresolved ON settle_anomaly_flags (resolved) WHERE resolved = FALSE;

COMMENT ON TABLE settle_anomaly_flags IS 'Anomaly detection flags for individual contributions. Used for admin review and automated reputation scoring.';

-- Columns on settle_contributions for reputation integration
ALTER TABLE settle_contributions ADD COLUMN contributor_reputation_score NUMERIC DEFAULT 0.0;
ALTER TABLE settle_contributions ADD COLUMN anomaly_flags JSONB DEFAULT '[]'::jsonb;
ALTER TABLE settle_contributions ADD COLUMN submission_quality_weight NUMERIC DEFAULT 1.0;
ALTER TABLE settle_contributions ADD COLUMN contributor_user_id UUID;

CREATE INDEX idx_settle_contributions_reputation ON settle_contributions (contributor_reputation_score);
CREATE INDEX idx_settle_contributions_contributor_user_id ON settle_contributions (contributor_user_id);

-- ============================================================================
-- Update alembic_version to the latest migration
-- ============================================================================

-- Create alembic_version table if it doesn't exist (it should, but just in case)
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL
);

-- Update to latest revision
DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('c3d4e5f6a7b8');

COMMIT;
