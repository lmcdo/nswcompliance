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
import {
  LOT_SQL,
  LotNotFound,
  arcgisAttributes,
  distanceQuery as lotDistanceQuery,
  lotForPoint,
  type FetchFn,
  type QueryFn,
} from '@/lib/lot-adjacency';

export { toEsriRings } from '@/lib/lot-adjacency';
export type { FetchFn } from '@/lib/lot-adjacency';

export interface RailOrBusyRoadConstraint {
  adjoins: true;
  /** DCP names of the busy roads the lot adjoins, e.g. "Pacific Highway". */
  roads: string[];
  rail: boolean;
}

/** The lot polygons holding the address point, merged, as GeoJSON (shared with lib/classified-road.ts). */
export const RAIL_ROAD_LOT_SQL = LOT_SQL;

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

const distanceQuery = (rings: number[][][], where: string, outFields: string) =>
  lotDistanceQuery(rings, where, outFields, TOLERANCE_M);

/** Raised when no cadastre lot holds the address point (the shared lib/lot-adjacency.ts error). */
export const RailRoadLotNotFound = LotNotFound;

/**
 * The constraint, or null when the lot adjoins neither. Throws when the lot is not found or a map service fails.
 */
export async function railOrBusyRoadForPoint(
  query: QueryFn,
  fetchFn: FetchFn,
  lon: number,
  lat: number
): Promise<RailOrBusyRoadConstraint | null> {
  const { rings } = await lotForPoint(query, lon, lat);

  const [roadHits, railHits] = await Promise.all([
    arcgisAttributes(fetchFn, ROAD_URL, distanceQuery(rings, ROAD_WHERE, 'roadnamelabel')),
    arcgisAttributes(fetchFn, RAIL_URL, distanceQuery(rings, RAIL_WHERE, 'PURPOSE')),
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
    if (err instanceof LotNotFound) {
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
