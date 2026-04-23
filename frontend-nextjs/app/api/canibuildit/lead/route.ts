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

  // Send confirmation email
  const addressLabel = cleanAddress ?? 'your property';
  try {
    await resend.emails.send({
      from: 'Can I Build It <info@plotdetect.com.au>',
      to: [cleanEmail],
      subject: `Your granny flat check is running — ${addressLabel}`,
      html: `
        <div style="font-family: system-ui, sans-serif; max-width: 520px; margin: 0 auto; color: #111;">
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">
            We're on it.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            Your granny flat check for <strong>${addressLabel}</strong> is running.
            We're pulling live aerial imagery, running satellite structure detection,
            and cross-referencing NSW Planning Portal rules — this takes 1–3 minutes.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            You can close the tab. We'll send your result here as soon as it's ready.
          </p>
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
