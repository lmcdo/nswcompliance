-- ============================================================================
-- Provision Versioning & Change Tracking Schema
-- ============================================================================
-- Purpose: Add provision-level versioning on top of existing document versioning
-- Author: Compliance Engine Team
-- Date: 2026-01-27
--
-- This migration adds:
--   1. provision_versions: Full historical snapshots when provisions change
--   2. provision_change_log: Lightweight audit trail
--   3. Version tracking columns in regulatory_provisions
-- ============================================================================

-- ============================================================================
-- TABLE: provision_versions
-- ============================================================================
-- Stores full historical copies of provisions when they change
-- Each provision can have multiple versions over time
-- ============================================================================

CREATE TABLE IF NOT EXISTS provision_versions (
    id SERIAL PRIMARY KEY,
    provision_id INTEGER NOT NULL REFERENCES regulatory_provisions(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,

    -- Snapshot of provision content
    provision_text TEXT NOT NULL,
    provision_type TEXT,
    v2_topic TEXT,
    v2_applicable_zones TEXT[],
    v2_applicable_dev_types TEXT[],
    v2_has_numeric_value BOOLEAN,

    -- Temporal tracking
    effective_from TIMESTAMP NOT NULL DEFAULT NOW(),
    effective_to TIMESTAMP,  -- NULL = current version

    -- Change metadata
    change_type TEXT CHECK (change_type IN ('created', 'modified', 'deleted', 'reinstated')),
    change_summary TEXT,
    text_hash TEXT NOT NULL,

    -- Provenance
    extracted_from_document TEXT,
    extraction_date TIMESTAMP DEFAULT NOW(),
    extraction_method TEXT DEFAULT 'manual',

    -- Ensure unique version numbers per provision
    UNIQUE(provision_id, version_number)
);

-- ============================================================================
-- INDEXES: provision_versions
-- ============================================================================

-- Fast lookup by provision_id (most common query)
CREATE INDEX IF NOT EXISTS idx_pv_provision_id
ON provision_versions(provision_id);

-- Fast lookup of current version (effective_to IS NULL)
CREATE INDEX IF NOT EXISTS idx_pv_current
ON provision_versions(provision_id, effective_to)
WHERE effective_to IS NULL;

-- Historical date range queries (e.g., "provisions as of 2024-05-15")
CREATE INDEX IF NOT EXISTS idx_pv_date_range
ON provision_versions(provision_id, effective_from, effective_to);

-- Lookup by text hash (detect duplicates)
CREATE INDEX IF NOT EXISTS idx_pv_text_hash
ON provision_versions(text_hash);

-- ============================================================================
-- TABLE: provision_change_log
-- ============================================================================
-- Lightweight audit trail of all changes
-- Links to specific version records for before/after comparison
-- ============================================================================

CREATE TABLE IF NOT EXISTS provision_change_log (
    id SERIAL PRIMARY KEY,
    provision_id INTEGER NOT NULL REFERENCES regulatory_provisions(id) ON DELETE CASCADE,
    version_from INTEGER REFERENCES provision_versions(id) ON DELETE SET NULL,
    version_to INTEGER REFERENCES provision_versions(id) ON DELETE SET NULL,

    -- Change details
    change_type TEXT NOT NULL,
    fields_changed TEXT[],

    -- Temporal and provenance
    changed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    triggered_by_document TEXT,
    amendment_reference TEXT,
    change_reason TEXT,

    detected_by TEXT DEFAULT 'extraction_pipeline'
);

-- ============================================================================
-- INDEXES: provision_change_log
-- ============================================================================

-- Fast lookup by provision_id
CREATE INDEX IF NOT EXISTS idx_pcl_provision_id
ON provision_change_log(provision_id);

-- Temporal queries (e.g., "changes since 2024-01-01")
CREATE INDEX IF NOT EXISTS idx_pcl_changed_at
ON provision_change_log(changed_at DESC);

-- Document-level queries (e.g., "what changed in DCP Part 2.1?")
CREATE INDEX IF NOT EXISTS idx_pcl_document
ON provision_change_log(triggered_by_document, changed_at DESC);

-- Change type queries (e.g., "all deletions")
CREATE INDEX IF NOT EXISTS idx_pcl_change_type
ON provision_change_log(change_type);

-- ============================================================================
-- ALTER TABLE: regulatory_provisions
-- ============================================================================
-- Add version tracking columns to existing table
-- ============================================================================

-- Add columns only if they don't exist
DO $$
BEGIN
    -- Reference to current version
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='regulatory_provisions'
                   AND column_name='current_version_id') THEN
        ALTER TABLE regulatory_provisions
        ADD COLUMN current_version_id INTEGER REFERENCES provision_versions(id) ON DELETE SET NULL;
    END IF;

    -- First time this provision was seen
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='regulatory_provisions'
                   AND column_name='first_seen_date') THEN
        ALTER TABLE regulatory_provisions
        ADD COLUMN first_seen_date TIMESTAMP;
    END IF;

    -- Last modification date
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='regulatory_provisions'
                   AND column_name='last_modified_date') THEN
        ALTER TABLE regulatory_provisions
        ADD COLUMN last_modified_date TIMESTAMP DEFAULT NOW();
    END IF;

    -- Total number of versions
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='regulatory_provisions'
                   AND column_name='version_count') THEN
        ALTER TABLE regulatory_provisions
        ADD COLUMN version_count INTEGER DEFAULT 1;
    END IF;

    -- Current/active status
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='regulatory_provisions'
                   AND column_name='is_current') THEN
        ALTER TABLE regulatory_provisions
        ADD COLUMN is_current BOOLEAN DEFAULT TRUE;
    END IF;

    -- Hash of current text for change detection
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='regulatory_provisions'
                   AND column_name='text_hash_current') THEN
        ALTER TABLE regulatory_provisions
        ADD COLUMN text_hash_current TEXT;
    END IF;
