-- Migration: Mark descriptive heritage provisions as non-actionable
-- Date: 2026-01-27
-- Reason: Extraction process marked HCA descriptions and historical context as actionable
--         These should not appear in compliance checks - they're background information

-- Backup query (run first to verify impact)
SELECT
  CASE
    WHEN document_id ILIKE '%Ashfield%' THEN 'Ashfield'
    WHEN document_id ILIKE '%Marrickville%' THEN 'Marrickville'
    WHEN document_id ILIKE '%Leichhardt%' THEN 'Leichhardt'
    ELSE 'Other'
  END as council,
  v2_heritage_type,
  v2_provision_type,
  COUNT(*) as count
FROM regulatory_provisions
WHERE v2_is_actionable = true
  AND v2_dcp_layer = 'condition'
  AND v2_site_condition_required = 'heritage'
  AND v2_heritage_type = 'descriptive'
GROUP BY 1, 2, 3
ORDER BY 1, 4 DESC;

-- Expected results:
-- Ashfield | descriptive | control    | 311
-- Ashfield | descriptive | definition | 9
-- Marrickville | descriptive | control | 18

-- Total affected: ~338 provisions

-- Migration: Update descriptive provisions to non-actionable
UPDATE regulatory_provisions
SET v2_is_actionable = false
WHERE v2_is_actionable = true
  AND v2_dcp_layer = 'condition'
  AND v2_site_condition_required = 'heritage'
  AND v2_heritage_type = 'descriptive';

-- Verification query (run after migration)
SELECT
  CASE
    WHEN document_id ILIKE '%Ashfield%' THEN 'Ashfield'
    WHEN document_id ILIKE '%Marrickville%' THEN 'Marrickville'
    WHEN document_id ILIKE '%Leichhardt%' THEN 'Leichhardt'
    ELSE 'Other'
  END as council,
  v2_is_actionable,
  v2_heritage_type,
  COUNT(*) as count
FROM regulatory_provisions
WHERE v2_dcp_layer = 'condition'
  AND v2_site_condition_required = 'heritage'
  AND v2_heritage_type = 'descriptive'
GROUP BY 1, 2, 3
ORDER BY 1, 2;

-- Expected results after migration:
-- Ashfield | false | descriptive | 320
-- Marrickville | false | descriptive | 18

-- Sample provisions affected
SELECT
  CASE
    WHEN document_id ILIKE '%Ashfield%' THEN 'Ashfield'
    WHEN document_id ILIKE '%Marrickville%' THEN 'Marrickville'
    ELSE 'Other'
  END as council,
  v2_topic,
  LEFT(provision_text, 100) as sample_text
FROM regulatory_provisions
WHERE v2_is_actionable = false  -- Now false after migration
  AND v2_dcp_layer = 'condition'
  AND v2_site_condition_required = 'heritage'
  AND v2_heritage_type = 'descriptive'
ORDER BY RANDOM()
LIMIT 10;
