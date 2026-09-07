/**
 * GET /api/dcp/coverage
 *
 * Returns councils that have structured DCP controls in dcp_setback_controls.
 * Uses lga_registry as single source of truth for display names. A
 * sub-council's rows (e.g. Ashfield, a legacy pre-2016-merger LGA) are
 * aggregated under its CURRENT parent council's display name (Inner West) —
 * the former councils no longer exist as their own local government areas,
 * so listing them separately would misstate real-world coverage.
 * Excludes nsw_statewide (SEPP/ADG, not a council DCP).
 *
 * Response: { councils: string[] }
 *   e.g. ["Bayside", "Blacktown", ..., "Woollahra"]
 */

import { NextResponse } from 'next/server';
import { getPool } from '@/lib/db';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const pool = getPool();

    // Join against lga_registry for display names, LEFT JOINed a second
    // time to resolve a sub-council's CURRENT parent (Ashfield/Leichhardt/
    // Marrickville -> Inner West). Exclude nsw_statewide (SEPP/ADG, not a
    // council DCP) and gate on needs_review, matching the standard guard
    // every serving path uses — a council counts as covered only by rows
    // the serving path would actually serve.
    //
    // FIXED 2026-09-07 (the "known gap, deliberately left for a ruling"
    // this comment used to name): previously filtered on `r.parent_lga IS
    // NULL`, meant to bucket a sub-council's rows under its parent's
    // display name — but Inner West's own registry row carries zero
    // current controls, so the filter silently DROPPED Ashfield/
    // Leichhardt/Marrickville entirely instead of showing them under
    // anything. First attempt at this fix (same day) just removed the
    // filter with no aggregation, which listed the three abolished
    // pre-2016-merger councils as separate CURRENT councils, overstating
    // coverage the opposite way — caught by Sol cross-review (HIGH 0.96)
    // on push, fixed before merge, not after. Verified against production:
    // the correct parent-aware count is 26 (25 + Inner West, newly
    // surfaced), not 28 and not 25.
    // COUNT re-measured 2026-09-07: 26. See ~/.claude/plans/
    // ce-verified-capability-statement-2026-08.md §3.2 and
    // frontend-nextjs/lib/coverage.ts's dcpNumericCouncils field, updated
    // to match in the same change.
    //
    // r.is_active / parent.is_active: neither lga_registry row (child or
    // resolved parent) may be retired. 0 rows are currently inactive, so
    // this is a defensive guard against a future state, not today's fix --
    // added per this project's own pre-pr-review rule (every SELECT needs
    // an explicit currency filter), caught by qa_gate's static DB guard.
    const result = await pool.query(
      `SELECT DISTINCT COALESCE(parent.display_name, r.display_name) AS display_name
       FROM dcp_setback_controls c
       JOIN lga_registry r ON r.slug = c.lga
       LEFT JOIN lga_registry parent ON parent.slug = r.parent_lga
       WHERE c.is_current = TRUE
         AND (c.needs_review IS NULL OR c.needs_review = FALSE)
         AND r.slug != 'nsw_statewide'
         AND r.is_active = TRUE
         AND (parent.is_active IS NULL OR parent.is_active = TRUE)
       ORDER BY display_name`,
    );

    const councils = result.rows.map(r => r.display_name as string);

    return NextResponse.json({ councils });
  } catch (err) {
    console.error('[dcp/coverage] DB error:', err);
    return NextResponse.json({ councils: [] }, { status: 500 });
  }
}
