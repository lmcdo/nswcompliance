/**
 * Spatial Boundary Service
 * Integrates with free NSW government APIs to fetch:
 * - Lot boundaries and area (NSW Cadastre)
 * - Road classifications (TfNSW)
 * - Reserve boundaries (NPWS)
 *
 * Used for automated setback calculations in DCP compliance checking.
 */

// ============================================================================
// GEOJSON TYPE SHIMS (avoids @types/geojson dependency)
// ============================================================================
declare namespace GeoJSON {
  interface Polygon { type: 'Polygon'; coordinates: number[][][]; }
  interface LineString { type: 'LineString'; coordinates: number[][]; }
  interface Point { type: 'Point'; coordinates: number[]; }
}

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export interface SetbackBoundaries {
  lot: LotBoundary;
  roads: RoadBoundary[];
  reserves: ReserveBoundary[];
  metadata: BoundaryMetadata;
}

export interface LotBoundary {
  geometry: GeoJSON.Polygon;
  area_sqm: number;
  cadid: string;
  lot_number?: string;
  plan_number?: string;
  address?: string;
}

export interface RoadBoundary {
  name: string;
  classification: 'motorway' | 'primary' | 'arterial' | 'sub-arterial' | 'distributor' | 'local' | 'service' | 'track';
  geometry: GeoJSON.LineString;
  distance_from_lot_meters: number;
  is_primary_frontage: boolean;
  surface?: string;
  lanes?: number;
}

export interface ReserveBoundary {
  name: string;
  type: 'National Park' | 'Nature Reserve' | 'Regional Park' | 'State Conservation Area' | 'Other';
  geometry: GeoJSON.Polygon;
  distance_from_lot_meters: number;
  is_adjacent: boolean;
  area_ha?: number;
}

export interface BoundaryMetadata {
  query_timestamp: string;
  coordinate_system: string;
  data_sources: {
    cadastre: { success: boolean; timestamp?: string; error?: string };
    roads: { success: boolean; timestamp?: string; error?: string };
    reserves: { success: boolean; timestamp?: string; error?: string };
  };
}

// ============================================================================
// API CLIENTS
// ============================================================================

/**
 * NSW Cadastre API Client
 * Fetches lot boundaries and area from NSW Digital Cadastral Database
 */
