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
// Bushfire pipeline (RFS BFPL + PostGIS overlays) typically <15s
export const maxDuration = 60;

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';

/**
 * POST /api/satellite/bushfire
 * Body: { address: string }
 *
 * Resolves address → lat/lng/prop_id, then calls Python /pipeline/bushfire.
 * Synchronous — returns RFS BFPL + cross-overlays immediately.
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

  const address = body.address?.trim();
  if (!address || address.length < 5) {
    return NextResponse.json({ error: 'address is required' }, { status: 400 });
  }

  // Resolve address — derive origin from request.url so preview deployments work
  const propUrl = `${new URL(request.url).origin}/api/property/${encodeURIComponent(address)}`;
  const internalHeaders: Record<string, string> = {};
  if (process.env.API_KEY) internalHeaders['x-api-key'] = process.env.API_KEY;
  const propResp = await fetch(propUrl, { headers: internalHeaders, signal: AbortSignal.timeout(25_000) }).catch((e) => {
    console.error('[bushfire] property fetch error:', e);
    return null;
  });
  if (!propResp?.ok) {
    const status = propResp?.status ?? 'timeout/network';
    const body = propResp ? await propResp.text().catch(() => '') : '';
    console.error(`[bushfire] property route returned ${status}:`, body);
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
  // Preserve lot geometry for PDF map rendering (EPSG:3857 rings)
  const lot_geometry = propData.lotGeometry?.rings?.[0]?.length
    ? { rings: propData.lotGeometry.rings }
    : null;

  let pythonResp: Response;
  try {
    pythonResp = await fetch(`${PYTHON_API}/pipeline/bushfire`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ address, prop_id, lat, lng, report_id, lot_geometry }),
      signal: AbortSignal.timeout(55_000),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: `Bushfire pipeline failed: ${msg}` }, { status: 502 });
  }

  if (!pythonResp.ok) {
    const text = await pythonResp.text().catch(() => '');
    return NextResponse.json(
      { error: `Bushfire pipeline error (${pythonResp.status}): ${text}` },
      { status: 502 },
    );
  }

  const result = await pythonResp.json();
  const report_token = signReport(lat, lng, address, result.run_date ?? '');
  // Include report_id so the frontend can pass it to the Stripe checkout route
  return NextResponse.json({ ...result, report_id, report_token, lot_polygon });
}
