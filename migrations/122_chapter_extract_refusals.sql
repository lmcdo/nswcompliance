-- 122: remember how often a chapter's CURRENT PDF has been refused by the extractor.
--
-- The daily dcp-extract re-read every flagged chapter, including one the extractor refuses
-- every time on an unchanged file: canterbury_bankstown chapter-7-6 was refused four times
-- on 2026-11-03 (PageLoss, pages 64 and 139), about ten minutes and model credit a run,
-- and always ahead of the chapter that needed reading. Nothing recorded the refusals, so
-- every run tried again.
--
-- dcp_extract_changed.py counts refusals per content hash. After 2 on the same hash the
-- daily run holds the chapter for 7 days and prints it, then tries once more (the
-- watchdog's >48h needs_extraction alarm keeps a held chapter visible meanwhile); a new PDF (new hash) ends the hold; a
-- named --chapter re-read bypasses it.

ALTER TABLE dcp_chapter_registry
    ADD COLUMN IF NOT EXISTS extract_refusals integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS extract_refused_hash text,
    ADD COLUMN IF NOT EXISTS extract_refused_reason text,
    ADD COLUMN IF NOT EXISTS extract_refused_at timestamptz;
