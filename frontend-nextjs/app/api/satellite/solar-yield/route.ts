import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { randomUUID } from 'crypto';
import {
  satelliteRateLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';
import { signReport } from '@/lib/report-token';

const getSupabase = () => createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
);

const PYTHON_API = process.env.PYTHON_API_URL!;

/** Convert Esri Web Mercator rings → GeoJSON Polygon (WGS84) */
function esriRingsToGeoJSON(rings: number[][][]): { type: 'Polygon'; coordinates: number[][][] } {
  const R = 20037508.342789244;
  const coords = rings.map(ring =>
    ring.map(([x, y]) => [
      (x / R) * 180.0,
      (Math.atan(Math.exp((y * Math.PI) / R)) * 2 - Math.PI / 2) * (180.0 / Math.PI),
    ])
  );
  return { type: 'Polygon', coordinates: coords };
}

export const dynamic = 'force-dynamic';
// Railway /pipeline/solar-yield can take up to ~50s (Google Solar API + clipping)
export const maxDuration = 60;

/**
 * POST /api/satellite/solar-yield
 * Body: { address: string }
 *
 * Calls Railway directly (no Trigger.dev) — returns complete report immediately.
 * 1. Resolve address → lat/lng
 * 2. Eligibility gates (unit/strata)
 * 3. Call Railway /pipeline/solar-yield (Google Solar API + lot clipping + heritage check)
 * 4. Return full report data including report_id for Stripe checkout
 */
export async function POST(request: NextRequest) {
  // Per-product rate limit — calls Google Solar API (paid) and Railway compute
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

  // Step 1: resolve address
  let propData: Record<string, unknown>;
  try {
    const internalHeaders: Record<string, string> = {};
    if (process.env.API_KEY) internalHeaders['x-api-key'] = process.env.API_KEY;
    const propResp = await fetch(`${new URL(request.url).origin}/api/property/${encodeURIComponent(address)}`, {
      headers: internalHeaders,
      signal: AbortSignal.timeout(10_000),
    });
    if (!propResp.ok) {
      return NextResponse.json({ error: `Could not resolve address: ${address}` }, { status: 422 });
    }
    propData = await propResp.json();
  } catch {
    return NextResponse.json({ error: 'Could not resolve address' }, { status: 422 });
  }

  if (!propData.success || !propData.property) {
    return NextResponse.json(
      { error: (propData.error as string) ?? 'Could not resolve address' },
      { status: 422 },
    );
  }

  const prop = propData.property as Record<string, unknown>;
  const prop_id = String(prop.prop_id);
  const lotGeometry = (propData.lotGeometry as Record<string, unknown>) ?? null;

  // -------------------------------------------------------------------------
  // Eligibility gates — run before calling Railway / Google Solar API (paid)
  // -------------------------------------------------------------------------

  // Gate 1: Unit / apartment address
  // Individual unit owners do not control the building roof — the owners
  // corporation does. A solar assessment for a unit number is misleading.
  const canonicalAddress: string = (prop.address as string) ?? '';
  if (/^(UNIT|APT|APARTMENT|FLAT|SUITE|LEVEL|SHOP|OFFICE|U)\s+\d/i.test(canonicalAddress)) {
    return NextResponse.json(
      {
        ineligible: true,
        error:
          'This address is a unit or apartment. Individual unit owners do not control the building roof — solar installation decisions belong to the owners corporation (strata body). A building-wide assessment would need to be commissioned by the strata manager.',
        evidence: canonicalAddress,
        evidence_label: 'NSW Planning Portal — canonical address',
      },
      { status: 422 },
    );
  }

  // Gate 2: Strata Plan lot
  // Lot descriptions like "Lot 1 SP 87654" indicate a strata scheme — same
  // roof ownership issue as Gate 1.
  const lot_description: string | null = (propData as { lot_description?: string | null }).lot_description ?? null;
  if (lot_description) {
    const spMatch = lot_description.match(/\bSP\s*(\d+)\b/i);
    if (spMatch) {
      return NextResponse.json(
        {
          ineligible: true,
          error:
            `This lot is registered on Strata Plan ${spMatch[1]}. Solar installation on a strata building requires owners corporation approval — individual lot owners cannot install panels on the common roof without a special resolution or by-law. Contact your strata manager to explore a building-wide system.`,
          evidence: lot_description,
          evidence_label: 'NSW Planning Portal — lot registration',
        },
        { status: 422 },
      );
    }
  }

  let lat: number | null = (prop.coordinates as Record<string, number>)?.lat ?? null;
  let lng: number | null = (prop.coordinates as Record<string, number>)?.lng ?? null;

  if ((!lat || !lng) && (lotGeometry as Record<string, unknown>)?.rings) {
    const ring = ((lotGeometry as Record<string, unknown>).rings as number[][][])[0];
    const cx = ring.reduce((s, p) => s + p[0], 0) / ring.length;
    const cy = ring.reduce((s, p) => s + p[1], 0) / ring.length;
    const R = 20037508.342789244;
    lng = (cx / R) * 180.0;
    lat = (Math.atan(Math.exp((cy * Math.PI) / R)) * 2 - Math.PI / 2) * (180.0 / Math.PI);
  }

  if (!lat || !lng) {
    return NextResponse.json({ error: 'Could not determine coordinates' }, { status: 422 });
  }

  const jobId = randomUUID();

  // Convert Esri rings → WGS84 GeoJSON once.
  // Sent to Railway for shapely lot-clipping AND used for the frontend map overlay.
  const lotPolygon = lotGeometry?.rings
    ? esriRingsToGeoJSON(lotGeometry.rings as number[][][])
    : null;

  // Step 2: call Railway directly
  let pipelineResult: Record<string, unknown>;
  try {
    const railwayResp = await fetch(`${PYTHON_API}/pipeline/solar-yield`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        address, lat, lng, prop_id,
        report_id: jobId,
        lot_polygon_wgs84: lotPolygon,
      }),
      signal: AbortSignal.timeout(55_000),
    });

    if (!railwayResp.ok) {
      const text = await railwayResp.text();
      throw new Error(`Railway error (${railwayResp.status}): ${text}`);
    }

    pipelineResult = await railwayResp.json();
  } catch (err) {
    console.error('[solar-yield] Railway call failed:', err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : 'Pipeline failed' },
      { status: 502 },
    );
  }

  // Step 3: store in Supabase (Railway already wrote it, this is the read-back for the frontend)
  const run_date = new Date().toISOString().slice(0, 10);
  const report_token = signReport(lat, lng, address, run_date);
  return NextResponse.json({
    jobId,
    status: 'complete',
    data: {
      product: 'solar-yield',
      address,
      lat,
      lng,
      lot_polygon: lotPolygon,
      run_date,
      outputs: pipelineResult.outputs,
      confidence: pipelineResult.confidence,
      data_sources: pipelineResult.data_sources,
      report_token,
      report_id: jobId,
    },
  }, { status: 200 });
}

/**
 * GET /api/satellite/solar-yield?jobId=<uuid>
 * Kept for compatibility but POST now returns data directly.
 */
export async function GET(request: NextRequest) {
  const jobId = request.nextUrl.searchParams.get('jobId');
  if (!jobId) {
    return NextResponse.json({ error: 'jobId is required' }, { status: 400 });
  }

  const { data, error } = await getSupabase()
    .from('property_reports')
    .select('*')
    .eq('id', jobId)
    .single();

  if (error || !data) {
    return NextResponse.json({ status: 'pending' });
  }

  if (data.confidence === 'pending') {
    return NextResponse.json({ status: 'pending' });
  }

  return NextResponse.json({ status: 'complete', data });
}
