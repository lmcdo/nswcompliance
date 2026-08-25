import { NextRequest, NextResponse } from 'next/server';
import { Resend } from 'resend';
import { query } from '@/lib/db';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const VALID_ROLES = ['planner', 'certifier', 'architect', 'conveyancer', 'agent', 'developer', 'other'];

// Off-domain recipient: from/to both @plotdetect.com.au via Resend is
// quarantined by Google Workspace as self-domain spoofing (shows "delivered"
// but never lands). Keep this on a different domain than the sender.
const NOTIFY_EMAIL = process.env.NOTIFY_EMAIL || 'lawrence.mcdonell@gmail.com';

export async function POST(request: NextRequest) {
  try {
    const { email, role, council_name, address, source } = await request.json();

    if (!email) {
      return NextResponse.json({ error: 'email is required' }, { status: 400 });
    }

    if (!EMAIL_REGEX.test(email)) {
      return NextResponse.json({ error: 'invalid email address' }, { status: 400 });
    }

    const normalised = email.trim().toLowerCase();
    const safeRole = role && VALID_ROLES.includes(role) ? role : null;
    const safeSource = source || 'assessment';

    await query(
      `INSERT INTO verify_interest (email, role, council_name, address, source)
       VALUES ($1, $2, $3, $4, $5)
       ON CONFLICT (email, source) DO UPDATE SET
         role = COALESCE(EXCLUDED.role, verify_interest.role),
         council_name = COALESCE(EXCLUDED.council_name, verify_interest.council_name),
         address = COALESCE(EXCLUDED.address, verify_interest.address)`,
      [normalised, safeRole, council_name?.trim() || null, address?.trim() || null, safeSource]
    );

    // Notify — fire and forget
    if (process.env.RESEND_API_KEY) {
      const resend = new Resend(process.env.RESEND_API_KEY);
      await resend.emails.send({
        from: 'PlotDetect <info@plotdetect.com.au>',
        to: NOTIFY_EMAIL,
        subject: `Verify interest: ${safeRole || 'unknown role'} — ${council_name || 'no council'}`,
        text: `New Verify registration\n\nEmail: ${normalised}\nRole: ${safeRole || '(not provided)'}\nCouncil: ${council_name || '(not provided)'}\nAddress: ${address || '(not provided)'}\nSource: ${safeSource}`,
      }).catch(err => console.error('[verify-interest] resend error:', err));
    }

    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error('[verify-interest] POST error:', err);
    return NextResponse.json({ error: 'internal server error' }, { status: 500 });
  }
}
