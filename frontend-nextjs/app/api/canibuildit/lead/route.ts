import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { Resend } from 'resend';

const resend = new Resend(process.env.RESEND_API_KEY);

export async function POST(req: NextRequest) {
  const { email, address, eligible, lga_name, interest_type } = await req.json();
  if (!email?.trim()) {
    return NextResponse.json({ error: 'email required' }, { status: 400 });
  }

  const cleanEmail = email.trim().toLowerCase();
  const cleanAddress = address?.trim() || null;

  try {
    const supabase = await createClient();
    await supabase.from('canibuildit_leads').insert({
      email: cleanEmail,
      address: cleanAddress,
      eligible: eligible ?? null,
      ...(lga_name ? { lga_name: lga_name.trim() } : {}),
      ...(interest_type ? { interest_type: interest_type.trim() } : {}),
    });
  } catch {
    // Non-blocking — don't error the user if DB insert fails
  }

  // Send confirmation email — copy varies by product
  const addressLabel = cleanAddress ?? 'your property';
  const { subject, body } = buildEmailContent(interest_type ?? 'granny-flat', addressLabel);
  try {
    await resend.emails.send({
      from: 'Can I Build It <info@plotdetect.com.au>',
      reply_to: 'hello@canibuildit.com.au',
      to: [cleanEmail],
      subject,
      html: `
        <div style="font-family: system-ui, sans-serif; max-width: 520px; margin: 0 auto; color: #111;">
          ${body}
          <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
          <p style="color: #999; font-size: 12px;">
            Can I Build It? &middot; <a href="https://canibuildit.com.au" style="color: #0d9488;">canibuildit.com.au</a>
          </p>
        </div>
      `,
    });
  } catch (emailErr) {
    console.error('[canibuildit/lead] Resend error:', emailErr);
  }

  return NextResponse.json({ ok: true });
}

export function buildEmailContent(product: string, address: string): { subject: string; body: string } {
  switch (product) {
    case 'flood':
    case 'flood-truth':
      return {
        subject: `Your flood risk result — ${address}`,
        body: `
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Your flood risk result is ready.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your flood risk check for <strong>${address}</strong> is complete.
            Visit <a href="https://canibuildit.com.au/reports/flood" style="color: #0d9488;">canibuildit.com.au/reports/flood</a>
            to run it again or check another address.
          </p>`,
      };
    case 'solar-yield':
    case 'solar':
      return {
        subject: `Your solar yield estimate — ${address}`,
        body: `
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Your solar estimate is ready.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your solar yield check for <strong>${address}</strong> is complete.
            Visit <a href="https://canibuildit.com.au/reports/solar-yield" style="color: #0d9488;">canibuildit.com.au/reports/solar-yield</a>
            to run it again or check another address.
          </p>`,
      };
    case 'shadow':
      return {
        subject: `Your shadow analysis — ${address}`,
        body: `
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Your shadow analysis is ready.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your shadow analysis for <strong>${address}</strong> is complete.
            Visit <a href="https://canibuildit.com.au/reports/shadow" style="color: #0d9488;">canibuildit.com.au/reports/shadow</a>
            to run it again or check another address.
          </p>`,
      };
    case 'threat-radar':
      return {
        subject: `Your Threat Radar result — ${address}`,
        body: `
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Your Threat Radar result is ready.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your DA activity check for <strong>${address}</strong> is complete.
            Visit <a href="https://canibuildit.com.au/reports/threat-radar" style="color: #0d9488;">canibuildit.com.au/reports/threat-radar</a>
            to monitor this address or check another.
          </p>`,
      };
    case 'granny-flat':
    default:
      return {
        subject: `Your granny flat check is running — ${address}`,
        body: `
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">We're on it.</p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your granny flat check for <strong>${address}</strong> is running.
            We're pulling live aerial imagery, running satellite structure detection,
            and cross-referencing NSW Planning Portal rules — this takes 1–3 minutes.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            You can close the tab. We'll send your result here as soon as it's ready.
          </p>`,
      };
  }
}
