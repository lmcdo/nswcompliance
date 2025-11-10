import { NextRequest, NextResponse } from 'next/server';
import { getPrecinctProvisions } from '@/lib/precinct-service';

/**
 * POST /api/precinct/provisions
 * Returns all DCP provisions for a specific precinct
 *
 * Request body:
 * {
 *   precinctId: string,  // e.g., "29_" (note: underscore format from database)
 *   lga: string          // e.g., "Inner West"
 * }
 *
 * Response:
 * {
 *   success: true,
 *   data: {
 *     provisions: [{
 *       id: number,
 *       precinct_id: string,
 *       precinct_name: string,
 *       provision_text: string,
 *       provision_type: string | null,
 *       ref_number: string,
 *       section_header: string,
 *       pdf_page: number,
 *       document_id: string,
 *       pdf_path: string
 *     }],
 *     count: number
 *   }
 * }
 */
export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body = await request.json();
    const { precinctId, lga } = body;

    // Validate required fields
    if (!precinctId || !lga) {
      return NextResponse.json({
        success: false,
        error: 'precinctId and lga are required'
      }, { status: 400 });
    }

    console.log('[Precinct Provisions API] Request:', { precinctId, lga });

    // Get provisions for precinct
    const provisions = await getPrecinctProvisions(precinctId, lga);

    const processingTime = Date.now() - startTime;

    console.log(`[Precinct Provisions API] Found ${provisions.length} provisions (${processingTime}ms)`);

    return NextResponse.json({
      success: true,
      data: {
        provisions,
        count: provisions.length
      },
      metadata: {
        precinctId,
        lga,
        processingTimeMs: processingTime,
        timestamp: new Date().toISOString()
      }
    });

  } catch (error) {
    console.error('[Precinct Provisions API] Error:', error);

    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
      data: {
        provisions: [],
        count: 0
      },
      processingTimeMs: Date.now() - startTime
    }, { status: 500 });
  }
}
