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
    const result = await pool.query(
      `SELECT DISTINCT r.display_name
       FROM dcp_setback_controls c
       JOIN lga_registry r ON r.slug = c.lga
       WHERE c.is_current = TRUE
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
