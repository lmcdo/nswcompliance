-- Migration 049: drop computed_at DEFAULT NOW() on lot_search_index
--
-- Bug: `computed_at TIMESTAMPTZ DEFAULT NOW()` (migration 048) pre-stamps every
-- Phase-1 base insert as "computed". Phase-2's `computed_at IS NULL` filter then
-- sees 0 pending lots and silently skips them — so newly inserted lots never get
-- constraint arithmetic even though FSR/height are present.
--
-- Fix: drop the default so base rows have computed_at = NULL until Phase-2 stamps
-- them. Recompute of existing rows is handled by the build script's --recompute
-- flag (scoped per-LGA reset of computed_at).
--
-- Apply BEFORE running the FSR backfill campaign.

ALTER TABLE lot_search_index ALTER COLUMN computed_at DROP DEFAULT;
