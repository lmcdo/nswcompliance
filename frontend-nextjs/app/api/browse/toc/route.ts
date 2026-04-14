/**
 * Browse TOC API - Table of Contents for DCP Navigation
 * Returns hierarchical TOC structure with provision counts
 *
 * Purpose: Enable professional DCP browsing by section/subsection
 * Use case: User browses "Marrickville DCP 2011 - 2.10 Parking" → sees subsections with counts
 */

import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';


export const dynamic = 'force-dynamic';
interface TOCSection {
  sectionNumber: string;
  sectionTitle: string;
  pageStart: number;
  pageEnd: number | null;
  partNumber: number;
  depth: number;
  parentSection: string | null;
  provisionCount: number;
  documentId: string;
}

interface TOCResponse {
  documentId: string;
  sections: TOCSection[];
  totalProvisions: number;
  groupedByPart: Record<number, TOCSection[]>;
}

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body = await request.json();
    const { documentId } = body;

    if (!documentId) {
      return NextResponse.json(
        {
          success: false,
          error: 'Document ID is required',
          details: 'Provide documentId in request body'
        },
        { status: 400 }
      );
    }

    console.log(`[Browse TOC] Fetching TOC for: ${documentId}`);

    // Query TOC with provision counts
    const tocResult = await query(`
      SELECT
        t.section_number,
        t.section_title,
        t.page_start,
        t.page_end,
        t.part_number,
        t.depth,
        t.parent_section,
        t.document_id,
        (
          SELECT COUNT(*)
          FROM regulatory_provisions p
          WHERE p.document_id = t.document_id
            AND p.is_current = TRUE
            AND p.pdf_page >= t.page_start
            AND (p.pdf_page <= t.page_end OR t.page_end IS NULL)
        ) as provision_count
      FROM dcp_table_of_contents t
      WHERE t.document_id = $1
      ORDER BY t.page_start
    `, [documentId]);

    if (tocResult.rows.length === 0) {
      return NextResponse.json(
        {
          success: false,
          error: 'TOC not found',
          details: `No TOC found for document: ${documentId}`,
          suggestion: 'This document may not have an extracted TOC. Use direct provision query instead.'
        },
        { status: 404 }
      );
    }

    // Transform to typed response
    const sections: TOCSection[] = tocResult.rows.map((row) => ({
      sectionNumber: row.section_number,
      sectionTitle: row.section_title,
      pageStart: row.page_start,
      pageEnd: row.page_end,
      partNumber: row.part_number,
      depth: row.depth,
      parentSection: row.parent_section,
      provisionCount: parseInt(row.provision_count),
      documentId: row.document_id
    }));

    // Group by part number for hierarchical display
    const groupedByPart: Record<number, TOCSection[]> = {};
    sections.forEach((section) => {
      if (!groupedByPart[section.partNumber]) {
        groupedByPart[section.partNumber] = [];
      }
      groupedByPart[section.partNumber].push(section);
    });

    // Calculate total provisions
    const totalProvisions = sections.reduce((sum, s) => sum + s.provisionCount, 0);

    const response: TOCResponse = {
      documentId,
      sections,
      totalProvisions,
      groupedByPart
    };

    const responseTime = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      data: response,
      meta: {
        responseTimeMs: responseTime,
        sectionCount: sections.length,
        partCount: Object.keys(groupedByPart).length,
        source: 'dcp_table_of_contents'
      }
    });

  } catch (error) {
    const responseTime = Date.now() - startTime;
    console.error('[Browse TOC] Error:', error);

    return NextResponse.json(
      {
        success: false,
        error: 'Internal server error',
        details: error instanceof Error ? error.message : 'Unknown error',
        responseTimeMs: responseTime
      },
      { status: 500 }
    );
  }
}

/**
 * GET endpoint for URL-based queries
 * /api/browse/toc?documentId=Marrickville_DCP_2011__2_10_Parking
 */
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const documentId = searchParams.get('documentId');

  if (!documentId) {
    return NextResponse.json(
      {
        success: false,
        error: 'Document ID is required',
        details: 'Provide documentId as query parameter'
      },
      { status: 400 }
    );
  }

  // Reuse POST logic by forwarding to POST handler
  return POST(new NextRequest(request.url, {
    method: 'POST',
    body: JSON.stringify({ documentId }),
    headers: { 'Content-Type': 'application/json' }
  }));
}
