/**
 * Ku-ring-gai DCP Part 20: does this lot adjoin the rail corridor or a busy road?
 *
 * prior-art-checked: reuse not viable. lib/greenweb-overlay.ts finds the lot the same way (nsw_cadastre_lots
 * covering the address point) but tests a DB overlay; Part 20's land is road and rail corridors on the NSW maps,
 * which no table here holds. lib/geometry/corner-lot-detection.ts reads road corridors for street edges only.
 *
 * The council's words (p20-2): "All development that is in, or immediately adjacent to, the rail corridor or a
 * busy road", and control 3 "On lots adjoining the rail corridor and/or a busy road". A lot is flagged when its
 * boundary is within the tolerance of:
 *  - a road-corridor parcel (NSW cadastre) labelled as one of the DCP's busy roads, or
 *  - Ku-ring-gai LEP SP2 railway land (the North Shore line).
 * Which roads, which labels, the tolerance and the measurements behind them: shared/krg-rail-busy-roads.json.
 *
 * Fail closed: no lot, or a map service that does not answer, gives a plain-words "couldn't check" note and no
 * flag, so the Part 20 rules are not shown and the page says why.
 */
import part20 from '@/shared/krg-rail-busy-roads.json';

type QueryFn = (
  sql: string,
  params?: unknown[]
) => Promise<{ rows: Array<Record<string, unknown>> }>;

export type FetchFn = (url: string, init: { method: 'POST'; body: URLSearchParams; signal?: AbortSignal }) =>
  Promise<{ ok: boolean; status: number; json: () => Promise<unknown> }>;

export interface RailOrBusyRoadConstraint {
  adjoins: true;
  /** DCP names of the busy roads the lot adjoins, e.g. "Pacific Highway". */
  roads: string[];
  rail: boolean;
}

/** The lot polygons holding the address point, merged, as GeoJSON. */
export const RAIL_ROAD_LOT_SQL = `
  SELECT ST_AsGeoJSON(ST_Union(l.geom)) AS lot_geojson
  FROM nsw_cadastre_lots l
  WHERE ST_Covers(l.geom, ST_SetSRID(ST_Point($1, $2), 4326))
`;

export const TOLERANCE_M: number = part20.tolerance_m;
const ROAD_URL = `${part20.road_corridor_layer}/query`;
const RAIL_URL = `${part20.rail_corridor.layer}/query`;

/** Map label -> the DCP's name for that road (only roads the maps can place). */
export const LABEL_TO_DCP_ROAD: ReadonlyMap<string, string> = new Map(
  part20.busy_roads.flatMap((r) => r.road_corridor_labels.map((label): [string, string] => [label, r.dcp_name]))
);

const sqlList = (values: Iterable<string>) => [...values].map((v) => `'${v.replace(/'/g, "''")}'`).join(',');
export const ROAD_WHERE = `roadnamelabel IN (${sqlList(LABEL_TO_DCP_ROAD.keys())})`;
export const RAIL_WHERE =
  `LGA_NAME = '${part20.rail_corridor.lga_name}' AND SYM_CODE = '${part20.rail_corridor.sym_code}'` +
  ` AND PURPOSE IN (${sqlList(part20.rail_corridor.purposes)})`;

/** GeoJSON Polygon / MultiPolygon -> Esri polygon rings. */
export function toEsriRings(geojson: unknown): number[][][] | null {
  const g = geojson as { type?: string; coordinates?: unknown };
  if (g?.type === 'Polygon' && Array.isArray(g.coordinates)) return g.coordinates as number[][][];
  if (g?.type === 'MultiPolygon' && Array.isArray(g.coordinates)) return (g.coordinates as number[][][][]).flat();
  return null;
}

function distanceQuery(rings: number[][][], where: string, outFields: string): URLSearchParams {
  return new URLSearchParams({
    where,
    geometry: JSON.stringify({ rings, spatialReference: { wkid: 4326 } }),
    geometryType: 'esriGeometryPolygon',
    inSR: '4326',
    spatialRel: 'esriSpatialRelIntersects',
    distance: String(TOLERANCE_M),
    units: 'esriSRUnit_Meter',
    outFields,
    returnGeometry: 'false',
    f: 'json',
  });
}

/** Feature attributes from an ArcGIS query; throws when the service answers with an error or no feature list. */
async function features(fetchFn: FetchFn, url: string, body: URLSearchParams): Promise<Array<Record<string, unknown>>> {
  const res = await fetchFn(url, { method: 'POST', body, signal: AbortSignal.timeout(10_000) });
  if (!res.ok) throw new Error(`map service HTTP ${res.status}`);
  const data = (await res.json()) as { error?: unknown; features?: Array<{ attributes?: Record<string, unknown> }> };
  if (data?.error || !Array.isArray(data?.features)) throw new Error('map service returned no feature list');
  return data.features.map((f) => f.attributes ?? {});
}

/** Raised when no cadastre lot holds the address point: adjacency is a property of the lot, so it was not checked. */
export class RailRoadLotNotFound extends Error {
  constructor() {
    super('no cadastre lot contains the address point');
    this.name = 'RailRoadLotNotFound';
  }
}

/**
 * The constraint, or null when the lot adjoins neither. Throws when the lot is not found or a map service fails.
 */
export async function railOrBusyRoadForPoint(
  query: QueryFn,
  fetchFn: FetchFn,
  lon: number,
  lat: number
): Promise<RailOrBusyRoadConstraint | null> {
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) throw new RailRoadLotNotFound();
  const lot = await query(RAIL_ROAD_LOT_SQL, [lon, lat]);
  const raw = lot.rows[0]?.lot_geojson;
  const rings = typeof raw === 'string' ? toEsriRings(JSON.parse(raw)) : null;
  if (!rings || rings.length === 0) throw new RailRoadLotNotFound();

  const [roadHits, railHits] = await Promise.all([
    features(fetchFn, ROAD_URL, distanceQuery(rings, ROAD_WHERE, 'roadnamelabel')),
    features(fetchFn, RAIL_URL, distanceQuery(rings, RAIL_WHERE, 'PURPOSE')),
  ]);
  const roads = [
    ...new Set(
      roadHits
        .map((a) => LABEL_TO_DCP_ROAD.get(String(a.roadnamelabel ?? '')))
        .filter((r): r is string => typeof r === 'string')
    ),
  ].sort();
  const rail = railHits.length > 0;
  return roads.length > 0 || rail ? { adjoins: true, roads, rail } : null;
}

/** What the property lookup records: the flag, or a plain-words note when the check could not run
 *  (without the flag the Part 20 rail and busy-road rules are not shown, so the page must say why). */
export async function railOrBusyRoadConstraints(
  query: QueryFn,
  fetchFn: FetchFn,
  lon: number,
  lat: number
): Promise<{ railOrBusyRoad?: RailOrBusyRoadConstraint; railOrBusyRoadUnchecked?: string }> {
  try {
    const railOrBusyRoad = await railOrBusyRoadForPoint(query, fetchFn, lon, lat);
    return railOrBusyRoad ? { railOrBusyRoad } : {};
  } catch (err) {
    if (err instanceof RailRoadLotNotFound) {
      return {
        railOrBusyRoadUnchecked:
          "We couldn't find this property's lot on the NSW lot map, so we couldn't check whether it adjoins the rail line or a busy road; the council's rail and busy-road rules may be missing.",
      };
    }
    console.warn('[rail-busy-road] adjacency check failed:', err);
    return {
      railOrBusyRoadUnchecked:
        "We couldn't check whether this lot adjoins the rail line or a busy road (the map service did not answer), so the council's rail and busy-road rules may be missing.",
    };
  }
}
