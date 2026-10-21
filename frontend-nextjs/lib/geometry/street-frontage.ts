/**
 * Street frontage and lot width measured from the road, not guessed from the lot's shape.
 *
 * prior-art-checked: reuse not viable because nothing in the repo knows which edge of a lot faces the road.
 * lot-dimensions.ts takes the shorter side of the minimum-area rectangle (#1342, after services/lot_dimensions.py
 * #499, whose own note says "The accurate frontage is the road-facing edge ... a planned follow-up"); that side
 * overstates the street edge on a wedge lot (6 Berrigan St Winston Hills: rectangle 22.4 m, street edge 13.3 m).
 * corner-lot-detection.ts queries the same road layer but keeps only road names. effective-lot-width.ts picks among
 * width candidates, three of which have no producer anywhere in the repo.
 *
 * WHAT IS MEASURED. The Housing SEPP minimums are "a minimum lot width at the front building line" (e.g. cl
 * 168(2)(b), quoted in housing_sepp_standards.source_quote). Where the front building line sits depends on the
 * design, so no single width can be read off the cadastre. Instead, for each named road the lot touches, this
 * measures the lot's width at every distance back from that road edge (the length of the line at that distance,
 * inside the lot). Two numbers carry the answer:
 *   minFrontHalf_m  narrowest width from the road edge to halfway back. If even this meets a minimum, the lot
 *                   meets it wherever in the front half the building line falls.
 *   maxAll_m        widest width anywhere. If even this is below a minimum, no building line can meet it.
 * Anything between is "depends on where the building sits" -- stated, never resolved by guessing.
 *
 * WHICH EDGES ARE THE ROAD. NSW cadastre lot and road-corridor polygons are not always coincident: measured gaps
 * of 1.2-1.5 m at 18 Wyreema Ave Padstow, 39A Neirbo Ave Hurstville and 390 Caddens Rd Claremont Meadows (a
 * "touches" query returns no road for them). A lot edge counts as road frontage when at least half of it lies
 * within EDGE_TOLERANCE_M of a road-corridor boundary running within EDGE_MAX_ANGLE_DEG of parallel; the parallel
 * test keeps a side boundary that merely meets the road at a corner out. Measured 2026-10-18 on 14 real lots:
 * Winston Hills 13.34 m (identical at tolerances 0.5-2.0 m), Padstow 15.27, Haberfield 14.44, Mortdale 6.19.
 * Unnamed road parcels (rear lanes, e.g. Haberfield) are counted separately and never treated as the front.
 *
 * Pure: no network. lib/geometry/road-corridors.ts fetches the road shapes.
 */

import { scaleFactorForRing, usableRing } from './mercator';

export const EDGE_TOLERANCE_M = 2.5;
export const EDGE_MAX_ANGLE_DEG = 30;
export const EDGE_MIN_FRACTION = 0.5;
/** A stretch of a road edge with no road beside it is cut from the frontage only when longer than this; shorter
 *  gaps are the road boundary curving away at a corner, not a break in the frontage (Haberfield, Logan Ave). */
export const FRONTAGE_GAP_M = 3.0;
/** Width readings are this far apart, measured back from the road edge. */
export const PROFILE_STEP_M = 0.5;
/**
 * Grid spacing for the width profile; coarser on large lots so the cost stays bounded. Each MUST divide
 * PROFILE_STEP_M exactly: at 0.2 m a step held 2 or 3 grid rows on a square-on lot, and a uniform 15 m
 * rectangle read 12-18 m (caught by the synthetic-rectangle test, 2026-10-18).
 */
const GRID_M = 0.1;
const GRID_LARGE_M = 0.25;
const LARGE_LOT_M2 = 2000;
/** Grid-counting noise is a few tenths of a metre; a verdict needs at least this clearance. */
export const WIDTH_MARGIN_M = 0.3;

type Pt = [number, number];
type Seg = [Pt, Pt];

export interface RoadShape {
  /** Road name from the road-corridor layer; null for an unnamed parcel (lanes, splays). */
  name: string | null;
  /** Polygon rings in the SAME coordinate system as the lot ring (EPSG:3857). */
  rings: number[][][];
}

export interface RoadWidthRange {
  road: string;
  /** Length of lot boundary along this road, in metres. */
  frontage_m: number;
  /** Narrowest lot width from this road edge to halfway back, in metres. */
  minFrontHalf_m: number;
  /** Widest lot width at any distance from this road edge, in metres. */
  maxAll_m: number;
  /** Furthest point of the lot from this road edge, in metres. */
  depth_m: number;
}

export interface StreetFrontage {
  /** measured: at least one named road edge found. not_identified: road data answered, no named road edge. */
  status: 'measured' | 'not_identified' | 'unavailable';
  roads: RoadWidthRange[];
  /** Lot boundary along unnamed road parcels (rear lanes etc.), in metres. Never treated as the front. */
  /** null when the frontage could not be measured (unavailable). */
  unnamedRoadEdge_m: number | null;
  error?: string;
}