END $$;

-- ============================================================================
-- INDEXES: regulatory_provisions (version-related)
-- ============================================================================

-- Fast lookup of current version
CREATE INDEX IF NOT EXISTS idx_rp_current_version
ON regulatory_provisions(current_version_id);

-- Fast filtering of current provisions (most common query)
-- Partial index for optimal performance
CREATE INDEX IF NOT EXISTS idx_rp_is_current
ON regulatory_provisions(is_current, id)
WHERE is_current = TRUE;

-- Text hash lookup for change detection
CREATE INDEX IF NOT EXISTS idx_rp_text_hash
ON regulatory_provisions(text_hash_current);

-- ============================================================================
-- VALIDATION QUERIES
-- ============================================================================
-- Run these after migration to verify schema creation
-- ============================================================================

-- Check table exists
SELECT
    'provision_versions' as table_name,
    COUNT(*) as row_count
FROM provision_versions;

SELECT
    'provision_change_log' as table_name,
    COUNT(*) as row_count
FROM provision_change_log;

-- Check new columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'regulatory_provisions'
  AND column_name IN (
      'current_version_id',
      'first_seen_date',
      'last_modified_date',
      'version_count',
      'is_current',
      'text_hash_current'
  )
ORDER BY column_name;

-- Check indexes exist
SELECT indexname
FROM pg_indexes
WHERE tablename IN ('provision_versions', 'provision_change_log', 'regulatory_provisions')
  AND indexname LIKE '%pv%' OR indexname LIKE '%pcl%' OR indexname LIKE '%version%' OR indexname LIKE '%current%'
ORDER BY indexname;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. Run backfill script after this migration to create version 1 baseline
-- 2. All existing provisions should be marked is_current = TRUE
-- 3. text_hash_current will be NULL until backfill runs
-- 4. Foreign key constraints use ON DELETE CASCADE to prevent orphans
-- ============================================================================
