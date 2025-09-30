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

      // Create constraint for each Special Provision with metadata for full text fetching
      provisions.push({
        type: 'special',
        value: classValue || title,
        unit: type.includes('%') ? '%' : undefined,
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

        // Use ONLY Planning API Special Provisions (not database unfiltered provisions)
        setComplianceData({
          building_envelope: apiResponse.data.building_envelope || [],
          environmental: apiResponse.data.environmental || [],
          special_provisions: planningAPIProvisions  // ONLY Planning API SEPP provisions
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
  }, [propertyData, extractPlanningAPIProvisions]);

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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {complianceData.special_provisions
                .filter(p => p.source.authority_level === 'SEPP')
                .map((constraint, index) => (
                <ConstraintCard
                  key={`sepp-${index}`}
                  constraint={constraint}
                  onViewDetails={handleViewDetails}
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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {complianceData.building_envelope
                .filter(c => c.source.authority_level === 'LEP')
                .map((constraint, index) => (
                <ConstraintCard
                  key={`lep-envelope-${index}`}
                  constraint={constraint}
                  onViewDetails={handleViewDetails}
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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {complianceData.building_envelope
                .filter(c => c.source.authority_level === 'DCP')
                .map((constraint, index) => (
                <ConstraintCard
                  key={`dcp-${index}`}
                  constraint={constraint}
                  onViewDetails={handleViewDetails}
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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {complianceData.environmental.map((constraint, index) => (
                <ConstraintCard
                  key={`environmental-${index}`}
                  constraint={constraint}
                  onViewDetails={handleViewDetails}
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
  );
}