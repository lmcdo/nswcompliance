'use client';

/**
 * State Level Controls Component
 * Displays SEPP, LEP, and ADG requirements in a unified view
 * Separated from DCP (council-level) provisions
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronRight, Scale, Building2, Car, FileImage } from 'lucide-react';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { AuthorityColors } from '@/lib/design-tokens';
import { StructuredSeppRequirements } from './StructuredSeppRequirements';
import { LandUseZoningCard } from './LandUseZoningCard';
import { MinimumLotSizeCard } from './MinimumLotSizeCard';
import { ADGBuildingSeparationTable } from './ADGBuildingSeparationTable';
import { ADGSummaryCard } from './ADGSummaryCard';
import { HousingSEPPEligibilityCard } from './HousingSEPPEligibilityCard';
import { NearbyTransportCard } from '../tod/NearbyTransportCard';

interface StateLevelControlsProps {
  propertyData: any;
  developmentType: string;
  buildingHeight?: number;
}

const APARTMENT_DEV_TYPES = [
  'multi_dwelling_housing',
  'residential_flat_building',
  'shop_top_housing',
  'boarding_house',
  'mixed_use'
];

// Zones that permit apartment developments (including LMR reforms)
// ADG should show for these zones regardless of development type selection
const APARTMENT_PERMITTING_ZONES = [
  'R1',   // General Residential - now permits low-rise apartments under LMR reforms (July 2024)
  'R2',   // Low Density Residential - now permits low-rise apartments under LMR reforms (July 2024)
  'R3',   // Medium Density Residential
  'R4',   // High Density Residential
  'B1',   // Neighbourhood Centre
  'B2',   // Local Centre
  'B3',   // Commercial Core
  'B4',   // Mixed Use
  'B5',   // Business Development
  'B6',   // Enterprise Corridor
  'MU1',  // Mixed Use (new naming)
  'E1',   // Local Centre (new naming)
  'E2',   // Commercial Centre (new naming)
];

export function StateLevelControls({
  propertyData,
  developmentType,
  buildingHeight
}: StateLevelControlsProps) {
  const [structuredRequirements, setStructuredRequirements] = useState<any[]>([]);
  const [adgRequirements, setAdgRequirements] = useState<any[]>([]);
  const [loadingSepp, setLoadingSepp] = useState(false);
  const [loadingAdg, setLoadingAdg] = useState(false);
  const [nearbyTransport, setNearbyTransport] = useState<any[]>([]);
  const [transportLoading, setTransportLoading] = useState(false);
  const [viewingPdfPage, setViewingPdfPage] = useState<{pageNumber: number, url: string, label: string} | null>(null);
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({
    sepp: false,
    lep: false,
    lmr: false,  // Housing SEPP LMR section
    adg: false,
    tod: false // TOD expanded by default when shown
  });

  const isApartmentDevelopment = APARTMENT_DEV_TYPES.includes(developmentType);

  // Toggle section collapse
  const toggleSection = (section: string) => {
    setCollapsedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // SEPP ID mapping: Planning Portal → Database
  // Note: Only sustainable_buildings_2022 currently has structured requirements in DB
  // Housing SEPP uses separate sepp_adg_requirements table
  // Others detected but no structured data available yet
  const SEPP_MAPPING: Record<string, string> = {
    'SEPP_HOUSING_2021': 'housing_2021',
    'SEPP_65': 'housing_2021',  // Old numbering, same SEPP
    'SEPP_SUSTAINABLE_BUILDINGS': 'sustainable_buildings_2022',
    'SEPP_SUSTAINABLE_BUILDINGS_2022': 'sustainable_buildings_2022',
    'SEPP_RESILIENCE_HAZARDS_2021': 'resilience_hazards_2021',
    'SEPP_PLANNING_SYSTEMS_2021': 'planning_systems_2021',
    'SEPP_TRANSPORT_INFRASTRUCTURE_2021': 'transport_infrastructure_2021',
    'SEPP_BIODIVERSITY_CONSERVATION_2017': 'biodiversity_conservation_2017',
    'SEPP_PRIMARY_PRODUCTION_2021': 'primary_production_2021',
    'SEPP_INDUSTRY_EMPLOYMENT_2021': 'industry_employment_2021',
    'SEPP_EXEMPT_COMPLYING_2008': 'exempt_complying_2008',
  };

  // Load ADG requirements when SEPP Housing 2021 detected
  const loadADGRequirements = useCallback(async () => {
    if (!developmentType) return;

    const applicableSepps = propertyData?.constraints?.applicableSepps || [];
    console.log('[StateLevelControls] Applicable SEPPs from portal:', applicableSepps);

    // Check if Housing SEPP applies
    const hasHousingSEPP = applicableSepps.some((sepp: string) => 
      sepp === 'SEPP_HOUSING_2021' || sepp === 'SEPP_65'
    );

    if (!hasHousingSEPP) {
      setAdgRequirements([]);
      return;
    }

    setLoadingAdg(true);
    try {
      console.log('[StateLevelControls] Fetching ADG requirements (Housing SEPP detected)');
      const response = await fetch(`/api/adg/requirements`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data) {
          // Filter high-value requirements
          const keyRequirements = data.data.filter((r: any) => 
            ['4A-1', '4D-1', '4E-1', '4B-1', '4C-1', '4F-1', '4G-1', '3F-1'].includes(r.criteriaId)
          );
          setAdgRequirements(keyRequirements);
          console.log(`[StateLevelControls] Loaded ${keyRequirements.length} ADG requirements`);
        }
      }
    } catch (error) {
      console.error('[StateLevelControls] Failed to fetch ADG requirements:', error);
      setAdgRequirements([]);
    } finally {
      setLoadingAdg(false);
    }
  }, [developmentType, propertyData]);

  // Load structured SEPP requirements (dynamic based on portal detection)
  const loadStructuredRequirements = useCallback(async () => {
    if (!developmentType || !propertyData) return;

    const applicableSepps = propertyData?.constraints?.applicableSepps || [];
    console.log('[StateLevelControls] Detected SEPPs:', applicableSepps);

    // Map portal SEPP IDs to database IDs
    const dbSeppIds = applicableSepps
      .map((portalId: string) => SEPP_MAPPING[portalId])
      .filter(Boolean);

    if (dbSeppIds.length === 0) {
      console.log('[StateLevelControls] No structured SEPPs detected');
      setStructuredRequirements([]);
      return;
    }

    setLoadingSepp(true);
    try {
      // Fetch requirements for each detected SEPP
      const results: any[] = [];
      for (const seppId of dbSeppIds) {
        console.log(`[StateLevelControls] Fetching requirements for ${seppId}`);
        const response = await fetch('/api/sepp/structured-requirements', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            seppId,
            developmentType: developmentType
          })
        });

        if (response.ok) {
          const data = await response.json();
          if (data.success && data.data.hasStructuredRequirements) {
            results.push(...data.data.requirements);
          }
        }
      }

      setStructuredRequirements(results);
      console.log(`[StateLevelControls] Loaded ${results.length} structured requirements`);
    } catch (error) {
      console.error('[StateLevelControls] Failed to fetch SEPP requirements:', error);
      setStructuredRequirements([]);
    } finally {
      setLoadingSepp(false);
    }
  }, [developmentType, propertyData]);

  useEffect(() => {
    loadStructuredRequirements();
  }, [loadStructuredRequirements]);

  useEffect(() => {
    loadADGRequirements();
  }, [loadADGRequirements]);


  // Extract property coordinates for transport proximity
  // Convert Web Mercator (x, y) to WGS84 (lat, lng) if needed
  const getCoordinates = () => {
    // Try WGS84 coordinates first
    if (propertyData?.geometry?.centroid?.lat) {
      return { lat: propertyData.geometry.centroid.lat, lng: propertyData.geometry.centroid.lng };
    }
    if (propertyData?.centroid?.lat) {
      return { lat: propertyData.centroid.lat, lng: propertyData.centroid.lng };
    }
    if (propertyData?.location?.lat) {
      return { lat: propertyData.location.lat, lng: propertyData.location.lng };
    }
    // Convert from Web Mercator if we have x/y
    if (propertyData?.geometry?.x && propertyData?.geometry?.y) {
      const x = propertyData.geometry.x;
      const y = propertyData.geometry.y;
      const lng = (x / 20037508.34) * 180;
      const lat = (Math.atan(Math.exp((y / 20037508.34) * Math.PI)) * 360 / Math.PI) - 90;
      return { lat, lng };
    }
    return { lat: undefined, lng: undefined };
  };
  const { lat: propertyLat, lng: propertyLng } = getCoordinates();

  // Fetch nearby transport data
  useEffect(() => {
    if (!propertyLat || !propertyLng) {
      setNearbyTransport([]);
      return;
    }

    const fetchTransport = async () => {
      setTransportLoading(true);
      try {
        const response = await fetch(
          `/api/tod/transport-autocomplete?lat=${propertyLat}&lng=${propertyLng}&limit=15`
        );
        if (response.ok) {
          const data = await response.json();
          // Filter to stops within 1km
          const nearby = (data.suggestions || []).filter((s: any) => s.distance <= 1000);
          setNearbyTransport(nearby);
        }
      } catch (err) {
        console.error('Failed to fetch transport:', err);
        setNearbyTransport([]);
      } finally {
        setTransportLoading(false);
      }
    };

    fetchTransport();
  }, [propertyLat, propertyLng]);

  // Extract zone and lot size data from propertyData
  const zone = propertyData?.constraints?.zone;
  const zoneDescription = propertyData?.constraints?.zoneDescription;
  const lga = propertyData?.constraints?.lga || 'Inner West';

  // Extract lot dimensions for Housing SEPP LMR eligibility
  const propertyAreaStr = propertyData?.propertyArea;
  const lotSize = propertyAreaStr
    ? parseFloat(propertyAreaStr.replace(/[^0-9.]/g, ''))
    : propertyData?.geometry?.area;

  // Lot width - from geometry calculations or property data
  const lotWidth = propertyData?.geometry?.frontageWidth
    || propertyData?.geometry?.estimatedWidth
    || propertyData?.constraints?.lotWidth
    || 15; // Default estimate if not available

  // Get station distance for TOD eligibility
  const stationDistance = propertyData?.constraints?.todPrecinct?.stationDistance
    || nearbyTransport.find(s => s.type === 'heavy_rail')?.distance;

  // Check if property is in LMR area (residential zone)
  // Zone may include colon (e.g., "R2: Low Density") - strip non-alphanumeric chars
  const zoneCode = zone?.split(' ')[0]?.replace(/[^A-Z0-9]/gi, '')?.toUpperCase() || '';
  const isLMRArea = ['R1', 'R2', 'R3', 'R4'].includes(zoneCode);

  // Show Housing SEPP LMR section for residential zones
  const showHousingSEPPSection = isLMRArea && lotSize && lotWidth;

  // Show ADG based on SEPP Housing 2021 detection (dynamic from planning portal)
  const applicableSepps = propertyData?.constraints?.applicableSepps || [];
  const hasHousingSEPP = applicableSepps.some((sepp: string) => 
    sepp === 'SEPP_HOUSING_2021' || sepp === 'SEPP_65'
  );
  
  // Show ADG section if Housing SEPP applies OR if it's apartment development OR if we fetched ADG requirements
  const showADGSection = hasHousingSEPP || isApartmentDevelopment || adgRequirements.length > 0;

  // Get land zoning layer data
  const landZoningLayer = propertyData?.planningLayers?.find(
    (layer: any) => layer.layerName === 'Land Zoning Map'
  );
  const zoneResult = landZoningLayer?.results?.[0];

  // Get lot size layer data
  const lotSizeLayer = propertyData?.planningLayers?.find(
    (layer: any) => layer.layerName === 'Lot Size Map' || layer.layerName === 'Minimum Lot Size'
  );
  const lotSizeResult = lotSizeLayer?.results?.[0];
  const minimumLotSize = lotSizeResult?.['Minimum Lot Size'] || lotSizeResult?.['Lot Size'];

  // Extract SEPP Sustainable Buildings layers from Planning Portal
  const sustainableBuildingsLayers = propertyData?.planningLayers?.filter(
    (layer: any) => layer.layerName?.includes('Sustainable Buildings') ||
                   layer.results?.some((r: any) => r['EPI Name']?.includes('Sustainable Buildings'))
  ) || [];

  // Parse the layer data into meaningful info
  const getSustainableBuildingsInfo = () => {
    const info: { waterTarget?: string; climateZone?: string; basixArea?: string } = {};

    for (const layer of sustainableBuildingsLayers) {
      for (const result of layer.results || []) {
        const mapType = result['Map Type'];
        const classValue = result['Class'];
        const label = result['Label'];

        if (mapType === 'WAT' && classValue) {
          info.waterTarget = classValue; // e.g., "40%"
        }
        if (mapType === 'CLM' && classValue) {
          info.climateZone = classValue; // e.g., "56"
        }
        if (mapType === 'BAL' && (classValue || label)) {
          info.basixArea = `Area ${classValue}${label ? ` (${label})` : ''}`; // e.g., "Area 5 (INNER WEST)"
        }
      }
    }
    return info;
  };

  const sustainableInfo = getSustainableBuildingsInfo();

  // Check for designated TOD layers from NSW Planning Portal (authoritative source)
  const todSitesLayer = propertyData?.planningLayers?.find(
    (layer: any) => layer.layerName === 'Transport Oriented Development Sites Map'
  );
  const acceleratedTodLayer = propertyData?.planningLayers?.find(
    (layer: any) => layer.layerName === 'Accelerated TOD Precincts Rezoning Areas Map'
  );
  const isInDesignatedTOD = !!(todSitesLayer?.results?.length || acceleratedTodLayer?.results?.length);

  // Check if any nearby transport qualifies for parking reductions (regulatory thresholds)
  const hasQualifyingTransport = nearbyTransport.some(stop => {
    if (stop.type === 'heavy_rail' && stop.distance <= 800) return true;
    if (stop.type === 'light_rail' && stop.distance <= 600) return true;
    if (stop.type === 'bus' && stop.distance <= 400 &&
        (stop.frequency === 'high' || stop.frequency === 'medium')) return true;
    return false;
  });

  // Show TOD section if property is in designated TOD OR has qualifying transport nearby
  const showTODSection = isInDesignatedTOD || hasQualifyingTransport;

  if (!propertyData) {
    return (
      <div className="bg-white border rounded-lg p-8 text-center text-gray-500">
        Select a property to view State-level controls
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* SEPP Section */}
      <Card className={`${AuthorityColors.SEPP.border.replace('500', '200')} ${AuthorityColors.SEPP.bg}/30`}>
        <CardHeader
          className={`cursor-pointer ${AuthorityColors.SEPP.hover.replace('100', '100/50')} transition-colors`}
          onClick={() => toggleSection('sepp')}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {collapsedSections.sepp ? (
                <ChevronRight className={`h-5 w-5 ${AuthorityColors.SEPP.text.replace('700', '600')}`} />
              ) : (
                <ChevronDown className={`h-5 w-5 ${AuthorityColors.SEPP.text.replace('700', '600')}`} />
              )}
              <Scale className={`h-5 w-5 ${AuthorityColors.SEPP.text.replace('700', '600')}`} />
              <CardTitle className={`text-lg ${AuthorityColors.SEPP.text.replace('700', '900')}`}>SEPP Requirements</CardTitle>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={`${AuthorityColors.SEPP.bg.replace('50', '100')} ${AuthorityColors.SEPP.text.replace('700', '800')}`}>State Policy</Badge>
            </div>
          </div>
          <p className={`text-sm ${AuthorityColors.SEPP.text} mt-1 ml-7`}>
            State Environmental Planning Policies - Mandatory requirements
          </p>
        </CardHeader>
        {!collapsedSections.sepp && (
          <CardContent className="pt-0 space-y-4">
            {/* Show ALL detected SEPPs from Planning Portal */}
            {propertyData?.constraints?.applicableSepps && propertyData.constraints.applicableSepps.length > 0 && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-4">
                <div className="text-sm font-semibold text-purple-900 mb-2">
                  Applicable State Policies (from Planning Portal)
                </div>
                <div className="flex flex-wrap gap-2">
                  {propertyData.constraints.applicableSepps.map((sepp: string) => (
                    <div key={sepp} className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded border border-purple-300">
                      {sepp.replace(/_/g, ' ')}
                    </div>
                  ))}
                </div>
                <div className="text-xs text-purple-700 mt-2">
                  Structured requirements available for: Sustainable Buildings, Housing (ADG)
                </div>
              </div>
            )}
            
            {/* Planning Portal Source Layers - Purple shades for cohesion with left column Special Provisions */}
            {(sustainableInfo.waterTarget || sustainableInfo.climateZone || sustainableInfo.basixArea) && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                <div className="text-xs font-semibold text-purple-800 mb-2">
                  📍 Applied from NSW Planning Portal
                </div>
                <div className="flex flex-wrap gap-2">
                  {sustainableInfo.waterTarget && (
                    <div className="text-xs bg-purple-100 text-purple-900 px-2 py-1 rounded border-l-4 border-purple-400">
                      💧 Water Target: <span className="font-bold">{sustainableInfo.waterTarget}</span>
                    </div>
                  )}
                  {sustainableInfo.climateZone && (
                    <div className="text-xs bg-purple-100 text-purple-900 px-2 py-1 rounded border-l-4 border-purple-500">
                      🌡️ Climate Zone: <span className="font-bold">{sustainableInfo.climateZone}</span>
                    </div>
                  )}
                  {sustainableInfo.basixArea && (
                    <div className="text-xs bg-purple-100 text-purple-900 px-2 py-1 rounded border-l-4 border-purple-600">
                      🏠 BASIX: <span className="font-bold">{sustainableInfo.basixArea}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Structured Requirements */}
            {loadingSepp ? (
              <div className="animate-pulse space-y-2">
                <div className={`h-4 ${AuthorityColors.SEPP.bg.replace('50', '200')} rounded w-3/4`}></div>
                <div className={`h-4 ${AuthorityColors.SEPP.bg.replace('50', '200')} rounded w-1/2`}></div>
              </div>
            ) : structuredRequirements.length > 0 ? (
              <StructuredSeppRequirements
                requirements={structuredRequirements}
                compact
              />
            ) : (
              <p className="text-sm text-gray-500 italic">
                No structured SEPP requirements for this development type
              </p>
            )}

            {/* BASIX Energy & Thermal - Complex Calculations */}
            {sustainableInfo.basixArea && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <div className="text-2xl">⚡</div>
                  <div className="flex-1">
                    <div className="font-semibold text-purple-900">BASIX Energy & Thermal Requirements</div>
                    <p className="text-sm text-purple-800 mt-1">
                      Energy efficiency and thermal comfort targets for {sustainableInfo.basixArea} require
                      detailed calculation through the official BASIX Certificate tool. Targets vary by
                      building type, orientation, and materials.
                    </p>
                    <div className="flex flex-wrap gap-2 mt-3">
                      <a
                        href="https://www.planningportal.nsw.gov.au/development-and-assessment/basix"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs bg-purple-600 text-white px-3 py-1.5 rounded hover:bg-purple-700 transition-colors"
                      >
                        🔗 Get BASIX Certificate
                      </a>
                      <a
                        href="https://www.planningportal.nsw.gov.au/basix/thermal-performance/simulation-method/accredited-assessors"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs bg-white text-purple-700 border border-purple-300 px-3 py-1.5 rounded hover:bg-purple-50 transition-colors"
                      >
                        👤 Find BASIX Assessor
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        )}
      </Card>

      {/* LEP Section */}
      <Card className={`${AuthorityColors.LEP.border.replace('500', '200')} ${AuthorityColors.LEP.bg}/30`}>
        <CardHeader
          className={`cursor-pointer ${AuthorityColors.LEP.hover.replace('100', '100/50')} transition-colors`}
          onClick={() => toggleSection('lep')}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {collapsedSections.lep ? (
                <ChevronRight className={`h-5 w-5 ${AuthorityColors.LEP.text.replace('700', '600')}`} />
              ) : (
                <ChevronDown className={`h-5 w-5 ${AuthorityColors.LEP.text.replace('700', '600')}`} />
              )}
              <Building2 className={`h-5 w-5 ${AuthorityColors.LEP.text.replace('700', '600')}`} />
              <CardTitle className={`text-lg ${AuthorityColors.LEP.text.replace('700', '900')}`}>LEP Controls</CardTitle>
            </div>
            <Badge className={`${AuthorityColors.LEP.bg.replace('50', '100')} ${AuthorityColors.LEP.text.replace('700', '800')}`}>Local Environmental Plan</Badge>
          </div>
          <p className={`text-sm ${AuthorityColors.LEP.text} mt-1 ml-7`}>
            Zoning, land use permissibility, and lot size requirements
          </p>
        </CardHeader>
        {!collapsedSections.lep && (
          <CardContent className="pt-0 space-y-4">
            {/* Land Use Zoning */}
            {zone && (
              <LandUseZoningCard
                zone={zone}
                zoneDescription={zoneDescription}
                lga={lga}
                legislationUrl={zoneResult?.['legislationUrl']}
                epiName={zoneResult?.['EPI Name']}
                amendment={zoneResult?.['Amendment']}
                legislativeClause={zoneResult?.['Legislative Clause']}
              />
            )}

            {/* Minimum Lot Size */}
            {minimumLotSize && (
              <MinimumLotSizeCard
                minimumSize={parseFloat(minimumLotSize)}
                unit={lotSizeResult?.['Units'] || 'm²'}
                epiName={lotSizeResult?.['EPI Name']}
                amendment={lotSizeResult?.['Amendment']}
                legislativeClause={lotSizeResult?.['Legislative Clause'] || 'Clause 4.1'}
              />
            )}

            {!zone && !minimumLotSize && (
              <p className="text-sm text-gray-500 italic">
                No LEP data available for this property
              </p>
            )}
          </CardContent>
        )}
      </Card>

      {/* Housing SEPP LMR Section - Shows for residential zones with lot data */}
      {showHousingSEPPSection && (
        <Card className="border-emerald-200 bg-emerald-50/30">
          <CardHeader
            className="cursor-pointer hover:bg-emerald-100/50 transition-colors"
            onClick={() => toggleSection('lmr')}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {collapsedSections.lmr ? (
                  <ChevronRight className="h-5 w-5 text-emerald-600" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-emerald-600" />
                )}
                <Building2 className="h-5 w-5 text-emerald-600" />
                <CardTitle className="text-lg text-emerald-900">Multiple Occupancy Options</CardTitle>
              </div>
              <Badge className="bg-emerald-100 text-emerald-800">NSW Reforms</Badge>
            </div>
            <p className="text-sm text-emerald-700 mt-1 ml-7">
              Duplexes, townhouses, apartments and other housing options under Low and Mid-Rise reforms
            </p>
          </CardHeader>
          {!collapsedSections.lmr && (
            <CardContent className="pt-0">
              <HousingSEPPEligibilityCard
                zoneCode={zone}
                lotSize={lotSize}
                lotWidth={lotWidth}
                stationDistance={stationDistance}
                isLMRArea={isLMRArea}
              />
            </CardContent>
          )}
        </Card>
      )}

      {/* ADG Section - Shows for apartment zones OR apartment development types */}
      {showADGSection && (
        <Card className="border-purple-200 bg-purple-50/30">
          <CardHeader
            className="cursor-pointer hover:bg-purple-100/50 transition-colors"
            onClick={() => toggleSection('adg')}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {collapsedSections.adg ? (
                  <ChevronRight className="h-5 w-5 text-purple-600" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-purple-600" />
                )}
                <Building2 className="h-5 w-5 text-purple-600" />
                <CardTitle className="text-lg text-purple-900">Apartment Design Guide</CardTitle>
              </div>
              <Badge className="bg-purple-100 text-purple-800">SEPP (Housing) 2021</Badge>
            </div>
            <p className="text-sm text-purple-700 mt-1 ml-7">
              Statutory Design Criteria for apartment developments
            </p>
          </CardHeader>
          {!collapsedSections.adg && (
            <CardContent className="pt-0">
              {/* Dynamic ADG Requirements from Planning Portal SEPP Detection */}
              {loadingAdg ? (
                <div className="animate-pulse space-y-2">
                  <div className="h-4 bg-indigo-200 rounded w-3/4"></div>
                  <div className="h-4 bg-indigo-200 rounded w-1/2"></div>
                </div>
              ) : adgRequirements.length > 0 ? (
                <div className="space-y-4">
                  <div className="text-sm text-gray-600 mb-3">
                    Showing {adgRequirements.length} high-value design criteria
                  </div>
                  {adgRequirements.map((req: any) => (
                    <div key={req.criteriaId} className="border-l-4 border-indigo-300 pl-4 py-2">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="font-semibold text-indigo-900">
                            {req.criteriaId}: {req.requirementSummary || req.requirement_summary}
                          </div>
                          {req.numericValue && (
                            <div className="text-sm text-gray-700 mt-1">
                              Value: <span className="font-medium">{req.numericValue} {req.numericUnit}</span>
                            </div>
                          )}
                        </div>
                        {req.sourcePage && (
                          <button
                            onClick={() => setViewingPdfPage({
                              pageNumber: req.sourcePage,
                              url: `/pdf-pages/adg-part3/page-${req.sourcePage}.png`,
                              label: `ADG ${req.criteriaId}`
                            })}
                            className="ml-3 text-xs text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                          >
                            <FileImage className="w-3 h-3" />
                            p.{req.sourcePage}
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <ADGSummaryCard developmentType={developmentType} zoneCode={zone} />
              )}
            </CardContent>
          )}
        </Card>
      )}

      {/* TOD Parking Reductions - Shows when property has regulatory TOD relevance */}
      {showTODSection && (
        <Card className="border-emerald-200 bg-emerald-50/30">
          <CardHeader
            className="cursor-pointer hover:bg-emerald-100/50 transition-colors"
            onClick={() => toggleSection('tod')}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {collapsedSections.tod ? (
                  <ChevronRight className="h-5 w-5 text-emerald-600" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-emerald-600" />
                )}
                <Car className="h-5 w-5 text-emerald-600" />
                <CardTitle className="text-lg text-emerald-900">TOD Parking Reductions</CardTitle>
              </div>
              <div className="flex items-center gap-2">
                {isInDesignatedTOD && (
                  <Badge className="bg-emerald-600 text-white">Designated TOD</Badge>
                )}
                <Badge className="bg-emerald-100 text-emerald-800">Transit Oriented</Badge>
              </div>
            </div>
            <p className="text-sm text-emerald-700 mt-1 ml-7">
              {isInDesignatedTOD
                ? 'This property is within a designated TOD precinct under SEPP (Housing) 2021.'
                : (() => {
                    const reasons: string[] = [];
                    if (nearbyTransport.some(s => s.type === 'heavy_rail' && s.distance <= 800)) {
                      reasons.push('heavy rail station within 800m');
                    }
                    if (nearbyTransport.some(s => s.type === 'light_rail' && s.distance <= 600)) {
                      reasons.push('light rail stop within 600m');
                    }
                    if (nearbyTransport.some(s => s.type === 'bus' && s.distance <= 400 && (s.frequency === 'high' || s.frequency === 'medium'))) {
                      reasons.push('frequent bus service within 400m');
                    }
                    return `Parking reductions may apply due to ${reasons.join(' and ')}.`;
                  })()
              }
            </p>
          </CardHeader>
          {!collapsedSections.tod && (
            <CardContent className="pt-0 space-y-4">
              {/* Designated TOD Precinct Info */}
              {isInDesignatedTOD && (
                <div className="bg-emerald-100 border border-emerald-300 rounded-lg p-3">
                  <p className="text-sm font-medium text-emerald-900">
                    This property is in a designated TOD precinct
                  </p>
                  <p className="text-xs text-emerald-700 mt-1">
                    Special parking provisions may apply under SEPP (Housing) 2021
                  </p>
                </div>
              )}

              {/* Nearby Transport Detection */}
              <div className="bg-white border border-emerald-100 rounded-lg p-3">
                <h4 className="text-xs font-semibold text-emerald-800 mb-2">
                  Qualifying Transport Near This Property
                </h4>
                <NearbyTransportCard
                  lat={propertyLat}
                  lng={propertyLng}
                  preloadedStops={nearbyTransport}
                  loading={transportLoading}
                />
              </div>

              {/* SEPP Parking Provisions */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-emerald-800">
                    SEPP (Housing) 2021 Parking Provisions
                  </h4>
                </div>

                {/* Boarding House Parking */}
                <div className="bg-white border border-emerald-200 rounded-lg p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-gray-900">Boarding Houses</p>
                      <p className="text-xs text-gray-700 mt-1">
                        <strong>In accessible area:</strong> 0.2 parking spaces per boarding room
                      </p>
                      <p className="text-xs text-gray-700">
                        <strong>Otherwise:</strong> 0.5 parking spaces per boarding room
                      </p>
                      <p className="text-xs text-gray-500 mt-2">
                        SEPP (Housing) 2021, Clause 24 - Non-discretionary development standards
                      </p>
                    </div>
                    <button
                      onClick={() => setViewingPdfPage({
                        pageNumber: 11,
                        url: '/pdf-pages/sepp-housing/sepp-housing_page_11.png',
                        label: 'SEPP (Housing) 2021 - Boarding House Parking'
                      })}
                      className="text-emerald-600 hover:text-emerald-800 transition-colors p-1 rounded hover:bg-emerald-50"
                    >
                      <FileImage className="h-5 w-5" />
                    </button>
                  </div>
                </div>

                {/* Co-Living Parking */}
                <div className="bg-white border border-emerald-200 rounded-lg p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-gray-900">Co-Living Housing</p>
                      <p className="text-xs text-gray-700 mt-1">
                        <strong>In accessible area:</strong> 0.2 parking spaces per private room
                      </p>
                      <p className="text-xs text-gray-700">
                        <strong>Otherwise:</strong> 0.5 parking spaces per private room
                      </p>
                      <p className="text-xs text-gray-500 mt-2">
                        SEPP (Housing) 2021, Clause 68 - Non-discretionary development standards
                      </p>
                    </div>
                    <button
                      onClick={() => setViewingPdfPage({
                        pageNumber: 32,
                        url: '/pdf-pages/sepp-housing/sepp-housing_page_32.png',
                        label: 'SEPP (Housing) 2021 - Co-Living Parking'
                      })}
                      className="text-emerald-600 hover:text-emerald-800 transition-colors p-1 rounded hover:bg-emerald-50"
                    >
                      <FileImage className="h-5 w-5" />
                    </button>
                  </div>
                </div>

                {/* Build-to-Rent Housing */}
                <div className="bg-white border border-emerald-200 rounded-lg p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-gray-900">Build-to-Rent Housing</p>
                      <p className="text-xs text-gray-700 mt-1">
                        <strong>In accessible area:</strong>
                      </p>
                      <ul className="text-xs text-gray-700 ml-3 mt-1 space-y-0.5">
                        <li>• 1 bedroom: 0.2 parking spaces per dwelling</li>
                        <li>• 2 bedrooms: 0.5 parking spaces per dwelling</li>
                        <li>• 3+ bedrooms: 1 parking space per dwelling</li>
                      </ul>
                      <p className="text-xs text-gray-500 mt-2">
                        SEPP (Housing) 2021, Clause 74 - Non-discretionary development standards
                      </p>
                    </div>
                    <button
                      onClick={() => setViewingPdfPage({
                        pageNumber: 35,
                        url: '/pdf-pages/sepp-housing/sepp-housing_page_35.png',
                        label: 'SEPP (Housing) 2021 - Build-to-Rent Parking'
                      })}
                      className="text-emerald-600 hover:text-emerald-800 transition-colors p-1 rounded hover:bg-emerald-50"
                    >
                      <FileImage className="h-5 w-5" />
                    </button>
                  </div>
                </div>

                {/* Affordable Housing / LHAC */}
                <div className="bg-white border border-emerald-200 rounded-lg p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-gray-900">Affordable Housing in TOD Areas</p>
                      <p className="text-xs text-gray-700 mt-1">
                        <strong>In accessible area:</strong>
                      </p>
                      <ul className="text-xs text-gray-700 ml-3 mt-1 space-y-0.5">
                        <li>• 1 bedroom: 0.4 parking spaces per dwelling</li>
                        <li>• 2 bedrooms: 0.5 parking spaces per dwelling</li>
                        <li>• 3+ bedrooms: 1 parking space per dwelling</li>
                      </ul>
                      <p className="text-xs text-gray-500 mt-2">
                        SEPP (Housing) 2021, Clause 42 - Low and mid rise housing
                      </p>
                    </div>
                    <button
                      onClick={() => setViewingPdfPage({
                        pageNumber: 18,
                        url: '/pdf-pages/sepp-housing/sepp-housing_page_18.png',
                        label: 'SEPP (Housing) 2021 - Affordable Housing Parking'
                      })}
                      className="text-emerald-600 hover:text-emerald-800 transition-colors p-1 rounded hover:bg-emerald-50"
                    >
                      <FileImage className="h-5 w-5" />
                    </button>
                  </div>
                </div>

                {/* Market-Rate Apartments */}
                <div className="bg-white border border-emerald-200 rounded-lg p-3">
                  <p className="text-sm font-semibold text-gray-900">Residential Flat Buildings & Apartments</p>
                  <p className="text-xs text-gray-700 mt-1">
                    Parking rates determined by <strong>council DCP</strong>. SEPP (Housing) 2021 refers to ADG Part 3J, which defers to local planning controls.
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    Check the <strong>DCP Provisions</strong> tab for {lga} parking requirements.
                  </p>
                </div>

                {/* Accessible Area Definition */}
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <p className="text-xs font-semibold text-emerald-900">What is an "Accessible Area"?</p>
                      <p className="text-xs text-emerald-800 mt-1">
                        Land within <strong>800m walking distance</strong> of a public entrance to a railway, metro or light rail station (Schedule 11)
                      </p>
                    </div>
                    <button
                      onClick={() => setViewingPdfPage({
                        pageNumber: 115,
                        url: '/pdf-pages/sepp-housing/sepp-housing_page_115.png',
                        label: 'SEPP (Housing) 2021 - Accessible Area Definition'
                      })}
                      className="text-emerald-600 hover:text-emerald-800 transition-colors p-1 rounded hover:bg-emerald-50"
                    >
                      <FileImage className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              </div>

            </CardContent>
          )}
        </Card>
      )}

      {/* Info for zones that don't permit apartments */}
      {!showADGSection && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-600">
          <p>
            <strong>Note:</strong> ADG Design Criteria apply to zones that permit apartment
            developments (R3, R4, B1-B6, MU1, E1-E2).
            {zone && <span> Current zone: <strong>{zone}</strong></span>}
          </p>
        </div>
      )}

      {/* TOD info when no qualifying transport found */}
      {!showTODSection && !showADGSection && propertyLat && propertyLng && !transportLoading && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-600">
          <p>
            <strong>TOD:</strong> No public transport within regulatory thresholds
            (800m rail, 600m light rail, 400m frequent bus) detected for this property.
          </p>
        </div>
      )}

      {/* PDF Image Modal */}
      <PdfImageModal
        isOpen={!!viewingPdfPage}
        onClose={() => setViewingPdfPage(null)}
        imageUrl={viewingPdfPage?.url || null}
        pageNumber={viewingPdfPage?.pageNumber}
        title={viewingPdfPage?.label}
      />
    </div>
  );
}
