-- ============================================================================
-- SETTLE Migrations: Reputation & Anomaly Detection + contributor_user_id fix
-- Applies on top of: a1b2c3d4e5f6 (rich fields already applied)
-- Target revision: c3d4e5f6a7b8
-- ============================================================================
-- Run this entire file in the Supabase SQL Editor.
-- ============================================================================

BEGIN;

-- ============================================================================
-- Migration 2: Reputation & Anomaly Detection (b2c3d4e5f6a7)
-- ============================================================================

-- Table: settle_contribution_reputation
CREATE TABLE IF NOT EXISTS settle_contribution_reputation (
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

CREATE INDEX IF NOT EXISTS idx_reputation_user_id ON settle_contribution_reputation (contributor_user_id);
CREATE INDEX IF NOT EXISTS idx_reputation_tier ON settle_contribution_reputation (tier);
CREATE INDEX IF NOT EXISTS idx_reputation_score ON settle_contribution_reputation (reputation_score);

COMMENT ON TABLE settle_contribution_reputation IS 'Per-attorney reputation scores for contribution weighting. Scores affect estimate calculation and submission review requirements.';

-- Table: settle_anomaly_flags
CREATE TABLE IF NOT EXISTS settle_anomaly_flags (
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

CREATE INDEX IF NOT EXISTS idx_anomaly_flags_contribution ON settle_anomaly_flags (contribution_id);
CREATE INDEX IF NOT EXISTS idx_anomaly_flags_severity ON settle_anomaly_flags (severity);
CREATE INDEX IF NOT EXISTS idx_anomaly_flags_unresolved ON settle_anomaly_flags (resolved) WHERE resolved = FALSE;

COMMENT ON TABLE settle_anomaly_flags IS 'Anomaly detection flags for individual contributions. Used for admin review and automated reputation scoring.';

-- Columns on settle_contributions for reputation integration
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'settle_contributions' AND column_name = 'contributor_reputation_score') THEN
        ALTER TABLE settle_contributions ADD COLUMN contributor_reputation_score NUMERIC DEFAULT 0.0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'settle_contributions' AND column_name = 'anomaly_flags') THEN
        ALTER TABLE settle_contributions ADD COLUMN anomaly_flags JSONB DEFAULT '[]'::jsonb;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'settle_contributions' AND column_name = 'submission_quality_weight') THEN
        ALTER TABLE settle_contributions ADD COLUMN submission_quality_weight NUMERIC DEFAULT 1.0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'settle_contributions' AND column_name = 'contributor_user_id') THEN
        ALTER TABLE settle_contributions ADD COLUMN contributor_user_id UUID;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_settle_contributions_reputation ON settle_contributions (contributor_reputation_score);
CREATE INDEX IF NOT EXISTS idx_settle_contributions_contributor_user_id ON settle_contributions (contributor_user_id);

-- ============================================================================
-- Update alembic_version to the latest migration
-- ============================================================================

CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL
);

DELETE FROM alembic_version;
INSERT INTO alembic_version (version_num) VALUES ('c3d4e5f6a7b8');

COMMIT;