export type WidthVerdict = 'meets' | 'below' | 'depends';

function segDist(p: Pt, a: Pt, b: Pt): number {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const len2 = dx * dx + dy * dy;
  const t = len2 === 0 ? 0 : Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / len2));
  return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy);
}

function angleBetween(a: Seg, b: Seg): number {
  const t1 = Math.atan2(a[1][1] - a[0][1], a[1][0] - a[0][0]);
  const t2 = Math.atan2(b[1][1] - b[0][1], b[1][0] - b[0][0]);
  const d = Math.abs((t1 - t2) * 180 / Math.PI) % 180;
  return Math.min(d, 180 - d);
}

function inside(p: Pt, ring: Pt[]): boolean {
  let c = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i];
    const [xj, yj] = ring[j];
    if ((yi > p[1]) !== (yj > p[1]) && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) c = !c;
  }
  return c;
}

function segmentsOf(ring: Pt[]): Seg[] {
  const out: Seg[] = [];
  for (let i = 0; i + 1 < ring.length; i++) out.push([ring[i], ring[i + 1]]);
  return out;
}

/** True when at least EDGE_MIN_FRACTION of the lot edge runs alongside one of the road segments. */
/** Share of the edge that is frontage: beside a road. A gap up to FRONTAGE_GAP_M at either END of the edge still
 *  counts (the road boundary curving away at a corner); a gap in the middle never does (Sol, 2026-10-20). */
function edgeFrontageShare(edge: Seg, road: Seg[]): number {
  const hits = edgeRoadHits(edge, road);
  const first = hits.indexOf(true);
  if (first < 0) return 0;
  const last = hits.lastIndexOf(true);
  const step = Math.hypot(edge[1][0] - edge[0][0], edge[1][1] - edge[0][1]) / hits.length;
  let counted = hits.filter(Boolean).length;
  for (const run of [first, hits.length - 1 - last]) if (run * step <= FRONTAGE_GAP_M) counted += run;
  return counted / hits.length;
}

/** For points along the edge (at least 40, at most 0.25 m apart), whether each runs alongside a road segment. */
function edgeRoadHits(edge: Seg, road: Seg[]): boolean[] {
  const n = Math.max(40, Math.ceil(Math.hypot(edge[1][0] - edge[0][0], edge[1][1] - edge[0][1]) / 0.25));
  const hits: boolean[] = [];
  for (let i = 0; i < n; i++) {
    const t = (i + 0.5) / n;
    const p: Pt = [edge[0][0] + (edge[1][0] - edge[0][0]) * t, edge[0][1] + (edge[1][1] - edge[0][1]) * t];
    let best: Seg | null = null;
    let bestD = Infinity;
    for (const s of road) {
      const d = segDist(p, s[0], s[1]);
      if (d < bestD) { bestD = d; best = s; }
    }
    hits.push(!!best && bestD < EDGE_TOLERANCE_M && angleBetween(edge, best) <= EDGE_MAX_ANGLE_DEG);
  }
  return hits;
}

/**
 * Lot width at each distance from the given road edges: the area of the lot between d and d + step from the road,
 * divided by step (the length of the line at distance d, by the coarea formula). Counted on a grid.
 */
export function widthProfile(ring: Pt[], roadEdges: Seg[], areaM2: number): { d: number; width: number }[] {
  const grid = areaM2 > LARGE_LOT_M2 ? GRID_LARGE_M : GRID_M;
  const xs = ring.map((p) => p[0]);
  const ys = ring.map((p) => p[1]);
  const counts = new Map<number, number>();
  for (let x = Math.min(...xs) + grid / 2; x < Math.max(...xs); x += grid) {
    for (let y = Math.min(...ys) + grid / 2; y < Math.max(...ys); y += grid) {
      if (!inside([x, y], ring)) continue;
      let d = Infinity;
      for (const s of roadEdges) d = Math.min(d, segDist([x, y], s[0], s[1]));
      const bin = Math.floor(d / PROFILE_STEP_M);
      counts.set(bin, (counts.get(bin) ?? 0) + 1);
    }
  }
  return [...counts.keys()].sort((a, b) => a - b)
    .map((bin) => ({ d: bin * PROFILE_STEP_M, width: ((counts.get(bin) ?? 0) * grid * grid) / PROFILE_STEP_M }));
}

function round2(v: number): number {
  return Math.round(v * 100) / 100;
}

/**
 * Street frontage per named road and the lot's width range back from each.
 * @param lotRing  outer ring of the lot, EPSG:3857
 * @param roads    road-corridor polygons near the lot, EPSG:3857
 */
