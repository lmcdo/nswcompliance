/**
 * Is this lot on the council's published Flood Planning Map (NSW Planning Portal, ePlanning
 * Hazard layer 230)?
 *
 * Before 2026-10-19 the assessment page set floodProne = false for EVERY property, so DA intake
 * pre-answered "flood prone: no" and the summary said "Flood: No". Only some councils publish a
 * flood planning map to this layer (10 on 2026-10-19: Hornsby, Wollongong, Wingecarribee and
 * seven regional councils), so "no polygon here" means "not flood mapped" ONLY for those
 * councils; for every other council it means we cannot tell from the map.
 *
 * 2026-10-20 (Sol cross-review of #1383): the first version tested ONE point, so a lot whose back
 * half is in the flood planning area could read "No". "No" is now given only when the WHOLE lot
 * boundary was tested; a point-only test can say "Yes" but never "No". Every unknown carries its
 * own reason, and the page shows that sentence rather than a fixed "no published map".
 *
 * prior-art-checked: EPLANNING_LAYERS.floodPlanningMap was registered in nsw-planning-portal.ts
 * but never queried; services/flood_truth.py queries a different SEED layer for the paid flood
 * report. This queries the registered layer (same service and id as
 * EPLANNING_LAYERS.floodPlanningMap; not imported, to keep nsw-planning-portal free of a cycle).
 */
import { fetchWithTimeout } from '../fetch-timeout';

const LAYER_URL =
  'https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning/Planning_Portal_Hazard/MapServer/230/query';

export interface FloodMapStatus {
  /** true = on the map; false = the WHOLE lot was tested and its plan publishes a map; null = cannot tell. */
  floodProne: boolean | null;
  /** The plain-words sentence the page shows, including why when it cannot tell. */
  note: string;
}

/** What the map query found: how many flood polygons touch the lot, and whether the whole lot was tested. */
export interface FloodHit {
  features: number | null;
  wholeLot: boolean;
}

let publishingPlans: Promise<Set<string> | null> | null = null;

/** Names of the plans (EPI_NAME) that publish a flood planning map to the layer. Cached per server instance. */
function plansWithAFloodMap(): Promise<Set<string> | null> {
  if (!publishingPlans) {
    publishingPlans = fetchWithTimeout(`${LAYER_URL}?where=1%3D1&outFields=EPI_NAME&returnDistinctValues=true&returnGeometry=false&f=json`)
      .then((r) => r.json())
      .then((d) => (!d.error && Array.isArray(d.features)
        ? new Set<string>(d.features.map((f: any) => String(f?.attributes?.EPI_NAME ?? '')).filter(Boolean))
        : null))
      .catch(() => null)
      .then((s) => {
        if (s == null) publishingPlans = null; // do not cache a failure
        return s;
      });
  }
  return publishingPlans;
}

const ON_MAP = "This lot is in a flood planning area on the council's flood planning map.";
const NOT_ON_MAP = "No part of this lot is in a flood planning area on the council's flood planning map.";
const UNREACHABLE = "We couldn't reach the NSW flood planning map, so we can't tell yet whether this lot is in a flood planning area.";
const PLANS_UNKNOWN = "We couldn't check whether this council publishes a flood planning map, so we can't tell from the map whether this lot is flood affected.";
const LOT_PLAN_UNKNOWN = "We couldn't tell which local environmental plan covers this lot, so we can't tell from the flood planning map whether it is flood affected.";
const NO_PUBLISHED_MAP = "We found no flood planning map on the NSW Planning Portal for this lot's local environmental plan, so we can't tell from the map whether this lot is flood affected. Check the council's flood studies.";
const POINT_ONLY = "The point the NSW Planning Portal gives for this address is not in a flood planning area, but the whole lot could not be checked, so part of it may be.";

/** Pure decision, kept separate so it can be tested without the network. */
export function decideFloodMap(hit: FloodHit, lotPlans: string[], plansWithMap: Set<string> | null): FloodMapStatus {
  if (hit.features == null) return { floodProne: null, note: UNREACHABLE };
  // A flood polygon touching the lot is a "Yes" whichever way it was found.
  if (hit.features > 0) return { floodProne: true, note: ON_MAP };
  if (plansWithMap == null) return { floodProne: null, note: PLANS_UNKNOWN };
  if (lotPlans.length === 0) return { floodProne: null, note: LOT_PLAN_UNKNOWN };
  if (!lotPlans.some((p) => plansWithMap.has(p))) return { floodProne: null, note: NO_PUBLISHED_MAP };
  // The plan publishes a map and nothing touches what was tested: "No" only for the whole lot.
  return hit.wholeLot ? { floodProne: false, note: NOT_ON_MAP } : { floodProne: null, note: POINT_ONLY };
}

