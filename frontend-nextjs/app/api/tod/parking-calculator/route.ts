import { NextRequest, NextResponse } from 'next/server';
import { TODSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';

interface ParkingCalculationRequest {
 development_type: string;
 unit_count: number;
 parking_rate: number; // Required - no defaults
 transport_proximity?: {
 type: string;
 distance: number;
 };
 rate_source?: string; // Where the rate came from (e.g., "Inner West DCP 2016 Table 2.1")
}

export async function POST(request: NextRequest) {
 try {
 const body: ParkingCalculationRequest = await request.json();

 // Validate request using TODSchema (use address as dummy value)
 const validation = validateRequest(TODSchema, {
 address: 'Parking Calculation',
 coordinates: body.transport_proximity ? { lat: 0, lng: 0 } : undefined,
 });

 if (!validation.success) {
 return NextResponse.json(
 {
 success: false,
 error: 'Invalid request data',
 details: formatValidationErrors(validation.details),
 },
 { status: 400 }
 );
 }

 // Validate required inputs
 if (!body.unit_count || !body.parking_rate) {
 return NextResponse.json(
 { error: 'Unit count and parking rate are required. No default rates are assumed.' },
 { status: 400 }
 );
 }

 // Use provided rate - NO ASSUMPTIONS
 const baseRequirement = Math.ceil(body.parking_rate * body.unit_count);

 const reductionFactors = [];
 let totalReduction = 0;

 // Calculate transport-based reductions
 if (body.transport_proximity) {
 const { type, distance } = body.transport_proximity;

 if (type === 'heavy_rail') {
 if (distance <= 400) {
 reductionFactors.push({
 type: 'heavy_rail',
 reduction_percentage: 30,
 description: `Heavy rail within 400m`
 });
 totalReduction += 30;
 } else if (distance <= 800) {
 reductionFactors.push({
 type: 'heavy_rail',
 reduction_percentage: 20,
 description: `Heavy rail within 800m`
 });
 totalReduction += 20;
 }
 } else if (type === 'light_rail') {
 if (distance <= 400) {
 reductionFactors.push({
 type: 'light_rail',
 reduction_percentage: 25,
 description: `Light rail within 400m`
 });
 totalReduction += 25;
 }
 } else if (type === 'bus') {
 if (distance <= 400) {
 reductionFactors.push({
 type: 'bus',
 reduction_percentage: 15,
 description: `High frequency bus within 400m`
 });
 totalReduction += 15;
 }
 }
 }

 // Cap at 50% maximum reduction
 totalReduction = Math.min(totalReduction, 50);

 const finalRequirement = Math.ceil(baseRequirement * (100 - totalReduction) / 100);

 return NextResponse.json({
 base_parking_requirement: baseRequirement,
 reduction_factors: reductionFactors,
 final_parking_requirement: finalRequirement,
 reduction_percentage: totalReduction,
 total_savings: baseRequirement - finalRequirement,
 development_type: body.development_type,
 unit_count: body.unit_count,
 parking_rate_used: body.parking_rate,
 rate_source: body.rate_source || 'User provided'
 });

 } catch (error) {
 console.error('Parking calculation error:', error);
 return NextResponse.json(
 { error: 'Failed to calculate parking requirements' },
 { status: 500 }
 );
 }
}

export async function GET() {
 return NextResponse.json({
 message: 'TOD Parking Calculator API',
 endpoints: {
 POST: 'Calculate parking requirements with TOD reductions'
 }
 });
}