/**
 * POST /api/intelligence-brief
 * Body: { address, lat?, lng?, prop_id?, include_satellite?, include_premium? }
 *
 * Triggers the intelligence-brief Trigger.dev task and returns { runId }.
 * The frontend then connects to GET /api/intelligence-brief/stream?runId=xxx
 * for progressive SSE updates (server-side proxy to Trigger.dev Realtime).
 */

import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const maxDuration = 15;

const TRIGGER_API = 'https://api.trigger.dev/api/v1/tasks/intelligence-brief/trigger';
const TRIGGER_SECRET = process.env.TRIGGER_SECRET_KEY!;

interface IntelligenceBriefBody {
  address?: string;
  lat?: number;
  lng?: number;
  prop_id?: string;
  include_satellite?: boolean;
  include_premium?: boolean;
}

export async function POST(request: NextRequest) {
  let body: IntelligenceBriefBody;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const { address, lat, lng, prop_id, include_satellite = false, include_premium = false } = body;

  if (!address?.trim()) {
    return NextResponse.json({ error: 'address is required' }, { status: 400 });
  }

  const triggerResp = await fetch(TRIGGER_API, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${TRIGGER_SECRET}`,
    },
    body: JSON.stringify({
      payload: {
        address: address.trim(),
        lat,
        lng,
        prop_id,
        include_satellite,
        include_premium,
      },
    }),
  });

  if (!triggerResp.ok) {
    const text = await triggerResp.text();
    console.error('[intelligence-brief] Trigger.dev error:', text);
    return NextResponse.json(
      { error: 'Failed to start intelligence brief' },
      { status: 502 },
    );
  }

  const triggerData = await triggerResp.json();
  const runId: string = triggerData.id;

  return NextResponse.json({ runId });
}
