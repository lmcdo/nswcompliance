/**
 * NSW Planning Portal API Integration
 * Real-time property data, zoning, and environmental overlays
 */

import { getRoadClassifications, type RoadClassification } from './road-classification-service';
import { getClauseNumbersForMapType } from './lep-local-provisions-mapping';
import { getKeySitesProvision } from './key-sites-map-provisions';

export interface NSWPropertyData {
 propId: number;
 address: string;
 landValue: string;
 valuationDate: string;
 propertyArea: string;
 zoneDescription: string;
 urbanity: string;
 geometry: {
 x: number;
 y: number;
 };
}

export interface LotGeometryData {
 geometry: {
 hasM: boolean;
 hasZ: boolean;
 rings: number[][][];
 spatialReference: {
 wkid: number;
 latestWkid?: number | null;
 };
 };
 cadId?: number;
 lotDescription?: string;
}

export interface PlanningConstraints {
 maxFsr: number | null;
 maxHeight: number | null;
 minLotSize: number | null;
 zone: string | null;
 zoneDescription: string | null;
 lga: string | null;
 precinctId?: string | null;
 precinctName?: string | null;
 formerCouncil?: string | null;
 heritage: boolean;
 heritageType?: string;
 heritageItemName?: string;
 heritageItemNumber?: string;
 heritageLegislativeClause?: string;
 heritageSignificance?: string;
 heritageLegislationUrl?: string;
 floodProne: boolean;
 floodInfo?: {
   name?: string;
   blockType?: string;
   blockStartDate?: string;
 } | null;
 bushfireProne: boolean;
 bushfireCategory?: string | null;
 acidSulfateSoils?: string;
 mineSubsidence?: {
   inDistrict: boolean;
   districtName?: string;
   lastUpdate?: string;
 } | null;
 landslideRisk?: {
   hasRisk: boolean;
   epiName?: string;
   lgaName?: string;
   layClass?: string;
   epiType?: string;
 } | null;
 contaminatedLand?: {
   hasNotifiedSites: boolean;
   nearestSite?: {
     name?: string;
     address?: string;
     managementClass?: string;
     contaminationType?: string;
     distance?: number; // meters
   };
 } | null;
 drinkingWaterCatchment?: {
   inCatchment: boolean;
   epiName?: string;
   lgaName?: string;
 } | null;
 terrestrialBiodiversity?: {
   inBiodiversityArea: boolean;
   epiName?: string;
   lgaName?: string;
 } | null;
 coastalEnvironment?: {
   inCoastalArea: boolean;
   zones?: string[]; // e.g., ["Coastal Wetlands", "Coastal Environment Area"]
 } | null;
 basixClimate: string | null;
 basixWater: string | null;

 // Phase 4: TOD/HIA fields
 todPrecinct?: TODPrecinctInfo;
 acceleratedTOD?: AcceleratedTODInfo;
 hiaArea?: HIAInfo;

 // Phase 1: Tree Canopy Coverage
 treeCanopy?: {
 coverage: string | null; // e.g., "35%" or "35"
 coverageClass: string | null; // e.g., "Medium-High"
 year: string;
 source: string;
 } | null;

 // Phase 6: Local Provisions (LEP Schedule 7)
 localProvisions?: LocalProvision[];

 // Spatial overlay constraints (PostGIS spatial_overlays table)
 additionalPermittedUses?: { hasAPU: boolean; schedules: string[] } | null;
 foreshoreBuildingLine?: { hasLine: boolean; layClass?: string } | null;
 landReservation?: { hasReservation: boolean; purpose?: string } | null;
 riparianLand?: { inRiparianArea: boolean; category?: string } | null;
 wetlands?: { inWetlandsArea: boolean } | null;
 keySite?: { isKeySite: boolean; clause?: string } | null;
 activeStreetFrontage?: { required: boolean; clause?: string } | null;
 dcpFloodMap?: { inFloodArea: boolean; classification?: string } | null;

 // Special Entertainment Precinct (Inner West LEP 2022, from council FeatureServer)
 specialEntertainmentPrecinct?: {
   inSEP: boolean;
   name?: string;   // "Inner West Special Entertainment Precinct" | "Draft Special Entertainment Precinct"
   isDraft?: boolean;
 } | null;

 // TOD precinct — polygon intersection (replaces walking-distance approximation for SEPP eligibility)
 todPrecinctSpatial?: {
   inTODPrecinct: boolean;
   classification?: string;  // "Transport Oriented Development Area" | "Accelerated TOD Precinct"
   isAccelerated?: boolean;  // Crows Nest, Bankstown, Hornsby, Kellyville etc.
   isDeferred?: boolean;
 } | null;

 // Planning instruments that apply to this property (from Land Application Map layer)
 landApplicationInstruments?: Array<{ type: string; name: string }> | null;

 // ePlanning Phase 1: Exclusion gates (true = excluded, false = not excluded, null = could not determine)
 lowMidRiseExcluded?: boolean | null;
 complyingExcluded?: boolean | null;
 exemptExcluded?: boolean | null;
 dualOccProhibited?: {
   prohibited: boolean;
   epiName?: string;
   lgaName?: string;
 } | null;
}

/**
 * Local Provision (LEP Part 6 Additional Local Provisions)
 * Special Entertainment Precincts, affordable housing, site-specific provisions
 */
export interface LocalProvision {
 class?: string;
 epiName?: string;
 title: string;
 description?: string;
 legislationUrl?: string;
 mapType?: string; // e.g., "SEP", "LAM", "KSM"
 clauseNumber?: string; // e.g., "6.32"
 provisionText?: string; // Full clause text from LEP
 pageNumber?: number; // Page number in LEP PDF
 isNearby?: boolean; // True if provision is for nearby property in same KSM area
}

/**
 * Transport Oriented Development (TOD) Precinct Information
 * From SEPP (Housing) 2021 TOD Sites Map
 */
export interface TODPrecinctInfo {
 inTODArea: boolean;
 precinctName: string;
 stationName?: string;
 stationDistance?: number;
 maxFSRBonus?: number;
 maxHeightBonus?: number;
 legislativeClause: string;
 seppReference: string;
}

/**
 * Accelerated TOD Precinct Information
 * Priority precincts for fast-tracked rezoning
 */
export interface AcceleratedTODInfo {
 inAcceleratedPrecinct: boolean;
 precinctName: string;
 expectedRezoning?: string;
 priorityArea: boolean;
}

/**
 * Housing Infrastructure Area (HIA) Information
 * Special infrastructure areas with modified controls
 */
export interface HIAInfo {
 inHIA: boolean;
 hiaName: string;
 specialControls?: string;
 legislativeClause?: string;
}

/**
 * ANEF (Australian Noise Exposure Forecast) Information
 * Aircraft noise zones from airport master plans
 */
