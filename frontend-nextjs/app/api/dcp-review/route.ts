// prior-art-checked: no existing DCP review-queue API/UI in the repo (audited 2026-06-20).
// List pending DCP provision changes for human review. Reads dcp_review_queue
// (migration 051). Worst/numeric-first so the riskiest changes surface at the top.
import { NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';
import { createClient } from '@/lib/supabase/server';

export const dynamic = 'force-dynamic';

/**
 * A page gate protects a PAGE, not an endpoint. `app/internal/dcp-review/page.tsx`
 * redirects to /login; this route did not, so the whole pending queue -- council
 * chapter names, every provision's old and new text, and the fidelity gate's own
 * verdicts -- was readable by anyone who knew the path. Same shape as
 * app/api/internal/pipeline-status, fixed the same day.
 *
 * No-op unless NEXT_PUBLIC_AUTH_ENABLED is 'true', so it cannot lock anyone out of
 * an environment that does not run auth.
 */
async function denyIfUnauthenticated(): Promise<NextResponse | null> {
  if (process.env.NEXT_PUBLIC_AUTH_ENABLED !== 'true') return null;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: 'unauthorised' }, { status: 401 });
  }
  return null;
}

export async function GET() {
  const denied = await denyIfUnauthenticated();
  if (denied) return denied;

  const pool = getPool();
  try {
    const { rows } = await pool.query(`
      SELECT q.id, q.council, q.chapter_key, q.document_id, q.ref_number, q.change_type,
             q.old_text, q.new_text, q.old_page, q.new_page, q.has_numeric_change,
             q.numeric_diff, q.summary, q.crop_url, q.source_content_hash, q.created_at,
             q.suspect_reason, q.fidelity_status, q.fidelity_detail, q.source_page_verified,
             q.fidelity_source_quote,
             r.r2_public_pdf_url AS pdf_url
      FROM dcp_review_queue q
      LEFT JOIN dcp_chapter_registry r
             ON r.council = q.council AND r.chapter_key = q.chapter_key
      WHERE q.status = 'pending'
      -- Worst first, by SEVERITY rather than by one status value. The previous
      -- ordering tested fidelity_status = 'flagged' alone, so 'failed' -- which is
      -- WORSE, the gate could not match the row to its source page at all -- sorted
      -- with the unchecked bulk. Measured 2026-09-23 after re-grading the backlog:
      -- 9 rows in the whole queue needed a person, and 3 of them were 'failed', so a
      -- third of the real work sat below ~490 rows that needed nobody.
      ORDER BY CASE q.fidelity_status
                 WHEN 'failed'   THEN 0
                 WHEN 'flagged'  THEN 1
                 WHEN 'grounded' THEN 3
                 ELSE 2                 -- ungraded: unknown, so above proven-grounded
               END,
               q.has_numeric_change DESC, q.council, q.chapter_key, q.created_at
      LIMIT 500
    `);
    // Total pending across the whole queue (the SELECT is capped at 500), so the UI can
    // show the real backlog and know to load the next batch instead of falsely reporting
    // "empty" once the loaded 500 are cleared.
    const totalRes = await pool.query(
      `SELECT COUNT(*)::int AS total FROM dcp_review_queue WHERE status = 'pending'`,
    );
    const total = totalRes.rows[0]?.total ?? rows.length;
    return NextResponse.json({ items: rows, count: rows.length, total });
  } catch (e) {
    // The failure stays visible -- an empty review queue that is really a broken
    // query is how work goes unreviewed -- but the driver's own text does not go to
    // the caller. A postgres error carries the failing SQL, the column names and
    // sometimes a row value, and this route is reachable before the gate above in
    // any deployment where NEXT_PUBLIC_AUTH_ENABLED is not 'true'.
    console.error('[dcp-review] pending query failed:', e);
    return NextResponse.json({ error: 'review queue query failed' }, { status: 500 });
  }
}
