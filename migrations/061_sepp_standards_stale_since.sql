-- SEPP auto-stale (regulatory-currency plan W3; founder decision 2026-07-29).
--
-- When the legislation monitor detects a version change of a source
-- instrument, dependent standards rows are marked STALE — NOT retired. The
-- founder-specified behaviour: reports keep showing the last-reviewed values
-- WITH a visible notice that the instrument changed and a re-check is
-- pending. stale_since/stale_reason are cleared during re-verification
-- (UPDATE ... SET stale_since = NULL, stale_reason = NULL after the founder
-- re-checks values against the amended instrument).
--
-- Additive columns; NULL = current behaviour, nothing changes until the
-- monitor first marks a row.

ALTER TABLE cdc_eligibility_standards
  ADD COLUMN IF NOT EXISTS stale_since  timestamptz,
  ADD COLUMN IF NOT EXISTS stale_reason text;

ALTER TABLE housing_sepp_standards
  ADD COLUMN IF NOT EXISTS stale_since  timestamptz,
  ADD COLUMN IF NOT EXISTS stale_reason text;
