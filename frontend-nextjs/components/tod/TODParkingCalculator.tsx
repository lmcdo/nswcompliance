'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface TransportService {
 type: 'heavy_rail' | 'light_rail' | 'bus' | 'ferry';
 name: string;
 distance: number;
 frequency: 'high' | 'medium' | 'low';
}

interface ParkingCalculation {
 base_parking_requirement: number;
 reduction_factors: Array<{
 type: string;
 reduction_percentage: number;
 description: string;
 }>;
 final_parking_requirement: number;
 reduction_percentage: number;
 total_savings: number;
}

interface TODParkingCalculatorProps {
 developmentType: string;
 unitCount?: number;
 gfa?: number;
 transportServices?: TransportService[];
 zoneCode?: string;
 lga?: string;
 onCalculationComplete?: (calculation: ParkingCalculation) => void;
}

export default function TODParkingCalculator({
 developmentType,
 unitCount,
 gfa,
 transportServices = [],
 zoneCode,
 lga,
 onCalculationComplete
}: TODParkingCalculatorProps) {
 const [calculation, setCalculation] = useState<ParkingCalculation | null>(null);
 const [isCalculating, setIsCalculating] = useState(false);
 const [isFetchingRate, setIsFetchingRate] = useState(false);
 const [manualUnitCount, setManualUnitCount] = useState<number>(unitCount || 0);
 const [manualParkingRate, setManualParkingRate] = useState<number | null>(null);
 const [selectedTransport, setSelectedTransport] = useState<TransportService[]>([]);
 const [rateSource, setRateSource] = useState<string>('');
 const [sourcesUnavailable, setSourcesUnavailable] = useState<string[]>([]);

 // NO HARDCODED RATES - User must provide or fetch from regulations

 // Calculate parking reduction based on transport proximity
 const calculateParkingReduction = useCallback(() => {
 if (!developmentType || manualUnitCount === 0 || !manualParkingRate) return null;

 // Use user-provided rate, no assumptions
 const baseRequirement = Math.ceil(manualParkingRate * manualUnitCount);

 const reductionFactors = [];
 let totalReduction = 0;

 // Transport-based reductions
 const relevantTransport = selectedTransport.length > 0 ? selectedTransport : transportServices;

 relevantTransport.forEach(service => {
 let reductionPercent = 0;
 let description = '';

 if (service.type === 'heavy_rail') {
 if (service.distance <= 400) {
 reductionPercent = 0 // Set by council DCP;
 description = `Heavy rail within 400m (${service.name})`;
 } else if (service.distance <= 800) {
 reductionPercent = 0 // Set by council DCP;
 description = `Heavy rail within 800m (${service.name})`;
 }
 } else if (service.type === 'light_rail') {
 if (service.distance <= 400) {
 reductionPercent = 0 // Set by council DCP;
 description = `Light rail within 400m (${service.name})`;
 } else if (service.distance <= 600) {
 reductionPercent = 0 // Set by council DCP;
 description = `Light rail within 600m (${service.name})`;
 }
 } else if (service.type === 'bus') {
 if (service.frequency === 'high' && service.distance <= 400) {
 reductionPercent = 0 // Set by council DCP;
 description = `High frequency bus within 400m (${service.name})`;
 } else if (service.frequency === 'medium' && service.distance <= 400) {
 reductionPercent = 0 // Set by council DCP;
 description = `Medium frequency bus within 400m (${service.name})`;
 }
 }

 if (reductionPercent > 0) {
 reductionFactors.push({
 type: service.type,
 reduction_percentage: reductionPercent,
 description
 });
 totalReduction += reductionPercent;
 }
 });

 // Multiple transport bonus (max 50% total reduction)
 if (reductionFactors.length > 1) {
const bonus = Math.min(50 - totalReduction, 0); // Bonus must be set by council DCP
 if (bonus > 0) {
 reductionFactors.push({
 type: 'multiple_transport',
 reduction_percentage: bonus,
 description: 'Multiple transport options bonus'
 });
 totalReduction += bonus;
 }
 }

 // Cap at 50% maximum reduction
 totalReduction = Math.min(totalReduction, 50);

 const finalRequirement = Math.ceil(baseRequirement * (100 - totalReduction) / 100);
 const savings = baseRequirement - finalRequirement;

 return {
 base_parking_requirement: baseRequirement,
 reduction_factors: reductionFactors,
 final_parking_requirement: finalRequirement,
 reduction_percentage: totalReduction,
 total_savings: savings
 };
 }, [developmentType, manualUnitCount, manualParkingRate, transportServices, selectedTransport]);

 // Don't auto-calculate - wait for button press
 // Only clear old calculation when inputs change
 useEffect(() => {
 setCalculation(null);
 }, [manualUnitCount, manualParkingRate, transportServices, selectedTransport, developmentType]);

 // DO NOT auto-calculate - user must provide unit count
 useEffect(() => {
 if (unitCount) {
 setManualUnitCount(unitCount);
 }
 // NO ASSUMPTIONS - User must explicitly provide unit count
 }, [unitCount]);

 // Fetch parking rate from database
 const fetchParkingRate = async () => {
 if (!zoneCode || !developmentType) return;

 setIsFetchingRate(true);
 try {
 const params = new URLSearchParams({
 zone: zoneCode,
 development_type: developmentType,
 ...(lga && { lga })
 });

 const response = await fetch(`/api/tod/parking-rates?${params}`);
 const data = await response.json();

 // A source that failed to load is NOT the same as a source that had nothing.
 // The API reports the difference; surface it instead of absorbing it, otherwise
 // a partial lookup reads to the user as a complete one.
 setSourcesUnavailable(Array.isArray(data.degraded) ? data.degraded : []);

 if (data.found && data.rate) {
 setManualParkingRate(data.rate);
 setRateSource(data.source || 'Regulatory provisions database');
 } else if (data.unavailable) {
 setRateSource('Parking rates unavailable - the sources could not be read. This is not a finding that no rate applies.');
 } else {
 // No rate found - user must enter manually
 setRateSource(data.message || 'Rate not found in database - enter manually');
 }
 } catch (error) {
 console.error('Failed to fetch parking rate:', error);
 setRateSource('Failed to fetch rate - enter manually');
 setSourcesUnavailable(['The parking rate service could not be reached.']);
 } finally {
 setIsFetchingRate(false);
 }
 };

 if (!developmentType) {
 return (
 <Card className="bg-gray-50">
 <CardContent className="p-6">
 {sourcesUnavailable.length > 0 && (
 <div
 role="alert"
 className="mb-4 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
 >
 <strong>Some parking sources could not be read.</strong> The figures below may be
 incomplete. This is not a finding that no requirement applies.
 <ul className="mt-1 list-disc pl-5">
 {sourcesUnavailable.map((reason) => (
 <li key={reason}>{reason}</li>
 ))}
 </ul>
 </div>
 )}

 <p className="text-gray-500 text-center">
 Select a development type to calculate TOD parking requirements
 </p>
 </CardContent>
 </Card>
 );
 }

 return (
 <Card>
 <CardHeader>
 <CardTitle className="flex items-center gap-2">
 TOD Parking Calculator
 <span className="text-sm font-normal text-gray-500">
 Transit-Oriented Development
 </span>
 </CardTitle>
 </CardHeader>
 <CardContent className="space-y-6">
 {/* Warning about no assumptions */}
 <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
 <p className="text-sm text-amber-800">
 <strong>Manual Input Required:</strong> Enter exact values from council DCP or LEP.
 No default rates are assumed.
 </p>
 </div>

 {/* Unit Count Input */}
 <div>
 <label className="block text-sm font-medium text-gray-700 mb-2">
 Number of Units/Premises <span className="text-red-500">*</span>
 </label>
 <input
 type="number"
 value={manualUnitCount}
 onChange={(e) => {
 setManualUnitCount(parseInt(e.target.value) || 0);
 }}
 className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
 min="1"
 placeholder="Enter exact number of units"
 required
 />
 <p className="text-xs text-gray-500 mt-1">
 Enter the actual number of units in your development
 </p>
 </div>

 {/* Parking Rate Input */}
 <div>
 <label className="block text-sm font-medium text-gray-700 mb-2">
 Base Parking Rate (spaces per unit) <span className="text-red-500">*</span>
 </label>
 <div className="flex gap-2">
 <input
 type="number"
 step="0.1"
 value={manualParkingRate || ''}
 onChange={(e) => {
 const value = e.target.value.trim();
 if (value === '') {
 setManualParkingRate(null);
 } else {
 const parsed = parseFloat(value);
 setManualParkingRate(isNaN(parsed) ? null : parsed);
 }
 }}
 className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
 min="0"
 placeholder="e.g., 1.5 (from council DCP)"
 required
 />
 {zoneCode && (
 <Button
 onClick={fetchParkingRate}
 disabled={isFetchingRate}
 variant="outline"
 className="px-4 py-2"
 >
 {isFetchingRate ? 'Fetching...' : 'Fetch Rate'}
 </Button>
 )}
 </div>
 <p className="text-xs text-gray-500 mt-1">
 Check your council's DCP for {developmentType.replace(/_/g, ' ')} parking requirements
 {rateSource && <span className="block mt-1 text-green-600">Source: {rateSource}</span>}
 </p>
 </div>

 {/* Transport Services Display */}
 {transportServices.length > 0 && (
 <div>
 <h4 className="text-sm font-medium text-gray-700 mb-2">
 Nearby Transport Services
 </h4>
 <div className="space-y-2">
 {transportServices.map((service, index) => (
 <div key={index} className="flex items-center justify-between p-2 bg-blue-50 rounded">
 <div>
 <span className="font-medium capitalize">{service.type.replace('_', ' ')}</span>
 <span className="text-sm text-gray-600 ml-2">{service.name}</span>
 </div>
 <div className="text-sm">
 <span className="text-gray-500">{service.distance}m</span>
 <span className={`ml-2 px-2 py-1 rounded text-xs ${
 service.frequency === 'high' ? 'bg-green-100 text-green-800' :
 service.frequency === 'medium' ? 'bg-yellow-100 text-yellow-800' :
 'bg-gray-100 text-gray-800'
 }`}>
 {service.frequency} frequency
 </span>
 </div>
 </div>
 ))}
 </div>
 </div>
 )}


 {/* Calculate Button */}
 {manualUnitCount > 0 && manualParkingRate !== null && manualParkingRate > 0 && (
 <div className="flex justify-center">
 <button
 type="button"
 onClick={() => {
 const result = calculateParkingReduction();
 if (result) {
 setCalculation(result);
 onCalculationComplete?.(result);
 }
 }}
 style={{
 backgroundColor: '#2563eb',
 color: 'white',
 padding: '0.5rem 1.5rem',
 borderRadius: '0.5rem',
 fontWeight: '600',
 cursor: 'pointer',
 border: 'none',
 boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
 }}
 onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#1d4ed8'}
 onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#2563eb'}
 >
 Calculate Parking Requirements
 </button>
 </div>
 )}

 {/* Show message if missing inputs */}
 {(manualUnitCount <= 0 || !manualParkingRate || manualParkingRate <= 0) && (
 <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
 <p className="text-sm text-yellow-800">
 Enter both unit count (&gt;0) and parking rate (&gt;0) to calculate requirements
 </p>
 </div>
 )}

 {/* Calculation Results */}
 {calculation && (
 <div className="bg-green-50 border border-green-200 rounded-lg p-4">
 <h4 className="font-semibold text-green-800 mb-3">
 Parking Calculation Results
 </h4>

 <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
 <div className="text-center">
 <div className="text-2xl font-bold text-gray-900">
 {calculation.base_parking_requirement}
 </div>
 <div className="text-sm text-gray-600">Base Requirement</div>
 </div>
 <div className="text-center">
 <div className="text-2xl font-bold text-green-600">
 -{calculation.reduction_percentage}%
 </div>
 <div className="text-sm text-gray-600">TOD Reduction</div>
 </div>
 <div className="text-center">
 <div className="text-2xl font-bold text-blue-600">
 {calculation.final_parking_requirement}
 </div>
 <div className="text-sm text-gray-600">Final Requirement</div>
 </div>
 </div>

 {/* Reduction Factors */}
 {calculation.reduction_factors.length > 0 && (
 <div>
 <h5 className="font-medium text-gray-700 mb-2">Reduction Factors Applied:</h5>
 <ul className="space-y-1">
 {calculation.reduction_factors.map((factor, index) => (
 <li key={index} className="text-sm flex justify-between">
 <span>{factor.description}</span>
 <span className="font-medium text-green-600">-{factor.reduction_percentage}%</span>
 </li>
 ))}
 </ul>
 </div>
 )}

 <div className="mt-4 pt-3 border-t border-green-200">
 <div className="flex justify-between items-center">
 <span className="font-medium">Parking Spaces Saved:</span>
 <span className="text-lg font-bold text-green-600">
 {calculation.total_savings} spaces
 </span>
 </div>
 </div>
 </div>
 )}

 {/* No Reductions Message */}
 {calculation && calculation.reduction_factors.length === 0 && (
 <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
 <p className="text-yellow-800">
 <strong>No TOD parking reductions available</strong><br />
 This property does not meet the proximity requirements for transit-oriented development parking reductions.
 Standard parking rates apply.
 </p>
 </div>
 )}

 {/* Export Button */}
 {calculation && (
 <Button
 onClick={() => {
 // TODO: Implement PDF export functionality
 console.log('Export parking calculation:', calculation);
 }}
 className="w-full"
 variant="outline"
 >
 Export Parking Assessment Report
 </Button>
 )}
 </CardContent>
 </Card>
 );
}
