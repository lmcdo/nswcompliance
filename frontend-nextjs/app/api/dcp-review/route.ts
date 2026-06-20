// prior-art-checked: no existing DCP review-queue API/UI in the repo (audited 2026-06-20).
// List pending DCP provision changes for human review. Reads dcp_review_queue
// (migration 051). Worst/numeric-first so the riskiest changes surface at the top.
import { NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';

export const dynamic = 'force-dynamic';

export async function GET() {
  const pool = getPool();
  try {
    const { rows } = await pool.query(`
      SELECT id, council, chapter_key, document_id, ref_number, change_type,
             old_text, new_text, old_page, new_page, has_numeric_change,
             numeric_diff, summary, crop_url, source_content_hash, created_at
      FROM dcp_review_queue
      WHERE status = 'pending'
      ORDER BY has_numeric_change DESC, council, chapter_key, created_at
      LIMIT 500
    `);
    return NextResponse.json({ items: rows, count: rows.length });
  } catch (e) {
    const message = e instanceof Error ? e.message : 'query failed';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
