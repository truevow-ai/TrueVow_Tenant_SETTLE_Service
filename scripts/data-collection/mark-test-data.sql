-- Mark Synthetic Test Data in Database
-- Run this SQL in Supabase SQL Editor to mark test data

UPDATE settle_contributions 
SET 
    status = 'flagged',
    rejection_reason = 'SYNTHETIC TEST DATA - NOT REAL COURT RECORDS - DO NOT USE FOR PRODUCTION',
    is_outlier = TRUE,
    confidence_score = 0.0
WHERE 
    case_type LIKE '%SAMPLE%' 
    OR collector_notes LIKE '%Research-based sample%'
    OR case_reference LIKE '%SAMPLE%';

-- Add a comment to the table
COMMENT ON TABLE settle_contributions IS 
'Contains test data. Synthetic cases marked with status=flagged. Replace with verified court records for production use.';

-- Verify the update
SELECT 
    COUNT(*) as total_cases,
    COUNT(*) FILTER (WHERE status = 'flagged') as test_data_cases,
    COUNT(*) FILTER (WHERE status != 'flagged') as real_cases
FROM settle_contributions;

