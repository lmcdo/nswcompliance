// prior-art-checked: reuse not viable because app/api/dcp-review/* are the internal review-queue
// verdict tools and app/api/internal/pipeline-status counts needs_extraction fleet-wide for ops;
// neither answers "does THIS council have a pending change" for the public setback panel.
import { query } from '@/lib/db';

/**
 * Whether a council's DCP has a change found at source that a person has not yet
 * reviewed. Setback-only councils (bayside, liverpool, ...) never reach the
 * provisions view's "Amendment detected" line, and their flagged setback rows are
 * dropped before serving (needs_review excluded) - so without this the numbers
 * just vanish and the page says nothing.
 */
export interface DcpReviewStatus {
  /** An active chapter's served rules were read from an older file than the one we now hold. */
  amendment_pending: boolean;
  /** Current setback rows held back because the council's file changed (r2_monitor). */
  withheld_source_changed: number;
  /** Rows held back for any OTHER reason - mostly a number that did not match the
   *  council's document (measured 2026-10-22: 114 of 192). Never called an amendment. */
  withheld_other: number;
}

/** null = the check failed. Never read as "nothing pending". */
export async function fetchDcpReviewStatus(slugs: string[]): Promise<DcpReviewStatus | null> {
  if (slugs.length === 0) return null;
  try {
    const { rows } = await query(
      `SELECT
         -- Evidence of a source change, not just a queued re-read: the rules we
         -- serve were read from a different file than the one we now hold (the
         -- same test as DQ-70). needs_extraction alone is also set by a manual
         -- re-read (dcp_queue_reread.py) with no new file (cross-review).
         EXISTS (SELECT 1 FROM dcp_chapter_registry
                 WHERE council = ANY($1) AND is_active = TRUE AND needs_extraction = TRUE
                   AND provisions_extracted_from_hash IS NOT NULL
                   AND content_hash IS DISTINCT FROM provisions_extracted_from_hash)
           AS amendment_pending,
         s.withheld_source_changed, s.withheld_other
       FROM (SELECT
               count(*) FILTER (WHERE review_reason = 'chapter_pdf_changed')::int
                 AS withheld_source_changed,
               count(*) FILTER (WHERE review_reason IS DISTINCT FROM 'chapter_pdf_changed')::int
                 AS withheld_other
             FROM dcp_setback_controls
             WHERE lga = ANY($1) AND is_current = TRUE AND needs_review = TRUE) s`,
      [slugs],
    );
    const row = rows[0];
    if (!row) return null;
    return {
      amendment_pending: row.amendment_pending === true,
      withheld_source_changed: Number(row.withheld_source_changed ?? 0),
      withheld_other: Number(row.withheld_other ?? 0),
    };
  } catch (err) {
    console.error('[dcp-review-status] check failed:', err);
    return null;
  }
}
