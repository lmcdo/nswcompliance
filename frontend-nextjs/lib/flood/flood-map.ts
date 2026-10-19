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
 * prior-art-checked: EPLANNING_LAYERS.floodPlanningMap was registered in nsw-planning-portal.ts
 * but never queried; services/flood_truth.py queries a different SEED layer for the paid flood
 * report. This queries the registered layer (same service and id as
 * EPLANNING_LAYERS.floodPlanningMap; not imported, to keep nsw-planning-portal free of a cycle).
 */
const LAYER_URL =
  'https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning/Planning_Portal_Hazard/MapServer/230/query';

export interface FloodMapStatus {
  /** true = on the map; false = the lot's plan publishes a map and the lot is not on it; null = cannot tell. */
  floodProne: boolean | null;
  /** The plain-words sentence the page shows. */
  note: string;
}

let publishingPlans: Promise<Set<string> | null> | null = null;

/** Names of the plans (EPI_NAME) that publish a flood planning map to the layer. Cached per server instance. */
function plansWithAFloodMap(): Promise<Set<string> | null> {
  if (!publishingPlans) {
    publishingPlans = fetch(`${LAYER_URL}?where=1%3D1&outFields=EPI_NAME&returnDistinctValues=true&returnGeometry=false&f=json`)
      .then((r) => r.json())
      .then((d) => (!d.error && Array.isArray(d.features)
        ? new Set<string>(d.features.map((f: any) => String(f?.attributes?.EPI_NAME ?? '')).filter(Boolean))
        : null))
      .catch(() => null)
      .then((s) => {
        if (s === null) publishingPlans = null; // do not cache a failure
        return s;
      });
  }
  return publishingPlans;
}

/** Pure decision, kept separate so it can be tested without the network. */
export function decideFloodMap(
  pointFeatures: number | null,
  lotPlans: string[],
  plansWithMap: Set<string> | null,
): FloodMapStatus {
  if (pointFeatures === null) {
    return { floodProne: null, note: "We couldn't reach the NSW flood planning map, so we can't tell yet whether this lot is in a flood planning area." };
  }
  if (pointFeatures > 0) {
    return { floodProne: true, note: "This lot is in a flood planning area on the council's flood planning map." };
  }
  if (plansWithMap === null) {
    return { floodProne: null, note: "We couldn't check whether this council publishes a flood planning map, so we can't tell from the map whether this lot is flood affected." };
  }
  if (lotPlans.some((p) => plansWithMap.has(p))) {
    return { floodProne: false, note: "This lot is not in a flood planning area on the council's flood planning map." };
  }
  return { floodProne: null, note: "This council has not published a flood planning map to the NSW Planning Portal, so we can't tell from the map whether this lot is flood affected. Check the council's flood studies." };
}

export async function floodMapStatus(lon: number, lat: number, lotPlans: string[]): Promise<FloodMapStatus> {
  const [pointFeatures, plansWithMap] = await Promise.all([
    fetch(`${LAYER_URL}?geometry=${lon},${lat}&geometryType=esriGeometryPoint&spatialRel=esriSpatialRelIntersects&outFields=LAY_CLASS&returnGeometry=false&f=json&inSR=4283`)
      .then((r) => r.json())
      .then((d) => (!d.error && Array.isArray(d.features) ? d.features.length : null))
      .catch(() => null),
    plansWithAFloodMap(),
  ]);
  return decideFloodMap(pointFeatures, lotPlans, plansWithMap);
}
