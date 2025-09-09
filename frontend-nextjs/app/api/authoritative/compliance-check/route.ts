import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Validate required fields
    const { property_id, zone_code, development_type } = body;
    
    if (!zone_code) {
      return NextResponse.json(
        { error: 'zone_code is required' }, 
        { status: 400 }
      );
    }

    console.log(`[PRP-8B API] Hierarchy resolution request: zone=${zone_code}, dev_type=${development_type}, property_id=${property_id}`);

    // Call HierarchyResolver via Python subprocess
    const result = await callHierarchyResolver(zone_code, property_id, development_type);

    return NextResponse.json(result);

  } catch (error) {
    console.error('Authoritative compliance check error:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

async function callHierarchyResolver(
  zoneCode: string, 
  propertyId?: number, 
  developmentType?: string
): Promise<any> {
  return new Promise((resolve, reject) => {
    // Path to Python CLI script
    const scriptPath = path.join(process.cwd(), '..', 'services', 'hierarchy_resolver_cli.py');
    const pythonPath = path.join(process.cwd(), '..', 'venv_linux', 'Scripts', 'python.exe');
    
    // Prepare arguments
    const args = [scriptPath, '--zone', zoneCode, '--format', 'json'];
    
    if (propertyId) {
      args.push('--property-id', propertyId.toString());
    }
    
    if (developmentType) {
      args.push('--development-type', developmentType);
    }

    console.log(`[PRP-8B API] Calling: ${pythonPath} ${args.join(' ')}`);

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
          // The CLI outputs JSON directly, try to parse the entire stdout
          const trimmedOutput = stdout.trim();
          
          if (trimmedOutput.startsWith('{') && trimmedOutput.endsWith('}')) {
            const result = JSON.parse(trimmedOutput);
            resolve(result);
          } else {
            // Try to find JSON in the output
            const lines = stdout.split('\n');
            let jsonContent = '';
            let inJson = false;
            
            for (const line of lines) {
              if (line.trim().startsWith('{')) {
                inJson = true;
                jsonContent = line;
              } else if (inJson && line.trim().endsWith('}')) {
                jsonContent += '\n' + line;
                break;
              } else if (inJson) {
                jsonContent += '\n' + line;
              }
            }
            
            if (jsonContent) {
              const result = JSON.parse(jsonContent);
              resolve(result);
            } else {
              console.log('[PRP-8B API] Raw Python output:', stdout);
              console.log('[PRP-8B API] Python stderr:', stderr);
              reject(new Error('No valid JSON response from HierarchyResolver'));
            }
          }
        } catch (parseError) {
          console.error('[PRP-8B API] JSON parse error:', parseError);
          console.log('[PRP-8B API] Raw output:', stdout);
          console.log('[PRP-8B API] Python stderr:', stderr);
          reject(new Error('Failed to parse HierarchyResolver response'));
        }
      } else {
        console.error(`[PRP-8B API] Python process exited with code ${code}`);
        console.error('[PRP-8B API] stderr:', stderr);
        reject(new Error(`HierarchyResolver failed with code ${code}: ${stderr}`));
      }
    });

    pythonProcess.on('error', (error) => {
      console.error('[PRP-8B API] Python process error:', error);
      reject(new Error(`Failed to start HierarchyResolver: ${error.message}`));
    });
  });
}

export async function GET() {
  return NextResponse.json({
    endpoint: 'POST /api/authoritative/compliance-check',
    description: 'PRP-8B Authoritative Compliance API with hierarchy resolution',
    version: 'chunk3_v1',
    required_fields: ['zone_code'],
    optional_fields: ['property_id', 'development_type'],
    response_structure: {
      property: 'Property details',
      tier_1_provisions: 'Fully authoritative provisions',
      tier_2_provisions: 'High authority provisions', 
      tier_3_provisions: 'Moderate authority provisions',
      tier_4_provisions: 'Framework guidance',
      tier_5_provisions: 'Specialist required',
      primary_authorities: 'Authority resolution by measurement context',
      complexity_assessment: 'Complexity level',
      confidence_level: 'Overall confidence score',
      legal_disclaimer: 'Legal disclaimer text'
    }
  });
}