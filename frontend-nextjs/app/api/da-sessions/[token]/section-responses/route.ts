import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const VALID_STATUSES = ['complies', 'varies', 'not_applicable', 'flagged'];

// PUT /api/da-sessions/[token]/section-responses — upsert a section response
export async function PUT(
  request: NextRequest,
  { params }: { params: { token: string } }
) {
  try {
    const { token } = params;

    if (!UUID_REGEX.test(token)) {
      return NextResponse.json({ error: 'invalid token format' }, { status: 400 });
    }

    const body = await request.json();
    const { section_key, section_title, status, narrative } = body;

    if (!section_key || typeof section_key !== 'string') {
      return NextResponse.json({ error: 'section_key is required' }, { status: 400 });
    }

    if (status && !VALID_STATUSES.includes(status)) {
      return NextResponse.json({ error: 'invalid status' }, { status: 400 });
    }

    const sessionResult = await query(
      `SELECT id FROM da_sessions WHERE session_token = $1`,
      [token]
    );

    if (sessionResult.rows.length === 0) {
      return NextResponse.json({ error: 'Session not found' }, { status: 404 });
    }

    const sessionId = sessionResult.rows[0].id;

    const result = await query(
      `INSERT INTO da_section_responses (da_session_id, section_key, section_title, status, narrative, updated_at)
       VALUES ($1, $2, $3, $4, $5, NOW())
       ON CONFLICT (da_session_id, section_key) DO UPDATE
         SET section_title = COALESCE(EXCLUDED.section_title, da_section_responses.section_title),
             status        = EXCLUDED.status,
             narrative     = EXCLUDED.narrative,
             updated_at    = NOW()
       RETURNING section_key, status, narrative, updated_at`,
      [sessionId, section_key, section_title || null, status || null, narrative || null]
    );

    return NextResponse.json({ response: result.rows[0] });
  } catch (error) {
    console.error('[DA Section Responses] PUT error:', error);
    return NextResponse.json({ error: 'Failed to save section response' }, { status: 500 });
  }
}
