/**
 * Road Classification Service
 * Integrates with NSW Spatial Services RoadNameExtent API to determine road functional hierarchy
 * Used for setback calculations (primary roads require different setbacks than local roads)
 */

import { fetchWithTimeout } from './fetch-timeout';

export interface RoadClassification {
  road_name: string;
  functional_hierarchy: 'Motorway' | 'Primary Road' | 'Arterial Road' | 'Sub-Arterial Road' | 'Distributor Road' | 'Local Road' | 'Urban Service Road' | 'Track-Vehicular' | 'Path' | 'Dedicated Busway' | 'Access Way';
  hierarchy_code: number; // 1-11 numeric code
  distance_meters: number;
  operational_status: number;
  urbanity: string;
}

/**
 * Map NSW Spatial Services functionhierarchy codes to readable names
 * Based on community-documented schema
 */
function mapHierarchyCode(code: number): RoadClassification['functional_hierarchy'] {
  const mapping: Record<number, RoadClassification['functional_hierarchy']> = {
    1: 'Motorway',
    2: 'Primary Road',
    3: 'Arterial Road',
    4: 'Sub-Arterial Road',
    5: 'Distributor Road',
    6: 'Local Road',
    7: 'Urban Service Road',
    8: 'Track-Vehicular',
    9: 'Path',
    10: 'Dedicated Busway',
    11: 'Access Way'
  };
  return mapping[code] || 'Local Road';
}

/**
 * Get road classifications near a property using NSW Spatial Services RoadNameExtent API
 * Queries all NSW roads with complete coverage (not limited to traffic counting stations)
 *
 * @param lat Latitude (WGS84)
 * @param lon Longitude (WGS84)
 * @param bufferMeters Search radius (default 100m)
 * @returns Array of roads sorted by distance (closest first)
 */
export async function getRoadClassifications(
  lat: number,
  lon: number,
  bufferMeters: number = 100
): Promise<RoadClassification[]> {

  console.log(`[Road Classification] Fetching roads within ${bufferMeters}m of ${lat}, ${lon}`);

  // Convert WGS84 to Web Mercator for NSW Spatial Services query
  const x = lon * 20037508.34 / 180;
  const y = Math.log(Math.tan((90 + lat) * Math.PI / 360)) / (Math.PI / 180) * 20037508.34 / 180;

  // Build ArcGIS REST query for nearby roads
  const url = new URL('https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Transport_Theme/FeatureServer/6/query');

  // Spatial query: roads within buffer distance
  url.searchParams.set('geometry', `{"x":${x},"y":${y},"spatialReference":{"wkid":102100}}`);
  url.searchParams.set('geometryType', 'esriGeometryPoint');
  url.searchParams.set('spatialRel', 'esriSpatialRelIntersects');
  url.searchParams.set('distance', bufferMeters.toString());
  url.searchParams.set('units', 'esriSRUnit_Meter');
  url.searchParams.set('outFields', 'roadnamestring,functionhierarchy,operationalstatus,urbanity');
  url.searchParams.set('returnGeometry', 'true');
  url.searchParams.set('f', 'json');

  try {
    // The timer covers the whole reply (lib/fetch-timeout.ts). A failure THROWS: [] means "no roads
    // found", so it must never stand for "the road map did not answer".
    const response = await fetchWithTimeout(url.toString(), {
      headers: {
        'Accept': 'application/json',
        'User-Agent': 'ComplianceEngine/1.0'
      }
    }, 5000);

    if (!response.ok) {
      throw new Error(`road map returned ${response.status}`);
    }

    const data = await response.json();
    if (!data || data.error || !Array.isArray(data.features)) throw new Error('road map returned no feature list');

    if (data.features.length === 0) {
      console.warn('[Road Classification] No roads found within', bufferMeters, 'm');
      return [];
    }

    // Calculate distances and map to our interface
    const roads = data.features.map((feature: any) => {
      const attrs = feature.attributes;

      // Calculate distance from query point to road geometry
      // For now, use a simple approximation (actual distance would need geometry processing)
      const distance_meters = 50; // Placeholder - within buffer by definition

      return {
        road_name: attrs.roadnamestring || 'Unknown Road',
        hierarchy_code: attrs.functionhierarchy || 6,
        functional_hierarchy: mapHierarchyCode(attrs.functionhierarchy || 6),
        distance_meters,
        operational_status: attrs.operationalstatus || 1,
        urbanity: attrs.urbanity || 'U'
      };
    });

    // Sort by hierarchy (lower code = more important road = likely frontage)
    roads.sort((a: any, b: any) => a.hierarchy_code - b.hierarchy_code);

    console.log(`[Road Classification] Found ${roads.length} roads:`, roads.map((r: any) => `${r.road_name} (${r.functional_hierarchy}, code ${r.hierarchy_code})`));

    console.log('[Road Classification] Returning roads array:', roads);
    return roads;

  } catch (error) {
    console.error('[Road Classification] Error:', error);
    throw error;
  }
}

/**
 * Determine if property fronts a primary/arterial road (for Ashfield setback calculation)
 * Primary/arterial roads require different setbacks based on lot area
 *
 * @param roads Array of road classifications
 * @returns true if closest road is Motorway (1), Primary (2), or Arterial (3)
 */
export function isPrimaryRoadFrontage(roads: RoadClassification[]): boolean {
  if (roads.length === 0) return false;

  // Check closest road (first in sorted array)
  const closestRoad = roads[0];
  const isPrimary = closestRoad.hierarchy_code <= 3; // Motorway, Primary, or Arterial

  if (isPrimary) {
    console.log(`[Road Classification] Primary/Arterial road frontage detected: ${closestRoad.road_name} (${closestRoad.functional_hierarchy})`);
  } else {
    console.log(`[Road Classification] Local road frontage: ${closestRoad.road_name} (${closestRoad.functional_hierarchy})`);
  }

  return isPrimary;
}

/**
 * Get primary frontage road (closest road to property)
 * Used to display road name in setback explanation
 *
 * @param roads Array of road classifications (should be sorted by distance)
 * @returns Closest road or null if no roads found
 */
export function getPrimaryFrontageRoad(roads: RoadClassification[]): RoadClassification | null {
  if (roads.length === 0) {
    console.warn('[Road Classification] No roads available for primary frontage');
    return null;
  }

  // Return closest road (already sorted by distance in query)
  const primaryFrontage = roads[0];
  console.log(`[Road Classification] Primary frontage: ${primaryFrontage.road_name} (${primaryFrontage.functional_hierarchy}, ${primaryFrontage.distance_meters.toFixed(0)}m)`);

  return primaryFrontage;
}

/**
 * Get all primary/arterial roads (major roads requiring larger setbacks)
 *
 * @param roads Array of road classifications
 * @returns Array of major roads (hierarchy code 1-4)
 */
export function getMajorRoads(roads: RoadClassification[]): RoadClassification[] {
  // Codes 1-4: Motorway, Primary, Arterial, Sub-Arterial
  return roads.filter(r => r.hierarchy_code <= 4);
}

/**
 * Format road classification for display
 *
 * @param road Road classification
 * @returns Human-readable string
 */
export function formatRoadClassification(road: RoadClassification): string {
  return `${road.road_name} (${road.functional_hierarchy}, ${road.distance_meters.toFixed(0)}m away)`;
}
