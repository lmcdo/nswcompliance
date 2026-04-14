import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

/**
 * Fetch provisions by their IDs
 * Used for source traceability in categorized requirements
 */

interface ProvisionsByIdsRequest {
  ids: number[];
}

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body: ProvisionsByIdsRequest = await request.json();
    const { ids } = body;

    if (!ids || !Array.isArray(ids) || ids.length === 0) {
      return NextResponse.json({
        success: false,
        error: 'Must provide an array of provision IDs'
      }, { status: 400 });
    }

    // Limit to reasonable number of IDs
    if (ids.length > 100) {
      return NextResponse.json({
        success: false,
        error: 'Too many IDs (max 100)'
      }, { status: 400 });
    }

    // Query provisions by IDs
    const placeholders = ids.map((_, i) => `$${i + 1}`).join(', ');
    const provisionsQuery = `
      SELECT
        rp.id,
        rp.document_id,
        rp.provision_type,
        rp.ref_number,
        rp.provision_text,
        rp.section_header,
        rp.zone,
        rp.development_type,
        rp.page_number,
        rp.pdf_page_image_url,
        d.pdf_name,
        d.regulation_year,
        d.amendment_reference
      FROM regulatory_provisions rp
      LEFT JOIN documents d ON rp.document_id = d.id
      WHERE rp.id IN (${placeholders})
        AND rp.is_current = TRUE
      ORDER BY rp.id
    `;

    const result = await query(provisionsQuery, ids);

    console.log(`[Provisions By IDs API] Found ${result.rows.length} provisions for ${ids.length} IDs`);

    // Check if we found all provisions
    const foundIds = new Set(result.rows.map((r: any) => r.id));
    const missingIds = ids.filter(id => !foundIds.has(id));

    if (missingIds.length > 0) {
      console.warn(`[Provisions By IDs API] Missing provisions for IDs:`, missingIds);
    }

    const processingTime = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      provisions: result.rows,
      metadata: {
        requested_count: ids.length,
        found_count: result.rows.length,
        missing_ids: missingIds.length > 0 ? missingIds : undefined,
        processingTimeMs: processingTime,
        timestamp: new Date().toISOString()
      }
    });

  } catch (error) {
    console.error('[Provisions By IDs API] Error:', error);

    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
      processingTimeMs: Date.now() - startTime
    }, { status: 500 });
  }
}
