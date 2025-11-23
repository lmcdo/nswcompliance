-- Precinct Provisions Architecture - Data Migration
-- Date: 2025-10-23
-- Populates dcp_precinct_provisions from regulatory_provisions_canonical

-- First, check how many rows we expect
DO $$
DECLARE
    row_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO row_count
    FROM regulatory_provisions_canonical
    WHERE document_id ~ '9_[0-9]+'
    AND provision_text IS NOT NULL
    AND LENGTH(provision_text) > 20;

    RAISE NOTICE 'Expected rows to migrate: %', row_count;
END $$;

-- Populate dcp_precinct_provisions
INSERT INTO dcp_precinct_provisions (
    precinct_id,
    precinct_name,
    lga,
    provision_text,
    provision_type,
    ref_number,
    section_header,
    parent_provision_id,
    pdf_page,
    display_order
)
SELECT
    -- Extract precinct ID: '9_29' from 'Marrickville_DCP_2011_9_29_South_Western_Marrickville'
    (regexp_match(document_id, '9_([0-9_]+)'))[1] as precinct_id,

    -- Extract precinct name from document_id
    -- 'Marrickville_DCP_2011_9_29_South_Western_Marrickville' -> 'South Western Marrickville'
    TRIM(regexp_replace(
        regexp_replace(document_id, '^.*9_[0-9_]+_', ''),
        '_', ' ', 'g'
    )) as precinct_name,

    -- Determine LGA
    CASE
        WHEN document_id ~ 'Marrickville' THEN 'Inner West'
        WHEN document_id ~ 'Ashfield' THEN 'Inner West'
        WHEN document_id ~ 'Leichhardt' THEN 'Inner West'
        ELSE 'Unknown'
    END as lga,

    provision_text,
    provision_type,
    ref_number,
    section_header,
    id as parent_provision_id,
    pdf_page,

    -- Display order: use ref_number for ordering, default to 999 if null
    CASE
        WHEN ref_number IS NOT NULL AND split_part(ref_number, '.', 3) != '' THEN
            -- Try to extract numeric part from ref_number like '9.29.1'
            CAST(split_part(ref_number, '.', 3) AS INTEGER)
        ELSE 999
    END as display_order

FROM regulatory_provisions  -- Use base table to access pdf_page
WHERE document_id ~ '9_[0-9]+'
    AND provision_text IS NOT NULL
    AND LENGTH(provision_text) > 20  -- Filter out empty/TOC entries
    AND provision_text NOT LIKE '#%Contents%'  -- Filter out table of contents
    AND provision_text NOT LIKE 'Part 9 Stra%'  -- Filter out generic headers
    AND is_canonical = true  -- IMPORTANT: Only canonical provisions
ON CONFLICT DO NOTHING;

-- Verify migration
DO $$
DECLARE
    migrated_count INTEGER;
    precinct_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO migrated_count FROM dcp_precinct_provisions;

    SELECT COUNT(DISTINCT precinct_id) INTO precinct_count FROM dcp_precinct_provisions;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'DATA MIGRATION COMPLETE';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Total provisions migrated: %', migrated_count;
    RAISE NOTICE 'Distinct precincts: %', precinct_count;
    RAISE NOTICE '========================================';

    IF migrated_count < 100 THEN
        RAISE WARNING 'Low provision count - expected ~230';
    END IF;

    IF precinct_count < 10 THEN
        RAISE WARNING 'Low precinct count - expected ~15';
    END IF;
END $$;