function countFrom(d: any): number | null {
  return !d?.error && Array.isArray(d?.features) ? d.features.length : null;
}

/** The lot boundary as the Portal returns it (rings plus the coordinate system they are in). */
export interface LotBoundary {
  rings?: unknown;
  spatialReference?: { wkid?: number | null; latestWkid?: number | null } | null;
}

/** Rings that are well formed (closed lists of [x, y] numbers), else null. */
function validRings(rings: unknown): number[][][] | null {
  if (!Array.isArray(rings) || rings.length === 0) return null;
  const ok = rings.every((ring) => Array.isArray(ring) && ring.length >= 4
    && ring.every((p) => Array.isArray(p) && p.length >= 2 && Number.isFinite(p[0]) && Number.isFinite(p[1])));
  return ok ? (rings as number[][][]) : null;
}

/** Is the address point inside the boundary, in the boundary's own coordinate system? A mislabelled,
 *  stale or neighbouring boundary fails this and only the point is tested (Sol, 2026-10-20). Only the
 *  systems the Portal uses are understood; anything else is not trusted for a "No". */
export function boundaryMatchesPoint(rings: number[][][], wkid: number, lon: number, lat: number): boolean {
  let px: number;
  let py: number;
  if (wkid === 3857 || wkid === 102100) {
    px = (lon * 20037508.34) / 180;
    py = (Math.log(Math.tan(((90 + lat) * Math.PI) / 360)) / (Math.PI / 180)) * (20037508.34 / 180);
  } else if (wkid === 4326 || wkid === 4283 || wkid === 7844) {
    px = lon;
    py = lat;
  } else {
    return false;
  }
  // The address point must lie INSIDE the boundary (even-odd rule over all rings): a neighbour's or a
  // stale boundary then fails and only the point is tested, which can never answer "No" (Sol, 2026-10-20).
  let inside = false;
  for (const ring of rings) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i];
      const [xj, yj] = ring[j];
      if ((yi > py) !== (yj > py) && px < ((xj - xi) * (py - yi)) / (yj - yi) + xi) inside = !inside;
    }
  }
  return inside;
}

/** Flood polygons touching the lot. The address point is ALWAYS tested; the boundary too when it is
 *  trusted (stated coordinate system, near the point). Yes if either touches a flood polygon; the
 *  whole lot counts as tested only when both queries answered, so a stale boundary can never hide a
 *  flooded address point (Sol, 2026-10-20). */
async function queryLot(lon: number, lat: number, boundary: LotBoundary | null | undefined): Promise<FloodHit> {
  const point = fetchWithTimeout(`${LAYER_URL}?geometry=${lon},${lat}&geometryType=esriGeometryPoint&spatialRel=esriSpatialRelIntersects&outFields=LAY_CLASS&returnGeometry=false&f=json&inSR=4283`)
    .then((r) => r.json())
    .then(countFrom)
    .catch(() => null);
  const rings = validRings(boundary?.rings);
  const wkid = boundary?.spatialReference?.latestWkid ?? boundary?.spatialReference?.wkid ?? null;
  const lot = rings && wkid && boundaryMatchesPoint(rings, wkid, lon, lat)
    ? fetchWithTimeout(LAYER_URL, {
      method: 'POST',
      body: new URLSearchParams({
        geometry: JSON.stringify({ rings, spatialReference: { wkid } }),
        geometryType: 'esriGeometryPolygon',
        inSR: String(wkid),
        spatialRel: 'esriSpatialRelIntersects',
        outFields: 'LAY_CLASS',
        returnGeometry: 'false',
        f: 'json',
      }),
    }).then((r) => r.json()).then(countFrom).catch(() => null)
    : Promise.resolve(null);
  const [p, l] = await Promise.all([point, lot]);
  if ((p ?? 0) > 0 || (l ?? 0) > 0) return { features: (p ?? 0) + (l ?? 0), wholeLot: l != null };
  // Nothing touched: a "No" needs every query that was asked to have answered.
  if (p == null) return { features: null, wholeLot: false };
  return { features: 0, wholeLot: l != null };
}

export async function floodMapStatus(
  lon: number,
  lat: number,
  lotPlans: string[],
  boundary?: LotBoundary | null,
): Promise<FloodMapStatus> {
  const [hit, plansWithMap] = await Promise.all([queryLot(lon, lat, boundary), plansWithAFloodMap()]);
  return decideFloodMap(hit, lotPlans, plansWithMap);
}
