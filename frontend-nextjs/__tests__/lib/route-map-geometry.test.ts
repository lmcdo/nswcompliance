/**
 * The route map is drawn from latitude/longitude with the Web Mercator projection the street-map tiles use: north must be up, east right,
 * every drawn point must be on the picture, and a degenerate route must never give NaN or Infinity.
 */
import { BASEMAP, destinationLabel, mercator, projectRouteMap, tileUrl, zoomFor } from '@/lib/route-map-geometry';
import type { LatLon, RouteLine, RouteMap } from '@/lib/evidence-statement';

const DEST = { name: 'Turramurra station', kind: 'station_outline' as const };

function line(points: LatLon[], busy: LatLon[] = []): RouteLine {
  return { length_m: 900, walk_m: 900, points, entrance: null, destination: DEST, busy_road_points: busy, osm_extract: null };
}
const mapOf = (careful: RouteLine | null, normal: RouteLine | null): RouteMap => ({ status: 'ok', careful, normal });

// a walk heading north-east: start (south-west) to end (north-east), about 700 m
const START: LatLon = [-33.7400, 151.1300];
const MID: LatLon = [-33.7380, 151.1330];
const END: LatLon = [-33.7355, 151.1385];
const NORMAL_PTS: LatLon[] = [START, [-33.7390, 151.1320], END];
const CAREFUL_PTS: LatLon[] = [START, MID, END];

const parse = (s: string) => s.split(' ').map((p) => { const [x, y] = p.split(',').map(Number); return { x, y }; });

