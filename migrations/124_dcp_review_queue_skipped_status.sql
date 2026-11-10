-- Allow 'skipped' in dcp_review_queue.status: "a correct reading, but not a rule — do not publish it".
--
-- Until now a reviewer had three verdicts: approve, reject, needs-info. 'rejected' deliberately blocks the
-- chapter's commit (dcp_commit_approved.find_committable_chapters): it means "this reading is wrong, re-read".
-- So a reviewer who only wanted to leave out non-rule text (heritage history, colour tables, contents lines)
-- had to block the whole chapter. Waverley DCP 2022 Amendment 6 (2026-11-10): 7,062 rows approved and 256
-- non-rule rows held the chapter back.
--
-- 'skipped' does not block: the commit applies approved rows only (status = 'approved' everywhere it reads
-- the queue), so a skipped row is simply not published. Widening a CHECK is additive: no existing row changes.

BEGIN;

ALTER TABLE dcp_review_queue
  DROP CONSTRAINT dcp_review_queue_status_chk;

ALTER TABLE dcp_review_queue
  ADD CONSTRAINT dcp_review_queue_status_chk CHECK (
    status = ANY (ARRAY[
      'pending'::text, 'in_progress'::text, 'approved'::text,
      'rejected'::text, 'needs_info'::text, 'superseded'::text, 'skipped'::text
    ])
  );

COMMIT;
