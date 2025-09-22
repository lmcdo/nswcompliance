/**
 * Enhanced Compliance API
 * Calls the real Python compliance engine - NO MOCK DATA
 */

import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const {
      propertyId,
      zone,
      zoneCode,
      developmentType,
      assessmentDate,
      includeRecommendations = true,
      includeCitations = true,
      detailedAnalysis = true
    } = body;

    // Handle both zone and zoneCode for compatibility
    const zoneValue = zone || zoneCode;

    // Validate required fields
    if (!zoneValue || !developmentType) {
      return NextResponse.json(
        { error: 'Missing required fields: zone, developmentType' },
        { status: 400 }
      );
    }

    console.log(`[Enhanced Compliance] Property: ${propertyId}, Zone: ${zoneValue}, Type: ${developmentType}`);

    // Call the real Python compliance engine
    const result = await callRealComplianceEngine(zoneValue, propertyId, developmentType);

    return NextResponse.json({
      success: true,
      data: result
    });

  } catch (error) {
    console.error('Enhanced compliance analysis error:', error);
    return NextResponse.json(
      { error: 'Internal server error', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

async function callRealComplianceEngine(
  zoneCode: string,
  propertyId?: number,
  developmentType?: string
): Promise<any> {
  return new Promise((resolve, reject) => {
    // Path to real Enhanced Compliance API script
    const scriptPath = path.join(process.cwd(), '..', 'services', 'enhanced_compliance_api.py');
    const pythonPath = path.join(process.cwd(), '..', 'venv_linux', 'Scripts', 'python.exe');

    // Prepare arguments for real compliance engine
    const args = [scriptPath, '--zone', zoneCode, '--format', 'json'];

    if (propertyId) {
      args.push('--property-id', propertyId.toString());
    }

    if (developmentType) {
      args.push('--development-type', developmentType);
      args.push('--include-development-permissions');
    }

    console.log(`Calling real compliance engine: ${pythonPath} ${args.join(' ')}`);

    const python = spawn(pythonPath, args);

    let stdout = '';
    let stderr = '';

    python.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    python.on('close', (code) => {
      if (code === 0) {
        try {
          const result = JSON.parse(stdout);
          resolve(result);
        } catch (parseError) {
          console.error('Failed to parse Python response:', stdout);
          reject(new Error(`Failed to parse response: ${parseError}`));
        }
      } else {
        console.error('Python script error:', stderr);
        reject(new Error(`Python script failed with code ${code}: ${stderr}`));
      }
    });

    python.on('error', (error) => {
      console.error('Failed to start Python script:', error);
      reject(new Error(`Failed to start compliance engine: ${error.message}`));
    });
  });
}