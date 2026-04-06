import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const getSupabase = () => createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
);

const TRIGGER_API = 'https://api.trigger.dev/api/v1/tasks/satellite-job-runner/trigger';
const TRIGGER_SECRET = process.env.TRIGGER_SECRET_KEY!;
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3003';

/**
 * POST /api/satellite/solar-yield
 * Body: { address: string }
 *
 * 1. Resolve address → lat/lng via /api/property/[address]
 * 2. Pre-allocate property_reports row (jobId)
 * 3. Trigger satellite-job-runner Trigger.dev task (no Vercel timeout)
 * 4. Return { jobId } — frontend polls /api/reports/status?jobId=X
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

  // Step 1: resolve address
  const propUrl = `${SITE_URL}/api/property/${encodeURIComponent(address)}`;
  let propResp: Response;
  try {
    propResp = await fetch(propUrl);
  } catch {
    return NextResponse.json({ error: 'Could not resolve address' }, { status: 422 });
  }

  if (!propResp.ok) {
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

  if ((!lat || !lng) && propData.lotGeometry?.rings?.[0]?.length) {
    const ring: [number, number][] = propData.lotGeometry.rings[0];
    const cx = ring.reduce((s: number, p: [number, number]) => s + p[0], 0) / ring.length;
    const cy = ring.reduce((s: number, p: [number, number]) => s + p[1], 0) / ring.length;
    const R = 20037508.342789244;
    lng = (cx / R) * 180.0;
    lat = (Math.atan(Math.exp((cy * Math.PI) / R)) * 2 - Math.PI / 2) * (180.0 / Math.PI);
  }

  if (!lat || !lng) {
    return NextResponse.json({ error: 'Could not determine coordinates for this address' }, { status: 422 });
  }

  // Step 2: pre-allocate report row
  const { data: reportRow, error: insertError } = await getSupabase()
    .from('property_reports')
    .insert({
      product: 'solar-yield',
      address,
      lat,
      lng,
      prop_id,
      run_date: new Date().toISOString().slice(0, 10),
      inputs: { lat, lng },
      outputs: null,
      confidence: 'pending',
      data_sources: [],
    })
    .select('id')
    .single();

  if (insertError || !reportRow) {
    console.error('[solar-yield] Failed to pre-allocate report row:', insertError);
    return NextResponse.json({ error: 'Failed to initialise report' }, { status: 500 });
  }

  const jobId = reportRow.id as string;

  // Step 3: enqueue Trigger.dev task
  const triggerResp = await fetch(TRIGGER_API, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${TRIGGER_SECRET}`,
    },
    body: JSON.stringify({
      payload: {
        product: 'solar-yield',
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
    console.error('[solar-yield] Trigger.dev error:', text);
    return NextResponse.json(
      { jobId, warning: 'Pipeline enqueue failed — retry or check Trigger.dev dashboard' },
      { status: 202 },
    );
  }

  return NextResponse.json({ jobId }, { status: 202 });
}

/**
 * GET /api/satellite/solar-yield?jobId=<uuid>
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
