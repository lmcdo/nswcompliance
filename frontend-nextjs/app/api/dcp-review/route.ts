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
      SELECT q.id, q.council, q.chapter_key, q.document_id, q.ref_number, q.change_type,
             q.old_text, q.new_text, q.old_page, q.new_page, q.has_numeric_change,
             q.numeric_diff, q.summary, q.crop_url, q.source_content_hash, q.created_at,
             r.r2_public_pdf_url AS pdf_url
      FROM dcp_review_queue q
      LEFT JOIN dcp_chapter_registry r
             ON r.council = q.council AND r.chapter_key = q.chapter_key
      WHERE q.status = 'pending'
      ORDER BY q.has_numeric_change DESC, q.council, q.chapter_key, q.created_at
      LIMIT 500
    `);
    return NextResponse.json({ items: rows, count: rows.length });
  } catch (e) {
    const message = e instanceof Error ? e.message : 'query failed';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
