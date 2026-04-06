import { NextRequest, NextResponse } from 'next/server';

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3003';

/**
 * POST /api/satellite/shadow
 * Body: { address: string }
 *
 * Option B — direct FastAPI call (<30s, pure geometry). No Trigger.dev. No polling.
 *
 * 1. Resolve address → prop_id + lot centroid via /api/property/[address]
 * 2. Call Python POST /pipeline/shadow  (generates report_id internally if not provided)
 * 3. Return pipeline result immediately
 */
export async function POST(request: NextRequest) {
  let body: { address?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const address = body.address?.trim();
  if (!address) {
    return NextResponse.json({ error: 'address is required' }, { status: 400 });
  }

  // Step 1: resolve address via existing property API
  const propUrl = `${SITE_URL}/api/property/${encodeURIComponent(address)}`;
  let propResp: Response;
  try {
    propResp = await fetch(propUrl);
  } catch (err) {
    return NextResponse.json({ error: 'Property lookup network error' }, { status: 502 });
  }

  if (!propResp.ok) {
    return NextResponse.json(
      { error: `Could not resolve address: ${address}` },
      { status: 422 },
    );
  }

  const propData = await propResp.json();
  if (!propData.success || !propData.property) {
    return NextResponse.json(
      { error: propData.error ?? 'Could not resolve address' },
      { status: 422 },
    );
  }

  const prop_id: string = String(propData.property.prop_id);

  // Extract centroid from lot geometry rings (rings contain [lng, lat] pairs in EPSG:4326)
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

  // Step 2: pre-allocate a report_id (Python will upsert using it)
  const report_id = crypto.randomUUID();

  // Step 3: call Python directly (synchronous, <30s)
  let pythonResp: Response;
  try {
    pythonResp = await fetch(`${PYTHON_API}/pipeline/shadow`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ address, prop_id, lat, lng, report_id }),
      // 55s to stay under Vercel's 60s timeout
      signal: AbortSignal.timeout(55_000),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: `Shadow pipeline failed: ${msg}` },
      { status: 502 },
    );
  }

  if (!pythonResp.ok) {
    const text = await pythonResp.text().catch(() => '');
    return NextResponse.json(
      { error: `Shadow pipeline error (${pythonResp.status}): ${text}` },
      { status: 502 },
    );
  }

  const result = await pythonResp.json();
  return NextResponse.json(result);
}
