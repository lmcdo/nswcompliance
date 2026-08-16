-- Fix layer tagging for heritage provisions
-- Issue: Heritage provisions in Part C Section 1 are tagged as 'generic' when they should be 'condition'
-- Date: 2026-01-11

BEGIN;

-- Show current state
SELECT
  v2_dcp_layer,
  COUNT(*) as count
FROM regulatory_provisions
WHERE v2_topic = 'heritage'
  AND document_id LIKE '%Leichhardt%'
GROUP BY v2_dcp_layer;

-- Update heritage provisions to condition layer
UPDATE regulatory_provisions
SET v2_dcp_layer = 'condition'
WHERE v2_topic = 'heritage'
  AND v2_dcp_layer = 'generic'
  AND document_id LIKE '%Leichhardt%'
  AND v2_is_actionable = true;

-- Show after state
SELECT
  v2_dcp_layer,
  COUNT(*) as count
FROM regulatory_provisions
WHERE v2_topic = 'heritage'
  AND document_id LIKE '%Leichhardt%'
GROUP BY v2_dcp_layer;

-- Show affected records
SELECT
  id,
  document_id,
  v2_dcp_part,
  v2_marker,
  v2_topic,
  v2_dcp_layer,
  LEFT(provision_text, 100) as text_preview
FROM regulatory_provisions
WHERE v2_topic = 'heritage'
  AND v2_dcp_layer = 'condition'
  AND document_id LIKE '%Leichhardt%'
LIMIT 10;

COMMIT;
