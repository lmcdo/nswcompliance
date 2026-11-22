// prior-art-checked: 2026-11-21. No map or route component in frontend-nextjs draws a walking route (grep for svg, leaflet, maplibre, mapbox in components/ and app/:
// ShadowMap, AerialTile and ThreatRadarTool draw other things). The routes and the basemap tiles are projected here with the same Web Mercator maths the tiles use,
// so a line and the street it follows cannot drift apart. No map library and no new dependency: a tile is an <image> in the same SVG, so it prints as part of the page.
import type { LatLon, RouteLine, RouteMap } from '@/lib/evidence-statement';

const SCALE_BAR_CHOICES_M = [20, 50, 100, 200, 500, 1000];
const MAX_BUSY_POINTS = 600;   // as many as a picture can usefully show
const EARTH_RADIUS_M = 6378137;
const TILE_PX = 256;
const MERCATOR_M_PER_PX_AT_Z0 = (2 * Math.PI * EARTH_RADIUS_M) / TILE_PX;
const MIN_ZOOM = 12;

/** The street map drawn under the routes. Swap this one object to change the source; the page names it in the caption. */
export const BASEMAP = {
  name: 'NSW Base Map',
  // NSW Spatial Services, free, official, Web Mercator 256 px tiles (the order in this service is z / y / x)
  urlTemplate: 'https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Base_Map/MapServer/tile/{z}/{y}/{x}',
  maxZoom: 19,
  attribution: 'Base map: State of New South Wales (Spatial Services, Department of Customer Service), Creative Commons Attribution.',
} as const;

export interface XY { x: number; y: number }
export interface DrawnLine { points: string; start: XY; end: XY }
export interface Tile { key: string; url: string; x: number; y: number; size: number }
export interface ProjectedRouteMap {
  size: number;
  careful: DrawnLine | null;
  normal: DrawnLine | null;
  busy: XY[];
  lot: XY;
  destination: XY;
  scaleBar: { px: number; m: number };
  zoom: number;
  tiles: Tile[];
}

/** Web Mercator metres for a latitude and longitude. */
export function mercator(p: LatLon): XY {
  const lat = Math.max(-85.0511, Math.min(85.0511, p[0]));
  return { x: (EARTH_RADIUS_M * p[1] * Math.PI) / 180, y: EARTH_RADIUS_M * Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360)) };
}

export function tileUrl(z: number, x: number, y: number, template: string = BASEMAP.urlTemplate): string {
  return template.replace('{z}', String(z)).replace('{y}', String(y)).replace('{x}', String(x));
}

/** The zoom whose tiles show a square `spanM` Mercator metres wide in no more than `size` pixels, so a tile is drawn at its own size or a little larger. */
export function zoomFor(spanM: number, size: number, maxZoom: number = BASEMAP.maxZoom): number {
  const z = Math.floor(Math.log2((size * MERCATOR_M_PER_PX_AT_Z0) / spanM));
  return Math.max(MIN_ZOOM, Math.min(maxZoom, Number.isFinite(z) ? z : MIN_ZOOM));
}

/** Project the routes in a route map onto a square picture, north up, fitting both routes plus `padM` metres all round, and work out the basemap tiles
 *  that sit under it. Returns null when there is nothing to draw. Pure: the same input always gives the same picture. */
export function projectRouteMap(rm: RouteMap, size = 820, padM = 150): ProjectedRouteMap | null {
  const lines = [rm.careful, rm.normal].filter((l): l is RouteLine => !!l && l.points.length >= 2);
  if (lines.length === 0) return null;
  const all: LatLon[] = lines.flatMap((l) => l.points);
  const ms = all.map(mercator);
  const lat0 = all.reduce((s, p) => s + p[0], 0) / all.length;
  const groundPerMercator = Math.cos((lat0 * Math.PI) / 180);   // a Mercator metre is longer than a ground metre away from the equator
  const pad = padM / groundPerMercator;
  const minX = Math.min(...ms.map((m) => m.x)) - pad, maxX = Math.max(...ms.map((m) => m.x)) + pad;
  const minY = Math.min(...ms.map((m) => m.y)) - pad, maxY = Math.max(...ms.map((m) => m.y)) + pad;
  const span = Math.max(maxX - minX, maxY - minY);   // pad > 0 keeps this above zero even for a one-point-wide route
  const k = size / span;
  const ox = (size - (maxX - minX) * k) / 2, oy = (size - (maxY - minY) * k) / 2;
  const toXY = (m: XY): XY => ({ x: ox + (m.x - minX) * k, y: oy + (maxY - m.y) * k });   // north is up
  const proj = (p: LatLon): XY => toXY(mercator(p));
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

  // basemap tiles covering the picture. The picture is the square [oxM, oxM+sideM] x [oyM, oyM+sideM] in Mercator metres.
  const viewMinX = minX - ox / k, viewMaxY = maxY + oy / k;   // the picture's top-left corner in Mercator metres
  const zoom = zoomFor(size / k, size);
  const mPerTilePx = MERCATOR_M_PER_PX_AT_Z0 / 2 ** zoom;
  const px0 = (viewMinX + Math.PI * EARTH_RADIUS_M) / mPerTilePx;           // world pixel of the left edge at this zoom
  const py0 = (Math.PI * EARTH_RADIUS_M - viewMaxY) / mPerTilePx;           // world pixel of the top edge
  const sidePx = size / k / mPerTilePx;                                      // the picture's side in tile pixels
  const scale = size / sidePx;                                               // svg units per tile pixel
  const lastTile = 2 ** zoom - 1;
  const tiles: Tile[] = [];
  for (let ty = Math.max(0, Math.floor(py0 / TILE_PX)); ty <= Math.min(lastTile, Math.floor((py0 + sidePx) / TILE_PX)); ty++) {
    for (let tx = Math.max(0, Math.floor(px0 / TILE_PX)); tx <= Math.min(lastTile, Math.floor((px0 + sidePx) / TILE_PX)); tx++) {
      tiles.push({ key: `${zoom}/${tx}/${ty}`, url: tileUrl(zoom, tx, ty), x: (tx * TILE_PX - px0) * scale, y: (ty * TILE_PX - py0) * scale, size: TILE_PX * scale });
    }
  }

  const groundMetresPerPx = groundPerMercator / k;
  const bar = [...SCALE_BAR_CHOICES_M].reverse().find((m) => m / groundMetresPerPx <= size * 0.3) ?? SCALE_BAR_CHOICES_M[0];
  return { size, careful, normal, busy, lot: first.start, destination: first.end, scaleBar: { px: bar / groundMetresPerPx, m: bar }, zoom, tiles };
}

/** A plain-words label for what a walk ends at. */
export function destinationLabel(d: { name: string | null; kind: string } | undefined | null): string {
  const name = d?.name ?? 'the destination';
  if (d?.kind === 'town_centre_edge') return `the edge of ${name}`;
  if (d?.kind === 'station_outline') return `${name} (the station outline: its entrance is not mapped)`;
  return `${name} (station entrance)`;
}
