-- =============================================================================
-- Add Audit Columns Migration
-- Date: 2026-03-02
-- Purpose: Add soft-delete and lifecycle audit columns per TrueVow standards
-- =============================================================================

-- =============================================================================
-- STEP 1: settle_contributions table
-- =============================================================================

-- Add soft-delete columns
ALTER TABLE settle_contributions
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS deleted_by UUID;

-- Add audit trail columns
ALTER TABLE settle_contributions
ADD COLUMN IF NOT EXISTS created_by UUID,
ADD COLUMN IF NOT EXISTS updated_by UUID;

-- Add index on deleted_at for soft-delete queries
CREATE INDEX IF NOT EXISTS idx_settle_contributions_deleted_at 
ON settle_contributions(deleted_at) 
WHERE deleted_at IS NULL;

-- Add index on deleted_by
CREATE INDEX IF NOT EXISTS idx_settle_contributions_deleted_by 
ON settle_contributions(deleted_by);

-- =============================================================================
-- STEP 2: settle_api_keys table
-- =============================================================================

-- Add soft-delete columns
ALTER TABLE settle_api_keys
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS deleted_by UUID;

-- Add audit trail columns
ALTER TABLE settle_api_keys
ADD COLUMN IF NOT EXISTS created_by UUID,
ADD COLUMN IF NOT EXISTS updated_by UUID;

-- Add index on deleted_at
CREATE INDEX IF NOT EXISTS idx_settle_api_keys_deleted_at 
ON settle_api_keys(deleted_at) 
WHERE deleted_at IS NULL;

-- Add index on deleted_by
CREATE INDEX IF NOT EXISTS idx_settle_api_keys_deleted_by 
ON settle_api_keys(deleted_by);

-- =============================================================================
-- STEP 3: settle_queries table (if exists)
-- =============================================================================

-- Check if table exists before adding columns
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'settle_queries') THEN
        -- Add soft-delete columns
        ALTER TABLE settle_queries
        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS deleted_by UUID;

        -- Add audit trail columns
        ALTER TABLE settle_queries
        ADD COLUMN IF NOT EXISTS created_by UUID,
        ADD COLUMN IF NOT EXISTS updated_by UUID;

        -- Add indexes
        CREATE INDEX IF NOT EXISTS idx_settle_queries_deleted_at 
        ON settle_queries(deleted_at) 
        WHERE deleted_at IS NULL;
        
        CREATE INDEX IF NOT EXISTS idx_settle_queries_deleted_by 
        ON settle_queries(deleted_by);
    END IF;
END $$;

-- =============================================================================
-- STEP 4: settle_reports table (if exists)
-- =============================================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'settle_reports') THEN
        ALTER TABLE settle_reports
        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
        ADD COLUMN IF NOT EXISTS deleted_by UUID;

        ALTER TABLE settle_reports
        ADD COLUMN IF NOT EXISTS created_by UUID,
        ADD COLUMN IF NOT EXISTS updated_by UUID;

        CREATE INDEX IF NOT EXISTS idx_settle_reports_deleted_at 
        ON settle_reports(deleted_at) 
        WHERE deleted_at IS NULL;
        
        CREATE INDEX IF NOT EXISTS idx_settle_reports_deleted_by 
        ON settle_reports(deleted_by);
    END IF;
END $$;

-- =============================================================================
-- STEP 5: Update trigger for updated_at (ensure it exists on all tables)
-- =============================================================================

-- Function to update updated_at (if not exists)
CREATE OR REPLACE FUNCTION settle_update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to settle_contributions (if not already applied)
DROP TRIGGER IF EXISTS update_settle_contributions_updated_at ON settle_contributions;
CREATE TRIGGER update_settle_contributions_updated_at
    BEFORE UPDATE ON settle_contributions
    FOR EACH ROW
    EXECUTE FUNCTION settle_update_updated_at_column();

-- Apply to settle_api_keys
DROP TRIGGER IF EXISTS update_settle_api_keys_updated_at ON settle_api_keys;
CREATE TRIGGER update_settle_api_keys_updated_at
    BEFORE UPDATE ON settle_api_keys
    FOR EACH ROW
    EXECUTE FUNCTION settle_update_updated_at_column();

-- =============================================================================
-- STEP 6: Add row_version for optimistic locking (optional enhancement)
-- =============================================================================

ALTER TABLE settle_contributions
ADD COLUMN IF NOT EXISTS row_version INTEGER NOT NULL DEFAULT 1;

ALTER TABLE settle_api_keys
ADD COLUMN IF NOT EXISTS row_version INTEGER NOT NULL DEFAULT 1;

-- =============================================================================
-- Comments for documentation
-- =============================================================================

COMMENT ON COLUMN settle_contributions.deleted_at IS 'Soft-delete timestamp - row hidden when not NULL';
COMMENT ON COLUMN settle_contributions.deleted_by IS 'UUID of user who soft-deleted the row';
COMMENT ON COLUMN settle_contributions.created_by IS 'UUID of user who created the row';
COMMENT ON COLUMN settle_contributions.updated_by IS 'UUID of user who last updated the row';
COMMENT ON COLUMN settle_contributions.row_version IS 'Optimistic locking version - increment on each update';

COMMENT ON COLUMN settle_api_keys.deleted_at IS 'Soft-delete timestamp - row hidden when not NULL';
COMMENT ON COLUMN settle_api_keys.deleted_by IS 'UUID of user who soft-deleted the row';
COMMENT ON COLUMN settle_api_keys.created_by IS 'UUID of user who created the row';
COMMENT ON COLUMN settle_api_keys.updated_by IS 'UUID of user who last updated the row';
COMMENT ON COLUMN settle_api_keys.row_version IS 'Optimistic locking version - increment on each update';
