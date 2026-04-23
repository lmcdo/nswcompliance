// app/api/property/[address]/route.ts
import { NextRequest, NextResponse } from 'next/server';
import type { PropertyIntelligenceResponse, PropertyData, LotGeometry, CornerLotInfo } from '@/types/property';
import { calculateLotDimensions, type LotDimensions } from '@/lib/geometry/lot-dimensions';
import { detectCornerLot } from '@/lib/geometry/corner-lot-detection';
import { PropertySearchSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';


export const dynamic = 'force-dynamic';
// NSW Planning API base URL
const NSW_API_BASE = process.env.NSW_PLANNING_API_BASE_URL || 'https://api.apps1.nsw.gov.au/planning';

interface NSWPropertyResponse {
 address: string;
 propId: number;
 GURASID: number;
}

interface NSWLotResponse {
 geometry: LotGeometry;
 attributes: {
 CADID: number;
 LotDescription: string;
 };
}

export async function GET(
 request: NextRequest,
 { params }: { params: { address: string } }
) {
 const startTime = Date.now();
 const address = decodeURIComponent(params.address);

 // Validate address from URL parameter
 const validation = validateRequest(PropertySearchSchema, { address });

 if (!validation.success) {
 return NextResponse.json(
 {
 success: false,
 property: null,
 lotGeometry: null,
 error: 'Invalid address',
 details: formatValidationErrors(validation.details),
 } as PropertyIntelligenceResponse,
 { status: 400 }
 );
 }

 // Get optional coordinates from query params
 const searchParams = request.nextUrl.searchParams;
 const lat = searchParams.get('lat') ? parseFloat(searchParams.get('lat')!) : undefined;
 const lng = searchParams.get('lng') ? parseFloat(searchParams.get('lng')!) : undefined;

 try {
 console.log(`[API] Property lookup for: ${address}`);

 // Step 1: Get property ID from NSW Planning API (with fallback handling)
 let propertyResponse;
 let apiAvailable = true;
 
 try {
 propertyResponse = await fetch(
 `${NSW_API_BASE}/viewersf/V1/ePlanningApi/address?a=${encodeURIComponent(address)}&noOfRecords=1`,
 {
 headers: {
 'Origin': 'https://www.planningportal.nsw.gov.au',
 'Referer': 'https://www.planningportal.nsw.gov.au/'
 },
 }
 );

 if (!propertyResponse.ok) {
 console.warn(`[API] NSW Planning API returned ${propertyResponse.status}, falling back to manual input`);
 apiAvailable = false;
 }
 } catch (apiError) {
 console.warn(`[API] NSW Planning API connection failed, falling back to manual input:`, apiError);
 apiAvailable = false;
 }

 // Handle API unavailable case
 if (!apiAvailable) {
 console.log(`[API] NSW Planning API unavailable, returning fallback response for manual zone input`);
 
 const fallbackProperty: PropertyData = {
 address: address,
 prop_id: Math.floor(Math.random() * 1000000), // Generate temporary ID for setback calculation
 gurasid: 0,
 zone: null, // User will need to select zone manually
 height_limit: null,
 fsr_limit: null,
 coordinates: lat && lng ? { lat, lng } : undefined,
 api_status: 'unavailable'
 };

 const response: PropertyIntelligenceResponse = {
 success: true,
 property: fallbackProperty,
 lotGeometry: null,
 warning: 'NSW Planning API is currently unavailable. Please select zone manually to calculate setbacks.',
 processing_time_ms: Date.now() - startTime
 };

 return NextResponse.json(response);
 }

 const propertyData: NSWPropertyResponse[] = await propertyResponse!.json();
 
 if (!propertyData || propertyData.length === 0) {
 return NextResponse.json({
 success: false,
 property: null,
 lotGeometry: null,
 error: `No property found for address: ${address}`
 } as PropertyIntelligenceResponse);
 }

 const property = propertyData[0];
 console.log(`[API] Found property ID: ${property.propId}`);

 // Step 2: Get lot geometry
 let lotGeometry: LotGeometry | null = null;
 let lot_description: string | null = null;

 try {
 const lotResponse = await fetch(
 `${NSW_API_BASE}/viewersf/V1/ePlanningApi/lot?propId=${property.propId}`,
 {
 headers: {
 'Origin': 'https://www.planningportal.nsw.gov.au',
 'Referer': 'https://www.planningportal.nsw.gov.au/'
 }
 }
 );

 if (lotResponse.ok) {
 const lotData: NSWLotResponse[] = await lotResponse.json();
 if (lotData && lotData.length > 0) {
 lotGeometry = lotData[0].geometry;
 lot_description = lotData[0].attributes?.LotDescription ?? null;
 console.log(`[API] Retrieved lot geometry with ${lotGeometry.rings[0]?.length || 0} coordinate points. Lot: ${lot_description ?? 'unknown'}`);
 }
 }
 } catch (error) {
 console.warn(`[API] Failed to get lot geometry: ${error}`);
 // Continue without geometry - not critical for basic property info
 }

 // Step 3: Get planning controls using layerintersect endpoint (zone, height, FSR)
 let planningData: PropertyData | null = null;
 
 try {
 const planningResponse = await fetch(
 `${NSW_API_BASE}/viewersf/V1/ePlanningApi/layerintersect?type=property&id=${property.propId}&layers=epi`,
 {
 headers: {
 'Origin': 'https://www.planningportal.nsw.gov.au',
 'Referer': 'https://www.planningportal.nsw.gov.au/'
 }
 }
 );

 if (planningResponse.ok) {
 const planningControls = await planningResponse.json();
 
 // Parse planning controls
 planningData = {
 address: property.address,
 prop_id: property.propId,
 gurasid: property.GURASID,
 zone: extractControlValue(planningControls, 'Land Zoning'),
 height_limit: parseFloat(extractControlValue(planningControls, 'Height of Buildings') || '0') || null,
 height_units: 'm',
 fsr_limit: parseFloat(extractControlValue(planningControls, 'Floor Space Ratio') || '0') || null,
 heritage_status: extractControlValue(planningControls, 'Heritage') || undefined,
 heritage_overlays: extractHeritageOverlays(planningControls),
 lga_name: extractControlValue(planningControls, 'Local Government Area') || undefined,
 applicable_lep: extractControlValue(planningControls, 'Environmental Planning Instrument') || undefined,
 coordinates: lat && lng ? { lat, lng } : undefined
 };

 console.log(`[API] Extracted planning data: Zone=${planningData?.zone || 'N/A'}, Height=${planningData?.height_limit || 'N/A'}m, FSR=${planningData?.fsr_limit || 'N/A'}`);
 }
 } catch (error) {
 console.warn(`[API] Failed to get planning controls: ${error}`);
 }

 // Fallback if planning data extraction failed
 if (!planningData) {
 planningData = {
 address: property.address,
 prop_id: property.propId,
 gurasid: property.GURASID,
 zone: null,
 height_limit: null,
 fsr_limit: null,
 coordinates: lat && lng ? { lat, lng } : undefined
 };
 }

 const processingTime = Date.now() - startTime;
 console.log(`[API] Property analysis completed in ${processingTime}ms`);

 // Calculate lot dimensions from geometry
 let lotDimensions: LotDimensions | null = null;
 if (lotGeometry) {
   lotDimensions = calculateLotDimensions(lotGeometry);
   if (lotDimensions) {
     console.log(`[API] Calculated lot dimensions: frontage=${lotDimensions.frontage}m, depth=${lotDimensions.depth}m, area=${lotDimensions.area}m²`);
   }
 }

 // Detect corner lot from adjacent road parcels
 let cornerLot: CornerLotInfo | null = null;
 if (lotGeometry) {
   cornerLot = await detectCornerLot(lotGeometry);
   if (cornerLot.confidence > 0) {
     console.log(`[API] Corner lot detection: isCornerLot=${cornerLot.isCornerLot}, roads=[${cornerLot.adjacentRoads.join(', ')}]`);
   } else if (cornerLot.error) {
     console.warn(`[API] Corner lot detection failed: ${cornerLot.error}`);
   }
 }

 const response: PropertyIntelligenceResponse = {
 success: true,
 property: planningData,
 lotGeometry: lotGeometry,
 lot_description: lot_description,
 lotDimensions: lotDimensions || undefined,
 cornerLot: cornerLot || undefined,
 processing_time_ms: processingTime
 };

 return NextResponse.json(response);

 } catch (error) {
 const processingTime = Date.now() - startTime;
 console.error(`[API] Property analysis failed:`, error);
 
 const response: PropertyIntelligenceResponse = {
 success: false,
 property: null,
 lotGeometry: null,
 error: error instanceof Error ? error.message : 'Unknown error occurred',
 processing_time_ms: processingTime
 };

 return NextResponse.json(response, { status: 500 });
 }
}

// Helper functions for layerintersect API response
function extractControlValue(controls: any[], controlName: string): string | null {
 // The layerintersect returns an array of layers with results
 const layer = controls.find((c: any) => 
 c.layerName?.includes(controlName)
 );
 
 if (!layer || !layer.results || layer.results.length === 0) {
 return null;
 }
 
 // Extract based on layer type
 if (controlName === 'Land Zoning') {
 const result = layer.results[0];
 return result.Zone || null;
 } else if (controlName === 'Height of Buildings') {
 const result = layer.results[0];
 return result['Maximum Building Height'] || null;
 } else if (controlName === 'Floor Space Ratio') {
 // FSR can be in any of the results, find the one with Floor Space Ratio field
 for (const result of layer.results) {
 if (result['Floor Space Ratio']) {
 return result['Floor Space Ratio'];
 }
 }
 return null;
 }
 
 return null;
}

function extractHeritageOverlays(controls: any[]): string[] {
 const heritageLayer = controls.find((c: any) => 
 c.layerName?.toLowerCase().includes('heritage')
 );
 
 if (!heritageLayer || !heritageLayer.results) {
 return [];
 }
 
 return heritageLayer.results.map((r: any) => r.title || r['Heritage Item']).filter(Boolean);
}