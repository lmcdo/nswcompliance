import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { getResend } from '@/lib/resend-client';
import { z } from 'zod';

const getSupabase = () => createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

const schema = z.object({
  email: z.string().email(),
  address: z.string().min(5),
  suburb: z.string().optional(),
  postcode: z.string().optional(),
  lat: z.number().optional(),
  lng: z.number().optional(),
});

function extractSuburbPostcode(address: string): { suburb: string | null; postcode: string | null } {
  // "42 Audley St, Petersham NSW 2049, Australia"
  const match = address.match(/,\s*([^,]+?)\s+NSW\s+(\d{4})/i);
  if (match) return { suburb: match[1].trim(), postcode: match[2] };
  return { suburb: null, postcode: null };
}

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });
  }

  const parsed = schema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: 'Invalid input' }, { status: 422 });
  }

  const { email, address, lat, lng } = parsed.data;
  const { suburb, postcode } = extractSuburbPostcode(address);

  // Insert — ignore duplicate (same email + address)
  const { error: dbError } = await getSupabase()
    .from('solar_coverage_interest')
    .upsert(
      { email, address, suburb, postcode, lat, lng },
      { onConflict: 'email,address', ignoreDuplicates: true }
    );

  if (dbError) {
    console.error('[solar-coverage-interest] DB error:', dbError.message);
    return NextResponse.json({ error: 'Could not save your interest' }, { status: 500 });
  }

  // Send confirmation email via Resend
  const suburbLabel = suburb ?? 'your area';
  try {
    await getResend()?.emails.send({
      from: 'PlotDetect <info@plotdetect.com.au>',
      to: [email],
      subject: `We'll notify you when full solar analysis reaches ${suburbLabel}`,
      html: `
        <div style="font-family: system-ui, sans-serif; max-width: 520px; margin: 0 auto; color: #111;">
          <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">
            You're on the list.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            We're expanding building-level solar analysis — precise roof area, orientation,
            and panel count — beyond Sydney metro to cover all of NSW.
          </p>
          <p style="color: #555; font-size: 14px; line-height: 1.6;">
            We'll send you one email when full analysis is available for
            <strong>${suburbLabel}</strong>. No spam, no newsletter.
          </p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;" />
          <p style="color: #999; font-size: 12px;">
            Address checked: ${address}<br />
            PlotDetect &middot; <a href="https://plotdetect.com.au" style="color: #0d9488;">plotdetect.com.au</a>
          </p>
        </div>
      `,
    });
  } catch (emailErr) {
    // Don't fail the request if email send fails — signup is still recorded
    console.error('[solar-coverage-interest] Resend error:', emailErr);
  }

  return NextResponse.json({ ok: true, suburb: suburbLabel });
}
