/**
 * Corner Lot Detection
 *
 * Detects corner lots by querying NSW Spatial Services for adjacent road parcels.
 * A corner lot has 2+ distinct roads touching its boundary.
 *
 * Legal definition (NSW): "A lot with 2 contiguous boundaries with roads
 * that intersect at an angle of 135 degrees or less"
 *
 * API: NSW Land Parcel Property Theme - RoadCorridor layer
 * Uses esriSpatialRelTouches to find roads that share a boundary with the lot.
 */

import type { LotGeometry } from '@/types/property';

// NSW Spatial Services Feature Server
const NSW_SPATIAL_BASE = 'https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Land_Parcel_Property_Theme_multiCRS/FeatureServer';

// Layer IDs
const ROAD_CORRIDOR_LAYER = 5;

export interface CornerLotResult {
  /** Whether lot is a corner lot (2+ adjacent roads) */
  isCornerLot: boolean;
  /** Names of adjacent roads */
  adjacentRoads: string[];
  /** Number of distinct road boundaries */
  roadCount: number;
  /** Confidence in detection (1.0 if API returned data, 0 if failed) */
  confidence: number;
  /** Error message if detection failed */
  error?: string;
}

interface RoadFeature {
  attributes: {
    cadid?: number;
    roadnamelabel?: string;
    roadtype?: string;
    objectid?: number;
  };
}

interface FeatureQueryResponse {
  features?: RoadFeature[];
  error?: {
    code: number;
    message: string;
  };
}

/**
 * Convert lot geometry rings to Esri JSON format for spatial query
 */
function lotGeometryToEsriJson(geometry: LotGeometry): string {
  const esriGeometry = {
    rings: geometry.rings,
    spatialReference: {
      wkid: geometry.spatialReference.wkid
    }
  };
  return JSON.stringify(esriGeometry);
}

/**
 * Detect if a lot is a corner lot by querying adjacent road parcels
 */
export async function detectCornerLot(geometry: LotGeometry): Promise<CornerLotResult> {
  if (!geometry?.rings?.length || !geometry.rings[0]?.length) {
    return {
      isCornerLot: false,
      adjacentRoads: [],
      roadCount: 0,
      confidence: 0,
      error: 'Invalid lot geometry'
    };
  }

  try {
    // Build the spatial query URL
    const geometryJson = lotGeometryToEsriJson(geometry);

    const queryParams = new URLSearchParams({
      geometry: geometryJson,
      geometryType: 'esriGeometryPolygon',
      spatialRel: 'esriSpatialRelTouches',
      outFields: 'roadnamelabel,roadtype,cadid',
      returnGeometry: 'false',
      f: 'json'
    });

    const url = `${NSW_SPATIAL_BASE}/${ROAD_CORRIDOR_LAYER}/query?${queryParams.toString()}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    });

    if (!response.ok) {
      return {
        isCornerLot: false,
        adjacentRoads: [],
        roadCount: 0,
        confidence: 0,
        error: `API returned ${response.status}: ${response.statusText}`
      };
    }

    const data: FeatureQueryResponse = await response.json();

    if (data.error) {
      return {
        isCornerLot: false,
        adjacentRoads: [],
        roadCount: 0,
        confidence: 0,
        error: `API error ${data.error.code}: ${data.error.message}`
      };
    }

    if (!data.features) {
      return {
        isCornerLot: false,
        adjacentRoads: [],
        roadCount: 0,
        confidence: 0,
        error: 'No features returned from API'
      };
    }

    // Extract unique road names
    const roadNames = new Set<string>();

    for (const feature of data.features) {
      const roadName = feature.attributes?.roadnamelabel;
      if (roadName && roadName.trim()) {
        roadNames.add(roadName.trim());
      }
    }

    const adjacentRoads = Array.from(roadNames).sort();
    const roadCount = adjacentRoads.length;
    const isCornerLot = roadCount >= 2;

    return {
      isCornerLot,
      adjacentRoads,
      roadCount,
      confidence: 1.0
    };

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return {
      isCornerLot: false,
      adjacentRoads: [],
      roadCount: 0,
      confidence: 0,
      error: `Failed to query road data: ${errorMessage}`
    };
  }
}
