/**
 * POST /api/intelligence-brief
 * Body: { address, lat?, lng?, prop_id?, include_satellite?, include_premium? }
 *
 * Triggers the intelligence-brief Trigger.dev task and returns
 * { runId, publicAccessToken } so the browser can connect directly
 * to the Trigger.dev Realtime stream (no server-side proxy needed).
 */

import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@trigger.dev/sdk/v3';
import {
  satelliteRateLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';

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
  // The Brief is open + anonymous (early-access, no signup/paywall — RULE 4),
  // but each run is an expensive ~40s background job, so cap abuse/cost per IP.
  // Generous for a human running a few briefs; kills scripted floods.
  const clientId = getClientIdentifier(request);
  const rl = await checkRateLimit(clientId, satelliteRateLimiter, 12, 3_600_000);
  if (!rl.success) {
    return NextResponse.json(
      { error: 'You have run several briefs in a short window. Please try again shortly.' },
      { status: 429, headers: createRateLimitHeaders(rl) },
    );
  }

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

  // Configure auth with the secret key (needed for createPublicToken)
  auth.configure({ secretKey: TRIGGER_SECRET });

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

  // Generate a scoped public token so the browser can connect directly
  // to the Trigger.dev Realtime stream without exposing the secret key.
  const publicAccessToken = await auth.createPublicToken({
    scopes: {
      read: { runs: [runId] },
    },
    expirationTime: '15m',
  });

  return NextResponse.json({ runId, publicAccessToken });
}