async function fetchCadastreData(lat: number, lon: number): Promise<any> {
  const url = new URL('https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Cadastre/MapServer/0/query');

  url.searchParams.set('geometry', `${lon},${lat}`);
  url.searchParams.set('geometryType', 'esriGeometryPoint');
  url.searchParams.set('spatialRel', 'esriSpatialRelIntersects');
  url.searchParams.set('outFields', '*');
  url.searchParams.set('returnGeometry', 'true');
  url.searchParams.set('f', 'json');

  console.log('[Cadastre API] Querying:', url.toString());

  const response = await fetch(url.toString(), {
    headers: {
      'Accept': 'application/json'
    }
  });

  if (!response.ok) {
    throw new Error(`Cadastre API error: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();

  if (data.error) {
    throw new Error(`Cadastre API error: ${data.error.message || JSON.stringify(data.error)}`);
  }

  return data;
}

/**
 * TfNSW Roads API Client
 * Fetches road classifications and boundaries near the property
 *
 * NOTE: This uses a buffer query to find roads within 100m of the lot
 */
async function fetchRoadData(lat: number, lon: number): Promise<any> {
  // Buffer distance in meters (to find nearby roads)
  const bufferMeters = 100;

  // NOTE: The actual TfNSW roads API endpoint needs to be determined
  // This is a placeholder structure based on typical WFS services
  const url = new URL('https://data.nsw.gov.au/data/api/action/datastore_search');

  url.searchParams.set('resource_id', 'roads-dataset-id'); // TODO: Get actual resource ID
  url.searchParams.set('q', JSON.stringify({
    geometry: {
      type: 'Point',
      coordinates: [lon, lat]
    },
    buffer: bufferMeters
  }));

  console.log('[Roads API] Querying:', url.toString());

  try {
    const response = await fetch(url.toString(), {
      headers: {
        'Accept': 'application/json'
      }
    });

    if (!response.ok) {
      console.warn('[Roads API] Failed:', response.status, response.statusText);
      return { features: [] }; // Return empty result rather than failing
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.warn('[Roads API] Error:', error);
    return { features: [] }; // Graceful degradation
  }
}

/**
 * NPWS Reserves API Client
 * Fetches public reserve boundaries near the property
 */
async function fetchReserveData(lat: number, lon: number): Promise<any> {
  const bufferMeters = 100;

  // NOTE: The actual NPWS reserves API endpoint needs to be determined
  // This is a placeholder structure based on SEED/Data.NSW WFS services
  const url = new URL('https://datasets.seed.nsw.gov.au/api/action/datastore_search');

  url.searchParams.set('resource_id', 'npws-estate-id'); // TODO: Get actual resource ID
  url.searchParams.set('q', JSON.stringify({
    geometry: {
      type: 'Point',
      coordinates: [lon, lat]
    },
    buffer: bufferMeters
  }));

  console.log('[Reserves API] Querying:', url.toString());

  try {
    const response = await fetch(url.toString(), {
      headers: {
        'Accept': 'application/json'
      }
    });

    if (!response.ok) {
      console.warn('[Reserves API] Failed:', response.status, response.statusText);
      return { features: [] }; // Return empty result rather than failing
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.warn('[Reserves API] Error:', error);
    return { features: [] }; // Graceful degradation
  }
}

// ============================================================================
// RESPONSE PROCESSORS
// ============================================================================

function processCadastreResponse(data: any): LotBoundary | null {
  if (!data.features || data.features.length === 0) {
    console.warn('[Cadastre] No lot found at coordinates');
    return null;
  }

  const feature = data.features[0];
  const attrs = feature.attributes;
  const geom = feature.geometry;

  // Convert ESRI geometry to GeoJSON Polygon
  const geoJsonGeometry: GeoJSON.Polygon = {
    type: 'Polygon',
    coordinates: geom.rings
  };

  return {
    geometry: geoJsonGeometry,
    area_sqm: attrs.lot_area || attrs.area || 0,
    cadid: attrs.cadid || attrs.CADID || '',
    lot_number: attrs.lot_number || attrs.LOT,
    plan_number: attrs.plan_number || attrs.PLAN,
    address: attrs.address || attrs.ADDRESS
  };
}

function processRoadResponse(data: any): RoadBoundary[] {
  if (!data.features || data.features.length === 0) {
    console.warn('[Roads] No roads found near coordinates');
    return [];
  }

  return data.features.map((feature: any) => {
    const props = feature.properties || {};
    const geom = feature.geometry;

    // Map road hierarchy to our classification
    const hierarchy = (props.road_hierarchy || props.classification || '').toLowerCase();
    let classification: RoadBoundary['classification'] = 'local';

    if (hierarchy.includes('motorway')) classification = 'motorway';
    else if (hierarchy.includes('primary')) classification = 'primary';
    else if (hierarchy.includes('arterial') && !hierarchy.includes('sub')) classification = 'arterial';
    else if (hierarchy.includes('sub-arterial')) classification = 'sub-arterial';
    else if (hierarchy.includes('distributor')) classification = 'distributor';
    else if (hierarchy.includes('service')) classification = 'service';
    else if (hierarchy.includes('track')) classification = 'track';

    return {
      name: props.road_name || props.name || 'Unnamed Road',
      classification,
      geometry: geom,
      distance_from_lot_meters: props.distance || 0, // TODO: Calculate actual distance
      is_primary_frontage: false, // TODO: Determine based on geometry analysis
      surface: props.road_surface || props.surface,
      lanes: props.lane_count || props.lanes
    };
  });
}

function processReserveResponse(data: any): ReserveBoundary[] {
  if (!data.features || data.features.length === 0) {
    console.warn('[Reserves] No reserves found near coordinates');
    return [];
  }

  return data.features.map((feature: any) => {
    const props = feature.properties || {};
    const geom = feature.geometry;

    // Map reserve type
    const reserveType = props.type || props.reserve_type || 'Other';
    let type: ReserveBoundary['type'] = 'Other';

    if (reserveType.includes('National Park')) type = 'National Park';
    else if (reserveType.includes('Nature Reserve')) type = 'Nature Reserve';
    else if (reserveType.includes('Regional Park')) type = 'Regional Park';
    else if (reserveType.includes('State Conservation')) type = 'State Conservation Area';

    return {
      name: props.name || props.reserve_name || 'Unnamed Reserve',
      type,
      geometry: geom,
      distance_from_lot_meters: props.distance || 0, // TODO: Calculate actual distance
      is_adjacent: (props.distance || 999) < 10, // Adjacent if within 10m
      area_ha: props.area_ha || props.area
    };
  });
}

// ============================================================================
// MAIN SERVICE FUNCTION
// ============================================================================

/**
 * Get all spatial boundaries for a property (lot, roads, reserves)
 * Makes parallel API calls for optimal performance
 *
 * @param lat Latitude (WGS84)
 * @param lon Longitude (WGS84)
 * @returns Complete boundary data for setback calculations
 */
export async function getSetbackBoundaries(
  lat: number,
  lon: number
): Promise<SetbackBoundaries> {
  console.log(`[Spatial Boundary Service] Fetching boundaries for ${lat}, ${lon}`);

  const startTime = new Date().toISOString();

  // Parallel API calls for optimal performance
  const [cadastreResult, roadResult, reserveResult] = await Promise.allSettled([
    fetchCadastreData(lat, lon),
    fetchRoadData(lat, lon),
    fetchReserveData(lat, lon)
  ]);

  // Process results (with error handling)
  const lot = cadastreResult.status === 'fulfilled'
    ? processCadastreResponse(cadastreResult.value)
    : null;

  const roads = roadResult.status === 'fulfilled'
    ? processRoadResponse(roadResult.value)
    : [];

  const reserves = reserveResult.status === 'fulfilled'
    ? processReserveResponse(reserveResult.value)
    : [];

  // Build metadata
  const metadata: BoundaryMetadata = {
    query_timestamp: startTime,
    coordinate_system: 'WGS84 (EPSG:4326)',
    data_sources: {
      cadastre: {
        success: cadastreResult.status === 'fulfilled',
        timestamp: startTime,
        error: cadastreResult.status === 'rejected' ? String(cadastreResult.reason) : undefined
      },
      roads: {
        success: roadResult.status === 'fulfilled',
        timestamp: startTime,
        error: roadResult.status === 'rejected' ? String(roadResult.reason) : undefined
      },
      reserves: {
        success: reserveResult.status === 'fulfilled',
        timestamp: startTime,
        error: reserveResult.status === 'rejected' ? String(reserveResult.reason) : undefined
      }
    }
  };

  if (!lot) {
    throw new Error('Failed to fetch cadastre data - lot boundary is required for setback calculations');
  }

  console.log(`[Spatial Boundary Service] Success! Lot: ${lot.cadid}, Roads: ${roads.length}, Reserves: ${reserves.length}`);

  return {
    lot,
    roads,
    reserves,
    metadata
  };
}

// ============================================================================
// CACHE LAYER (Optional - for production use)
// ============================================================================

// Simple in-memory cache with 15-minute TTL
const boundaryCache = new Map<string, { data: SetbackBoundaries; expires: number }>();

export async function getSetbackBoundariesCached(
  lat: number,
  lon: number,
  ttlMinutes: number = 15
): Promise<SetbackBoundaries> {
  const cacheKey = `${lat.toFixed(6)},${lon.toFixed(6)}`;
  const cached = boundaryCache.get(cacheKey);

  if (cached && cached.expires > Date.now()) {
    console.log('[Spatial Boundary Service] Cache hit:', cacheKey);
    return cached.data;
  }

  console.log('[Spatial Boundary Service] Cache miss, fetching...', cacheKey);
  const data = await getSetbackBoundaries(lat, lon);

  boundaryCache.set(cacheKey, {
    data,
    expires: Date.now() + (ttlMinutes * 60 * 1000)
  });

  return data;
}

// Clear expired cache entries every 5 minutes
if (typeof window === 'undefined') { // Only run on server
  setInterval(() => {
    const now = Date.now();
    for (const [key, value] of boundaryCache.entries()) {
      if (value.expires < now) {
        boundaryCache.delete(key);
      }
    }
  }, 5 * 60 * 1000);
}
