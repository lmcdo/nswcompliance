/**
 * POST /api/stripe/checkout/solar-yield
 * Body: { report_id: string; email: string }
 *
 * Creates a Stripe Checkout session for the $19 Solar Yield report.
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

  if (!report_id) return NextResponse.json({ error: 'report_id is required' }, { status: 400 });
  if (!email)     return NextResponse.json({ error: 'email is required' }, { status: 400 });

  const priceId = process.env.STRIPE_SOLAR_YIELD_PRICE_ID;
  if (!priceId) {
    console.error('[stripe/checkout/solar-yield] STRIPE_SOLAR_YIELD_PRICE_ID not set');
    return NextResponse.json({ error: 'Payment not configured' }, { status: 500 });
  }

  const origin = req.headers.get('origin') ?? 'https://canibuildit.com.au';

  try {
    const session = await stripe.checkout.sessions.create({
      mode: 'payment',
      customer_email: email,
      line_items: [{ price: priceId, quantity: 1 }],
      metadata: { report_id, email, product: 'solar-yield-report' },
      success_url: `${origin}/reports/solar-yield?payment=success&report_id=${report_id}`,
      cancel_url:  `${origin}/reports/solar-yield?payment=cancelled`,
    });
    return NextResponse.json({ checkout_url: session.url });
  } catch (err) {
    console.error('[stripe/checkout/solar-yield] Stripe error:', err);
    return NextResponse.json({ error: 'Failed to create checkout session' }, { status: 500 });
  }
}
