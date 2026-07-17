'use client';

/**
 * State Level Controls Component
 * Displays SEPP, LEP, and ADG requirements in a unified view
 * Separated from DCP (council-level) provisions
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronRight, Scale, Building2, Car, FileImage, Clock, Shield, AlertTriangle, Info } from 'lucide-react';
import { lmrFrontageStatus, roadHierarchyAnnotation } from '@/lib/see/propertyUtils';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';
import { AuthorityColors } from '@/lib/design-tokens';
import { StructuredSeppRequirements } from './StructuredSeppRequirements';
import { LandUseZoningCard } from './LandUseZoningCard';
import { MinimumLotSizeCard } from './MinimumLotSizeCard';
// ADG Building Separation Table hidden — setback_rules table empty (never populated with ADG 3F-1 data)
import { ADGSummaryCard } from './ADGSummaryCard';
import { HousingSEPPEligibilityCard } from './HousingSEPPEligibilityCard';
import { PatternBookEligibilityCard } from './PatternBookEligibilityCard';
import { NearbyTransportCard } from '../tod/NearbyTransportCard';
import { NotApplicableCard } from './NotApplicableCard';
import { ExemptComplyingProvisions } from './ExemptComplyingProvisions';
import { PathwaySummaryCard } from './PathwaySummaryCard';
import { NSW_PLANNING_CONSTANTS, isResidentialZone, isIndustrialZone, isLMRApplicable, permitsApartmentDevelopment } from '@/lib/regulatory-constants';
import { getSeppPdfUrl, getAdgPdfUrl } from '@/lib/pdf-url-builder';
import { tryGetLGAConfig } from '@/lib/lga-configs';
import { battleaxeAwareLotWidth } from '@/lib/geometry/effective-lot-width';

interface StrataInfo {
  isStrata: boolean;
  source: string | null;
  strataUnit: string | null;
}

interface StateLevelControlsProps {
  propertyData: any;
  developmentType: string;
  buildingHeight?: number;
  onNavigateToDcp?: (topic: string, hcaSlug?: string) => void;
  strataInfo?: StrataInfo;
}

// ADG applies to residential flat buildings only (SEPP Housing 2021 Part 4).
// multi_dwelling_housing (townhouses) and boarding_house use separate standards.
const APARTMENT_DEV_TYPES = [
  'residential_flat_building',
  'shop_top_housing',
  'mixed_use'
];

export function StateLevelControls({
  propertyData,
  developmentType,
  buildingHeight,
  onNavigateToDcp,
  strataInfo,
}: StateLevelControlsProps) {
  const [structuredRequirements, setStructuredRequirements] = useState<any[]>([]);
  const [adgRequirements, setAdgRequirements] = useState<any[]>([]);
  const [adgStructuredRequirements, setAdgStructuredRequirements] = useState<any[]>([]);
  const [transportRequirements, setTransportRequirements] = useState<any[]>([]);
  const [loadingSepp, setLoadingSepp] = useState(false);
  const [loadingAdg, setLoadingAdg] = useState(false);
  const [nearbyTransport, setNearbyTransport] = useState<any[]>([]);
  const nearbyTransportRef = useRef<any[]>([]);
  const walkingFetchedRef = useRef<string | null>(null); // tracks coords for which we've fetched
  const [transportLoading, setTransportLoading] = useState(false);
  const [walkingDistance, setWalkingDistance] = useState<{
    walking_m: number | null;
    crow_flies_m: number | null;
    tod_eligible: boolean | null;
    station_name: string;
    threshold_m: number;
  } | null>(null);
  const [walkingDistanceLoading, setWalkingDistanceLoading] = useState(false);
  const [viewingPdfPage, setViewingPdfPage] = useState<{pageNumber: number, url: string, label: string} | null>(null);
  const [collapsedSections, setCollapsedSections] = useState<Record<string, boolean>>({
    sepp: false,
    lep: false,
    lmr: false,  // Housing SEPP LMR section
    adg: false,
    tod: false // TOD expanded by default when shown
  });

  // Pathway summary state for cross-pathway intelligence card
  const [patternBookStatus, setPatternBookStatus] = useState<'ELIGIBLE' | 'INELIGIBLE' | 'CONDITIONAL' | undefined>();
  const [exemptComplyingCount, setExemptComplyingCount] = useState<number>(0);

  const isApartmentDevelopment = APARTMENT_DEV_TYPES.includes(developmentType);

  // Toggle section collapse
  const toggleSection = (section: string) => {
    setCollapsedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  // ============================================================================
  // LGA Configuration - Load LGA-specific config with graceful fallback
  // ============================================================================
  // Extract LGA from property data (provided by NSW Planning Portal)
  const lga = propertyData?.constraints?.lga;

  // Try to load LGA config. If LGA is not configured yet (returns null),
  // the component will fall back to NSW-wide defaults.
  // Currently configured LGAs: Inner West
  const lgaConfig = lga ? tryGetLGAConfig(lga.toLowerCase().replace(/\s+/g, '_')) : null;

  // Development logging for LGA config status
  if (process.env.NODE_ENV === 'development' && lga) {
    if (lgaConfig) {
      console.log(`[StateLevelControls] LGA config loaded for: ${lgaConfig.name}`);
    } else {
      console.log(`[StateLevelControls] No config found for LGA: ${lga} (using NSW defaults)`);
    }
  }

  // ============================================================================
  // SEPP ID Mapping: Planning Portal → Database
  // ============================================================================
  // Default NSW-wide mapping. Can be overridden by LGA config if needed.
  // Note: Only sustainable_buildings_2022 currently has structured requirements in DB
  // Housing SEPP uses separate sepp_adg_requirements table
  // Others detected but no structured data available yet
  const DEFAULT_SEPP_MAPPING: Record<string, string> = {
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

  // Use LGA-specific SEPP mapping if provided, otherwise use NSW default
  const SEPP_MAPPING = lgaConfig?.sepp?.sepp_id_mapping || DEFAULT_SEPP_MAPPING;

  // Load ADG requirements only where an apartment / residential flat building is
  // actually permitted — R4 and business/mixed-use zones under the Standard Instrument,
  // or R1–R3 where the Stage-2 LMR mid-rise reforms reach the LGA. R1–R3 outside a
  // designated region (e.g. regional R3 in Wingecarribee) do not engage the ADG.
  const loadADGRequirements = useCallback(async () => {
    if (!permitsApartmentDevelopment(
      propertyData?.constraints?.zone || '',
      propertyData?.constraints?.lga || '',
    )) {
      setAdgRequirements([]);
      return;
    }

    setLoadingAdg(true);
    try {
      console.log('[StateLevelControls] Fetching ADG requirements (RFB development type)');
      const response = await fetch(`/api/adg/requirements`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data) {
          // Filter high-value requirements
          const keyRequirements = data.data.filter((r: any) => 
            (NSW_PLANNING_CONSTANTS.ADG.KEY_CRITERIA_IDS as readonly string[]).includes(r.criteriaId)
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
    // Also load ADG structured requirements (Phase 4a)
    try {
      const structuredResponse = await fetch('/api/sepp/structured-requirements', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          seppId: 'housing_2021',
          developmentType,
          schedule: 'apartment_design_guide'
        })
      });

      if (structuredResponse.ok) {
        const structuredData = await structuredResponse.json();
        if (structuredData.success && structuredData.data?.requirements) {
          setAdgStructuredRequirements(structuredData.data.requirements);
          console.log(`[StateLevelControls] Loaded ${structuredData.data.requirements.length} ADG structured requirements`);
        }
      }
    } catch (error) {
      console.error('[StateLevelControls] Failed to fetch ADG structured requirements:', error);
      setAdgStructuredRequirements([]);
    }

    }
  }, [developmentType, propertyData]);

  // Load structured SEPP requirements (dynamic based on portal detection)
  const loadStructuredRequirements = useCallback(async () => {
    if (!developmentType || !propertyData) return;

    const applicableSepps = propertyData?.constraints?.applicableSepps || [];
    console.log('[StateLevelControls] Detected SEPPs:', applicableSepps);

    // Get zone information for filtering
    const zone = propertyData?.constraints?.zone;
    const zoneCode = zone?.split(' ')[0]?.replace(/[^A-Z0-9]/gi, '')?.toUpperCase() || '';
    
    // Define zones that permit residential development
    const residentialZones = NSW_PLANNING_CONSTANTS.ZONES.RESIDENTIAL;
    const industrialZones = NSW_PLANNING_CONSTANTS.ZONES.INDUSTRIAL;
    
    const permitsResidential = residentialZones.includes(zoneCode);
    const isIndustrialZone = industrialZones.includes(zoneCode);
    
    // Map portal SEPP IDs to database IDs
    let dbSeppIds = applicableSepps
      .map((portalId: string) => SEPP_MAPPING[portalId])
      .filter(Boolean);
    
    // Filter out residential-only SEPPs if zone doesn't permit residential
    if (!permitsResidential) {
      const beforeFilter = dbSeppIds.length;
      dbSeppIds = dbSeppIds.filter((seppId: any) => seppId !== 'housing_2021');
      if (beforeFilter > dbSeppIds.length) {
        console.log(`[StateLevelControls] ${zoneCode} zone does not permit residential - excluding Housing SEPP (ADG, Secondary Dwellings)`);
      }
    }

    // Force-fetch contamination requirements for industrial zones
    // Planning Portal only detects EPA investigation areas, not zone-based risk
    if (isIndustrialZone && !dbSeppIds.includes('resilience_hazards_2021')) {
      console.log(`[StateLevelControls] Industrial zone ${zoneCode} detected - force-fetching contamination requirements`);
      dbSeppIds.push('resilience_hazards_2021');
    }

    if (dbSeppIds.length === 0) {
      console.log('[StateLevelControls] No structured SEPPs detected');
      setStructuredRequirements([]);
      return;
    }

    setLoadingSepp(true);
    try {
      // Fetch requirements for each detected SEPP
      const results: any[] = [];
      const transportResults: any[] = [];

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
            // Separate transport infrastructure for dedicated section
            if (seppId === 'transport_infrastructure_2021') {
              transportResults.push(...data.data.requirements);
            } else {
              results.push(...data.data.requirements);
            }
          }
        }
      }

      setStructuredRequirements(results);
      setTransportRequirements(transportResults);
      console.log(`[StateLevelControls] Loaded ${results.length} structured requirements, ${transportResults.length} transport requirements`);
    } catch (error) {
      console.error('[StateLevelControls] Failed to fetch SEPP requirements:', error);
      setStructuredRequirements([]);
      setTransportRequirements([]);
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
          const nearby = (data.suggestions || []).filter((s: any) => s.distance <= NSW_PLANNING_CONSTANTS.TOD.TRANSPORT_PROXIMITY_SEARCH_M);
          nearbyTransportRef.current = nearby;
          setNearbyTransport(nearby);
          // Reset walking fetch guard when transport data arrives for new coords
          walkingFetchedRef.current = null;
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

  // Fetch walking network distance for nearest qualifying rail station.
  // Reads transport via ref to avoid render loop. Guarded to fire once per property.
  useEffect(() => {
    if (!propertyLat || !propertyLng) return;

    const coordKey = `${propertyLat},${propertyLng}`;
    if (walkingFetchedRef.current === coordKey) return;

    const stops = nearbyTransportRef.current;
    if (stops.length === 0) return;

    walkingFetchedRef.current = coordKey;

    const railStation = stops.find(
      (s: any) => (s.type === 'heavy_rail' || s.type === 'light_rail') &&
        s.distance <= NSW_PLANNING_CONSTANTS.TOD.HEAVY_RAIL_WALKABLE_M &&
        s.lat && s.lng
    );
    if (!railStation) return;

    const threshold = railStation.type === 'light_rail'
      ? NSW_PLANNING_CONSTANTS.TOD.LIGHT_RAIL_WALKABLE_M
      : NSW_PLANNING_CONSTANTS.TOD.HEAVY_RAIL_WALKABLE_M;

    const controller = new AbortController();
    setWalkingDistanceLoading(true);
    const spatialBase = process.env.NEXT_PUBLIC_SPATIAL_API_URL || '/api/spatial';
    fetch(`${spatialBase}/tod`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        property_lat: propertyLat,
        property_lng: propertyLng,
        station_lat: railStation.lat,
        station_lng: railStation.lng,
        station_name: railStation.name,
        tod_threshold_m: threshold,
      }),
      signal: controller.signal,
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.walking_m !== undefined) {
          setWalkingDistance({
            walking_m: data.walking_m,
            crow_flies_m: data.crow_flies_m,
            tod_eligible: data.tod_eligible,
            station_name: railStation.name,
            threshold_m: threshold,
          });
        }
      })
      .catch(() => { /* spatial API unavailable or aborted — silently skip */ })
      .finally(() => setWalkingDistanceLoading(false));

    return () => controller.abort();
  }, [propertyLat, propertyLng, transportLoading]);

  // Fetch pathway summary data for PathwaySummaryCard
  useEffect(() => {
    const fetchPathwaySummary = async () => {
      if (!propertyData) return;

      const zoneCode = propertyData?.constraints?.zone?.split(' ')[0]?.replace(/[^A-Z0-9]/gi, '')?.toUpperCase() || '';

      // Fetch Pattern Book eligibility
      try {
        const pbResponse = await fetch('/api/pathway/pattern-book-eligibility', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ propertyData })
        });
        if (pbResponse.ok) {
          const data = await pbResponse.json();
          const eligibility = data.data?.eligibility || data;
          setPatternBookStatus(eligibility.status);
        }
      } catch (err) {
        console.error('[PathwaySummary] Failed to fetch Pattern Book status:', err);
      }

      // Fetch Exempt & Complying counts
      if (zoneCode) {
        try {
          const ecResponse = await fetch(`/api/sepp/exempt-complying?zone=${zoneCode}`);
          if (ecResponse.ok) {
            const data = await ecResponse.json();
            // notApplicable means zone is not covered by Housing Code — treat as 0 work types
            if (data.notApplicable) {
              setExemptComplyingCount(0);
            } else {
              const counts = data.counts || {};
              const totalCount = Object.values(counts).reduce((a: any, b: any) => a + b, 0) as number;
              setExemptComplyingCount(totalCount > 0 ? Object.keys(counts).length : 0);
            }
          }
        } catch (err) {
          console.error('[PathwaySummary] Failed to fetch E&C counts:', err);
        }
      }
    };

    fetchPathwaySummary();
  }, [propertyData]);

  // Extract zone and lot size data from propertyData
  const zone = propertyData?.constraints?.zone;
  const zoneDescription = propertyData?.constraints?.zoneDescription;
  // Note: lga is defined earlier in the component near LGA config loading

  // Extract lot dimensions for Housing SEPP LMR eligibility
  // First try calculated dimensions from lot geometry, then fallback to property data
  const propertyAreaStr = propertyData?.propertyArea;
  const lotSize = propertyData?.lotDimensions?.area
    ?? (propertyAreaStr ? parseFloat(propertyAreaStr.replace(/[^0-9.]/g, '')) || null : null)
    ?? propertyData?.geometry?.area;

  // Lot width - from calculated geometry (cadastre), then fallbacks.
  // battleaxeAwareLotWidth returns the head width for a battleaxe (the cadastral
  // "frontage" there is the access handle, which would understate width-based
  // SEPP/LMR eligibility), otherwise the frontage.
  const lotWidth = battleaxeAwareLotWidth(propertyData?.lotDimensions)
    ?? propertyData?.geometry?.frontageWidth
    ?? propertyData?.geometry?.estimatedWidth
    ?? propertyData?.constraints?.lotWidth
    ?? NSW_PLANNING_CONSTANTS.HOUSING_SEPP.DEFAULT_LOT_WIDTH_M; // Default estimate if not available

  // Lot depth - from calculated geometry
  const lotDepth = propertyData?.lotDimensions?.depth || null;

  // Get station distance for TOD eligibility
  const stationDistance = propertyData?.constraints?.todPrecinct?.stationDistance
    || nearbyTransport.find(s => s.type === 'heavy_rail')?.distance;

  // Zone may include colon (e.g., "R2: Low Density") - strip non-alphanumeric chars
  const zoneCode = zone?.split(' ')[0]?.replace(/[^A-Z0-9]/gi, '')?.toUpperCase() || '';
  // LMR applicability: Stage 2 (R1–R4 within designated regions) OR Stage 1 (R2 statewide, excl. 4 LGAs)
  const isLMRArea = zone && lga ? isLMRApplicable(zone, lga) : false;

  // Extract LEP height and FSR from Planning Portal layers for SEPP-LEP override comparison
  const heightLayer = propertyData?.planningLayers?.find(
    (l: any) => l.layerName === 'Height of Buildings Map'
  );
  const lepHeight: number | null = (() => {
    const val = heightLayer?.results?.[0]?.['Maximum Building Height']
      ?? heightLayer?.results?.[0]?.['MAX_B_H']
      ?? heightLayer?.results?.[0]?.['B_H']
      ?? heightLayer?.results?.[0]?.['HEIGHT'];
    return val != null ? parseFloat(val) : null;
  })();

  const fsrLayer = propertyData?.planningLayers?.find(
    (l: any) => l.layerName === 'Floor Space Ratio Map'
  );
  const lepFsr: number | null = (() => {
    const result = fsrLayer?.results?.find((r: any) => r['Floor Space Ratio']);
    return result ? parseFloat(result['Floor Space Ratio']) : null;
  })();

  // Show Housing SEPP LMR section for residential zones
  const showHousingSEPPSection = isLMRArea && lotSize && lotWidth;

  // Show ADG based on SEPP Housing 2021 detection (dynamic from planning portal)
  const applicableSepps = propertyData?.constraints?.applicableSepps || [];
  const hasHousingSEPP = applicableSepps.some((sepp: string) => 
    sepp === 'SEPP_HOUSING_2021' || sepp === 'SEPP_65'
  );
  
  // Show ADG only where an apartment / RFB is permissible: R4 + business/mixed-use zones
  // under the Standard Instrument, or R1–R3 where Stage-2 LMR reaches the LGA. The old
  // gate used a flat zone list that treated every R1/R2/R3 lot as apartment-permitting,
  // so it wrongly showed the ADG panel on regional low/medium-density lots (e.g. R3 Bowral)
  // even where the Housing SEPP LMR reforms are correctly reported as not applicable.
  const showADGSection =
    permitsApartmentDevelopment(propertyData?.constraints?.zone || '', lga || '') ||
    adgRequirements.length > 0;

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
    if (stop.type === 'heavy_rail' && stop.distance <= NSW_PLANNING_CONSTANTS.TOD.HEAVY_RAIL_WALKABLE_M) return true;
    if (stop.type === 'light_rail' && stop.distance <= NSW_PLANNING_CONSTANTS.TOD.LIGHT_RAIL_WALKABLE_M) return true;
    if (stop.type === 'bus' && stop.distance <= NSW_PLANNING_CONSTANTS.TOD.BUS_WALKABLE_M &&
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

  // Validate LGA is present - required for state-level controls
  if (!lga) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardContent className="p-6">
          <div className="flex items-start gap-3">
            <div className="text-red-500 text-2xl">⚠️</div>
            <div className="flex-1">
              <p className="text-red-900 font-semibold text-lg">LGA Information Required</p>
              <p className="text-red-700 text-sm mt-2">
                Unable to determine the Local Government Area (LGA) for this property.
                State-level planning controls cannot be displayed without LGA context.
              </p>
              <div className="mt-4 bg-white border border-red-200 rounded p-3">
                <p className="text-xs font-semibold text-red-800 mb-1">Why is this needed?</p>
                <p className="text-xs text-red-700">
                  SEPP requirements, BASIX zones, and other state controls vary by LGA.
                  The LGA is typically provided by the NSW Planning Portal when you search for a property.
                </p>
              </div>
              <div className="mt-3 text-xs text-red-600">
                <p className="font-medium">Possible causes:</p>
                <ul className="list-disc ml-4 mt-1 space-y-0.5">
                  <li>Property not found in NSW Planning Portal database</li>
                  <li>Address outside NSW jurisdiction</li>
                  <li>API connection issue - try refreshing the page</li>
                </ul>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Data currency indicator */}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <span className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0" />
        <span className="font-medium text-gray-700">NSW State Planning Instruments</span>
        <span>·</span>
        <span>Sourced live — NSW Planning Portal</span>
      </div>

      {/* SEPP Tab Intro Banner */}
      <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-r-lg">
        <div className="font-semibold text-amber-900 mb-1">State Environmental Planning Policies</div>
        <div className="text-sm text-amber-800">Mandatory state-wide requirements that apply to this property</div>
      </div>

      {/* Pathway Summary - Cross-pathway intelligence card */}
      <PathwaySummaryCard
        propertyData={propertyData}
        patternBookStatus={patternBookStatus}
        exemptComplyingCount={exemptComplyingCount}
        housingLmrApplicable={isLMRArea}
        zoneCode={zoneCode}
      />

      {/* Strata notice — shown when unit address detected */}
      {strataInfo?.isStrata && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 flex items-start gap-3">
          <Info className="h-5 w-5 text-orange-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-orange-900">Strata unit — interpret controls at scheme level</p>
            <p className="text-sm text-orange-800 mt-1">
              SEPP standards below apply to the building or development on the lot as a whole. Works to an individual unit are governed by the strata by-laws and require owners corporation consent for anything affecting common property. Secondary dwellings (granny flats) cannot be erected on strata lots. CDC whole-dwelling pathways apply to new development on the scheme&apos;s parent lot, not individual unit alterations.
            </p>
          </div>
        </div>
      )}

      {/* Exempt & Complying Development Standards - certifier CDC gateway, shown first */}
      {zoneCode && (
        <ExemptComplyingProvisions
          zoneCode={zoneCode}
          lotArea={lotSize}
          heritageItem={!!(propertyData?.heritage?.isHeritage && propertyData?.heritage?.heritageType?.toLowerCase().includes('item'))}
          heritageAffected={!!propertyData?.heritage?.isHeritage}
          isStrata={!!strataInfo?.isStrata}
        />
      )}

      {/* Pattern Book CDC Pathway - Pathway triage for housing developments */}
      <PatternBookEligibilityCard
        propertyData={propertyData}
        onNavigateToDcp={onNavigateToDcp}
        lotDimensions={propertyData?.lotDimensions || null}
        lotSize={lotSize || null}
        address={propertyData?.address || null}
        strataInfo={strataInfo}
      />

      {/* SEPP Section */}
      <Card className={`${AuthorityColors.SEPP.border.replace('500', '200')} ${AuthorityColors.SEPP.bg}`}>
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
              <Badge variant="outline" className="text-xs text-gray-500 flex items-center gap-1">
                <Clock className="h-3 w-3" />
                Updated Feb 2026
              </Badge>
            </div>
          </div>
          <p className={`text-sm ${AuthorityColors.SEPP.text} mt-1 ml-7`}>
            State Environmental Planning Policies - Mandatory requirements
          </p>
        </CardHeader>
        {!collapsedSections.sepp && (
          <CardContent className="pt-0 space-y-4">
            {/* Show ALL detected SEPPs from Planning Portal */}
            {propertyData?.constraints?.applicableSepps && propertyData.constraints.applicableSepps.length > 0 && (() => {
              const SEPP_NAMES: Record<string, string> = {
                SEPP_SUSTAINABLE_BUILDINGS_2022: 'SEPP (Sustainable Buildings) 2022',
                SEPP_SUSTAINABLE_BUILDINGS: 'SEPP (Sustainable Buildings) 2022',
                SEPP_HOUSING_2021: 'SEPP (Housing) 2021',
                SEPP_65: 'SEPP (Housing) 2021',
                SEPP_RESILIENCE_HAZARDS_2021: 'SEPP (Resilience and Hazards) 2021',
              };
              const STRUCTURED_KEYS = new Set(Object.keys(SEPP_NAMES));
              const structured = propertyData.constraints.applicableSepps.filter((s: string) => STRUCTURED_KEYS.has(s));
              const unstructured = propertyData.constraints.applicableSepps.filter((s: string) => !STRUCTURED_KEYS.has(s));
              return (
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-4">
                  <div className="text-sm font-semibold text-purple-900 mb-2">
                    Applicable State Policies (from Planning Portal)
                  </div>
                  {structured.length > 0 && (
                    <div className="space-y-1 mb-2">
                      {structured.map((sepp: string) => (
                        <div key={sepp} className="text-xs text-purple-900">
                          ✓ {SEPP_NAMES[sepp]} — structured requirements shown below
                        </div>
                      ))}
                    </div>
                  )}
                  {unstructured.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-purple-200">
                      <div className="text-xs font-semibold text-amber-800 mb-1">
                        Assess manually — no structured data available:
                      </div>
                      {unstructured.map((sepp: string) => (
                        <div key={sepp} className="text-xs text-amber-700">
                          ⚠ {sepp.replace(/_/g, ' ')}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })()}
            
            {/* Planning Portal Source Layers - Purple shades for cohesion with left column Special Provisions */}
            {(sustainableInfo.waterTarget || sustainableInfo.climateZone || sustainableInfo.basixArea) && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                <div className="text-xs font-semibold text-purple-800 mb-1">
                  📍 Applied from NSW Planning Portal
                </div>
                <div className="text-xs text-purple-700 mb-2 italic">
                  BASIX sustainability requirements determined by location and climate zone
                </div>
                <div className="space-y-2">
                  {sustainableInfo.waterTarget && (
                    <>
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-xs bg-purple-100 text-purple-900 px-2 py-1 rounded border-l-4 border-purple-400 flex-1">
                        💧 Water Target: <span className="font-bold">{sustainableInfo.waterTarget}</span>
                      </div>
                      <button
                        onClick={() => setViewingPdfPage({
                          pageNumber: 11,
                          url: getSeppPdfUrl('sustainable_buildings', 11),
                          label: 'Schedule 2: Water Fixtures (Toilets, Showers, Taps)'
                        })}
                        className="p-1 rounded hover:bg-purple-100 transition-colors flex-shrink-0"
                        title="View Schedule 2 water fixture standards"
                      >
                        <FileImage className="w-4 h-4 text-purple-500 hover:text-purple-700" />
                      </button>
                    </div>
                    <div className="text-xs text-purple-700 ml-2">{NSW_PLANNING_CONSTANTS.BASIX.WATER_REDUCTION_PERCENT}% reduction from baseline water use via efficient fixtures</div>
                    </>
                  )}
                  {sustainableInfo.climateZone && (
                    <>
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-xs bg-purple-100 text-purple-900 px-2 py-1 rounded border-l-4 border-purple-500 flex-1">
                        🌡️ Climate Zone: <span className="font-bold">{sustainableInfo.climateZone}</span>
                      </div>
                      <button
                        onClick={() => setViewingPdfPage({
                          pageNumber: 9,
                          url: getSeppPdfUrl('sustainable_buildings', 9),
                          label: 'Table 3: Thermal Performance by Climate Zone'
                        })}
                        className="p-1 rounded hover:bg-purple-100 transition-colors flex-shrink-0"
                        title="View thermal performance standards for climate zone"
                      >
                        <FileImage className="w-4 h-4 text-purple-500 hover:text-purple-700" />
                      </button>
                    </div>
                    <div className="text-xs text-purple-700 ml-2">Climate Zone {sustainableInfo.climateZone} — verify thermal performance targets against Table 3 of SEPP Sustainable Buildings 2022.</div>
                    </>
                  )}
                  {sustainableInfo.basixArea && (
                    <>
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-xs bg-purple-100 text-purple-900 px-2 py-1 rounded border-l-4 border-purple-600 flex-1">
                        🏠 BASIX: <span className="font-bold">{sustainableInfo.basixArea}</span>
                      </div>
                      <a
                        href="https://www.planningportal.nsw.gov.au/publications/environmental-planning-instruments/state-environmental-planning-policy-sustainable-buildings-2022"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1 rounded hover:bg-purple-100 transition-colors flex-shrink-0"
                        title="View BASIX maps on NSW Planning Portal"
                      >
                        <FileImage className="w-4 h-4 text-purple-500 hover:text-purple-700" />
                      </a>
                    </div>
                    <div className="text-xs text-purple-700 ml-2">{sustainableInfo.basixArea} - specific thermal comfort and energy targets for this LGA</div>
                    </>
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
                No Housing SEPP structured requirements for this development type
              </p>
            )}


            {/* BASIX Energy & Thermal - Complex Calculations */}
            {sustainableInfo.basixArea && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <div className="text-2xl">⚡</div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <div className="font-semibold text-purple-900">BASIX Energy & Thermal Requirements</div>
                      <button
                        onClick={() => setViewingPdfPage({
                          pageNumber: 13,
                          url: getSeppPdfUrl('sustainable_buildings', 13),
                          label: 'Insulation Standards (Floors/Ceilings R-values)'
                        })}
                        className="p-1 rounded hover:bg-purple-100 transition-colors flex-shrink-0"
                        title="View insulation R-value standards"
                      >
                        <FileImage className="w-4 h-4 text-purple-500 hover:text-purple-700" />
                      </button>
                    </div>
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

            {/* Compliance-grade guarantee */}
            <div className="flex items-center gap-2 text-xs text-gray-600 border-t border-purple-100 pt-3 mt-4">
              <Shield className="h-4 w-4 text-green-600 flex-shrink-0" />
              <span>Provision text sourced from NSW Planning Portal and SEPP instruments. Zone eligibility, heritage classification, and property-specific constraints require independent verification against current legislation.</span>
            </div>
          </CardContent>
        )}
      </Card>


      {/* Transport Infrastructure Section - Shows when SEPP_TRANSPORT_INFRASTRUCTURE_2021 detected */}
      {transportRequirements.length > 0 && (
        <Card className="border-purple-200 bg-purple-50/30">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-purple-600" />
              <CardTitle className="text-lg text-purple-900">Transport Infrastructure Requirements</CardTitle>
            </div>
            <Badge className="bg-purple-100 text-purple-800 mt-2">SEPP (Transport and Infrastructure) 2021</Badge>
            <p className="text-sm text-purple-700 mt-2">
              Requirements for development near railway corridors, classified roads, and aviation facilities
            </p>
          </CardHeader>
          <CardContent>
            <StructuredSeppRequirements
              requirements={transportRequirements}
              compact={false}
            />
          </CardContent>
        </Card>
      )}


      {/* X7: Road Classification Alert */}
      {(() => {
        const roads: any[] = propertyData?.roadClassifications || [];
        if (!roads.length) return null;
        const highImpact = roads
          .map((r: any) => ({ ...r, impact: roadHierarchyAnnotation(r.functional_hierarchy || '', r.distance_meters) }))
          .filter((r: any) => r.impact.isHighImpact)
          .sort((a: any, b: any) => a.distance_meters - b.distance_meters);
        if (!highImpact.length) return null;
        const primary = highImpact[0];
        return (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-amber-900">
                  {primary.road_name} — {primary.functional_hierarchy}
                </p>
                <p className="text-xs text-amber-700 mt-0.5">{primary.impact.annotation}</p>
                {highImpact.length > 1 && (
                  <p className="text-xs text-amber-600 mt-0.5">
                    Also: {highImpact.slice(1).map((r: any) => r.road_name).join(', ')}
                  </p>
                )}
              </div>
            </div>
          </div>
        );
      })()}

      {/* X8: Housing Infrastructure Area */}
      {propertyData?.constraints?.hiaArea?.inHIA && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <Info className="h-4 w-4 text-purple-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-purple-900">
                Housing Infrastructure Area — {propertyData.constraints.hiaArea.hiaName}
              </p>
              {propertyData.constraints.hiaArea.specialControls && (
                <p className="text-xs text-purple-700 mt-0.5">
                  {propertyData.constraints.hiaArea.specialControls}
                </p>
              )}
              {propertyData.constraints.hiaArea.legislativeClause && (
                <p className="text-xs text-purple-500 mt-0.5">
                  {propertyData.constraints.hiaArea.legislativeClause}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

            {/* Housing SEPP LMR Section - Always shown */}
      {showHousingSEPPSection ? (
        <Card className="border-purple-200 bg-purple-50/30">
          <CardHeader
            className="cursor-pointer hover:bg-purple-100/50 transition-colors"
            onClick={() => toggleSection('lmr')}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {collapsedSections.lmr ? (
                  <ChevronRight className="h-5 w-5 text-purple-600" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-purple-600" />
                )}
                <Building2 className="h-5 w-5 text-purple-600" />
                <CardTitle className="text-lg text-purple-900">Multiple Occupancy Options</CardTitle>
              </div>
              <Badge className="bg-purple-100 text-purple-800">NSW Reforms</Badge>
            </div>
            <p className="text-sm text-purple-700 mt-1 ml-7">
              Duplexes, townhouses, apartments and other housing options under Low and Mid-Rise reforms
            </p>
          </CardHeader>
          {!collapsedSections.lmr && (
            <CardContent className="pt-0 space-y-3">
              {/* X4: Frontage check against LMR minimums */}
              {lotWidth && (() => {
                const status = lmrFrontageStatus(lotWidth);
                if (!status.excluded.length) return null;
                return (
                  <div className="bg-amber-50 border border-amber-200 rounded p-2">
                    <div className="flex items-start gap-1.5">
                      <AlertTriangle className="h-3.5 w-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="text-xs font-semibold text-amber-800">
                          Frontage {lotWidth.toFixed(1)}m
                        </span>
                        <span className="text-xs text-amber-700">
                          {' '}— below {status.excluded[0].minimumM}m minimum:
                          {' '}{status.excluded.map(e => e.label).join(', ')} not available
                        </span>
                        <span className="text-xs text-amber-600 block mt-0.5">
                          SEPP (Housing) 2021
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* X3: Battleaxe lot SEPP compliance */}
              {propertyData?.lotDimensions?.lotType === 'battleaxe' &&
               propertyData.lotDimensions.battleaxe && (
                <div className={`border rounded p-2 ${
                  propertyData.lotDimensions.battleaxe.meetsMinimumRequirements
                    ? 'bg-green-50 border-green-200'
                    : 'bg-red-50 border-red-200'
                }`}>
                  <div className="flex items-start gap-1.5">
                    <AlertTriangle className={`h-3.5 w-3.5 flex-shrink-0 mt-0.5 ${
                      propertyData.lotDimensions.battleaxe.meetsMinimumRequirements
                        ? 'text-green-600' : 'text-red-600'
                    }`} />
                    <div>
                      <span className={`text-xs font-semibold ${
                        propertyData.lotDimensions.battleaxe.meetsMinimumRequirements
                          ? 'text-green-800' : 'text-red-800'
                      }`}>
                        Battleaxe lot — access way {propertyData.lotDimensions.battleaxe.accessWayWidth.toFixed(1)}m wide
                      </span>
                      {propertyData.lotDimensions.battleaxe.meetsMinimumRequirements ? (
                        <span className="text-xs text-green-700 ml-1">
                          (meets 3m SEPP Housing 2021 minimum)
                        </span>
                      ) : (
                        <div>
                          <span className="text-xs text-red-700 ml-1">
                            (below 3m SEPP Housing 2021 minimum)
                          </span>
                          {propertyData.lotDimensions.battleaxe.complianceIssues?.length > 0 && (
                            <ul className="mt-0.5 ml-1">
                              {propertyData.lotDimensions.battleaxe.complianceIssues.map((issue: string, i: number) => (
                                <li key={i} className="text-xs text-red-700">• {issue}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              <HousingSEPPEligibilityCard
                zoneCode={zone}
                lotSize={lotSize}
                lotWidth={lotWidth}
                stationDistance={stationDistance}
                isLMRArea={isLMRArea}
                strataInfo={strataInfo}
                lepHeight={lepHeight}
                lepFsr={lepFsr}
              />
            </CardContent>
          )}
        </Card>
      ) : (
        <NotApplicableCard
          title="Low and Mid-Rise Housing Reforms"
          reason="Not applicable to this address. Property is not in an LMR area or lot size/width data unavailable."
          color="purple"
        />
      )}

      {/* ADG Section - Always shown */}
      {showADGSection ? (
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
                  <div className="h-4 bg-purple-200 rounded w-3/4"></div>
                  <div className="h-4 bg-indigo-200 rounded w-1/2"></div>
                </div>
              ) : adgRequirements.length > 0 ? (
                <div className="space-y-4">
                  <div className="text-sm text-gray-600 mb-3">
                    Showing {adgRequirements.length} high-value design criteria
                  </div>
                  {adgRequirements.map((req: any) => (
                    <div key={req.criteriaId} className="border-l-4 border-purple-300 pl-4 py-2">
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
                              url: getAdgPdfUrl(req.sourcePage),
                              label: `ADG ${req.criteriaId}`
                            })}
                            className="ml-3 text-xs text-purple-600 hover:text-purple-800 flex items-center gap-1"
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
                <>
                  <ADGSummaryCard developmentType={developmentType} zoneCode={zone} />

                  {/* ADG Building Separation Table hidden — setback_rules table not populated.
                     Re-enable once ADG 3F-1 data is ingested into setback_rules. */}

                  {adgStructuredRequirements.length > 0 && (
                    <div className="mt-4">
                      <StructuredSeppRequirements
                        requirements={adgStructuredRequirements}
                        compact={false}
                        onViewFullText={() => {}}
                      />
                    </div>
                  )}
                </>
              )}
            </CardContent>
          )}
        </Card>
      ) : (
        <NotApplicableCard
          title="Apartment Design Guide (ADG)"
          reason="Not applicable to this address. Property zone does not permit apartments and development type is not apartment-related."
          color="purple"
        />
      )}

      {/* TOD Parking Reductions - Always shown */}
      {showTODSection ? (
        <Card className="border-purple-200 bg-purple-50/30">
          <CardHeader
            className="cursor-pointer hover:bg-purple-100/50 transition-colors"
            onClick={() => toggleSection('tod')}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {collapsedSections.tod ? (
                  <ChevronRight className="h-5 w-5 text-purple-600" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-purple-600" />
                )}
                <Car className="h-5 w-5 text-purple-600" />
                <CardTitle className="text-lg text-purple-900">TOD Parking Reductions</CardTitle>
              </div>
              <div className="flex items-center gap-2">
                {isInDesignatedTOD && (
                  <Badge className="bg-purple-600 text-white">Designated TOD</Badge>
                )}
                <Badge className="bg-purple-100 text-purple-800">Transit Oriented</Badge>
              </div>
            </div>
            <p className="text-sm text-purple-700 mt-1 ml-7">
              {isInDesignatedTOD
                ? 'This property is within a designated TOD precinct under SEPP (Housing) 2021.'
                : (() => {
                    const reasons: string[] = [];
                    if (nearbyTransport.some(s => s.type === 'heavy_rail' && s.distance <= NSW_PLANNING_CONSTANTS.TOD.HEAVY_RAIL_WALKABLE_M)) {
                      reasons.push(`heavy rail station within ${NSW_PLANNING_CONSTANTS.TOD.HEAVY_RAIL_WALKABLE_M}m`);
                    }
                    if (nearbyTransport.some(s => s.type === 'light_rail' && s.distance <= NSW_PLANNING_CONSTANTS.TOD.LIGHT_RAIL_WALKABLE_M)) {
                      reasons.push(`light rail stop within ${NSW_PLANNING_CONSTANTS.TOD.LIGHT_RAIL_WALKABLE_M}m`);
                    }
                    if (nearbyTransport.some(s => s.type === 'bus' && s.distance <= NSW_PLANNING_CONSTANTS.TOD.BUS_WALKABLE_M && (s.frequency === 'high' || s.frequency === 'medium'))) {
                      reasons.push(`frequent bus service within ${NSW_PLANNING_CONSTANTS.TOD.BUS_WALKABLE_M}m`);
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
                <div className="bg-purple-100 border border-purple-300 rounded-lg p-3">
                  <p className="text-sm font-medium text-purple-900">
                    This property is in a designated TOD precinct
                  </p>
                  <p className="text-xs text-purple-700 mt-1">
                    Special parking provisions may apply under SEPP (Housing) 2021
                  </p>
                  {(propertyData?.constraints?.todPrecinct?.maxFSRBonus ||
                    propertyData?.constraints?.todPrecinct?.maxHeightBonus) && (
                    <div className="mt-2 pt-2 border-t border-purple-300">
                      <p className="text-xs font-semibold text-purple-900 mb-1">
                        TOD Development Standard Bonuses
                      </p>
                      <div className="grid grid-cols-2 gap-2">
                        {propertyData?.constraints?.todPrecinct?.maxFSRBonus && (
                          <div className="bg-white rounded border border-purple-200 px-2 py-1.5">
                            <p className="text-xs text-purple-600">Max FSR</p>
                            <p className="text-sm font-bold text-purple-900">
                              {propertyData.constraints.todPrecinct.maxFSRBonus}:1
                            </p>
                          </div>
                        )}
                        {propertyData?.constraints?.todPrecinct?.maxHeightBonus && (
                          <div className="bg-white rounded border border-purple-200 px-2 py-1.5">
                            <p className="text-xs text-purple-600">Max Height</p>
                            <p className="text-sm font-bold text-purple-900">
                              {propertyData.constraints.todPrecinct.maxHeightBonus}m
                            </p>
                          </div>
                        )}
                      </div>
                      <p className="text-xs text-purple-500 mt-1.5">
                        {propertyData?.constraints?.todPrecinct?.legislativeClause || 'SEPP (Housing) 2021'} —
                        Verify against current LEP controls until rezoning is gazetted.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Walking network distance from city2graph spatial API */}
              {(walkingDistanceLoading || walkingDistance) && (
                <div className="bg-white border border-purple-200 rounded-lg p-3">
                  <p className="text-xs font-semibold text-purple-900 mb-1">Walking Network Distance</p>
                  {walkingDistanceLoading ? (
                    <div className="animate-pulse h-3 bg-purple-100 rounded w-2/3" />
                  ) : walkingDistance && (
                    <>
                      <div className="flex items-center gap-4 mt-1">
                        <div>
                          <p className="text-xs text-gray-500">Walking route</p>
                          <p className={`text-sm font-bold ${walkingDistance.tod_eligible ? 'text-green-700' : 'text-red-700'}`}>
                            {walkingDistance.walking_m != null ? `${walkingDistance.walking_m}m` : '—'}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Crow-flies</p>
                          <p className="text-sm font-medium text-gray-700">
                            {walkingDistance.crow_flies_m != null ? `${walkingDistance.crow_flies_m}m` : '—'}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-500">Threshold</p>
                          <p className={`text-xs font-semibold px-1.5 py-0.5 rounded ${walkingDistance.tod_eligible ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                            {walkingDistance.tod_eligible ? `Within ${walkingDistance.threshold_m}m` : `Outside ${walkingDistance.threshold_m}m`}
                          </p>
                        </div>
                      </div>
                      <p className="text-xs text-gray-400 mt-1.5">
                        To {walkingDistance.station_name} via OSM walking network
                      </p>
                    </>
                  )}
                </div>
              )}

              {/* X18: Accelerated TOD warning — LEP controls remain in force until rezoning gazetted */}
              {acceleratedTodLayer?.results?.length > 0 && (
                <div className="bg-amber-50 border border-amber-300 rounded-lg p-3 flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-semibold text-amber-900">
                      Accelerated TOD Precinct — LEP controls remain in force
                    </p>
                    <p className="text-xs text-amber-800 mt-1">
                      This site is within an <strong>Accelerated TOD rezoning area</strong>.
                      The TOD bonus FSR and height standards do <strong>not yet apply</strong> — current LEP controls
                      remain in force until the rezoning is gazetted.
                      {propertyData?.constraints?.acceleratedTOD?.expectedRezoning
                        ? ` Rezoning expected: ${propertyData.constraints.acceleratedTOD.expectedRezoning}.`
                        : ''}
                    </p>
                  </div>
                </div>
              )}

              {/* Nearby Transport Detection */}
              <div className="bg-white border border-purple-100 rounded-lg p-3">
                <h4 className="text-xs font-semibold text-purple-800 mb-2">
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
                  <h4 className="text-xs font-semibold text-purple-800">
                    SEPP (Housing) 2021 Parking Provisions
                  </h4>
                </div>

                {/* Boarding House Parking */}
                <div className="bg-white border border-purple-200 rounded-lg p-3">
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
                        url: getSeppPdfUrl('housing', 11),
                        label: 'SEPP (Housing) 2021 - Boarding House Parking'
                      })}
                      className="text-purple-600 hover:text-purple-800 transition-colors p-1 rounded hover:bg-purple-50"
                    >
                      <FileImage className="h-5 w-5" />
                    </button>
                  </div>
                </div>

                {/* Co-Living Parking */}
                <div className="bg-white border border-purple-200 rounded-lg p-3">
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
                        url: getSeppPdfUrl('housing', 32),
                        label: 'SEPP (Housing) 2021 - Co-Living Parking'
                      })}
                      className="text-purple-600 hover:text-purple-800 transition-colors p-1 rounded hover:bg-purple-50"
                    >
                      <FileImage className="h-5 w-5" />
                    </button>
                  </div>
                </div>

                {/* Build-to-Rent Housing */}
                <div className="bg-white border border-purple-200 rounded-lg p-3">
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
                        url: getSeppPdfUrl('housing', 35),
                        label: 'SEPP (Housing) 2021 - Build-to-Rent Parking'
                      })}
                      className="text-purple-600 hover:text-purple-800 transition-colors p-1 rounded hover:bg-purple-50"
                    >
                      <FileImage className="h-5 w-5" />
                    </button>
                  </div>
                {/* In-Fill Affordable Housing */}
                <div className="bg-white border border-purple-200 rounded-lg p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-gray-900">In-Fill Affordable Housing</p>
                      <p className="text-xs text-gray-700 mt-1">
                        <strong>In accessible area:</strong> 0.2 parking spaces per dwelling
                      </p>
                      <p className="text-xs text-gray-700">
                        <strong>Otherwise:</strong> 0.5 parking spaces per dwelling
                      </p>
                      <p className="text-xs text-gray-500 mt-2">
                        SEPP (Housing) 2021, Clause 19 - In-fill affordable housing
                      </p>
                    </div>
                    <button
                      onClick={() => setViewingPdfPage({
                        pageNumber: 35,
                        url: getSeppPdfUrl('housing_2021', 35, 'infill_affordable'),
                        label: 'SEPP (Housing) 2021 - In-Fill Affordable Housing Parking'
                      })}
                      className="text-purple-600 hover:text-purple-800 transition-colors p-1 rounded hover:bg-purple-50"
                    >
                      <FileImage className="h-5 w-5" />
                    </button>
                  </div>
                </div>

                {/* Seniors Independent Living */}
                <div className="bg-white border border-purple-200 rounded-lg p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-gray-900">Seniors Independent Living</p>
                      <p className="text-xs text-gray-700 mt-1">
                        <strong>Social housing:</strong> 1 parking space per 5 dwellings
                      </p>
                      <p className="text-xs text-gray-700">
                        <strong>Other seniors housing:</strong> 0.5 parking spaces per bedroom
                      </p>
                      <p className="text-xs text-gray-500 mt-2">
                        SEPP (Housing) 2021, Schedule 4 Part 5 — Seniors housing parking
                      </p>
                    </div>
                    <button
                      onClick={() => setViewingPdfPage({
                        pageNumber: 47,
                        url: getSeppPdfUrl('housing_2021', 47, 'seniors_independent'),
                        label: 'SEPP (Housing) 2021 - Seniors Independent Living Parking'
                      })}
                      className="text-purple-600 hover:text-purple-800 transition-colors p-1 rounded hover:bg-purple-50"
                    >
                      <FileImage className="h-5 w-5" />
                    </button>
                  </div>
                </div>

                </div>

                {/* Affordable Housing / LHAC */}
                <div className="bg-white border border-purple-200 rounded-lg p-3">
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
                        url: getSeppPdfUrl('housing', 18),
                        label: 'SEPP (Housing) 2021 - Affordable Housing Parking'
                      })}
                      className="text-purple-600 hover:text-purple-800 transition-colors p-1 rounded hover:bg-purple-50"
                    >
                      <FileImage className="h-5 w-5" />
                    </button>
                  </div>
                </div>

                {/* Market-Rate Apartments */}
                <div className="bg-white border border-purple-200 rounded-lg p-3">
                  <p className="text-sm font-semibold text-gray-900">Residential Flat Buildings & Apartments</p>
                  <p className="text-xs text-gray-700 mt-1">
                    Parking rates determined by <strong>council DCP</strong>. SEPP (Housing) 2021 refers to ADG Part 3J, which defers to local planning controls.
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    Check the <strong>DCP Provisions</strong> tab for {lga} parking requirements.
                  </p>
                </div>

                {/* Accessible Area Definition */}
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <p className="text-xs font-semibold text-purple-900">What is an "Accessible Area"?</p>
                      <p className="text-xs text-purple-800 mt-1">
                        Land within <strong>800m walking distance</strong> of a public entrance to a railway, metro or light rail station (Schedule 11)
                      </p>
                    </div>
                    <button
                      onClick={() => setViewingPdfPage({
                        pageNumber: 115,
                        url: getSeppPdfUrl('housing', 115),
                        label: 'SEPP (Housing) 2021 - Accessible Area Definition'
                      })}
                      className="text-purple-600 hover:text-purple-800 transition-colors p-1 rounded hover:bg-purple-50"
                    >
                      <FileImage className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              </div>

            </CardContent>
          )}
        </Card>
      ) : (
        <NotApplicableCard
          title="Transit Oriented Development (TOD) Parking"
          reason="Not applicable to this address. Property is not in a designated TOD precinct and has no qualifying public transport within regulatory thresholds (800m rail, 600m light rail, 400m frequent bus)."
          color="purple"
        />
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
