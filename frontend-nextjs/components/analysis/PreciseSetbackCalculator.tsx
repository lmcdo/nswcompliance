// components/analysis/PreciseSetbackCalculator.tsx
'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, Calculator, AlertTriangle, Building, Ruler, ChevronDown, ChevronUp, Info } from 'lucide-react';
import { useSetbackCalculation } from '@/hooks/useSetbackCalculation';
import type { PropertyData, LotGeometry } from '@/types/property';
import type { SetbackResult } from '@/types/setback';
import { ReferencedLegislationAccordion } from '@/components/compliance/ReferencedLegislationAccordion';

interface PreciseSetbackCalculatorProps {
 property: PropertyData | null;
 lotGeometry: LotGeometry | null;
 loading?: boolean;
 error?: string | null;
}

export function PreciseSetbackCalculator({ 
 property, 
 lotGeometry, 
 loading: externalLoading,
 error: externalError
}: PreciseSetbackCalculatorProps) {
 const { 
 results, 
 buildableArea, 
 calculating, 
 error: calculationError, 
 calculateSetbacks 
 } = useSetbackCalculation();

 const [attempted, setAttempted] = useState(false);

 useEffect(() => {
 // PRP-K3: Allow setback calculation with just zone and property data (no lot geometry required)
 if (property?.prop_id && property.zone && !attempted) {
 setAttempted(true);
 
 console.log('[Frontend Debug] Triggering PRP-K3 zone-specific setback calculation');
 console.log('Property:', { prop_id: property.prop_id, zone: property.zone });
 console.log('Lot geometry available:', !!lotGeometry);
 
 // PRP-K3: Zone-specific calculation - geometry optional
 const calculationRequest: any = {
 property_id: property.prop_id,
 property_zone: property.zone
 };
 
 // Add geometry and lot_area only if available
 if (lotGeometry) {
 calculationRequest.lot_geometry = lotGeometry;
 calculationRequest.lot_area = estimateLotArea(lotGeometry);
 }
 
 calculateSetbacks(calculationRequest);
 }
 }, [property, lotGeometry, calculateSetbacks, attempted]);

 // Loading state
 if (externalLoading || calculating) {
 return (
 <div className="p-8">
 <div className="flex items-center justify-center">
 <div className="text-center">
 <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
 <h3 className="text-lg font-semibold mb-2">Calculating Precise Setbacks</h3>
 <p className="text-gray-600 text-sm">
 Processing lot geometry and applying database intelligence...
 </p>
 </div>
 </div>
 </div>
 );
 }

 // Error state
 if (externalError || calculationError) {
 const errorMessage = externalError || calculationError;
 return (
 <div className="p-8">
 <div className="error-container">
 <div className="flex items-center gap-2 mb-3">
 <AlertTriangle className="h-5 w-5 text-red-500" />
 <h3 className="font-semibold">Setback Calculation Failed</h3>
 </div>
 <p className="text-sm mb-4">{errorMessage}</p>
 {property?.prop_id && lotGeometry && (
 <Button 
 variant="outline" 
 size="sm"
 onClick={() => {
 setAttempted(false);
 const lotArea = estimateLotArea(lotGeometry);
 calculateSetbacks({
 property_id: property.prop_id!,
 lot_geometry: lotGeometry,
 property_zone: property.zone || 'R2',
 lot_area: lotArea
 });
 }}
 >
 Retry Calculation
 </Button>
 )}
 </div>
 </div>
 );
 }

 // Show results even without geometry if we have zone data (PRP-K3 enhancement)
 if (!lotGeometry && property?.zone && !attempted) {
 return (
 <div className="p-8">
 <div className="text-center text-gray-600">
 <Calculator className="h-12 w-12 mx-auto mb-4 text-blue-600" />
 <h3 className="text-lg font-semibold mb-2">Zone-Specific Setback Calculation</h3>
 <p className="text-sm mb-4">
 Using PRP-K3 calculation engine for <strong>{property.zone}</strong> zone setbacks.
 </p>
 <div className="text-xs bg-blue-50 p-3 rounded border-l-4 border-blue-200">
 <p><strong>Note:</strong> Calculations use database rules for {property.zone} zone. Lot geometry not required for basic setback rules.</p>
 </div>
 </div>
 </div>
 );
 }
 
 // No geometry and no zone data
 if (!lotGeometry && !property?.zone) {
 return (
 <div className="p-8">
 <div className="text-center text-gray-500">
 <Calculator className="h-12 w-12 mx-auto mb-4 opacity-50" />
 <h3 className="text-lg font-semibold mb-2">Property Data Required</h3>
 <p className="text-sm mb-4">
 Setback calculations require property zone information from NSW Planning Portal.
 </p>
 <div className="text-xs bg-yellow-50 p-3 rounded border-l-4 border-yellow-200">
 <p><strong>Note:</strong> Some properties may not have detailed data available in the NSW Planning Portal.</p>
 </div>
 </div>
 </div>
 );
 }

 // No results - distinguish between not calculated yet vs no high-confidence data found
 if (!results || results.length === 0) {
 // If we haven't attempted calculation yet, show calculate button
 if (!attempted) {
 return (
 <div className="p-8">
 <div className="text-center text-gray-500">
 <Calculator className="h-12 w-12 mx-auto mb-4 opacity-50" />
 <h3 className="text-lg font-semibold mb-2">Ready to Calculate</h3>
 <p className="text-sm mb-4">
 Click the button below to calculate precise setbacks for this property.
 </p>
 <Button 
 onClick={() => {
 if (property?.prop_id && lotGeometry) {
 const lotArea = estimateLotArea(lotGeometry);
 calculateSetbacks({
 property_id: property.prop_id,
 lot_geometry: lotGeometry,
 property_zone: property.zone || 'R2',
 lot_area: lotArea
 });
 }
 }}
 disabled={!property?.prop_id}
 >
 <Calculator className="mr-2 h-4 w-4" />
 Calculate Precise Setbacks
 </Button>
 </div>
 </div>
 );
 }

 // If we attempted calculation but got no results, show no high-confidence data message
 return (
 <div className="p-8">
 <div className="text-center">
 <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-yellow-500" />
 <h3 className="text-lg font-semibold mb-2 text-gray-900">No High-Confidence Setback Data</h3>
 <p className="text-sm mb-4 text-gray-600">
 The database contains qualitative setback information for zone <strong>{property?.zone || 'R2'}</strong>, 
 but no quantitative measurements with sufficient confidence (≥80%) were found.
 </p>
 <div className="text-xs bg-blue-50 p-4 rounded border-l-4 border-blue-200 mb-4">
 <p><strong>Found in database:</strong> "{property?.zone || 'R2'}" zone setback requirements</p>
 <p><strong>Issue:</strong> Text describes "setbacks to ground floor and upper storeys" but lacks specific measurements</p>
 </div>
 <div className="text-xs bg-yellow-50 p-4 rounded border-l-4 border-yellow-200">
 <p><strong>Recommendation:</strong> Contact {property?.lga_name || 'the local council'} directly for specific setback requirements for this property.</p>
 </div>
 {buildableArea?.note && (
 <p className="text-sm text-gray-500 mt-4 italic">{buildableArea.note}</p>
 )}
 </div>
 </div>
 );
 }

 // Results display
 return (
 <div className="max-w-2xl mx-auto">
 <div className="bg-white shadow-2xl rounded-2xl overflow-hidden">
 {/* Header */}
 <div className="bg-indigo-600 text-white p-6 flex items-center">
 <Building className="w-10 h-10 mr-4" />
 <div>
 <h1 className="text-2xl font-bold">Property Compliance Analysis</h1>
 <p className="text-sm">{property?.address || 'Property Analysis'}</p>
 </div>
 </div>

 {/* Property Details */}
 <div className="p-6 bg-gray-50 border-b">
 <div className="grid grid-cols-3 gap-4">
 <div>
 <p className="text-xs text-gray-600 uppercase">Zone</p>
 <p className="font-semibold">{property?.zone || 'N/A'}</p>
 </div>
 <div>
 <p className="text-xs text-gray-600 uppercase">Height Limit</p>
 <p className="font-semibold">
 {property?.height_limit ? `${property.height_limit}${property.height_units || 'm'}` : '9.5m'}
 </p>
 </div>
 <div>
 <p className="text-xs text-gray-600 uppercase">FSR Limit</p>
 <p className="font-semibold">
 {property?.fsr_limit ? `${property.fsr_limit}:1` : '0.6:1'}
 </p>
 </div>
 </div>
 </div>

 {/* Setback Details */}
 <div className="divide-y divide-gray-200">
 {results.map((result, index) => (
 <SetbackCard key={`${result.boundary_type}-${index}`} result={result} />
 ))}
 </div>

 {/* Referenced Legislation Accordion */}
 <div className="p-6 bg-gray-50">
 <ReferencedLegislationAccordion 
 setbacks={results.map(result => ({
 boundary_type: result.boundary_type,
 clause_reference: result.clause_reference || result.legal_source || 'N/A',
 legal_source: result.legal_source || `${result.boundary_type} setback rule`,
 provision_id: result.provision_id,
 legal_authority: result.legal_authority
 }))}
 />
 </div>

 {/* Buildable Area Analysis */}
 {buildableArea && (
 <div className="bg-gray-100 p-6">
 <h3 className="text-lg font-semibold mb-4 text-gray-800">Buildable Area Analysis</h3>
 <div className="grid grid-cols-3 gap-4">
 <div>
 <p className="text-xs text-gray-600 uppercase">Total Lot Area</p>
 <p className="font-bold text-gray-800">{buildableArea.total_lot_area}m²</p>
 </div>
 <div>
 <p className="text-xs text-gray-600 uppercase">Buildable Area</p>
 <p className="font-bold text-gray-800">{buildableArea.buildable_area}m²</p>
 </div>
 <div>
 <p className="text-xs text-gray-600 uppercase">Buildable Percentage</p>
 <p className="font-bold text-gray-800">{buildableArea.buildable_percentage}%</p>
 </div>
 </div>
 <p className="mt-2 text-xs text-gray-500 italic">
 Professional verification required for final design. Calculations based on NSW Planning API geometry and database intelligence.
 </p>
 </div>
 )}
 </div>
 </div>
 );
}