describe('projectRouteMap', () => {
  it('puts north up and east right', () => {
    const r = projectRouteMap(mapOf(line(CAREFUL_PTS), null))!;
    const pts = parse(r.careful!.points);
    // END has a larger latitude than START: it must be higher on the picture, which is a SMALLER y
    expect(pts[2].y).toBeLessThan(pts[0].y);
    // END has a larger longitude than START: it must be further right, which is a LARGER x
    expect(pts[2].x).toBeGreaterThan(pts[0].x);
    // due north: y falls, x does not move
    const n = projectRouteMap(mapOf(line([[-33.74, 151.13], [-33.73, 151.13]]), null))!;
    const np = parse(n.careful!.points);
    expect(np[1].y).toBeLessThan(np[0].y);
    expect(Math.abs(np[1].x - np[0].x)).toBeLessThan(0.11);
    // due east: x rises, y does not move
    const e = projectRouteMap(mapOf(line([[-33.74, 151.13], [-33.74, 151.14]]), null))!;
    const ep = parse(e.careful!.points);
    expect(ep[1].x).toBeGreaterThan(ep[0].x);
    expect(Math.abs(ep[1].y - ep[0].y)).toBeLessThan(0.11);
  });

  it('keeps every projected route point inside the picture, with the padding margin kept clear', () => {
    const size = 820, padM = 150;
    const r = projectRouteMap(mapOf(line(CAREFUL_PTS), line(NORMAL_PTS)), size, padM)!;
    const all = [...parse(r.careful!.points), ...parse(r.normal!.points)];
    for (const p of all) {
      expect(p.x).toBeGreaterThanOrEqual(0); expect(p.x).toBeLessThanOrEqual(size);
      expect(p.y).toBeGreaterThanOrEqual(0); expect(p.y).toBeLessThanOrEqual(size);
    }
    // padM metres of margin all round (a little slack for the one-decimal rounding of the points)
    const minX = Math.min(...all.map((p) => p.x)), maxX = Math.max(...all.map((p) => p.x));
    const minY = Math.min(...all.map((p) => p.y)), maxY = Math.max(...all.map((p) => p.y));
    const pxPerM = r.scaleBar.px / r.scaleBar.m;
    const marginPx = padM * pxPerM;
    expect(minX).toBeGreaterThanOrEqual(marginPx - 0.2);
    expect(minY).toBeGreaterThanOrEqual(marginPx - 0.2);
    expect(size - maxX).toBeGreaterThanOrEqual(marginPx - 0.2);
    expect(size - maxY).toBeGreaterThanOrEqual(marginPx - 0.2);
    // and the margin is a real one, not nothing
    expect(marginPx).toBeGreaterThan(10);
  });

  it('works for a different picture size', () => {
    const r = projectRouteMap(mapOf(line(CAREFUL_PTS), null), 400, 100)!;
    expect(r.size).toBe(400);
    for (const p of parse(r.careful!.points)) {
      expect(p.x).toBeGreaterThanOrEqual(0); expect(p.x).toBeLessThanOrEqual(400);
      expect(p.y).toBeGreaterThanOrEqual(0); expect(p.y).toBeLessThanOrEqual(400);
    }
  });

  it('returns null when neither route has two or more points', () => {
    expect(projectRouteMap(mapOf(null, null))).toBeNull();
    expect(projectRouteMap(mapOf(line([]), line([])))).toBeNull();
    expect(projectRouteMap(mapOf(line([START]), line([END])))).toBeNull();
    expect(projectRouteMap({ status: 'unavailable' })).toBeNull();
  });

  it('draws the one route that has two or more points when the other has fewer', () => {
    const r = projectRouteMap(mapOf(line([START]), line(NORMAL_PTS)))!;
    expect(r.careful).toBeNull();
    expect(r.normal).not.toBeNull();
    expect(r.lot).toEqual(r.normal!.start);
    expect(r.destination).toEqual(r.normal!.end);
  });

  it('does not give NaN or Infinity for a route whose points are all identical', () => {
    const r = projectRouteMap(mapOf(line([START, START, START]), null))!;
    expect(r).not.toBeNull();
    const nums = [...parse(r.careful!.points).flatMap((p) => [p.x, p.y]), r.lot.x, r.lot.y, r.destination.x, r.destination.y, r.scaleBar.px, r.scaleBar.m];
    for (const n of nums) expect(Number.isFinite(n)).toBe(true);
    expect(r.scaleBar.px).toBeGreaterThan(0);
    expect(r.careful!.points).not.toMatch(/NaN|Infinity/);
    expect(r.lot.x).toBeGreaterThanOrEqual(0); expect(r.lot.x).toBeLessThanOrEqual(820);
    expect(r.lot.y).toBeGreaterThanOrEqual(0); expect(r.lot.y).toBeLessThanOrEqual(820);
  });

  it('gives the same output for the same input, and does not change its input', () => {
    const rm = mapOf(line(CAREFUL_PTS, [MID]), line(NORMAL_PTS, [MID]));
    const before = JSON.stringify(rm);
    const a = projectRouteMap(rm);
    const b = projectRouteMap(rm);
    expect(a).toEqual(b);
    expect(JSON.stringify(rm)).toBe(before);
    expect(projectRouteMap(JSON.parse(before))).toEqual(a);
  });

  describe('busy-road points', () => {
    it('drops busy points that are off the picture, and keeps those on it', () => {
      const far: LatLon = [-33.60, 151.30];   // many kilometres away
      const r = projectRouteMap(mapOf(line(CAREFUL_PTS, [MID, far]), null))!;
      expect(r.busy).toHaveLength(1);
      for (const b of r.busy) {
        expect(b.x).toBeGreaterThanOrEqual(0); expect(b.x).toBeLessThanOrEqual(r.size);
        expect(b.y).toBeGreaterThanOrEqual(0); expect(b.y).toBeLessThanOrEqual(r.size);
      }
    });

    it('merges duplicates that land in the same pixel, also across the two routes', () => {
      const nearMid: LatLon = [MID[0] + 0.0000001, MID[1]];   // about a centimetre away: the same pixel
      const r = projectRouteMap(mapOf(line(CAREFUL_PTS, [MID, MID, nearMid]), line(NORMAL_PTS, [MID])))!;
      expect(r.busy).toHaveLength(1);
    });

    it('keeps busy points that are far enough apart to be different pixels', () => {
      const r = projectRouteMap(mapOf(line(CAREFUL_PTS, [START, MID, END]), null))!;
      expect(r.busy).toHaveLength(3);
    });

    it('returns at most 600 busy points, however many are given', () => {
      const grid: LatLon[] = [];
      for (let i = 0; i < 60; i++) for (let j = 0; j < 60; j++) grid.push([-33.7400 + i * 0.00008, 151.1300 + j * 0.00010]);
      const one = projectRouteMap(mapOf(line(CAREFUL_PTS, grid), null))!;
      expect(one.busy.length).toBeGreaterThan(0);
      expect(one.busy.length).toBeLessThanOrEqual(600);
      const two = projectRouteMap(mapOf(line(CAREFUL_PTS, grid), line(NORMAL_PTS, grid)))!;
      expect(two.busy.length).toBeLessThanOrEqual(600);
    });
  });

  describe('scale bar', () => {
    it('is one of the round lengths, has a positive length in pixels, and is no more than 30% of the picture', () => {
      for (const size of [820, 400, 1200]) {
        for (const rm of [mapOf(line(CAREFUL_PTS), null), mapOf(line([[-33.74, 151.13], [-33.74, 151.1301]]), null), mapOf(line([[-33.80, 151.10], [-33.70, 151.20]]), null)]) {
          const r = projectRouteMap(rm, size)!;
          expect([20, 50, 100, 200, 500, 1000]).toContain(r.scaleBar.m);
          expect(r.scaleBar.px).toBeGreaterThan(0);
          expect(r.scaleBar.px).toBeLessThanOrEqual(0.3 * size + 1e-9);
        }
      }
    });

    it('is in proportion to the picture: its pixels per metre match the route pixels per metre', () => {
      const r = projectRouteMap(mapOf(line([[-33.74, 151.13], [-33.74, 151.1400]]), null))!;
      const p = parse(r.careful!.points);
      const metres = 0.01 * Math.cos((-33.74 * Math.PI) / 180) * 111320;
      const pxPerM = (p[1].x - p[0].x) / metres;
      expect(r.scaleBar.px / r.scaleBar.m).toBeCloseTo(pxPerM, 3);
    });
  });

  it('takes the lot from the start of the first drawn line and the destination from its end, careful before normal', () => {
    const both = projectRouteMap(mapOf(line(CAREFUL_PTS), line([[-33.7405, 151.1295], [-33.7350, 151.1390]])))!;
    expect(both.lot).toEqual(both.careful!.start);
    expect(both.destination).toEqual(both.careful!.end);
    expect(both.lot).not.toEqual(both.normal!.start);
    const onlyNormal = projectRouteMap(mapOf(null, line(NORMAL_PTS)))!;
    expect(onlyNormal.lot).toEqual(onlyNormal.normal!.start);
    expect(onlyNormal.destination).toEqual(onlyNormal.normal!.end);
    // start is the first point and end is the last point of the line
    const pts = parse(both.careful!.points);
    expect(Math.abs(both.lot.x - pts[0].x)).toBeLessThan(0.06);
    expect(Math.abs(both.lot.y - pts[0].y)).toBeLessThan(0.06);
    expect(Math.abs(both.destination.x - pts[pts.length - 1].x)).toBeLessThan(0.06);
    expect(Math.abs(both.destination.y - pts[pts.length - 1].y)).toBeLessThan(0.06);
  });

  it('writes the points as "x,y x,y" with one decimal place', () => {
    const r = projectRouteMap(mapOf(line(CAREFUL_PTS), null))!;
    expect(r.careful!.points).toMatch(/^-?\d+\.\d,-?\d+\.\d( -?\d+\.\d,-?\d+\.\d)+$/);
    expect(r.careful!.points.split(' ')).toHaveLength(CAREFUL_PTS.length);
  });
});

