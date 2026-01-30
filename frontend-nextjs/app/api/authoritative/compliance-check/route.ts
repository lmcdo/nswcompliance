import { NextRequest, NextResponse } from 'next/server';
import { ComplianceCheckSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate request using ComplianceCheckSchema
    const validation = validateRequest(ComplianceCheckSchema, {
      address: body.address || 'N/A',
      zone: body.zone_code,
      developmentType: body.development_type || 'other',
    });

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

    const { property_id, zone_code, development_type, include_development_permissions, basix_provisions, special_provisions } = body;

    console.log(`[Enhanced API] Compliance request: zone=${zone_code}, dev_type=${development_type}, property_id=${property_id}`);

    // Call the FastAPI compliance server
    const complianceRequest = {
      zone_code,
      property_id,
      development_type,
      include_development_permissions,
      climate_zone: basix_provisions?.climate_zone,
      water_zone: basix_provisions?.water_zone,
      special_provisions
    };

    console.log('[Enhanced API] Calling FastAPI server at http://localhost:8000/compliance');
    console.log('[Enhanced API] Request payload:', JSON.stringify(complianceRequest));

    const response = await fetch('http://localhost:8000/compliance', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(complianceRequest)
    });

    console.log(`[Enhanced API] FastAPI response status: ${response.status}`);

    if (!response.ok) {
      throw new Error(`FastAPI server responded with ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error || 'FastAPI server returned error');
    }

    console.log('[Enhanced API] Successfully received data from FastAPI server');
    return NextResponse.json(result.data);

  } catch (error) {
    console.error('Authoritative compliance check error:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    endpoint: 'POST /api/authoritative/compliance-check',
    description: 'Enhanced Authoritative Compliance API via FastAPI',
    version: 'fastapi_v1',
    required_fields: ['zone_code'],
    optional_fields: ['property_id', 'development_type', 'include_development_permissions', 'basix_provisions', 'special_provisions'],
    backend: 'FastAPI server at http://localhost:8000'
  });
}