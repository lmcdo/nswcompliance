// app/api/compliance/live-check/route.ts
// PRP-Q1: Live Compliance Calculator API Endpoint
import { NextRequest, NextResponse } from 'next/server';

interface ComplianceCheckRequest {
  address: string;
  proposed_development: {
    gross_floor_area?: number;
    height?: number;
    building_area?: number;
  };
  coordinates?: {
    lat: number;
    lng: number;
  };
}

interface ComplianceResult {
  compliant: boolean;
  actual_value: number;
  limit_value: number;
  margin: number | null;
  units: string;
  confidence: number;
  data_source: string;
  calculation_time_ms: number;
}

interface ComplianceResponse {
  success: boolean;
  compliance?: {
    fsr_compliance?: ComplianceResult;
    height_compliance?: ComplianceResult;
    site_coverage_compliance?: ComplianceResult;
    overall_compliant: boolean;
    warnings: string[];
    total_calculation_time_ms: number;
  };
  error?: string;
  processing_time_ms: number;
}

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body: ComplianceCheckRequest = await request.json();
    const { address, proposed_development, coordinates } = body;

    // Validate required parameters
    if (!address || !proposed_development) {
      return NextResponse.json({
        success: false,
        error: 'Address and proposed development details required',
        processing_time_ms: Date.now() - startTime
      } as ComplianceResponse, { status: 400 });
    }

    // Validate proposed development has at least one parameter
    const hasValidDevelopment = (
      (proposed_development.gross_floor_area && proposed_development.gross_floor_area > 0) ||
      (proposed_development.height && proposed_development.height > 0) ||
      (proposed_development.building_area && proposed_development.building_area > 0)
    );

    if (!hasValidDevelopment) {
      return NextResponse.json({
        success: false,
        error: 'At least one valid development parameter required (gross_floor_area, height, or building_area)',
        processing_time_ms: Date.now() - startTime
      } as ComplianceResponse, { status: 400 });
    }

    // Call Python live compliance engine
    const pythonScript = `
import asyncio
import sys
import json
import os
sys.path.append('${process.cwd().replace(/\\/g, '/')}')
sys.path.append('${process.cwd().replace(/\\/g, '/')}/services')

async def main():
    try:
        from services.live_compliance_engine import LiveComplianceEngine

        engine = LiveComplianceEngine()

        address = "${address.replace(/"/g, '\\"')}"
        proposed_dev = ${JSON.stringify(proposed_development)}
        coords = ${coordinates ? JSON.stringify(coordinates) : 'None'}

        result = await engine.calculate_compliance(address, proposed_dev, coords)

        # Convert ComplianceAssessment to JSON-serializable dict
        response = {
            'overall_compliant': result.overall_compliant,
            'warnings': result.warnings,
            'total_calculation_time_ms': result.total_calculation_time_ms
        }

        # Add FSR compliance if available
        if result.fsr_compliance:
            response['fsr_compliance'] = {
                'compliant': result.fsr_compliance.compliant,
                'actual_value': result.fsr_compliance.actual_value,
                'limit_value': result.fsr_compliance.limit_value,
                'margin': result.fsr_compliance.margin,
                'units': result.fsr_compliance.units,
                'confidence': result.fsr_compliance.confidence,
                'data_source': result.fsr_compliance.data_source,
                'calculation_time_ms': result.fsr_compliance.calculation_time_ms
            }

        # Add height compliance if available
        if result.height_compliance:
            response['height_compliance'] = {
                'compliant': result.height_compliance.compliant,
                'actual_value': result.height_compliance.actual_value,
                'limit_value': result.height_compliance.limit_value,
                'margin': result.height_compliance.margin,
                'units': result.height_compliance.units,
                'confidence': result.height_compliance.confidence,
                'data_source': result.height_compliance.data_source,
                'calculation_time_ms': result.height_compliance.calculation_time_ms
            }

        # Add site coverage compliance if available
        if result.site_coverage_compliance:
            response['site_coverage_compliance'] = {
                'compliant': result.site_coverage_compliance.compliant,
                'actual_value': result.site_coverage_compliance.actual_value,
                'limit_value': result.site_coverage_compliance.limit_value,
                'margin': result.site_coverage_compliance.margin,
                'units': result.site_coverage_compliance.units,
                'confidence': result.site_coverage_compliance.confidence,
                'data_source': result.site_coverage_compliance.data_source,
                'calculation_time_ms': result.site_coverage_compliance.calculation_time_ms
            }

        print(json.dumps(response))

    except ImportError as e:
        print(json.dumps({
            'error': f'Live compliance engine not available: {str(e)}',
            'overall_compliant': False,
            'warnings': ['Live compliance engine not implemented'],
            'total_calculation_time_ms': 0
        }))
    except Exception as e:
        print(json.dumps({
            'error': f'Compliance calculation failed: {str(e)}',
            'overall_compliant': False,
            'warnings': [str(e)],
            'total_calculation_time_ms': 0
        }))

asyncio.run(main())
`;

    console.log('[API] Starting live compliance calculation...');

    const { spawn } = require('child_process');
    const python = spawn('python', ['-c', pythonScript]);

    let result = '';
    let error = '';

    python.stdout.on('data', (data: Buffer) => {
      result += data.toString();
    });

    python.stderr.on('data', (data: Buffer) => {
      error += data.toString();
    });

    const complianceResult = await new Promise<any>((resolve, reject) => {
      python.on('close', (code: number) => {
        if (code !== 0) {
          console.error('[API] Python process failed:', error);
          reject(new Error(`Python process failed with code ${code}: ${error}`));
        } else {
          try {
            const parsed = JSON.parse(result.trim());
            resolve(parsed);
          } catch (e) {
            console.error('[API] Failed to parse Python response:', result);
            reject(new Error(`Invalid JSON response: ${result.substring(0, 200)}...`));
          }
        }
      });

      // Set timeout for Python process
      setTimeout(() => {
        python.kill();
        reject(new Error('Live compliance calculation timed out'));
      }, 30000); // 30 second timeout
    });

    console.log('[API] Live compliance calculation completed');

    // Return successful response
    const response: ComplianceResponse = {
      success: true,
      compliance: complianceResult,
      processing_time_ms: Date.now() - startTime
    };

    return NextResponse.json(response);

  } catch (error) {
    console.error('[API] Live compliance check failed:', error);

    const response: ComplianceResponse = {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred',
      processing_time_ms: Date.now() - startTime
    };

    return NextResponse.json(response, { status: 500 });
  }
}

// GET endpoint for testing
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const address = searchParams.get('address');

  if (!address) {
    return NextResponse.json({
      success: false,
      error: 'Address parameter required for testing',
      example: '/api/compliance/live-check?address=45 Liverpool Street, Ashfield NSW 2131'
    });
  }

  // Test with sample development proposal
  const testProposal = {
    address,
    proposed_development: {
      gross_floor_area: 180,
      height: 8.5,
      building_area: 120
    }
  };

  // Convert to POST request internally
  const testResponse = await POST(new NextRequest(request.url, {
    method: 'POST',
    body: JSON.stringify(testProposal),
    headers: {
      'Content-Type': 'application/json'
    }
  }));

  return testResponse;
}