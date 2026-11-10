-- 125: hold a council's new chapter file to one side until the reviewed rules are published.
--
-- WHY. Intake (scripts/r2_monitor.py, incl. --from-file) used to re-point the LIVE registry row
-- (r2_current_path, r2_public_pdf_url, content_hash) at the new file at once. Two things broke while the
-- reviewed rules were still the old edition's:
--   1. every live page link opened the NEW file at the OLD page numbers;
--   2. the r2_current_path change fires migrations 078/079/111/112, which clear the citation, page and
--      quote proofs of every rule in the chapter (Waverley Amdt 6, 2026-11-10: DQ-145 131 -> 3,077,
--      2,946 quotes wiped). Undone by hand four times that day.
--
-- WHAT. New file + fingerprint go in the staged_* columns. Live columns do not move. The extractor, the
-- auto-approver and the commit worker read COALESCE(staged_*, live). dcp_commit_approved.py switches the
-- live row to the staged file in the SAME transaction as the publish (scripts/dcp_staged.py), then re-runs
-- the proof scripts. A chapter with no live file (first load) has nothing to protect and is not staged.
--
-- Additive: nullable columns, no row changes, no trigger changes. NULL staged_r2_path = nothing staged.

BEGIN;

ALTER TABLE dcp_chapter_registry
    ADD COLUMN IF NOT EXISTS staged_r2_path            text,
    ADD COLUMN IF NOT EXISTS staged_version_label      text,
    ADD COLUMN IF NOT EXISTS staged_public_pdf_url     text,
    ADD COLUMN IF NOT EXISTS staged_content_hash       text,
    ADD COLUMN IF NOT EXISTS staged_url_content_length bigint,
    ADD COLUMN IF NOT EXISTS staged_at                 timestamptz;

COMMENT ON COLUMN dcp_chapter_registry.staged_r2_path IS
  'New council file received but not yet published. Live page links and proofs still use r2_current_path. Switched by dcp_commit_approved.py (scripts/dcp_staged.py).';

COMMIT;
