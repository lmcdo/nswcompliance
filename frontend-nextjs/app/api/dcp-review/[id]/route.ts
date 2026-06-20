// prior-art-checked: no existing DCP review-queue API/UI in the repo (audited 2026-06-20).
// Record a human verdict on a queued DCP change. Increment 3 records the verdict
// + audit trail ONLY (reviewed_by/at/reason). Commit-on-approve — writing approved
// provisions to regulatory_provisions — is wired in increment 4; this never mutates
// regulatory data.
import { NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';
import { createClient } from '@/lib/supabase/server';

const ACTION_TO_STATUS: Record<string, string> = {
  approve: 'approved',
  reject: 'rejected',
  'needs-info': 'needs_info',
};

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const body = await req.json().catch(() => ({} as Record<string, unknown>));
  const action = typeof body?.action === 'string' ? body.action : '';
  const status = ACTION_TO_STATUS[action];
  if (!status) {
    return NextResponse.json({ error: 'invalid action' }, { status: 400 });
  }

  // Named reviewer for the audit trail.
  let reviewer = 'unknown';
  try {
    const supabase = await createClient();
    const { data: { user } } = await supabase.auth.getUser();
    if (user?.email) reviewer = user.email;
  } catch {
    // auth optional in this environment — fall back to 'unknown'
  }

  const reason = typeof body?.reason === 'string' ? body.reason : null;
  const pool = getPool();
  try {
    const { rowCount } = await pool.query(
      `UPDATE dcp_review_queue
          SET status = $1, reviewed_by = $2, reviewed_at = NOW(), review_reason = $3
        WHERE id = $4 AND status IN ('pending', 'in_progress')`,
      [status, reviewer, reason, id],
    );
    if (!rowCount) {
      return NextResponse.json(
        { error: 'not found or already resolved' },
        { status: 404 },
      );
    }
    return NextResponse.json({ ok: true, id, status, reviewed_by: reviewer });
  } catch (e) {
    const message = e instanceof Error ? e.message : 'update failed';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
