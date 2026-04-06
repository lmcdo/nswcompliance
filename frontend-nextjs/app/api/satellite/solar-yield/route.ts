import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const getSupabase = () => createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
);

const TRIGGER_API = 'https://api.trigger.dev/api/v1/tasks/satellite-job-runner/trigger';
const TRIGGER_SECRET = process.env.TRIGGER_SECRET_KEY!;

/**
 * POST /api/satellite/solar-yield
 *
 * Body: { address: string, propId?: string }
 *
 * 1. Geocode address via /api/property/[address] to get lat/lng
 * 2. Pre-allocate a property_reports row UUID (jobId)
 * 3. Trigger satellite-job-runner Trigger.dev task
 * 4. Return { jobId } — frontend polls /api/reports/status?jobId=X
 */
export async function POST(request: NextRequest) {
  let body: { address?: string; propId?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const { address, propId } = body;
  if (!address?.trim()) {
    return NextResponse.json({ error: 'address is required' }, { status: 400 });
  }

  // Step 1: Geocode
  const propertyUrl = new URL(
    `/api/property/${encodeURIComponent(address)}`,
    process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3003'
  );
  const propResp = await fetch(propertyUrl.toString());
  if (!propResp.ok) {
    return NextResponse.json(
      { error: `Could not resolve address: ${address}` },
      { status: 422 }
    );
  }
  const propData = await propResp.json();
  const lat: number = propData.property?.coordinates?.lat ?? propData.lat ?? propData.latitude;
  const lng: number = propData.property?.coordinates?.lng ?? propData.lng ?? propData.longitude;

  if (!lat || !lng) {
    return NextResponse.json({ error: 'Could not geocode address' }, { status: 422 });
  }

  // Step 2: Pre-allocate report row so frontend can poll immediately
  const { data: reportRow, error: insertError } = await getSupabase()
    .from('property_reports')
    .insert({
      product: 'solar-yield',
      address,
      lat,
      lng,
      prop_id: propId ?? propData.propId ?? null,
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

  // Step 3: Trigger Trigger.dev task
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
        prop_id: propId ?? propData.propId ?? null,
        report_id: jobId,
        lot_geometry: propData.lotGeometry ?? null,
      },
    }),
  });

  if (!triggerResp.ok) {
    const text = await triggerResp.text();
    console.error('[solar-yield] Trigger.dev error:', text);
    // Don't fail the request — the row exists, user can retry
    return NextResponse.json(
      { jobId, warning: 'Pipeline enqueue failed — retry or check Trigger.dev dashboard' },
      { status: 202 }
    );
  }

  return NextResponse.json({ jobId }, { status: 202 });
}

/**
 * GET /api/satellite/solar-yield?jobId=<uuid>
 * Proxy to /api/reports/status for convenience.
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
