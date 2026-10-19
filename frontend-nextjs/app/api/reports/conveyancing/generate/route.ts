/**
 * POST /api/reports/conveyancing/generate
 *
 * One call path: the Stripe webhook, with { checkout_session_id, report_id }.
 * The PDF is paid-only, so the session is confirmed with Stripe (paid, this product, this
 * report) and the address and coordinates are taken from the session, never from the request.
 * Before 2026-10-19 anyone who could POST got the paid PDF for any address: the route checked
 * nothing (the flood/shadow/bushfire routes check a DB row or a signed token).
 *
 * Calls Railway /pipeline/conveyancing/pdf, returns { pdf_url }.
 */

import { NextRequest, NextResponse } from 'next/server';
import { getStripe } from '@/lib/stripe-client';

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

export async function POST(req: NextRequest) {
  let body: {
    report_id?: string;
    checkout_session_id?: string;
  };

  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const report_id = body.report_id?.trim();
  const sessionId = body.checkout_session_id?.trim();
  if (!report_id || !sessionId) {
    return NextResponse.json({ error: 'report_id and checkout_session_id are required' }, { status: 400 });
  }

  const stripe = getStripe();
  if (!stripe) {
    return NextResponse.json({ error: 'Payment not configured' }, { status: 500 });
  }
  let meta: Record<string, string>;
  try {
    const session = await stripe.checkout.sessions.retrieve(sessionId);
    meta = (session.metadata ?? {}) as Record<string, string>;
    if (session.payment_status !== 'paid'
        || meta.product !== 'conveyancing-report'
        || meta.report_id !== report_id) {
      return NextResponse.json({ error: 'No paid order for this report' }, { status: 403 });
    }
  } catch (err) {
    // An unknown session id is a refusal; Stripe being unreachable is an outage, not a refusal.
    const code = (err as { code?: string; type?: string } | null);
    if (code?.code === 'resource_missing' || code?.type === 'StripeInvalidRequestError') {
      return NextResponse.json({ error: 'No paid order for this report' }, { status: 403 });
    }
    console.error('[conveyancing/generate] Stripe session lookup failed:', err);
    return NextResponse.json({ error: 'Could not confirm payment with Stripe' }, { status: 502 });
  }

  const address = meta.address;
  const lat = meta.lat ? parseFloat(meta.lat) : NaN;
  const lng = meta.lng ? parseFloat(meta.lng) : NaN;
  const prop_id = meta.prop_id || null;
  if (!address || !Number.isFinite(lat) || !Number.isFinite(lng)) {
    return NextResponse.json({ error: 'The paid order has no address or location' }, { status: 422 });
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
