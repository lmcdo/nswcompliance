/**
 * POST /api/reports/conveyancing/generate
 *
 * Two call paths:
 *   A) Stripe webhook: { report_id, address, lat, lng, prop_id } — generates paid PDF via Railway
 *   B) Direct:         Not supported — conveyancing PDF is paid-only
 *
 * Calls Railway /pipeline/conveyancing/pdf, returns { pdf_url }.
 */

import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

export async function POST(req: NextRequest) {
  let body: {
    report_id?: string;
    address?: string;
    lat?: number;
    lng?: number;
    prop_id?: string;
  };

  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const { report_id, address, lat, lng, prop_id } = body;

  if (!report_id || !address) {
    return NextResponse.json({ error: 'report_id and address are required' }, { status: 400 });
  }

  if (lat == null || lng == null) {
    return NextResponse.json({ error: 'lat and lng are required' }, { status: 400 });
  }

  const pythonUrl = process.env.PYTHON_API_URL;
  if (!pythonUrl) {
    console.error('[conveyancing/generate] PYTHON_API_URL not set');
    return NextResponse.json({ error: 'Backend not configured' }, { status: 500 });
  }

  try {
    const resp = await fetch(`${pythonUrl}/pipeline/conveyancing/pdf`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        address,
        lat,
        lng,
        prop_id: prop_id ?? null,
        report_id,
      }),
      signal: AbortSignal.timeout(55_000),
    });

    if (!resp.ok) {
      const errText = await resp.text().catch(() => 'Unknown error');
      console.error('[conveyancing/generate] Railway error:', resp.status, errText);
      return NextResponse.json({ error: 'PDF generation failed' }, { status: 502 });
    }

    const result = await resp.json();
    return NextResponse.json({
      pdf_url: result.pdf_url,
      report_id: result.report_id,
      address: result.address,
    });
  } catch (err) {
    console.error('[conveyancing/generate] Error:', err);
    return NextResponse.json({ error: 'PDF generation failed' }, { status: 500 });
  }
}
