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
  /** An active chapter is waiting to be re-read from a newer council file. */
  amendment_pending: boolean;
  /** Current setback rows held back from the page until reviewed. */
  withheld_controls: number;
}

/** null = the check failed. Never read as "nothing pending". */
export async function fetchDcpReviewStatus(slugs: string[]): Promise<DcpReviewStatus | null> {
  if (slugs.length === 0) return null;
  try {
    const { rows } = await query(
      `SELECT
         EXISTS (SELECT 1 FROM dcp_chapter_registry
                 WHERE council = ANY($1) AND is_active = TRUE AND needs_extraction = TRUE)
           AS amendment_pending,
         (SELECT count(*)::int FROM dcp_setback_controls
          WHERE lga = ANY($1) AND is_current = TRUE AND needs_review = TRUE)
           AS withheld_controls`,
      [slugs],
    );
    const row = rows[0];
    if (!row) return null;
    return {
      amendment_pending: row.amendment_pending === true,
      withheld_controls: Number(row.withheld_controls ?? 0),
    };
  } catch (err) {
    console.error('[dcp-review-status] check failed:', err);
    return null;
  }
}
