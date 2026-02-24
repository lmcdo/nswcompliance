-- Migration: Add SEPP Version Tracking Fields
-- Date: 2026-02-20
-- Purpose: Enable robust tracking of SEPP amendments and consolidation dates

-- Add version tracking columns to documents table
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS consolidated_as_of_date DATE,
ADD COLUMN IF NOT EXISTS consolidation_url TEXT,
ADD COLUMN IF NOT EXISTS amending_epis TEXT[],
ADD COLUMN IF NOT EXISTS major_amendments JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS next_check_date DATE,
ADD COLUMN IF NOT EXISTS is_superseded BOOLEAN DEFAULT false;

-- Create index for efficient version queries
CREATE INDEX IF NOT EXISTS idx_documents_version_status
ON documents(document_type, version_status, is_superseded)
WHERE document_type IN ('SEPP', 'LEP', 'DCP');

-- Create index for next check date queries (for quarterly review workflow)
CREATE INDEX IF NOT EXISTS idx_documents_next_check
ON documents(next_check_date)
WHERE next_check_date IS NOT NULL;

-- Add comments for documentation
COMMENT ON COLUMN documents.consolidated_as_of_date IS 'Date of the consolidated version from NSW Legislation (e.g., 2026-01-15)';
COMMENT ON COLUMN documents.consolidation_url IS 'URL to NSW Legislation consolidated version with point-in-time date';
COMMENT ON COLUMN documents.amending_epis IS 'Array of EPI numbers that have amended this document (e.g., ["512/2025", "597/2025"])';
COMMENT ON COLUMN documents.major_amendments IS 'Structured amendment history as JSONB array: [{"epi": "597/2025", "effective_date": "2025-07-30", "description": "Added Part 3BA", "affects_provisions": true}]';
COMMENT ON COLUMN documents.next_check_date IS 'When to next verify this document for amendments (typically consolidated_as_of_date + 90 days)';
COMMENT ON COLUMN documents.is_superseded IS 'True if this is an old version that has been replaced by a newer document';

-- Verify migration
DO $$
DECLARE
    col_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO col_count
    FROM information_schema.columns
    WHERE table_name = 'documents'
      AND column_name IN ('consolidated_as_of_date', 'consolidation_url', 'amending_epis',
                          'major_amendments', 'next_check_date', 'is_superseded');

    IF col_count = 6 THEN
        RAISE NOTICE 'SUCCESS: All 6 version tracking columns added to documents table';
    ELSE
        RAISE WARNING 'WARNING: Only % of 6 expected columns were added', col_count;
    END IF;
END $$;

-- Show sample of new schema
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'documents'
  AND column_name IN ('consolidated_as_of_date', 'consolidation_url', 'amending_epis',
                      'major_amendments', 'next_check_date', 'is_superseded')
ORDER BY ordinal_position;
