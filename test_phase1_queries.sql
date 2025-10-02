-- ============================================================================
-- TEST QUERIES FOR PHASE 1 MIGRATION
-- ============================================================================
-- Run these AFTER migration to verify everything works
-- ============================================================================

-- Test 1: Basic count comparison
-- Expected: ~20,329 canonical vs 22,648 total
\echo '\n=== TEST 1: Count Comparison ==='
SELECT
  COUNT(*) FILTER (WHERE is_canonical = TRUE) as canonical_count,
  COUNT(*) FILTER (WHERE is_canonical = FALSE) as duplicate_count,
  COUNT(*) as total_count
FROM regulatory_provisions;

-- Test 2: View works correctly
-- Expected: Same count as canonical in Test 1
\echo '\n=== TEST 2: View Returns Canonical Only ==='
SELECT COUNT(*) as view_count
FROM regulatory_provisions_canonical;

-- Test 3: Example duplicate group
-- Shows one canonical and its duplicates
\echo '\n=== TEST 3: Sample Duplicate Group ==='
WITH sample_canonical AS (
  SELECT id, ref_number, LEFT(provision_text, 100) as text
  FROM regulatory_provisions
  WHERE is_canonical = TRUE
    AND id IN (
      SELECT canonical_provision_id
      FROM regulatory_provisions
      WHERE is_canonical = FALSE
      LIMIT 1
    )
)
SELECT
  'CANONICAL' as type,
  rp.id,
  rp.ref_number,
  rp.text
FROM sample_canonical rp
UNION ALL
SELECT
  'DUPLICATE' as type,
  dup.id,
  dup.ref_number,
  LEFT(dup.provision_text, 100) as text
FROM regulatory_provisions dup
JOIN sample_canonical canon ON dup.canonical_provision_id = canon.id
WHERE dup.is_canonical = FALSE;

-- Test 4: Check no orphaned duplicates
-- Expected: 0
\echo '\n=== TEST 4: Orphaned Duplicates Check ==='
SELECT
  COUNT(*) as orphaned_count,
  CASE
    WHEN COUNT(*) = 0 THEN '✓ PASS'
    ELSE '✗ FAIL'
  END as status
FROM regulatory_provisions dup
LEFT JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
WHERE dup.is_canonical = FALSE
  AND (canonical.id IS NULL OR canonical.is_canonical = FALSE);

-- Test 5: Compare query results before/after
-- This simulates a typical frontend query
\echo '\n=== TEST 5: Frontend Query Comparison ==='
\echo 'WITHOUT filter (returns duplicates):'
SELECT COUNT(*) as count_with_duplicates
FROM regulatory_provisions
WHERE document_id LIKE '%Sustainable_Buildings%';

\echo 'WITH filter (canonical only):'
SELECT COUNT(*) as count_canonical_only
FROM regulatory_provisions
WHERE document_id LIKE '%Sustainable_Buildings%'
  AND is_canonical = TRUE;

\echo 'USING VIEW:'
SELECT COUNT(*) as count_using_view
FROM regulatory_provisions_canonical
WHERE document_id LIKE '%Sustainable_Buildings%';

-- Test 6: Performance check
-- Verify indexes are working
\echo '\n=== TEST 6: Index Usage ==='
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*)
FROM regulatory_provisions
WHERE is_canonical = TRUE;

-- Test 7: Text hash coverage
-- Expected: 100% coverage
\echo '\n=== TEST 7: Text Hash Coverage ==='
SELECT
  COUNT(*) as total,
  COUNT(text_hash) as with_hash,
  COUNT(*) - COUNT(text_hash) as missing_hash,
  CASE
    WHEN COUNT(*) - COUNT(text_hash) = 0 THEN '✓ PASS'
    ELSE '✗ FAIL'
  END as status
FROM regulatory_provisions;

-- Test 8: Verify canonical records have no canonical_provision_id
-- Expected: All canonical records should have NULL canonical_provision_id
\echo '\n=== TEST 8: Canonical Records Integrity ==='
SELECT
  COUNT(*) as invalid_canonical_count,
  CASE
    WHEN COUNT(*) = 0 THEN '✓ PASS'
    ELSE '✗ FAIL'
  END as status
FROM regulatory_provisions
WHERE is_canonical = TRUE
  AND canonical_provision_id IS NOT NULL;

-- Test 9: Top duplicate groups
-- Shows which provisions had most duplicates
\echo '\n=== TEST 9: Top 10 Duplicate Groups ==='
SELECT
  canonical.ref_number,
  canonical.document_id,
  LEFT(canonical.provision_text, 60) as text_preview,
  COUNT(*) as duplicate_count
FROM regulatory_provisions dup
JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
WHERE dup.is_canonical = FALSE
GROUP BY canonical.id, canonical.ref_number, canonical.document_id, canonical.provision_text
ORDER BY COUNT(*) DESC
LIMIT 10;

-- Test 10: Verify migration_phase tracking
\echo '\n=== TEST 10: Migration Phase Tracking ==='
SELECT
  migration_phase,
  COUNT(*) as count
FROM regulatory_provisions
GROUP BY migration_phase
ORDER BY migration_phase;

\echo '\n=== ALL TESTS COMPLETE ==='
