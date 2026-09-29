/**
 * API endpoint to fetch stored LEP clause text (Part 5 / Part 6) from the database.
 * Used by the LEP tab's heritage and local provisions cards.
 *
 * `epi` is REQUIRED and scopes the lookup to that instrument's own rows. Clause numbers
 * repeat across every Standard Instrument LEP, so a lookup by clause number alone (the
 * previous behaviour) returned Inner West LEP 2022 text for any council's clause 5.10 or
 * 6.x. An EPI with no stored text gets a 404 — callers show the live legislation link.
 */

import { NextRequest, NextResponse } from 'next/server';
import { getClient } from '@/lib/database/pool-manager';
import { LEP_TEXT_DOCUMENT_PREFIXES } from '@/lib/citation-instrument-urls';


export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  let client;

  try {
    const searchParams = request.nextUrl.searchParams;
    const clauseNumber = searchParams.get('clause');
    const epi = searchParams.get('epi')?.toLowerCase() ?? null;

    if (!clauseNumber || !epi) {
      return NextResponse.json(
        { error: 'Missing clause or epi parameter' },
        { status: 400 }
      );
    }

    const documentPrefix = LEP_TEXT_DOCUMENT_PREFIXES[epi];
    if (!documentPrefix) {
      return NextResponse.json(
        { error: 'No stored clause text for this instrument' },
        { status: 404 }
      );
    }

    // Connect to database using pool manager
    client = await getClient();

    // This instrument's rows only (exact prefix — LIKE would treat '_' as a wildcard),
    // skipping rows explicitly marked superseded; prefer Part 6, then the longest text.
    const result = await client.query(`
      SELECT
        ref_number as "clauseNumber",
        section_header as "clauseTitle",
        provision_text as "provisionText",
        page_number as "pageNumber"
      FROM regulatory_provisions
      WHERE left(document_id, length($2)) = $2
        AND ref_number = $1
        AND is_current IS NOT FALSE
      ORDER BY
        CASE WHEN document_id = $2 || '_Part_6' THEN 0 ELSE 1 END,
        LENGTH(provision_text) DESC
      LIMIT 1
    `, [clauseNumber, documentPrefix]);

    if (result.rows.length === 0) {
      return NextResponse.json(
        { error: 'Provision not found' },
        { status: 404 }
      );
    }

    return NextResponse.json(result.rows[0]);

  } catch (error) {
    console.error('Error fetching LEP provision:', error);
    return NextResponse.json(
      { error: 'Failed to fetch provision', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  } finally {
    if (client) {
      client.release();
    }
  }
}
