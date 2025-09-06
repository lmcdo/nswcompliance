// components/analysis/PreciseSetbackCalculator.tsx
'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Loader2, Calculator, AlertTriangle } from 'lucide-react';
import { useSetbackCalculation } from '@/hooks/useSetbackCalculation';
import type { PropertyData, LotGeometry } from '@/types/property';
import type { SetbackResult } from '@/types/setback';

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
    <div className="space-y-6 p-6">
      {/* Results Header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            <Calculator className="h-5 w-5 text-blue-600" />
            Precise Setback Calculations
            <span className="text-sm font-normal text-green-600 bg-green-50 px-2 py-1 rounded">
              Precision: Centimeter
            </span>
          </CardTitle>
        </CardHeader>
      </Card>

      {/* Setback Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {results.map((result, index) => (
          <SetbackCard key={`${result.boundary_type}-${index}`} result={result} />
        ))}
      </div>

      {/* Buildable Area Summary */}
      {buildableArea && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              🏗️ Buildable Area Analysis
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-6">
              <div className="text-center">
                <div className="text-3xl font-bold text-gray-900">{buildableArea.total_lot_area}m²</div>
                <div className="text-sm text-gray-600">Total Lot Area</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-green-600">{buildableArea.buildable_area}m²</div>
                <div className="text-sm text-gray-600">Buildable Area</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-blue-600">{buildableArea.buildable_percentage}%</div>
                <div className="text-sm text-gray-600">Buildable Percentage</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-red-600">{buildableArea.setback_area_lost}m²</div>
                <div className="text-sm text-gray-600">Area Lost to Setbacks</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Disclaimer */}
      <div className="text-sm text-gray-500 bg-yellow-50 p-4 rounded border-l-4 border-yellow-200">
        <div className="flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5 flex-shrink-0" />
          <div>
            <strong>Professional verification required for final design.</strong>
            <br />
            Calculations based on NSW Planning API geometry and database intelligence.
          </div>
        </div>
      </div>
    </div>
  );
}

// Sub-components
function SetbackCard({ result }: { result: SetbackResult }) {
  const boundaryTypeColors: { [key: string]: string } = {
    front: 'border-l-4 border-blue-500 bg-blue-50',
    rear: 'border-l-4 border-green-500 bg-green-50', 
    side_left: 'border-l-4 border-purple-500 bg-purple-50',
    side_right: 'border-l-4 border-orange-500 bg-orange-50',
    side: 'border-l-4 border-purple-500 bg-purple-50'
  };

  const colorClass = boundaryTypeColors[result.boundary_type] || 'border-l-4 border-gray-500 bg-gray-50';
  
  // Get boundary icon
  const getBoundaryIcon = (type: string) => {
    const icons: { [key: string]: string } = {
      front: '🏠', rear: '🌳', side: '🏘️', side_left: '⬅️', side_right: '➡️'
    };
    return icons[type] || '📏';
  };

  return (
    <div className="bg-white border rounded-lg p-6 mb-4 shadow-lg">
      {/* Simplified Professional Header */}
      <div className="bg-slate-800 text-white p-6 rounded-lg mb-4 flex justify-between items-center">
        <div>
          <h3 className="text-xl font-bold">
            {result.boundary_type.replace('_', ' ')} Setback
            {result.conditions && (
              <span className="text-lg font-normal text-purple-300 ml-2">
                ({result.conditions})
              </span>
            )}
          </h3>
          <div className="flex gap-2 mt-2">
            <span className="bg-blue-500 text-white px-2 py-1 rounded text-sm">
              {result.authority} • Level {result.precedence}
            </span>
            {result.conditions && (
              <span className="bg-purple-500 text-white px-2 py-1 rounded text-sm">
                🏠 {result.conditions}
              </span>
            )}
          </div>
        </div>
        <div className="text-4xl font-black">{result.required_setback}m</div>
      </div>
      
      <div className="space-y-4">
        <div className="bg-blue-50 p-4 rounded border-l-4 border-blue-500">
          <h4 className="font-bold text-blue-900">What this means:</h4>
          <p className="text-blue-800">{result.legal_context}</p>
        </div>
        
        <div className="bg-green-50 p-4 rounded border-l-4 border-green-500">
          <h4 className="font-bold text-green-900">Requirement:</h4>
          <p className="text-green-800">{result.reasoning}</p>
        </div>
        
        <div className="bg-purple-50 p-4 rounded border-l-4 border-purple-500">
          <h4 className="font-bold text-purple-900">Legal Authority:</h4>
          <p className="text-purple-800">{result.authority_explanation}</p>
        </div>
      </div>
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
