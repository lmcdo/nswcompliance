/**
 * API endpoint to fetch LEP Part 6 provisions from database
 * Used for Local Provisions from Planning Portal
 */

import { NextRequest, NextResponse } from 'next/server';
import { getClient } from '@/lib/database/pool-manager';


export const dynamic = 'force-dynamic';
const DOCUMENT_ID = 'Inner_West_Local_Environmental_Plan_2022_Part_6';

export async function GET(request: NextRequest) {
  let client;

  try {
    const searchParams = request.nextUrl.searchParams;
    const clauseNumber = searchParams.get('clause');

    if (!clauseNumber) {
      return NextResponse.json(
        { error: 'Missing clause parameter' },
        { status: 400 }
      );
    }

    // Connect to database using pool manager
    client = await getClient();

    // Query provision - search all Inner West LEP documents, prioritize Part 6 and longest text
    const result = await client.query(`
      SELECT
        ref_number as "clauseNumber",
        section_header as "clauseTitle",
        provision_text as "provisionText",
        page_number as "pageNumber"
      FROM regulatory_provisions
      WHERE document_id LIKE 'Inner_West_Local_Environmental_Plan_2022%'
        AND ref_number = $1
      ORDER BY
        CASE WHEN document_id = $2 THEN 0 ELSE 1 END,
        LENGTH(provision_text) DESC
      LIMIT 1
    `, [clauseNumber, DOCUMENT_ID]);

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
