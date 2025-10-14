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
import { StructuredSeppRequirements } from './StructuredSeppRequirements';
import { ADGBuildingSeparationTable } from './ADGBuildingSeparationTable';
import { HeritageDetails } from './HeritageDetails';
import {
  assessControlRelevance,
  createFilterContext,
  type FilterResult
} from '@/lib/environmental-relevance-filter';
import { extractVersionFromPlanningAPI } from '@/lib/version-metadata-utils';
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
  description?: string;
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
  // Relevance filter fields
  requiresAction?: boolean;
  category?: 'basix' | 'environmental_overlay' | 'informational' | 'prohibition';
  provision_id?: number;
}

export interface ComplianceData {
  building_envelope: ComplianceConstraint[];
  environmental: ComplianceConstraint[];
  special_provisions: ComplianceConstraint[];
}
import type { PropertyData } from '@/lib/property-data';

interface ComplianceDashboardProps {
  propertyData: PropertyData;
  developmentType?: string;
  buildingHeight?: number | null;
  className?: string;
}

// ✓ REMOVED: Hard-coded DCP section mapping
// Now handled dynamically by API based on database content

export function ComplianceDashboard({
  propertyData,
  developmentType = 'dwelling_house',
  buildingHeight = null,
  className = ''
}: ComplianceDashboardProps) {
  const [complianceData, setComplianceData] = useState<ComplianceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [permissionStatus, setPermissionStatus] = useState<string | null>(null);

  // Slide-out panel state
  const [panelOpen, setPanelOpen] = useState(false);
  const [selectedProvision, setSelectedProvision] = useState<SelectedProvision | null>(null);

  // Structured SEPP requirements state
  const [structuredRequirements, setStructuredRequirements] = useState<any[]>([]);

  // Parking requirements state
  const [parkingData, setParkingData] = useState<{
    fullTable: string;
    relevantRow: string | null;
    description: string;
    provisionId: number;
  } | null>(null);

  // Extract NSW Planning API Special Provisions (Water Use, BASIX, etc.)
  const extractPlanningAPIProvisions = useCallback((): ComplianceConstraint[] => {
    const specialProvisionsLayer = propertyData.planningLayers?.find(
      layer => layer.layerName === 'Special Provisions'
    );

    if (!specialProvisionsLayer?.results) {
      return [];
    }

    // Create filter context
    const filterContext = createFilterContext(
      developmentType,
      propertyData.constraints?.zone || ''
    );

    const provisions: ComplianceConstraint[] = [];
    let filteredCount = 0;

    specialProvisionsLayer.results.forEach((result) => {
      const epiName = result['EPI Name'] || 'Unknown SEPP';
      const type = result.Type || '';
      const classValue = result.Class || '';
      const mapType = result['Map Type'] || '';
      const title = result.title || '';

      // Apply relevance filter
      const relevance = assessControlRelevance(result, filterContext);

      if (!relevance.isRelevant) {
        filteredCount++;
        console.log('[ComplianceDashboard] Filtered out irrelevant control:', type, '-', relevance.reason);
        return; // Skip this control
      }

      // Format the display value
      let displayValue = classValue || title;
      let displayUnit = undefined;
      let description = relevance.reason || undefined;

      // For percentage values (Water Use), remove % from value since we'll add it as unit
      if (type.includes('%') && displayValue.includes('%')) {
        displayValue = displayValue.replace('%', '');
        displayUnit = '%';
        if (!description) {
          description = 'BASIX water efficiency target - fixtures, hot water, pools must meet minimum standards';
        }
      }
      // For Climate Zones, prefix with "Class"
      else if (type.toLowerCase().includes('climate')) {
        displayValue = `Class ${classValue}`;
        if (!description) {
          if (mapType === 'CLM') {
            description = 'Climate zone for BASIX new buildings - determines insulation, glazing, thermal comfort requirements';
          } else if (mapType === 'BAL') {
            description = 'Climate zone for BASIX alterations - affects renovation thermal performance requirements';
          }
        }
      }
      // For Thermal Energy from Waste (should be filtered for residential, but keep description)
      else if (type.toLowerCase().includes('thermal') || type.toLowerCase().includes('greater sydney')) {
        if (!description) {
          description = 'Thermal energy from waste facilities prohibited in this area';
        }
      }

      // Extract version metadata from Planning API
      const versionMetadata = extractVersionFromPlanningAPI(result);

      // Create constraint for each Special Provision with metadata for full text fetching
      provisions.push({
        type: 'special',
        value: displayValue,
        unit: displayUnit,
        description: description,
        source: {
          clause: `${mapType || 'Special'} - ${type}`,
          document: epiName,
          authority_level: 'SEPP'
        },
        // Add provisions array with version metadata for badge display
        provisions: versionMetadata ? [{
          id: 0, // Planning API provisions don't have database IDs
          ref_number: `${mapType || 'Special'} - ${type}`,
          section_header: type,
          provision_text: `${type}: ${displayValue}${displayUnit || ''}`,
          document_id: epiName,
          version: versionMetadata
        }] : undefined,
        // Add metadata for fetching full SEPP text from database
        seppMetadata: {
          epiName: epiName,
          mapType: mapType,
          keywords: [
            type.toLowerCase().includes('water') ? 'water' : undefined,
            type.toLowerCase().includes('climate') ? 'climate' : undefined,
            type.toLowerCase().includes('basix') ? 'BASIX' : undefined
          ].filter(Boolean) as string[]
        },
        // Add relevance filter metadata
        requiresAction: relevance.requiresAction,
        category: relevance.category
      });
    });

    console.log(`[ComplianceDashboard] Extracted ${provisions.length} Planning API provisions (filtered ${filteredCount} irrelevant)`);
    return provisions;
  }, [propertyData, developmentType]);

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
        // Extract version metadata from Planning API
        const versionMetadata = extractVersionFromPlanningAPI(result);

        constraints.push({
          type: 'height',
          value: parseFloat(height),
          unit: 'm',
          source: {
            clause: result['Legislative Clause'] || 'Clause 4.3',
            document: result['EPI Name'] || 'Local Environmental Plan',
            authority_level: 'LEP'
          },
          // Add provisions array with version metadata for badge display
          provisions: versionMetadata ? [{
            id: 0,
            ref_number: result['Legislative Clause'] || 'Clause 4.3',
            section_header: 'Maximum Building Height',
            provision_text: `Maximum building height: ${height}m`,
            document_id: result['EPI Name'] || 'Local Environmental Plan',
            version: versionMetadata
          }] : undefined,
          lepMetadata: {
            documentId: 'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation',
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

        // Extract version metadata from Planning API
        const versionMetadata = extractVersionFromPlanningAPI(fsrResult);

        constraints.push({
          type: 'fsr',
          value: parseFloat(fsr),
          unit: ':1 sq m',
          source: {
            clause: fsrResult['Legislative Clause'] || 'Clause 4.4',
            document: fsrResult['EPI Name'] || 'Local Environmental Plan',
            authority_level: 'LEP'
          },
          // Add provisions array with version metadata for badge display
          provisions: versionMetadata ? [{
            id: 0,
            ref_number: fsrResult['Legislative Clause'] || 'Clause 4.4',
            section_header: 'Floor Space Ratio',
            provision_text: `Maximum floor space ratio: ${fsr}:1`,
            document_id: fsrResult['EPI Name'] || 'Local Environmental Plan',
            version: versionMetadata
          }] : undefined,
          lepMetadata: {
            documentId: 'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation',
            refNumber: '4.4'
          }
        });
      }
    }

    console.log('[ComplianceDashboard] Extracted', constraints.length, 'LEP constraints');
    return constraints;
  }, [propertyData]);

  // Load structured SEPP requirements (manually curated, 100% reliable)
  const loadStructuredRequirements = useCallback(async () => {
    try {
      console.log('[ComplianceDashboard] Fetching structured SEPP requirements...');

      const response = await fetch('/api/sepp/structured-requirements', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          seppId: 'sustainable_buildings_2022',
          developmentType: developmentType
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data.hasStructuredRequirements) {
          console.log('[ComplianceDashboard] Loaded structured requirements:', data.data.requirements);
          setStructuredRequirements(data.data.requirements);
        } else {
          console.log('[ComplianceDashboard] No structured requirements available');
          setStructuredRequirements([]);
        }
      }
    } catch (error) {
      console.error('[ComplianceDashboard] Failed to fetch structured requirements:', error);
      setStructuredRequirements([]);
    }
  }, [developmentType]);

  // Load compliance data from real API
  // Note: DCP constraints now come from database via API (development_controls + zone_setback_rules)
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

        // Note: DCP constraints now come from database API, not frontend extraction

        // Extract clause numbers from Planning API layers (generic per LGA)
        const planningApiClauses: string[] = [];

        // Extract clauses from all Planning API layers
        if (propertyData.planningLayers) {
          for (const layer of propertyData.planningLayers) {
            if (layer.results) {
              for (const result of layer.results) {
                // Look for Legislative Clause field (NSW Planning Portal standard)
                const clause = result['Legislative Clause'] ||
                               result['legislative_clause'] ||
                               result['Clause'] ||
                               result['clause'];

                if (clause && typeof clause === 'string') {
                  planningApiClauses.push(clause);
                  console.log(`[ComplianceDashboard] Extracted clause ${clause} from ${layer.layerName}`);
                }
              }
            }
          }
        }

        // Remove duplicates
        const uniqueClauses = Array.from(new Set(planningApiClauses));

        console.log('[ComplianceDashboard] Planning API clauses for SEPP override matching:', uniqueClauses);

        // Call real API endpoint for database provisions
        const response = await fetch('/api/compliance/constraints', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            address: propertyData.address,
            zone: propertyData.constraints.zone,
            lga: propertyData.constraints?.lga,
            developmentType: developmentType,
            propId: propertyData.propId,
            planningApiClauses: uniqueClauses  // Pass extracted clauses (generic per LGA)
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

        // Set permission status from API response
        if (apiResponse.data.permission_status) {
          setPermissionStatus(apiResponse.data.permission_status);
          console.log('[ComplianceDashboard] Permission status:', apiResponse.data.permission_status);
        }

        // Helper function to deduplicate constraints by provision_id or clause
        const deduplicateConstraints = (constraints: ComplianceConstraint[]) => {
          const seen = new Set<string>();
          return constraints.filter(c => {
            // Create unique key from provision_id or clause + document
            const key = c.provision_id
              ? `id-${c.provision_id}`
              : `${c.source.clause}-${c.source.document}`;

            if (seen.has(key)) {
              console.log('[ComplianceDashboard] Removing duplicate:', c.type, c.source.clause);
              return false;
            }
            seen.add(key);
            return true;
          });
        };

        // Use Planning API provisions + LEP constraints + Database DCP constraints
        // Note: dcpConstraints are just placeholders, real DCP data comes from API
        setComplianceData({
          building_envelope: deduplicateConstraints([
            ...lepConstraints,  // LEP Height/FSR from Planning API
            ...(apiResponse.data.building_envelope || [])  // Database provisions (includes DCP)
          ]),
          environmental: deduplicateConstraints([
            ...(apiResponse.data.environmental || [])  // Database provisions (includes DCP)
          ]),
          special_provisions: deduplicateConstraints([
            ...planningAPIProvisions,  // ONLY Planning API SEPP provisions
            ...(apiResponse.data.special_provisions || [])  // Database provisions (includes DCP)
          ])
        });

        // Fetch structured SEPP requirements if SEPP provisions exist
        if (planningAPIProvisions.length > 0) {
          await loadStructuredRequirements();
        }

        // Fetch parking requirements
        try {
          const parkingResponse = await fetch('/api/dcp/parking', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              developmentType,
              zone: propertyData.constraints.zone,
              lga: propertyData.constraints?.lga
            })
          });

          if (parkingResponse.ok) {
            const parkingResult = await parkingResponse.json();
            if (parkingResult.success) {
              console.log('[ComplianceDashboard] Loaded parking requirements:', parkingResult.data);
              setParkingData({
                fullTable: parkingResult.data.fullTable,
                relevantRow: parkingResult.data.relevantRow,
                description: parkingResult.data.description,
                provisionId: parkingResult.data.provisionId
              });
            }
          }
        } catch (parkingErr) {
          console.error('[ComplianceDashboard] Failed to load parking requirements:', parkingErr);
          // Don't fail the whole dashboard if parking fails
        }

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
  }, [propertyData, developmentType, extractPlanningAPIProvisions, extractLEPConstraints]);

  // Handler for opening slide-out panel
  const handleViewProvision = useCallback(async (constraint: ComplianceConstraint) => {
    console.log('[ComplianceDashboard] Opening panel for:', constraint);

    // If constraint has REAL provisions (not synthetic id:0 placeholders), use them directly
    const hasRealProvisions = constraint.provisions &&
      constraint.provisions.length > 0 &&
      constraint.provisions.some(p => p.id > 0);

    if (hasRealProvisions) {
      setSelectedProvision({
        constraint,
        provisions: constraint.provisions
      });
      setPanelOpen(true);
      return;
    }

    // If SEPP with metadata, fetch full text
    if (constraint.seppMetadata) {
      try {
        const response = await fetch('/api/sepp/full-text', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            epiName: constraint.seppMetadata.epiName,
            keywords: constraint.seppMetadata.keywords,
            mapType: constraint.seppMetadata.mapType,
            developmentType: developmentType  // ✅ Pass development type for context-aware filtering
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
    // If SEPP override with provision_id, fetch by ID
    else if (constraint.source.authority_level === 'SEPP' && constraint.provision_id) {
      try {
        console.log('[ComplianceDashboard] Fetching SEPP override by provision ID:', constraint.provision_id);

        const response = await fetch('/api/sepp/full-text', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            provisionId: constraint.provision_id
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
        console.error('[ComplianceDashboard] Failed to fetch SEPP override provision:', error);
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
      // Fallback: Try to fetch by clause number and document type
      console.log('[ComplianceDashboard] No metadata found, attempting fallback fetch for:', {
        clause: constraint.source.clause,
        document: constraint.source.document,
        authorityLevel: constraint.source.authority_level
      });

      try {
        // Try generic provision fetch by clause
        const response = await fetch('/api/provisions/search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            clause: constraint.source.clause,
            document: constraint.source.document,
            authorityLevel: constraint.source.authority_level
          })
        });

        if (response.ok) {
          const data = await response.json();
          if (data.success && data.provisions && data.provisions.length > 0) {
            setSelectedProvision({
              constraint,
              provisions: data.provisions
            });
            setPanelOpen(true);
            return;
          }
        }
      } catch (error) {
        console.error('[ComplianceDashboard] Fallback fetch failed:', error);
      }

      // If all else fails, show with empty provisions
      console.warn('[ComplianceDashboard] No provisions found for constraint:', constraint);
      setSelectedProvision({
        constraint,
        provisions: []
      });
      setPanelOpen(true);
    }
  }, [developmentType]);  // ✅ Add developmentType to dependencies

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
          {/* Permission Status Badge */}
          {permissionStatus && (
            <div className="mb-4">
              {permissionStatus === 'exempt' && (
                <div className="bg-green-100 border border-green-300 rounded-lg px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">✓</span>
                    <div>
                      <div className="font-semibold text-green-800">Exempt Development</div>
                      <div className="text-sm text-green-700">
                        No Development Application required if standards are met
                      </div>
                    </div>
                  </div>
                </div>
              )}
              {permissionStatus === 'complying' && (
                <div className="bg-blue-100 border border-blue-300 rounded-lg px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">📋</span>
                    <div>
                      <div className="font-semibold text-blue-800">Complying Development</div>
                      <div className="text-sm text-blue-700">
                        Complying Development Certificate (CDC) pathway available if standards are met
                      </div>
                    </div>
                  </div>
                </div>
              )}
              {permissionStatus === 'consent_required' && (
                <div className="bg-orange-100 border border-orange-300 rounded-lg px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">⚠</span>
                    <div>
                      <div className="font-semibold text-orange-800">Development Approval Required</div>
                      <div className="text-sm text-orange-700">
                        Full Development Application (DA) required
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Quick Reference Strip */}
          <div className="bg-gray-50 px-4 py-2 rounded-lg text-sm font-mono">
            {getQuickReference()}
          </div>
        </CardContent>
      </Card>

      {/* SEPP Overlay Indicator removed - SEPP cards shown inline below */}

      {/* Flex Layout: Constraints List + Slide-Out Panel */}
      <div className="flex gap-4" style={{ minHeight: 'calc(100vh - 400px)' }}>
        {/* Left: Constraints List (expands/contracts with panel) */}
        <div className={`
          transition-all duration-300 ease-in-out
          ${panelOpen ? 'w-[40%]' : 'w-full'}
          space-y-4
        `}>

      {/* SEPP Special Provisions Section - PRIORITY */}
      {complianceData?.special_provisions &&
       complianceData.special_provisions.filter(p => p.source.authority_level === 'SEPP').length > 0 && (() => {
        const seppProvisions = complianceData.special_provisions.filter(p => p.source.authority_level === 'SEPP');
        const actionRequired = seppProvisions.filter(p => p.requiresAction !== false);
        const informational = seppProvisions.filter(p => p.requiresAction === false);

        return (
        <Card className="border-orange-200">
          <CardHeader className="bg-orange-50">
            <CardTitle className="flex items-center gap-2">
              <span className="text-xl">🟥</span>
              SEPP Special Provisions
              {informational.length > 0 && (
                <span className="text-sm font-normal text-gray-600">
                  ({actionRequired.length} require action, {informational.length} informational)
                </span>
              )}
            </CardTitle>
            <p className="text-sm text-gray-600 mt-1">
              State Environmental Planning Policies - Highest legal precedence
            </p>
          </CardHeader>
          <CardContent className="pt-4">
            {/* Structured Requirements (100% Reliable) */}
            {structuredRequirements.length > 0 && (
              <div className="mb-6">
                <div className="mb-3 flex items-center gap-2">
                  <span className="text-sm font-semibold text-purple-900">
                    📋 Actionable Requirements
                  </span>
                  <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">
                    100% Reliable
                  </span>
                </div>
                <StructuredSeppRequirements
                  requirements={structuredRequirements}
                  onViewFullText={async (provisionId) => {
                    // Fetch full provision text from database by provision ID
                    try {
                      const response = await fetch(`/api/provisions/${provisionId}/complete`);
                      if (response.ok) {
                        const data = await response.json();
                        if (data.success && data.provision) {
                          setSelectedProvision({
                            constraint: {
                              type: 'special',
                              value: 'SEPP Requirements',
                              source: {
                                clause: data.provision.ref_number || 'Schedule 1 & 2',
                                document: data.provision.document_id || 'SEPP (Sustainable Buildings) 2022',
                                authority_level: 'SEPP'
                              }
                            },
                            provisions: [{
                              id: data.provision.id,
                              ref_number: data.provision.ref_number,
                              section_header: data.provision.section_header || 'BASIX Requirements',
                              provision_text: data.provision.provision_text,
                              document_id: data.provision.document_id
                            }]
                          });
                          setPanelOpen(true);
                        }
                      }
                    } catch (error) {
                      console.error('[ComplianceDashboard] Failed to fetch structured requirement provision:', error);
                    }
                  }}
                  compact={true}
                />
              </div>
            )}

            {/* Action Required Controls - Only show if NO structured requirements */}
            {actionRequired.length > 0 && structuredRequirements.length === 0 && (
              <div className="mb-6">
                <div className="mb-2 text-sm font-semibold text-orange-900">
                  Action Required:
                </div>
                <div className="space-y-3">
                  {actionRequired.map((constraint, index) => (
                    <ConstraintCard
                      key={`sepp-action-${index}`}
                      constraint={constraint}
                      onViewDetails={handleViewProvision}
                      compact={true}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Informational Controls - Only show if NO structured requirements */}
            {informational.length > 0 && structuredRequirements.length === 0 && (
              <div>
                <div className="mb-2 text-sm font-semibold text-blue-700 flex items-center gap-2">
                  <span>Informational Only:</span>
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded font-normal">
                    No action required
                  </span>
                </div>
                <div className="space-y-3 opacity-75">
                  {informational.map((constraint, index) => (
                    <ConstraintCard
                      key={`sepp-info-${index}`}
                      constraint={constraint}
                      onViewDetails={handleViewProvision}
                      compact={true}
                    />
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
        );
      })()}

      {/* ADG Building Separation Standards (Multi-Dwelling Only) */}
      {buildingHeight && buildingHeight > 0 && (
        developmentType === 'multi_dwelling' ||
        developmentType === 'residential_flat' ||
        developmentType === 'shop_top_housing'
      ) && (
        <Card className="border-red-300">
          <CardHeader className="bg-red-50">
            <CardTitle className="flex items-center gap-2">
              <span className="text-xl">🟥</span>
              NSW Apartment Design Guide - Building Separation
            </CardTitle>
            <p className="text-sm text-gray-600 mt-1">
              Statutory standards under SEPP (Housing) 2021
            </p>
          </CardHeader>
          <CardContent className="pt-4">
            <ADGBuildingSeparationTable
              buildingHeight={buildingHeight}
              developmentType={developmentType}
            />
          </CardContent>
        </Card>
      )}

      {/* Heritage Details (LEP Level - Between ADG and LEP Envelope) */}
      <HeritageDetails
        heritage={propertyData.heritage}
        propertyGeometry={propertyData.geometry}
        lga={propertyData.constraints?.lga}
      />

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

      {/* DCP Parking Requirements */}
      {parkingData && (
        <Card className="border-green-200">
          <CardHeader className="bg-green-50">
            <CardTitle className="flex items-center gap-2">
              <span className="text-xl">🅿️</span>
              Parking Requirements
            </CardTitle>
            <p className="text-sm text-gray-600 mt-1">
              Marrickville DCP 2011 - Section 2.10
            </p>
          </CardHeader>
          <CardContent className="pt-4">
            <div className="bg-white border rounded-lg p-4">
              <div className="text-sm text-gray-700 mb-3">
                <strong>Development Type:</strong> {developmentType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </div>
              <div className="text-sm text-gray-600 mb-4">
                {parkingData.description}
              </div>

              {parkingData.relevantRow && (
                <div className="bg-gray-50 rounded p-3 mb-3 overflow-x-auto">
                  <div
                    className="text-xs"
                    dangerouslySetInnerHTML={{ __html: parkingData.relevantRow }}
                  />
                </div>
              )}

              <button
                onClick={() => {
                  // Open full table in slide-out panel
                  setSelectedProvision({
                    constraint: {
                      type: 'special',
                      value: 'Parking Requirements',
                      source: {
                        clause: 'Table 1',
                        document: 'Marrickville DCP 2011 - Section 2.10',
                        authority_level: 'DCP'
                      }
                    },
                    provisions: [{
                      id: parkingData.provisionId,
                      ref_number: 'Table 1',
                      section_header: 'Car Parking Requirements',
                      provision_text: parkingData.fullTable,
                      document_id: 'Marrickville_DCP_2011__2_10_Parking'
                    }]
                  });
                  setPanelOpen(true);
                }}
                className="text-sm text-blue-600 hover:text-blue-700 underline"
              >
                View Full Parking Table
              </button>
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
          transition-all duration-300 ease-in-out overflow-hidden
          ${panelOpen ? 'w-[60%] opacity-100' : 'w-0 opacity-0'}
        `}>
          {panelOpen && selectedProvision && (
            <LegalTextPanel
              key={`provision-${selectedProvision.constraint.provision_id || selectedProvision.constraint.source.clause}`}
              selectedProvision={selectedProvision}
              onClose={() => setPanelOpen(false)}
            />
          )}
        </div>
      </div>
    </div>
  );
}// Trigger recompile