export interface AnefInfo {
  inAnefZone: boolean;
  anefLevel: number | null;
  airport: {
    code: string;
    name: string;
    version: string;
  } | null;
  buildingAcceptability: Array<{
    buildingType: string;
    displayName: string;
    status: 'acceptable' | 'conditional' | 'unacceptable';
  }> | null;
  standardReference: string;
}

export interface PlanningLayer {
 layerName: string;
 results: Array<{
 [key: string]: any;
 legislationUrl?: string;
 'Legislative Clause'?: string;
 'EPI Name'?: string;
 }>;
}

// Suburb proximity map for Inner West LGA Part 6 nearby filtering.
// Only Part 6 clauses whose suburb is in the user's nearby set will show as "nearby".
// Suburbs not listed here (e.g. Rhodes) are outside the LGA and always filtered out.
const SUBURB_NEARBY_MAP: Record<string, string[]> = {
 'annandale': ['annandale', 'stanmore', 'enmore', 'st peters', 'marrickville'],
 'stanmore': ['stanmore', 'annandale', 'enmore', 'petersham', 'marrickville'],
 'enmore': ['enmore', 'annandale', 'stanmore', 'petersham', 'marrickville'],
 'st peters': ['st peters', 'annandale', 'stanmore', 'marrickville'],
 'marrickville': ['marrickville', 'petersham', 'stanmore', 'enmore', 'st peters'],
 'petersham': ['petersham', 'marrickville', 'stanmore', 'enmore'],
 'leichhardt': ['leichhardt', 'lilyfield', 'rozelle', 'annandale', 'haberfield'],
 'lilyfield': ['lilyfield', 'leichhardt', 'rozelle', 'annandale', 'balmain'],
 'rozelle': ['rozelle', 'lilyfield', 'leichhardt', 'balmain'],
 'balmain': ['balmain', 'rozelle', 'lilyfield', 'drummoyne'],
 'haberfield': ['haberfield', 'leichhardt', 'ashfield', 'five dock'],
 'ashfield': ['ashfield', 'haberfield', 'five dock'],
 'five dock': ['five dock', 'ashfield', 'haberfield'],
 'drummoyne': ['drummoyne', 'balmain', 'rozelle'],
};

function extractSuburbFromTitle(title: string): string | null {
 // Try comma-suburb pattern first: "...Street, Leichhardt"
 const commaMatch = title.match(/,\s*([A-Za-z][A-Za-z\s]*?)(?:\s*$)/);
 if (commaMatch) return commaMatch[1].trim().toLowerCase();
 // Fallback: "at Suburb" at end (e.g. "...Mixed Use at Haberfield")
 const atMatch = title.match(/\bat\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*$/);
 if (atMatch) return atMatch[1].trim().toLowerCase();
 return null;
}

