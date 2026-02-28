-- Migration 008: Extraction pipeline columns
-- Adds source tracing and soft-delete support for chapter-scoped re-extraction.
-- Adds audit columns to dcp_chapter_registry for tracking extraction runs.
--
-- Run with:
--   python scripts/run_migration_008.py
--   (or: psql $DATABASE_URL -f migrations/008_extraction_columns.sql)

BEGIN;

-- ── regulatory_provisions: source tracing ─────────────────────────────────
-- source_chapter_key: matches chapter_key in dcp_chapter_registry
-- source_council: matches council in dcp_chapter_registry
-- is_current: FALSE for provisions superseded by a re-extraction
-- Existing provisions get NULL in source columns — correct, extracted by old pipeline.
-- Existing provisions default is_current=TRUE — they remain live.

ALTER TABLE regulatory_provisions
  ADD COLUMN IF NOT EXISTS source_chapter_key TEXT,
  ADD COLUMN IF NOT EXISTS source_council      TEXT,
  ADD COLUMN IF NOT EXISTS is_current          BOOLEAN NOT NULL DEFAULT TRUE;

-- Partial index for fast chapter-scoped queries during re-extraction
CREATE INDEX IF NOT EXISTS idx_rp_source_chapter
  ON regulatory_provisions (source_council, source_chapter_key)
  WHERE is_current = TRUE AND source_chapter_key IS NOT NULL;

-- ── dcp_chapter_registry: extraction audit ────────────────────────────────
ALTER TABLE dcp_chapter_registry
  ADD COLUMN IF NOT EXISTS last_extracted_at      TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_extracted_version TEXT;

COMMIT;