export function measureStreetFrontage(lotRing: unknown, roads: RoadShape[]): StreetFrontage {
  const raw = usableRing(lotRing);
  if (!raw || raw.length < 4) return { status: 'unavailable', roads: [], unnamedRoadEdge_m: null, error: 'unusable lot ring' };
  const scale = scaleFactorForRing(raw);
  const toM = (p: number[]): Pt => [p[0] / scale, p[1] / scale];
  const ring = raw.map(toM);
  const lotEdges = segmentsOf(ring);
  let area = 0;
  for (const [a, b] of lotEdges) area += a[0] * b[1] - b[0] * a[1];
  area = Math.abs(area) / 2;

  // A Set: one road can arrive as several parcels with the same name (Nicholls Ave, Haberfield).
  // An edge belongs to a road when most of it runs beside that road. Its frontage is the share of it beside THAT road
  // (all its parcels together): an edge half beside the road is half frontage, and another road never fills the gap
  // (Sol on #1347). Short gaps, e.g. the road boundary curving away at a corner, still count (FRONTAGE_GAP_M).
  const byRoad = new Map<string, Set<Seg>>();
  const segsByRoad = new Map<string, Seg[]>();
  let unnamed = 0;
  for (const road of roads) {
    const roadSegs = (road.rings || []).flatMap((r) => {
      const ok = usableRing(r);
      return ok ? segmentsOf(ok.map(toM)) : [];
    });
    if (!roadSegs.length) continue;
    const name = road.name?.trim() || null;
    if (name) {
      segsByRoad.set(name, [...(segsByRoad.get(name) ?? []), ...roadSegs]);
      continue;
    }
    for (const edge of lotEdges) {
      if (edgeFrontageShare(edge, roadSegs) < EDGE_MIN_FRACTION) continue;
      unnamed += Math.hypot(edge[1][0] - edge[0][0], edge[1][1] - edge[0][1]) * edgeFrontageShare(edge, roadSegs);
    }
  }
  // Ownership is judged against all parcels of a named road together, so a road split into parcels along one edge
  // still owns it (Sol, 2026-10-20).
  for (const [name, segs] of segsByRoad) {
    for (const edge of lotEdges) {
      if (edgeFrontageShare(edge, segs) < EDGE_MIN_FRACTION) continue;
      const set = byRoad.get(name) ?? new Set<Seg>();
      set.add(edge);
      byRoad.set(name, set);
    }
  }

  const out: RoadWidthRange[] = [];
  for (const [road, edgeSet] of [...byRoad.entries()].sort(([a], [b]) => a.localeCompare(b))) {
    const edges = [...edgeSet];
    const prof = widthProfile(ring, edges, area);
    if (!prof.length) continue;
    const depth = prof[prof.length - 1].d + PROFILE_STEP_M;
    const front = prof.filter((p) => p.d < depth / 2);
    out.push({
      road,
      frontage_m: round2(edges.reduce((s, e) => s + Math.hypot(e[1][0] - e[0][0], e[1][1] - e[0][1]) * edgeFrontageShare(e, segsByRoad.get(road) ?? []), 0)),
      minFrontHalf_m: round2(Math.min(...front.map((p) => p.width))),
      maxAll_m: round2(Math.max(...prof.map((p) => p.width))),
      depth_m: round2(depth),
    });
  }
  return { status: out.length ? 'measured' : 'not_identified', roads: out, unnamedRoadEdge_m: round2(unnamed) };
}

/**
 * Whether the lot meets a minimum width at the front building line, wherever that line falls in the front half.
 * A corner lot must give the same answer from every named road, or the answer is 'depends'.
 */
export function widthVerdict(sf: StreetFrontage | null | undefined, requiredM: number): WidthVerdict {
  if (!sf || sf.status !== 'measured' || !sf.roads.length) return 'depends';
  const each = sf.roads.map((r): WidthVerdict => {
    if (r.minFrontHalf_m >= requiredM + WIDTH_MARGIN_M) return 'meets';
    if (r.maxAll_m < requiredM - WIDTH_MARGIN_M) return 'below';
    return 'depends';
  });
  return each.every((v) => v === each[0]) ? each[0] : 'depends';
}

/** The width range to show and to send to the eligibility check: narrowest front-half and widest over all roads. */
export function widthRange(sf: StreetFrontage | null | undefined): { min: number; max: number } | null {
  if (!sf || sf.status !== 'measured' || !sf.roads.length) return null;
  return { min: Math.min(...sf.roads.map((r) => r.minFrontHalf_m)), max: Math.max(...sf.roads.map((r) => r.maxAll_m)) };
}

function titleRoad(name: string): string {
  return name.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * The one wording for a printed street frontage, so every surface says the same thing:
 * "13.3 m along Berrigan St", or "26.3 m along Logan Ave and 46.1 m along Nicholls Ave" on a corner lot.
 * Null when no named road edge was measured: callers print "not measured", never a substitute width.
 */
export function streetFrontageText(sf: StreetFrontage | null | undefined): string | null {
  if (!sf || sf.status !== 'measured' || !sf.roads.length) return null;
  return sf.roads.map((r) => `${r.frontage_m.toFixed(1)} m along ${titleRoad(r.road)}`).join(' and ');
}
