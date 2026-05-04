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
  const meta = session.metadata ?? {};

  // ---------------------------------------------------------------------------
  // Route by product
  // ---------------------------------------------------------------------------

  if (session.mode === 'subscription' && meta.product === 'threat-radar-monitor') {
    return handleThreatRadarMonitor(session, meta);
  }

  if (meta.product === 'pre-da-history-report') {
    return handlePreDAHistoryReport(session, meta);
  }

  if (meta.product === 'flood-truth-report') {
    return handleSatelliteReport(session, meta, 'flood-truth');
  }

  if (meta.product === 'shadow-report') {
    return handleSatelliteReport(session, meta, 'shadow');
  }

  if (meta.product === 'solar-yield-report') {
    return handleSatelliteReport(session, meta, 'solar-yield');
  }

  if (meta.product === 'granny-flat-analysis') {
    return handleGrannyFlatAnalysis(session, meta);
  }

  // Default: granny flat one-time report PDF (legacy flow)
  return handleGrannyFlatReport(session, meta);
}

// ---------------------------------------------------------------------------
// Threat Radar monitoring subscription — activate monitoring + confirm email
// ---------------------------------------------------------------------------

async function handleThreatRadarMonitor(
  session: Stripe.Checkout.Session,
  meta: Record<string, string>
) {
  const { email, address } = meta;

  if (!email || !address) {
    console.error('[stripe/webhook] threat-radar-monitor missing metadata on session:', session.id);
    return NextResponse.json({ received: true });
  }

  // Activate monitoring by calling the existing threat-radar subscribe endpoint
  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://canibuildit.com.au';
  try {
    await fetch(`${baseUrl}/api/satellite/threat-radar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ address, email, stripe_subscription_id: session.subscription }),
    });
  } catch (err) {
    // Log but don't retry — monitoring save failure is non-critical
    console.error('[stripe/webhook] threat-radar monitoring activation error:', err);
  }

  // Send confirmation email
  try {
    await resend.emails.send({
      from: 'Can I Build It <info@plotdetect.com.au>',
      replyTo: 'hello@canibuildit.com.au',
      to: [email],
      subject: 'Threat Radar monitoring activated',
      html: `
        <div style="font-family: system-ui, sans-serif; max-width: 520px; margin: 0 auto; color: #111;">
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">
            You're now being monitored.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            We'll send you a weekly email every Monday when new DA or CDC applications
            are lodged within 200m of <strong>${address}</strong>.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            To cancel your subscription, reply to this email or visit your Stripe billing portal.
          </p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
          <p style="color: #999; font-size: 12px;">
            Can I Build It? &middot; <a href="https://canibuildit.com.au" style="color: #0d9488;">canibuildit.com.au</a>
          </p>
        </div>
      `,
    });
  } catch (err) {
    console.error('[stripe/webhook] threat-radar confirm email error:', err);
  }

  return NextResponse.json({ received: true });
}

// ---------------------------------------------------------------------------
// Granny Flat analysis (new paywall flow) — detect already running, send link
// ---------------------------------------------------------------------------

async function handleGrannyFlatAnalysis(
  session: Stripe.Checkout.Session,
  meta: Record<string, string>
) {
  const { job_id, address } = meta;
  // Use metadata email first; fall back to email Stripe collected at checkout
  const email = meta.email || session.customer_details?.email || session.customer_email || '';

  if (!job_id || !address) {
    console.error('[stripe/webhook] granny-flat-analysis missing metadata on session:', session.id);
    return NextResponse.json({ received: true });
  }

  if (!email) {
    // No email anywhere — nothing to send, but still acknowledge
    return NextResponse.json({ received: true });
  }

  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://canibuildit.com.au';
  const resultsUrl = `${baseUrl}/reports/granny-flat?jobId=${job_id}&payment=success&address=${encodeURIComponent(address)}`;

  try {
    await resend.emails.send({
      from: 'Can I Build It <info@plotdetect.com.au>',
      replyTo: 'hello@canibuildit.com.au',
      to: [email],
      subject: 'Your granny flat analysis — view your results',
      html: `
        <div style="font-family: system-ui, sans-serif; max-width: 520px; margin: 0 auto; color: #111;">
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">
            Your analysis is running.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your granny flat analysis for <strong>${address}</strong> is in progress.
            The AI is scanning aerial imagery and cross-referencing NSW planning rules.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Click the button below to view your results — takes 1&ndash;3 minutes on first run.
          </p>
          <p style="margin: 28px 0;">
            <a href="${resultsUrl}"
               style="display: inline-block; padding: 12px 24px; background: #0d9488; color: white;
                      text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 14px;">
              View your results &rarr;
            </a>
          </p>
          <p style="color: #999; font-size: 12px;">
            This link is unique to your purchase. Bookmark it for your records.
          </p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
          <p style="color: #999; font-size: 12px;">
            Can I Build It? &middot; <a href="https://canibuildit.com.au" style="color: #0d9488;">canibuildit.com.au</a>
          </p>
        </div>
      `,
    });
  } catch (err) {
    console.error('[stripe/webhook] granny-flat-analysis email error:', err);
  }

  return NextResponse.json({ received: true });
}

// ---------------------------------------------------------------------------
// Granny Flat one-time report — generate PDF + email attachment
// ---------------------------------------------------------------------------

async function handleGrannyFlatReport(
  _session: Stripe.Checkout.Session,
  meta: Record<string, string>
) {
  const { report_id, email } = meta;

  if (!report_id || !email) {
    console.error('[stripe/webhook] granny-flat missing metadata');
    return NextResponse.json({ received: true });
  }

  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://canibuildit.com.au';
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
    return NextResponse.json({ error: 'PDF generation failed' }, { status: 500 });
  }

  const filename = `granny-flat-report-${report_id.slice(0, 8)}.pdf`;

  try {
    await resend.emails.send({
      from: 'Can I Build It <info@plotdetect.com.au>',
      replyTo: 'hello@canibuildit.com.au',
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

// ---------------------------------------------------------------------------
// Flood Truth / Shadow / Solar Yield — generate PDF + email attachment
// ---------------------------------------------------------------------------

const SATELLITE_REPORT_META: Record<
  'flood-truth' | 'shadow' | 'solar-yield',
  { generatePath: string; subject: string; bodyLine: string; filePrefix: string }
> = {
  'flood-truth': {
    generatePath: '/api/reports/flood/generate',
    subject: 'Your Flood Truth Report',
    bodyLine: 'Your Flood Truth Report is attached as a PDF. It includes your statutory flood zone classification, council flood study overlay, BOM gauge flood event history, 40-year satellite water history, Copernicus EMS observed events, and full data source citations.',
    filePrefix: 'flood-truth-report',
  },
  'shadow': {
    generatePath: '/api/reports/shadow/generate',
    subject: 'Your Shadow Analysis Report',
    bodyLine: 'Your Shadow Analysis Report is attached as a PDF. It includes hourly and seasonal shadow diagrams, ADG compliance assessment, and an objection-ready summary for your council submission.',
    filePrefix: 'shadow-report',
  },
  'solar-yield': {
    generatePath: '/api/reports/solar-yield/generate',
    subject: 'Your Solar Yield Report',
    bodyLine: 'Your Solar Yield Report is attached as a PDF. It includes system sizing, installed cost estimate, annual bill savings, payback period, and a monthly kWh breakdown.',
    filePrefix: 'solar-yield-report',
  },
};

async function handleSatelliteReport(
  _session: Stripe.Checkout.Session,
  meta: Record<string, string>,
  product: 'flood-truth' | 'shadow' | 'solar-yield'
) {
  const { report_id, email } = meta;
  const cfg = SATELLITE_REPORT_META[product];

  if (!report_id || !email) {
    console.error(`[stripe/webhook] ${product} missing metadata`);
    return NextResponse.json({ received: true });
  }

  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://canibuildit.com.au';
  let pdfBuffer: Buffer;

  try {
    const pdfRes = await fetch(`${baseUrl}${cfg.generatePath}`, {
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
    console.error(`[stripe/webhook] ${product} PDF generation error:`, err);
    return NextResponse.json({ error: 'PDF generation failed' }, { status: 500 });
  }

  const filename = `${cfg.filePrefix}-${report_id.slice(0, 8)}.pdf`;

  try {
    await resend.emails.send({
      from: 'Can I Build It <info@plotdetect.com.au>',
      replyTo: 'hello@canibuildit.com.au',
      to: [email],
      subject: cfg.subject,
      html: `
        <div style="font-family: system-ui, sans-serif; max-width: 520px; margin: 0 auto; color: #111;">
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Your report is attached.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">${cfg.bodyLine}</p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
          <p style="color: #999; font-size: 12px;">
            Can I Build It? &middot; <a href="https://canibuildit.com.au" style="color: #0d9488;">canibuildit.com.au</a>
          </p>
        </div>
      `,
      attachments: [{ filename, content: pdfBuffer }],
    });
  } catch (err) {
    console.error(`[stripe/webhook] ${product} Resend email error:`, err);
  }

  return NextResponse.json({ received: true });
}

// ---------------------------------------------------------------------------
// Pre-DA Site History — generate PDF + email attachment
// ---------------------------------------------------------------------------

async function handlePreDAHistoryReport(
  _session: Stripe.Checkout.Session,
  meta: Record<string, string>
) {
  const { report_id, email } = meta;

  if (!report_id || !email) {
    console.error('[stripe/webhook] pre-da-history missing metadata');
    return NextResponse.json({ received: true });
  }

  const baseUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://canibuildit.com.au';

  let pdfBuffer: Buffer;

  try {
    const pdfRes = await fetch(`${baseUrl}/api/reports/pre-da-history/generate`, {
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
    console.error('[stripe/webhook] pre-da-history PDF generation error:', err);
    return NextResponse.json({ error: 'PDF generation failed' }, { status: 500 });
  }

  const filename = `pre-da-history-${report_id.slice(0, 8)}.pdf`;

  try {
    await resend.emails.send({
      from: 'Can I Build It <info@plotdetect.com.au>',
      replyTo: 'hello@canibuildit.com.au',
      to: [email],
      subject: 'Your Pre-DA Site History Report',
      html: `
        <div style="font-family: system-ui, sans-serif; max-width: 520px; margin: 0 auto; color: #111;">
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">
            Your report is attached.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your Pre-DA Site History Report is attached as a PDF.
            It covers satellite change detection across 2017–2024, matched DA and CC events from
            the NSW ePlanning Portal, heritage flag status, and flood/bushfire event annotations.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            You can share this with your town planner, solicitor, or buyer's agent for preliminary due diligence.
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
    console.error('[stripe/webhook] pre-da-history Resend email error:', err);
  }

  return NextResponse.json({ received: true });
}
