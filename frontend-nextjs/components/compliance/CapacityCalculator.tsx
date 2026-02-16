'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ChevronDown, FileImage } from 'lucide-react';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { getPdfImageUrl } from '@/lib/pdf-image-url';

interface CapacityCalculatorProps {
  propertyAddress: string;
  coordinates: google.maps.LatLngLiteral | null;
  developmentType: string;
  lotArea: number | null;
  zone: string;
  lga: string;
  formerCouncil: string;
  planningLayers?: any[];  // Extract FSR/height from here
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
    partName?: string;
    pdfPage?: number;
    pdfPageImageUrl?: string;
  }>;
  lepClauses?: Array<{
    clause_number: string;
    clause_title: string;
    requirements: string[];
    pdfPage?: number;
    pdfPrintedPage?: number;
    pdfPageImageUrl?: string;
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
  formerCouncil,
  planningLayers
}: CapacityCalculatorProps) {
  const [result, setResult] = useState<CapacityResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [autoCalculate, setAutoCalculate] = useState(false);
  const [viewingPdfPage, setViewingPdfPage] = useState<{ pageNumber: number; url: string; label: string } | null>(null);

  // Auto-calculate immediately if we have Planning Portal data
  useEffect(() => {
    if (!lotArea || !planningLayers || planningLayers.length === 0) return;

    // Extract FSR from planning layers (same as PropertyDetailsComprehensive)
    let fsr: number | null = null;
    let maxHeight: number | null = null;

    for (const layer of planningLayers) {
      for (const result of layer.results || []) {
        if (!fsr && result['Floor Space Ratio']) {
          fsr = parseFloat(result['Floor Space Ratio']);
        }
        if (!maxHeight && result['Maximum Building Height']) {
          const heightStr = String(result['Maximum Building Height']);
          maxHeight = parseFloat(heightStr.replace(/[^\d.]/g, ''));
        }
        if (fsr && maxHeight) break;
      }
      if (fsr && maxHeight) break;
    }

    if (lotArea && fsr && maxHeight) {
      // Calculate directly from Planning Portal data
      const maxGFA = lotArea * fsr;
      const approxStoreys = Math.floor(maxHeight / 3.0);

      setResult({
        success: true,
        capacity: {
          maxGFA: maxGFA,
          gfaSource: 'Planning Portal FSR data',
          maxHeight: maxHeight,
          maxFSR: fsr,
          approxStoreys: approxStoreys,
          lotArea: lotArea
        }
      });
      setAutoCalculate(true);

      // Also fetch parking/landscaping/LEP clauses from API
      calculateCapacity();
    }
  }, [lotArea, planningLayers]);

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
      console.log('API returned:', { hasParking: !!data.parking, hasLandscaping: !!data.landscaping, hasLepClauses: !!data.lepClauses });
      // Merge API data with existing Planning Portal data (don't overwrite capacity if we have it)
      setResult(prev => {
        const merged = {
          ...data,
          capacity: prev?.capacity || data.capacity  // Keep Planning Portal capacity if we have it
        };
        console.log('After merge:', { hasParking: !!merged.parking, hasLandscaping: !!merged.landscaping, hasLepClauses: !!merged.lepClauses });
        return merged;
      });
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
  // BUT: Skip if we already have Planning Portal data
  useEffect(() => {
    if (autoCalculate && developmentType && lotArea && !result?.capacity) {
      calculateCapacity();
    }
  }, [developmentType, autoCalculate]);

  return (
    <React.Fragment>
    <Collapsible className="bg-white border rounded-lg mb-4">
      <CollapsibleTrigger className="w-full p-3 hover:bg-gray-50 font-medium text-sm flex items-center gap-3 group">
        <ChevronDown className="w-5 h-5 transition-transform group-data-[state=open]:rotate-0 group-data-[state=closed]:-rotate-90" />
        <span className="flex-1 text-left">📊 Development Capacity Calculator</span>
        <span className="text-xs text-gray-500">FSR · Height · GFA</span>
      </CollapsibleTrigger>

      <CollapsibleContent className="px-3 pb-3 space-y-2">
      {!lotArea && (
        <div className="p-2 bg-amber-50 border border-amber-200 rounded text-xs">
          <p className="text-amber-900">⚠️ Lot area not available from Planning Portal</p>
        </div>
      )}

      {result && (
        <div className="mt-2 space-y-2">
          {result.error ? (
            <div className="p-4 bg-red-50 border border-red-200 rounded">
              <p className="text-sm text-red-700">{result.error}</p>
            </div>
          ) : (
            <>
              {/* Calculation Methodology - ABOVE results */}
              {(result.capacity?.maxGFA || result.capacity?.maxFSR || (result.landscaping && result.landscaping.length > 0)) && (
                <Collapsible className="border rounded text-sm">
                  <CollapsibleTrigger className="w-full p-2 hover:bg-gray-50 font-medium text-xs flex items-center gap-2">
                    <ChevronDown className="w-4 h-4 transition-transform group-data-[state=open]:rotate-0 group-data-[state=closed]:-rotate-90" />
                    <span>📐 Working</span>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="p-2 bg-gray-50 border-t space-y-2 text-xs">
                    {/* GFA Calculation */}
                    {result.capacity?.maxFSR && result.capacity?.maxGFA && (
                      <div className="p-2 bg-white border rounded font-mono text-xs space-y-0.5">
                        <p>Max GFA = FSR × Lot Area</p>
                        <p>Max GFA = {result.capacity.maxFSR}:1 × {result.capacity.lotArea}m²</p>
                        <p className="text-green-700 font-bold">= {result.capacity.maxGFA.toFixed(1)}m²</p>
                      </div>
                    )}

                    {/* Height Calculation */}
                    {result.capacity?.maxHeight && result.capacity?.approxStoreys && (
                      <div className="p-2 bg-white border rounded font-mono text-xs space-y-0.5">
                        <p>Storeys = Height ÷ 3m/storey</p>
                        <p>Storeys = {result.capacity.maxHeight}m ÷ 3m</p>
                        <p className="text-green-700 font-bold">= ~{result.capacity.approxStoreys} storeys</p>
                      </div>
                    )}

                    {/* Landscaping Calculation */}
                    {result.landscaping && result.landscaping.length > 0 && lotArea && (
                      <>
                        {result.landscaping.map((l, i) => {
                          const unit = (l.unit === 'percent' || l.unit === 'percentage') ? '%' : (l.unit || '%');
                          if (unit === '%') {
                            const landscapeArea = (l.value / 100) * lotArea;
                            const landscapeDimension = Math.sqrt(landscapeArea);
                            return (
                              <div key={i} className="p-2 bg-white border rounded font-mono text-xs space-y-0.5">
                                <p>Required Landscaping = {l.value}% × Lot Area</p>
                                <p>Required Landscaping = {l.value}% × {lotArea}m²</p>
                                <p className="text-green-700 font-bold">= {landscapeArea.toFixed(1)}m²</p>
                                <p className="text-gray-600 mt-1">If square: √{landscapeArea.toFixed(1)}m²</p>
                                <p className="text-green-700 font-bold">≈ {landscapeDimension.toFixed(2)}m × {landscapeDimension.toFixed(2)}m</p>
                              </div>
                            );
                          }
                          return null;
                        })}
                      </>
                    )}
                  </CollapsibleContent>
                </Collapsible>
              )}

              {/* Main Capacity Card */}
              <div className="p-2 bg-blue-50 border border-blue-200 rounded">
                <h3 className="font-semibold text-sm mb-2">Maximum Building Envelope</h3>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  {/* Lot Area */}
                  <div>
                    <p className="text-gray-600">Lot Area</p>
                    <p className="text-base font-semibold">{result.capacity?.lotArea}m²</p>
                  </div>

                  {/* Max GFA */}
                  {result.capacity?.maxGFA && (
                    <div>
                      <p className="text-gray-600">Max GFA</p>
                      <p className="text-base font-semibold">{result.capacity.maxGFA.toFixed(1)}m²</p>
                    </div>
                  )}

                  {/* Max Height */}
                  {result.capacity?.maxHeight && (
                    <div>
                      <p className="text-gray-600">Max Height</p>
                      <p className="text-base font-semibold">{result.capacity.maxHeight}m <span className="text-xs text-gray-500">~{result.capacity.approxStoreys} storeys</span></p>
                    </div>
                  )}

                  {/* Max FSR */}
                  {result.capacity?.maxFSR && (
                    <div>
                      <p className="text-gray-600">Max FSR</p>
                      <p className="text-base font-semibold">{result.capacity.maxFSR}:1</p>
                    </div>
                  )}
                </div>

                {/* No Calculations Available Message - only if NO data at all */}
                {!result.capacity?.maxGFA && !result.capacity?.maxHeight && !result.capacity?.maxFSR && (!result.lepClauses || result.lepClauses.length === 0) && (
                  <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded text-xs">
                    <p className="text-amber-900 font-medium">⚠️ No FSR or height limits found</p>
                    <p className="text-amber-800 mt-1">
                      Check the {zone} zone table in {lga} LEP or contact council for capacity controls.
                    </p>
                  </div>
                )}
              </div>

              {/* Parking */}
              {result.parking && result.parking.length > 0 && (
                <div className="p-2 border rounded text-xs">
                  <p className="font-semibold text-gray-700 mb-1">Parking</p>
                  <div className="space-y-1">
                    {result.parking.map((p, i) => (
                      <div key={i} className="flex items-baseline gap-2">
                        <span className="font-semibold text-gray-900">{p.spaces} spaces</span>
                        <span className="text-gray-600 text-xs">• {p.text.substring(0, 80)}...</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Landscaping */}
              {result.landscaping && result.landscaping.length > 0 && (
                <div className="p-2 border rounded text-xs">
                  <p className="font-semibold text-gray-700 mb-1">Landscaping / Open Space</p>
                  <div className="space-y-2">
                    {result.landscaping.map((l, i) => {
                      const unit = (l.unit === 'percent' || l.unit === 'percentage') ? '%' : (l.unit || '%');
                      return (
                        <div key={i} className="space-y-0.5">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-gray-900">{l.value}{unit}</span>
                            <span className="text-gray-600 text-xs flex-1">• {l.text}</span>
                            {l.pdfPageImageUrl && l.pdfPage && (
                              <button
                                onClick={() => setViewingPdfPage({
                                  pageNumber: l.pdfPage!,
                                  url: l.pdfPageImageUrl!,
                                  label: `${formerCouncil} DCP - Page ${l.pdfPage}`
                                })}
                                className="p-1 rounded hover:bg-blue-100 transition-colors flex-shrink-0"
                                title="View PDF page"
                              >
                                <FileImage className="w-4 h-4 text-blue-500 hover:text-blue-700" />
                              </button>
                            )}
                          </div>
                          {(l.partName || l.pdfPage) && (
                            <div className="text-xs text-gray-500 ml-6">
                              <span>{formerCouncil} DCP</span>
                              {l.partName && <span> · {l.partName}</span>}
                              {l.pdfPage && <span> · Page {l.pdfPage}</span>}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* LEP Clauses */}
              {result.lepClauses && result.lepClauses.length > 0 && (
                <div className="p-2 border rounded text-xs">
                  <p className="font-semibold text-gray-700 mb-1">{lga} LEP 2022</p>
                  <div className="space-y-2">
                    {result.lepClauses.map((clause, i) => (
                        <div key={i}>
                          <div className="font-medium text-gray-900 mb-0.5">
                            <span className="text-blue-700 font-mono">Clause {clause.clause_number}</span>
                            {clause.clause_title && clause.clause_title !== clause.clause_number && (
                              <span className="ml-1.5">· {clause.clause_title}</span>
                            )}
                          </div>
                          <div className="text-xs text-gray-500 ml-3 mb-0.5">
                            {lga} LEP 2022
                          </div>
                          {clause.requirements && clause.requirements.length > 0 && (
                            <div className="ml-3 text-gray-600 space-y-0.5">
                              {clause.requirements.map((req, j) => {
                                // Clean up Word artifacts (replace single capital letters surrounded by spaces/punctuation)
                                const cleanReq = req.replace(/\b([A-Z])\s+(\d)/g, '$2').replace(/\s+([A-Z])\b/g, '');
                                return (
                                  <div key={j}>• {cleanReq}</div>
                                );
                              })}
                            </div>
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
      </CollapsibleContent>
    </Collapsible>

    {/* PDF Image Modal */}
    {viewingPdfPage && (
      <PdfImageModal
        isOpen={true}
        onClose={() => setViewingPdfPage(null)}
        pageNumber={viewingPdfPage.pageNumber}
        imageUrl={viewingPdfPage.url}
        label={viewingPdfPage.label}
      />
    )}
    </React.Fragment>
  );
}
