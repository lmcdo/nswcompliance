/**
 * POST /api/stripe/webhook
 *
 * Handles Stripe webhook events. On checkout.session.completed:
 *   1. Verifies signature
 *   2. Reads report_id + email from session metadata
 *   3. Calls the PDF generate route to render the report
 *   4. Emails the PDF to the customer via Resend
 *
 * Must be configured in Stripe dashboard to receive:
 *   - checkout.session.completed
 */

import { NextRequest, NextResponse } from 'next/server';
import Stripe from 'stripe';
import { Resend } from 'resend';

// Stripe requires the raw body for signature verification — disable body parsing
export const dynamic = 'force-dynamic';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2026-04-22.dahlia',
});

const resend = new Resend(process.env.RESEND_API_KEY);

export async function POST(req: NextRequest) {
  const sig = req.headers.get('stripe-signature');
  const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

  if (!sig || !webhookSecret) {
    return NextResponse.json({ error: 'Missing signature or webhook secret' }, { status: 400 });
  }

  let event: Stripe.Event;
  let rawBody: Buffer;

  try {
    rawBody = Buffer.from(await req.arrayBuffer());
    event = stripe.webhooks.constructEvent(rawBody, sig, webhookSecret);
  } catch (err) {
    console.error('[stripe/webhook] Signature verification failed:', err);
    return NextResponse.json({ error: 'Webhook signature invalid' }, { status: 400 });
  }

  if (event.type !== 'checkout.session.completed') {
    // Acknowledge but take no action for other event types
    return NextResponse.json({ received: true });
  }

  const session = event.data.object as Stripe.Checkout.Session;
  const { report_id, email } = session.metadata ?? {};

  if (!report_id || !email) {
    console.error('[stripe/webhook] Missing metadata on session:', session.id);
    // Return 200 so Stripe does not retry — this is a configuration error, not transient
    return NextResponse.json({ received: true });
  }

  // Generate the PDF by calling our own generate route internally
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL ?? 'https://canibuildit.com.au';
  let pdfBuffer: Buffer;

  try {
    const pdfRes = await fetch(`${baseUrl}/api/reports/granny-flat/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ report_id }),
    });

    if (!pdfRes.ok) {
      const errBody = await pdfRes.json().catch(() => ({}));
      throw new Error(`PDF generation failed: ${pdfRes.status} — ${JSON.stringify(errBody)}`);
    }

    pdfBuffer = Buffer.from(await pdfRes.arrayBuffer());
  } catch (err) {
    console.error('[stripe/webhook] PDF generation error:', err);
    // Return 500 — Stripe will retry, giving the pipeline a chance to recover
    return NextResponse.json({ error: 'PDF generation failed' }, { status: 500 });
  }

  // Email the PDF
  const filename = `granny-flat-report-${report_id.slice(0, 8)}.pdf`;

  try {
    await resend.emails.send({
      from: 'Can I Build It <info@plotdetect.com.au>',
      to: [email],
      subject: 'Your Granny Flat Eligibility Report',
      html: `
        <div style="font-family: system-ui, sans-serif; max-width: 520px; margin: 0 auto; color: #111;">
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">
            Your report is attached.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your granny flat eligibility report is attached as a PDF.
            It includes the CDC pathway checklist, applicable setback standards with
            clause citations, a yield sensitivity analysis, and a full data source log.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            You can share this with your builder, certifier, or town planner.
          </p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
          <p style="color: #999; font-size: 12px;">
            Can I Build It? &middot; <a href="https://canibuildit.com.au" style="color: #0d9488;">canibuildit.com.au</a>
          </p>
        </div>
      `,
      attachments: [
        {
          filename,
          content: pdfBuffer,
        },
      ],
    });
  } catch (err) {
    // Email failure is logged but we return 200 — PDF was generated, retry would re-charge
    console.error('[stripe/webhook] Resend email error:', err);
  }

  return NextResponse.json({ received: true });
}
