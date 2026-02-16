import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

// PUT /api/da-sessions/[token]/responses — upsert a provision response
export async function PUT(
  request: NextRequest,
  { params }: { params: { token: string } }
) {
  try {
    const { token } = params;

    // Validate UUID format
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    if (!uuidRegex.test(token)) {
      return NextResponse.json({ error: 'invalid token format' }, { status: 400 });
    }

    const body = await request.json();
    const { provision_id, response_text, compliance_status } = body;

    if (!provision_id) {
      return NextResponse.json({ error: 'provision_id is required' }, { status: 400 });
    }

    if (compliance_status && !['complies', 'varies', 'not_applicable'].includes(compliance_status)) {
      return NextResponse.json({ error: 'invalid compliance_status' }, { status: 400 });
    }

    // Resolve session_id from token
    const sessionResult = await query(
      `SELECT id FROM da_sessions WHERE session_token = $1`,
      [token]
    );

    if (sessionResult.rows.length === 0) {
      return NextResponse.json({ error: 'Session not found' }, { status: 404 });
    }

    const sessionId = sessionResult.rows[0].id;

    const result = await query(
      `INSERT INTO da_responses (da_session_id, provision_id, response_text, compliance_status, updated_at)
       VALUES ($1, $2, $3, $4, NOW())
       ON CONFLICT (da_session_id, provision_id) DO UPDATE
         SET response_text = EXCLUDED.response_text,
             compliance_status = EXCLUDED.compliance_status,
             updated_at = NOW()
       RETURNING provision_id, response_text, compliance_status, updated_at`,
      [sessionId, provision_id, response_text || null, compliance_status || null]
    );

    return NextResponse.json({ response: result.rows[0] });
  } catch (error) {
    console.error('[DA Responses] PUT error:', error);
    return NextResponse.json({ error: 'Failed to save response' }, { status: 500 });
  }
}
