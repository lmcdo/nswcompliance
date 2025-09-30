'use client';

/**
 * Compliance Dashboard Component
 * Expert-friendly dashboard layout replacing dropdown navigation
 * Follows Universal Technical Implementation Specification
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ConstraintCard } from './ConstraintCard';
import { SeppOverlayIndicator } from './SeppOverlayIndicator';
import { LegalTextPanel, SelectedProvision } from './LegalTextPanel';
// Import types only, will use API endpoint for data
export interface ProvisionContent {
  id: number;
  ref_number: string;
  section_header: string;
  provision_text: string;
  document_id: string;
}

export interface ComplianceConstraint {
  type: 'height' | 'fsr' | 'setback' | 'heritage' | 'environmental' | 'special';
  value: string | number;
  unit?: string;
  source: {
    clause: string;
    document: string;
    authority_level: 'LEP' | 'DCP' | 'SEPP';
  };
  provisions?: ProvisionContent[];
  seppMetadata?: {
    epiName: string;
    mapType?: string;
    keywords?: string[];
  };
  lepMetadata?: {
    documentId: string;
    refNumber: string;
  };
  dcpMetadata?: {
    documentId: string;
    controlNumber?: string;
    chapter?: string;
    category?: string;
  };
}

export interface ComplianceData {
  building_envelope: ComplianceConstraint[];
  environmental: ComplianceConstraint[];
  special_provisions: ComplianceConstraint[];
}
import type { PropertyData } from '@/lib/property-data';

interface ComplianceDashboardProps {
  propertyData: PropertyData;
  className?: string;
}

export function ComplianceDashboard({
  propertyData,
  className = ''
}: ComplianceDashboardProps) {
  const [complianceData, setComplianceData] = useState<ComplianceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Slide-out panel state
  const [panelOpen, setPanelOpen] = useState(false);
  const [selectedProvision, setSelectedProvision] = useState<SelectedProvision | null>(null);

  // Extract NSW Planning API Special Provisions (Water Use, BASIX, etc.)
  const extractPlanningAPIProvisions = useCallback((): ComplianceConstraint[] => {
    const specialProvisionsLayer = propertyData.planningLayers?.find(
      layer => layer.layerName === 'Special Provisions'
    );

    if (!specialProvisionsLayer?.results) {
      return [];
    }

    const provisions: ComplianceConstraint[] = [];

    specialProvisionsLayer.results.forEach((result) => {
      const epiName = result['EPI Name'] || 'Unknown SEPP';
      const type = result.Type || '';
      const classValue = result.Class || '';
      const mapType = result['Map Type'] || '';
      const title = result.title || '';

      // Format the display value
      let displayValue = classValue || title;
      let displayUnit = undefined;

      // For percentage values (Water Use), remove % from value since we'll add it as unit
      if (type.includes('%') && displayValue.includes('%')) {
        displayValue = displayValue.replace('%', '');
        displayUnit = '%';
      }
      // For Climate Zones, prefix with "Class"
      else if (type.toLowerCase().includes('climate')) {
        displayValue = `Class ${classValue}`;
      }

      // Create constraint for each Special Provision with metadata for full text fetching
      provisions.push({
        type: 'special',
        value: displayValue,
        unit: displayUnit,
        source: {
          clause: `${mapType || 'Special'} - ${type}`,
          document: epiName,
          authority_level: 'SEPP'
        },
        // Add metadata for fetching full SEPP text from database
        seppMetadata: {
          epiName: epiName,
          mapType: mapType,
          keywords: [
            type.toLowerCase().includes('water') ? 'water' : undefined,
            type.toLowerCase().includes('climate') ? 'climate' : undefined,
            type.toLowerCase().includes('basix') ? 'BASIX' : undefined
          ].filter(Boolean) as string[]
        }
      });
    });

    console.log('[ComplianceDashboard] Extracted', provisions.length, 'Planning API provisions');
    return provisions;
  }, [propertyData]);

  // Extract LEP constraints from Planning API (Height, FSR)
  const extractLEPConstraints = useCallback((): ComplianceConstraint[] => {
    const constraints: ComplianceConstraint[] = [];

    // Height of Buildings Map
    const heightLayer = propertyData.planningLayers?.find(
      layer => layer.layerName === 'Height of Buildings Map'
    );
    if (heightLayer?.results?.[0]) {
      const result = heightLayer.results[0];
      const height = result['Maximum Building Height'];
      if (height) {
        constraints.push({
          type: 'height',
          value: parseFloat(height),
          unit: 'm',
          source: {
            clause: result['Legislative Clause'] || 'Clause 4.3',
            document: result['EPI Name'] || 'Local Environmental Plan',
            authority_level: 'LEP'
          },
          lepMetadata: {
            documentId: 'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_1_50',
            refNumber: '4.3'
          }
        });
      }
    }

    // Floor Space Ratio Map
    const fsrLayer = propertyData.planningLayers?.find(
      layer => layer.layerName === 'Floor Space Ratio Map'
    );
    if (fsrLayer?.results) {
      // Find the result with actual FSR value (not the amendment-only entry)
      const fsrResult = fsrLayer.results.find(r => r['Floor Space Ratio']);
      if (fsrResult) {
        const fsr = fsrResult['Floor Space Ratio'];
        constraints.push({
          type: 'fsr',
          value: parseFloat(fsr),
          unit: ':1',
          source: {
            clause: fsrResult['Legislative Clause'] || 'Clause 4.4',
            document: fsrResult['EPI Name'] || 'Local Environmental Plan',
            authority_level: 'LEP'
          },
          lepMetadata: {
            documentId: 'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_1_50',
            refNumber: '4.4'
          }
        });
      }
    }

    console.log('[ComplianceDashboard] Extracted', constraints.length, 'LEP constraints');
    return constraints;
  }, [propertyData]);

  // Extract DCP constraints (setbacks, parking, landscaping)
  const extractDCPConstraints = useCallback((): ComplianceConstraint[] => {
    const constraints: ComplianceConstraint[] = [];

    // Only add DCP constraints if we have a zone
    if (!propertyData.constraints?.zone) {
      return constraints;
    }

    const zone = propertyData.constraints.zone;
    const dcpDocId = 'Inner_West_Ashfield_DCP_2016___Chapter_F___Development_Category_with_IWLEP_2022_amendment';

    // Setback requirements (Priority 1 for certifiers)
    constraints.push({
      type: 'setback',
      value: 'See DCP',
      source: {
        clause: 'Building Setbacks',
        document: 'Inner West DCP 2016 - Chapter F',
        authority_level: 'DCP'
      },
      dcpMetadata: {
        documentId: dcpDocId,
        chapter: 'F',
        category: 'setback'
      }
    });

    // Car parking requirements (Priority 1 for certifiers)
    constraints.push({
      type: 'special',
      value: 'See DCP',
      source: {
        clause: 'Car Parking',
        document: 'Inner West DCP 2016 - Chapter F',
        authority_level: 'DCP'
      },
      dcpMetadata: {
        documentId: dcpDocId,
        chapter: 'F',
        category: 'parking'
      }
    });

    // Landscaping requirements
    constraints.push({
      type: 'environmental',
      value: 'See DCP',
      source: {
        clause: 'Landscaping',
        document: 'Inner West DCP 2016 - Chapter F',
        authority_level: 'DCP'
      },
      dcpMetadata: {
        documentId: dcpDocId,
        chapter: 'F',
        category: 'landscaping'
      }
    });

    console.log('[ComplianceDashboard] Extracted', constraints.length, 'DCP constraints');
    return constraints;
  }, [propertyData]);

  // Load compliance data from real API
  useEffect(() => {
    const loadComplianceData = async () => {
      try {
        setLoading(true);
        setError(null);

        if (!propertyData?.constraints?.zone) {
          setError('Property zone not available');
          setLoading(false);
          return;
        }

        console.log('[ComplianceDashboard] Fetching constraints for zone:', propertyData.constraints.zone);

        // Extract NSW Planning API Special Provisions FIRST (priority display)
        const planningAPIProvisions = extractPlanningAPIProvisions();

        // Extract LEP constraints from Planning API (Height, FSR)
        const lepConstraints = extractLEPConstraints();

        // Extract DCP constraints (setbacks, parking, landscaping)
        const dcpConstraints = extractDCPConstraints();

        // Call real API endpoint for database provisions
        const response = await fetch('/api/compliance/constraints', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            address: propertyData.address,
            zone: propertyData.constraints.zone,
            developmentType: propertyData.developmentType || undefined,
            propId: propertyData.propId
          })
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const apiResponse = await response.json();

        if (!apiResponse.success) {
          throw new Error(apiResponse.error || 'Failed to load constraints');
        }

        console.log('[ComplianceDashboard] Loaded database constraints:', apiResponse.data);
        console.log('[ComplianceDashboard] Metadata:', apiResponse.metadata);

        // Use Planning API provisions + LEP constraints + DCP constraints
        setComplianceData({
          building_envelope: [
            ...lepConstraints,  // LEP Height/FSR from Planning API
            ...dcpConstraints.filter(c => c.type === 'setback'),  // DCP setbacks
            ...(apiResponse.data.building_envelope || [])
          ],
          environmental: [
            ...dcpConstraints.filter(c => c.type === 'environmental'),  // DCP landscaping
            ...(apiResponse.data.environmental || [])
          ],
          special_provisions: [
            ...planningAPIProvisions,  // ONLY Planning API SEPP provisions
            ...dcpConstraints.filter(c => c.type === 'special')  // DCP parking
          ]
        });

      } catch (err) {
        console.error('[ComplianceDashboard] Failed to load compliance data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load compliance data');
      } finally {
        setLoading(false);
      }
    };

    if (propertyData) {
      loadComplianceData();
    }
  }, [propertyData, extractPlanningAPIProvisions, extractLEPConstraints, extractDCPConstraints]);

  // Handler for opening slide-out panel
  const handleViewProvision = useCallback(async (constraint: ComplianceConstraint) => {
    console.log('[ComplianceDashboard] Opening panel for:', constraint);

    // If SEPP with metadata, fetch full text
    if (constraint.seppMetadata) {
      try {
        const response = await fetch('/api/sepp/full-text', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            epiName: constraint.seppMetadata.epiName,
            keywords: constraint.seppMetadata.keywords,
            mapType: constraint.seppMetadata.mapType
          })
        });

        if (response.ok) {
          const data = await response.json();
          if (data.success && data.data.provisions) {
            const provisions = data.data.provisions.map((p: any) => ({
              id: p.id,
              ref_number: p.clause,
              section_header: p.sectionHeader || '',
              provision_text: p.fullText,
              document_id: p.documentId
            }));

            setSelectedProvision({
              constraint,
              provisions
            });
            setPanelOpen(true);
          }
        }
      } catch (error) {
        console.error('[ComplianceDashboard] Failed to fetch SEPP provision:', error);
      }
    }
    // If LEP with metadata, fetch from database
    else if (constraint.lepMetadata) {
      try {
        const response = await fetch('/api/lep/full-text', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            documentId: constraint.lepMetadata.documentId,
            refNumber: constraint.lepMetadata.refNumber
          })
        });

        if (response.ok) {
          const data = await response.json();
          if (data.success && data.data.provisions) {
            const provisions = data.data.provisions.map((p: any) => ({
              id: p.id,
              ref_number: p.ref_number,
              section_header: p.section_header || '',
              provision_text: p.provision_text,
              document_id: p.document_id
            }));

            setSelectedProvision({
              constraint,
              provisions
            });
            setPanelOpen(true);
          }
        }
      } catch (error) {
        console.error('[ComplianceDashboard] Failed to fetch LEP provision:', error);
      }
    }
    // If DCP with metadata, fetch from database
    else if (constraint.dcpMetadata) {
      try {
        const response = await fetch('/api/dcp/full-text', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            documentId: constraint.dcpMetadata.documentId,
            controlNumber: constraint.dcpMetadata.controlNumber,
            chapter: constraint.dcpMetadata.chapter,
            category: constraint.dcpMetadata.category
          })
        });

        if (response.ok) {
          const data = await response.json();
          if (data.success && data.data.provisions) {
            const provisions = data.data.provisions.map((p: any) => ({
              id: p.id,
              ref_number: p.ref_number,
              section_header: p.section_header || '',
              provision_text: p.provision_text,
              document_id: p.document_id
            }));

            setSelectedProvision({
              constraint,
              provisions
            });
            setPanelOpen(true);
          }
        }
      } catch (error) {
        console.error('[ComplianceDashboard] Failed to fetch DCP provision:', error);
      }
    } else {
      // For non-SEPP/LEP/DCP, show with empty provisions (will display "no details available")
      setSelectedProvision({
        constraint,
        provisions: []
      });
      setPanelOpen(true);
    }
  }, []);

  // Handle provision detail requests
  const handleViewDetails = useCallback(async (constraint: ComplianceConstraint) => {
    try {
      if (!constraint.provisions || constraint.provisions.length === 0) {
        // Fetch provision details from API endpoint
        const response = await fetch('/api/compliance/provisions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            clause: constraint.source.clause,
            documentType: constraint.source.authority_level
          })
        });

        if (response.ok) {
          const result = await response.json();
          if (result.success) {
            // Update the constraint with provisions
            constraint.provisions = result.data;

            // Trigger re-render
            setComplianceData(current => {
              if (!current) return current;
              return { ...current };
            });
          }
        }
      }
    } catch (err) {
      console.error('Failed to load provision details:', err);
    }
  }, []);

  // Quick reference strip
  const getQuickReference = () => {
    if (!propertyData.constraints) return null;

    const items = [];
    if (propertyData.constraints.zone) items.push(propertyData.constraints.zone);
    if (propertyData.constraints.maxHeight) items.push(`${propertyData.constraints.maxHeight}m`);
    if (propertyData.constraints.maxFsr) items.push(`${propertyData.constraints.maxFsr}:1`);
    if (propertyData.heritage?.isHeritage) items.push('Heritage: Yes');
    else items.push('Heritage: No');
    if (propertyData.constraints.floodProne !== undefined) {
      items.push(`Flood: ${propertyData.constraints.floodProne ? 'Yes' : 'No'}`);
    }
    if (propertyData.constraints.basixWater) items.push(`${propertyData.constraints.basixWater} Water SEPP`);

    return items.join(' | ');
  };

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>Loading Compliance Data...</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-32 bg-gray-200 rounded-lg animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={`border-red-200 bg-red-50 ${className}`}>
        <CardContent className="p-6">
          <div className="text-red-800">
            <div className="font-medium">Error Loading Compliance Data</div>
            <div className="text-sm mt-1">{error}</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Property Header */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-xl">
            Property Compliance: {propertyData.address}
          </CardTitle>
          <div className="text-sm text-gray-600">
            {propertyData.constraints?.lga && `${propertyData.constraints.lga} LGA`}
          </div>
        </CardHeader>
        <CardContent>
          {/* Quick Reference Strip */}
          <div className="bg-gray-50 px-4 py-2 rounded-lg text-sm font-mono">
            {getQuickReference()}
          </div>
        </CardContent>
      </Card>

      {/* SEPP Overlay Indicator - Prominent Position */}
      {complianceData?.special_provisions && complianceData.special_provisions.length > 0 && (
        <SeppOverlayIndicator
          seppProvisions={complianceData.special_provisions.filter(p =>
            p.source.authority_level === 'SEPP'
          )}
          affectedConstraints={[
            ...(complianceData.building_envelope.some(c => c.type === 'height') ? ['Building Height'] : []),
            ...(complianceData.building_envelope.some(c => c.type === 'fsr') ? ['Floor Space Ratio'] : []),
            ...(complianceData.environmental.some(c => c.type === 'heritage') ? ['Heritage'] : [])
          ]}
        />
      )}

      {/* Flex Layout: Constraints List + Slide-Out Panel */}
      <div className="flex gap-4" style={{ height: 'calc(100vh - 400px)', minHeight: '600px' }}>
        {/* Left: Constraints List (expands/contracts with panel) */}
        <div className={`
          transition-all duration-300 ease-in-out
          ${panelOpen ? 'w-[40%]' : 'w-full'}
          space-y-4 overflow-y-auto h-full
        `}>

      {/* SEPP Special Provisions Section - PRIORITY */}
      {complianceData?.special_provisions &&
       complianceData.special_provisions.filter(p => p.source.authority_level === 'SEPP').length > 0 && (
        <Card className="border-red-200">
          <CardHeader className="bg-red-50">
            <CardTitle className="flex items-center gap-2">
              <span className="text-xl">🟥</span>
              SEPP Special Provisions (Overrides Local Controls)
            </CardTitle>
            <p className="text-sm text-gray-600 mt-1">
              State Environmental Planning Policies - Highest legal precedence
            </p>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="space-y-3">
              {complianceData.special_provisions
                .filter(p => p.source.authority_level === 'SEPP')
                .map((constraint, index) => (
                <ConstraintCard
                  key={`sepp-${index}`}
                  constraint={constraint}
                  onViewDetails={handleViewProvision}
                  compact={true}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* LEP Building Envelope Section */}
      {complianceData?.building_envelope &&
       complianceData.building_envelope.filter(c => c.source.authority_level === 'LEP').length > 0 && (
        <Card className="border-blue-200">
          <CardHeader className="bg-blue-50">
            <CardTitle className="flex items-center gap-2">
              <span className="text-xl">🟦</span>
              LEP Building Envelope Constraints
            </CardTitle>
            <p className="text-sm text-gray-600 mt-1">
              Local Environmental Plan - Height, FSR, Lot Size
            </p>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="space-y-3">
              {complianceData.building_envelope
                .filter(c => c.source.authority_level === 'LEP')
                .map((constraint, index) => (
                <ConstraintCard
                  key={`lep-envelope-${index}`}
                  constraint={constraint}
                  onViewDetails={handleViewProvision}
                  compact={true}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* DCP Design Controls Section */}
      {complianceData?.building_envelope &&
       complianceData.building_envelope.filter(c => c.source.authority_level === 'DCP').length > 0 && (
        <Card className="border-green-200">
          <CardHeader className="bg-green-50">
            <CardTitle className="flex items-center gap-2">
              <span className="text-xl">🟢</span>
              DCP Design Controls
            </CardTitle>
            <p className="text-sm text-gray-600 mt-1">
              Development Control Plan - Setbacks, Design Guidelines
            </p>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="space-y-3">
              {complianceData.building_envelope
                .filter(c => c.source.authority_level === 'DCP')
                .map((constraint, index) => (
                <ConstraintCard
                  key={`dcp-${index}`}
                  constraint={constraint}
                  onViewDetails={handleViewProvision}
                  compact={true}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Environmental Constraints */}
      {complianceData?.environmental && complianceData.environmental.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span className="text-xl">🌳</span>
              Environmental Constraints
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {complianceData.environmental.map((constraint, index) => (
                <ConstraintCard
                  key={`environmental-${index}`}
                  constraint={constraint}
                  onViewDetails={handleViewProvision}
                  compact={true}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

          {/* Empty State */}
          {(!complianceData ||
            (complianceData.building_envelope.length === 0 &&
             complianceData.environmental.length === 0 &&
             complianceData.special_provisions.length === 0)) && (
            <Card>
              <CardContent className="p-8 text-center text-gray-500">
                <div className="text-lg mb-2">No Compliance Data Available</div>
                <div className="text-sm">
                  Compliance constraints could not be loaded for this property.
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right: Slide-Out Legal Text Panel */}
        <div className={`
          transition-all duration-300 ease-in-out overflow-hidden h-full
          ${panelOpen ? 'w-[60%] opacity-100' : 'w-0 opacity-0'}
        `}>
          {panelOpen && (
            <LegalTextPanel
              selectedProvision={selectedProvision}
              onClose={() => setPanelOpen(false)}
            />
          )}
        </div>
      </div>
    </div>
  );
}