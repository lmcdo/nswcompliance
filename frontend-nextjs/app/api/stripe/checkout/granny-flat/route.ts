/**
 * POST /api/stripe/checkout/granny-flat
 * Body: { job_id: string; address: string; email?: string }
 *
 * Creates a Stripe Checkout session for the $49 granny flat analysis.
 * Detect job is already running — job_id, address, email stored in metadata
 * so the webhook can send a resume-link email after payment.
 *
 * success_url redirects to /reports/granny-flat with ?jobId + ?payment=success
 * so the page auto-polls and shows the confirmation flow.
 */

import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2026-04-22.dahlia',
});

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  let job_id: string | undefined;
  let address: string | undefined;
  let email: string | undefined;

  try {
    const body = await req.json();
    job_id = body?.job_id?.trim();
    address = body?.address?.trim();
    email = body?.email?.trim() || undefined;
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  if (!job_id) {
    return NextResponse.json({ error: 'job_id is required' }, { status: 400 });
  }
  if (!address) {
    return NextResponse.json({ error: 'address is required' }, { status: 400 });
  }

  const priceId = process.env.STRIPE_GRANNY_FLAT_PRICE_ID;
  if (!priceId) {
    console.error('[stripe/checkout/granny-flat] STRIPE_GRANNY_FLAT_PRICE_ID not set');
    return NextResponse.json({ error: 'Payment not configured' }, { status: 500 });
  }

  const origin = process.env.NEXT_PUBLIC_APP_URL ?? 'https://canibuildit.com.au';

  try {
    const session = await stripe.checkout.sessions.create({
      mode: 'payment',
      ...(email ? { customer_email: email } : {}),
      line_items: [{ price: priceId, quantity: 1 }],
      metadata: {
        job_id,
        address,
        email: email ?? '',
        product: 'granny-flat-analysis',
      },
      success_url: `${origin}/reports/granny-flat?jobId=${job_id}&payment=success&address=${encodeURIComponent(address)}`,
      cancel_url: `${origin}/canibuildit?payment=cancelled&address=${encodeURIComponent(address)}`,
    });

    return NextResponse.json({ checkout_url: session.url });
  } catch (err) {
    console.error('[stripe/checkout/granny-flat] Stripe error:', err);
    return NextResponse.json({ error: 'Failed to create checkout session' }, { status: 500 });
  }
}
