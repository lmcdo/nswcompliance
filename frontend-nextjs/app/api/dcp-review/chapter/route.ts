// prior-art-checked: the per-id route (../[id]/route.ts) records ONE verdict; this
// records the SAME verdict for every pending row of one (council, chapter_key) so a
// human can accept/reject a whole reviewed chapter in a single click. It is still a
// human-initiated action (the reviewer clicks the button) — it does not bypass the
// review gate, it just batches it. Never mutates regulatory_provisions.
import { NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';
import { requireReviewer } from '@/lib/internal-reviewer';
import { ACTION_TO_STATUS } from '../_status';

export async function POST(req: Request) {
  const { reviewer, denied } = await requireReviewer();
  if (denied) return denied;

  const body = await req.json().catch(() => ({} as Record<string, unknown>));
  const action = typeof body?.action === 'string' ? body.action : '';
  const council = typeof body?.council === 'string' ? body.council : '';
  const chapterKey = typeof body?.chapter_key === 'string' ? body.chapter_key : '';
  const status = ACTION_TO_STATUS[action];
  if (!status) {
    return NextResponse.json({ error: 'invalid action' }, { status: 400 });
  }
  if (!council || !chapterKey) {
    return NextResponse.json({ error: 'council and chapter_key are required' }, { status: 400 });
  }

  const reason = typeof body?.reason === 'string' ? body.reason : null;
  const pool = getPool();
  try {
    const { rowCount } = await pool.query(
      `UPDATE dcp_review_queue
          SET status = $1, reviewed_by = $2, reviewed_at = NOW(), review_reason = $3
        WHERE council = $4 AND chapter_key = $5
          AND status IN ('pending', 'in_progress')`,
      [status, reviewer, reason, council, chapterKey],
    );
    if (!rowCount) {
      return NextResponse.json(
        { error: 'no pending rows for that chapter' },
        { status: 404 },
      );
    }
    return NextResponse.json({
      ok: true,
      council,
      chapter_key: chapterKey,
      status,
      reviewed_by: reviewer,
      count: rowCount,
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : 'update failed';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
