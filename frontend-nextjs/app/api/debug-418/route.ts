/**
 * Debug endpoint to check section 4.1.8 data structure
 */

import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

export async function GET(req: NextRequest) {
  try {
    // First, check what document_ids exist for Marrickville
    const docResult = await query(`
      SELECT DISTINCT document_id
      FROM regulatory_provisions
      WHERE document_id LIKE '%Marrickville%'
      LIMIT 20
    `);

    // Get ALL provisions from the 4.1 document
    const provResult = await query(`
      SELECT
        id,
        document_id,
        pdf_page,
        v2_marker,
        v2_provision_type,
        section_header,
        LEFT(provision_text, 200) as provision_text_preview,
        provision_text as provision_text_full,
        LENGTH(provision_text) as text_length
      FROM regulatory_provisions
      WHERE document_id = 'Marrickville_DCP_2011__4.1_Low_Density_Residential_Development'
        AND (
          section_header LIKE '%4.1.8%'
          OR section_header LIKE '%Dormer%'
          OR v2_marker IN ('C32', 'C33', 'C34', 'C35', 'C36', 'C37', 'C38', 'C39', 'C40')
        )
      ORDER BY pdf_page, id
    `);

    // Get TOC entries for section 4.1.8
    const tocResult = await query(`
      SELECT *
      FROM dcp_table_of_contents
      WHERE document_id = 'Marrickville_DCP_2011__4.1_Low_Density_Residential_Development'
        AND section_number LIKE '4.1.8%'
      ORDER BY section_number
    `);

    return NextResponse.json({
      success: true,
      document_ids: docResult.rows,
      provision_count: provResult.rows.length,
      provisions: provResult.rows,
      toc_count: tocResult.rows.length,
      toc_entries: tocResult.rows,
    }, { status: 200 });
  } catch (error: any) {
    return NextResponse.json({
      error: error.message,
      stack: error.stack
    }, { status: 500 });
  }
}
