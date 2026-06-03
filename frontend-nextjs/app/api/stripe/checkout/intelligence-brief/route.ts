/**
 * POST /api/stripe/checkout/intelligence-brief
 * Body: { address: string; prop_id?: string; email?: string }
 *
 * Creates a Stripe Checkout session for the Intelligence Brief.
 * Uses address (not report_id) as the identifier since the brief is
 * generated via Trigger.dev and has no report_id at checkout time.
 */
import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  let address: string | undefined;
  let prop_id: string | undefined;
  let email: string | undefined;

  try {
    const body = await req.json();
    address = body?.address?.trim();
    prop_id = body?.prop_id?.trim() || undefined;
    email   = body?.email?.trim() || undefined;
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  if (!address) return NextResponse.json({ error: 'address is required' }, { status: 400 });

  const priceId = process.env.STRIPE_INTELLIGENCE_BRIEF_PRICE_ID;
  if (!priceId) {
    console.error('[stripe/checkout/intelligence-brief] STRIPE_INTELLIGENCE_BRIEF_PRICE_ID not set');
    return NextResponse.json({ error: 'Payment not configured' }, { status: 500 });
  }

  const origin = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://plotdetect.com.au';

  try {
    const session = await stripe.checkout.sessions.create({
      mode: 'payment',
      allow_promotion_codes: true,
      ...(email ? { customer_email: email } : {}),
      line_items: [{ price: priceId, quantity: 1 }],
      metadata: {
        address,
        product: 'intelligence-brief',
        ...(prop_id ? { prop_id } : {}),
      },
      success_url: `${origin}/intelligence-brief?payment=success&address=${encodeURIComponent(address)}`,
      cancel_url:  `${origin}/intelligence-brief?payment=cancelled`,
    });
    return NextResponse.json({ checkout_url: session.url });
  } catch (err) {
    console.error('[stripe/checkout/intelligence-brief] Stripe error:', err);
    return NextResponse.json({ error: 'Failed to create checkout session' }, { status: 500 });
  }
}
