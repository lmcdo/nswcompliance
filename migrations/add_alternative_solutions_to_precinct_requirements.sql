-- Migration: Add alternative solutions fields to precinct requirements table
-- Date: 2025-11-02
-- Purpose: Enable Heritage Intelligence "Design Flexibility Pathways" feature

BEGIN;

-- Add alternative solutions fields
ALTER TABLE dcp_precinct_requirements
ADD COLUMN IF NOT EXISTS allows_alternative_solutions BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS alternative_solutions_criteria TEXT;

-- Add indexes for performance (only index TRUE values for efficiency)
CREATE INDEX IF NOT EXISTS idx_precinct_alt_solutions
ON dcp_precinct_requirements(allows_alternative_solutions)
WHERE allows_alternative_solutions = TRUE;

-- Verify addition
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'dcp_precinct_requirements'
AND column_name LIKE '%alternative%'
ORDER BY ordinal_position;

COMMIT;

-- Success message
\echo 'Migration complete: Alternative solutions fields added to dcp_precinct_requirements'
