/**
 * Shared pieces for "does this LOT adjoin X" checks: find the lot that holds the address point, and ask a public
 * ArcGIS layer for features within a distance of that lot.
 *
 * prior-art-checked: split out of lib/rail-busy-road.ts (Ku-ring-gai Part 20) so lib/classified-road.ts can use the
 * same lot lookup and the same fail-closed service handling instead of a copy.
 */

import { lookupBudgetSignal } from './fetch-timeout';

export type QueryFn = (
  sql: string,
  params?: unknown[]
) => Promise<{ rows: Array<Record<string, unknown>> }>;

export type FetchFn = (url: string, init: { method: 'POST'; body: URLSearchParams; signal?: AbortSignal }) =>
  Promise<{ ok: boolean; status: number; json: () => Promise<unknown> }>;

/** The lot polygons holding the address point, merged, as GeoJSON. */
export const LOT_SQL = `
  SELECT ST_AsGeoJSON(ST_Union(l.geom)) AS lot_geojson
  FROM nsw_cadastre_lots l
  WHERE ST_Covers(l.geom, ST_SetSRID(ST_Point($1, $2), 4326))
`;

/** Raised when no cadastre lot holds the address point: adjacency is a property of the lot, so it was not checked. */
export class LotNotFound extends Error {
  constructor() {
    super('no cadastre lot contains the address point');
    this.name = 'LotNotFound';
  }
}

/** GeoJSON Polygon / MultiPolygon -> Esri polygon rings. */
export function toEsriRings(geojson: unknown): number[][][] | null {
  const g = geojson as { type?: string; coordinates?: unknown };
  if (g?.type === 'Polygon' && Array.isArray(g.coordinates)) return g.coordinates as number[][][];
  if (g?.type === 'MultiPolygon' && Array.isArray(g.coordinates)) return (g.coordinates as number[][][][]).flat();
  return null;
}

/** The lot holding (lon, lat) as Esri rings, plus its GeoJSON text. Throws LotNotFound when there is none. */
export async function lotForPoint(query: QueryFn, lon: number, lat: number): Promise<{ rings: number[][][]; geojson: string }> {
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) throw new LotNotFound();
  const lot = await query(LOT_SQL, [lon, lat]);
  const raw = lot.rows[0]?.lot_geojson;
  const rings = typeof raw === 'string' ? toEsriRings(JSON.parse(raw)) : null;
  if (typeof raw !== 'string' || !rings || rings.length === 0) throw new LotNotFound();
  return { rings, geojson: raw };
}

/** An ArcGIS query for features within `distanceM` of the lot. `format` 'geojson' also returns geometry (WGS84). */
export function distanceQuery(
  rings: number[][][],
  where: string,
  outFields: string,
  distanceM: number,
  format: 'json' | 'geojson' = 'json'
): URLSearchParams {
  return new URLSearchParams({
    where,
    geometry: JSON.stringify({ rings, spatialReference: { wkid: 4326 } }),
    geometryType: 'esriGeometryPolygon',
    inSR: '4326',
    spatialRel: 'esriSpatialRelIntersects',
    distance: String(distanceM),
    units: 'esriSRUnit_Meter',
    outFields,
    ...(format === 'geojson' ? { returnGeometry: 'true', outSR: '4326', f: 'geojson' } : { returnGeometry: 'false', f: 'json' }),
  });
}

async function post(fetchFn: FetchFn, url: string, body: URLSearchParams): Promise<Record<string, unknown>> {
  // 10 s for this call, and never past the lookup's own time limit (lib/fetch-timeout.ts).
  const budget = lookupBudgetSignal();
  const signal = budget ? AbortSignal.any([AbortSignal.timeout(10_000), budget]) : AbortSignal.timeout(10_000);
  const res = await fetchFn(url, { method: 'POST', body, signal });
  if (!res.ok) throw new Error(`map service HTTP ${res.status}`);
  const data = (await res.json()) as Record<string, unknown> | null;
  if (!data || data.error || !Array.isArray(data.features)) throw new Error('map service returned no feature list');
  // A capped answer is an incomplete answer: fail closed rather than miss the feature that was cut off.
  if (data.exceededTransferLimit === true || (data.properties as { exceededTransferLimit?: boolean } | undefined)?.exceededTransferLimit) {
    throw new Error('map service answer was cut off');
  }
  return data;
}

/** Feature attributes from an f=json query; throws when the service answers with an error or no feature list. */
export async function arcgisAttributes(fetchFn: FetchFn, url: string, body: URLSearchParams): Promise<Array<Record<string, unknown>>> {
  const data = await post(fetchFn, url, body);
  return (data.features as Array<{ attributes?: Record<string, unknown> }>).map((f) => f.attributes ?? {});
}

/** GeoJSON features (properties + geometry) from an f=geojson query; throws like arcgisAttributes. */
export async function arcgisGeojson(
  fetchFn: FetchFn,
  url: string,
  body: URLSearchParams
): Promise<Array<{ properties: Record<string, unknown>; geometry: unknown }>> {
  const data = await post(fetchFn, url, body);
  const feats = data.features as Array<{ properties?: Record<string, unknown>; geometry?: unknown }>;
  // A feature with no shape cannot be tested, so the answer is unknown (the page says so), never "no road".
  if (feats.some((f) => !f.geometry)) throw new Error('map service returned a feature with no geometry');
  return feats.map((f) => ({ properties: f.properties ?? {}, geometry: f.geometry }));
}
