BEGIN;

-- Migration 035: Add registration_status to dcp_chapter_registry
-- Supports auto-detection of new chapters from hub scrapes.
-- Values: 'confirmed' (existing/manually added), 'auto_detected' (discovered by monitor),
--         'rejected' (reviewed and dismissed)

ALTER TABLE dcp_chapter_registry
  ADD COLUMN IF NOT EXISTS registration_status TEXT NOT NULL DEFAULT 'confirmed';

-- Index for quick lookups of pending auto-detected chapters
CREATE INDEX IF NOT EXISTS idx_dcp_chapter_registration_status
  ON dcp_chapter_registry (registration_status)
  WHERE registration_status = 'auto_detected';

COMMIT;
