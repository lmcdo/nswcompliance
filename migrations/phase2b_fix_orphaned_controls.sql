-- ============================================================================
-- Phase 2.5: Fix Orphaned Foreign Key References
-- ============================================================================
-- Date: 2025-10-01
-- Purpose: Update development_controls and development_permissions foreign keys
--          to point to canonical provisions instead of duplicates
-- Risk: 2/10 - Safe, reversible with backup
-- Expected Changes: ~522 controls updated
-- ============================================================================

-- SAFETY CHECKS
DO $$
BEGIN
    -- Check Phase 1/2A completed
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'regulatory_provisions'
        AND column_name = 'is_canonical'
    ) THEN
        RAISE EXCEPTION 'Phase 1 not complete - is_canonical column missing';
    END IF;

    -- Check canonical view exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.views
        WHERE table_name = 'regulatory_provisions_canonical'
    ) THEN
        RAISE EXCEPTION 'Phase 1 not complete - canonical view missing';
    END IF;

    RAISE NOTICE 'Safety checks passed - proceeding with migration';
END $$;

-- ============================================================================
-- STEP 1: Update development_controls foreign keys
-- ============================================================================

-- Count before update
DO $$
DECLARE
    orphaned_count INT;
BEGIN
    SELECT COUNT(*) INTO orphaned_count
    FROM development_controls dc
    WHERE dc.provision_id IN (
        SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
    );

    RAISE NOTICE 'Step 1: Found % orphaned development_controls', orphaned_count;
END $$;

-- Update control foreign keys to canonical provisions
UPDATE development_controls dc
SET provision_id = rp_canonical.id::text
FROM regulatory_provisions rp_dup
JOIN regulatory_provisions rp_canonical
  ON rp_canonical.id = rp_dup.canonical_provision_id
WHERE dc.provision_id = rp_dup.id::text
  AND rp_dup.is_canonical = FALSE
  AND rp_dup.canonical_provision_id IS NOT NULL;

-- Report results
DO $$
DECLARE
    updated_count INT;
    remaining_orphaned INT;
BEGIN
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE 'Step 1: Updated % control foreign keys', updated_count;

    -- Check remaining orphaned
    SELECT COUNT(*) INTO remaining_orphaned
    FROM development_controls dc
    WHERE dc.provision_id IN (
        SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
    );

    IF remaining_orphaned > 0 THEN
        RAISE WARNING 'Step 1: % controls still orphaned (no canonical found)', remaining_orphaned;
    ELSE
        RAISE NOTICE 'Step 1: All controls successfully linked to canonical provisions';
    END IF;
END $$;

-- ============================================================================
-- STEP 2: Update development_permissions foreign keys (if they exist)
-- ============================================================================

-- Count before update
DO $$
DECLARE
    orphaned_count INT;
BEGIN
    SELECT COUNT(*) INTO orphaned_count
    FROM development_permissions dp
    WHERE dp.source_provision_id IS NOT NULL
      AND dp.source_provision_id IN (
          SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
      );

    RAISE NOTICE 'Step 2: Found % orphaned development_permissions', orphaned_count;
END $$;

-- Update permission foreign keys to canonical provisions
UPDATE development_permissions dp
SET source_provision_id = rp_canonical.id::text
FROM regulatory_provisions rp_dup
JOIN regulatory_provisions rp_canonical
  ON rp_canonical.id = rp_dup.canonical_provision_id
WHERE dp.source_provision_id = rp_dup.id::text
  AND rp_dup.is_canonical = FALSE
  AND rp_dup.canonical_provision_id IS NOT NULL;

-- Report results
DO $$
DECLARE
    updated_count INT;
    remaining_orphaned INT;
BEGIN
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RAISE NOTICE 'Step 2: Updated % permission foreign keys', updated_count;

    -- Check remaining orphaned
    SELECT COUNT(*) INTO remaining_orphaned
    FROM development_permissions dp
    WHERE dp.source_provision_id IS NOT NULL
      AND dp.source_provision_id IN (
          SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
      );

    IF remaining_orphaned > 0 THEN
        RAISE WARNING 'Step 2: % permissions still orphaned (no canonical found)', remaining_orphaned;
    ELSE
        RAISE NOTICE 'Step 2: All permissions successfully linked to canonical provisions';
    END IF;
END $$;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    orphaned_controls INT;
    orphaned_permissions INT;
    total_controls INT;
    canonical_join_count INT;
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'PHASE 2.5 MIGRATION COMPLETE';
    RAISE NOTICE '========================================';

    -- Count orphaned controls
    SELECT COUNT(*) INTO orphaned_controls
    FROM development_controls dc
    WHERE dc.provision_id IN (
        SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
    );

    -- Count orphaned permissions
    SELECT COUNT(*) INTO orphaned_permissions
    FROM development_permissions dp
    WHERE dp.source_provision_id IS NOT NULL
      AND dp.source_provision_id IN (
          SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
      );

    -- Count total controls
    SELECT COUNT(*) INTO total_controls
    FROM development_controls;

    -- Test canonical view join
    SELECT COUNT(DISTINCT dc.id) INTO canonical_join_count
    FROM regulatory_provisions_canonical rp
    JOIN development_controls dc ON dc.provision_id = rp.id::text;

    RAISE NOTICE 'Orphaned controls: %', orphaned_controls;
    RAISE NOTICE 'Orphaned permissions: %', orphaned_permissions;
    RAISE NOTICE 'Total controls: %', total_controls;
    RAISE NOTICE 'Controls joinable via canonical view: %', canonical_join_count;

    IF orphaned_controls = 0 AND orphaned_permissions = 0 THEN
        RAISE NOTICE '';
        RAISE NOTICE 'SUCCESS: All foreign keys point to canonical provisions';
        RAISE NOTICE '========================================';
    ELSE
        RAISE WARNING '';
        RAISE WARNING 'PARTIAL SUCCESS: Some foreign keys still orphaned';
        RAISE WARNING 'Review orphaned records manually';
        RAISE WARNING '========================================';
    END IF;
END $$;

-- ============================================================================
-- ROLLBACK INSTRUCTIONS
-- ============================================================================

-- To rollback this migration, use the rollback_phase2b.py script
-- OR manually restore from the backup created before migration

-- Manual rollback (NOT RECOMMENDED - use script instead):
-- This migration changes foreign key values, which cannot be automatically
-- reversed without the backup. The rollback script uses the backup to restore
-- the original provision_id values.
