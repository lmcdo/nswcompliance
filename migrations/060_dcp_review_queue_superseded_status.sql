-- Allow 'superseded' in dcp_review_queue.status (issue: PR #830 follow-up).
--
-- #830 made re-extraction flip prior 'rejected' rows to 'superseded' (audit
-- history that stops blocking the chapter's commit), and the triage flow marks
-- stale approved rows the same way — but the status CHECK constraint predates
-- the value, so the first real supersede would crash with a CheckViolation.
-- Widening a CHECK is additive: no existing row is affected.

ALTER TABLE dcp_review_queue
  DROP CONSTRAINT dcp_review_queue_status_chk;

ALTER TABLE dcp_review_queue
  ADD CONSTRAINT dcp_review_queue_status_chk CHECK (
    status = ANY (ARRAY[
      'pending'::text, 'in_progress'::text, 'approved'::text,
      'rejected'::text, 'needs_info'::text, 'superseded'::text
    ])
  );
