import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { property_id, zone_code, development_type, include_development_permissions, basix_provisions, special_provisions } = body;

    if (!zone_code) {
      return NextResponse.json(
        { error: 'zone_code is required' },
        { status: 400 }
      );
    }

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