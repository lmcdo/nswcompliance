-- 054: record whether a queued chapter is a FULL re-extraction or a targeted amendment.
--
-- The commit worker replaces a whole chapter (soft-delete all current provisions, insert
-- the queue). That is correct for a full re-extraction / baseline, but WRONG for a
-- targeted amendment where only a few provisions changed — it would delete the unchanged
-- ones. This flag lets the commit tell the two apart:
--   TRUE  -> full replace (restructure or empty baseline): blanket soft-delete + insert.
--   FALSE -> targeted diff: supersede only the changed/removed refs, keep the rest.
--   NULL  -> legacy rows enqueued before this column; treated as full replace (the
--            current leichhardt baseline is all full re-extractions, verified safe).
--
-- Nullable and additive. Safe to re-run.

ALTER TABLE dcp_review_queue
    ADD COLUMN IF NOT EXISTS is_full_replace BOOLEAN;

COMMENT ON COLUMN dcp_review_queue.is_full_replace IS
    'TRUE = the chapter was fully re-extracted (restructure/empty baseline) -> commit '
    'blanket-replaces it; FALSE = targeted amendment -> commit updates only the changed '
    'refs and leaves unchanged provisions intact; NULL = legacy, treated as full replace.';
