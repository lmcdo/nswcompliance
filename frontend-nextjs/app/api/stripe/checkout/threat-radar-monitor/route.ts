/**
 * POST /api/stripe/checkout/threat-radar-monitor
 * Body: { email: string; address: string }
 *
 * Creates a Stripe Checkout session for the $9.99/month Threat Radar
 * monitoring subscription. address and email stored in metadata so
 * the webhook can activate monitoring after payment.
 */

import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2026-05-27.dahlia',
});

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  let email: string | undefined;
  let address: string | undefined;

  try {
    const body = await req.json();
    email = body?.email?.trim();
    address = body?.address?.trim();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  if (!email) return NextResponse.json({ error: 'email is required' }, { status: 400 });
  if (!address) return NextResponse.json({ error: 'address is required' }, { status: 400 });

  const priceId = process.env.STRIPE_THREAT_RADAR_MONITOR_PRICE_ID;
  if (!priceId) {
    console.error('[stripe/checkout/threat-radar-monitor] STRIPE_THREAT_RADAR_MONITOR_PRICE_ID not set');
    return NextResponse.json({ error: 'Payment not configured' }, { status: 500 });
  }

  const origin = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://plotdetect.com.au';

  try {
    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      allow_promotion_codes: true,
      customer_email: email,
      line_items: [{ price: priceId, quantity: 1 }],
      metadata: {
        address,
        email,
        product: 'threat-radar-monitor',
      },
      success_url: `${origin}/reports/threat-radar?subscribed=1&address=${encodeURIComponent(address)}`,
      cancel_url: `${origin}/reports/threat-radar?address=${encodeURIComponent(address)}`,
    });

    return NextResponse.json({ checkout_url: session.url });
  } catch (err) {
    console.error('[stripe/checkout/threat-radar-monitor] Stripe error:', err);
    return NextResponse.json({ error: 'Failed to create checkout session' }, { status: 500 });
  }
}
