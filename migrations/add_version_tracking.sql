-- ============================================================
-- VERSION TRACKING MIGRATION
-- Extracts version metadata from pdf_name into structured fields
-- For certifier legal compliance and staleness warnings
-- ============================================================

BEGIN;

-- Step 1: Add version tracking columns
ALTER TABLE documents ADD COLUMN IF NOT EXISTS regulation_year INTEGER;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS amendment_reference TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS amendment_date DATE;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS last_verified_date DATE DEFAULT CURRENT_DATE;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS version_status TEXT DEFAULT 'unverified';

-- Step 2: Create index for version queries
CREATE INDEX IF NOT EXISTS idx_documents_version_status ON documents(version_status);
CREATE INDEX IF NOT EXISTS idx_documents_last_verified ON documents(last_verified_date);

-- Step 3: Extract version data from pdf_name
UPDATE documents SET
    regulation_year = (regexp_match(pdf_name, '(202[0-9]|201[0-9])'))[1]::INTEGER,
    amendment_reference = (regexp_match(pdf_name, '(Amdt?\s*\d+|IWLEP\s*\d{4})', 'i'))[1],
    amendment_date = CASE
        -- Handle "28 Mar 23" or "28 Mar 2023" format (day with month)
        WHEN pdf_name ~ '\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2,4}' THEN
            CASE
                WHEN (regexp_match(pdf_name, '\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{2,4})', 'i'))[1]::INTEGER > 99 THEN
                    -- 4-digit year
                    to_date(
                        (regexp_match(pdf_name, '(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})', 'i'))[1],
                        'DD Mon YYYY'
                    )
                ELSE
                    -- 2-digit year
                    to_date(
                        (regexp_match(pdf_name, '(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2})', 'i'))[1],
                        'DD Mon YY'
                    )
            END
        -- Handle "Nov 22" or "Nov 2023" format (month only)
        WHEN pdf_name ~ '(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2,4}' THEN
            CASE
                WHEN (regexp_match(pdf_name, '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{2,4})', 'i'))[1]::INTEGER > 99 THEN
                    -- 4-digit year
                    to_date(
                        '01 ' || (regexp_match(pdf_name, '((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})', 'i'))[1],
                        'DD Mon YYYY'
                    )
                ELSE
                    -- 2-digit year
                    to_date(
                        '01 ' || (regexp_match(pdf_name, '((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{2})', 'i'))[1],
                        'DD Mon YY'
                    )
            END
        ELSE NULL
    END,
    last_verified_date = CURRENT_DATE,
    version_status = 'unverified';

-- Step 4: Add comment explaining unverified status
COMMENT ON COLUMN documents.version_status IS
    'current: Manually verified as current within 60 days
     superseded: Known to be replaced by newer version
     unverified: Not yet checked against official source';

COMMIT;

-- ============================================================
-- VERIFICATION QUERY
-- ============================================================
SELECT
    document_type,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE regulation_year IS NOT NULL) as with_year,
    COUNT(*) FILTER (WHERE amendment_reference IS NOT NULL) as with_amendment,
    COUNT(*) FILTER (WHERE amendment_date IS NOT NULL) as with_date
FROM documents
GROUP BY document_type;
