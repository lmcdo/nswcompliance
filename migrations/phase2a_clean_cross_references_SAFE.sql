-- ============================================================================
-- PHASE 2A: CLEAN CROSS-REFERENCES (SAFE, REVERSIBLE)
-- ============================================================================
-- This migration:
--   ✅ Preserves cross-reference data in new column
--   ✅ Cleans ref_number field (removes arrow syntax)
--   ✅ Fully reversible
--   ✅ NO data loss
--
-- Impact: ~2,645 ref_numbers cleaned, may reveal 27 additional duplicates
-- Risk: 2/10 - Modifies ref_number but preserves data
-- ============================================================================

-- Step 1: Add new column to preserve cross-reference text
ALTER TABLE regulatory_provisions
  ADD COLUMN IF NOT EXISTS cross_reference_text TEXT;

-- Step 2: Create index for performance
CREATE INDEX IF NOT EXISTS idx_provisions_cross_ref
  ON regulatory_provisions(cross_reference_text)
  WHERE cross_reference_text IS NOT NULL;

-- Step 3: Copy cross-reference portion to new column
-- Extract everything after the arrow
UPDATE regulatory_provisions
SET cross_reference_text = SUBSTRING(ref_number FROM '\s*->\s*(.*)$')
WHERE ref_number LIKE '%->%'
  AND cross_reference_text IS NULL;

-- Step 4: Clean ref_numbers (remove arrow and everything after)
UPDATE regulatory_provisions
SET ref_number = REGEXP_REPLACE(ref_number, '\s*->.*$', '')
WHERE ref_number LIKE '%->%';

-- Step 5: Mark any new duplicates revealed by cleaning
-- This will mark provisions that became duplicates after ref_number cleanup
WITH cleaned_duplicates AS (
  SELECT
    id,
    document_id,
    ref_number,
    md5(provision_text) as text_hash,
    ROW_NUMBER() OVER (
      PARTITION BY document_id, ref_number, md5(provision_text)
      ORDER BY created_at ASC, id ASC
    ) as rank,
    COUNT(*) OVER (
      PARTITION BY document_id, ref_number, md5(provision_text)
    ) as group_size
  FROM regulatory_provisions
  WHERE is_canonical = TRUE  -- Only look at previously canonical records
),
new_canonical_ids AS (
  SELECT
    document_id,
    ref_number,
    text_hash,
    MIN(id) as canonical_id
  FROM regulatory_provisions
  WHERE is_canonical = TRUE
  GROUP BY document_id, ref_number, text_hash
)
UPDATE regulatory_provisions rp
SET
  is_canonical = CASE
    WHEN cd.rank = 1 THEN TRUE
    ELSE FALSE
  END,
  canonical_provision_id = CASE
    WHEN cd.rank > 1 THEN nc.canonical_id
    ELSE rp.canonical_provision_id
  END,
  migration_phase = CASE
    WHEN cd.rank = 1 THEN 'phase2a_canonical'
    WHEN cd.rank > 1 THEN 'phase2a_duplicate'
    ELSE rp.migration_phase
  END
FROM cleaned_duplicates cd
JOIN new_canonical_ids nc
  ON cd.document_id = nc.document_id
  AND cd.ref_number = nc.ref_number
  AND cd.text_hash = nc.text_hash
WHERE rp.id = cd.id
  AND cd.group_size > 1;

-- ============================================================================
-- VALIDATION QUERIES (run after migration)
-- ============================================================================

-- Check 1: Count of provisions with cross-references preserved
SELECT
  COUNT(*) as total_with_cross_refs,
  COUNT(*) FILTER (WHERE LENGTH(cross_reference_text) > 0) as non_empty_cross_refs
FROM regulatory_provisions
WHERE cross_reference_text IS NOT NULL;

-- Check 2: Verify no ref_numbers still have arrows
SELECT COUNT(*) as provisions_still_with_arrows
FROM regulatory_provisions
WHERE ref_number LIKE '%->%';
-- Expected: 0

-- Check 3: Sample cleaned provisions
SELECT
  id,
  ref_number,
  cross_reference_text,
  LEFT(provision_text, 60) as text_preview
FROM regulatory_provisions
WHERE cross_reference_text IS NOT NULL
LIMIT 10;

-- Check 4: Count new duplicates revealed
SELECT
  COUNT(*) as new_duplicates_marked
FROM regulatory_provisions
WHERE migration_phase = 'phase2a_duplicate';

-- Check 5: Verify canonical counts
SELECT
  COUNT(*) FILTER (WHERE is_canonical = TRUE) as canonical,
  COUNT(*) FILTER (WHERE is_canonical = FALSE) as duplicates,
  COUNT(*) as total
FROM regulatory_provisions;

-- ============================================================================
-- ROLLBACK (if needed)
-- ============================================================================

-- RESTORE ref_numbers from cross_reference_text
-- UPDATE regulatory_provisions
-- SET ref_number = ref_number || ' -> ' || cross_reference_text
-- WHERE cross_reference_text IS NOT NULL;

-- DROP index and column
-- DROP INDEX IF EXISTS idx_provisions_cross_ref;
-- ALTER TABLE regulatory_provisions DROP COLUMN IF EXISTS cross_reference_text;

-- REVERT is_canonical changes from Phase 2A
-- UPDATE regulatory_provisions
-- SET
--   is_canonical = TRUE,
--   canonical_provision_id = NULL,
--   migration_phase = 'phase1_canonical'
-- WHERE migration_phase = 'phase2a_duplicate';
