import { NextRequest, NextResponse } from 'next/server';
import { Resend } from 'resend';
import { query } from '@/lib/db';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function POST(request: NextRequest) {
  try {
    const { email, council_name, address } = await request.json();

    if (!email || !council_name) {
      return NextResponse.json({ error: 'email and council_name are required' }, { status: 400 });
    }

    if (!EMAIL_REGEX.test(email)) {
      return NextResponse.json({ error: 'invalid email address' }, { status: 400 });
    }

    const normalised = email.trim().toLowerCase();

    await query(
      `INSERT INTO dcp_interest (email, council_name, address)
       VALUES ($1, $2, $3)
       ON CONFLICT (email, council_name) DO NOTHING`,
      [normalised, council_name.trim(), address?.trim() || null]
    );

    // Notify info@plotdetect.com.au — fire and forget, don't fail the request
    if (process.env.RESEND_API_KEY) {
      const resend = new Resend(process.env.RESEND_API_KEY);
      resend.emails.send({
        from: 'PlotDetect <info@plotdetect.com.au>',
        to: 'info@plotdetect.com.au',
        subject: `DCP interest: ${council_name}`,
        text: `New DCP interest registration\n\nEmail: ${normalised}\nCouncil: ${council_name}\nAddress: ${address || '(not provided)'}`,
      }).catch(err => console.error('[dcp-interest] resend error:', err));
    }

    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error('[dcp-interest] POST error:', err);
    return NextResponse.json({ error: 'internal server error' }, { status: 500 });
  }
}

// GET /api/dcp-interest — internal demand summary (council → count)
export async function GET() {
  try {
    const result = await query(
      `SELECT council_name, COUNT(*) AS interest_count
       FROM dcp_interest
       GROUP BY council_name
       ORDER BY interest_count DESC`
    );
    return NextResponse.json({ data: result.rows });
  } catch (err) {
    console.error('[dcp-interest] GET error:', err);
    return NextResponse.json({ error: 'internal server error' }, { status: 500 });
  }
}
