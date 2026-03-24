-- Migration 012: Retire old-format Marrickville provision document_ids
-- Purpose: Marrickville DCP was imported three times with different document_id conventions:
--   1. double-underscore-dash: Marrickville__DCP__2011__-__2__10__Parking (source_chapter_key = null)
--   2. single-dash:            Marrickville_DCP_2011_-_2_10_Parking      (source_chapter_key = null)
--   3. new-clean:              Marrickville_DCP_2011__part2_s10_parking   (source_chapter_key = part2-s10-parking)
--
-- All three formats currently have is_current = TRUE, causing every property query to
-- return 3x the provisions (duplication). After migration 011, the TOC document_ids
-- use new-clean format — so only new-clean provisions get TOC section matches.
--
-- Fix: retire formats 1 and 2 (set is_current = FALSE). New-clean becomes canonical.
--   - New-clean covers 83 chapters (77 from old formats + 6 new sections s20-s26)
--   - Old-format provisions are NOT deleted — da_responses references provision_id (int PK)
--   - Existing session responses remain intact; new queries return only new-clean
--
-- Verified: 2026-03-21
--   Single-dash: 1014 is_current = true → to be retired
--   Double-us-dash: 614 is_current = true → to be retired
--   New-clean: 457 is_current = true (83 distinct chapters) → canonical

BEGIN;

-- Retire double-underscore-dash format (source_chapter_key = null, old import)
UPDATE regulatory_provisions
SET is_current = FALSE
WHERE document_id LIKE 'Marrickville__%__%__%'
  AND document_id NOT LIKE 'Marrickville_DCP_%'
  AND is_current = TRUE;

-- Retire single-dash format (source_chapter_key = null, old import)
UPDATE regulatory_provisions
SET is_current = FALSE
WHERE document_id LIKE 'Marrickville_DCP_2011_-_%'
  AND is_current = TRUE;

COMMIT;

-- Verification queries (run after applying):
-- SELECT count(*), is_current FROM regulatory_provisions
--   WHERE document_id LIKE 'Marrickville%' GROUP BY is_current;
-- Expected: old formats (1628) now is_current=false, new-clean (457) still is_current=true
