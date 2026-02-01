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
 formerCouncil?: string | null;
 heritage: boolean;
 heritageType?: string;
 heritageItemName?: string;
 heritageItemNumber?: string;
 heritageLegislativeClause?: string;
 heritageSignificance?: string;
 heritageLegislationUrl?: string;
 floodProne: boolean;
 bushfireProne: boolean;
 acidSulfateSoils?: string;
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

export class NSWPlanningPortalService {
 private static BASE_URL = 'https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi';
 private static VALUATION_URL = 'https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/5/query';

 /**
 * Search for property by address using NSW Planning Portal
 * Returns the first matching result (follows same pattern as map-viewer project)
 */
 static async searchProperty(address: string): Promise<{ propId: number; address: string; GURASID: number } | null> {
 console.log('=== DEBUG: searchProperty ===');
 console.log('Address:', address);
 console.log('Encoded:', encodeURIComponent(address));
 console.log('URL:', `${this.BASE_URL}/address?a=${encodeURIComponent(address)}&noOfRecords=1`);
 
 try {
 const encodedAddress = encodeURIComponent(address);
 
 const controller = new AbortController();
 const timeoutId = setTimeout(() => controller.abort(), 5000); // 30 second timeout
 
 const response = await fetch(
 `${this.BASE_URL}/address?a=${encodedAddress}&noOfRecords=1`,
 {
 signal: controller.signal,
 headers: {
 'Accept': 'application/json',
 'User-Agent': 'ComplianceEngine/1.0'
 }
 }
 );
 
 clearTimeout(timeoutId);
 
 console.log('Search response status:', response.status);
 console.log('Search response ok:', response.ok);
 
 if (!response.ok) {
 const errorText = await response.text();
 console.log('Search error response:', errorText);
 throw new Error(`Address search failed: ${response.status}`);
 }
 
 const results = await response.json() as any[];
 console.log('Search results:', results);
 console.log('Results length:', results?.length);
 
 if (!results || results.length === 0) {
 console.log('No results found');
 return null;
 }
 
 console.log('Returning result:', results[0]);
 // Return the first result - NSW Planning Portal API handles the matching
 return results[0];
 
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
 console.log('=== DEBUG: getPlanningLayers ===');
 console.log('PropId:', propId, 'Retry:', retryCount);

 // Add timeout protection to prevent indefinite hangs
 const controller = new AbortController();
 const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

 try {
 const response = await fetch(
 `${this.BASE_URL}/layerintersect?type=property&id=${propId}&layers=epi`,
 { signal: controller.signal }
 );

 // Clear timeout on successful response
 clearTimeout(timeoutId);

 console.log('Response status:', response.status);
 console.log('Response ok:', response.ok);

 if (response.status === 429) {
 if (retryCount < 2) {
 console.log('Rate limited! Waiting 2 seconds before retry...');
 await new Promise(resolve => setTimeout(resolve, 2000)); // Reduced from 10s to 2s
 return this.getPlanningLayers(propId, retryCount + 1);
 } else {
 console.log('Rate limited after 2 retries, giving up');
 return [];
 }
 }

 if (!response.ok) {
 const errorText = await response.text();
 console.log('Response error text:', errorText);
 throw new Error(`Planning layers failed: ${response.status}`);
 }

 const data = await response.json();
 console.log('Planning layers data received:', data?.length || 0, 'layers');

 return data || [];

 } catch (error) {
 // Clear timeout in case of error
 clearTimeout(timeoutId);

 // Handle timeout specifically
 if (error instanceof Error && error.name === 'AbortError') {
 console.error('Planning layers request timed out after 10 seconds');
 if (retryCount < 1) {
 console.log('Retrying after timeout...');
 await new Promise(resolve => setTimeout(resolve, 2000));
 return this.getPlanningLayers(propId, retryCount + 1);
 } else {
 console.error('Planning layers timeout after retry, giving up');
 return [];
 }
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
 const timeoutId = setTimeout(() => controller.abort(), 5000); // 30 second timeout
 
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
 const timeoutId = setTimeout(() => controller.abort(), 5000);

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
 const todLayers: PlanningLayer[] = [];

 const controller = new AbortController();
 const timeoutId = setTimeout(() => controller.abort(), 8000); // 8s timeout

 try {
 console.log('=== Fetching TOD/HIA Layers (Phase 3) ===');
 console.log('Geometry:', geometry);

 // Query 1: TOD Sites Map (SEPP Housing 2021)
 const todUrl = `https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/SEPP_Housing_2021/MapServer/3/query?` +
 `geometry=${geometry.x},${geometry.y}&geometryType=esriGeometryPoint&` +
 `spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json`;

 console.log('Querying TOD Sites Map...');
 const todResponse = await fetch(todUrl, { signal: controller.signal });

 if (todResponse.ok) {
 const todData = await todResponse.json();
 if (todData.features && todData.features.length > 0) {
 console.log('✅ TOD layer found:', todData.features.length, 'features');
 todLayers.push({
 layerName: 'Transport Oriented Development Sites Map',
 results: todData.features.map((f: any) => f.attributes)
 });
 } else {
 console.log('❌ No TOD features at this location');
 }
 }

 // Query 2: Accelerated TOD Precincts
 const acceleratedUrl = `https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning/Planning_Portal_SEPP/MapServer/759/query?` +
 `geometry=${geometry.x},${geometry.y}&geometryType=esriGeometryPoint&` +
 `spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json`;

 console.log('Querying Accelerated TOD Precincts...');
 const acceleratedResponse = await fetch(acceleratedUrl, { signal: controller.signal });

 if (acceleratedResponse.ok) {
 const acceleratedData = await acceleratedResponse.json();
 if (acceleratedData.features && acceleratedData.features.length > 0) {
 console.log('✅ Accelerated TOD found:', acceleratedData.features.length, 'features');
 todLayers.push({
 layerName: 'Accelerated TOD Precincts Rezoning Areas Map',
 results: acceleratedData.features.map((f: any) => f.attributes)
 });
 } else {
 console.log('❌ No Accelerated TOD features at this location');
 }
 }

 clearTimeout(timeoutId);
 console.log('TOD/HIA query complete. Found', todLayers.length, 'layer(s)');
 return todLayers;

 } catch (error) {
 clearTimeout(timeoutId);

 if (error instanceof Error && error.name === 'AbortError') {
 console.error('TOD layers request timed out after 8 seconds (non-critical)');
 } else {
 console.error('TOD layers fetch failed (non-critical):', error);
 }

 // Graceful degradation - return empty array, don't break property lookup
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

 // ===== PHASE 2 TOD/HIA LAYER AUDIT =====
 console.log('\n=== LAYER COVERAGE AUDIT (Phase 2) ===');
 console.log('Total layers received:', layers.length);
 console.log('\nAll layer names:');
 layers.forEach((layer, index) => {
 console.log(`  ${index + 1}. ${layer.layerName} (${layer.results?.length || 0} results)`);
 });

 // Check for TOD/HIA-related keywords
 const todKeywords = ['transport', 'tod', 'housing', 'accelerated', 'hia', 'infrastructure', 'station', 'precinct'];
 const todRelatedLayers = layers.filter(l =>
 todKeywords.some(keyword => l.layerName.toLowerCase().includes(keyword))
 );

 if (todRelatedLayers.length > 0) {
 console.log('\n✅ TOD/HIA-related layers FOUND:');
 todRelatedLayers.forEach(l => console.log(`  - ${l.layerName}`));
 } else {
 console.log('\n❌ NO TOD/HIA-related layers found in EPI response');
 console.log('  Will need separate API call (Phase 3)');
 }
 console.log('=== END LAYER AUDIT ===\n');
 // ===== END PHASE 2 AUDIT =====

 console.log('Extracting from', layers.length, 'layers');
 layers.forEach(layer => {
 console.log('Layer:', layer.layerName, 'Results:', layer.results?.length || 0);
 if (layer.results?.length > 0) {
 console.log('First result keys:', Object.keys(layer.results[0]));
 console.log('First result:', JSON.stringify(layer.results[0], null, 2));
 }
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
 // Extract LGA from Land Application Map
 if (result['LGA Name']) {
 constraints.lga = result['LGA Name'];
 }
 break;
 
 case 'Greater Sydney Tree Canopy Cover 2019':
 console.log('✅ Extracting Tree Canopy data:', result);
 // Field name in actual API response is "Canopy %" not "Tree Canopy Cover %"
 constraints.treeCanopy = {
 coverage: result['Canopy %'] || result['Tree Canopy Cover %'] || result['Canopy_Cover'],
 coverageClass: result['Cover Class'] || result['Canopy_Class'] || result['Canopy Class'],
 year: '2019',
 source: 'Greater Sydney Tree Canopy Cover 2019'
 };
 console.log('Tree canopy extracted:', constraints.treeCanopy);
 break;

 // ===== PHASE 5: TOD/HIA EXTRACTION =====
 case 'Transport Oriented Development Sites Map':
 case 'TOD Precinct':
 case 'SEPP Housing 2021 - TOD':
 case 'SEPP (Housing) 2021':
 console.log('✅ Extracting TOD precinct data:', result);
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
 console.log('TOD precinct extracted:', constraints.todPrecinct);
 break;

 case 'Accelerated TOD Precincts Rezoning Areas Map':
 case 'Accelerated Transport Oriented Development':
 case 'Priority Precincts':
 console.log('✅ Extracting Accelerated TOD data:', result);
 constraints.acceleratedTOD = {
 inAcceleratedPrecinct: true,
 precinctName: result['Precinct Name'] || result['PrecinctName'] ||
 result['Name'] || 'Accelerated TOD Precinct',
 expectedRezoning: result['Rezoning Date'] || result['ExpectedDate'] ||
 result['Expected_Rezoning'] || result['REZONING_DATE'],
 priorityArea: true
 };
 console.log('Accelerated TOD extracted:', constraints.acceleratedTOD);
 break;

 case 'Housing Infrastructure Areas':
 case 'HIA Map':
 case 'State Significant Development':
 console.log('✅ Extracting HIA data:', result);
 constraints.hiaArea = {
 inHIA: true,
 hiaName: result['HIA Name'] || result['Name'] || result['Area Name'] || 'HIA Area',
 specialControls: result['Special Controls'] || result['Controls'] || result['CONTROLS'],
 legislativeClause: result['Legislative Clause'] || result['Clause']
 };
 console.log('HIA area extracted:', constraints.hiaArea);
 break;

			case 'Local Provisions':
				if (process.env.NODE_ENV === 'development') {
					console.log('Extracting Local Provisions:', result);
				}
				if (!constraints.localProvisions) {
					constraints.localProvisions = [];
				}

				// Extract Map Type and get clause numbers
				const mapType = result['Map Type'];
				const clauseNumbers = mapType ? getClauseNumbersForMapType(mapType) : [];

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

 console.log('Final constraints:', constraints);
 return constraints;
 }

 /**
 * Extract applicable SEPPs from special provisions data
 */
 static extractApplicableSepps(result: any, constraints: PlanningConstraints & { applicableSepps?: string[] }): void {
 console.log('Processing special provisions result:', JSON.stringify(result, null, 2));
 
 // Look for SEPP identifiers in various fields
 const searchFields = ['Type', 'Category', 'EPI Name', 'Legislative Clause', 'Description', 'Map Type'];
 const seppKeywords = ['sepp', 'state environmental planning policy'];
 
 for (const field of searchFields) {
 const value = result[field];
 if (typeof value === 'string') {
 const lowerValue = value.toLowerCase();
 
 // Check if this field mentions any SEPP
 if (seppKeywords.some(keyword => lowerValue.includes(keyword))) {
 console.log(`Found SEPP reference in ${field}: ${value}`);
 
 // Extract SEPP number/identifier
 const seppMatch = value.match(/sepp[^\d]*(\d+)/i) || value.match(/state environmental planning policy[^\d]*(\d+)/i);
 if (seppMatch) {
 const seppNumber = seppMatch[1];
 const seppIdentifier = `SEPP_${seppNumber}`;
 
 if (!constraints.applicableSepps?.includes(seppIdentifier)) {
 constraints.applicableSepps?.push(seppIdentifier);
 console.log(`Added SEPP identifier: ${seppIdentifier}`);
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
 lotGeometry?: LotGeometryData | null;
 } | null> {
 console.log('=== DEBUG: getPropertyComplianceData ===');
 console.log('Address:', address);
 
 try {
 // Step 1: Search for property
 console.log('Step 1: Searching for property...');
 const searchResult = await this.searchProperty(address);
 console.log('Search result:', searchResult);
 
 if (!searchResult) {
 throw new Error('Property not found');
 }

 // Step 2: Get planning layers, valuation data, and TOD layers in parallel
 console.log('Step 2: Getting planning layers, valuation data, TOD/HIA, ANEF, and lot geometry...');
 const [layers, propertyData, todLayers, roadClassifications, anefData, lotGeometry] = await Promise.all([
 this.getPlanningLayers(searchResult.propId),
 this.getPropertyValuation(searchResult.propId),
 // Fetch TOD layers after we get property data (need geometry)
 this.getPropertyValuation(searchResult.propId)
 .then(pd => pd ? this.getTODLayers(pd.geometry) : [])
 .catch(() => {
 console.log('TOD layers fetch failed, continuing without TOD data');
 return [];
 }),
 // Fetch road classifications for setback calculations (need WGS84 coordinates)
 this.getPropertyValuation(searchResult.propId)
 .then(pd => {
 if (!pd) return [];
 // Convert Web Mercator (x, y) to WGS84 (lon, lat)
 const lon = (pd.geometry.x / 20037508.34) * 180;
 const lat = (Math.atan(Math.exp((pd.geometry.y / 20037508.34) * Math.PI)) * 360 / Math.PI) - 90;
 console.log(`[Road Classification] Converted coordinates: Web Mercator (${pd.geometry.x}, ${pd.geometry.y}) → WGS84 (${lat.toFixed(6)}, ${lon.toFixed(6)})`);
 return getRoadClassifications(lat, lon);
 })
 .catch(() => {
 console.log('Road classification fetch failed, continuing without road data');
 return [];
 }),
 // Fetch ANEF (Aircraft Noise Exposure Forecast) zone data
 this.getPropertyValuation(searchResult.propId)
 .then(async (pd) => {
 if (!pd) return null;
 // Convert Web Mercator (x, y) to WGS84 (lon, lat)
 const lon = (pd.geometry.x / 20037508.34) * 180;
 const lat = (Math.atan(Math.exp((pd.geometry.y / 20037508.34) * Math.PI)) * 360 / Math.PI) - 90;
 console.log(`[ANEF] Checking coordinates: (${lat.toFixed(6)}, ${lon.toFixed(6)})`);
 const response = await fetch(`/api/environmental/anef?lat=${lat}&lon=${lon}`);
 if (!response.ok) return null;
 const result = await response.json();
 return result.success ? result.data : null;
 })
 .catch((err) => {
 console.log('ANEF check failed, continuing without ANEF data:', err);
 return null;
 }),
 // Fetch lot geometry for dimension calculations
 this.getLotGeometry(searchResult.propId)
 .catch((err) => {
 console.log('Lot geometry fetch failed, continuing without lot data:', err);
 return null;
 })
 ]);

 console.log('Layers received:', layers);
 console.log('Property data received:', propertyData);
 console.log('TOD layers received:', todLayers);
 console.log('Road classifications received:', roadClassifications);
 console.log('ANEF data received:', anefData);
 console.log('Lot geometry received:', lotGeometry ? `${lotGeometry.geometry?.rings?.[0]?.length || 0} vertices` : 'none');

 if (!propertyData) {
 throw new Error('Property valuation data not found');
 }

 // Step 3: Merge all layers and extract constraints
 console.log('Step 3: Merging layers and extracting constraints...');
 const allLayers = [...layers, ...todLayers];
 console.log('Total layers (including TOD):', allLayers.length);
 const constraints = this.extractPlanningConstraints(allLayers, address);

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

 return {
 propertyData,
 constraints,
 layers: allLayers, // Return merged layers including TOD/HIA
 roadClassifications, // Return road classification data for setback calculations
 anefData, // Return ANEF zone data for aircraft noise assessment
 lotGeometry // Return lot polygon geometry for dimension calculations
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