// app/api/setbacks/calculate/route.ts - PRP-K3 Zone-Specific Calculation Engine
import { NextRequest, NextResponse } from 'next/server';
import { PreciseSetbackCalculator } from '@/lib/geometry/calculator';
import { DatabaseClient } from '@/lib/database/client';
import type { SetbackCalculationRequest, SetbackCalculationResponse } from '@/types/setback';
import { z } from 'zod';

// Request validation schema - PRP-K3 Zone-Specific (geometry optional)
const SetbackRequestSchema = z.object({
  property_id: z.number().int().positive(),
  lot_geometry: z.object({
    hasM: z.boolean(),
    hasZ: z.boolean(),
    rings: z.array(z.array(z.array(z.number()))),  // NSW format: rings[0][0] = [x,y] coordinate pair
    spatialReference: z.object({
      wkid: z.number(),
      latestWkid: z.number().optional().nullable(),
      vcsWkid: z.number().optional().nullable(),
      latestVcsWkid: z.number().optional().nullable(),
      wkt: z.string().optional().nullable()
    })
  }).optional(), // Geometry is optional for PRP-K3 zone-specific calculations
  property_zone: z.string().min(1).max(10),
  lot_area: z.number().positive().optional() // Optional - can estimate from zone defaults
});

export async function POST(request: NextRequest) {
  const startTime = Date.now();
  
  try {
    console.log('[API] PRP-K3: Zone-Specific Setback Calculation');

    // Parse and validate request body
    const body = await request.json();
    
    const validationResult = SetbackRequestSchema.safeParse(body);
    if (!validationResult.success) {
      console.error('[API] Validation failed:', validationResult.error);
      return NextResponse.json({
        success: false,
        error: 'Invalid request data: ' + validationResult.error.issues.map(i => i.message).join(', '),
        setback_results: [],
        buildable_area_analysis: {
          total_lot_area: 0,
          buildable_area: 0,
          buildable_percentage: 0,
          setback_area_lost: 0
        },
        precision_level: '',
        processing_method: '',
        processing_time_ms: Date.now() - startTime
      } as SetbackCalculationResponse, { status: 400 });
    }

    const validatedData = validationResult.data;
    console.log(`[API] Calculating setbacks for property ${validatedData.property_id} in zone ${validatedData.property_zone}`);

    // Use PRP-K3 Zone-Specific Calculation Engine
    const dbClient = new DatabaseClient();
    
    try {
      // Determine council from property location (simplified for demo)
      const council = 'Marrickville'; // In production, derive from geocoding
      
      // Get zone-specific setback rules from unified table
      const setbackRules = await dbClient.getZoneSetbackRules(
        validatedData.property_zone,
        council,
        0.75 // Minimum confidence threshold
      );
      
      console.log(`[API] PRP-K3: Found ${setbackRules.length} zone setback rules`);
      
      if (setbackRules.length > 0) {
        // Use provided lot_area or estimate based on zone defaults
        const estimatedLotArea = validatedData.lot_area || (validatedData.property_zone === 'R2' ? 500 : 400);
        
        return NextResponse.json({
          success: true,
          setback_results: setbackRules,
          buildable_area_analysis: {
            total_lot_area: estimatedLotArea,
            buildable_area: Math.max(0, estimatedLotArea * 0.6),
            buildable_percentage: 60,
            setback_area_lost: estimatedLotArea * 0.4
          },
          precision_level: 'legislative_clause',
          processing_method: 'PRP-K3 Zone-Specific Calculation Engine',
          processing_time_ms: Date.now() - startTime
        } as SetbackCalculationResponse);
      } else {
        // No rules found for this zone
        console.log(`[API] No rules found for zone ${validatedData.property_zone} in ${council}`);
        const estimatedLotArea = validatedData.lot_area || (validatedData.property_zone === 'R2' ? 500 : 400);
        
        return NextResponse.json({
          success: true,
          setback_results: [],
          buildable_area_analysis: {
            total_lot_area: estimatedLotArea,
            buildable_area: 0,
            buildable_percentage: 0,
            setback_area_lost: 0
          },
          precision_level: 'no_data',
          processing_method: 'PRP-K3 Zone-Specific Calculation Engine',
          processing_time_ms: Date.now() - startTime,
          warning: `No setback rules available for zone ${validatedData.property_zone} in ${council}`
        } as SetbackCalculationResponse);
      }
      
    } catch (dbError) {
      console.error('[API] PRP-K3 database error:', dbError);
      console.error('[API] Full error details:', JSON.stringify(dbError, null, 2));
      
      // Return fallback with clear error message
      return NextResponse.json({
        success: false,
        error: `Database error: ${dbError instanceof Error ? dbError.message : 'Unknown error'}`,
        setback_results: [],
        buildable_area_analysis: {
          total_lot_area: validatedData.lot_area,
          buildable_area: 0,
          buildable_percentage: 0,
          setback_area_lost: 0
        },
        precision_level: 'error',
        processing_method: 'PRP-K3 Zone-Specific Calculation Engine',
        processing_time_ms: Date.now() - startTime
      } as SetbackCalculationResponse, { status: 503 });
    }

  } catch (error) {
    const processingTime = Date.now() - startTime;
    console.error('[API] Setback calculation error:', error);
    
    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Calculation failed',
      setback_results: [],
      buildable_area_analysis: {
        total_lot_area: 0,
        buildable_area: 0,
        buildable_percentage: 0,
        setback_area_lost: 0
      },
      precision_level: 'error',
      processing_method: 'PRP-K3 Zone-Specific Calculation Engine',
      processing_time_ms: processingTime
    } as SetbackCalculationResponse, { status: 500 });
  }
}

// Health check endpoint
export async function GET(request: NextRequest) {
  try {
    const { DatabaseClient } = require('@/lib/database/client');
    const dbClient = new DatabaseClient();
    
    const testConnection = await dbClient.testConnection();
    
    return NextResponse.json({
      status: testConnection ? 'healthy' : 'unhealthy',
      endpoint: 'PRP-K3 Zone-Specific Setback Calculator',
      database_connection: testConnection,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    return NextResponse.json({
      status: 'unhealthy',
      error: error instanceof Error ? error.message : 'Unknown error',
      endpoint: 'PRP-K3 Zone-Specific Setback Calculator',
      timestamp: new Date().toISOString()
    }, { status: 500 });
  }
}