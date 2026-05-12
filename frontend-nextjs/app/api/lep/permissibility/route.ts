import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

export const dynamic = 'force-dynamic';

function normalizeLga(raw: string): string {
  // Handle hyphenated names like "Canterbury-Bankstown", "Ku-Ring-Gai"
  return raw.split(' ').map(word =>
    word.split('-').map(part => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase()).join('-')
  ).join(' ');
}

/**
 * GET /api/lep/permissibility?zone=R2&lga=Inner+West
 *
 * Returns all permissibility entries for a zone/LGA pair, gated by lep_zone_coverage.
 * Used to auto-populate WorksScopeAnswers in DCP intake when zone coverage is complete.
 *
 * Response:
 *   covered: false → zone/LGA not in lep_zone_coverage or is_complete = false; entries = []
 *   covered: true  → entries contains all rows for the zone
 */
export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const zone = searchParams.get('zone');
  const lgaRaw = searchParams.get('lga');

  if (!zone || !lgaRaw) {
    return NextResponse.json({ error: 'Missing zone or lga parameter' }, { status: 400 });
  }

  const lga = normalizeLga(lgaRaw);

  try {
    // Safety gate: only return data when coverage is confirmed complete
    const coverageResult = await query(
      `SELECT is_complete, scraped_at, source_url FROM lep_zone_coverage WHERE zone = $1 AND lga = $2`,
      [zone, lga]
    );

    const row = coverageResult.rows[0];
    const covered = row?.is_complete === true;

    if (!covered) {
      return NextResponse.json({ covered: false, zone, lga, entries: [] });
    }

    const result = await query(
      `SELECT development_type, permissibility
       FROM lep_land_use_table
       WHERE zone = $1 AND lga = $2
       ORDER BY permissibility, development_type`,
      [zone, lga]
    );

    return NextResponse.json({
      covered: true,
      zone,
      lga,
      scraped_at: row.scraped_at,
      source_url: row.source_url,
      entries: result.rows,
    });
  } catch (error) {
    console.error('[LEP permissibility]', error);
    return NextResponse.json(
      { error: 'Failed to fetch permissibility data' },
      { status: 500 }
    );
  }
}
