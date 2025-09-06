import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { determineFormerCouncilAreaEnhanced, Polygon } from '../../../../lib/spatial/geometry-utils';

/**
 * API route for retrieving setback rules for a property
 * 
 * This route returns setback rules extracted from regulatory documents
 * using the NSW Development Compliance MVP processing pipeline
 */
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const address = searchParams.get('address');
  const geometryParam = searchParams.get('geometry');
  
  if (!address) {
    return NextResponse.json(
      { error: 'Address parameter required' },
      { status: 400 }
    );
  }
  
  try {
    // Parse geometry data if provided
    let geometry: Polygon | undefined;
    if (geometryParam) {
      try {
        geometry = JSON.parse(geometryParam);
      } catch (e) {
        console.warn('Failed to parse geometry parameter:', e);
      }
    }
    
    // Determine which former council area the property is in
    // Uses spatial geometry first, falls back to address parsing
    const formerCouncilArea = determineFormerCouncilAreaEnhanced(geometry, address);
    
    if (!formerCouncilArea) {
      return NextResponse.json(
        { 
          error: 'Address does not appear to be in Inner West LGA or former council area could not be determined',
          formerCouncilArea: null,
          setbacks: null
        },
        { status: 404 }
      );
    }
    
    // Read pre-processed setback data from our processing pipeline
    const dataPath = path.join(process.cwd(), 'public', 'regulatory-data', 'inner-west-setbacks.json');
    
    if (!fs.existsSync(dataPath)) {
      return NextResponse.json(
        { 
          error: 'Setback data not available. Please run the processing pipeline first.',
          formerCouncilArea,
          setbacks: null
        },
        { status: 500 }
      );
    }
    
    const rawData = fs.readFileSync(dataPath, 'utf8');
    const setbackData = JSON.parse(rawData);
    
    // Get setback rules for the determined council area
    const areaData = setbackData.areas[formerCouncilArea];
    
    if (!areaData) {
      return NextResponse.json(
        {
          error: `No setback data available for ${formerCouncilArea}`,
          formerCouncilArea,
          setbacks: {
            rear: null,
            side: null,
            front: null
          }
        },
        { status: 404 }
      );
    }
    
    // Return setback rules for the specific former council area
    return NextResponse.json({
      setbacks: areaData.setbacks,
      formerCouncilArea,
      determinationMethod: geometry ? 'spatial' : 'address',
      success: true
    });
  } catch (error) {
    console.error('Setback data fetch failed:', error);
    return NextResponse.json(
      { error: 'Failed to retrieve setback rules' },
      { status: 500 }
    );
  }
}

// Legacy function kept for reference - now handled by geometry-utils.ts