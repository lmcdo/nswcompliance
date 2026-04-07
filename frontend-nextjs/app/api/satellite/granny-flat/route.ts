import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3003';
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
  const propUrl = `${SITE_URL}/api/property/${encodeURIComponent(address)}`;
  const propResp = await fetch(propUrl).catch(() => null);
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
    const ring: [number, number][] = lotGeometry.rings[0];
    lng = ring.reduce((s, p) => s + p[0], 0) / ring.length;
    lat = ring.reduce((s, p) => s + p[1], 0) / ring.length;
  }

  if (!lat || !lng) {
    return NextResponse.json(
      { error: 'Could not determine coordinates for this address' },
      { status: 422 },
    );
  }

  // -------------------------------------------------------------------------
  // DETECT — async via Trigger.dev
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

    return NextResponse.json({ jobId }, { status: 202 });
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

    // Extract lot_area_m2 from lot geometry rings using shoelace (metres, EPSG:3857)
    let lot_area_m2: number | null = null;
    if (lotGeometry?.rings?.[0]) {
      const ring: [number, number][] = lotGeometry.rings[0];
      let area = 0;
      for (let i = 0; i < ring.length; i++) {
        const [x1, y1] = ring[i];
        const [x2, y2] = ring[(i + 1) % ring.length];
        area += x1 * y2 - x2 * y1;
      }
      lot_area_m2 = Math.abs(area) / 2;
    }

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
