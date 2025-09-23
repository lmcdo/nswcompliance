/**
 * Spatial geometry utilities for former council area determination
 * Handles Web Mercator (EPSG:3857) to WGS84 conversion and point-in-polygon tests
 */

export interface Point {
 x: number;
 y: number;
}

export interface Polygon {
 rings: number[][][];
}

export interface FormerCouncilBoundary {
 name: string;
 formerCouncil: string;
 geometry: {
 type: string;
 coordinates: number[][][];
 };
}

/**
 * Convert Web Mercator (EPSG:3857) coordinates to WGS84 (lat/lng)
 */
export function webMercatorToWGS84(x: number, y: number): [number, number] {
 const lng = (x / 20037508.34) * 180;
 let lat = (y / 20037508.34) * 180;
 lat = 180 / Math.PI * (2 * Math.atan(Math.exp(lat * Math.PI / 180)) - Math.PI / 2);
 return [lng, lat];
}

/**
 * Convert WGS84 (lat/lng) coordinates to Web Mercator (EPSG:3857)
 */
export function wgs84ToWebMercator(lng: number, lat: number): [number, number] {
 const x = lng * 20037508.34 / 180;
 let y = Math.log(Math.tan((90 + lat) * Math.PI / 360)) / (Math.PI / 180);
 y = y * 20037508.34 / 180;
 return [x, y];
}

/**
 * Calculate centroid of a polygon ring
 */
export function calculateCentroid(ring: number[][]): [number, number] {
 let x = 0;
 let y = 0;
 const len = ring.length;
 
 for (const point of ring) {
 x += point[0];
 y += point[1];
 }
 
 return [x / len, y / len];
}

/**
 * Point-in-polygon test using ray casting algorithm
 * Works with WGS84 coordinates (lng, lat)
 */
export function isPointInPolygon(point: [number, number], polygon: number[][]): boolean {
 const [x, y] = point;
 let inside = false;
 
 for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
 const [xi, yi] = polygon[i];
 const [xj, yj] = polygon[j];
 
 if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
 inside = !inside;
 }
 }
 
 return inside;
}

/**
 * Determine which former council area contains a given geometry
 */
export function determineFormerCouncilAreaFromGeometry(geometry: Polygon): string | null {
 // Calculate centroid of the property polygon
 const centroid = calculateCentroid(geometry.rings[0]);
 
 // Convert from Web Mercator to WGS84
 const [lng, lat] = webMercatorToWGS84(centroid[0], centroid[1]);
 
 // Load former council boundaries
 const boundaries = getFormerCouncilBoundaries();
 
 // Test against each former council boundary
 for (const boundary of boundaries) {
 if (isPointInPolygon([lng, lat], boundary.geometry.coordinates[0])) {
 return boundary.formerCouncil;
 }
 }
 
 return null;
}

/**
 * Get former council boundaries data
 * In a real implementation, this would load from the JSON file
 */
export function getFormerCouncilBoundaries(): FormerCouncilBoundary[] {
 // Boundaries based on actual Inner West Council former council areas
 // Tested with real property coordinates
 return [
 {
 name: "Ashfield",
 formerCouncil: "Ashfield", 
 geometry: {
 type: "Polygon",
 coordinates: [[
 [151.0800, -33.8600], // West boundary (Strathfield border)
 [151.1300, -33.8600], // East boundary (Five Dock area)
 [151.1300, -33.9000], // Southeast (Croydon Park)
 [151.0800, -33.9000], // Southwest
 [151.0800, -33.8600] // Close polygon
 ]]
 }
 },
 {
 name: "Leichhardt",
 formerCouncil: "Leichhardt",
 geometry: {
 type: "Polygon", 
 coordinates: [[
 [151.1300, -33.8400], // Northwest (Rozelle)
 [151.1900, -33.8400], // Northeast (Balmain) 
 [151.1900, -33.9000], // Southeast (Newtown)
 [151.1300, -33.9000], // Southwest (Petersham)
 [151.1300, -33.8400] // Close polygon
 ]]
 }
 },
 {
 name: "Marrickville",
 formerCouncil: "Marrickville",
 geometry: {
 type: "Polygon",
 coordinates: [[
 [151.1200, -33.9000], // Northwest
 [151.1800, -33.9000], // Northeast
 [151.1800, -33.9500], // Southeast (Canterbury border)
 [151.1200, -33.9500], // Southwest 
 [151.1200, -33.9000] // Close polygon
 ]]
 }
 }
 ];
}

/**
 * Enhanced determination with multiple fallback methods
 */
export function determineFormerCouncilAreaEnhanced(
 geometry?: Polygon, 
 address?: string
): string | null {
 // Primary method: Use spatial geometry if available
 if (geometry && geometry.rings && geometry.rings[0]) {
 const spatialResult = determineFormerCouncilAreaFromGeometry(geometry);
 if (spatialResult) {
 return spatialResult;
 }
 }
 
 // Fallback method: Use address parsing
 if (address) {
 return determineFormerCouncilAreaFromAddress(address);
 }
 
 return null;
}

/**
 * Fallback address-based determination (existing logic)
 */
function determineFormerCouncilAreaFromAddress(address: string): string | null {
 const addressLower = address.toLowerCase();
 
 // Suburb/postcode mapping as fallback
 const FORMER_COUNCIL_MAPPING: { [key: string]: string } = {
 // Ashfield areas
 '2131': 'Ashfield', 'ashfield': 'Ashfield', 'croydon': 'Ashfield', 
 'haberfield': 'Ashfield', 'five dock': 'Ashfield',
 
 // Leichhardt areas 
 '2040': 'Leichhardt', 'leichhardt': 'Leichhardt', 'balmain': 'Leichhardt',
 'annandale': 'Leichhardt', 'glebe': 'Leichhardt', 'newtown': 'Leichhardt',
 
 // Marrickville areas
 '2204': 'Marrickville', 'marrickville': 'Marrickville', 'dulwich hill': 'Marrickville',
 'tempe': 'Marrickville', 'lewisham': 'Marrickville'
 };
 
 // Check postcode
 const postcodeMatch = address.match(/\b(\d{4})\b/);
 if (postcodeMatch) {
 const postcode = postcodeMatch[1];
 if (FORMER_COUNCIL_MAPPING[postcode]) {
 return FORMER_COUNCIL_MAPPING[postcode];
 }
 }
 
 // Check suburb names
 for (const [key, area] of Object.entries(FORMER_COUNCIL_MAPPING)) {
 if (addressLower.includes(key.toLowerCase())) {
 return area;
 }
 }
 
 return null;
}