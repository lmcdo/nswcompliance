// app/api/property/lot-geometry/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { validateRequest, formatValidationErrors } from '@/lib/schemas';

// Schema for lot geometry query params
const LotGeometryQuerySchema = z.object({
  propId: z.string().min(1, 'Property ID is required'),
});

export async function GET(request: NextRequest) {
 const searchParams = request.nextUrl.searchParams;

 // Convert query params to object and validate
 const params = {
 propId: searchParams.get('propId'),
 };

 const validation = validateRequest(LotGeometryQuerySchema, params);

 if (!validation.success) {
 return NextResponse.json(
 {
 success: false,
 error: 'Invalid query parameters',
 details: formatValidationErrors(validation.details),
 },
 { status: 400 }
 );
 }

 const { propId } = validation.data;

 try {
 const url = `https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/lot?propId=${propId}`;
 console.log('[API] Fetching lot geometry for property:', propId);
 
 const response = await fetch(url);
 
 if (!response.ok) {
 throw new Error(`NSW API returned ${response.status}`);
 }
 
 const data = await response.json();
 
 if (!data || data.length === 0) {
 return NextResponse.json(
 { error: 'No lot geometry found for this property' },
 { status: 404 }
 );
 }
 
 // Return the first lot's geometry
 const lotData = data[0];
 console.log('[API] Lot geometry found:', lotData.attributes?.LotDescription);
 
 return NextResponse.json({
 success: true,
 geometry: lotData.geometry,
 lotDescription: lotData.attributes?.LotDescription || 'Unknown',
 cadId: lotData.attributes?.CADID || null
 });
 
 } catch (error) {
 console.error('[API] Error fetching lot geometry:', error);
 return NextResponse.json(
 { 
 error: error instanceof Error ? error.message : 'Failed to fetch lot geometry' 
 },
 { status: 500 }
 );
 }
}