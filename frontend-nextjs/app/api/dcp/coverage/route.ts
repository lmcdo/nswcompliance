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
    //
    // Round 2 (Sol HIGH 0.99): the first version of this guard,
    // `parent.is_active IS NULL OR parent.is_active = TRUE`, was meant to
    // let a PARENTLESS row (parent_lga IS NULL, so the LEFT JOIN naturally
    // produces NULL parent.* fields) pass through on its own name -- but
    // it ALSO let a row that DOES declare a parent_lga through whenever
    // the parent registry row was missing or itself had NULL is_active,
    // which would surface the abolished child's own name via COALESCE's
    // fallback instead of being excluded. Corrected to require an
    // explicitly ACTIVE parent whenever one is declared: a row only
    // passes on its own name if it has no parent at all.
    const result = await pool.query(
      `SELECT DISTINCT COALESCE(parent.display_name, r.display_name) AS display_name
       FROM dcp_setback_controls c
       JOIN lga_registry r ON r.slug = c.lga
       LEFT JOIN lga_registry parent ON parent.slug = r.parent_lga
       WHERE c.is_current = TRUE
         AND (c.needs_review IS NULL OR c.needs_review = FALSE)
         AND r.slug != 'nsw_statewide'
         AND r.is_active = TRUE
         AND (r.parent_lga IS NULL OR parent.is_active = TRUE)
       ORDER BY display_name`,
    );

    // display_name is NOT NULL on lga_registry (checked live against
    // production: is_nullable='NO', 0 NULL rows) on both sides of the
    // COALESCE, so this cast is sound today. Guarded anyway (Sol HIGH
    // 0.99): a future migration relaxing that constraint would otherwise
    // silently serve `{"councils":[null]}` with no visible failure. Fail
    // closed like every other error path here, not fail open with a
    // malformed entry.
    const councils = result.rows.map(r => {
      const name = r.display_name;
      if (typeof name !== 'string' || name.trim() === '') {
        throw new Error(`[dcp/coverage] non-string display_name in result row: ${JSON.stringify(r)}`);
      }
      return name;
    });

    return NextResponse.json({ councils });
  } catch (err) {
    console.error('[dcp/coverage] DB error:', err);
    return NextResponse.json({ councils: [] }, { status: 500 });
  }
}
