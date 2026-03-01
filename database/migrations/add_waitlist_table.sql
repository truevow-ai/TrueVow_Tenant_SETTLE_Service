-- Migration: Update settle_waitlist table for new features
-- Purpose: Add new fields to support enhanced waitlist management
-- Date: 2025-12-24
-- Note: settle_waitlist table already exists in settle_supabase.sql

-- Add new columns to existing table
ALTER TABLE settle_waitlist 
    ADD COLUMN IF NOT EXISTS firm_name TEXT,
    ADD COLUMN IF NOT EXISTS contact_name TEXT,
    ADD COLUMN IF NOT EXISTS phone TEXT,
    ADD COLUMN IF NOT EXISTS practice_areas TEXT[],
    ADD COLUMN IF NOT EXISTS jurisdiction TEXT,
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reviewed_by TEXT;

-- Update existing columns to match new schema
-- Map law_firm_name to firm_name (copy data if exists)
UPDATE settle_waitlist 
SET firm_name = law_firm_name 
WHERE firm_name IS NULL AND law_firm_name IS NOT NULL;

-- Set default contact_name from email if not provided
UPDATE settle_waitlist 
SET contact_name = split_part(email, '@', 1) 
WHERE contact_name IS NULL;

-- Convert single practice_area to array
UPDATE settle_waitlist 
SET practice_areas = ARRAY[practice_area]::TEXT[]
WHERE practice_areas IS NULL AND practice_area IS NOT NULL;

-- Map state to jurisdiction
UPDATE settle_waitlist 
SET jurisdiction = state 
WHERE jurisdiction IS NULL AND state IS NOT NULL;

-- Update status constraint to include 'rejected'
ALTER TABLE settle_waitlist DROP CONSTRAINT IF EXISTS valid_waitlist_status;
ALTER TABLE settle_waitlist ADD CONSTRAINT valid_waitlist_status 
    CHECK (status IN ('pending', 'approved', 'invited', 'converted', 'rejected'));

-- Ensure NOT NULL constraints on key fields
ALTER TABLE settle_waitlist 
    ALTER COLUMN firm_name SET NOT NULL,
    ALTER COLUMN contact_name SET NOT NULL;

-- Add index on joined_at if not exists (this is the "created_at" equivalent)
CREATE INDEX IF NOT EXISTS idx_settle_waitlist_joined ON settle_waitlist(joined_at);

-- Comments
COMMENT ON COLUMN settle_waitlist.firm_name IS 'Law firm name';
COMMENT ON COLUMN settle_waitlist.contact_name IS 'Primary contact person name';
COMMENT ON COLUMN settle_waitlist.phone IS 'Contact phone number';
COMMENT ON COLUMN settle_waitlist.practice_areas IS 'Array of practice areas (e.g., Personal Injury, Medical Malpractice)';
COMMENT ON COLUMN settle_waitlist.jurisdiction IS 'State or jurisdiction';
COMMENT ON COLUMN settle_waitlist.reviewed_at IS 'Timestamp when entry was reviewed by admin';
COMMENT ON COLUMN settle_waitlist.reviewed_by IS 'Admin user who reviewed the entry';

-- Note: joined_at is used as "created_at" in this table

