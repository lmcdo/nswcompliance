/**
 * Does this lot front a State road or a classified road?
 *
 * prior-art-checked: reuses lib/lot-adjacency.ts (the lot lookup and fail-closed map calls of lib/rail-busy-road.ts,
 * Ku-ring-gai Part 20). Part 20 matches named roads for one council; this check reads the road CLASS from Transport
 * for NSW for any lot, so it is its own module.
 *
 * DCP rows such as "sites adjoining a classified road" (Ashfield F p63) or "not permitted to front state roads"
 * (Canterbury-Bankstown 10.7 p13) apply only to lots on those roads (gate rules: scripts/gate_rules_roads.py).
 * TfNSW publishes the State and Regional roads as CENTRELINES. A lot is flagged when it is within the tolerance of a
 * cadastre road corridor that a State or Regional centreline runs inside, never by its distance to the centreline.
 * Layers, tolerance, the unclassified-regional numbering assumption and the measurements: shared/classified-roads.json.
 *
 * Fail closed: no lot, or a map service that does not answer, gives a plain-words "couldn't check" note and no
 * flag, so those rules are not shown and the page says why.
 */
import cfg from '@/shared/classified-roads.json';
import {
  LotNotFound,
  arcgisGeojson,
  distanceQuery,
  lotForPoint,
  type FetchFn,
  type QueryFn,
} from '@/lib/lot-adjacency';

export type { FetchFn, QueryFn } from '@/lib/lot-adjacency';

export type RoadClass = 'state' | 'classified_regional' | 'unclassified_regional';

export interface AdjoiningRoad {
  roadNumber: string;
  roadName: string | null;
  roadClass: RoadClass;
}

export interface ClassifiedRoadConstraint {
  /** The lot touches a corridor carrying a TfNSW State road (condition 'state_road'). */
  state: boolean;
  /** ... a State road or a classified Regional road (condition 'classified_road'). */
  classified: boolean;
  /** ... an unclassified Regional road (no gated row uses this yet; recorded for rows that say "regional road"). */
  unclassifiedRegional: boolean;
  roads: AdjoiningRoad[];
}

export const TOLERANCE_M: number = cfg.tolerance_m;
export const CENTRELINE_SEARCH_M: number = cfg.centreline_search_m;
export const MIN_INSIDE_M: number = cfg.min_inside_m;
export const CORRIDOR_URL = `${cfg.road_corridor_layer}/query`;
export const STATE_URL = `${cfg.road_class_source.service}/${cfg.road_class_source.state_layer}/query`;
export const REGIONAL_URL = `${cfg.road_class_source.service}/${cfg.road_class_source.regional_layer}/query`;

const UNCLASSIFIED = cfg.unclassified_regional_number_range;

/** TfNSW admin class + road number -> class. Unknown admin class -> null (not counted). */
export function roadClass(adminClass: unknown, roadNumber: unknown): RoadClass | null {
  if (adminClass === 'S') return 'state';
  if (adminClass !== 'R') return null;
  const s = String(roadNumber ?? '');
  // Standard numbers are 7 digits ('0007421'). A non-standard one is treated as classified (shown, not hidden).
  if (!/^\d{7}$/.test(s)) return 'classified_regional';
  const n = Number(s);
  return n >= UNCLASSIFIED.from && n <= UNCLASSIFIED.to ? 'unclassified_regional' : 'classified_regional';
}

/** Which centrelines run at least MIN_INSIDE_M inside any of the corridors. $1 corridors, $2 lines (GeoJSON arrays). */
export const INSIDE_CORRIDOR_SQL = `
  WITH c AS (
    SELECT ST_SetSRID(ST_GeomFromGeoJSON(e::text), 4326) AS g FROM json_array_elements($1::json) e
  ), l AS (
    SELECT (e->>'i')::int AS i, ST_SetSRID(ST_GeomFromGeoJSON((e->'g')::text), 4326) AS g FROM json_array_elements($2::json) e
  )
  SELECT DISTINCT l.i
  FROM l JOIN c ON ST_Intersects(l.g, c.g)
  WHERE ST_Length(ST_Intersection(l.g, c.g)::geography) >= $3
`;

