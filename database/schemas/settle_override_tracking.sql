-- ============================================================================
-- TrueVow SETTLE™ Service - Override Tracking Schema (Phase 3.3)
-- ============================================================================
-- Purpose: Track when actual settlements differ from estimates
-- Used for: Learning from overrides, improving estimates over time
-- ============================================================================

CREATE TABLE IF NOT EXISTS settle_estimate_overrides (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Link to original query and contribution
    query_id UUID,                                    -- References settle_queries(id)
    contribution_id UUID,                             -- References settle_contributions(id)

    -- Estimate vs Actual
    estimate_median DECIMAL,                          -- Median estimate at time of query
    actual_outcome DECIMAL,                           -- Actual settlement amount
    delta_pct DECIMAL,                                -- Percentage difference
    delta_direction TEXT,                             -- 'above' or 'below'

    -- Context
    jurisdiction TEXT,
    case_type TEXT,
    injury_category TEXT[],
    medical_bills DECIMAL,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT now(),
    created_by UUID,                                  -- User who submitted the override

    CONSTRAINT valid_delta_direction CHECK (
        delta_direction IN ('above', 'below')
    )
);

CREATE INDEX IF NOT EXISTS idx_overrides_query ON settle_estimate_overrides(query_id);
CREATE INDEX IF NOT EXISTS idx_overrides_contribution ON settle_estimate_overrides(contribution_id);
CREATE INDEX IF NOT EXISTS idx_overrides_created_at ON settle_estimate_overrides(created_at);
CREATE INDEX IF NOT EXISTS idx_overrides_jurisdiction ON settle_estimate_overrides(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_overrides_case_type ON settle_estimate_overrides(case_type);

COMMENT ON TABLE settle_estimate_overrides IS 'Tracks estimate vs actual outcome deltas for learning';

DO $$
BEGIN
    RAISE NOTICE 'Override Tracking Schema Created Successfully!';
END $$;
