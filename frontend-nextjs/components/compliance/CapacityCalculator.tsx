'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';

interface CapacityCalculatorProps {
  propertyAddress: string;
  coordinates: google.maps.LatLngLiteral | null;
  developmentType: string;
  lotArea: number | null;
  zone: string;
  lga: string;
  formerCouncil: string;
}

interface CapacityResult {
  success: boolean;
  capacity?: {
    maxGFA: number | null;
    gfaSource: string;
    maxHeight: number | null;
    maxFSR: number | null;
    approxStoreys: number | null;
    lotArea: number;
  };
  setbacks?: {
    type: 'numeric' | 'prevailing' | 'precinct_specific' | 'not_available';
    front?: number;
    side?: number;
    rear?: number;
    message?: string;
    method?: string;
    minimum_standards?: any;
    source?: string;
    precinct_name?: string;
    values?: Array<{
      type: string;
      value: number;
      unit: string;
      text: string;
    }>;
  };
  parking?: Array<{
    text: string;
    spaces: number;
  }>;
  landscaping?: Array<{
    text: string;
    value: number;
    unit: string;
  }>;
  lepClauses?: Array<{
    clause_number: string;
    clause_title: string;
    requirements: string[];
  }>;
  error?: string;
}

export function CapacityCalculator({
  propertyAddress,
  coordinates,
  developmentType,
  lotArea,
  zone,
  lga,
  formerCouncil
}: CapacityCalculatorProps) {
  const [result, setResult] = useState<CapacityResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [autoCalculate, setAutoCalculate] = useState(false);

  async function calculateCapacity() {
    if (!lotArea) {
      setResult({
        success: false,
        error: 'Lot area not available from NSW Planning Portal'
      });
      return;
    }

    setLoading(true);
    try {
      // Estimate frontage from lot area if not available (square root approximation)
      const estimatedFrontage = Math.sqrt(lotArea);

      // Valid development types accepted by API
      const validDevTypes = [
        'dwelling_house', 'dual_occupancy', 'multi_dwelling_housing',
        'residential_flat_building', 'manor_house', 'terrace_house',
        'semi_detached_dwelling', 'attached_dwelling', 'secondary_dwelling',
        'shop_top_housing', 'boarding_house', 'group_home', 'hostels',
        'seniors_housing', 'shop', 'commercial_premises', 'office_premises',
        'retail_premises', 'warehouse', 'light_industry', 'general_industry', 'other'
      ];

      // Only include developmentType if it's valid
      const requestBody: any = {
        address: propertyAddress,
        coordinates: coordinates,
        lotSize: lotArea,  // API expects 'lotSize', not 'lotArea'
        frontage: estimatedFrontage,  // Required by API schema
        zone: zone,
        lga: lga,
        formerCouncil: formerCouncil
      };

      if (developmentType && validDevTypes.includes(developmentType)) {
        requestBody.developmentType = developmentType;
      }

      const response = await fetch('/api/capacity/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });

      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Capacity calculation failed:', error);
      setResult({
        success: false,
        error: 'Failed to calculate capacity. Please try again.'
      });
    } finally {
      setLoading(false);
    }
  }

  // Auto-calculate when dev type changes (if user has calculated once)
  useEffect(() => {
    if (autoCalculate && developmentType && lotArea) {
      calculateCapacity();
    }
  }, [developmentType, autoCalculate]);

  return (
    <div className="bg-white border rounded-lg p-6 mb-6">
      <h2 className="text-xl font-semibold mb-2">Development Capacity</h2>
      <p className="text-sm text-gray-600 mb-4">
        Calculate maximum buildable area, height, and site requirements
      </p>

      <div className="flex gap-4 items-center mb-4">
        <Button
          onClick={() => {
            calculateCapacity();
            setAutoCalculate(true);
          }}
          disabled={loading || !lotArea}
        >
          {loading ? 'Calculating...' : 'Calculate Capacity'}
        </Button>

        {!lotArea && (
          <p className="text-sm text-amber-600">
            Lot area not available from Planning Portal
          </p>
        )}
      </div>

      {result && (
        <div className="mt-4 space-y-4">
          {result.error ? (
            <div className="p-4 bg-red-50 border border-red-200 rounded">
              <p className="text-sm text-red-700">{result.error}</p>
            </div>
          ) : (
            <>
              {/* Main Capacity Card */}
              <div className="p-4 bg-blue-50 border border-blue-200 rounded">
                <h3 className="font-semibold text-lg mb-3">Maximum Building Envelope</h3>

                <div className="grid grid-cols-2 gap-4">
                  {/* Lot Area */}
                  <div>
                    <p className="text-sm text-gray-600">Lot Area</p>
                    <p className="text-xl font-semibold">{result.capacity?.lotArea}m²</p>
                  </div>

                  {/* Max GFA */}
                  {result.capacity?.maxGFA && (
                    <div>
                      <p className="text-sm text-gray-600">Max Gross Floor Area</p>
                      <p className="text-xl font-semibold">{result.capacity.maxGFA.toFixed(1)}m²</p>
                      <p className="text-xs text-gray-500">{result.capacity.gfaSource}</p>
                    </div>
                  )}

                  {/* Max Height */}
                  {result.capacity?.maxHeight && (
                    <div>
                      <p className="text-sm text-gray-600">Max Height</p>
                      <p className="text-xl font-semibold">{result.capacity.maxHeight}m</p>
                      {result.capacity.approxStoreys && (
                        <p className="text-xs text-gray-500">~{result.capacity.approxStoreys} storeys</p>
                      )}
                    </div>
                  )}

                  {/* Max FSR */}
                  {result.capacity?.maxFSR && (
                    <div>
                      <p className="text-sm text-gray-600">Max FSR</p>
                      <p className="text-xl font-semibold">{result.capacity.maxFSR}:1</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Calculation Methodology */}
              {(result.capacity?.maxGFA || result.capacity?.maxFSR || result.lepClauses?.length > 0) && (
                <details className="border rounded">
                  <summary className="p-3 cursor-pointer hover:bg-gray-50 font-medium text-sm flex items-center gap-2">
                    <span>📐 Calculation Methodology</span>
                    <span className="text-xs text-gray-500 font-normal">(show working)</span>
                  </summary>
                  <div className="p-4 bg-gray-50 border-t space-y-3">
                    {/* GFA Calculation */}
                    {result.capacity?.maxFSR && result.capacity?.maxGFA && (
                      <div className="p-3 bg-white border rounded">
                        <p className="text-sm font-semibold mb-2">Floor Space Ratio (FSR) Calculation:</p>
                        <div className="text-sm text-gray-700 space-y-1 font-mono">
                          <p>Max GFA = FSR × Lot Area</p>
                          <p>Max GFA = {result.capacity.maxFSR}:1 × {result.capacity.lotArea}m²</p>
                          <p className="text-green-700 font-bold">Max GFA = {result.capacity.maxGFA.toFixed(1)}m²</p>
                        </div>
                      </div>
                    )}

                    {/* Height Calculation */}
                    {result.capacity?.maxHeight && result.capacity?.approxStoreys && (
                      <div className="p-3 bg-white border rounded">
                        <p className="text-sm font-semibold mb-2">Height to Storeys Conversion:</p>
                        <div className="text-sm text-gray-700 space-y-1 font-mono">
                          <p>Storeys = Max Height ÷ 3m per storey</p>
                          <p>Storeys = {result.capacity.maxHeight}m ÷ 3m</p>
                          <p className="text-green-700 font-bold">~{result.capacity.approxStoreys} storeys</p>
                        </div>
                      </div>
                    )}

                    {/* LEP Clauses Referenced */}
                    {result.lepClauses && result.lepClauses.length > 0 && (
                      <div className="p-3 bg-white border rounded">
                        <p className="text-sm font-semibold mb-2">LEP Clauses Referenced:</p>
                        <div className="space-y-2">
                          {result.lepClauses.map((clause: any, idx: number) => (
                            <div key={idx} className="text-sm border-l-2 border-blue-400 pl-3">
                              <p className="font-medium text-blue-900">
                                Clause {clause.clause_number}: {clause.clause_title}
                              </p>
                              {clause.requirements && (
                                <ul className="text-xs text-gray-700 mt-1 space-y-1">
                                  {clause.requirements.map((req: string, i: number) => (
                                    <li key={i}>• {req}</li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Source Attribution */}
                    <div className="text-xs text-gray-600 italic">
                      <p>Calculations based on {lga} Local Environmental Plan and Development Control Plan provisions.</p>
                      <p className="mt-1">Always verify with qualified planning consultant before lodging applications.</p>
                    </div>
                  </div>
                </details>
              )}

              {/* Setbacks */}
              {result.setbacks && (
                <div className="p-4 border rounded">
                  <h4 className="font-semibold mb-2">Setbacks</h4>

                  {result.setbacks.type === 'numeric' && (
                    <div className="space-y-2">
                      {result.setbacks.front && (
                        <div className="flex justify-between">
                          <span className="text-sm">Front:</span>
                          <span className="font-medium">{result.setbacks.front}m minimum</span>
                        </div>
                      )}
                      {result.setbacks.side && (
                        <div className="flex justify-between">
                          <span className="text-sm">Side:</span>
                          <span className="font-medium">{result.setbacks.side}m minimum</span>
                        </div>
                      )}
                      {result.setbacks.rear && (
                        <div className="flex justify-between">
                          <span className="text-sm">Rear:</span>
                          <span className="font-medium">{result.setbacks.rear}m minimum</span>
                        </div>
                      )}
                      <p className="text-xs text-gray-500 mt-2">Source: {result.setbacks.source}</p>
                    </div>
                  )}

                  {result.setbacks.type === 'prevailing' && (
                    <div className="space-y-2">
                      <div className="p-3 bg-yellow-50 border border-yellow-200 rounded">
                        <p className="text-sm font-medium text-yellow-900 mb-1">
                          {result.setbacks.message}
                        </p>
                        <p className="text-xs text-yellow-800">{result.setbacks.method}</p>
                      </div>

                      {result.setbacks.minimum_standards && (
                        <div className="mt-2">
                          <p className="text-xs font-medium mb-1">Minimum Standards:</p>
                          <ul className="text-xs text-gray-600 space-y-1">
                            {Object.entries(result.setbacks.minimum_standards).map(([key, value]) => (
                              <li key={key}>
                                {key}: {value as string}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}

                  {result.setbacks.type === 'precinct_specific' && result.setbacks.values && (
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-green-900">
                        Precinct: {result.setbacks.precinct_name}
                      </p>
                      {result.setbacks.values.map((sb, i) => (
                        <div key={i} className="text-sm">
                          <span className="font-medium capitalize">{sb.type}:</span> {sb.value}{sb.unit}
                          <p className="text-xs text-gray-600">{sb.text.substring(0, 100)}...</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {result.setbacks.type === 'not_available' && (
                    <div className="p-3 bg-gray-50 border border-gray-200 rounded">
                      <p className="text-sm text-gray-700">{result.setbacks.message}</p>
                      {result.setbacks.method && (
                        <p className="text-xs text-gray-600 mt-1">{result.setbacks.method}</p>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Parking */}
              {result.parking && result.parking.length > 0 && (
                <div className="p-4 border rounded">
                  <h4 className="font-semibold mb-2">Parking Requirements</h4>
                  <ul className="space-y-2">
                    {result.parking.map((p, i) => (
                      <li key={i} className="text-sm">
                        <span className="font-medium">{p.spaces} spaces</span>
                        <p className="text-xs text-gray-600">{p.text.substring(0, 150)}...</p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Landscaping */}
              {result.landscaping && result.landscaping.length > 0 && (
                <div className="p-4 border rounded">
                  <h4 className="font-semibold mb-2">Landscaping / Open Space</h4>
                  <ul className="space-y-2">
                    {result.landscaping.map((l, i) => (
                      <li key={i} className="text-sm">
                        <span className="font-medium">{l.value}{l.unit || '%'}</span>
                        <p className="text-xs text-gray-600">{l.text.substring(0, 150)}...</p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* LEP Clauses */}
              {result.lepClauses && result.lepClauses.length > 0 && (
                <div className="p-4 border rounded">
                  <h4 className="font-semibold mb-2">Applicable LEP Clauses</h4>
                  <div className="space-y-3">
                    {result.lepClauses.map((clause, i) => (
                      <div key={i}>
                        <p className="text-sm font-medium">
                          Clause {clause.clause_number}: {clause.clause_title}
                        </p>
                        {clause.requirements && clause.requirements.length > 0 && (
                          <ul className="text-xs text-gray-600 ml-4 list-disc mt-1">
                            {clause.requirements.map((req, j) => (
                              <li key={j}>{req}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
