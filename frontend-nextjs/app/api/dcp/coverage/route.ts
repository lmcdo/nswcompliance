/**
 * GET /api/dcp/coverage
 *
 * Returns councils that have structured DCP controls in dcp_setback_controls.
 * Uses lga_registry as single source of truth for display names.
 * Excludes nsw_statewide and Inner West sub-councils (shown under parent).
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

    // Join against lga_registry for display names.
    // Exclude nsw_statewide (SEPP/ADG, not a council DCP). Metadata reader
    // (item 5): keeps direct SQL by design but carries the standard guard
    // predicates — a council counts as covered only by rows the serving
    // path would actually serve.
    //
    // FIXED 2026-09-07 (the "known gap, deliberately left for a ruling"
    // this comment used to name): no longer filters on `r.parent_lga IS
    // NULL`. That filter was meant to bucket a sub-council's rows under its
    // parent's display name (e.g. "shown under Inner West"), but Inner
    // West's own registry row carries zero current controls — so the
    // filter silently dropped Ashfield/Leichhardt/Marrickville entirely
    // instead of showing them under anything. Those three carry 99 current
    // controls and are the only councils with full DCP integration in the
    // product; they were invisible to the one endpoint that answers "which
    // councils do you cover". Verified against production before shipping:
    // dropping the filter takes the result from 25 to 28, adding exactly
    // those three, zero duplicates, no other change.
    // COUNT re-measured 2026-09-07: 28. See ~/.claude/plans/
    // ce-verified-capability-statement-2026-08.md §3.2 and
    // frontend-nextjs/lib/coverage.ts's dcpNumericCouncils field, updated
    // to match in the same change.
    const result = await pool.query(
      `SELECT DISTINCT r.display_name
       FROM dcp_setback_controls c
       JOIN lga_registry r ON r.slug = c.lga
       WHERE c.is_current = TRUE
         AND (c.needs_review IS NULL OR c.needs_review = FALSE)
         AND r.slug != 'nsw_statewide'
       ORDER BY r.display_name`,
    );

    const councils = result.rows.map(r => r.display_name as string);

    return NextResponse.json({ councils });
  } catch (err) {
    console.error('[dcp/coverage] DB error:', err);
    return NextResponse.json({ councils: [] }, { status: 500 });
  }
}
