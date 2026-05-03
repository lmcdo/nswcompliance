/**
 * POST /api/satellite/pre-da-history
 * Body: { address: string; lot_area_m2?: number }
 *
 * Async pattern (same as granny-flat):
 *   1. Pre-allocates a pre_da_history_reports row with status='pending'
 *   2. In production: fires Trigger.dev satellite-job-runner task → returns { report_id }
 *   3. In dev: calls Python directly (synchronous, with long timeout)
 *   4. Frontend polls GET ?report_id=X every 3s until status='complete'|'error'
 *
 * GET /api/satellite/pre-da-history?report_id=<uuid>
 *   Returns { status: 'pending' } | { status: 'complete', data: reportJson } | { status: 'error', error: string }
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient as createServiceClient } from '@supabase/supabase-js';

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';
const TRIGGER_API = 'https://api.trigger.dev/api/v1/tasks/satellite-job-runner/trigger';
const TRIGGER_SECRET = process.env.TRIGGER_SECRET_KEY!;

const getSupabase = () =>
  createServiceClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
  );

// ---------------------------------------------------------------------------
// POST — kick off the pipeline
// ---------------------------------------------------------------------------

export async function POST(req: NextRequest) {
  let body: { address?: string; lot_area_m2?: number };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const address = body?.address?.trim();
  if (!address) {
    return NextResponse.json({ error: 'address is required' }, { status: 400 });
  }

  // Pre-allocate the DB row
  const supabase = getSupabase();
  const { data: row, error: insertError } = await supabase
    .from('pre_da_history_reports')
    .insert({
      address,
      status: 'pending',
      run_date: new Date().toISOString().slice(0, 10),
    })
    .select('id')
    .single();

  if (insertError || !row) {
    console.error('[pre-da-history] Failed to pre-allocate row:', insertError);
    return NextResponse.json({ error: 'Failed to initialise report' }, { status: 500 });
  }

  const report_id = row.id as string;

  // Dev: call Python directly (no Trigger.dev)
  if (process.env.NODE_ENV === 'development') {
    // Fire and forget — return report_id immediately, Python will update the row
    fetch(`${PYTHON_API}/pipeline/pre-da-history`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        address,
        lot_area_m2: body?.lot_area_m2 ?? null,
        report_id,
      }),
    }).catch((err) => {
      console.error('[pre-da-history] Dev pipeline call failed:', err);
      // Mark row as error
      supabase
        .from('pre_da_history_reports')
        .update({ status: 'error', error_msg: String(err) })
        .eq('id', report_id)
        .then(() => {});
    });

    return NextResponse.json({ report_id }, { status: 202 });
  }

  // Production: fire Trigger.dev task
  const triggerResp = await fetch(TRIGGER_API, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${TRIGGER_SECRET}`,
    },
    body: JSON.stringify({
      payload: {
        product: 'pre-da-history',
        address,
        report_id,
        extra_body: { lot_area_m2: body?.lot_area_m2 ?? null },
      },
    }),
  });

  if (!triggerResp.ok) {
    const text = await triggerResp.text();
    console.error('[pre-da-history] Trigger.dev error:', text);
    // Return report_id anyway — user can retry polling
    return NextResponse.json(
      { report_id, warning: 'Pipeline enqueue failed — retry or check Trigger.dev' },
      { status: 202 },
    );
  }

  return NextResponse.json({ report_id }, { status: 202 });
}

// ---------------------------------------------------------------------------
// GET — poll for result
// ---------------------------------------------------------------------------

export async function GET(req: NextRequest) {
  const report_id = req.nextUrl.searchParams.get('report_id');
  if (!report_id) {
    return NextResponse.json({ error: 'report_id is required' }, { status: 400 });
  }

  const supabase = getSupabase();
  const { data, error } = await supabase
    .from('pre_da_history_reports')
    .select('status, report_json, error_msg')
    .eq('id', report_id)
    .single();

  if (error || !data) {
    return NextResponse.json({ status: 'pending' });
  }

  if (data.status === 'error') {
    return NextResponse.json({
      status: 'error',
      error: data.error_msg ?? 'Pipeline failed — please try again.',
    });
  }

  if (data.status === 'complete' && data.report_json) {
    return NextResponse.json({ status: 'complete', data: data.report_json });
  }

  return NextResponse.json({ status: 'pending' });
}
