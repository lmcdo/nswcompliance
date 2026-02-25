import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';
import { PropertyDataService } from '@/lib/property-data';
import { assessPatternBookEligibility, PropertyConstraints } from '@/lib/pattern-book-eligibility';

/**
 * Pattern Book CDC Eligibility API
 *
 * Checks if a property is eligible for the Pattern Book 10-day CDC pathway
 * BEFORE users spend $1,000-$25,000 on pattern designs.
 *
 * Housing Code Schedule 1 provisions (validated database extraction):
 * - 32 exclusion triggers (Schedule 1 automated extraction)
 * - 37 numeric standards (extractable quantifiable standards)
 * - 68 override rules (59 Schedule 1 + 9 other SEPPs)
 *
 * Source: SEPP (Exempt and Complying Development Codes) 2008 Schedule 1
 * Database: sepp_structured_requirements table (128 Schedule 1 provisions)
 * Extracted: 2026-02-26
 */

interface RequestBody {
  address?: string;
  propertyData?: any; // PropertyData from existing lookup
}

export async function POST(req: NextRequest) {
  try {
    const body: RequestBody = await req.json();
    const { address, propertyData } = body;

    // Validate input
    if (!address && !propertyData) {
      return NextResponse.json(
        {
          success: false,
          error: 'Either address or propertyData is required'
        },
        { status: 400 }
      );
    }

    // Get property data if not provided
    let property = propertyData;
    if (!property && address) {
      console.log(`[Pattern Book API] Fetching property data for: ${address}`);
      property = await PropertyDataService.getPropertyComplianceData(address);
    }

    if (!property) {
      return NextResponse.json(
        {
          success: false,
          error: 'Failed to fetch property data'
        },
        { status: 404 }
      );
    }

    console.log(`[Pattern Book API] Assessing eligibility for: ${property.address}`);

    // Build constraints object from property data
    const constraints: PropertyConstraints = {
      heritage: property.heritage,
      environmental: property.environmental,
      zone: property.constraints?.zone,
      lga: property.constraints?.lga,
      planningLayers: property.planningLayers,
      anefData: property.anefData
    };

    // Get lot dimensions
    const lotDimensions = property.lotDimensions || null;

    // Get database pool
    const pool = getPool();

    // Assess Pattern Book eligibility
    const eligibility = await assessPatternBookEligibility(
      constraints,
      lotDimensions,
      pool
    );

    console.log(`[Pattern Book API] Result: ${eligibility.status} - ${eligibility.pathway}`);

    return NextResponse.json({
      success: true,
      data: {
        address: property.address,
        eligibility,
        metadata: {
          timestamp: new Date().toISOString(),
          confidence: eligibility.confidence,
          dataSource: 'NSW Planning Portal + PlotDetect SEPP Extraction'
        }
      }
    });

  } catch (error) {
    console.error('[Pattern Book API] Error:', error);

    return NextResponse.json(
      {
        success: false,
        error: 'Failed to assess Pattern Book eligibility',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}

/**
 * GET endpoint for simple address-based lookup
 */
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const address = searchParams.get('address');

  if (!address) {
    return NextResponse.json(
      {
        success: false,
        error: 'Address parameter is required',
        example: '/api/pathway/pattern-book-eligibility?address=3 Wilkinson Ln, Telopea NSW 2117'
      },
      { status: 400 }
    );
  }

  // Reuse POST logic
  return POST(
    new NextRequest(req.url, {
      method: 'POST',
      body: JSON.stringify({ address })
    })
  );
}
