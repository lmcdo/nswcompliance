import { NextRequest, NextResponse } from 'next/server';
import { getPrecinctForAddress } from '@/lib/precinct-service';

/**
 * POST /api/precinct/match
 * Matches an address to its corresponding DCP precinct
 *
 * Request body:
 * {
 *   address: string,        // e.g., "22 Illawarra Road, Marrickville"
 *   lga: string,           // e.g., "Inner West" or "Marrickville"
 *   coordinates?: {        // Optional coordinates for spatial matching
 *     lat: number,
 *     lon: number
 *   }
 * }
 *
 * Response:
 * {
 *   success: true,
 *   precinct: {
 *     precinctNumber: string,  // e.g., "9_29"
 *     precinctName: string,    // e.g., "South Western Marrickville"
 *     documentId: string,
 *     lga: string
 *   } | null,
 *   hasPrecinct: boolean
 * }
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { address, lga, coordinates } = body;

    // Validate required fields
    if (!address || !lga) {
      return NextResponse.json({
        success: false,
        error: 'address and lga are required'
      }, { status: 400 });
    }

    console.log('[Precinct Match API] Matching address:', { address, lga, hasCoordinates: !!coordinates });

    // Get precinct for address - pass coordinates if available
    const precinct = await getPrecinctForAddress(address, lga, coordinates);

    if (precinct) {
      console.log('[Precinct Match API] Matched to precinct:', precinct.precinctNumber);
    } else {
      console.log('[Precinct Match API] No precinct match found');
    }

    return NextResponse.json({
      success: true,
      precinct: precinct,
      hasPrecinct: !!precinct
    });

  } catch (error) {
    console.error('[Precinct Match API] Error:', error);

    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
      precinct: null,
      hasPrecinct: false
    }, { status: 500 });
  }
}
