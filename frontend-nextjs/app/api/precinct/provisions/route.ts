import { NextRequest, NextResponse } from 'next/server';
import { getPrecinctProvisions } from '@/lib/precinct-service';
import { ProvisionLookupSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';

/**
 * POST /api/precinct/provisions
 * Returns all DCP provisions for a specific precinct
 *
 * Request body:
 * {
 *   precinctId: string,  // e.g., "29_" (note: underscore format from database)
 *   zone?: string,       // Optional zone filter
 *   limit?: number       // Optional limit (default 50)
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

    // Validate request data with Zod
    const validation = validateRequest(ProvisionLookupSchema, body);

    if (!validation.success) {
      return NextResponse.json(
        {
          success: false,
          error: 'Invalid request data',
          details: formatValidationErrors(validation.details),
        },
        { status: 400 }
      );
    }

    const { precinctId, zone, limit } = validation.data;

    // Extract additional fields for compatibility
    const lga = body.lga ?? null;
    // Inner West precincts are keyed by FORMER council in regulatory_provisions
    // (ashfield / leichhardt / marrickville), so the LGA alone cannot identify
    // them. Accept it from the caller when known; the lookup falls back to the
    // LGA slug when it is absent, which is what Ku-ring-gai needs.
    const formerCouncil = body.formerCouncil ?? body.former_council ?? null;

    // Require either precinctId or zone
    if (!precinctId && !zone) {
      return NextResponse.json({
        success: false,
        error: 'Either precinctId or zone is required'
      }, { status: 400 });
    }

    console.log('[Precinct Provisions API] Request:', { precinctId, zone, lga, limit });

    // Get provisions for precinct
    const provisions = await getPrecinctProvisions(precinctId || '', lga, formerCouncil);

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
