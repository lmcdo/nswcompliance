/**
 * POST /api/stripe/checkout/pre-da-history
 * Body: { report_id: string; email: string }
 *
 * Creates a Stripe Checkout session for the $49 Pre-DA Site History Report.
 * report_id and email are stored in session metadata so the webhook
 * can generate and deliver the PDF after payment.
 */

import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2026-04-22.dahlia',
});

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  let report_id: string | undefined;
  let email: string | undefined;

  try {
    const body = await req.json();
    report_id = body?.report_id?.trim();
    email = body?.email?.trim();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  if (!report_id) {
    return NextResponse.json({ error: 'report_id is required' }, { status: 400 });
  }
  if (!email) {
    return NextResponse.json({ error: 'email is required' }, { status: 400 });
  }

  const priceId = process.env.STRIPE_PRE_DA_HISTORY_PRICE_ID;
  if (!priceId) {
    console.error('[stripe/checkout/pre-da-history] STRIPE_PRE_DA_HISTORY_PRICE_ID not set');
    return NextResponse.json({ error: 'Payment not configured' }, { status: 500 });
  }

  const origin = req.headers.get('origin') ?? 'https://canibuildit.com.au';

  try {
    const session = await stripe.checkout.sessions.create(
      {
        mode: 'payment',
        customer_email: email,
        line_items: [{ price: priceId, quantity: 1 }],
        metadata: {
          report_id,
          email,
          product: 'pre-da-history-report',
        },
        success_url: `${origin}/reports/pre-da-history?payment=success&report_id=${report_id}`,
        cancel_url: `${origin}/reports/pre-da-history?payment=cancelled`,
      },
      { idempotencyKey: `pre-da-${report_id}` },
    );

    return NextResponse.json({ checkout_url: session.url });
  } catch (err) {
    console.error('[stripe/checkout/pre-da-history] Stripe error:', err);
    return NextResponse.json({ error: 'Failed to create checkout session' }, { status: 500 });
  }
}
