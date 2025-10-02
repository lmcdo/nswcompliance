-- Migration: Add document_category column to regulatory_provisions
-- This separates DOCUMENT TYPE (SEPP/LEP/DCP) from SEMANTIC TYPE (provision_type)

-- Option 1: Add new column (RECOMMENDED)
-- ========================================
-- Adds a proper 'document_category' column alongside existing 'provision_type'

BEGIN;

-- Add the column
ALTER TABLE regulatory_provisions
ADD COLUMN IF NOT EXISTS document_category TEXT;

-- Populate it based on document_id patterns
UPDATE regulatory_provisions
SET document_category = CASE
    WHEN document_id LIKE '%SEPP%'
         OR document_id LIKE '%Housing%'
         OR document_id LIKE '%State Environmental Planning Policy%'
    THEN 'SEPP'

    WHEN document_id LIKE '%LEP%'
         OR document_id LIKE '%Local Environmental Plan%'
    THEN 'LEP'

    WHEN document_id LIKE '%DCP%'
         OR document_id LIKE '%Development Control Plan%'
    THEN 'DCP'

    ELSE 'OTHER'
END;

-- Create index for fast queries
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_document_category
ON regulatory_provisions(document_category);

-- Verify results
SELECT
    document_category,
    COUNT(*) as provision_count
FROM regulatory_provisions
GROUP BY document_category
ORDER BY provision_count DESC;

COMMIT;

-- Now you can query cleanly:
-- SELECT * FROM regulatory_provisions WHERE document_category = 'SEPP';


-- Option 2: Use documents table JOIN (BEST PRACTICE)
-- ===================================================
-- Leverage existing 'documents' table which already has document_type

/*
-- This doesn't require migration, just better queries:
SELECT rp.*
FROM regulatory_provisions rp
JOIN documents d ON rp.document_id = d.id
WHERE d.document_type = 'SEPP';

-- Benefit: Single source of truth (documents table)
-- Drawback: Requires JOIN on every query
*/


-- Option 3: Create VIEW with document_category (HYBRID)
-- ======================================================
-- Best of both: no schema change, performance boost

CREATE OR REPLACE VIEW provisions_with_category AS
SELECT
    rp.*,
    d.document_type as document_category
FROM regulatory_provisions rp
LEFT JOIN documents d ON rp.document_id = d.id;

-- Usage:
-- SELECT * FROM provisions_with_category WHERE document_category = 'SEPP';