import { NextRequest, NextResponse } from 'next/server';
import {
  satelliteRateLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';

export const dynamic = 'force-dynamic';
// Climate risk score: PostGIS overlays + NARCliM raster sampling — typically <10s
export const maxDuration = 30;

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';

/**
 * POST /api/satellite/climate-risk
 * Body: { address: string }
 *
 * Resolves address → lat/lng, then calls Python /pipeline/climate-risk.
 * Returns composite climate risk score with per-hazard breakdown and
 * NARCliM trajectory data.
 */
export async function POST(request: NextRequest) {
  const clientIP = getClientIdentifier(request);
  const rl = await checkRateLimit(clientIP, satelliteRateLimiter, 10, 60000);
  if (!rl.success) {
    return NextResponse.json(
      { error: 'Rate limit exceeded. Please try again later.' },
      { status: 429, headers: createRateLimitHeaders(rl) },
    );
  }

  let body: { address?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const address = body.address?.trim();
  if (!address || address.length < 5) {
    return NextResponse.json({ error: 'address is required' }, { status: 400 });
  }

  // Resolve address → coordinates
  const propUrl = `${new URL(request.url).origin}/api/property/${encodeURIComponent(address)}`;
  const internalHeaders: Record<string, string> = {};
  if (process.env.API_KEY) internalHeaders['x-api-key'] = process.env.API_KEY;
  const propResp = await fetch(propUrl, { headers: internalHeaders, signal: AbortSignal.timeout(25_000) }).catch((e) => {
    console.error('[climate-risk] property fetch error:', e);
    return null;
  });
  if (!propResp?.ok) {
    const status = propResp?.status ?? 'timeout/network';
    const errBody = propResp ? await propResp.text().catch(() => '') : '';
    console.error(`[climate-risk] property route returned ${status}:`, errBody);
    return NextResponse.json({ error: `Could not resolve address: ${address} (property API: ${status})` }, { status: 422 });
  }

  const propData = await propResp.json();
  if (!propData.success || !propData.property) {
    return NextResponse.json(
      { error: propData.error ?? 'Could not resolve address' },
      { status: 422 },
    );
  }

  let lat: number | null = propData.property.coordinates?.lat ?? null;
  let lng: number | null = propData.property.coordinates?.lng ?? null;

  if ((!lat || !lng) && propData.lotGeometry?.rings?.[0]?.length) {
    const ring: [number, number][] = propData.lotGeometry.rings[0];
    const cx = ring.reduce((s, p) => s + p[0], 0) / ring.length;
    const cy = ring.reduce((s, p) => s + p[1], 0) / ring.length;
    const R = 20037508.342789244;
    lng = (cx / R) * 180.0;
    lat = (Math.atan(Math.exp((cy * Math.PI) / R)) * 2 - Math.PI / 2) * (180.0 / Math.PI);
  }

  if (!lat || !lng) {
    return NextResponse.json(
      { error: 'Could not determine coordinates for this address' },
      { status: 422 },
    );
  }

  let pythonResp: Response;
  try {
    pythonResp = await fetch(`${PYTHON_API}/pipeline/climate-risk`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ address, lat, lng }),
      signal: AbortSignal.timeout(25_000),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: `Climate risk pipeline failed: ${msg}` }, { status: 502 });
  }

  if (!pythonResp.ok) {
    const text = await pythonResp.text().catch(() => '');
    return NextResponse.json(
      { error: `Climate risk pipeline error (${pythonResp.status}): ${text}` },
      { status: 502 },
    );
  }

  const result = await pythonResp.json();
  return NextResponse.json(result);
}
