import { NextRequest, NextResponse } from 'next/server';
import { getClient } from '@/lib/db';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const council = searchParams.get('council');

  if (!council) {
    return NextResponse.json({ error: 'council param required' }, { status: 400 });
  }

  const client = await getClient();
  try {
    // State instruments apply to all councils — fetch by NULL council or the specific council
    // needs_review lives on instrument_registry (set TRUE by legislation_monitor.py
    // when an amendment is detected, cleared by update_instrument_provisions.py once
    // a human reconciles). The UI uses it to fail closed: an instrument with a
    // detected-but-unreconciled change must NOT show as "verified/current".
    // LEFT JOIN so currency rows without a registry row (e.g. DCP) default to false.
    const { rows } = await client.query<{
      instrument_key: string;
      instrument_label: string;
      instrument_type: string;
      verified_at: string | null;
      version_label: string | null;
      source_url: string | null;
      needs_review: boolean;
    }>(
      `SELECT ic.instrument_key, ic.instrument_label, ic.instrument_type,
              ic.verified_at, ic.version_label, ic.source_url,
              COALESCE(r.needs_review, FALSE) AS needs_review
       FROM instrument_currency ic
       LEFT JOIN instrument_registry r ON r.instrument_key = ic.instrument_key
       WHERE ic.council = $1 OR ic.council IS NULL
       ORDER BY ic.instrument_type, ic.instrument_label`,
      [council],
    );

    return NextResponse.json({ currency: rows });
  } finally {
    client.release();
  }
}
