// DA Session API - create sessions, retrieve with responses
import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// POST /api/da-sessions — create or upsert a DA session
// GET  /api/da-sessions?token=UUID — retrieve session with responses
// PATCH /api/da-sessions?token=UUID — update dev_type
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { address, former_council, zone, dev_type } = body;

    if (!address) {
      return NextResponse.json({ error: 'address is required' }, { status: 400 });
    }

    const result = await query(
      `INSERT INTO da_sessions (address, former_council, zone, dev_type)
       VALUES ($1, $2, $3, $4)
       RETURNING id, session_token`,
      [address, former_council || null, zone || null, dev_type || null]
    );

    const row = result.rows[0];
    return NextResponse.json({ session_id: row.id, session_token: row.session_token });
  } catch (error) {
    console.error('[DA Sessions] POST error:', error);
    return NextResponse.json({ error: 'Failed to create session' }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  try {
    const token = request.nextUrl.searchParams.get('token');
    if (!token) {
      return NextResponse.json({ error: 'token is required' }, { status: 400 });
    }

    if (!UUID_REGEX.test(token)) {
      return NextResponse.json({ error: 'invalid token format' }, { status: 400 });
    }

    const sessionResult = await query(
      `SELECT id, address, former_council, zone, dev_type, proposed_values, created_at
       FROM da_sessions WHERE session_token = $1`,
      [token]
    );

    if (sessionResult.rows.length === 0) {
      return NextResponse.json({ error: 'Session not found' }, { status: 404 });
    }

    const session = sessionResult.rows[0];

    const responsesResult = await query(
      `SELECT provision_id, response_text, compliance_status, updated_at
       FROM da_responses WHERE da_session_id = $1`,
      [session.id]
    );

    // Build responses map: { [provision_id]: { response_text, compliance_status } }
    const responses: Record<number, { response_text: string | null; compliance_status: string | null }> = {};
    for (const row of responsesResult.rows) {
      responses[row.provision_id] = {
        response_text: row.response_text,
        compliance_status: row.compliance_status,
      };
    }

    return NextResponse.json({ session, responses });
  } catch (error) {
    console.error('[DA Sessions] GET error:', error);
    return NextResponse.json({ error: 'Failed to retrieve session' }, { status: 500 });
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const token = request.nextUrl.searchParams.get('token');
    if (!token) {
      return NextResponse.json({ error: 'token is required' }, { status: 400 });
    }

    if (!UUID_REGEX.test(token)) {
      return NextResponse.json({ error: 'invalid token format' }, { status: 400 });
    }

    const body = await request.json();
    const { dev_type } = body;

    await query(
      `UPDATE da_sessions SET dev_type = $1 WHERE session_token = $2`,
      [dev_type || null, token]
    );

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('[DA Sessions] PATCH error:', error);
    return NextResponse.json({ error: 'Failed to update session' }, { status: 500 });
  }
}
