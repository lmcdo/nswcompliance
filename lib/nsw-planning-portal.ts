/**
 * NSW Planning Portal API Integration
 * Real-time property data, zoning, and environmental overlays
 */

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

export interface PlanningConstraints {
 maxFsr: number | null;
 maxHeight: number | null;
 minLotSize: number | null;
 zone: string | null;
 lga: string | null;
 heritage: boolean;
 heritageType?: string;
 floodProne: boolean;
 bushfireProne: boolean;
 acidSulfateSoils?: string;
 basixClimate: string | null;
 basixWater: string | null;
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
 const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
 
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
 */
 static async getPlanningLayers(propId: number, retryCount: number = 0): Promise<PlanningLayer[]> {
 console.log('=== DEBUG: getPlanningLayers ===');
 console.log('PropId:', propId, 'Retry:', retryCount);
 
 try {
 const response = await fetch(
 `${this.BASE_URL}/layerintersect?type=property&id=${propId}&layers=epi`
 );
 
 console.log('Response status:', response.status);
 console.log('Response ok:', response.ok);
 
 if (response.status === 429) {
 if (retryCount < 2) {
 console.log('Rate limited! Waiting 10 seconds before retry...');
 await new Promise(resolve => setTimeout(resolve, 10000));
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
 const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
 
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
 * Extract planning constraints from layers
 */
 static extractPlanningConstraints(layers: PlanningLayer[]): PlanningConstraints & { applicableSepps?: string[] } {
 const constraints: PlanningConstraints & { applicableSepps?: string[] } = {
 maxFsr: null,
 maxHeight: null,
 minLotSize: null,
 zone: null,
 lga: null,
 heritage: false,
 floodProne: false,
 bushfireProne: false,
 basixClimate: null,
 basixWater: null,
 applicableSepps: []
 };

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
 // From API: "Zone": "R4"
 if (result['Zone']) {
 constraints.zone = result['Zone'];
 }
 break;
 
 case 'Lot Size Map':
 constraints.minLotSize = parseFloat(result['Lot Size'] || '0') || null;
 break;
 
 case 'Heritage Map':
 constraints.heritage = true;
 constraints.heritageType = result['Heritage Type'];
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
 break;
 
 case 'Greater Sydney Tree Canopy Cover 2019':
 // Add tree canopy data extraction
 break;
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
 
 if (!constraints.applicableSepps.includes(seppIdentifier)) {
 constraints.applicableSepps.push(seppIdentifier);
 console.log(`Added SEPP identifier: ${seppIdentifier}`);
 }
 }
 
 // Also check for specific known SEPPs
 if (lowerValue.includes('housing')) {
 if (!constraints.applicableSepps.includes('SEPP_HOUSING_2021')) {
 constraints.applicableSepps.push('SEPP_HOUSING_2021');
 }
 }
 
 if (lowerValue.includes('planning') && lowerValue.includes('systems')) {
 if (!constraints.applicableSepps.includes('SEPP_PLANNING_SYSTEMS_2021')) {
 constraints.applicableSepps.push('SEPP_PLANNING_SYSTEMS_2021');
 }
 }
 
 if (lowerValue.includes('resilience') || lowerValue.includes('hazards')) {
 if (!constraints.applicableSepps.includes('SEPP_RESILIENCE_HAZARDS_2021')) {
 constraints.applicableSepps.push('SEPP_RESILIENCE_HAZARDS_2021');
 }
 }
 }
 }
 }
 }

 /**
 * Get comprehensive property compliance data
 */
 static async getPropertyComplianceData(address: string): Promise<{
 propertyData: NSWPropertyData;
 constraints: PlanningConstraints & { applicableSepps?: string[] };
 layers: PlanningLayer[];
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

 // Step 2: Get planning layers and valuation data in parallel
 console.log('Step 2: Getting planning layers and valuation data...');
 const [layers, propertyData] = await Promise.all([
 this.getPlanningLayers(searchResult.propId),
 this.getPropertyValuation(searchResult.propId)
 ]);

 console.log('Layers received:', layers);
 console.log('Property data received:', propertyData);

 if (!propertyData) {
 throw new Error('Property valuation data not found');
 }

 // Step 3: Extract constraints from layers
 console.log('Step 3: Extracting constraints from layers...');
 const constraints = this.extractPlanningConstraints(layers);

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
 layers
 };
 
 } catch (error) {
 console.error('Property compliance data error:', error);
 return null;
 }
 }
}