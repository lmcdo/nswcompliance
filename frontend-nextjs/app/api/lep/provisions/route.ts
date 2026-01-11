/**
 * API endpoint to fetch LEP Part 6 provisions from database
 * Used for Local Provisions from Planning Portal
 */

import { NextRequest, NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

const DB_PATH = path.join(process.cwd(), '..', 'nsw_planning.db');
const DOCUMENT_ID = 'Inner_West_Local_Environmental_Plan_2022_Part_6';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const clauseNumber = searchParams.get('clause');

    if (!clauseNumber) {
      return NextResponse.json(
        { error: 'Missing clause parameter' },
        { status: 400 }
      );
    }

    // Open database
    const db = new Database(DB_PATH, { readonly: true });

    // Query provision - search all Inner West LEP documents, prioritize Part 6 and longest text
    const provision = db.prepare(`
      SELECT
        ref_number as clauseNumber,
        section_header as clauseTitle,
        provision_text as provisionText,
        page_number as pageNumber
      FROM regulatory_provisions
      WHERE document_id LIKE 'Inner_West_Local_Environmental_Plan_2022%'
        AND ref_number = ?
      ORDER BY
        CASE WHEN document_id = ? THEN 0 ELSE 1 END,
        LENGTH(provision_text) DESC
      LIMIT 1
    `).get(clauseNumber, DOCUMENT_ID);

    db.close();

    if (!provision) {
      return NextResponse.json(
        { error: 'Provision not found' },
        { status: 404 }
      );
    }

    return NextResponse.json(provision);

  } catch (error) {
    console.error('Error fetching LEP provision:', error);
    return NextResponse.json(
      { error: 'Failed to fetch provision' },
      { status: 500 }
    );
  }
}
