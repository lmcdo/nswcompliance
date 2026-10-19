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
 * Queries an envelope around the lot and keeps only roads whose boundary runs
 * along a lot edge (street-frontage.ts) -- the geometry, not the query, decides.
 */

import type { LotGeometry } from '@/types/property';
import { scaleFactorForRing, usableRing } from './mercator';
import { measureStreetFrontage, type RoadShape, type StreetFrontage } from './street-frontage';

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
  /** Street edges per named road and the lot's width range back from each (street-frontage.ts). */
  streetFrontage?: StreetFrontage;
}

interface RoadFeature {
  attributes: {
    cadid?: number;
    roadnamelabel?: string;
    roadtype?: string;
    objectid?: number;
  };
  geometry?: { rings: number[][][] };
}

interface FeatureQueryResponse {
  features?: RoadFeature[];
  error?: {
    code: number;
    message: string;
  };
}

/**
 * Envelope around the lot, padded by ROAD_SEARCH_PAD_M. A "touches" query on the lot polygon itself missed the road
 * entirely wherever the cadastre's lot and road-corridor layers are not coincident: measured gaps of 1.2-1.5 m at
 * 18 Wyreema Ave Padstow, 39A Neirbo Ave Hurstville and 390 Caddens Rd Claremont Meadows (roadCount 0 for lots that
 * plainly front a street; 1 Logan Ave Haberfield, on Logan Ave and Nicholls Ave, read "not a corner"). Which road
 * edges actually bound the lot is then decided by geometry in street-frontage.ts, not by the query.
 */
const ROAD_SEARCH_PAD_M = 20;

function paddedEnvelope(ring: number[][]): string | null {
  const ok = usableRing(ring);
  if (!ok) return null;
  const pad = ROAD_SEARCH_PAD_M * scaleFactorForRing(ok);
  const xs = ok.map((p) => p[0]);
  const ys = ok.map((p) => p[1]);
  return `${Math.min(...xs) - pad},${Math.min(...ys) - pad},${Math.max(...xs) + pad},${Math.max(...ys) + pad}`;
}

function unavailable(error: string): CornerLotResult {
  return {
    isCornerLot: false,
    adjacentRoads: [],
    roadCount: 0,
    confidence: 0,
    error,
    streetFrontage: { status: 'unavailable', roads: [], unnamedRoadEdge_m: 0, error },
  };
}

/**
 * Detect corner lot and measure street frontage from the road parcels around the lot.
 * A corner lot has street frontage on 2+ named roads.
 */
export async function detectCornerLot(geometry: LotGeometry): Promise<CornerLotResult> {
  if (!geometry?.rings?.length || !geometry.rings[0]?.length) {
    return unavailable('Invalid lot geometry');
  }
  const wkid = geometry.spatialReference?.wkid;
  if (wkid !== 3857 && wkid !== 102100) {
    return unavailable(`Lot geometry is in wkid ${wkid}; street frontage needs EPSG:3857`);
  }
  const envelope = paddedEnvelope(geometry.rings[0]);
  if (!envelope) return unavailable('Invalid lot geometry');

  try {
    const queryParams = new URLSearchParams({
      geometry: envelope,
      geometryType: 'esriGeometryEnvelope',
      inSR: '3857',
      outSR: '3857',
      spatialRel: 'esriSpatialRelIntersects',
      outFields: 'roadnamelabel,roadtype,cadid',
      returnGeometry: 'true',
      f: 'json'
    });

    const url = `${NSW_SPATIAL_BASE}/${ROAD_CORRIDOR_LAYER}/query?${queryParams.toString()}`;

    // The NSW road map times out now and then (Winston Hills, 2026-10-19: "This operation was
    // aborted" after one 10 s try). A lot either is on a corner or is not, so try again with a
    // longer wait before telling the reader we could not find out.
    let response: Response | null = null;
    let lastError: unknown = null;
    for (const waitMs of [10000, 15000, 20000]) {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), waitMs);
      try {
        response = await fetch(url, {
          method: 'GET',
          headers: {
            'Accept': 'application/json'
          },
          signal: controller.signal
        });
        if (response.ok || response.status < 500) break;
      } catch (e) {
        lastError = e;
        response = null;
      } finally {
        clearTimeout(timeoutId);
      }
    }
    if (!response) throw lastError ?? new Error('road map did not answer');

    if (!response.ok) {
      return unavailable(`API returned ${response.status}: ${response.statusText}`);
    }

    const data: FeatureQueryResponse = await response.json();

    if (data.error) {
      return unavailable(`API error ${data.error.code}: ${data.error.message}`);
    }

    if (!data.features) {
      return unavailable('No features returned from API');
    }

    const roads: RoadShape[] = data.features
      .filter((f) => Array.isArray(f.geometry?.rings))
      .map((f) => ({ name: f.attributes?.roadnamelabel ?? null, rings: f.geometry!.rings }));
    const streetFrontage = measureStreetFrontage(geometry.rings[0], roads);

    const adjacentRoads = streetFrontage.roads.map((r) => r.road);
    const roadCount = adjacentRoads.length;

    return {
      isCornerLot: roadCount >= 2,
      adjacentRoads,
      roadCount,
      confidence: 1.0,
      streetFrontage,
    };

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return unavailable(`Failed to query road data: ${errorMessage}`);
  }
}
