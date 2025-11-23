-- Migration: Add page_range column to regulatory_provisions
-- Purpose: Track all pages a provision spans (not just starting page)
-- Date: 2025-10-29

-- Add page_range column (array of integers)
ALTER TABLE regulatory_provisions
ADD COLUMN IF NOT EXISTS page_range int[];

-- Initialize page_range with existing pdf_page
-- (Single page provisions will have array with one element)
UPDATE regulatory_provisions
SET page_range = ARRAY[pdf_page]
WHERE page_range IS NULL AND pdf_page IS NOT NULL;

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_page_range
ON regulatory_provisions USING GIN (page_range);

-- Verify migration
SELECT
    COUNT(*) as total_provisions,
    COUNT(page_range) as with_page_range,
    COUNT(CASE WHEN array_length(page_range, 1) > 1 THEN 1 END) as multi_page_provisions
FROM regulatory_provisions;
