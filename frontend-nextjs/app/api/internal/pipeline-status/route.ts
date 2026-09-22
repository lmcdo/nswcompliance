// prior-art-checked: no pipeline STATUS surface exists (swept 2026-09-22).
// /internal/page.tsx is a HAND-TYPED list of routes -- its own comment says "Update
// this list when a route ships" -- so it shows no live state. /internal/dcp-review is
// for APPROVING queue rows, and /internal/setback-review for adjudicating suspect
// values; neither answers "is the pipeline running and what is waiting on me". There is
// also no run-history table (searched information_schema for run/job/monitor/log), so
// "last activity" is DERIVED from the data each stage writes.
//
// Deriving it from data rather than a run log is deliberate: it measures whether a stage
// ACHIEVED something, not whether it was invoked. The repo has been burned by the
// opposite -- a monitor that ran, wrote zero rows, and stayed green.
//
// ⚠ THE ONE THING THIS CANNOT TELL YOU: a stage that ran and legitimately found nothing
// looks identical to a stage that never ran. Closing that needs the dead-man's-switch
// (HC_PING_URL per stage, alert on ABSENCE of a success ping), which is why `staleDays`
// is surfaced per stage rather than a bare green tick.
import { NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';
import { createClient } from '@/lib/supabase/server';

export const dynamic = 'force-dynamic';

/**
 * A page gate protects a PAGE, not an endpoint. `app/internal/pipeline/page.tsx`
 * checks `supabase.auth.getUser()` and this route did not, so anyone who knew the
 * path could read council chapter names, the review queue's contents, which rows
 * were auto-rejected and why, corpus counts, and -- through the catch below --
 * raw database error text, without ever meeting the login screen.
 *
 * Copied deliberately from `app/api/internal/structure-labels/route.ts`, whose own
 * comment makes the same point, rather than invented here: this route was the odd
 * one out on the /internal surface, not the start of a new pattern.
 *
 * Returns null when the caller may proceed, a response when they may not.
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

// pool.query() returns untyped rows, so every shape this route reads is declared
// here. Without it each callback parameter is an implicit `any` and tsc fails --
// and, more importantly, a renamed column would go unnoticed until the page
// rendered blank.
interface QueueRow { council: string; chapter_key: string; status: string; n: number; newest: string | null }
interface RuleStatusRow { status: string; n: number }
interface StuckRow { council: string; chapter_key: string; url_last_changed: string | null; last_extracted_at: string | null }
interface RejectedRow { council: string; chapter_key: string; n: number }
interface FreshnessRow { detect: string | null; extract: string | null; review: string | null; approve: string | null; commit: string | null }
interface ServedRow { served: number; council_rows: number }

const DAY = 24 * 60 * 60 * 1000;

function daysSince(ts: string | Date | null): number | null {
  if (!ts) return null;
  const t = new Date(ts).getTime();
  if (Number.isNaN(t)) return null;
  return Math.floor((Date.now() - t) / DAY);
}

export async function GET() {
  const denied = await denyIfUnauthenticated();
  if (denied) return denied;

  const pool = getPool();
  try {
    const [
      queue,
      stageFreshness,
      ruleStatus,
      served,
      staleChapters,
      rejected,
    ] = await Promise.all([
      // What is sitting in the review queue, by state. 'approved' here means
      // approved-but-not-yet-committed: work that is DONE and not yet live.
      pool.query<QueueRow>(`
        SELECT council, chapter_key, status, count(*)::int AS n,
               max(created_at) AS newest
          FROM dcp_review_queue
         WHERE status IN ('pending', 'approved', 'rejected')
         GROUP BY council, chapter_key, status
         ORDER BY council, chapter_key, status
      `),

      // Last time each stage actually produced something.
      pool.query<FreshnessRow>(`
        SELECT
          (SELECT max(url_last_checked)   FROM dcp_chapter_registry)                    AS detect,
          (SELECT max(last_extracted_at)  FROM dcp_chapter_registry)                    AS extract,
          (SELECT max(created_at)         FROM dcp_review_queue)                        AS review,
          (SELECT max(reviewed_at)        FROM dcp_review_queue)                        AS approve,
          (SELECT max(last_modified_date) FROM regulatory_provisions WHERE is_current)  AS commit
      `),

      // Rule formulation: text -> structured numbers. NULL means never processed.
      pool.query<RuleStatusRow>(`
        SELECT COALESCE(v2_extraction_status, 'not_yet_processed') AS status,
               count(*)::int AS n
          FROM regulatory_provisions
         WHERE is_current AND v2_is_actionable
         GROUP BY 1 ORDER BY 2 DESC
      `),

      pool.query<ServedRow>(`
        SELECT count(*)::int AS served,
               count(*) FILTER (WHERE source_council IS NOT NULL)::int AS council_rows
          FROM regulatory_provisions
         WHERE is_current AND v2_is_actionable
      `),

      // Flagged as changed, and still not re-read. This is the "stuck chapter"
      // failure: detection keeps firing and nothing downstream picks it up.
      pool.query<StuckRow>(`
        SELECT council, chapter_key, url_last_changed, last_extracted_at
          FROM dcp_chapter_registry
         WHERE is_active AND needs_extraction
         ORDER BY url_last_changed NULLS FIRST
         LIMIT 50
      `),

      // Rows the pipeline itself refused -- machine-detectable defects it did NOT
      // leave for a human. Worth watching: a spike means a source or reader broke.
      pool.query<RejectedRow>(`
        SELECT council, chapter_key, count(*)::int AS n
          FROM dcp_review_queue
         WHERE status = 'rejected' AND suspect_reason LIKE '%artifacts:%'
         GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 20
      `),
    ]);

    const f: Partial<FreshnessRow> = stageFreshness.rows[0] ?? {};
    const stages = [
      { id: 'detect', label: 'Detect source changes', last: f.detect ?? null },
      { id: 'extract', label: 'Read PDFs into rules', last: f.extract ?? null },
      { id: 'review', label: 'Queue changes for review', last: f.review ?? null },
      { id: 'approve', label: 'Approve', last: f.approve ?? null },
      { id: 'commit', label: 'Publish to live', last: f.commit ?? null },
    ].map((s) => ({ ...s, staleDays: daysSince(s.last) }));

    const rules: RuleStatusRow[] = ruleStatus.rows;
    const notProcessed =
      rules.find((r: RuleStatusRow) => r.status === 'not_yet_processed')?.n ?? 0;
    const totalActionable = rules.reduce((a: number, r: RuleStatusRow) => a + r.n, 0);

    const queueRows: QueueRow[] = queue.rows;
    const approvedUncommitted = queueRows
      .filter((r: QueueRow) => r.status === 'approved')
      .reduce((a: number, r: QueueRow) => a + r.n, 0);
    const pending = queueRows
      .filter((r: QueueRow) => r.status === 'pending')
      .reduce((a: number, r: QueueRow) => a + r.n, 0);

    return NextResponse.json({
      generatedAt: new Date().toISOString(),
      needsYou: {
        approvedUncommitted,
        pending,
        stuckChapters: staleChapters.rowCount ?? 0,
      },
      stages,
      ruleFormulation: {
        rows: rules,
        notProcessed,
        totalActionable,
        // The headline: what fraction of served rules has a structured rule behind it.
        formulatedPct:
          totalActionable > 0
            ? Math.round(((totalActionable - notProcessed) / totalActionable) * 100)
            : null,
      },
      corpus: served.rows[0] ?? null,
      queue: queueRows,
      stuckChapters: (staleChapters.rows as StuckRow[]).map((r: StuckRow) => ({
        ...r,
        changedDaysAgo: daysSince(r.url_last_changed),
      })),
      autoRejected: rejected.rows,
    });
  } catch (err) {
    // Fail visibly, but not verbosely. A status page that renders empty on error is
    // worse than one that says it could not read -- the whole point is knowing when
    // something is wrong -- so the 500 and the message the page shows both stay.
    // What does NOT go to the caller is the driver's own text: a postgres error
    // carries the failing SQL, column names and sometimes a row value, and this
    // endpoint is reachable before the login check in any deployment where
    // NEXT_PUBLIC_AUTH_ENABLED is not 'true'. Detail goes to the server log, where
    // the person debugging it can still read it.
    console.error('[pipeline-status] query failed:', err);
    return NextResponse.json(
      { error: 'pipeline status query failed' },
      { status: 500 },
    );
  }
}
