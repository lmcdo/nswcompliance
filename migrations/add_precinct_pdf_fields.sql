-- Add missing fields to dcp_precinct_provisions for PDF page display
-- These fields are denormalized from regulatory_provisions_canonical and regulatory_provisions
-- to avoid slow JOINs in the UI API

ALTER TABLE dcp_precinct_provisions
ADD COLUMN IF NOT EXISTS document_id TEXT,
ADD COLUMN IF NOT EXISTS pdf_path TEXT,
ADD COLUMN IF NOT EXISTS pdf_page_image_url TEXT;

-- Populate the new fields from parent provision
UPDATE dcp_precinct_provisions pp
SET
    document_id = rpc.document_id,
    pdf_path = rpc.pdf_path,
    pdf_page_image_url = rp.pdf_page_image_url
FROM regulatory_provisions_canonical rpc
LEFT JOIN regulatory_provisions rp ON rpc.id = rp.id
WHERE pp.parent_provision_id = rpc.id
AND pp.document_id IS NULL;

-- Verify the update
SELECT
    COUNT(*) as total_provisions,
    COUNT(document_id) as with_document_id,
    COUNT(pdf_page_image_url) as with_pdf_url
FROM dcp_precinct_provisions;
