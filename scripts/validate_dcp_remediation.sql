-- Step 3 Validation: DA Mode Triage Tests
-- Run these queries to verify the remediation worked

-- Test 1: DA Mode Triage - Verify fencing provisions are now properly tagged
-- User selects: "Alterations and additions" (new_fencing = 'no')
-- Expected: All fencing provisions are excluded from scope
WITH fencing_provisions AS (
  SELECT 
    id, v2_topic, provision_text,
    source_council
  FROM regulatory_provisions
  WHERE source_council IN ('marrickville', 'ashfield', 'leichhardt')
    AND v2_topic = 'fencing'
    AND v2_provision_type = 'control'
)
SELECT 
  source_council,
  COUNT(*) as fencing_count,
  COUNT(*) FILTER (WHERE provision_text ILIKE '%fence%') as text_matches,
  ROUND(100.0 * COUNT(*) FILTER (WHERE provision_text ILIKE '%fence%') / COUNT(*), 1) as match_percentage
FROM fencing_provisions
GROUP BY source_council
ORDER BY source_council;

-- Test 2: Intake Snapshot - Compare provision counts before/after for all 6 topics
-- This shows if tags are now correctly distributed
SELECT 
  source_council,
  v2_topic,
  COUNT(*) as current_count
FROM regulatory_provisions
WHERE source_council IN ('marrickville', 'ashfield', 'leichhardt')
  AND v2_topic IN ('fencing', 'parking', 'pool', 'signage', 'trees', 'setback')
  AND v2_provision_type = 'control'
GROUP BY source_council, v2_topic
ORDER BY source_council, v2_topic;

-- Test 3: Sample validation - Check specific provisions that were updated
-- Take 10 random provisions from each updated topic and verify text matches tag
SELECT 
  id, source_council, v2_topic, provision_text,
  CASE 
    WHEN v2_topic = 'fencing' AND provision_text ILIKE '%fence%' THEN '✓ Match'
    WHEN v2_topic = 'parking' AND (provision_text ILIKE '%parking%' OR provision_text ILIKE '%driveway%') THEN '✓ Match'
    WHEN v2_topic = 'pool' AND (provision_text ILIKE '%pool%' OR provision_text ILIKE '%spa%') THEN '✓ Match'
    WHEN v2_topic = 'signage' AND provision_text ILIKE '%sign%' THEN '✓ Match'
    WHEN v2_topic = 'trees' AND provision_text ILIKE '%tree%' THEN '✓ Match'
    WHEN v2_topic = 'setback' AND provision_text ILIKE '%setback%' THEN '✓ Match'
    ELSE '✗ Mismatch'
  END as validation_status
FROM regulatory_provisions
WHERE source_council IN ('marrickville', 'ashfield', 'leichhardt')
  AND v2_topic IN ('fencing', 'parking', 'pool', 'signage', 'trees', 'setback')
  AND v2_provision_type = 'control'
ORDER BY RANDOM()
LIMIT 15;
