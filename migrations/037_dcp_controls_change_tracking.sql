-- Migration 037: Add change-tracking columns to dcp_setback_controls
--
-- Problem: when a DCP chapter PDF changes, provisions get re-extracted
-- automatically, but structured control rows in dcp_setback_controls are
-- NOT flagged for review. This means stale values can be served indefinitely.
--
-- Solution: link each control row to its source chapter, and flag rows
-- for human review when that chapter is re-extracted after a PDF change.

-- source_chapter_key: links this row to dcp_chapter_registry.chapter_key
-- so we can identify which control rows are affected when a chapter changes.
ALTER TABLE dcp_setback_controls
  ADD COLUMN IF NOT EXISTS source_chapter_key text;

-- needs_review: set TRUE when the source chapter PDF changes and provisions
-- are re-extracted. Human must verify the control value is still correct
-- before clearing this flag.
ALTER TABLE dcp_setback_controls
  ADD COLUMN IF NOT EXISTS needs_review boolean NOT NULL DEFAULT FALSE;

-- review_reason: why this row was flagged — for Telegram alert context.
-- Values: 'chapter_pdf_changed' | 'manual_staleness_check'
ALTER TABLE dcp_setback_controls
  ADD COLUMN IF NOT EXISTS review_reason text;

-- reviewed_at: timestamp when a human last verified this row is correct.
-- Cleared (set NULL) when needs_review is set TRUE, stamped when cleared.
ALTER TABLE dcp_setback_controls
  ADD COLUMN IF NOT EXISTS reviewed_at timestamptz;

-- Index for the watchdog query: find all rows needing review
CREATE INDEX IF NOT EXISTS dcp_setback_controls_needs_review
  ON dcp_setback_controls(needs_review)
  WHERE needs_review = TRUE;

-- Index for the chapter-change flagging query: find control rows by (lga, source_chapter_key)
CREATE INDEX IF NOT EXISTS dcp_setback_controls_source_chapter
  ON dcp_setback_controls(lga, source_chapter_key)
  WHERE source_chapter_key IS NOT NULL AND is_current = TRUE;

COMMENT ON COLUMN dcp_setback_controls.source_chapter_key IS
  'Matches dcp_chapter_registry.chapter_key — links this control row to the '
  'chapter it was extracted from. Used to flag rows for review when that chapter changes.';

COMMENT ON COLUMN dcp_setback_controls.needs_review IS
  'TRUE when the source chapter PDF has changed and this row may be stale. '
  'Human must verify the value, then SET needs_review=FALSE, reviewed_at=now().';

COMMENT ON COLUMN dcp_setback_controls.review_reason IS
  'Why this row was flagged: chapter_pdf_changed (automated after re-extraction), '
  'manual_staleness_check (watchdog time-based fallback).';

COMMENT ON COLUMN dcp_setback_controls.reviewed_at IS
  'Last time a human verified this row is correct. NULL = never reviewed since flagging.';
