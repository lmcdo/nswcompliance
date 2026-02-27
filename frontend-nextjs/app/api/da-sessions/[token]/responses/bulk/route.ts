// Bulk DA responses — upsert multiple provision responses in a single request.
// Used by the structured intake to pre-populate N/A responses for excluded provisions.
import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

interface BulkResponseItem {
  provision_id: number;
  compliance_status: string;
  response_text?: string;
}

// PUT /api/da-sessions/[token]/responses/bulk
// Body: { responses: BulkResponseItem[] }
// Returns: { count: number }
export async function PUT(
  request: NextRequest,
  { params }: { params: { token: string } }
) {
  try {
    const { token } = params;

    if (!UUID_REGEX.test(token)) {
      return NextResponse.json({ error: 'invalid token format' }, { status: 400 });
    }

    // Resolve session id
    const sessionResult = await query(
      `SELECT id FROM da_sessions WHERE session_token = $1`,
      [token]
    );

    if (sessionResult.rows.length === 0) {
      return NextResponse.json({ error: 'Session not found' }, { status: 404 });
    }

    const sessionId = sessionResult.rows[0].id;

    const body = await request.json();
    const { responses } = body as { responses: BulkResponseItem[] };

    if (!Array.isArray(responses) || responses.length === 0) {
      return NextResponse.json({ count: 0 });
    }

    // Validate items
    for (const item of responses) {
      if (typeof item.provision_id !== 'number') {
        return NextResponse.json({ error: 'Each response must have a numeric provision_id' }, { status: 400 });
      }
    }

    // Bulk upsert using unnest — one round-trip regardless of count
    const provisionIds = responses.map(r => r.provision_id);
    const statuses = responses.map(r => r.compliance_status ?? null);
    const texts = responses.map(r => r.response_text ?? null);

    await query(
      `INSERT INTO da_responses (da_session_id, provision_id, compliance_status, response_text, updated_at)
       SELECT $1, provision_id, compliance_status, response_text, NOW()
       FROM unnest(
         $2::int[],
         $3::text[],
         $4::text[]
       ) AS t(provision_id, compliance_status, response_text)
       ON CONFLICT (da_session_id, provision_id)
       DO UPDATE SET
         compliance_status = EXCLUDED.compliance_status,
         response_text = EXCLUDED.response_text,
         updated_at = NOW()`,
      [sessionId, provisionIds, statuses, texts]
    );

    return NextResponse.json({ count: responses.length });
  } catch (error) {
    console.error('[DA Sessions] bulk PUT error:', error);
    return NextResponse.json({ error: 'Failed to save bulk responses' }, { status: 500 });
  }
}
