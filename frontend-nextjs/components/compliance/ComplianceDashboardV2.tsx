'use client';

/**
 * Compliance Dashboard V2 - Using Phase 2 Zone Applicability API
 *
 * Key Changes:
 * - Uses /api/provisions/zone-applicability for provisions
 * - Priority-based progressive disclosure (display_priority from Phase 1)
 * - Lazy loading for low-priority provisions
 * - Cross-reference inline display
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ConstraintCard } from './ConstraintCard';
import { SeppOverlayIndicator } from './SeppOverlayIndicator';
import { LegalTextPanel, SelectedProvision } from './LegalTextPanel';
import type { PropertyData } from '@/lib/property-data';
import type { ComplianceConstraint, ProvisionContent } from './ComplianceDashboard';

interface ComplianceDashboardProps {
  propertyData: PropertyData;
  developmentType?: string;
  className?: string;
}

interface ZoneProvision {
  provisionId: number;
  refNumber: string;
  provisionText: string;
  explicitZone: string | null;
  appliesToZone: string | null;
  appliesToAllZones: boolean;
  appliesToLGA: string | null;
  appliesStateWide: boolean;
  applicabilitySource: string;
  confidenceScore: number;
  documentId: string;
  provisionCategory: string;
  displayPriority: number;
}

export function ComplianceDashboardV2({
  propertyData,
  developmentType = 'dwelling_house',
  className = ''
}: ComplianceDashboardProps) {
  const [provisions, setProvisions] = useState<ZoneProvision[]>([]);
  const [provisionsByPriority, setProvisionsByPriority] = useState<Record<number, ZoneProvision[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showLowPriority, setShowLowPriority] = useState(false);

  // Slide-out panel state
  const [panelOpen, setPanelOpen] = useState(false);
  const [selectedProvision, setSelectedProvision] = useState<SelectedProvision | null>(null);

  // Load provisions using Phase 2 zone-applicability endpoint
  useEffect(() => {
    const loadProvisions = async () => {
      try {
        setLoading(true);
        setError(null);

        const zone = propertyData?.constraints?.zone;
        const lga = propertyData?.constraints?.lga;

        if (!zone) {
          setError('Property zone not available');
          setLoading(false);
          return;
        }

        console.log('[DashboardV2] Fetching provisions for zone:', zone, 'LGA:', lga);

        // Call Phase 2 zone-applicability endpoint
        const response = await fetch(
          `/api/provisions/zone-applicability?zone=${encodeURIComponent(zone)}&lga=${encodeURIComponent(lga || '')}&limit=100`
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const apiResponse = await response.json();

        if (!apiResponse.success) {
          throw new Error(apiResponse.error || 'Failed to load provisions');
        }

        console.log('[DashboardV2] Loaded provisions:', apiResponse.data.totalCount);
        console.log('[DashboardV2] By priority:', apiResponse.data.byPriority);

        setProvisions(apiResponse.data.provisions);
        setProvisionsByPriority(apiResponse.data.byPriority);

      } catch (err) {
        console.error('[DashboardV2] Failed to load provisions:', err);
        setError(err instanceof Error ? err.message : 'Failed to load provisions');
      } finally {
        setLoading(false);
      }
    };

    if (propertyData) {
      loadProvisions();
    }
  }, [propertyData, developmentType]);

  // Convert provision to constraint format for existing components
  const provisionToConstraint = (provision: ZoneProvision): ComplianceConstraint => {
    const documentType = provision.documentId.includes('SEPP') ? 'SEPP' :
                         provision.documentId.includes('LEP') ? 'LEP' : 'DCP';

    // Infer constraint type from provision category
    let type: ComplianceConstraint['type'] = 'special';
    if (provision.provisionCategory === 'numeric_control') type = 'setback';
    else if (provision.provisionCategory === 'diagram_requirement') type = 'setback';
    else if (provision.provisionCategory === 'use_permission') type = 'special';

    return {
      type,
      value: provision.refNumber,
      source: {
        clause: provision.refNumber,
        document: provision.documentId.substring(0, 50),
        authority_level: documentType as 'SEPP' | 'LEP' | 'DCP'
      },
      provision_id: provision.provisionId,
      full_text: provision.provisionText,
      provisions: [{
        id: provision.provisionId,
        ref_number: provision.refNumber,
        section_header: '',
        provision_text: provision.provisionText,
        document_id: provision.documentId
      }]
    };
  };

  // Handle viewing provision details
  const handleViewProvision = useCallback(async (constraint: ComplianceConstraint) => {
    console.log('[DashboardV2] Opening panel for provision:', constraint.provision_id);

    if (constraint.provisions && constraint.provisions.length > 0) {
      setSelectedProvision({
        constraint,
        provisions: constraint.provisions
      });
      setPanelOpen(true);
      return;
    }

    // Fetch enhanced provision data with cross-references
    try {
      const response = await fetch(`/api/provisions/${constraint.provision_id}/enhanced`);
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          const enhanced = data.data;

          setSelectedProvision({
            constraint,
            provisions: [{
              id: enhanced.id,
              ref_number: enhanced.refNumber,
              section_header: enhanced.sectionHeader || '',
              provision_text: enhanced.provisionText,
              document_id: enhanced.documentId
            }],
            // Pass cross-references for inline display
            crossReferences: enhanced.crossReferences.references,
            controlCodes: enhanced.controlCodes.codes
          });
          setPanelOpen(true);
        }
      }
    } catch (error) {
      console.error('[DashboardV2] Failed to fetch enhanced provision:', error);
    }
  }, []);

  // Get quick reference
  const getQuickReference = () => {
    if (!propertyData.constraints) return null;

    const items = [];
    if (propertyData.constraints.zone) items.push(propertyData.constraints.zone);
    if (propertyData.constraints.maxHeight) items.push(`${propertyData.constraints.maxHeight}m`);
    if (propertyData.constraints.maxFsr) items.push(`${propertyData.constraints.maxFsr}:1`);
    if (propertyData.heritage?.isHeritage) items.push('Heritage: Yes');
    else items.push('Heritage: No');

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

  // Separate provisions by priority (1=highest, 6=lowest)
  const highPriorityProvisions = [...(provisionsByPriority[1] || []), ...(provisionsByPriority[2] || [])];
  const mediumPriorityProvisions = [...(provisionsByPriority[3] || []), ...(provisionsByPriority[4] || [])];
  const lowPriorityProvisions = [...(provisionsByPriority[5] || []), ...(provisionsByPriority[6] || [])];

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Property Header */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-xl">
            Property Compliance: {propertyData.address}
          </CardTitle>
          <div className="text-sm text-gray-600">
            {propertyData.constraints?.lga && `${propertyData.constraints.lga} LGA`} | Zone: {propertyData.constraints?.zone}
          </div>
        </CardHeader>
        <CardContent>
          {/* Quick Reference Strip */}
          <div className="bg-gray-50 px-4 py-2 rounded-lg text-sm font-mono">
            {getQuickReference()}
          </div>

          {/* Stats */}
          <div className="mt-4 grid grid-cols-3 gap-4 text-center text-sm">
            <div>
              <div className="text-2xl font-bold text-red-600">{highPriorityProvisions.length}</div>
              <div className="text-gray-600">Critical</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-orange-600">{mediumPriorityProvisions.length}</div>
              <div className="text-gray-600">Important</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-600">{lowPriorityProvisions.length}</div>
              <div className="text-gray-600">Reference</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Flex Layout: Provisions List + Slide-Out Panel */}
      <div className="flex gap-4" style={{ height: 'calc(100vh - 400px)', minHeight: '600px' }}>
        {/* Left: Provisions List */}
        <div className={`
          transition-all duration-300 ease-in-out
          ${panelOpen ? 'w-[40%]' : 'w-full'}
          space-y-4 overflow-y-auto h-full
        `}>
          {/* Priority 1-2: Critical Provisions */}
          {highPriorityProvisions.length > 0 && (
            <Card className="border-red-200">
              <CardHeader className="bg-red-50">
                <CardTitle className="flex items-center gap-2">
                  <span className="text-xl">🔴</span>
                  Critical Provisions (Priority 1-2)
                </CardTitle>
                <p className="text-sm text-gray-600 mt-1">
                  Overrides and mandatory numeric controls
                </p>
              </CardHeader>
              <CardContent className="pt-4">
                <div className="space-y-3">
                  {highPriorityProvisions.map((provision, index) => (
                    <ConstraintCard
                      key={`high-${index}`}
                      constraint={provisionToConstraint(provision)}
                      onViewDetails={handleViewProvision}
                      compact={true}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Priority 3-4: Important Provisions */}
          {mediumPriorityProvisions.length > 0 && (
            <Card className="border-orange-200">
              <CardHeader className="bg-orange-50">
                <CardTitle className="flex items-center gap-2">
                  <span className="text-xl">🟠</span>
                  Important Provisions (Priority 3-4)
                </CardTitle>
                <p className="text-sm text-gray-600 mt-1">
                  Diagram requirements and conditional provisions
                </p>
              </CardHeader>
              <CardContent className="pt-4">
                <div className="space-y-3">
                  {mediumPriorityProvisions.map((provision, index) => (
                    <ConstraintCard
                      key={`medium-${index}`}
                      constraint={provisionToConstraint(provision)}
                      onViewDetails={handleViewProvision}
                      compact={true}
                    />
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Priority 5-6: Reference Provisions (Lazy Load) */}
          {lowPriorityProvisions.length > 0 && (
            <Card className="border-gray-200">
              <CardHeader className="bg-gray-50">
                <CardTitle className="flex items-center gap-2 justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">⚪</span>
                    Reference Provisions (Priority 5-6)
                  </div>
                  <button
                    onClick={() => setShowLowPriority(!showLowPriority)}
                    className="text-sm px-3 py-1 bg-white border rounded hover:bg-gray-50"
                  >
                    {showLowPriority ? 'Hide' : 'Show'} ({lowPriorityProvisions.length})
                  </button>
                </CardTitle>
                <p className="text-sm text-gray-600 mt-1">
                  Cross-references and general provisions
                </p>
              </CardHeader>
              {showLowPriority && (
                <CardContent className="pt-4">
                  <div className="space-y-3">
                    {lowPriorityProvisions.map((provision, index) => (
                      <ConstraintCard
                        key={`low-${index}`}
                        constraint={provisionToConstraint(provision)}
                        onViewDetails={handleViewProvision}
                        compact={true}
                      />
                    ))}
                  </div>
                </CardContent>
              )}
            </Card>
          )}

          {/* Empty State */}
          {provisions.length === 0 && (
            <Card>
              <CardContent className="p-8 text-center text-gray-500">
                <div className="text-lg mb-2">No Provisions Found</div>
                <div className="text-sm">
                  No applicable provisions found for zone {propertyData.constraints?.zone}
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
