-- Add pdf_page_image_url column to dcp_general_provisions
-- Migration: add_pdf_page_image_url_column
-- Date: 2025-10-28

ALTER TABLE dcp_general_provisions
ADD COLUMN IF NOT EXISTS pdf_page_image_url TEXT;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_dcp_general_provisions_pdf_page
ON dcp_general_provisions(pdf_page)
WHERE pdf_page IS NOT NULL;

-- Verify
SELECT
    COUNT(*) as total_provisions,
    COUNT(pdf_page) as with_pdf_page,
    COUNT(pdf_page_image_url) as with_pdf_image_url
FROM dcp_general_provisions;
