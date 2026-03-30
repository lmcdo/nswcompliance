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
    const { rows } = await client.query<{
      instrument_key: string;
      instrument_label: string;
      instrument_type: string;
      verified_at: string | null;
      version_label: string | null;
      source_url: string | null;
    }>(
      `SELECT instrument_key, instrument_label, instrument_type,
              verified_at, version_label, source_url
       FROM instrument_currency
       WHERE council = $1 OR council IS NULL
       ORDER BY instrument_type, instrument_label`,
      [council],
    );

    return NextResponse.json({ currency: rows });
  } finally {
    client.release();
  }
}
