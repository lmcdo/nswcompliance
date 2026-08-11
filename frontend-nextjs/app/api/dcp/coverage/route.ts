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
    // Exclude nsw_statewide (SEPP/ADG, not a council DCP) and
    // sub-councils with a parent_lga (shown under parent, e.g. Inner West).
    // Metadata reader (item 5): keeps direct SQL by design but carries the
    // standard guard predicates — a council counts as covered only by rows
    // the serving path would actually serve.
    //
    // COUNT, re-measured 2026-08-08 by running this exact query: it returns 25.
    // The previous comment here said "28 -> 28" and was wrong. Reconciliation:
    //   30 distinct `lga` values in dcp_setback_controls
    //   -1  nsw_statewide (not a council)
    //   -1  inner_west     (29 rows, ALL is_current = FALSE, so no clean row)
    //   -3  ashfield / leichhardt / marrickville (parent_lga = 'inner_west')
    //   = 25
    // KNOWN GAP, deliberately left for a ruling rather than patched here: the
    // three Inner West former councils are excluded by parent_lga, and their
    // parent has no current rows to be shown under — so 99 current controls,
    // and the only three councils with full DCP integration, are invisible to
    // the endpoint that answers "which councils do you cover".
    // See ~/.claude/plans/ce-verified-capability-statement-2026-08.md §3.2.
    const result = await pool.query(
      `SELECT DISTINCT r.display_name
       FROM dcp_setback_controls c
       JOIN lga_registry r ON r.slug = c.lga
       WHERE c.is_current = TRUE
         AND (c.needs_review IS NULL OR c.needs_review = FALSE)
         AND r.slug != 'nsw_statewide'
         AND r.parent_lga IS NULL
       ORDER BY r.display_name`,
    );

    const councils = result.rows.map(r => r.display_name as string);

    return NextResponse.json({ councils });
  } catch (err) {
    console.error('[dcp/coverage] DB error:', err);
    return NextResponse.json({ councils: [] }, { status: 500 });
  }
}
