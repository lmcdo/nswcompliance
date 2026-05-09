BEGIN;

-- Migration 036: Track which PDF version provisions were extracted from
-- Enables single-query staleness check:
--   SELECT * FROM dcp_chapter_registry
--   WHERE content_hash != provisions_extracted_from_hash
--     AND is_active = TRUE
--
-- NULL = never extracted. Set by dcp-commit workflow after successful extraction.

ALTER TABLE dcp_chapter_registry
  ADD COLUMN IF NOT EXISTS provisions_extracted_from_hash TEXT;

-- Backfill: chapters with needs_extraction=FALSE and a content_hash
-- have provisions matching their current PDF.
-- Chapters with needs_extraction=TRUE are stale — leave NULL.
-- Liverpool (content_hash IS NULL) also left NULL — never extracted.
UPDATE dcp_chapter_registry
SET provisions_extracted_from_hash = content_hash
WHERE is_active = TRUE
  AND needs_extraction = FALSE
  AND content_hash IS NOT NULL;

COMMIT;
