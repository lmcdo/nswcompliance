import { NextRequest, NextResponse } from 'next/server';
import { EnhancedPropertyDataService } from '../../../../lib/v1/enhanced-property-data';

/**
 * API v1 - Enhanced Property Data Endpoint
 * 
 * Comprehensive property information endpoint that returns complete
 * property data with all planning constraints, environmental overlays,
 * and compliance information - no more N/A values for available data
 */
export async function GET(req: NextRequest) {
 const { searchParams } = new URL(req.url);
 const address = searchParams.get('address');
 
 if (!address) {
 return NextResponse.json(
 { 
 error: 'Address parameter required',
 example: '/api/v1/property?address=3 Wilkinson Ln, Telopea NSW 2117'
 },
 { status: 400 }
 );
 }
 
 try {
 // Get comprehensive property data with all available information
 const propertyData = await EnhancedPropertyDataService.getComprehensivePropertyData(address);
 
 return NextResponse.json({
 version: '1.0',
 success: true,
 data: propertyData,
 metadata: {
 timestamp: new Date().toISOString(),
 source: 'NSW Planning Portal + Australian Government Data',
 api_version: '1.0'
 }
 });
 
 } catch (error) {
 console.error('V1 Property data fetch failed:', error);
 
 return NextResponse.json(
 { 
 error: 'Failed to retrieve comprehensive property data',
 details: error instanceof Error ? error.message : 'Unknown error',
 version: '1.0'
 },
 { status: 500 }
 );
 }
}