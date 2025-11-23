-- Migration: Add precinct_number column to both tables for proper JOIN
-- Date: 2025-11-01
-- Purpose: Fix precinct requirements not showing due to schema mismatch

-- Step 1: Add precinct_number column to dcp_precinct_boundaries
ALTER TABLE dcp_precinct_boundaries
ADD COLUMN IF NOT EXISTS precinct_number TEXT;

-- Step 2: Populate precinct_number by extracting from precinct_name
-- Pattern: "... Precinct 40" → "40"
UPDATE dcp_precinct_boundaries
SET precinct_number = (
    SELECT (regexp_matches(precinct_name, 'Precinct\s+(\d+)', 'i'))[1]
)
WHERE precinct_name ~* 'Precinct\s+\d+';

-- Step 3: For precincts without "Precinct XX" pattern, use a fallback
-- (e.g., "Ashfield Town Centre" → extract from precinct_id if possible)
-- For now, leave NULL for non-numbered precincts

-- Step 4: Add precinct_number column to dcp_precinct_requirements
ALTER TABLE dcp_precinct_requirements
ADD COLUMN IF NOT EXISTS precinct_number TEXT;

-- Step 5: Populate precinct_number by stripping underscore from precinct_id
-- Pattern: "40_" → "40"
UPDATE dcp_precinct_requirements
SET precinct_number = REGEXP_REPLACE(precinct_id, '_', '', 'g')
WHERE precinct_id IS NOT NULL;

-- Step 6: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_precinct_boundaries_number
ON dcp_precinct_boundaries(precinct_number);

CREATE INDEX IF NOT EXISTS idx_precinct_requirements_number
ON dcp_precinct_requirements(precinct_number);

-- Step 7: Verify the migration
DO $$
DECLARE
    boundary_populated INTEGER;
    requirement_populated INTEGER;
    matching_count INTEGER;
BEGIN
    -- Check population rates
    SELECT COUNT(*) FILTER (WHERE precinct_number IS NOT NULL)
    INTO boundary_populated
    FROM dcp_precinct_boundaries;

    SELECT COUNT(*) FILTER (WHERE precinct_number IS NOT NULL)
    INTO requirement_populated
    FROM dcp_precinct_requirements;

    -- Check matching count
    SELECT COUNT(DISTINCT b.precinct_number)
    INTO matching_count
    FROM dcp_precinct_boundaries b
    INNER JOIN dcp_precinct_requirements r ON b.precinct_number = r.precinct_number
    WHERE b.precinct_number IS NOT NULL;

    RAISE NOTICE 'Migration Complete:';
    RAISE NOTICE '  Boundaries with precinct_number: %', boundary_populated;
    RAISE NOTICE '  Requirements with precinct_number: %', requirement_populated;
    RAISE NOTICE '  Matching precincts (JOIN works): %', matching_count;
END $$;
