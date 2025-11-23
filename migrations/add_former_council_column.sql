-- Migration: Add former_council filtering to dcp_general_requirements
-- Date: 2025-10-30
-- Purpose: Filter general provisions by former council boundary (Marrickville, Ashfield, Leichhardt)

-- Step 1: Create backup table
CREATE TABLE dcp_general_requirements_backup_20251030 AS
SELECT * FROM dcp_general_requirements;

-- Verify backup
SELECT COUNT(*) as backup_count FROM dcp_general_requirements_backup_20251030;

-- Step 2: Add former_council column (nullable initially)
ALTER TABLE dcp_general_requirements
ADD COLUMN former_council VARCHAR(50);

-- Step 3: Populate Marrickville data
UPDATE dcp_general_requirements
SET former_council = 'Marrickville'
WHERE part_number LIKE 'Section 2.%';

-- Verify Marrickville
SELECT former_council, COUNT(*)
FROM dcp_general_requirements
WHERE former_council = 'Marrickville'
GROUP BY former_council;

-- Step 4: Populate Ashfield data
UPDATE dcp_general_requirements
SET former_council = 'Ashfield'
WHERE dcp_chapter = 'F' OR part_number LIKE 'Chapter F%';

-- Verify Ashfield
SELECT former_council, COUNT(*)
FROM dcp_general_requirements
WHERE former_council = 'Ashfield'
GROUP BY former_council;

-- Step 5: Check for NULL values (should be 0)
SELECT COUNT(*) as null_count
FROM dcp_general_requirements
WHERE former_council IS NULL;

-- Step 6: View distribution by former council
SELECT
    former_council,
    part_number,
    COUNT(*) as count
FROM dcp_general_requirements
GROUP BY former_council, part_number
ORDER BY former_council, count DESC;

-- Step 7: Make NOT NULL (only if Step 5 shows 0)
-- ALTER TABLE dcp_general_requirements
-- ALTER COLUMN former_council SET NOT NULL;

-- Rollback instructions (if needed):
-- DROP TABLE dcp_general_requirements;
-- ALTER TABLE dcp_general_requirements_backup_20251030
-- RENAME TO dcp_general_requirements;
