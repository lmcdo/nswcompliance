/**
 * Assessment API Gateway - Uses existing infrastructure
 * Consolidates multiple existing APIs for assessment workflow
 */

import { NextRequest, NextResponse } from 'next/server';

// Import existing services
import { NSWPlanningPortalService } from '@/lib/nsw-planning-portal';
import { PropertyDataService } from '@/lib/property-data';

export async function POST(request: NextRequest) {
 try {
 const body = await request.json();
 const { action, ...params } = body;

 switch (action) {
 case 'loadProperty':
 return await handleLoadProperty(params);

 case 'getCompliance':
 return await handleGetCompliance(params);

 case 'searchProvisions':
 return await handleSearchProvisions(params);

 default:
 return NextResponse.json(
 { error: 'Unknown action' },
 { status: 400 }
 );
 }
 } catch (error) {
 console.error('Assessment API error:', error);
 return NextResponse.json(
 { error: 'Internal server error' },
 { status: 500 }
 );
 }
}

async function handleLoadProperty({ address }: { address: string }) {
 // Use existing property API
 const propertyData = await PropertyDataService.getPropertyComplianceData(address);

 if (!propertyData) {
 return NextResponse.json(
 { error: 'Property not found' },
 { status: 404 }
 );
 }

 return NextResponse.json({
 success: true,
 data: {
 property: {
 propId: propertyData.propId,
 address: propertyData.address,
 zone: propertyData.constraints.zone,
 lga: propertyData.constraints.lga,
 area: propertyData.propertyArea,
 landValue: propertyData.landValue,
 heritage: propertyData.constraints.heritage
 },
 constraints: propertyData.constraints
 }
 });
}

async function handleGetCompliance({
 propertyId,
 zone,
 developmentType,
 assessmentDate
}: {
 propertyId: number;
 zone: string;
 developmentType: string;
 assessmentDate?: string;
}) {
 // Call real enhanced compliance endpoint - NO MOCK DATA
 try {
 const response = await fetch(`${process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000'}/api/compliance/enhanced`, {
 method: 'POST',
 headers: {
 'Content-Type': 'application/json',
 },
 body: JSON.stringify({
 propertyId,
 zone,
 developmentType,
 assessmentDate
 })
 });

 if (!response.ok) {
 throw new Error(`Enhanced compliance API failed: ${response.status}`);
 }

 const result = await response.json();
 return NextResponse.json(result);

 } catch (error) {
 console.error('Failed to call enhanced compliance API:', error);
 // Return error instead of falling back to mock data
 return NextResponse.json(
 { error: 'Compliance analysis failed', details: error instanceof Error ? error.message : 'Unknown error' },
 { status: 500 }
 );
 }
}

async function handleSearchProvisions({
 query,
 zone,
 developmentType
}: {
 query: string;
 zone?: string;
 developmentType?: string;
}) {
 // Call real provisions search endpoint - NO MOCK DATA
 try {
 const searchParams = new URLSearchParams({
 q: query
 });

 if (zone) searchParams.append('zones', zone);
 if (developmentType) searchParams.append('development_types', developmentType);

 const response = await fetch(`${process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000'}/api/provisions?${searchParams.toString()}`);

 if (!response.ok) {
 throw new Error(`Provisions search API failed: ${response.status}`);
 }

 const result = await response.json();
 return NextResponse.json(result);

 } catch (error) {
 console.error('Failed to call provisions search API:', error);
 // Return error instead of falling back to mock data
 return NextResponse.json(
 { error: 'Provisions search failed', details: error instanceof Error ? error.message : 'Unknown error' },
 { status: 500 }
 );
 }
}
