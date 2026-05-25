import { NextRequest, NextResponse } from 'next/server';
import { getClient } from '@/lib/db';
import { getHeritageCache, createCacheKey } from '@/lib/cache';
import { PropertySearchSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';

/**
 * Convert Web Mercator (EPSG:3857) coordinates to WGS84 (EPSG:4326)
 * NSW Valuation API returns coordinates in Web Mercator format
 * HCA GeoJSON uses WGS84 format
 *
 * @param x - Web Mercator X coordinate (meters)
 * @param y - Web Mercator Y coordinate (meters)
 * @returns [longitude, latitude] in WGS84 degrees
 */
function webMercatorToWGS84(x: number, y: number): [number, number] {
  const earthRadius = 20037508.34; // Earth's radius in Web Mercator
  const lon = (x / earthRadius) * 180;
  const lat = (Math.atan(Math.exp((y / earthRadius) * Math.PI)) * 360 / Math.PI) - 90;
  return [lon, lat];
}

/**
 * Detect coordinate system based on magnitude
 * Web Mercator coordinates for NSW are typically 16-17 million (x) and -4 million (y)
 * WGS84 coordinates for NSW are typically 150-152 (lon) and -33 to -34 (lat)
 *
 * @param x - X coordinate
 * @param y - Y coordinate
 * @returns true if coordinates appear to be Web Mercator
 */
function isWebMercator(x: number, y: number): boolean {
  // NSW in Web Mercator: x ~16-17 million, y ~-4 million
  // NSW in WGS84: x ~150-152, y ~-33 to -34
  return Math.abs(x) > 1000 || Math.abs(y) > 1000;
}

/**
 * Point-in-polygon check using ray casting algorithm
 * No external dependencies required
 */
function pointInPolygon(point: [number, number], polygon: number[][][]): boolean {
  const [x, y] = point;
  const ring = polygon[0]; // Use outer ring of polygon

  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];

    const intersect = ((yi > y) !== (yj > y)) &&
      (x < (xj - xi) * (y - yi) / (yj - yi) + xi);

    if (intersect) inside = !inside;
  }

  return inside;
}

/**
 * POST /api/heritage/hca-check
 *
 * Check if a property point is within a Heritage Conservation Area
 *
 * Request body:
 * {
 *   "x": 151.159,
 *   "y": -33.899,
 *   "lga": "INNER WEST"
 * }
 *
 * Response:
 * {
 *   "success": true,
 *   "data": {
 *     "inHCA": true,
 *     "hca": {
 *       "id": "C86",
 *       "name": "Lackey Street and Simpson Park Heritage Conservation Area",
 *       "significance": "Local",
 *       "legislativeClause": "Clause 5.10",
 *       "epiName": "Inner West Local Environmental Plan 2022",
 *       "layClass": "Conservation Area - General"
 *     }
 *   }
 * }
 */
export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    // Validate request using PropertySearchSchema
    const validation = validateRequest(PropertySearchSchema, {
      address: body.address || 'Heritage Check',
      lga: body.lga,
    });

    if (!validation.success) {
      return NextResponse.json({
        success: false,
        error: 'Invalid request data',
        details: formatValidationErrors(validation.details),
      }, { status: 400 });
    }

    const { x, y, lga: lgaRaw } = body;

    // Normalise LGA to uppercase to match heritage_conservation_areas.lga_name format
    const lga = typeof lgaRaw === 'string' ? lgaRaw.toUpperCase() : lgaRaw;

    // Validate inputs
    if (!x || !y) {
      return NextResponse.json({
        success: false,
        error: 'Missing required parameters: x, y'
      }, { status: 400 });
    }

    // Parse coordinates
    let pointX = parseFloat(x);
    let pointY = parseFloat(y);

    // Check cache (round coordinates to 6 decimal places for cache key)
    const roundedX = pointX.toFixed(6);
    const roundedY = pointY.toFixed(6);
    const cacheKey = createCacheKey('hca', { x: roundedX, y: roundedY, lga: lga?.toUpperCase() });
    const cache = getHeritageCache();
    const cached = cache.get(cacheKey);

    if (cached) {
      console.log(`[Heritage HCA API] Cache HIT: ${cacheKey}`);
      return NextResponse.json({
        ...cached,
        metadata: {
          ...cached.metadata,
          fromCache: true,
          cacheHit: true
        }
      });
    }

    console.log(`[Heritage HCA API] Cache MISS: ${cacheKey}`);

    if (isNaN(pointX) || isNaN(pointY)) {
      return NextResponse.json({
        success: false,
        error: 'Invalid coordinates'
      }, { status: 400 });
    }

    console.log(`[HCA Check] Input coordinates: (${pointX}, ${pointY}), LGA: ${lga}`);

    // Auto-detect and convert Web Mercator to WGS84 if needed
    if (isWebMercator(pointX, pointY)) {
      const [lon, lat] = webMercatorToWGS84(pointX, pointY);
      console.log(`[HCA Check] Detected Web Mercator, converted to WGS84: (${lon}, ${lat})`);
      pointX = lon;
      pointY = lat;
    } else {
      console.log(`[HCA Check] Coordinates appear to be WGS84, using as-is`);
    }

    // Stage 1: Bounding box pre-filter (fast)
    const client = await getClient();

    try {
      const bboxQuery = `
        SELECT
          h_id,
          h_name,
          significance,
          legislative_clause,
          epi_name,
          lay_class,
          geometry_json
        FROM heritage_conservation_areas
        WHERE lga_name = $1
        AND bbox_min_x <= $2
        AND bbox_max_x >= $2
        AND bbox_min_y <= $3
        AND bbox_max_y >= $3;
      `;

      const bboxResult = await client.query(bboxQuery, [lga, pointX, pointY]);

      console.log(`[HCA Check] Bounding box filter: ${bboxResult.rows.length} candidates`);

      if (bboxResult.rows.length === 0) {
        const response = {
          success: true,
          data: { inHCA: false },
          metadata: { fromCache: false }
        };
        cache.set(cacheKey, response);
        return NextResponse.json(response);
      }

      // Stage 2: Precise point-in-polygon check
      for (const row of bboxResult.rows) {
        const geometry = row.geometry_json;

        if (geometry.type === 'Polygon') {
          const isInside = pointInPolygon([pointX, pointY], geometry.coordinates);

          if (isInside) {
            console.log(`[HCA Check] Match found: ${row.h_id} - ${row.h_name}`);

            const response = {
              success: true,
              data: {
                inHCA: true,
                hca: {
                  id: row.h_id,
                  name: row.h_name,
                  significance: row.significance,
                  legislativeClause: row.legislative_clause,
                  epiName: row.epi_name,
                  layClass: row.lay_class
                }
              },
              metadata: { fromCache: false }
            };
            cache.set(cacheKey, response);
            return NextResponse.json(response);
          }
        }
      }

      // No match found after precise check
      console.log(`[HCA Check] No match found (bbox candidates checked, none contained point)`);

      const response = {
        success: true,
        data: { inHCA: false },
        metadata: { fromCache: false }
      };
      cache.set(cacheKey, response);
      return NextResponse.json(response);

    } finally {
      client.release();
    }

  } catch (error) {
    console.error('[HCA Check] Error:', error);

    return NextResponse.json({
      success: false,
      error: 'Failed to check HCA status'
    }, { status: 500 });
  }
}
