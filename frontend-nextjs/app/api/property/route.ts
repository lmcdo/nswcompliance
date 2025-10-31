import { NextRequest, NextResponse } from 'next/server';
import { PropertyDataService } from '../../../lib/property-data';

/**
 * General NSW Property Data API Endpoint
 * 
 * Returns comprehensive property data for any NSW property address
 * Fixed to use real data instead of N/A values
 */
export async function GET(req: NextRequest) {
 const { searchParams } = new URL(req.url);
 const address = searchParams.get('address');
 
 if (!address) {
 return NextResponse.json(
 { 
 error: 'Address parameter required',
 example: '/api/property?address=3 Wilkinson Ln, Telopea NSW 2117'
 },
 { status: 400 }
 );
 }
 
 try {
 // Get comprehensive property data
 const propertyData = await PropertyDataService.getPropertyComplianceData(address);

 // Transform Web Mercator geometry (EPSG:3857) to WGS84 coordinates (EPSG:4326)
 // ComplianceDashboard needs coordinates for geographic neighbourhood detection
 if (propertyData.geometry && !propertyData.coordinates) {
 const { x, y } = propertyData.geometry;

 // Web Mercator to WGS84 transformation
 const lon = (x / 20037508.34) * 180;
 const lat = (Math.atan(Math.exp((y / 20037508.34) * Math.PI)) * 360 / Math.PI) - 90;

 propertyData.coordinates = { lat, lon };

 console.log(`[Property API] Transformed coordinates: Web Mercator (${x.toFixed(2)}, ${y.toFixed(2)}) → WGS84 (${lat.toFixed(6)}, ${lon.toFixed(6)})`);
 }

 return NextResponse.json({
 success: true,
 data: propertyData,
 metadata: {
 timestamp: new Date().toISOString(),
 source: 'NSW Planning Portal',
 api_version: 'current'
 }
 });
 
 } catch (error) {
 console.error('Property data fetch failed:', error);
 
 return NextResponse.json(
 { 
 error: 'Failed to retrieve property data',
 details: error instanceof Error ? error.message : 'Unknown error'
 },
 { status: 500 }
 );
 }
}