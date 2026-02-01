/**
 * Compliance Dashboard API Route
 * Serves comprehensive compliance data for dashboard display
 * Follows Universal Technical Implementation Specification - REAL DATA ONLY
 */

import { NextRequest, NextResponse } from 'next/server';
import { ComplianceDataClient, type ComplianceData } from '@/lib/database/compliance-client';
import { ComplianceCheckSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';


export const dynamic = 'force-dynamic';
export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;

    // Extract query parameters
    const zone = searchParams.get('zone');
    const heritage = searchParams.get('heritage') === 'true';
    const maxHeight = searchParams.get('maxHeight');
    const maxFsr = searchParams.get('maxFsr');
    const basixWater = searchParams.get('basixWater');
    const lga = searchParams.get('lga');

    // Validate required parameters
    if (!zone) {
      return NextResponse.json(
        {
          success: false,
          error: 'Zone parameter is required',
          code: 'MISSING_ZONE'
        },
        { status: 400 }
      );
    }

    // Build constraints object
    const constraints = {
      zone,
      maxHeight: maxHeight ? parseFloat(maxHeight) : undefined,
      maxFsr: maxFsr ? parseFloat(maxFsr) : undefined,
      basixWater,
      lga,
      heritage,
      floodProne: false, // Default values
      bushfireProne: false
    };

    // Get compliance data from real database
    const complianceClient = new ComplianceDataClient();
    const complianceData: ComplianceData = await complianceClient.getComplianceData(
      zone,
      heritage,
      constraints
    );

    // Format response according to API standards
    const response = {
      success: true,
      data: {
        compliance_data: complianceData,
        query_parameters: {
          zone,
          heritage,
          maxHeight,
          maxFsr,
          basixWater,
          lga
        },
        metadata: {
          total_constraints:
            complianceData.building_envelope.length +
            complianceData.environmental.length +
            complianceData.special_provisions.length,
          generated_at: new Date().toISOString(),
          data_source: 'postgresql_regulatory_provisions'
        }
      },
      timestamp: new Date().toISOString()
    };

    return NextResponse.json(response);

  } catch (error) {
    console.error('Compliance dashboard API error:', error);

    // Error handling per specification
    const errorResponse = {
      success: false,
      error: 'Failed to retrieve compliance data',
      code: 'COMPLIANCE_DATA_ERROR',
      details: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString()
    };

    return NextResponse.json(errorResponse, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate request body
    const validation = validateRequest(ComplianceCheckSchema, body);

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

    const { zone, developmentType } = validation.data;

    // Extract constraints from request body
    const constraints = {
      zone,
      maxHeight: body.maxHeight,
      maxFsr: body.maxFsr,
      basixWater: body.basixWater,
      lga: body.lga,
      heritage: body.heritage || false,
      floodProne: body.floodProne || false,
      bushfireProne: body.bushfireProne || false
    };

    // Get compliance data
    const complianceClient = new ComplianceDataClient();
    const complianceData: ComplianceData = await complianceClient.getComplianceData(
      zone,
      body.heritage || false,
      constraints
    );

    const response = {
      success: true,
      data: {
        compliance_data: complianceData,
        request_parameters: constraints,
        metadata: {
          total_constraints:
            complianceData.building_envelope.length +
            complianceData.environmental.length +
            complianceData.special_provisions.length,
          generated_at: new Date().toISOString(),
          data_source: 'postgresql_regulatory_provisions'
        }
      },
      timestamp: new Date().toISOString()
    };

    return NextResponse.json(response);

  } catch (error) {
    console.error('Compliance dashboard POST error:', error);

    const errorResponse = {
      success: false,
      error: 'Failed to process compliance request',
      code: 'COMPLIANCE_PROCESSING_ERROR',
      details: error instanceof Error ? error.message : 'Unknown error',
      timestamp: new Date().toISOString()
    };

    return NextResponse.json(errorResponse, { status: 500 });
  }
}