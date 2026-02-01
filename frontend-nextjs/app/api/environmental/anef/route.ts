import { NextRequest, NextResponse } from 'next/server';
import { getClient } from '@/lib/db';
import { CoordinatesSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';


export const dynamic = 'force-dynamic';
/**
 * ANEF Building Acceptability Standards (AS2021:2015)
 * Defines acceptable, conditional, and unacceptable ANEF levels for each building type
 */
const BUILDING_STANDARDS: Record<string, {
  displayName: string;
  acceptableMax: number;
  conditionalMax: number;
}> = {
  house: {
    displayName: 'House, home unit, flat, caravan park',
    acceptableMax: 20,
    conditionalMax: 25,
  },
  hotel: {
    displayName: 'Hotel, motel, hostel',
    acceptableMax: 25,
    conditionalMax: 30,
  },
  school: {
    displayName: 'School, university',
    acceptableMax: 20,
    conditionalMax: 25,
  },
  hospital: {
    displayName: 'Hospital, nursing home',
    acceptableMax: 20,
    conditionalMax: 25,
  },
  public: {
    displayName: 'Public building',
    acceptableMax: 20,
    conditionalMax: 30,
  },
  commercial: {
    displayName: 'Commercial building',
    acceptableMax: 25,
    conditionalMax: 35,
  },
  light_industrial: {
    displayName: 'Light industrial',
    acceptableMax: 30,
    conditionalMax: 40,
  },
  industrial: {
    displayName: 'Other industrial',
    acceptableMax: 999, // Acceptable in all zones
    conditionalMax: 999,
  },
};

/**
 * POST /api/environmental/anef
 *
 * Check ANEF contour levels for a property location
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate coordinates using CoordinatesSchema
    const validation = validateRequest(CoordinatesSchema, {
      lat: body.lat,
      lng: body.lng,
    });

    if (!validation.success) {
      return NextResponse.json({
        success: false,
        error: 'Invalid coordinates',
        details: formatValidationErrors(validation.details),
      }, { status: 400 });
    }

    const { lat, lng } = validation.data;

    // Delegate to GET handler with query params
    const url = new URL(request.url);
    url.searchParams.set('lat', lat.toString());
    url.searchParams.set('lng', lng.toString());

    return GET(new NextRequest(url));
  } catch (error) {
    console.error('[ANEF API] POST error:', error);
    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error'
    }, { status: 500 });
  }
}

/**
 * Point-in-polygon check using ray casting algorithm
 */
function pointInPolygon(point: [number, number], polygon: number[][][]): boolean {
  const [x, y] = point;
  const ring = polygon[0];

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
 * Calculate building acceptability for a given ANEF level
 */
function getBuildingAcceptability(anefLevel: number): Array<{
  buildingType: string;
  displayName: string;
  status: 'acceptable' | 'conditional' | 'unacceptable';
}> {
  return Object.entries(BUILDING_STANDARDS).map(([type, standards]) => {
    let status: 'acceptable' | 'conditional' | 'unacceptable';

    if (anefLevel < standards.acceptableMax) {
      status = 'acceptable';
    } else if (anefLevel <= standards.conditionalMax) {
      status = 'conditional';
    } else {
      status = 'unacceptable';
    }

    return {
      buildingType: type,
      displayName: standards.displayName,
      status,
    };
  });
}

/**
 * GET /api/environmental/anef
 *
 * Check if a property is within an ANEF (Aircraft Noise Exposure Forecast) zone
 *
 * Query parameters:
 * - lat: Latitude (WGS84)
 * - lon: Longitude (WGS84)
 *
 * Response:
 * {
 *   "success": true,
 *   "data": {
 *     "inAnefZone": true,
 *     "anefLevel": 25,
 *     "airport": {
 *       "code": "YSSY",
 *       "name": "Sydney Airport",
 *       "version": "ANEF 2039"
 *     },
 *     "buildingAcceptability": [
 *       { "buildingType": "house", "displayName": "House...", "status": "conditional" },
 *       ...
 *     ],
 *     "standardReference": "AS2021:2015"
 *   }
 * }
 */
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const lat = parseFloat(searchParams.get('lat') || '');
    const lon = parseFloat(searchParams.get('lon') || '');

    if (isNaN(lat) || isNaN(lon)) {
      return NextResponse.json({
        success: false,
        error: 'Invalid coordinates. Required: lat, lon (WGS84)'
      }, { status: 400 });
    }

    console.log(`[ANEF Check] Checking coordinates: (${lon}, ${lat})`);

    const client = await getClient();

    try {
      // Query ANEF zones that contain the point
      // Using bounding box pre-filter then point-in-polygon
      const query = `
        SELECT
          anef_level,
          airport_code,
          airport_name,
          anef_version,
          geometry_json
        FROM anef_zones
        WHERE bbox_min_lon <= $1
          AND bbox_max_lon >= $1
          AND bbox_min_lat <= $2
          AND bbox_max_lat >= $2
        ORDER BY anef_level DESC;
      `;

      const result = await client.query(query, [lon, lat]);

      console.log(`[ANEF Check] Bounding box filter: ${result.rows.length} candidates`);

      if (result.rows.length === 0) {
        return NextResponse.json({
          success: true,
          data: {
            inAnefZone: false,
            anefLevel: null,
            airport: null,
            buildingAcceptability: null,
            standardReference: 'AS2021:2015'
          }
        });
      }

      // Check each zone with point-in-polygon
      // Return the highest (most restrictive) ANEF level
      let highestAnef: {
        level: number;
        code: string;
        name: string;
        version: string;
      } | null = null;

      for (const row of result.rows) {
        const geometry = row.geometry_json;

        if (geometry && geometry.type === 'Polygon') {
          const isInside = pointInPolygon([lon, lat], geometry.coordinates);

          if (isInside) {
            if (!highestAnef || row.anef_level > highestAnef.level) {
              highestAnef = {
                level: row.anef_level,
                code: row.airport_code,
                name: row.airport_name,
                version: row.anef_version,
              };
            }
          }
        }
      }

      if (!highestAnef) {
        return NextResponse.json({
          success: true,
          data: {
            inAnefZone: false,
            anefLevel: null,
            airport: null,
            buildingAcceptability: null,
            standardReference: 'AS2021:2015'
          }
        });
      }

      console.log(`[ANEF Check] Property in ANEF ${highestAnef.level} zone`);

      return NextResponse.json({
        success: true,
        data: {
          inAnefZone: true,
          anefLevel: highestAnef.level,
          airport: {
            code: highestAnef.code,
            name: highestAnef.name,
            version: highestAnef.version,
          },
          buildingAcceptability: getBuildingAcceptability(highestAnef.level),
          standardReference: 'AS2021:2015'
        }
      });

    } finally {
      client.release();
    }

  } catch (error) {
    console.error('[ANEF Check] Error:', error);

    return NextResponse.json({
      success: false,
      error: 'Failed to check ANEF status'
    }, { status: 500 });
  }
}
