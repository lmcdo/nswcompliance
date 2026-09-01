/**
 * POST /api/stripe/checkout/solar-yield
 * Body: { report_id: string; address: string; email?: string }
 *
 * Creates a Stripe Checkout session for the $19 Solar Yield report.
 * email is optional — Stripe's hosted checkout collects it if absent.
 */
import { NextRequest, NextResponse } from 'next/server';
import { getStripe } from '@/lib/stripe-client';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  let report_id: string | undefined;
  let address: string | undefined;
  let email: string | undefined;
  let firm_name: string | undefined;

  try {
    const body = await req.json();
    report_id = body?.report_id?.trim();
    address   = body?.address?.trim();
    email     = body?.email?.trim() || undefined;
    firm_name = body?.firm_name?.trim() || undefined;
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  if (!report_id) return NextResponse.json({ error: 'report_id is required' }, { status: 400 });
  if (!address)   return NextResponse.json({ error: 'address is required' }, { status: 400 });

  const priceId = process.env.STRIPE_SOLAR_YIELD_PRICE_ID;
  if (!priceId) {
    console.error('[stripe/checkout/solar-yield] STRIPE_SOLAR_YIELD_PRICE_ID not set');
    return NextResponse.json({ error: 'Payment not configured' }, { status: 500 });
  }

  const stripe = getStripe();
  if (!stripe) {
    return NextResponse.json({ error: 'Payment not configured' }, { status: 500 });
  }

  const origin = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://plotdetect.com.au';

  try {
    const session = await stripe.checkout.sessions.create({
      mode: 'payment',
      allow_promotion_codes: true,
      ...(email ? { customer_email: email } : {}),
      line_items: [{ price: priceId, quantity: 1 }],
      metadata: { report_id, address, product: 'solar-yield-report', ...(firm_name ? { firm_name } : {}) },
      success_url: `${origin}/reports/solar-yield?payment=success&report_id=${report_id}&address=${encodeURIComponent(address)}`,
      cancel_url:  `${origin}/reports/solar-yield?payment=cancelled`,
    });
    return NextResponse.json({ checkout_url: session.url });
  } catch (err) {
    console.error('[stripe/checkout/solar-yield] Stripe error:', err);
    return NextResponse.json({ error: 'Failed to create checkout session' }, { status: 500 });
  }
}
