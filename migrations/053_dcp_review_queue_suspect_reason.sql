-- 053: flag guard-suspect chapters in the review queue.
--
-- The review UI dumped every provision change in a flat list with no signal of which
-- chapters the extraction guards (coverage/truncation/schema/count-drop) flagged as
-- likely-broken. Reviewers could not tell which to scrutinise and blind-approved.
-- This column stores suspect_reason(review_data) at enqueue time so the UI can group
-- by chapter and mark the flagged ones with a "check this" badge.
--
-- Nullable and additive: NULL means "not flagged" (the common case). Safe to re-run.

ALTER TABLE dcp_review_queue
    ADD COLUMN IF NOT EXISTS suspect_reason TEXT;

COMMENT ON COLUMN dcp_review_queue.suspect_reason IS
    'Guard verdict for the chapter at extraction time (count_drop / schema_fail / '
    'coverage_fail / truncation_fail), or NULL when the chapter passed all guards. '
    'Populated by enqueue_review_changes; drives the review UI "check this" badge.';
