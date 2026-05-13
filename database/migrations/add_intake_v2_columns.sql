-- =============================================================================
-- Year-2 Mandatory 8-field Intake — schema migration
-- =============================================================================
-- Additive only. Existing rows remain valid and are tagged intake_version_id='v1'
-- by the cds_settle_ingest backfill. New /submit traffic writes rows with
-- intake_version_id='v2', which MUST populate every field below.
--
-- The CHECK constraint is version-scoped: legacy v1 rows may carry NULL in the
-- v2 columns; only rows with intake_version_id='v2' are enforced.
--
-- Reference: plans/Year-2_Guardrails_Resume_6027ecaa.md, Task C.3
-- =============================================================================

ALTER TABLE settle_contributions
    ADD COLUMN IF NOT EXISTS intake_version_id TEXT,
    ADD COLUMN IF NOT EXISTS economic_strength_at_intake TEXT,
    ADD COLUMN IF NOT EXISTS final_treatment_escalation TEXT,
    ADD COLUMN IF NOT EXISTS settlement_band TEXT,
    ADD COLUMN IF NOT EXISTS policy_limit_known BOOLEAN,
    ADD COLUMN IF NOT EXISTS time_to_resolution TEXT,
    ADD COLUMN IF NOT EXISTS litigation_filed BOOLEAN;

-- Version-scoped completeness check.
-- Legacy rows (intake_version_id IS NULL OR != 'v2') pass unconditionally.
-- v2 rows MUST populate every field with a valid enum value.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'v2_intake_complete'
    ) THEN
        ALTER TABLE settle_contributions
            ADD CONSTRAINT v2_intake_complete CHECK (
                intake_version_id IS DISTINCT FROM 'v2'
                OR (
                    economic_strength_at_intake IN ('weak','moderate','strong')
                    AND final_treatment_escalation IN (
                        'none','pt_only','injections','surgery_consult','surgery_performed'
                    )
                    AND settlement_band IN (
                        'under_50k','50k_150k','150k_500k','500k_1m','over_1m'
                    )
                    AND policy_limit_known IS NOT NULL
                    AND time_to_resolution IN (
                        'lt_6_months','6_12_months','12_24_months','gt_24_months'
                    )
                    AND litigation_filed IS NOT NULL
                )
            );
    END IF;
END$$;

-- Index used by IntelligenceGate and admin reporting to segment v1 vs v2 cohorts.
CREATE INDEX IF NOT EXISTS idx_settle_contrib_intake_version
    ON settle_contributions(intake_version_id);

-- -----------------------------------------------------------------------------
-- Backfill legacy rows to 'v1'. Safe to re-run.
-- -----------------------------------------------------------------------------
UPDATE settle_contributions
   SET intake_version_id = 'v1'
 WHERE intake_version_id IS NULL;
