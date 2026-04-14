/**
 * Browse Section API - Provisions for Specific TOC Section
 * Returns all provisions for a DCP section or subsection
 *
 * Purpose: Enable focused browsing of specific DCP sections
 * Use case: User clicks "2.10.1 Objectives" → sees all 8 provisions for that subsection
 */

import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { dataRateLimiter, getClientIdentifier, checkRateLimit, createRateLimitHeaders } from '@/lib/rate-limit';


export const dynamic = 'force-dynamic';
interface Provision {
  id: number;
  documentId: string;
  refNumber: string;
  sectionHeader: string | null;
  provisionText: string;
  provisionType: string | null;
  pdfPage: number | null;
  zone: string | null;
  developmentType: string | null;
}

interface SectionInfo {
  sectionNumber: string;
  sectionTitle: string;
  pageStart: number;
  pageEnd: number | null;
  depth: number;
  parentSection: string | null;
}

interface SectionResponse {
  sectionInfo: SectionInfo;
  provisions: Provision[];
  count: number;
}

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body = await request.json();
    const { sectionNumber, documentId } = body;

    if (!sectionNumber || !documentId) {
      return NextResponse.json(
        {
          success: false,
          error: 'Section number and document ID are required',
          details: 'Provide sectionNumber and documentId in request body'
        },
        { status: 400 }
      );
    }

    console.log(`[Browse Section] Fetching provisions for: ${documentId} / ${sectionNumber}`);

    // First, get section info from TOC
    const sectionResult = await query(`
      SELECT
        section_number,
        section_title,
        page_start,
        page_end,
        depth,
        parent_section
      FROM dcp_table_of_contents
      WHERE document_id = $1 AND section_number = $2
    `, [documentId, sectionNumber]);

    if (sectionResult.rows.length === 0) {
      return NextResponse.json(
        {
          success: false,
          error: 'Section not found',
          details: `No TOC entry found for: ${documentId} / ${sectionNumber}`
        },
        { status: 404 }
      );
    }

    const section = sectionResult.rows[0];

    // Get provisions linked by page range
    // Build query conditionally based on whether page_end exists
    let provisionQuery: string;
    let provisionParams: any[];

    if (section.page_end === null) {
      provisionQuery = `
        SELECT
          p.id,
          p.document_id,
          p.ref_number,
          p.section_header,
          p.provision_text,
          p.provision_type,
          p.pdf_page,
          p.zone,
          p.development_type
        FROM regulatory_provisions p
        WHERE p.document_id = $1
          AND p.is_current = TRUE
          AND p.pdf_page >= $2
        ORDER BY p.pdf_page, p.id
      `;
      provisionParams = [documentId, section.page_start];
    } else {
      provisionQuery = `
        SELECT
          p.id,
          p.document_id,
          p.ref_number,
          p.section_header,
          p.provision_text,
          p.provision_type,
          p.pdf_page,
          p.zone,
          p.development_type
        FROM regulatory_provisions p
        WHERE p.document_id = $1
          AND p.is_current = TRUE
          AND p.pdf_page >= $2
          AND p.pdf_page <= $3
        ORDER BY p.pdf_page, p.id
      `;
      provisionParams = [documentId, section.page_start, section.page_end];
    }

    const provisionsResult = await query(provisionQuery, provisionParams);

    // Transform provisions
    const provisions: Provision[] = provisionsResult.rows.map((row) => ({
      id: row.id,
      documentId: row.document_id,
      refNumber: row.ref_number,
      sectionHeader: row.section_header,
      provisionText: row.provision_text,
      provisionType: row.provision_type,
      pdfPage: row.pdf_page,
      zone: row.zone,
      developmentType: row.development_type
    }));

    const sectionInfo: SectionInfo = {
      sectionNumber: section.section_number,
      sectionTitle: section.section_title,
      pageStart: section.page_start,
      pageEnd: section.page_end,
      depth: section.depth,
      parentSection: section.parent_section
    };

    const response: SectionResponse = {
      sectionInfo,
      provisions,
      count: provisions.length
    };

    const responseTime = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      data: response,
      meta: {
        responseTimeMs: responseTime,
        provisionCount: provisions.length,
        pageRange: section.page_end
          ? `${section.page_start}-${section.page_end}`
          : `${section.page_start}+`,
        source: 'regulatory_provisions + dcp_table_of_contents'
      }
    });

  } catch (error) {
    const responseTime = Date.now() - startTime;
    console.error('[Browse Section] Error:', error);

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
 * /api/browse/section?documentId=...&sectionNumber=2.10.1
 */
export async function GET(request: NextRequest) {
  const clientIP = getClientIdentifier(request);
  const rateLimitResult = await checkRateLimit(clientIP, dataRateLimiter, 30, 60000);
  if (!rateLimitResult.success) {
    return NextResponse.json(
      { error: 'Rate limit exceeded. Please try again in a minute.' },
      { status: 429, headers: createRateLimitHeaders(rateLimitResult) }
    );
  }

  const searchParams = request.nextUrl.searchParams;
  const documentId = searchParams.get('documentId');
  const sectionNumber = searchParams.get('sectionNumber');

  if (!documentId || !sectionNumber) {
    return NextResponse.json(
      {
        success: false,
        error: 'Document ID and section number are required',
        details: 'Provide documentId and sectionNumber as query parameters'
      },
      { status: 400 }
    );
  }

  // Reuse POST logic by forwarding to POST handler
  return POST(new NextRequest(request.url, {
    method: 'POST',
    body: JSON.stringify({ documentId, sectionNumber }),
    headers: { 'Content-Type': 'application/json' }
  }));
}
