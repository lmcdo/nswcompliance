// prior-art-checked: 2026-11-21. No map or route component in frontend-nextjs draws a walking route (grep for svg, leaflet, maplibre, mapbox in components/ and app/:
// ShadowMap, AerialTile and ThreatRadarTool draw other things). The Desktop outreach tool lead-finder/outreach/route_map_lib.py projects with UTM on the server;
// a local flat projection is exact to well under a metre over the ~2 km a walk covers, so no projection library is needed in the browser.
import type { LatLon, RouteLine, RouteMap } from '@/lib/evidence-statement';

const M_PER_DEG_LAT = 110540;
const M_PER_DEG_LON_AT_EQUATOR = 111320;
const SCALE_BAR_CHOICES_M = [20, 50, 100, 200, 500, 1000];
const MAX_BUSY_POINTS = 600;   // as many as a picture can usefully show

export interface XY { x: number; y: number }
export interface DrawnLine { points: string; start: XY; end: XY }
export interface ProjectedRouteMap {
  size: number;
  careful: DrawnLine | null;
  normal: DrawnLine | null;
  busy: XY[];
  lot: XY;
  destination: XY;
  scaleBar: { px: number; m: number };
}

/** Project the routes in a route map onto a square picture, north up, fitting both routes plus `padM` metres all round.
 *  Returns null when there is nothing to draw. Pure: the same input always gives the same picture. */
export function projectRouteMap(rm: RouteMap, size = 820, padM = 150): ProjectedRouteMap | null {
  const lines = [rm.careful, rm.normal].filter((l): l is RouteLine => !!l && l.points.length >= 2);
  if (lines.length === 0) return null;
  const all: LatLon[] = lines.flatMap((l) => l.points);
  const lat0 = all.reduce((s, p) => s + p[0], 0) / all.length;
  const lon0 = all.reduce((s, p) => s + p[1], 0) / all.length;
  const mLon = Math.cos((lat0 * Math.PI) / 180) * M_PER_DEG_LON_AT_EQUATOR;
  const toM = (p: LatLon): XY => ({ x: (p[1] - lon0) * mLon, y: (p[0] - lat0) * M_PER_DEG_LAT });
  const ms = all.map(toM);
  const minX = Math.min(...ms.map((m) => m.x)) - padM, maxX = Math.max(...ms.map((m) => m.x)) + padM;
  const minY = Math.min(...ms.map((m) => m.y)) - padM, maxY = Math.max(...ms.map((m) => m.y)) + padM;
  const span = Math.max(maxX - minX, maxY - minY);   // padM > 0 keeps this above zero even for a one-point-wide route
  const k = size / span;
  const ox = (size - (maxX - minX) * k) / 2, oy = (size - (maxY - minY) * k) / 2;
  const proj = (p: LatLon): XY => { const m = toM(p); return { x: ox + (m.x - minX) * k, y: oy + (maxY - m.y) * k }; };   // north is up
  const fmt = (n: number) => n.toFixed(1);
  const draw = (l: RouteLine | null | undefined): DrawnLine | null => {
    if (!l || l.points.length < 2) return null;
    const xy = l.points.map(proj);
    return { points: xy.map((q) => `${fmt(q.x)},${fmt(q.y)}`).join(' '), start: xy[0], end: xy[xy.length - 1] };
  };
  // busy-road points: de-duplicated to the pixel, only those on the picture, and no more than a picture can usefully show
  const seen = new Set<string>();
  const busy: XY[] = [];
  for (const p of lines.flatMap((l) => l.busy_road_points)) {
    if (busy.length >= MAX_BUSY_POINTS) break;   // one loop over both routes' points, so the cap is a cap
    const q = proj(p);
    const key = `${Math.round(q.x)},${Math.round(q.y)}`;
    if (q.x < 0 || q.y < 0 || q.x > size || q.y > size || seen.has(key)) continue;
    seen.add(key);
    busy.push(q);
  }
  const careful = draw(rm.careful), normal = draw(rm.normal);
  const first = careful ?? normal;
  if (!first) return null;
  const metresPerPx = 1 / k;
  const bar = [...SCALE_BAR_CHOICES_M].reverse().find((m) => m / metresPerPx <= size * 0.3) ?? SCALE_BAR_CHOICES_M[0];
  return { size, careful, normal, busy, lot: first.start, destination: first.end, scaleBar: { px: bar / metresPerPx, m: bar } };
}

/** A plain-words label for what a walk ends at. */
export function destinationLabel(d: { name: string | null; kind: string } | undefined | null): string {
  const name = d?.name ?? 'the destination';
  if (d?.kind === 'town_centre_edge') return `the edge of ${name}`;
  if (d?.kind === 'station_outline') return `${name} (the station outline: its entrance is not mapped)`;
  return `${name} (station entrance)`;
}
