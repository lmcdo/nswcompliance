-- Migration 030: Add is_inert flag to dcp_chapter_registry
-- =========================================================
-- is_inert = cover pages, table of contents, and other non-provision PDFs
-- that change cosmetically (e.g. amendment date on cover) but contain no
-- extractable development controls.
--
-- Behaviour in r2_monitor.py:
--   is_inert=FALSE (default) -- normal: hash-checked, extraction triggered on change
--   is_spatial=TRUE          -- map/boundary: hash-checked, no extraction, Telegram alert
--   is_inert=TRUE            -- cover/ToC: hash-checked, no extraction, NO alert (silent)
--
-- is_spatial and is_inert are mutually exclusive.
--
-- Run with:
--   psql $DATABASE_URL -f migrations/030_dcp_chapter_registry_is_inert.sql

BEGIN;

ALTER TABLE dcp_chapter_registry
    ADD COLUMN IF NOT EXISTS is_inert BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN dcp_chapter_registry.is_inert IS
    'TRUE for cover pages, ToC, and other PDFs with no extractable provisions. '
    'Hash-tracked so changes are recorded, but no extraction is triggered and '
    'no Telegram alert is sent. Use --inert flag in add_new_chapter.py.';

-- Backfill known cover/ToC entries
UPDATE dcp_chapter_registry
SET is_inert = TRUE
WHERE (council, chapter_key) IN (
    ('leichhardt',   'cover'),
    ('leichhardt',   'toc'),
    ('marrickville', 'cover'),
    ('marrickville', 'toc'),
    ('marrickville', 'cover-part-4'),
    ('marrickville', 'cover-part-7'),
    ('marrickville', 'cover-part-9')
);

COMMIT;
