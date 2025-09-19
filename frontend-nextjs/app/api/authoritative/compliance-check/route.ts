import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate required fields
    const { property_id, zone_code, development_type, include_development_permissions, basix_provisions, special_provisions } = body;

    if (!zone_code) {
      return NextResponse.json(
        { error: 'zone_code is required' },
        { status: 400 }
      );
    }

    console.log(`[Enhanced API] Compliance request: zone=${zone_code}, dev_type=${development_type}, property_id=${property_id}, include_dev_permissions=${include_development_permissions}, basix=${!!basix_provisions}`);

    // Call Enhanced Compliance API (maintains backward compatibility)
    const result = await callEnhancedComplianceAPI(zone_code, property_id, development_type, include_development_permissions, basix_provisions, special_provisions);

    return NextResponse.json(result);

  } catch (error) {
    console.error('Authoritative compliance check error:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

async function callEnhancedComplianceAPI(
  zoneCode: string,
  propertyId?: number,
  developmentType?: string,
  includeDevelopmentPermissions?: boolean,
  basixProvisions?: any,
  specialProvisions?: any
): Promise<any> {
  return new Promise((resolve, reject) => {
    // Path to Enhanced Compliance API script
    const scriptPath = path.join(process.cwd(), '..', 'services', 'enhanced_compliance_api.py');
    const pythonPath = path.join(process.cwd(), '..', 'venv_linux', 'Scripts', 'python.exe');

    // Prepare arguments
    const args = [scriptPath, '--zone', zoneCode, '--format', 'json'];

    if (propertyId) {
      args.push('--property-id', propertyId.toString());
    }

    if (developmentType) {
      args.push('--development-type', developmentType);
    }

    if (includeDevelopmentPermissions) {
      args.push('--include-development-permissions');
    }

    if (basixProvisions?.climate_zone) {
      args.push('--climate-zone', basixProvisions.climate_zone);
    }

    if (basixProvisions?.water_zone) {
      args.push('--water-zone', basixProvisions.water_zone);
    }

    if (specialProvisions && Array.isArray(specialProvisions) && specialProvisions.length > 0) {
      args.push('--special-provisions', JSON.stringify(specialProvisions));
    }

    console.log(`[Enhanced API] Calling: ${pythonPath} ${args.join(' ')}`);

    const pythonProcess = spawn(pythonPath, args);

    let stdout = '';
    let stderr = '';

    pythonProcess.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    pythonProcess.on('close', (code) => {
      if (code === 0) {
        try {
          // The CLI outputs JSON directly - strip any warning lines
          let cleanOutput = stdout.trim();

          // Remove any warning lines that start with "Warning:"
          const lines = cleanOutput.split('\n');
          const jsonLines = lines.filter(line => !line.trim().startsWith('Warning:'));
          cleanOutput = jsonLines.join('\n').trim();

          // Find the first line that starts with { and parse from there
          const jsonStartIndex = cleanOutput.indexOf('{');
          if (jsonStartIndex > 0) {
            cleanOutput = cleanOutput.substring(jsonStartIndex);
          }

          const result = JSON.parse(cleanOutput);
          resolve(result);
        } catch (parseError) {
          console.error('[Enhanced API] JSON parse error:', parseError);
          console.log('[Enhanced API] Raw output:', stdout);
          reject(new Error('Failed to parse Enhanced Compliance API response'));
        }
      } else {
        console.error(`[Enhanced API] Python process exited with code ${code}`);
        console.error('[Enhanced API] stderr:', stderr);
        reject(new Error(`Enhanced Compliance API failed with code ${code}: ${stderr}`));
      }
    });

    pythonProcess.on('error', (error) => {
      console.error('[Enhanced API] Python process error:', error);
      reject(new Error(`Failed to start Enhanced Compliance API: ${error.message}`));
    });
  });
}

// Legacy function maintained for backward compatibility
async function callHierarchyResolver(
  zoneCode: string,
  propertyId?: number,
  developmentType?: string
): Promise<any> {
  // Redirect to enhanced API without development permissions for backward compatibility
  return callEnhancedComplianceAPI(zoneCode, propertyId, developmentType, false);
}

export async function GET() {
  return NextResponse.json({
    endpoint: 'POST /api/authoritative/compliance-check',
    description: 'Enhanced Authoritative Compliance API with optional development permissions (PRP-P5)',
    version: 'enhanced_v1',
    required_fields: ['zone_code'],
    optional_fields: [
      'property_id',
      'development_type',
      'include_development_permissions',
      'basix_provisions',
      'special_provisions'
    ],
    backward_compatibility: 'Fully maintained - existing requests work unchanged',
    new_features: {
      development_permissions: 'Optional zone development permissions when include_development_permissions=true',
      feasibility_check: 'Automatic feasibility check when development_type provided'
    },
    response_structure: {
      // Core hierarchy resolver response (maintained)
      property: 'Property details',
      tier_1_provisions: 'Fully authoritative provisions',
      tier_2_provisions: 'High authority provisions',
      tier_3_provisions: 'Moderate authority provisions',
      tier_4_provisions: 'Framework guidance',
      tier_5_provisions: 'Specialist required',
      primary_authorities: 'Authority resolution by measurement context',
      complexity_assessment: 'Complexity level',
      confidence_level: 'Overall confidence score',
      legal_disclaimer: 'Legal disclaimer text',

      // New optional fields (PRP-P5)
      development_permissions: {
        description: 'Included when include_development_permissions=true',
        structure: {
          permitted_without_consent: 'Development types that are permitted',
          permitted_with_consent: 'Development types requiring consent',
          prohibited: 'Development types that are prohibited',
          source_summary: 'Data source breakdown',
          total_combinations: 'Number of development type combinations',
          coverage_note: 'Coverage quality assessment'
        }
      },
      feasibility_check: {
        description: 'Included when development_type is provided',
        structure: {
          development_type: 'Requested development type',
          zone: 'Zone code',
          permission_status: 'permitted/consent/prohibited/unknown',
          confidence: 'high/medium/low',
          message: 'Human readable result',
          source_type: 'Data source for this result'
        }
      }
    },
    data_source: 'Consolidated dataset: 221 combinations across 22 zones',
    performance: 'Target response time: <2 seconds'
  });
}