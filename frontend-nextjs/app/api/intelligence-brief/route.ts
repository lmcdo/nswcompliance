/**
 * POST /api/intelligence-brief
 * Body: { address, lat?, lng?, prop_id?, include_satellite?, include_premium? }
 *
 * Triggers the intelligence-brief Trigger.dev task and returns
 * { runId, publicAccessToken } so the frontend can subscribe to
 * the Realtime Stream for progressive rendering.
 *
 * The public access token is a JWT signed with the Trigger.dev secret key,
 * scoped to read the specific run — same pattern the Trigger.dev SDK uses
 * internally (see @trigger.dev/core/v3/apiClient triggerTask).
 */

import { NextRequest, NextResponse } from 'next/server';
import { SignJWT } from 'jose';

export const dynamic = 'force-dynamic';
export const maxDuration = 15; // Only triggers the task — doesn't wait for completion

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

/**
 * Generate a public access token (JWT) for the frontend to subscribe
 * to a specific Trigger.dev run's realtime stream.
 *
 * Mirrors the pattern in @trigger.dev/core apiClient.triggerTask():
 *   - HS256 signed with the secret key
 *   - Scoped to read:runs:{runId}
 *   - 1 hour expiry (brief generation takes ~37s, generous margin)
 */
async function createPublicAccessToken(runId: string): Promise<string> {
  const secret = new TextEncoder().encode(TRIGGER_SECRET);
  return new SignJWT({ scopes: [`read:runs:${runId}`] })
    .setIssuer('https://id.trigger.dev')
    .setAudience('https://api.trigger.dev')
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('1h')
    .sign(secret);
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

  // Trigger the intelligence-brief task
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

  // Generate a public access token scoped to this run
  const publicAccessToken = await createPublicAccessToken(runId);

  return NextResponse.json({
    runId,
    publicAccessToken,
  });
}
