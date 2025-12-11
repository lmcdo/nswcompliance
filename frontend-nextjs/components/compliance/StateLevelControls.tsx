'use client';

/**
 * State Level Controls Component
 * Displays SEPP, LEP, and ADG requirements in a unified view
 * Separated from DCP (council-level) provisions
 */

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronRight, Scale, Building2, Car } from 'lucide-react';
import { AuthorityColors } from '@/lib/design-tokens';
import { StructuredSeppRequirements } from './StructuredSeppRequirements';
import { LandUseZoningCard } from './LandUseZoningCard';
import { MinimumLotSizeCard } from './MinimumLotSizeCard';
import { ADGBuildingSeparationTable } from './ADGBuildingSeparationTable';
import { ADGSummaryCard } from './ADGSummaryCard';
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

// Zones that typically permit apartment developments
// ADG should show for these zones regardless of development type selection
const APARTMENT_PERMITTING_ZONES = [
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
  const [loadingSepp, setLoadingSepp] = useState(false);
  const [nearbyTransport, setNearbyTransport] = useState<any[]>([]);
  const [transportLoading, setTransportLoading] = useState(false);
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({
    sepp: false,
    lep: false,
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

  // Load structured SEPP requirements
  const loadStructuredRequirements = useCallback(async () => {
    if (!developmentType) return;

    setLoadingSepp(true);
    try {
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
          setStructuredRequirements(data.data.requirements);
        } else {
          setStructuredRequirements([]);
        }
      }
    } catch (error) {
      console.error('[StateLevelControls] Failed to fetch SEPP requirements:', error);
      setStructuredRequirements([]);
    } finally {
      setLoadingSepp(false);
    }
  }, [developmentType]);

  useEffect(() => {
    loadStructuredRequirements();
  }, [loadStructuredRequirements]);

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

  // Show ADG if zone permits apartments (regardless of dev type selection)
  const zonePrefix = zone?.split(' ')[0]?.toUpperCase();
  const isApartmentZone = zonePrefix ? APARTMENT_PERMITTING_ZONES.includes(zonePrefix) : false;

  // Show ADG section if either condition is true
  const showADGSection = isApartmentDevelopment || isApartmentZone;

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
            {/* Planning Portal Source Layers */}
            {(sustainableInfo.waterTarget || sustainableInfo.climateZone || sustainableInfo.basixArea) && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                <div className="text-xs font-semibold text-purple-800 mb-2">
                  📍 Applied from NSW Planning Portal
                </div>
                <div className="flex flex-wrap gap-2">
                  {sustainableInfo.waterTarget && (
                    <div className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                      💧 Water Target: <span className="font-bold">{sustainableInfo.waterTarget}</span>
                    </div>
                  )}
                  {sustainableInfo.climateZone && (
                    <div className="text-xs bg-orange-100 text-orange-800 px-2 py-1 rounded">
                      🌡️ Climate Zone: <span className="font-bold">{sustainableInfo.climateZone}</span>
                    </div>
                  )}
                  {sustainableInfo.basixArea && (
                    <div className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
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
              <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <div className="text-2xl">⚡</div>
                  <div className="flex-1">
                    <div className="font-semibold text-green-900">BASIX Energy & Thermal Requirements</div>
                    <p className="text-sm text-green-800 mt-1">
                      Energy efficiency and thermal comfort targets for {sustainableInfo.basixArea} require
                      detailed calculation through the official BASIX Certificate tool. Targets vary by
                      building type, orientation, and materials.
                    </p>
                    <div className="flex flex-wrap gap-2 mt-3">
                      <a
                        href="https://www.basix.nsw.gov.au/iframe/basix-help/basix-help-single.html"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs bg-green-600 text-white px-3 py-1.5 rounded hover:bg-green-700 transition-colors"
                      >
                        🔗 Get BASIX Certificate
                      </a>
                      <a
                        href="https://www.basix.nsw.gov.au/iframe/find-assessor.html"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs bg-white text-green-700 border border-green-300 px-3 py-1.5 rounded hover:bg-green-50 transition-colors"
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
              {/* ADG Summary Card - All Design Criteria */}
              <ADGSummaryCard developmentType={developmentType} zoneCode={zone} />
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

              {/* Reference Table */}
              <div>
                <h4 className="text-xs font-semibold text-emerald-800 mb-2">
                  TOD Parking Reduction Rates
                </h4>
                <p className="text-xs text-gray-600 mb-2">
                  Reference rates for sites near frequent public transport.
                </p>
                <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="pb-2">Transport Type</th>
                    <th className="pb-2">Distance</th>
                    <th className="pb-2">Reduction</th>
                  </tr>
                </thead>
                <tbody className="text-gray-700">
                  <tr className="border-b border-gray-100">
                    <td className="py-1.5">Heavy Rail (train)</td>
                    <td className="py-1.5">≤400m</td>
                    <td className="py-1.5 font-medium text-emerald-700">30%</td>
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="py-1.5">Heavy Rail</td>
                    <td className="py-1.5">400-800m</td>
                    <td className="py-1.5 font-medium text-emerald-700">20%</td>
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="py-1.5">Light Rail</td>
                    <td className="py-1.5">≤400m</td>
                    <td className="py-1.5 font-medium text-emerald-700">25%</td>
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="py-1.5">Light Rail</td>
                    <td className="py-1.5">400-600m</td>
                    <td className="py-1.5 font-medium text-emerald-700">15%</td>
                  </tr>
                  <tr className="border-b border-gray-100">
                    <td className="py-1.5">Bus (high freq)</td>
                    <td className="py-1.5">≤400m</td>
                    <td className="py-1.5 font-medium text-emerald-700">15%</td>
                  </tr>
                  <tr>
                    <td className="py-1.5">Bus (medium freq)</td>
                    <td className="py-1.5">≤400m</td>
                    <td className="py-1.5 font-medium text-emerald-700">10%</td>
                  </tr>
                </tbody>
                </table>
                <p className="text-xs text-gray-500 mt-2 italic">
                  Multiple transport: +10% bonus. Max total: 50%. Check council DCP for specific requirements.
                </p>
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
    </div>
  );
}