function extractSuburbFromAddress(address: string): string | null {
 // Try comma-suburb pattern: "123 Street, Suburb NSW 2038"
 const commaMatch = address.match(/,\s*([A-Za-z][A-Za-z\s]*?)(?:\s+NSW|\s*$)/i);
 if (commaMatch) return commaMatch[1].trim().toLowerCase();
 // Planning Portal returns no comma: "185 PARRAMATTA ROAD ANNANDALE 2038"
 // Match word(s) before postcode or NSW
 const noCommaMatch = address.match(/([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:NSW\s+)?\d{4}\s*$/i);
 if (noCommaMatch) {
  // Could be "ROAD ANNANDALE" - take last word only if second-to-last looks like a street type
  const words = noCommaMatch[1].trim().split(/\s+/);
  if (words.length === 2) {
   const streetTypes = ['road', 'street', 'avenue', 'drive', 'lane', 'way', 'place', 'court'];
   if (streetTypes.includes(words[0].toLowerCase())) {
    return words[1].toLowerCase();
   }
  }
  return words[words.length - 1].toLowerCase();
 }
 return null;
}

function isSuburbNearby(userSuburb: string, clauseSuburb: string): boolean {
 if (userSuburb === clauseSuburb) return true;
 const nearbySet = SUBURB_NEARBY_MAP[userSuburb];
 if (nearbySet) return nearbySet.includes(clauseSuburb);
 // If user suburb not in map, allow all Inner West suburbs but block non-Inner West ones
 const allInnerWestSuburbs = new Set(Object.keys(SUBURB_NEARBY_MAP));
 return allInnerWestSuburbs.has(clauseSuburb);
}

export interface StrataInfo {
  isStrata: boolean;
  source: 'valuation_fallback' | 'address_heuristic' | 'combined' | null;
  strataUnit: string | null;
}

// ---------------------------------------------------------------------------
// ePlanning MapServer Layer Registry
// ---------------------------------------------------------------------------
// All ePlanning layer IDs in one place. When DPE republishes a service and
// shifts layer IDs, update here — the watchdog (scripts/dcp_watchdog.py)
// health-checks these IDs weekly and alerts on drift.
//
// `geometryType`: 'point' for area layers (centroid query is fine),
//                 'polygon' for corridor/linear layers (need lot boundary).
// `expectField`:  field the watchdog checks to verify the layer hasn't moved.

const EPLANNING_BASE = 'https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning';

export const EPLANNING_LAYERS = {
  // Phase 1: Correctness — exclusion gates
  lowMidRiseExclusion:    { service: 'Planning_Portal_SEPP',              id: 776, expectField: 'LAY_CLASS', geometryType: 'point' as const },
  complyingExclusion:     { service: 'Planning_Portal_SEPP',              id: 92,  expectField: 'LAY_CLASS', geometryType: 'point' as const },
  exemptExclusion:        { service: 'Planning_Portal_SEPP',              id: 93,  expectField: 'LAY_CLASS', geometryType: 'point' as const },
  dualOccProhibition:     { service: 'Planning_Portal_Local_Provisions',  id: 452, expectField: 'LAY_CLASS', geometryType: 'point' as const },

  // Phase 2: New data
  floodPlanningMap:       { service: 'Planning_Portal_Hazard',            id: 230, expectField: 'LAY_CLASS', geometryType: 'point' as const },
  contributionPlan:       { service: 'Planning_Portal_Development_Control', id: 219, expectField: 'PLAN_NAME', geometryType: 'point' as const },
  specialInfrastructure:  { service: 'Planning_Portal_Development_Control', id: 218, expectField: 'LAY_CLASS', geometryType: 'point' as const },
  sunAccessProtection:    { service: 'Planning_Portal_Local_Provisions',  id: 572, expectField: 'LAY_CLASS', geometryType: 'point' as const },
  sunPlaneProtection:     { service: 'Planning_Portal_Local_Provisions',  id: 573, expectField: 'LAY_CLASS', geometryType: 'point' as const },

  // Phase 3: Enrichment
  deferredTOD:            { service: 'Planning_Portal_SEPP',              id: 765, expectField: 'LAY_CLASS', geometryType: 'point' as const },
  townCentres:            { service: 'Planning_Portal_SEPP',              id: 766, expectField: 'LAY_CLASS', geometryType: 'point' as const },
  metroCorridorProtection:{ service: 'Planning_Portal_SEPP',              id: 745, expectField: 'LAY_CLASS', geometryType: 'polygon' as const },
  shortTermRental:        { service: 'Planning_Portal_SEPP',              id: 160, expectField: 'LAY_CLASS', geometryType: 'point' as const },

  // Phase 4: Environmental
  landslideRisk:          { service: 'Planning_Portal_Hazard',            id: 232, expectField: 'LAY_CLASS', geometryType: 'point' as const },
  groundwaterVulnerability:{ service: 'Planning_Portal_Protection',       id: 237, expectField: 'LAY_CLASS', geometryType: 'point' as const },
  obstacleLimitationSurface:{ service: 'Planning_Portal_Protection',     id: 239, expectField: 'LAY_CLASS', geometryType: 'point' as const },
  allowableClearing:      { service: 'Planning_Portal_SEPP',              id: 289, expectField: 'LAY_CLASS', geometryType: 'point' as const },
} as const;

/**
 * Build a point query URL for an ePlanning layer.
 */
export function ePlanningPointQuery(
  layerKey: keyof typeof EPLANNING_LAYERS,
  lon: number,
  lat: number,
  outFields = '*',
): string {
  const layer = EPLANNING_LAYERS[layerKey];
  return (
    `${EPLANNING_BASE}/${layer.service}/MapServer/${layer.id}/query?` +
    `geometry=${lon},${lat}&geometryType=esriGeometryPoint&` +
    `spatialRel=esriSpatialRelIntersects&outFields=${outFields}&` +
    `returnGeometry=false&f=json&inSR=4283`
  );
}

/**
 * Build a polygon query URL for an ePlanning layer (for corridor/linear features).
 * `rings` should be the lot boundary rings in WGS84 (EPSG:4283).
 */
export function ePlanningPolygonQuery(
  layerKey: keyof typeof EPLANNING_LAYERS,
  rings: number[][][],
  outFields = '*',
): string {
  const layer = EPLANNING_LAYERS[layerKey];
  const geometry = JSON.stringify({ rings, spatialReference: { wkid: 4283 } });
  return (
    `${EPLANNING_BASE}/${layer.service}/MapServer/${layer.id}/query?` +
    `geometry=${encodeURIComponent(geometry)}&geometryType=esriGeometryPolygon&` +
    `spatialRel=esriSpatialRelIntersects&outFields=${outFields}&` +
    `returnGeometry=false&f=json&inSR=4283`
  );
}

export class NSWPlanningPortalService {
 private static BASE_URL = 'https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi';
 private static VALUATION_URL = 'https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/5/query';

 /**
 * Search for property by address using NSW Planning Portal
 * Returns the best matching result from multiple candidates
 * Fetches multiple results and filters for best match to avoid keyword collisions
 */
 static async searchProperty(address: string): Promise<{ propId: number; address: string; GURASID: number } | null> {
 try {
 const controller = new AbortController();
 const timeoutId = setTimeout(() => controller.abort(), 15000);

 // Fetch multiple results to find best match (fixes "Ashfield St" returning "Ashfield Place Glen Alpine" bug)
 const response = await fetch(
 `${this.BASE_URL}/address?a=${encodeURIComponent(address)}&noOfRecords=5`,
 {
 signal: controller.signal,
 headers: {
 'Accept': 'application/json',
 'User-Agent': 'ComplianceEngine/1.0'
 }
 }
 );

 clearTimeout(timeoutId);

 if (!response.ok) {
 throw new Error(`Address search failed: ${response.status}`);
 }

 const results = await response.json() as any[];

 if (!results || results.length === 0) {
 return null;
 }

 // Extract search components for matching
 const searchLower = address.toLowerCase();
 const postcodeMatch = address.match(/\b(\d{4})\b/);
 const searchPostcode = postcodeMatch ? postcodeMatch[1] : null;

 // Score each result by relevance
 const scored = results.map((result: any) => {
   const resultLower = result.address.toLowerCase();
   let score = 0;

   // Exact match = highest priority
   if (resultLower === searchLower) score += 100;

   // Postcode match = high priority (filters out wrong suburbs)
   if (searchPostcode && resultLower.includes(searchPostcode)) score += 50;

   // Suburb name match (but not just any keyword match)
   const searchWords = searchLower.split(/\s+/).filter(w => w.length > 2 && !w.match(/^\d/));
   const resultWords = resultLower.split(/\s+/);
   const matchingWords = searchWords.filter(w => resultWords.includes(w)).length;
   score += matchingWords * 10;

   // Penalize if different state or far-off postcode
   if (searchPostcode && !resultLower.includes(searchPostcode)) {
     const resultPostcodeMatch = result.address.match(/\b(\d{4})\b/);
     if (resultPostcodeMatch) {
       const diff = Math.abs(parseInt(searchPostcode) - parseInt(resultPostcodeMatch[1]));
       if (diff > 100) score -= 50; // Very different postcode area
     }
   }

   return { result, score };
 });

 // Sort by score descending and return best match
 scored.sort((a, b) => b.score - a.score);

 console.log(`[NSW Planning Portal] Address search: "${address}"`);
 console.log(`[NSW Planning Portal] Top match: "${scored[0].result.address}" (score: ${scored[0].score})`);
 if (scored.length > 1) {
   console.log(`[NSW Planning Portal] Alt matches: ${scored.slice(1).map(s => `"${s.result.address}" (${s.score})`).join(', ')}`);
 }

 return scored[0].result;
 
 } catch (error) {
 console.error('Property search error:', error);
 return null;
 }
 }

 /**
 * Get planning layers (zoning, height, FSR, heritage, etc.)
 * Now includes 10s timeout to prevent indefinite hangs
 */
 static async getPlanningLayers(propId: number, retryCount: number = 0): Promise<PlanningLayer[]> {
 const controller = new AbortController();
 const timeoutId = setTimeout(() => controller.abort(), 10000);

 try {
 const response = await fetch(
 `${this.BASE_URL}/layerintersect?type=property&id=${propId}&layers=epi`,
 { signal: controller.signal }
 );

 clearTimeout(timeoutId);

 if (response.status === 429) {
 if (retryCount < 2) {
 await new Promise(resolve => setTimeout(resolve, 2000));
 return this.getPlanningLayers(propId, retryCount + 1);
 }
 return [];
 }

 if (!response.ok) {
 throw new Error(`Planning layers failed: ${response.status}`);
 }

 const data = await response.json();
 return data || [];

 } catch (error) {
 clearTimeout(timeoutId);

 if (error instanceof Error && error.name === 'AbortError') {
 if (retryCount < 1) {
 await new Promise(resolve => setTimeout(resolve, 2000));
 return this.getPlanningLayers(propId, retryCount + 1);
 }
 return [];
 }

 console.error('Planning layers error:', error);
 return [];
 }
 }


 /**
 * Get property valuation and physical data
 */
 static async getPropertyValuation(propId: number): Promise<NSWPropertyData | null> {
 try {
 const controller = new AbortController();
 const timeoutId = setTimeout(() => controller.abort(), 15000);

 const response = await fetch(
 `${this.VALUATION_URL}?where=propid=${propId}&outFields=propid,address,val1_bd,val1_lv,prop_area,zone_desc,urbanity&f=json`,
 {
 signal: controller.signal,
 headers: {
 'Accept': 'application/json',
 'User-Agent': 'ComplianceEngine/1.0'
 }
 }
 );
 
 clearTimeout(timeoutId);
 
 if (!response.ok) {
 throw new Error(`Property valuation failed: ${response.status}`);
 }
 
 const data = await response.json() as any;
 
 if (data.features && data.features.length > 0) {
 const feature = data.features[0];
 const attrs = feature.attributes;
 const geom = feature.geometry;
 
 return {
 propId: attrs.propid,
 address: attrs.address?.trim() || '',
 landValue: attrs.val1_lv || 'Unknown',
 valuationDate: attrs.val1_bd || 'Unknown',
 propertyArea: attrs.prop_area || 'Unknown',
 zoneDescription: attrs.zone_desc || 'Unknown',
 urbanity: attrs.urbanity || 'U',
 geometry: {
 x: geom?.x || 0,
 y: geom?.y || 0
 }
 };
 }
 
 return null;

 } catch (error) {
 console.error('Property valuation error:', error);
 return null;
 }
 }

 /**
 * Get lot geometry (polygon boundary) for a property
 * Returns detailed boundary coordinates for dimension calculations
 */
 static async getLotGeometry(propId: number): Promise<LotGeometryData | null> {
 try {
 const controller = new AbortController();
 const timeoutId = setTimeout(() => controller.abort(), 15000);

 const response = await fetch(
 `${this.BASE_URL}/lot?propId=${propId}`,
 {
 signal: controller.signal,
 headers: {
 'Accept': 'application/json',
 'Origin': 'https://www.planningportal.nsw.gov.au',
 'Referer': 'https://www.planningportal.nsw.gov.au/'
 }
 }
 );

 clearTimeout(timeoutId);

 if (!response.ok) {
 console.warn(`Lot geometry fetch failed: ${response.status}`);
 return null;
 }

 const data = await response.json();

 if (data && data.length > 0) {
 const lot = data[0];
 return {
 geometry: lot.geometry,
 cadId: lot.attributes?.CADID,
 lotDescription: lot.attributes?.LotDescription
 };
 }

 return null;
 } catch (error) {
 console.warn('Lot geometry fetch failed:', error);
 return null;
 }
 }

 /**
 * Get TOD and HIA layer data from NSW Planning Portal
 * Queries SEPP Housing 2021 MapServer for TOD boundaries
 * Phase 3: Separate API call for TOD/HIA detection
 */
 static async getTODLayers(geometry: { x: number; y: number }): Promise<PlanningLayer[]> {
 const todController = new AbortController();
 const accController = new AbortController();
 const todTimeout = setTimeout(() => todController.abort(), 8000);
 const accTimeout = setTimeout(() => accController.abort(), 8000);

 try {
 const todUrl = `https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/SEPP_Housing_2021/MapServer/3/query?` +
 `geometry=${geometry.x},${geometry.y}&geometryType=esriGeometryPoint&` +
 `spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json`;

 const acceleratedUrl = `https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning/Planning_Portal_SEPP/MapServer/759/query?` +
 `geometry=${geometry.x},${geometry.y}&geometryType=esriGeometryPoint&` +
 `spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json`;

 const [todResponse, acceleratedResponse] = await Promise.all([
 fetch(todUrl, { signal: todController.signal }).catch(() => null),
 fetch(acceleratedUrl, { signal: accController.signal }).catch(() => null)
 ]);

 clearTimeout(todTimeout);
 clearTimeout(accTimeout);

 const todLayers: PlanningLayer[] = [];

 if (todResponse?.ok) {
 const todData = await todResponse.json();
 if (todData.features?.length > 0) {
 todLayers.push({
 layerName: 'Transport Oriented Development Sites Map',
 results: todData.features.map((f: any) => f.attributes)
 });
 }
 }

 if (acceleratedResponse?.ok) {
 const acceleratedData = await acceleratedResponse.json();
 if (acceleratedData.features?.length > 0) {
 todLayers.push({
 layerName: 'Accelerated TOD Precincts Rezoning Areas Map',
 results: acceleratedData.features.map((f: any) => f.attributes)
 });
 }
 }

 return todLayers;

 } catch (error) {
 clearTimeout(todTimeout);
 clearTimeout(accTimeout);
 // Graceful degradation — TOD layers are non-critical
 return [];
 }
 }

 /**
 * Extract planning constraints from layers
 */
 static extractPlanningConstraints(layers: PlanningLayer[], address?: string): PlanningConstraints & { applicableSepps?: string[] } {
 const constraints: PlanningConstraints & { applicableSepps?: string[] } = {
 maxFsr: null,
 maxHeight: null,
 minLotSize: null,
 zone: null,
 zoneDescription: null,
 lga: null,
 heritage: false,
 floodProne: false,
 bushfireProne: false,
 basixClimate: null,
 basixWater: null,
 applicableSepps: []
 };

 layers.forEach(layer => {
 layer.results?.forEach(result => {
 switch (layer.layerName) {
 case 'Floor Space Ratio Map':
 // From API: "Floor Space Ratio": "0.6"
 if (result['Floor Space Ratio']) {
 constraints.maxFsr = parseFloat(result['Floor Space Ratio']);
 }
 if (result['LGA Name']) {
 constraints.lga = result['LGA Name'];
 }
 break;
 
 case 'Height of Buildings Map':
 // From API: "Maximum Building Height": "14"
 if (result['Maximum Building Height']) {
 constraints.maxHeight = parseFloat(result['Maximum Building Height']);
 }
 break;
 
 case 'Land Zoning Map':
 // From API: "Zone": "R4", "title": "R4: High Density Residential"
 if (result['Zone']) {
 constraints.zone = result['Zone'];
 }
 // Extract official zone description from title field
 if (result['title']) {
 constraints.zoneDescription = result['title'];
 }
 // Extract LGA from Land Zoning Map
 if (result['LGA Name']) {
 constraints.lga = result['LGA Name'];
 }
 break;
 
 case 'Lot Size Map':
 constraints.minLotSize = parseFloat(result['Lot Size'] || '0') || null;
 break;
 
 case 'Heritage Map':
 constraints.heritage = true;
 constraints.heritageType = result['Heritage Type'];
 constraints.heritageItemName = result['Item Name'];
 constraints.heritageItemNumber = result['Item Number'];
 constraints.heritageLegislativeClause = result['Legislative Clause'];
 constraints.heritageSignificance = result['Significance'];
 constraints.heritageLegislationUrl = result['legislationUrl'];
 break;
 
 case 'Special Provisions':
 // Extract BASIX data
 if (result['Type'] === 'Climate Zones' && result['Map Type'] === 'CLM') {
 constraints.basixClimate = result['Class'];
 }
 if (result['Type']?.includes('Water Use')) {
 constraints.basixWater = result['Class'];
 }
 
 // Extract applicable SEPPs
 this.extractApplicableSepps(result, constraints);
 break;
 
 case 'Acid Sulfate Soils Map':
 constraints.acidSulfateSoils = result['Class'];
 // Extract LGA from Acid Sulfate Soils Map
 if (result['LGA Name']) {
 constraints.lga = result['LGA Name'];
 }
 break;

 case 'Land Application Map':
 if (result['LGA Name']) {
 constraints.lga = result['LGA Name'];
 }
 // Collect all instruments/maps that apply to this property
 {
 const instrName = result['EPI Name'] || result['Name'] || result['name'];
 const instrType = result['Type'] || result['EPI Type'] || 'Instrument';
 if (instrName) {
   if (!constraints.landApplicationInstruments) constraints.landApplicationInstruments = [];
   if (!constraints.landApplicationInstruments.some(i => i.name === instrName)) {
     constraints.landApplicationInstruments.push({ type: instrType, name: instrName });
   }
 }
 }
 break;
 
 case 'Greater Sydney Tree Canopy Cover 2019':
 constraints.treeCanopy = {
 coverage: result['Canopy %'] || result['Tree Canopy Cover %'] || result['Canopy_Cover'],
 coverageClass: result['Cover Class'] || result['Canopy_Class'] || result['Canopy Class'],
 year: '2019',
 source: 'Greater Sydney Tree Canopy Cover 2019'
 };
 break;

 // ===== PHASE 5: TOD/HIA EXTRACTION =====
 case 'Transport Oriented Development Sites Map':
 case 'TOD Precinct':
 case 'SEPP Housing 2021 - TOD':
 case 'SEPP (Housing) 2021':
 constraints.todPrecinct = {
 inTODArea: true,
 precinctName: result['Precinct Name'] || result['PrecinctName'] ||
 result['Station Name'] || result['StationName'] ||
 result['Name'] || 'TOD Precinct',
 stationName: result['Station Name'] || result['StationName'] || result['STATION_NAME'],
 stationDistance: result['Distance to Station'] || result['StationDistance'] ||
 result['DISTANCE'] ? parseFloat(result['Distance to Station'] || result['StationDistance'] || result['DISTANCE']) : undefined,
 maxFSRBonus: result['Maximum FSR'] || result['Max FSR'] || result['FSR'] ?
 parseFloat(result['Maximum FSR'] || result['Max FSR'] || result['FSR']) : 2.5,
 maxHeightBonus: result['Maximum Height'] || result['Max Height'] || result['HEIGHT'] ?
 parseFloat(result['Maximum Height'] || result['Max Height'] || result['HEIGHT']) : 24,
 legislativeClause: result['Legislative Clause'] || result['Clause'] || 'Clause 4.4',
 seppReference: result['EPI Name'] || result['SEPP'] || 'SEPP (Housing) 2021'
 };
 break;

 case 'Accelerated TOD Precincts Rezoning Areas Map':
 case 'Accelerated Transport Oriented Development':
 case 'Priority Precincts':
 constraints.acceleratedTOD = {
 inAcceleratedPrecinct: true,
 precinctName: result['Precinct Name'] || result['PrecinctName'] ||
 result['Name'] || 'Accelerated TOD Precinct',
 expectedRezoning: result['Rezoning Date'] || result['ExpectedDate'] ||
 result['Expected_Rezoning'] || result['REZONING_DATE'],
 priorityArea: true
 };
 break;

 case 'Housing Infrastructure Areas':
 case 'HIA Map':
 case 'State Significant Development':
 constraints.hiaArea = {
 inHIA: true,
 hiaName: result['HIA Name'] || result['Name'] || result['Area Name'] || 'HIA Area',
 specialControls: result['Special Controls'] || result['Controls'] || result['CONTROLS'],
 legislativeClause: result['Legislative Clause'] || result['Clause']
 };
 break;

			case 'Local Provisions':
				if (process.env.NODE_ENV === 'development') {
					console.log('Extracting Local Provisions:', result);
				}
				if (!constraints.localProvisions) {
					constraints.localProvisions = [];
				}

				// Extract Map Type and get clause numbers (EPI-name-aware for LGA-specific lookup)
				const mapType = result['Map Type'];
				const epiName = result['EPI Name'];
				const clauseNumbers = mapType ? getClauseNumbersForMapType(mapType, epiName) : [];

				// Store basic info from Planning Portal
				const localProvision: LocalProvision = {
					class: result['Class'],
					epiName: result['EPI Name'],
					title: result['title'] || result['Title'],
					description: result['Description'],
					legislationUrl: result['legislationUrl'],
					mapType: mapType,
					clauseNumber: clauseNumbers[0] // Use first clause if multiple
				};

				// Provision text and page will be fetched on-demand via API
				constraints.localProvisions.push(localProvision);

				if (process.env.NODE_ENV === 'development') {
					console.log('Local Provisions extracted:', {
						...localProvision,
						clauseNumbers
					});
				}
				break;

			case 'Key Sites Map':
			case 'Additional Permitted Uses Map':
				if (process.env.NODE_ENV === 'development') {
					console.log(`Extracting ${layer.layerName}:`, result);
				}
				if (!constraints.localProvisions) {
					constraints.localProvisions = [];
				}

				// Parse Legislative Clause field (e.g., "Clauses 4.3C, 4.4, 6.14, 6.15")
				const legislativeClause = result['Legislative Clause'];
				let extractedClauses: string[] = [];
				if (legislativeClause) {
					// Extract clause numbers from text like "Clauses 4.3C, 4.4, 6.14, 6.15" or "Clause 6.14"
					const matches = legislativeClause.match(/(\d+\.\d+[A-Z]?)/g);
					if (matches) {
						extractedClauses = matches;
					}
				}

				// Create a provision for each clause
				// Page numbers come from getKeySitesProvision imported at top
				//
				// FILTER STRATEGY:
				// - Part 4 clauses (4.3C, 4.4): Apply based on zone restrictions (applicableZones)
				//   - If applicableZones defined, only show if property zone matches
				//   - If no applicableZones, apply to ALL Key Sites
				// - Part 6 clauses: Site-specific, but Planning Portal returns ALL clauses in the KSM polygon
				//   - Show exact address matches (required)
				//   - Mark nearby clauses as "nearby" (optional to display)
				// General Part 6 provisions that are NOT site-specific Key Sites.
				// These are zone-based or thematic clauses the Planning Portal may include
				// in the Legislative Clause field but which don't identify specific properties.
				const NON_SITE_SPECIFIC_CLAUSES = new Set([
					'6.14', // Diverse housing
					'6.15', // Development control plans for certain development
					'6.21', // Business and office premises in Zones E3 and E4
					'6.22', // Dwellings and residential flat buildings in Zone E3
					'6.23', // Residential accommodation as part of mixed use in Zone E3
					'6.33', // Affordable housing
				]);

				for (const clauseNum of extractedClauses) {
					// Skip general Part 6 provisions - not site-specific Key Sites
					if (NON_SITE_SPECIFIC_CLAUSES.has(clauseNum)) continue;

					const ksmProvision = getKeySitesProvision(clauseNum);

					// Check zone-specific filtering for Part 4 clauses
					if (ksmProvision?.applicableZones && ksmProvision.applicableZones.length > 0) {
						// Extract zone code (e.g., "R1" from "R1 General Residential")
						const propertyZoneCode = constraints.zone?.split(' ')[0];
						const zoneMatches = propertyZoneCode && ksmProvision.applicableZones.includes(propertyZoneCode);
						if (!zoneMatches) {
							if (process.env.NODE_ENV === 'development') {
								console.log(`Skipping clause ${clauseNum} - zone ${propertyZoneCode} not in applicable zones: ${ksmProvision.applicableZones.join(', ')}`);
							}
							continue; // Skip this provision - doesn't apply to this zone
						}
					}

					const clauseTitle = ksmProvision?.title || `${layer.layerName} - ${result['Label'] || result['Class']} (Clause ${clauseNum})`;

					let isNearby = false;

					// Check if Part 6 clause matches this specific property address
					if (clauseNum.startsWith('6.')) {
						// Part 6 clause - check if title matches property address
						const addressParts = address?.toLowerCase().split(/[\s,]+/) || [];
						const titleLower = clauseTitle.toLowerCase();

						// Check if street name and/or number appears in clause title
						const hasAddressMatch = addressParts.some(part =>
							part.length > 2 && titleLower.includes(part)
						);

						if (!hasAddressMatch) {
							// Check suburb proximity - only show as nearby if geographically close
							const clauseSuburb = extractSuburbFromTitle(clauseTitle);
							const userSuburb = extractSuburbFromAddress(address || '');
								if (clauseSuburb && userSuburb && !isSuburbNearby(userSuburb, clauseSuburb)) {
								// Suburb is too far away (e.g., Rhodes for an Annandale search) - skip
								if (process.env.NODE_ENV === 'development') {
									console.log(`Skipping Part 6 clause ${clauseNum} - suburb "${clauseSuburb}" not near "${userSuburb}"`);
								}
								continue;
							}
							// This Part 6 clause is for a nearby property in the same area
							isNearby = true;
							if (process.env.NODE_ENV === 'development') {
								console.log(`Marking Part 6 clause ${clauseNum} as nearby - doesn't match address: ${address}`);
								console.log(`  Clause title: ${clauseTitle}`);
							}
						}
					}

					const provision: LocalProvision = {
						class: result['Class'] || result['Label'],
						epiName: result['EPI Name'],
						title: clauseTitle,
						legislationUrl: result['legislationUrl'],
						mapType: layer.layerName === 'Key Sites Map' ? 'KSM' : 'APU',
						clauseNumber: clauseNum,
						pageNumber: ksmProvision?.pageNumber,
						isNearby: isNearby // Mark nearby provisions
					};
					constraints.localProvisions.push(provision);
				}

				if (process.env.NODE_ENV === 'development') {
					console.log(`${layer.layerName} provisions added:`, extractedClauses.length);
				}
				break;

 // ===== END PHASE 5 =====
 }
 });
 });

 return constraints;
 }

 /**
 * Extract applicable SEPPs from special provisions data
 */
 static extractApplicableSepps(result: any, constraints: PlanningConstraints & { applicableSepps?: string[] }): void {
 // Look for SEPP identifiers in various fields
 const searchFields = ['Type', 'Category', 'EPI Name', 'Legislative Clause', 'Description', 'Map Type'];
 const seppKeywords = ['sepp', 'state environmental planning policy'];
 
 for (const field of searchFields) {
 const value = result[field];
 if (typeof value === 'string') {
 const lowerValue = value.toLowerCase();
 
 // Check if this field mentions any SEPP
 if (seppKeywords.some(keyword => lowerValue.includes(keyword))) {
 // Extract SEPP number/identifier
 const seppMatch = value.match(/sepp[^\d]*(\d+)/i) || value.match(/state environmental planning policy[^\d]*(\d+)/i);
 if (seppMatch) {
 const seppNumber = seppMatch[1];
 const seppIdentifier = `SEPP_${seppNumber}`;
 
 if (!constraints.applicableSepps?.includes(seppIdentifier)) {
 constraints.applicableSepps?.push(seppIdentifier);
 }
 }
 
 // Also check for specific known SEPPs
 if (lowerValue.includes('housing')) {
 if (!constraints.applicableSepps?.includes('SEPP_HOUSING_2021')) {
 constraints.applicableSepps?.push('SEPP_HOUSING_2021');
 }
 }
 
 if (lowerValue.includes('planning') && lowerValue.includes('systems')) {
 if (!constraints.applicableSepps?.includes('SEPP_PLANNING_SYSTEMS_2021')) {
 constraints.applicableSepps?.push('SEPP_PLANNING_SYSTEMS_2021');
 }
 }
 
 if (lowerValue.includes('resilience') || lowerValue.includes('hazards')) {
 if (!constraints.applicableSepps?.includes('SEPP_RESILIENCE_HAZARDS_2021')) {
 constraints.applicableSepps?.push('SEPP_RESILIENCE_HAZARDS_2021');
 }
 }
 }
 }
 }
 }

 /**
 * Get property coordinates (WGS84 lat/lon) from address
 * Used by precinct-service for PostGIS geometric matching
 */
 static async getPropertyCoordinates(address: string): Promise<{ latitude: number; longitude: number } | null> {
   try {
     const searchResult = await this.searchProperty(address);
     if (!searchResult) {
       return null;
     }

     const propertyData = await this.getPropertyValuation(searchResult.propId);
     if (!propertyData || !propertyData.geometry) {
       return null;
     }

     // Convert Web Mercator (x, y) to WGS84 (lon, lat)
     const x = propertyData.geometry.x;
     const y = propertyData.geometry.y;
     const longitude = (x / 20037508.34) * 180;
     const latitude = (Math.atan(Math.exp((y / 20037508.34) * Math.PI)) * 360 / Math.PI) - 90;

     return { latitude, longitude };
   } catch (error) {
     console.error('getPropertyCoordinates error:', error);
     return null;
   }
 }

/**
 * Get comprehensive property compliance data
 */
 static async getPropertyComplianceData(address: string): Promise<{
 propertyData: NSWPropertyData;
 constraints: PlanningConstraints & { applicableSepps?: string[] };
 layers: PlanningLayer[];
 roadClassifications?: any[];
 anefData?: AnefInfo | null;
 strataInfo: StrataInfo;
 lotGeometry?: LotGeometryData | null;
 } | null> {
 try {
 const searchResult = await this.searchProperty(address);

 if (!searchResult) {
 throw new Error('Property not found');
 }

 // Stage 1: independent fetches in parallel (valuation called once only)
 const [layers, initialPropertyData, initialLotGeometry] = await Promise.all([
   this.getPlanningLayers(searchResult.propId),
   this.getPropertyValuation(searchResult.propId),
   this.getLotGeometry(searchResult.propId).catch(() => null)
 ]);

 // Fallback: when the top-scored propId has no valuation (strata unit propIds),
 // try other candidates from a broader search until one has valuation data.
 let propertyData = initialPropertyData;
 let lotGeometry = initialLotGeometry;
 if (!propertyData) {
   try {
     const fbRes = await fetch(
       `${this.BASE_URL}/address?a=${encodeURIComponent(address)}&noOfRecords=10`,
       { headers: { 'Accept': 'application/json', 'User-Agent': 'ComplianceEngine/1.0' } }
     );
     if (fbRes.ok) {
       const fbResults = await fbRes.json();
       for (const candidate of fbResults) {
         if (candidate.propId === searchResult.propId) continue;
         const candidateData = await this.getPropertyValuation(candidate.propId);
         if (candidateData) {
           propertyData = candidateData;
           lotGeometry = await this.getLotGeometry(candidate.propId).catch(() => null);
           break;
         }
       }
     }
   } catch {
     // fallback failed — propertyData stays null, will throw below
   }
 }

 // Detect strata: valuation-null fallback (strata unit propIds return no valuation) combined
 // with address heuristic ("5/12 Smith St", "Unit 3/12 Smith St").
 const valuationFallback = !initialPropertyData;
 const unitMatch = address.match(/^(\d+)\//i) ?? address.match(/^(?:unit|apt|apartment|flat)\s+(\d+)/i);
 const strataInfo: StrataInfo = {
   isStrata: valuationFallback || !!unitMatch,
   source: (valuationFallback && unitMatch) ? 'combined'
         : valuationFallback               ? 'valuation_fallback'
         : unitMatch                       ? 'address_heuristic'
         : null,
   strataUnit: unitMatch?.[1] ?? null,
 };

 // Stage 2: fan out from single valuation result (needs geometry for coordinate conversion)
 let todLayers: PlanningLayer[] = [];
 let roadClassifications: any[] = [];
 let anefData: AnefInfo | null = null;
 let bushfireData: any = null;
 let mineSubsidenceData: any = null;
 let contaminatedLandData: any = null;
 let drinkingWaterData: any = null;
 let coastalData: any = null;
 let seppExclusionData: { lowMidRise: boolean | null; complying: boolean | null; exempt: boolean | null } | null = null;
 let dualOccData: { prohibited: boolean; epiName?: string; lgaName?: string } | null = null;

 if (propertyData) {
   const lon = (propertyData.geometry.x / 20037508.34) * 180;
   const lat = (Math.atan(Math.exp((propertyData.geometry.y / 20037508.34) * Math.PI)) * 360 / Math.PI) - 90;

   [todLayers, roadClassifications, anefData, bushfireData, mineSubsidenceData, contaminatedLandData, drinkingWaterData, coastalData, seppExclusionData, dualOccData] = await Promise.all([
     this.getTODLayers(propertyData.geometry).catch(() => []),
     getRoadClassifications(lat, lon).catch(() => []),
     // ANEF (Aircraft Noise) - Using NSW Planning Portal Protection Layer 2
     fetch(`https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Protection/MapServer/2/query?geometry=${lon},${lat}&geometryType=esriGeometryPoint&spatialRel=esriSpatialRelIntersects&outFields=ANEF_CODE,EPI_NAME,LGA_NAME&returnGeometry=false&f=json&inSR=4283`)
       .then(res => res.json())
       .then(data => {
         if (!data.features || data.features.length === 0) return null;
         const attrs = data.features[0].attributes;
         // Parse ANEF level from ANEF_CODE (e.g., "20-25", "25-30", ">40")
         const anefCode = attrs.ANEF_CODE || '';
         let anefLevel = null;
         if (anefCode.includes('>')) {
           anefLevel = 40; // ">40" means 40+
         } else if (anefCode.includes('-')) {
           const parts = anefCode.split('-');
           anefLevel = parseInt(parts[0]); // Use lower bound of range
         } else {
           anefLevel = parseInt(anefCode) || null;
         }
         return {
           inAnefZone: true,
           anefLevel: anefLevel,
           anefCode: anefCode,
           epiName: attrs.EPI_NAME,
           lgaName: attrs.LGA_NAME,
           airport: null,
           buildingAcceptability: null,
           standardReference: ''
         } as any;
       })
       .catch(() => null),
     // Bushfire data
     fetch(`https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Fire/BFPL/MapServer/0/query?geometry=${lon},${lat}&geometryType=esriGeometryPoint&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json&inSR=4283`)
       .then(res => res.json())
       .then(data => data.features?.[0]?.attributes || null)
       .catch(() => null),
     // Mine subsidence data
     fetch(`https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme/FeatureServer/7/query?f=json&geometry=${JSON.stringify({x: lon, y: lat, spatialReference: {wkid: 4326}})}&geometryType=esriGeometryPoint&spatialRel=esriSpatialRelIntersects&outFields=districtname,lastupdate&returnGeometry=false`)
       .then(res => res.json())
       .then(data => data.features?.[0]?.attributes || null)
       .catch(() => null),
     // Contaminated land (within 500m)
     fetch(`https://mapprod2.environment.nsw.gov.au/arcgis/rest/services/EPA/Contaminated_land_notified_sites/MapServer/0/query?geometry=${lon},${lat}&geometryType=esriGeometryPoint&distance=500&units=esriSRUnit_Meter&spatialRel=esriSpatialRelIntersects&outFields=SiteName,SiteStreet,Suburb,ManagementClass,ContaminationActivityType&returnGeometry=true&f=json&inSR=4283&orderByFields=OBJECTID ASC`)
       .then(res => res.json())
       .then(data => {
         if (!data.features || data.features.length === 0) return null;
         const site = data.features[0].attributes;
         const geom = data.features[0].geometry;
         // Calculate approximate distance
         const dx = (geom.x - lon) * 111320 * Math.cos(lat * Math.PI / 180);
         const dy = (geom.y - lat) * 110540;
         const distance = Math.sqrt(dx * dx + dy * dy);
         return { ...site, distance };
       })
       .catch(() => null),
     // Drinking water catchment
     fetch(`https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/Protection/MapServer/3/query?geometry=${lon},${lat}&geometryType=esriGeometryPoint&spatialRel=esriSpatialRelIntersects&outFields=EPI_NAME,LGA_NAME&returnGeometry=false&f=json&inSR=4283`)
       .then(res => res.json())
       .then(data => data.features?.[0]?.attributes || null)
       .catch(() => null),
     // Coastal environment (check multiple coastal layers)
     Promise.all([
       fetch(`https://mapprod1.environment.nsw.gov.au/arcgis/rest/services/CoastalManagementSEPP/CoastalManagementSEPP/MapServer/1/query?geometry=${lon},${lat}&geometryType=esriGeometryPoint&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json&inSR=4283`).then(r => r.json()).then(d => d.features?.[0] ? 'Coastal Wetlands' : null).catch(() => null),
       fetch(`https://mapprod1.environment.nsw.gov.au/arcgis/rest/services/CoastalManagementSEPP/CoastalManagementSEPP/MapServer/6/query?geometry=${lon},${lat}&geometryType=esriGeometryPoint&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json&inSR=4283`).then(r => r.json()).then(d => d.features?.[0] ? 'Coastal Environment Area' : null).catch(() => null),
       fetch(`https://mapprod1.environment.nsw.gov.au/arcgis/rest/services/CoastalManagementSEPP/CoastalManagementSEPP/MapServer/3/query?geometry=${lon},${lat}&geometryType=esriGeometryPoint&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json&inSR=4283`).then(r => r.json()).then(d => d.features?.[0] ? 'Littoral Rainforests' : null).catch(() => null),
     ]).then(results => results.filter(Boolean))
       .catch(() => []),
     // ePlanning Phase 1: SEPP exclusion layers (776, 92, 93) — batch as 3 parallel fetches to same service
     Promise.all([
       fetch(ePlanningPointQuery('lowMidRiseExclusion', lon, lat, 'LAY_CLASS')).then(r => r.json()).then(d => (!d.error && Array.isArray(d.features)) ? d.features.length > 0 : null).catch(() => null),
       fetch(ePlanningPointQuery('complyingExclusion', lon, lat, 'LAY_CLASS')).then(r => r.json()).then(d => (!d.error && Array.isArray(d.features)) ? d.features.length > 0 : null).catch(() => null),
       fetch(ePlanningPointQuery('exemptExclusion', lon, lat, 'LAY_CLASS')).then(r => r.json()).then(d => (!d.error && Array.isArray(d.features)) ? d.features.length > 0 : null).catch(() => null),
     ]).then(([lowMidRise, complying, exempt]) => ({
       lowMidRise,
       complying,
       exempt,
     })).catch(() => null),
     // ePlanning Phase 1: Dual occupancy prohibition (layer 452)
     fetch(ePlanningPointQuery('dualOccProhibition', lon, lat, 'LAY_CLASS,EPI_NAME,LGA_NAME'))
       .then(r => r.json())
       .then(d => {
         if (d.error || !Array.isArray(d.features)) return null;
         if (d.features.length === 0) return { prohibited: false };
         const attrs = d.features[0].attributes;
         return { prohibited: true, epiName: attrs.EPI_NAME, lgaName: attrs.LGA_NAME };
       })
       .catch(() => null),
   ]);
 }

 if (!propertyData) {
 throw new Error('Property valuation data not found');
 }

 const allLayers = [...layers, ...todLayers];
 const constraints = this.extractPlanningConstraints(allLayers, address);

 // Add environmental constraint data
 if (bushfireData) {
   constraints.bushfireProne = true;
   constraints.bushfireCategory = bushfireData.Category || bushfireData.TYPE || null;
 }
 if (mineSubsidenceData) {
   constraints.mineSubsidence = {
     inDistrict: true,
     districtName: mineSubsidenceData.districtname,
     lastUpdate: mineSubsidenceData.lastupdate
   };
 }
 if (contaminatedLandData) {
   constraints.contaminatedLand = {
     hasNotifiedSites: true,
     nearestSite: {
       name: contaminatedLandData.SiteName,
       address: contaminatedLandData.SiteStreet + (contaminatedLandData.Suburb ? ', ' + contaminatedLandData.Suburb : ''),
       managementClass: contaminatedLandData.ManagementClass,
       contaminationType: contaminatedLandData.ContaminationActivityType,
       distance: Math.round(contaminatedLandData.distance)
     }
   };
 }
 if (drinkingWaterData) {
   constraints.drinkingWaterCatchment = {
     inCatchment: true,
     epiName: drinkingWaterData.EPI_NAME,
     lgaName: drinkingWaterData.LGA_NAME
   };
 }
 if (coastalData && coastalData.length > 0) {
   constraints.coastalEnvironment = {
     inCoastalArea: true,
     zones: coastalData
   };
 }

 // ePlanning Phase 1: exclusion gates
 if (seppExclusionData) {
   constraints.lowMidRiseExcluded = seppExclusionData.lowMidRise;
   constraints.complyingExcluded = seppExclusionData.complying;
   constraints.exemptExcluded = seppExclusionData.exempt;
 }
 if (dualOccData) {
   constraints.dualOccProhibited = dualOccData;
 }

 // Step 4: Clean up the address from search result
 // Hunter Street Lewisham has incorrect "8-12" in addresses - remove it
 let cleanAddress = searchResult.address;
 if (cleanAddress.includes('HUNTER STREET LEWISHAM') && cleanAddress.includes('8-12')) {
 // Convert "14 8-12 HUNTER STREET LEWISHAM 2049" to "14 HUNTER ST, LEWISHAM NSW 2049"
 const streetNumber = cleanAddress.match(/^(\d+)/)?.[1];
 if (streetNumber) {
 cleanAddress = `${streetNumber} HUNTER ST, LEWISHAM NSW 2049`;
 }
 }
 propertyData.address = cleanAddress;

 // searchResult.address includes the street number; propertyData.address (from valuation API) omits it
 const mergedPropertyData = searchResult.address
   ? { ...propertyData, address: searchResult.address }
   : propertyData;

 return {
 propertyData: mergedPropertyData,
 constraints,
 layers: allLayers, // Return merged layers including TOD/HIA
 roadClassifications, // Return road classification data for setback calculations
 anefData, // Return ANEF zone data for aircraft noise assessment
 lotGeometry, // Return lot polygon geometry for dimension calculations
 strataInfo,
 };

 } catch (error) {
 console.error('Property compliance data error:', error);
 return null;
 }
 }
}

/**
 * Standalone export for getPropertyCoordinates
 * Wraps the static class method for easier imports
 */
export async function getPropertyCoordinates(address: string): Promise<{ latitude: number; longitude: number } | null> {
  return NSWPlanningPortalService.getPropertyCoordinates(address);
}