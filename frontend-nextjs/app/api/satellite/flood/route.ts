import { NextRequest, NextResponse } from 'next/server';
import {
  satelliteRateLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';
import { signReport } from '@/lib/report-token';
import { esriRingsToGeoJSON } from '@/lib/geo-utils';

export const dynamic = 'force-dynamic';
// Flood pipeline (EPI WFS + EMS + JRC + BOM + SAR) can take up to ~50s
export const maxDuration = 60;

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';

/**
 * POST /api/satellite/flood
 * Body: { address: string }
 *
 * Resolves address → lat/lng/prop_id, then calls Python /pipeline/flood.
 * Synchronous — returns EPI flood overlay immediately (<10s).
 * SAR analysis is only available for pre-computed results.
 */
export async function POST(request: NextRequest) {
  // Per-product rate limit — Railway compute
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

  // One budget for the whole request. maxDuration is 60 s, but the address
  // lookup (25 s) plus the pipeline (55 s) could take 80, so Vercel cut the
  // function off and the browser got an HTML error page instead of JSON.
  const deadline = Date.now() + 57_000;
  const address = body.address?.trim();
  if (!address || address.length < 5) {
    return NextResponse.json({ error: 'address is required' }, { status: 400 });
  }

  // Resolve address — derive origin from request.url so preview deployments work
  const propUrl = `${new URL(request.url).origin}/api/property/${encodeURIComponent(address)}`;
  const internalHeaders: Record<string, string> = {};
  if (process.env.API_KEY) internalHeaders['x-api-key'] = process.env.API_KEY;
  const propResp = await fetch(propUrl, { headers: internalHeaders, signal: AbortSignal.timeout(25_000) }).catch((e) => {
    console.error('[flood] property fetch error:', e);
    return null;
  });
  if (!propResp?.ok) {
    const status = propResp?.status ?? 'timeout/network';
    const body = propResp ? await propResp.text().catch(() => '') : '';
    console.error(`[flood] property route returned ${status}:`, body);
    return NextResponse.json({ error: `Could not resolve address: ${address} (property API: ${status})` }, { status: 422 });
  }

  const propData = await propResp.json();
  if (!propData.success || !propData.property) {
    return NextResponse.json(
      { error: propData.error ?? 'Could not resolve address' },
      { status: 422 },
    );
  }

  const prop_id = String(propData.property.prop_id);
  let lat: number | null = propData.property.coordinates?.lat ?? null;
  let lng: number | null = propData.property.coordinates?.lng ?? null;

  if ((!lat || !lng) && propData.lotGeometry?.rings?.[0]?.length) {
    // Rings are EPSG:3857 (Web Mercator metres) — convert centroid to WGS84
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

  const lot_polygon = propData.lotGeometry?.rings?.length
    ? esriRingsToGeoJSON(propData.lotGeometry.rings)
    : null;

  const report_id = crypto.randomUUID();

  let pythonResp: Response;
  try {
    pythonResp = await fetch(`${PYTHON_API}/pipeline/flood`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ address, prop_id, lat, lng, report_id }),
      signal: AbortSignal.timeout(Math.max(5_000, deadline - Date.now())),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error('[flood] pipeline call failed:', msg);
    return NextResponse.json({ error: 'The flood check did not finish in time. Please try again in a minute.' }, { status: 504 });
  }

  if (!pythonResp.ok) {
    const text = await pythonResp.text().catch(() => '');
    console.error(`[flood] pipeline returned ${pythonResp.status}:`, text.slice(0, 500));
    return NextResponse.json(
      { error: 'The flood check hit an error. Please try again in a minute.' },
      { status: 502 },
    );
  }

  const result = await pythonResp.json();
  const report_token = signReport(lat, lng, address, result.run_date ?? '');
  // Include report_id so the frontend can pass it to the Stripe checkout route
  return NextResponse.json({ ...result, report_id, report_token, lot_polygon });
}
