import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import {
  satelliteRateLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';
const TRIGGER_API = 'https://api.trigger.dev/api/v1/tasks/satellite-job-runner/trigger';
const TRIGGER_SECRET = process.env.TRIGGER_SECRET_KEY!;

const getSupabase = () => createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
);

/**
 * POST /api/satellite/granny-flat
 * Body: { address: string, action: 'detect' | 'confirm', ...confirmPayload? }
 *
 * action=detect (async — LangSAM inference can exceed Vercel 60s limit):
 *   Geocodes address, pre-allocates a granny_flat_reports row, triggers
 *   satellite-job-runner Trigger.dev task → returns { jobId }.
 *   Frontend polls GET /api/satellite/granny-flat?jobId=X every 2s.
 *   When status='detected', the detect result is in the response.
 *
 * action=confirm (direct — <30s):
 *   User confirmed structure count. Calls /pipeline/granny-flat/confirm directly.
 */
export async function POST(request: NextRequest) {
  // Per-product rate limit — LangSAM inference is expensive
  const clientIP = getClientIdentifier(request);
  const rl = await checkRateLimit(clientIP, satelliteRateLimiter, 10, 60000);
  if (!rl.success) {
    return NextResponse.json(
      { error: 'Rate limit exceeded. Please try again later.' },
      { status: 429, headers: createRateLimitHeaders(rl) },
    );
  }

  let body: {
    address?: string;
    action?: 'detect' | 'confirm';
    detect_id?: string;
    confirmed_structure_count?: number;
    samgeo_structure_count?: number;
    postcode?: string;
    report_id?: string;
  };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const { address, action = 'detect' } = body;
  if (!address?.trim()) {
    return NextResponse.json({ error: 'address is required' }, { status: 400 });
  }

  // Resolve address for both actions
  const propUrl = `${new URL(request.url).origin}/api/property/${encodeURIComponent(address)}`;
  const internalHeaders: Record<string, string> = {};
  if (process.env.API_KEY) internalHeaders['x-api-key'] = process.env.API_KEY;
  const propResp = await fetch(propUrl, { headers: internalHeaders, signal: AbortSignal.timeout(10_000) }).catch(() => null);
  if (!propResp?.ok) {
    return NextResponse.json({ error: `Could not resolve address: ${address}` }, { status: 422 });
  }

  const propData = await propResp.json();
  if (!propData.success || !propData.property) {
    return NextResponse.json(
      { error: propData.error ?? 'Could not resolve address' },
      { status: 422 },
    );
  }

  const prop_id = String(propData.property.prop_id);
  const lotGeometry = propData.lotGeometry ?? null;

  let lat: number | null = propData.property.coordinates?.lat ?? null;
  let lng: number | null = propData.property.coordinates?.lng ?? null;

  if ((!lat || !lng) && lotGeometry?.rings?.[0]?.length) {
    // Rings are EPSG:3857 (Mercator metres) — convert centroid to WGS84
    const ring: [number, number][] = lotGeometry.rings[0];
    const xMerc = ring.reduce((s: number, p: [number, number]) => s + p[0], 0) / ring.length;
    const yMerc = ring.reduce((s: number, p: [number, number]) => s + p[1], 0) / ring.length;
    const R = 20037508.342789244;
    lng = xMerc * 180.0 / R;
    lat = (Math.atan(Math.exp(yMerc * Math.PI / R)) * 2 - Math.PI / 2) * (180 / Math.PI);
  }

  if (!lat || !lng) {
    return NextResponse.json(
      { error: 'Could not determine coordinates for this address' },
      { status: 422 },
    );
  }

  // Convert EPSG:3857 lot geometry ring to WGS84 GeoJSON polygon + centroid
  let lotPolygonWgs84: { type: 'Polygon'; coordinates: number[][][] } | null = null;
  let centroidLat = lat as number;
  let centroidLng = lng as number;
  if (lotGeometry?.rings?.[0]?.length) {
    const R = 20037508.342789244;
    const ring: [number, number][] = lotGeometry.rings[0];
    const wgs84Ring = ring.map(([x, y]: [number, number]): [number, number] => [
      x * 180.0 / R,
      (Math.atan(Math.exp(y * Math.PI / R)) * 2 - Math.PI / 2) * (180 / Math.PI),
    ]);
    lotPolygonWgs84 = { type: 'Polygon', coordinates: [wgs84Ring] };
    centroidLng = wgs84Ring.reduce((s, p) => s + p[0], 0) / wgs84Ring.length;
    centroidLat = wgs84Ring.reduce((s, p) => s + p[1], 0) / wgs84Ring.length;
  }

  // -------------------------------------------------------------------------
  // DETECT — async via Trigger.dev (production) / direct Python call (dev)
  // -------------------------------------------------------------------------
  if (action === 'detect') {
    // Pre-allocate report row so frontend can poll immediately
    const { data: reportRow, error: insertError } = await getSupabase()
      .from('granny_flat_reports')
      .insert({
        product: 'granny-flat',
        address,
        lat,
        lng,
        prop_id,
        run_date: new Date().toISOString().slice(0, 10),
        confidence: null,
        outputs: null,
      })
      .select('id')
      .single();

    if (insertError || !reportRow) {
      console.error('[granny-flat] Failed to pre-allocate report row:', insertError);
      return NextResponse.json({ error: 'Failed to initialise report' }, { status: 500 });
    }

    const jobId = reportRow.id as string;

    // In local dev, call Python directly (Trigger.dev can't reach localhost).
    if (process.env.NODE_ENV === 'development') {
      let detectResp: Response;
      try {
        detectResp = await fetch(`${PYTHON_API}/pipeline/granny-flat/detect`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ address, lat, lng, prop_id, report_id: jobId, lot_geometry: lotGeometry }),
          signal: AbortSignal.timeout(180_000),
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        return NextResponse.json({ error: `Detect failed: ${msg}` }, { status: 502 });
      }
      if (!detectResp.ok) {
        const text = await detectResp.text().catch(() => '');
        return NextResponse.json({ error: `Detect error (${detectResp.status}): ${text}` }, { status: 502 });
      }
      return NextResponse.json({ jobId, lotPolygonWgs84, centroidLat, centroidLng }, { status: 202 });
    }

    const triggerResp = await fetch(TRIGGER_API, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${TRIGGER_SECRET}`,
      },
      body: JSON.stringify({
        payload: {
          product: 'granny-flat',
          endpoint_suffix: '/detect',
          address,
          lat,
          lng,
          prop_id,
          report_id: jobId,
          extra_body: { lot_geometry: lotGeometry },
        },
      }),
    });

    if (!triggerResp.ok) {
      const text = await triggerResp.text();
      console.error('[granny-flat] Trigger.dev error:', text);
      return NextResponse.json(
        { jobId, warning: 'Pipeline enqueue failed — retry or check Trigger.dev dashboard' },
        { status: 202 },
      );
    }

    return NextResponse.json({ jobId, lotPolygonWgs84, centroidLat, centroidLng }, { status: 202 });
  }

  // -------------------------------------------------------------------------
  // CONFIRM — direct call (<30s)
  // -------------------------------------------------------------------------
  if (action === 'confirm') {
    const { detect_id, confirmed_structure_count, samgeo_structure_count, postcode, report_id } = body;

    if (!detect_id) {
      return NextResponse.json({ error: 'detect_id is required for confirm action' }, { status: 400 });
    }
    if (confirmed_structure_count == null) {
      return NextResponse.json(
        { error: 'confirmed_structure_count is required for confirm action' },
        { status: 400 },
      );
    }
    if (
      !Number.isInteger(confirmed_structure_count) ||
      confirmed_structure_count < 0 ||
      confirmed_structure_count > 20
    ) {
      return NextResponse.json(
        { error: 'confirmed_structure_count must be an integer between 0 and 20' },
        { status: 400 },
      );
    }

    // Shoelace on EPSG:3857 rings with Mercator cos²(lat) correction
    let lot_area_m2: number | null = null;
    if (lotGeometry?.rings?.[0]) {
      const ring: [number, number][] = lotGeometry.rings[0];
      let area = 0;
      for (let i = 0; i < ring.length; i++) {
        const [x1, y1] = ring[i];
        const [x2, y2] = ring[(i + 1) % ring.length];
        area += x1 * y2 - x2 * y1;
      }
      const scale = Math.cos((lat as number) * Math.PI / 180);
      lot_area_m2 = (Math.abs(area) / 2) * scale * scale;
    }

    const is_heritage = !!(propData.property?.heritage_status || propData.property?.heritage_overlays?.length);

    let pythonResp: Response;
    try {
      pythonResp = await fetch(`${PYTHON_API}/pipeline/granny-flat/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          detect_id,
          address,
          prop_id,
          lat,
          lng,
          lot_area_m2,
          confirmed_structure_count,
          samgeo_structure_count: samgeo_structure_count ?? null,
          postcode: postcode ?? null,
          report_id: report_id ?? crypto.randomUUID(),
          is_heritage,
        }),
        signal: AbortSignal.timeout(30_000),
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return NextResponse.json({ error: `Confirm failed: ${msg}` }, { status: 502 });
    }

    if (!pythonResp.ok) {
      const text = await pythonResp.text().catch(() => '');
      return NextResponse.json(
        { error: `Confirm error (${pythonResp.status}): ${text}` },
        { status: 502 },
      );
    }

    return NextResponse.json(await pythonResp.json());
  }

  return NextResponse.json({ error: `Unknown action: ${action}` }, { status: 400 });
}

/**
 * GET /api/satellite/granny-flat?jobId=<uuid>
 * Poll granny_flat_reports for detect result.
 * Returns { status: 'pending' } or { status: 'detected', data: detectResult }
 */
export async function GET(request: NextRequest) {
  const jobId = request.nextUrl.searchParams.get('jobId');
  if (!jobId) {
    return NextResponse.json({ error: 'jobId is required' }, { status: 400 });
  }

  const { data, error } = await getSupabase()
    .from('granny_flat_reports')
    .select('confidence, outputs')
    .eq('id', jobId)
    .single();

  if (error || !data) {
    return NextResponse.json({ status: 'pending' });
  }

  if (data.confidence !== 'pending_confirm' || !data.outputs) {
    return NextResponse.json({ status: 'pending' });
  }

  return NextResponse.json({ status: 'detected', data: data.outputs });
}
