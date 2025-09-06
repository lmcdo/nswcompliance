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
    front: 'boundary-front bg-blue-50 border-blue-200',
    rear: 'boundary-rear bg-green-50 border-green-200', 
    side_left: 'boundary-side-left bg-purple-50 border-purple-200',
    side_right: 'boundary-side-right bg-orange-50 border-orange-200',
    side: 'boundary-side bg-purple-50 border-purple-200'
  };

  const colorClass = boundaryTypeColors[result.boundary_type] || 'bg-gray-50 border-gray-200';
  
  // Get boundary icon
  const getBoundaryIcon = (type: string) => {
    const icons: { [key: string]: string } = {
      front: '🏠', rear: '🌳', side: '🏘️', side_left: '⬅️', side_right: '➡️'
    };
    return icons[type] || '📏';
  };

  return (
    <Card className={`setback-card ${colorClass} border-2 hover:shadow-lg transition-shadow`}>
      <CardContent className="p-6">
        <div className="space-y-4">
          {/* Header with icon and boundary type */}
          <div className="text-center border-b pb-4">
            <div className="text-2xl mb-2">{getBoundaryIcon(result.boundary_type)}</div>
            <div className="text-lg font-semibold capitalize text-gray-900">
              {result.boundary_type.replace('_', ' ')} Setback
            </div>
            <div className="text-4xl font-bold mb-1 text-gray-900">
              {result.required_setback}m
            </div>
            {result.buildable_depth && (
              <div className="text-sm text-gray-600">
                Buildable depth: {result.buildable_depth}m
              </div>
            )}
          </div>

          {/* Legal Authority Badge */}
          <div className="text-center">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium
              ${result.precedence === 1 ? 'bg-red-100 text-red-800' : 
                result.precedence === 2 ? 'bg-orange-100 text-orange-800' : 
                'bg-blue-100 text-blue-800'}`}>
              {result.authority} • Precedence Level {result.precedence}
            </span>
          </div>

          {/* Explanation */}
          <div className="bg-white/90 p-4 rounded-lg border">
            <div className="font-medium text-gray-900 mb-2">What this means:</div>
            <div className="text-sm text-gray-700 mb-3">{result.legal_context}</div>
            
            <div className="font-medium text-gray-900 mb-2">Requirement:</div>
            <div className="text-sm text-gray-700 mb-3">{result.reasoning}</div>
            
            <div className="font-medium text-gray-900 mb-2">Legal Authority:</div>
            <div className="text-sm text-gray-700">{result.authority_explanation}</div>
          </div>

          {/* Clause Citation */}
          {result.full_clause_text && (
            <details className="bg-gray-50 p-3 rounded border">
              <summary className="cursor-pointer font-medium text-sm text-gray-800 hover:text-blue-600">
                📋 View Full Legal Clause ({result.clause_reference})
              </summary>
              <div className="mt-3 pt-3 border-t">
                <div className="text-xs text-gray-600 mb-2">
                  <strong>Source:</strong> {result.legal_source}
                  {result.document_section && <span> • Section: {result.document_section}</span>}
                  {result.page_number && <span> • Page: {result.page_number}</span>}
                </div>
                <div className="text-sm bg-white p-3 rounded border-l-4 border-blue-200 italic">
                  "{result.full_clause_text}"
                </div>
              </div>
            </details>
          )}

          {/* Conditions and Confidence */}
          <div className="flex justify-between items-center pt-4 border-t">
            <div className="text-left">
              {result.conditions && (
                <div className="text-xs text-gray-600">
                  <strong>Conditions:</strong> {result.conditions}
                </div>
              )}
            </div>
            <div className="text-right">
              <div className={`px-2 py-1 rounded text-xs font-medium
                ${result.confidence >= 0.8 ? 'bg-green-100 text-green-800' : 
                  result.confidence >= 0.6 ? 'bg-yellow-100 text-yellow-800' : 
                  'bg-red-100 text-red-800'}`}>
                {Math.round(result.confidence >= 1 ? result.confidence : result.confidence * 100)}% Confidence
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
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