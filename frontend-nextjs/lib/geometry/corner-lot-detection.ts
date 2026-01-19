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
 * Uses a small buffer around the lot bounding box to find adjacent roads,
 * since road corridor polygons don't always touch lot boundaries exactly.
 */

import type { LotGeometry } from '@/types/property';

// NSW Spatial Services Feature Server
const NSW_SPATIAL_BASE = 'https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Land_Parcel_Property_Theme_multiCRS/FeatureServer';

// Layer IDs
const ROAD_CORRIDOR_LAYER = 5;

// Buffer distance in meters for road detection
// Road corridor polygons often don't touch lot boundaries exactly
const ROAD_BUFFER_METERS = 10;

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
 * Create a buffered envelope around the lot geometry for spatial query.
 * This accounts for small gaps between road corridors and lot boundaries.
 */
function createBufferedEnvelope(geometry: LotGeometry, bufferMeters: number): string {
  const coords = geometry.rings[0];
  const xs = coords.map(c => c[0]);
  const ys = coords.map(c => c[1]);

  const envelope = {
    xmin: Math.min(...xs) - bufferMeters,
    ymin: Math.min(...ys) - bufferMeters,
    xmax: Math.max(...xs) + bufferMeters,
    ymax: Math.max(...ys) + bufferMeters,
    spatialReference: {
      wkid: geometry.spatialReference.wkid
    }
  };
  return JSON.stringify(envelope);
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
    // Build the spatial query URL with buffered envelope
    // Using envelope + intersects instead of polygon + touches because
    // road corridor polygons often have small gaps from lot boundaries
    const envelopeJson = createBufferedEnvelope(geometry, ROAD_BUFFER_METERS);

    const queryParams = new URLSearchParams({
      geometry: envelopeJson,
      geometryType: 'esriGeometryEnvelope',
      spatialRel: 'esriSpatialRelIntersects',
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
