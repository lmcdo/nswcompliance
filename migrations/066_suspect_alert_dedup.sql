-- 066_suspect_alert_dedup.sql
--
-- Stop the daily SUSPECT alert repeating an unchanged condition.
--
-- WHY THIS EXISTS
-- ---------------
-- Between 1 and 13 August 2026 the VerifyOpsBot channel received a
-- byte-identical message every single day:
--
--   DCP extract: 2 SUSPECT chapter(s) for 'all' — review before approving:
--   • [city_of_sydney] section-3-general-provisions: preflight_two_column (...)
--   • [hornsby] part-1-general: preflight_two_column (...)
--
-- Thirteen consecutive days, same two chapters, same wording. The extractor
-- runs nightly and re-derives the same flags from the same unchanged PDFs, and
-- the alert had no memory, so "this is new" and "this is still true" were
-- indistinguishable. An operator learns within a week that the message carries
-- no information and stops reading the channel — which is how the far more
-- serious signals in the same channel (numeric value changes, stuck chapters)
-- went unactioned for weeks.
--
-- THE KEY IS (content_hash, reason), NOT content_hash ALONE
-- ---------------------------------------------------------
-- Keying on the hash alone would silence a chapter whose PDF is unchanged but
-- whose failure MODE changed — e.g. a chapter that was flagged two_column and
-- now also drops half its provisions. That is new information and must alert.
-- Keying on the reason alone would re-alert on every re-export of an identical
-- document. Both parts are required.
--
-- WHY NOT A NEW TABLE
-- -------------------
-- dcp_chapter_registry already holds this chapter's operational state
-- (check_failures, needs_extraction, url_last_checked, content_hash,
-- provisions_extracted_from_hash). A separate alert-state table would be a
-- parallel surface keyed identically, with its own drift.
--
-- NULL MEANS NEVER ALERTED — AND THAT IS THE SAFE DIRECTION
-- ---------------------------------------------------------
-- Both columns are nullable with no default and there is deliberately NO
-- backfill. Every existing chapter therefore reads as "never alerted", so the
-- first run after this deploys alerts once for anything still flagged and only
-- then goes quiet. Suppression that starts by hiding a live condition would be
-- the wrong failure direction.
--
-- SUPPRESSED IS NOT SILENT
-- ------------------------
-- The weekly dcp_watchdog independently reports the same review-blocked
-- chapters, and since 2026-08-14 reports their true age from the chapter flag.
-- That is the standing digest; this migration only removes the daily repeat.
-- If that watchdog check is ever removed, this suppression must be removed with
-- it, or a real condition can go unreported.

BEGIN;

ALTER TABLE dcp_chapter_registry
  ADD COLUMN IF NOT EXISTS last_suspect_alert_key TEXT,
  ADD COLUMN IF NOT EXISTS last_suspect_alert_at  TIMESTAMPTZ;

COMMENT ON COLUMN dcp_chapter_registry.last_suspect_alert_key IS
  'content_hash::reason of the last SUSPECT alert sent for this chapter. NULL = never alerted. Set by dcp_extract_changed.py after a successful send; a differing key re-alerts.';
COMMENT ON COLUMN dcp_chapter_registry.last_suspect_alert_at IS
  'When the last SUSPECT alert was sent for this chapter. Diagnostic only — suppression is decided by last_suspect_alert_key, never by elapsed time.';

COMMIT;
