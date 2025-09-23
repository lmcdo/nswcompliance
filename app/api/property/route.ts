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