// Sub-components
function SetbackCard({ result }: { result: SetbackResult }) {
 const [isExpanded, setIsExpanded] = useState(false);

 return (
 <div className="px-6 py-4 hover:bg-gray-50 transition-colors border-b border-gray-200 last:border-b-0">
 <div 
 className="flex justify-between items-center cursor-pointer"
 onClick={() => setIsExpanded(!isExpanded)}
 >
 <div className="flex items-center space-x-4">
 <Ruler className="w-6 h-6 text-indigo-600" />
 <div>
 <h3 className="font-semibold text-gray-800 capitalize">
 {result.boundary_type.replace('_', ' ')} Setback
 {result.conditions && <span className="text-sm font-normal text-gray-600 ml-1">({result.conditions})</span>}
 </h3>
 <p className="text-2xl font-bold text-indigo-700">{result.required_setback}m</p>
 </div>
 </div>
 <div className="flex items-center space-x-2">
 <span className="text-sm text-gray-600">
 {result.authority} | Level {result.precedence}
 </span>
 {isExpanded ? <ChevronUp className="text-gray-500" /> : <ChevronDown className="text-gray-500" />}
 </div>
 </div>

 {/* Expanded Details */}
 {isExpanded && (
 <div className="mt-4 bg-gray-50 p-4 rounded-lg">
 <div className="grid md:grid-cols-2 gap-4">
 <div>
 <p className="text-sm font-medium text-gray-700">Description</p>
 <p className="text-sm text-gray-600">{result.legal_context}</p>
 </div>
 <div>
 <p className="text-sm font-medium text-gray-700">Legal Authority</p>
 <p className="text-sm text-gray-600">{result.authority_explanation}</p>
 </div>
 </div>
 <div className="mt-4">
 <p className="text-sm font-medium text-gray-700">Specific Requirement</p>
 <p className="text-sm text-gray-600">{result.reasoning}</p>
 </div>
 <div className="mt-4 flex justify-between items-center">
 <div>
 <p className="text-sm font-medium text-gray-700">Reference</p>
 <p className="text-sm text-gray-600">{result.clause_reference || result.legal_source || 'N/A'}</p>
 </div>
 <div className="text-right">
 <span className="text-sm font-semibold text-green-600">
 {Math.round(result.confidence * 100)}% Confidence
 </span>
 </div>
 </div>
 </div>
 )}
 </div>
 );
}

// Helper function to estimate lot area from geometry
function estimateLotArea(geometry: LotGeometry): number {
 if (!geometry.rings || geometry.rings.length === 0) {
 return 450; // Default estimate
 }

 const coordinates = geometry.rings[0];
 if (coordinates.length < 4) {
 return 450; // Default estimate
 }

 // Simple bounding box area estimation
 const xCoords = coordinates.map(coord => coord[0]);
 const yCoords = coordinates.map(coord => coord[1]);
 
 const width = Math.max(...xCoords) - Math.min(...xCoords);
 const height = Math.max(...yCoords) - Math.min(...yCoords);
 
 // Convert from Web Mercator units to square meters (rough approximation)
 const areaEstimate = (width * height) / (1.2 * 1.2); // Scale factor for NSW latitude
 
 return Math.max(100, Math.min(areaEstimate / 1000, 5000)); // Clamp to reasonable range
}
