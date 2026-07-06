// prior-art-checked: no existing extracted-value trust-review API/UI in the repo
// (audited 2026-07-02). The /api/dcp-review queue is DCP change-DETECTION (a
// separate staging table, migration 051); this reviews suspect VALUES already
// live in dcp_setback_controls, flagged by the data-integrity checker.
//
// Lists setback control rows a human must verify — rows the checker/watchdog
// flagged (needs_review) that are still being served (is_current). The riskiest
// data in the system (DCP prose-extracted numbers), surfaced value-next-to-clause.
import { NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';

export const dynamic = 'force-dynamic';

export async function GET() {
  const pool = getPool();
  try {
    const { rows } = await pool.query(`
      SELECT id, lga, dev_type, control_type, value_min, value_max, unit,
             condition, section_ref, source_text, review_reason,
             reviewed_at, source_chapter_key
      FROM dcp_setback_controls
      WHERE needs_review = TRUE AND is_current = TRUE
      ORDER BY lga, control_type, dev_type, id
      LIMIT 500
    `);
    return NextResponse.json({ items: rows, count: rows.length });
  } catch (e) {
    const message = e instanceof Error ? e.message : 'query failed';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