/** The constraint, or null when the lot touches no corridor carrying a State or Regional road.
 *  Throws when the lot is not found or a map service fails. */
export async function classifiedRoadForPoint(
  query: QueryFn,
  fetchFn: FetchFn,
  lon: number,
  lat: number
): Promise<ClassifiedRoadConstraint | null> {
  const { rings } = await lotForPoint(query, lon, lat);
  const lineFields = 'road_number,road_name,admin_class';
  const [corridors, stateLines, regionalLines] = await Promise.all([
    arcgisGeojson(fetchFn, CORRIDOR_URL, distanceQuery(rings, '1=1', 'roadnamelabel', TOLERANCE_M, 'geojson')),
    arcgisGeojson(fetchFn, STATE_URL, distanceQuery(rings, '1=1', lineFields, CENTRELINE_SEARCH_M, 'geojson')),
    arcgisGeojson(fetchFn, REGIONAL_URL, distanceQuery(rings, '1=1', lineFields, CENTRELINE_SEARCH_M, 'geojson')),
  ]);
  const lines = [...stateLines, ...regionalLines]
    .map((f) => ({ f, cls: roadClass(f.properties.admin_class, f.properties.road_number) }))
    .filter((x): x is { f: (typeof stateLines)[number]; cls: RoadClass } => x.cls !== null);
  if (corridors.length === 0 || lines.length === 0) return null;

  const inside = await query(INSIDE_CORRIDOR_SQL, [
    JSON.stringify(corridors.map((c) => c.geometry)),
    JSON.stringify(lines.map((x, i) => ({ i, g: x.f.geometry }))),
    MIN_INSIDE_M,
  ]);
  const hit = new Set(inside.rows.map((r) => Number(r.i)));
  const byNumber = new Map<string, AdjoiningRoad>();
  lines.forEach((x, i) => {
    if (!hit.has(i)) return;
    const roadNumber = String(x.f.properties.road_number ?? '');
    if (!byNumber.has(roadNumber)) {
      const name = x.f.properties.road_name;
      byNumber.set(roadNumber, { roadNumber, roadName: typeof name === 'string' ? name : null, roadClass: x.cls });
    }
  });
  if (byNumber.size === 0) return null;
  const roads = [...byNumber.values()].sort((a, b) => a.roadNumber.localeCompare(b.roadNumber));
  const onState = roads.some((r) => r.roadClass === 'state');
  return {
    state: onState,
    classified: onState || roads.some((r) => r.roadClass === 'classified_regional'),
    unclassifiedRegional: roads.some((r) => r.roadClass === 'unclassified_regional'),
    roads,
  };
}

/** What the property lookup records: the flag, or a plain-words note when the check could not run
 *  (without the flag the rules for lots on State or classified roads are not shown, so the page must say why). */
export async function classifiedRoadConstraints(
  query: QueryFn,
  fetchFn: FetchFn,
  lon: number,
  lat: number
): Promise<{ classifiedRoad?: ClassifiedRoadConstraint; classifiedRoadUnchecked?: string }> {
  try {
    const classifiedRoad = await classifiedRoadForPoint(query, fetchFn, lon, lat);
    return classifiedRoad ? { classifiedRoad } : {};
  } catch (err) {
    if (err instanceof LotNotFound) {
      return {
        classifiedRoadUnchecked:
          "We couldn't find this property's lot on the NSW lot map, so we couldn't check whether it fronts a State or classified road; council rules for lots on those roads may be missing.",
      };
    }
    console.warn('[classified-road] frontage check failed:', err);
    return {
      classifiedRoadUnchecked:
        "We couldn't check whether this lot fronts a State or classified road (the map service did not answer), so council rules for lots on those roads may be missing.",
    };
  }
}