describe('destinationLabel', () => {
  it('gives each kind its plain-words form', () => {
    expect(destinationLabel({ name: 'Turramurra station and town centre', kind: 'town_centre_edge' })).toBe('the edge of Turramurra station and town centre');
    expect(destinationLabel({ name: 'Penrith station', kind: 'station_outline' })).toBe('Penrith station (the station outline: its entrance is not mapped)');
    expect(destinationLabel({ name: 'Penrith station', kind: 'entrance' })).toBe('Penrith station (station entrance)');
  });

  it('falls back to "the destination" for a missing destination or name', () => {
    expect(destinationLabel(null)).toBe('the destination (station entrance)');
    expect(destinationLabel(undefined)).toBe('the destination (station entrance)');
    expect(destinationLabel({ name: null, kind: 'town_centre_edge' })).toBe('the edge of the destination');
    expect(destinationLabel({ name: null, kind: 'entrance' })).toBe('the destination (station entrance)');
  });
});


describe('Web Mercator and the street-map tiles', () => {
  it('mercator puts the equator at 0 and longitude 180 at half the world', () => {
    expect(mercator([0, 0]).x).toBeCloseTo(0, 6);
    expect(mercator([0, 0]).y).toBeCloseTo(0, 6);
    expect(mercator([0, 180]).x).toBeCloseTo(Math.PI * 6378137, 3);
    expect(mercator([45, 0]).y).toBeCloseTo(5621521.486, 2);          // the published value for 45 degrees north
  });

  it('a known Sydney point lands in the known tile (zoom 16, Sydney CBD)', () => {
    const r = projectRouteMap(mapOf(line([[-33.8688, 151.2093], [-33.8680, 151.2100]]), null), 820, 5)!;
    const k = 2 ** r.zoom;
    const lat = (-33.8688 * Math.PI) / 180;
    const wx = Math.floor(((151.2093 + 180) / 360) * k);
    const wy = Math.floor(((1 - Math.log(Math.tan(lat) + 1 / Math.cos(lat)) / Math.PI) / 2) * k);
    expect(r.tiles.map((t) => t.key)).toContain(`${r.zoom}/${wx}/${wy}`);
  });

  it('tiles cover the whole picture with no gap, and are drawn at least at their own size', () => {
    const r = projectRouteMap(mapOf(line(CAREFUL_PTS), line(NORMAL_PTS)))!;
    expect(r.tiles.length).toBeGreaterThan(0);
    expect(r.tiles.length).toBeLessThanOrEqual(25);
    const minX = Math.min(...r.tiles.map((t) => t.x)), minY = Math.min(...r.tiles.map((t) => t.y));
    const maxX = Math.max(...r.tiles.map((t) => t.x + t.size)), maxY = Math.max(...r.tiles.map((t) => t.y + t.size));
    expect(minX).toBeLessThanOrEqual(0.001); expect(minY).toBeLessThanOrEqual(0.001);
    expect(maxX).toBeGreaterThanOrEqual(r.size - 0.001); expect(maxY).toBeGreaterThanOrEqual(r.size - 0.001);
    const size = r.tiles[0].size;
    expect(size).toBeGreaterThanOrEqual(256 * 0.999);                  // never shrunk, so street names are not made smaller than the tile's own
    expect(size).toBeLessThan(256 * 2.001);
    for (const t of r.tiles) expect(Math.abs(t.size - size)).toBeLessThan(1e-6);
  });

  it('neighbouring tiles touch exactly', () => {
    const r = projectRouteMap(mapOf(line(CAREFUL_PTS), null))!;
    const byKey = new Map(r.tiles.map((t) => [t.key, t]));
    for (const t of r.tiles) {
      const [z, x, y] = t.key.split('/').map(Number);
      const right = byKey.get(`${z}/${x + 1}/${y}`), below = byKey.get(`${z}/${x}/${y + 1}`);
      if (right) expect(right.x).toBeCloseTo(t.x + t.size, 6);
      if (below) expect(below.y).toBeCloseTo(t.y + t.size, 6);
    }
  });

  it('the route stays on the tiles: the start point sits inside the tile that holds it', () => {
    const r = projectRouteMap(mapOf(line(CAREFUL_PTS), null))!;
    const first = parse(r.careful!.points)[0];
    const holder = r.tiles.find((t) => first.x >= t.x && first.x < t.x + t.size && first.y >= t.y && first.y < t.y + t.size);
    expect(holder).toBeTruthy();
    const n = 2 ** r.zoom;
    const lat = (START[0] * Math.PI) / 180;
    const tx = Math.floor(((START[1] + 180) / 360) * n);
    const ty = Math.floor(((1 - Math.log(Math.tan(lat) + 1 / Math.cos(lat)) / Math.PI) / 2) * n);
    expect(holder!.key).toBe(`${r.zoom}/${tx}/${ty}`);
  });

  it('zoom is clamped to the service, and is finite for any span', () => {
    expect(zoomFor(1, 820)).toBe(BASEMAP.maxZoom);
    expect(zoomFor(1e9, 820)).toBe(12);
    expect(zoomFor(0, 820)).toBeLessThanOrEqual(BASEMAP.maxZoom);
    expect(Number.isFinite(zoomFor(NaN, 820))).toBe(true);
  });

  it('tileUrl fills z, y then x in the order this service uses', () => {
    expect(tileUrl(16, 60294, 39327)).toBe('https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Base_Map/MapServer/tile/16/39327/60294');
    expect(tileUrl(3, 1, 2, 'https://t.example/{z}/{x}/{y}.png')).toBe('https://t.example/3/1/2.png');
  });

  it('the scale bar is in ground metres', () => {
    const r = projectRouteMap(mapOf(line(CAREFUL_PTS), null))!;
    const a = mercator(START), b = mercator(END);
    const groundM = Math.hypot(b.x - a.x, b.y - a.y) * Math.cos((-33.74 * Math.PI) / 180);
    const q = parse(r.careful!.points);
    const px = Math.hypot(q[2].x - q[0].x, q[2].y - q[0].y);
    expect(r.scaleBar.px / r.scaleBar.m).toBeCloseTo(px / groundM, 1);
  });
});
